"""llm_engine.py
Structured prompt assembly and guarded local LLM inference for inline meeting suggestions.

Optimized for low-latency completion on:
- Model: llama-2-7b-chat
- Quant: Q4_K_M
- Context: 2k tokens max
- Hardware: RTX 2060 6GB or CPU fallback

Design goals:
- Keep transcript context first, retrieved docs second, inference input last.
- Enforce output contract through guardrails.
- Use a structured response model so downstream consumers know what they got.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

LOG = logging.getLogger("llm_engine")


@dataclass(frozen=True)
class LLMSuggestion:
    """Structured suggestion contract for downstream consumers."""

    text: str
    language: str = "en"
    token_count: int = 0
    source: str = "llm"


def _build_suggest_prompt(transcript: str, docs: str, current: str) -> str:
    """Assemble a compact prompt for low-latency completion.

    Keeping the prompt compact preserves generation budget on small context models.
    Rule of thumb: as much transcript context as fits, capped doc block, minimal system framing.
    """
    transcript_block = (transcript or "").strip()[:1000]
    doc_block = (docs or "").strip()[:220]
    current_block = (current or "").strip()

    parts = ["<s>[INST] <<SYS>>", "You are a silent meeting copilot."]
    parts.extend(
        [
            "Output only concise inline text suggestions.",
            "Use the speaker's language: English, Bangla, or mixed.",
            "Mirror the language of the current sentence.",
            "Do not explain, narrate, or add punctuation unless it helps insertion.",
            "<</SYS>>",
            "",
            "Transcript context:",
            transcript_block,
            "",
        ]
    )
    if doc_block:
        parts.extend(["Retrieved docs:", doc_block, ""])
    parts.extend(
        [
            "Current transcription:",
            current_block,
            "",
            "Reply suggestion: [/INST]",
        ]
    )
    prompt = "\n".join(parts)
    return prompt


def apply_suggestion_guardrails(text: str, max_chars: int = 800) -> str:
    """Apply deterministic guardrails to LLM output."""
    if not text:
        return ""
    normalized = " ".join(text.split())
    if len(normalized) > max_chars:
        normalized = normalized[:max_chars].rstrip() + "…"
    return normalized


class LLMEngine:
    """Wrapper around local LLM inference with guarded output contract."""

    def __init__(self, model_path: str, n_ctx: int = 2048, n_gpu_layers: int = 35) -> None:
        try:
            from llama_cpp import Llama  # noqa: F811

            self._model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
        except Exception as exc:
            LOG.error("LLM init failed: %s", exc)
            raise RuntimeError(f"llm_init_failed:{exc}") from exc

    def suggest_structured(
        self,
        transcript: str = "",
        docs: str = "",
        current: str = "",
        max_tokens: int = 220,
        temperature: float = 0.15,
    ) -> LLMSuggestion:
        prompt = _build_suggest_prompt(
            transcript=transcript, docs=docs, current=current
        )
        try:
            result = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["User:", "\nUser", "Assistant:"],
            )
        except Exception as exc:
            LOG.warning("LLM inference failed: %s", exc)
            return LLMSuggestion(text="", source="fallback")

        choices = result.get("choices") or []
        raw_text = ""
        if choices:
            raw_text = (choices[0].get("text") or "").strip()
        text = apply_suggestion_guardrails(raw_text)
        usage = result.get("usage") or {}
        token_count = int(usage.get("total_tokens") or len(prompt.split()))
        return LLMSuggestion(text=text, token_count=token_count, source="llm")

    def suggest(
        self,
        prompt: str,
        max_tokens: int = 220,
        temperature: float = 0.15,
    ) -> LLMSuggestion:
        """Backwards-compatible wrapper for single-prompt suggestion calls.
        Kept so benchmark and legacy callers do not need edits.
        """
        return self.suggest_structured(
            transcript=prompt, max_tokens=max_tokens, temperature=temperature
        )

    def close(self) -> None:
        try:
            del self._model
        except Exception as exc:
            LOG.debug("LLM close failed: %s", exc)
