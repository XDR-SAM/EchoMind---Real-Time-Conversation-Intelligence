import threading

import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_name="small", device="cuda", compute_type="float16"):
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self._prev_lang = "en"
        self._lang_lock = threading.Lock()

    def _choose_language(self, override=None):
        if override in {"en", "bn"}:
            with self._lang_lock:
                self._prev_lang = override
            return override
        with self._lang_lock:
            return self._prev_lang

    def _split_chunks(self, audio_np, seconds=1.5, overlap=0.25):
        sr = 16000
        frame = int(seconds * sr)
        hop = frame - int(overlap * sr)
        if hop <= 0:
            hop = frame
        starts = range(0, max(audio_np.shape[0], 1), hop)
        out = []
        for start in starts:
            end = start + frame
            chunk = audio_np[start:end]
            if chunk.shape[0] == 0:
                break
            if chunk.shape[0] < frame:
                chunk = np.pad(chunk, (0, frame - chunk.shape[0]))
            out.append(np.ascontiguousarray(chunk, dtype=np.float32))
        return out or [np.zeros(frame, dtype=np.float32)]

    def transcribe(self, audio_np, language=None):
        audio_np = np.ascontiguousarray(audio_np, dtype=np.float32)
        chunks = self._split_chunks(audio_np)
        hint = self._choose_language(language)
        text_parts = []
        detected_lang = hint
        for chunk in chunks:
            segments, info = self.model.transcribe(
                chunk,
                language=hint,
                beam_size=1,
                repetition_penalty=1.05,
                temperature=0.0,
                condition_on_previous_text=True,
            )
            for segment in segments:
                text = segment.text.strip()
                if text:
                    text_parts.append(text)
            detected_lang = info.language or detected_lang
        full = " ".join(text_parts).strip()
        if not full:
            return "", detected_lang
        with self._lang_lock:
            self._prev_lang = detected_lang
        return full, detected_lang

    def close(self):
        try:
            del self.model
        except Exception:
            pass
