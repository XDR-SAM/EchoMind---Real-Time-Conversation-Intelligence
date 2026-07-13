import threading
import time
from queue import Queue


class Pipeline:
    def __init__(
        self,
        audio: AudioCapture,
        transcriber: Transcriber,
        context_engine: ContextEngine,
        llm_engine: LLMEngine,
        ui_queue: Queue,
        vad: EnergyVAD | None = None,
    ):
        self.audio = audio
        self.transcriber = transcriber
        self.context = context_engine
        self.llm = llm_engine
        self.ui_queue = ui_queue
        self.vad = EnergyVAD() if vad is None else vad

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.transcript_buffer: list[str] = []
        self.latest_lang = "en"

    def _build_prompt(self, transcript_text: str, context_text: str) -> str:
        return (
            "<s>[INST] <<SYS>>\n"
            "You are an in-meeting assistant for the speaker. "
            "Generate concise, actionable reply suggestions.\n"
            "<</SYS>>\n\n"
            f"Transcript:\n{transcript_text}\n\n"
            f"Context:\n{context_text}\n\n"
            "Reply suggestion: [/INST]"
        )

    def _worker(self) -> None:
        while not self._stop.is_set():
            audio = self.audio.read()
            if audio is None:
                time.sleep(0.03)
                continue

            if not bool(self.vad(audio)):
                continue

            try:
                text, lang = self.transcriber.transcribe(audio)
            except Exception:
                continue

            text = (text or "").strip()
            if not text:
                continue

            self.latest_lang = lang or self.latest_lang
            self.transcript_buffer.append(text)

            window = " ".join(self.transcript_buffer[-12:])[-1500:]
            context_text = ""
            try:
                context_text = self.context.search(window)
            except Exception:
                context_text = ""

            prompt = self._build_prompt(window, context_text)
            try:
                suggestion = self.llm.suggest(prompt, max_tokens=220, temperature=0.15)
            except Exception:
                suggestion = ""

            try:
                self.ui_queue.put_nowait(
                    {
                        "transcript": window,
                        "suggestion": suggestion,
                        "lang": self.latest_lang,
                    }
                )
            except Exception:
                pass

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
