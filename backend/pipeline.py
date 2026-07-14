"""CrewAI-inspired pipeline execution with explicit phases and state management."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from queue import Queue
from typing import Callable, Optional


class PipelineGuardRailError(Exception):
    """Raised when pipeline output fails validation."""


@dataclass
class SuggestionCandidate:
    candidate: str
    source: str = "llm"


@dataclass
class PipelineState:
    """Structured state flowing through pipeline phases."""
    transcript_window: str = ""
    latest_lang: str = "en"
    raw_suggestion: str = ""
    validated_suggestion: Optional[SuggestionCandidate] = None
    context_snippet: str = ""
    phase: str = "init"
    phase_errors: list[str] = field(default_factory=list)


Guardrail = Callable[[str, PipelineState], tuple[bool, str]]


def default_suggestion_guardrail(raw: str, state: PipelineState) -> tuple[bool, str]:
    """Reject empty or suspiciously long suggestions; normalize whitespace."""
    stripped = (raw or "").strip()
    if not stripped:
        return False, "empty suggestion"
    if len(stripped) > 800:
        return False, f"oversized suggestion ({len(stripped)} chars)"
    normalized = " ".join(stripped.split())
    return True, normalized


class Pipeline:
    def __init__(
        self,
        audio: object,
        transcriber: object,
        context_engine: object,
        llm_engine: object,
        ui_queue: Queue,
        vad: object | None = None,
        session_mgr: object | None = None,
    ) -> None:
        self.audio = audio
        self.transcriber = transcriber
        self.context = context_engine
        self.llm = llm_engine
        self.ui_queue = ui_queue
        self.vad: object = vad
        self.session_mgr = session_mgr

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self.guardrails: list[Guardrail] = [default_suggestion_guardrail]

    # -------------- Phases --------------

    def _run_transcribe_phase(self, audio_chunk, state: PipelineState) -> None:
        """Transcribe audio and update language prior."""
        try:
            text, lang = self.transcriber.transcribe(audio_chunk)
        except Exception as exc:
            raise RuntimeError(f"transcribe_failed: {exc}") from exc

        if text and text.strip():
            state.latest_lang = lang or state.latest_lang

            if not state.transcript_window:
                state.transcript_window = text.strip()
            else:
                state.transcript_window = (
                    f"{state.transcript_window} {text.strip()}"
                )[-1200:]
        else:
            raise RuntimeError("empty_transcript")

    def _run_retrieval_phase(self, state: PipelineState) -> None:
        """Retrieve relevant context for the current transcript window."""
        if not state.transcript_window:
            state.context_snippet = ""
            return
        try:
            state.context_snippet = self.context.search(state.transcript_window) or ""
        except Exception as exc:
            state.phase_errors.append(f"rag_failed:{exc}")
            state.context_snippet = ""

    def _run_reasoning_phase(self, state: PipelineState) -> None:
        """Generate inline suggestion and validate through guardrails."""
        prompt = self._build_prompt(state.transcript_window, state.context_snippet)
        try:
            state.raw_suggestion = self.llm.suggest(prompt, max_tokens=220, temperature=0.15)
        except Exception as exc:
            raise RuntimeError(f"llm_failed:{exc}") from exc

        raw = state.raw_suggestion or ""
        for fn in self.guardrails:
            passed, msg = fn(raw, state)
            if not passed:
                raise PipelineGuardRailError(msg)
            raw = msg

        state.validated_suggestion = SuggestionCandidate(
            candidate=raw, source="llm"
        )

    def _run_emit_phase(self, state: PipelineState) -> None:
        """Dispatch transcript and suggestion to the UI."""
        payload = {
            "transcript": state.transcript_window,
            "suggestion": state.validated_suggestion.candidate
            if state.validated_suggestion
            else "",
            "lang": state.latest_lang,
        }
        try:
            self.ui_queue.put_nowait(payload)
        except Exception:
            pass

    # -------------- Orchestrator --------------

    def _run_single_iteration(self, audio_chunk) -> Optional[PipelineState]:
        state = PipelineState(phase="transcribe")

        # Phase 1: transcribe
        try:
            self._run_transcribe_phase(audio_chunk, state)
            state.phase = "retrieval"
        except RuntimeError:
            return None

        # Phase 2: retrieval
        self._run_retrieval_phase(state)
        state.phase = "reasoning"

        # Phase 3: reasoning + validation
        try:
            self._run_reasoning_phase(state)
        except (RuntimeError, PipelineGuardRailError):
            return None

        state.phase = "emit"
        self._run_emit_phase(state)
        state.phase = "ready"

        if state.transcript_window:
            try:
                mgr = self.session_mgr
                if mgr is not None and hasattr(mgr, "record_chunk"):
                    mgr.record_chunk(state.transcript_window, state.latest_lang)
            except Exception:
                pass

        return state

    def _worker(self) -> None:
        while not self._stop.is_set():
            audio = self.audio.read()
            if audio is None:
                time.sleep(0.03)
                continue

            vad_result = bool(self.vad(audio)) if self.vad is not None else True
            if not vad_result:
                continue

            result = self._run_single_iteration(audio)
            if result is None:
                continue

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)

    # -------------- Prompt construction --------------

    def _build_prompt(self, transcript_text: str, context_text: str) -> str:
        return (
            "<s>[INST] <<SYS>>\n"
            "You are a concise meeting assistant for the speaker. "
            "Output only concise, actionable inline suggestions in the user's language. "
            "Do not narrate or explain."
            "<</SYS>>\n\n"
            f"Transcript:\n{transcript_text}\n\n"
            f"Context:\n{context_text}\n\n"
            "Reply suggestion: [/INST]"
        )
