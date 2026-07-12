"""Manual runner when package execution is awkward on Windows."""

import logging
import sys
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QTextCharFormat, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from audio_capture import AudioCapture
from backend.config import settings
from context_engine import ContextEngine
from llm_engine import LLMEngine
from transcriber import Transcriber
from ui import OverlayWindow
from vad import EnergyVAD

logging.basicConfig(level=logging.INFO)


def build_pipeline(audio, transcriber, context_engine, llm_engine, ui_queue):
    # Intentionally avoid importing Pipeline to keep this script explicit.
    from backend.pipeline import Pipeline

    vad = EnergyVAD(energy_floor=0.006, hangover_frames=5)
    pipeline = Pipeline(audio, transcriber, context_engine, llm_engine, ui_queue, vad)
    pipeline.start()
    return pipeline


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ui_queue = __import__("queue").Queue(maxsize=8)
    window = OverlayWindow(ui_queue)
    window.show()

    audio = AudioCapture(
        sample_rate=settings.SAMPLE_RATE,
        chunk_seconds=settings.CHUNK_SECONDS,
        device_substr=settings.DEVICE_NAME_SUBSTR,
    )
    transcriber = Transcriber(
        model_name=settings.MODEL_NAME,
        device="cuda",
        compute_type="float16",
    )
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
    pipeline = build_pipeline(audio, transcriber, context_engine, llm_engine, ui_queue)

    def drain_queue():
        try:
            start = time.perf_counter()
            count = 0
            while True:
                item = ui_queue.get_nowait()
                window.apply_update(item)
                count += 1
                if count >= 4:
                    break
            elapsed_ms = (time.perf_counter() - start) * 1000
            if elapsed_ms > 8:
                logging.info("ui_queue drain=%d elapsed=%.1fms", count, elapsed_ms)
        except __import__("queue").Empty:
            pass

    timer = QTimer()
    timer.timeout.connect(drain_queue)
    timer.start(90)

    try:
        exit_code = app.exec()
    except KeyboardInterrupt:
        exit_code = 0

    pipeline.stop()
    audio.stop()
    transcriber.close()
    llm_engine.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())