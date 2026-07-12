from __future__ import annotations

import logging

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from backend.audio_capture import AudioCapture
from backend.config import settings
from backend.context_engine import ContextEngine
from backend.llm_engine import LLMEngine
from backend.transcriber import Transcriber
from backend.ui import OverlayWindow
from backend.vad import EnergyVAD


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)

    ui_queue = __import__("queue").Queue(maxsize=12)
    window = OverlayWindow(ui_queue)
    window.show()

    audio = AudioCapture(
        sample_rate=settings.SAMPLE_RATE,
        chunk_seconds=settings.CHUNK_SECONDS,
        device_substr=settings.DEVICE_NAME_SUBSTR,
    )
    transcriber = Transcriber(model_name=settings.MODEL_NAME, device="cuda", compute_type="float16")
    context_engine = ContextEngine(
        embedding_model=settings.RAG_EMBEDDING_MODEL,
        docs_dir=settings.DOCS_DIR,
        top_k=settings.RAG_TOP_K,
    )
    llm_engine = LLMEngine(
        model_path=settings.LLM_MODEL_PATH,
        n_ctx=settings.LLM_CONTEXT_SIZE,
        n_gpu_layers=settings.LLM_GPU_LAYERS,
    )

    vad = EnergyVAD()
    from backend.pipeline import Pipeline

    pipeline = Pipeline(audio, transcriber, context_engine, llm_engine, ui_queue, vad)
    pipeline.start()

    def cleanup():
        try:
            pipeline.stop()
        except Exception:
            pass
        try:
            audio.stop()
        except Exception:
            pass
        try:
            transcriber.close()
        except Exception:
            pass
        try:
            llm_engine.close()
        except Exception:
            pass

    fast_exit = QTimer()
    fast_exit.setSingleShot(True)
    fast_exit.timeout.connect(app.quit)
    fast_exit.start(10)

    try:
        exit_code = app.exec()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        cleanup()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
