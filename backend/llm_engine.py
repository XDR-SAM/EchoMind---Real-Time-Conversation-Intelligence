"""llm_engine.py
Structured prompt assembly and guarded local LLM inference for inline meeting suggestions.

Optimized for low-latency completion on:
|- Model: NVIDIA-Nemotron-3-Nano-4B
|- Quant: Q4_K_M
|- Context: 2k tokens max
|- Hardware: RTX 2060 6GB or CPU fallback

Design goals:
- Keep transcript context first, retrieved docs second, inference input last.
- Enforce output contract through guardrails.
- Use a structured response model so downstream consumers know what they got.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

LOG = logging.getLogger("llm_engine")


@dataclass(frozen=True)
class ActionItem:
    text: str
    owner: str | None = None
    due: str | None = None
    confidence: float = 0.0


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


def _build_action_prompt(transcript: str) -> str:
    """Assemble a constrained prompt to extract action items."""
    transcript_block = (transcript or "").strip()[:1200]
    return (
        "<s>[INST] <<SYS>>\n"
        "Extract only the explicit action items from the meeting transcript.\n"
        'Reply as a JSON array only: [{"text": "...", "owner": "...", "due": "..."}].\n'
        "Use empty strings instead of inventing missing fields.\n"
        "<</SYS>>\n\n"
        f"Transcript:\n{transcript_block}\n\n"
        "Reply JSON: [/INST]"
    )


def apply_suggestion_guardrails(text: str, max_chars: int = 800) -> str:
    """Apply deterministic guardrails to LLM output."""
    if not text:
        return ""
    normalized = " ".join(text.split())
    if len(normalized) > max_chars:
        normalized = normalized[:max_chars].rstrip() + "…"
    return normalized


class LLMEngine:
    """Wrapper around local or OpenAI-compatible inference with guarded output contract."""

    def __init__(self, model_path: str, n_ctx: int = 2048, n_gpu_layers: int = 35) -> None:
        self._backend = getattr(settings, "LLM_BACKEND", "local")
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._model = None
        if self._backend != "openai_compat":
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

    def _openai_chat(self, prompt: str, generation_kwargs: dict | None = None) -> str:
        api_base = getattr(settings, "OPENAI_API_BASE", "http://localhost:1234/v1").rstrip("/")
        api_key = getattr(settings, "OPENAI_API_KEY", "lm-studio") or "lm-studio"
        model = getattr(settings, "OPENAI_MODEL", "")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.15,
            "max_tokens": 220,
        }
        if generation_kwargs:
            payload.update(generation_kwargs)
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError
        import json as _json
        data = _json.dumps(payload).encode("utf-8")
        req = Request(f"{api_base}/chat/completions", data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=120) as resp:
                body = _json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"openai_http_error:{exc.code}:{exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"openai_url_error:{exc.reason}") from exc
        choices = body.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message") or {}).get("content") or ""

    def suggest_structured(
        self,
        transcript: str = "",
        docs: str = "",
        current: str = "",
        generation_kwargs: dict | None = None,
    ) -> LLMSuggestion:
        prompt = _build_suggest_prompt(
            transcript=transcript, docs=docs, current=current
        )
        raw_text = ""
        token_count = 0
        try:
            if self._backend == "openai_compat":
                raw_text = self._openai_chat(prompt, generation_kwargs)
                token_count = len(prompt.split())
            else:
                stop_tokens = ["User:", "\nUser", "Assistant:"]
                gen = {
                    "max_tokens": 220,
                    "temperature": 0.15,
                    "stop": stop_tokens,
                }
                if generation_kwargs:
                    gen.update(generation_kwargs)
                result = self._model(prompt, **gen)
                choices = result.get("choices") or []
                if choices:
                    raw_text = (choices[0].get("text") or "").strip()
                usage = result.get("usage") or {}
                token_count = int(usage.get("total_tokens") or len(prompt.split()))
        except Exception as exc:
            LOG.warning("LLM inference failed: %s", exc)
            return LLMSuggestion(text="", source="fallback")

        text = apply_suggestion_guardrails(raw_text)
        return LLMSuggestion(text=text, token_count=token_count, source="llm")

    def suggest(
        self,
        prompt: str,
        generation_kwargs: dict | None = None,
    ) -> LLMSuggestion:
        """Backwards-compatible wrapper for single-prompt suggestion calls.
        Kept so benchmark and legacy callers do not need edits.
        """
        return self.suggest_structured(
            transcript=prompt, generation_kwargs=generation_kwargs
        )

    def suggest_action_items(
        self,
        transcript: str,
        generation_kwargs: dict | None = None,
    ) -> list[ActionItem]:
        prompt = _build_action_prompt(transcript)
        try:
            if self._backend == "openai_compat":
                raw_text = self._openai_chat(prompt, generation_kwargs)
            else:
                stop_tokens = ["User:", "\nUser", "Assistant:"]
                gen = {
                    "max_tokens": 160,
                    "temperature": 0.0,
                    "stop": stop_tokens,
                }
                if generation_kwargs:
                    gen.update(generation_kwargs)
                result = self._model(prompt, **gen)
                choices = result.get("choices") or []
                raw_text = ""
                if choices:
                    raw_text = (choices[0].get("text") or "").strip()
        except Exception as exc:
            LOG.warning("LLM action item extraction failed: %s", exc)
            return []
        if not raw_text:
            return []
        try:
            objects = json.loads(raw_text)
        except json.JSONDecodeError:
            LOG.debug("Action items JSON parse failed; returning empty list.")
            return []
        if not isinstance(objects, list):
            return []
        items: list[ActionItem] = []
        for item in objects:
            if not isinstance(item, dict):
                continue
            text = (item.get("text") or "").strip()
            if not text:
                continue
            owner = (item.get("owner") or "").strip() or None
            due = (item.get("due") or "").strip() or None
            confidence = float(item.get("confidence") or 0.4)
            confidence = max(0.0, min(1.0, confidence))
            items.append(ActionItem(text=text, owner=owner, due=due, confidence=confidence))
        return items

    def close(self) -> None:
        try:
            del self._model
        except Exception as exc:
            LOG.debug("LLM close failed: %s", exc)
