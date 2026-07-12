from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_name="small", device="cuda", compute_type="float16"):
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(self, audio_np, language=None):
        audio_np = np.ascontiguousarray(audio_np, dtype=np.float32)
        segments, info = self.model.transcribe(
            audio_np,
            language=language,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=200),
            repetition_penalty=1.05,
            temperature=0.0,
            condition_on_previous_text=True,
        )
        text_parts, detected_lang = [], info.language
        for segment in segments:
            text_parts.append(segment.text.strip())
        return " ".join(text_parts).strip(), detected_lang

    def close(self):
        try:
            del self.model
        except Exception:
            pass
