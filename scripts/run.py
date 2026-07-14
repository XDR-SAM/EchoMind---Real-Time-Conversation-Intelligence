"""Manual launcher for Windows when package execution is awkward."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

# Ensure repo root is on sys.path so backend/* can be imported as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.audio_capture import AudioCapture
from backend.config import compute_for_stt, settings
from backend.context_engine import ContextEngine
from backend.llm_engine import LLMEngine
from backend.main import main
from backend.transcriber import Transcriber
from backend.vad import EnergyVAD


def _make_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(["MeetingCopilot"])
    app.setQuitOnLastWindowClosed(False)
    return app


def run() -> int:
    app = _make_app()
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
