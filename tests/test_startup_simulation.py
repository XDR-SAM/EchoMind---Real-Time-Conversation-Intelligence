"""Import-safe startup simulation for main.py.

Mock backend.config before importing main so sandbox config/binary-dependency issues
don't block verification.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import TestCase
from unittest import mock

import numpy as np


class StartupSimulationTests(TestCase):
    @staticmethod
    def _make_fake_settings():
        return types.SimpleNamespace(
            SAMPLE_RATE=16000,
            CHUNK_SECONDS=2.0,
            MODEL_NAME="base",
            MODEL_DIR=Path("models"),
            DOCS_DIR=Path("docs_ingested"),
            LLM_MODEL_PATH="models/llama-2-7b-chat.Q4_K_M.gguf",
            LLM_CONTEXT_SIZE=2048,
            LLM_GPU_LAYERS=-1,
            RAG_EMBEDDING_MODEL="all-MiniLM-L6-v2",
            RAG_TOP_K=3,
            MAX_TRANSCRIPT_CHARS=1200,
            OVERLAY_OPACITY=0.92,
            OVERLAY_WIDTH=520,
            OVERLAY_HEIGHT=420,
            DEVICE_NAME_SUBSTR="speakers",
        )

    def _inject_fake_config(self):
        fake_mod = types.ModuleType("backend.config")
        fake_mod.settings = self._make_fake_settings()
        sys.modules["backend.config"] = fake_mod

    def test_main_returns_zero_from_benchmark_mode_without_qt(self) -> None:
        self._inject_fake_config()
        try:
            import backend.main as main_module
        finally:
            sys.modules.pop("backend.config", None)

        fake_model = Path("models/llama-2-7b-chat.Q4_K_M.gguf")

        class FakePath:
            def __init__(self, *args, **kwargs):
                pass

            def exists(self, *args, **kwargs):
                return True

            def is_file(self, *args, **kwargs):
                return True

            def stat(self, *args, **kwargs):
                return FakeStat()

            def mkdir(self, *args, **kwargs):
                return None

            def __truediv__(self, other):
                return FakePath()

        class FakeStat:
            st_size = 20_000_000
            def __init__(self, *args, **kwargs):
                pass

        class FakeAudioCapture:
            def __init__(self, *args, **kwargs):
                pass
            def read(self):
                return None
            def start(self):
                return None
            def stop(self):
                return None

        class FakeTranscriber:
            def __init__(self, *args, **kwargs):
                pass
            def transcribe(self, audio):
                return "hello world", "en"
            def close(self):
                return None

        class FakeContextEngine:
            def __init__(self, *args, **kwargs):
                pass
            def search(self, query):
                return ""

        class FakeLLMEngine:
            def __init__(self, *args, **kwargs):
                pass
            def suggest(self, prompt, max_tokens=0, temperature=0.0):
                return "suggestion"
            def close(self):
                return None

        class FakeVAD:
            def __call__(self, chunk):
                return True
            def reset(self):
                return None

        def fake_detect_cuda():
            return False, "nvidia-smi not found"

        def fake_check_model():
            return True, FakePath(), f"model ok: {fake_model} (19.1 MB)"

        with mock.patch.object(main_module, "_detect_cuda", side_effect=fake_detect_cuda):
            with mock.patch.object(main_module, "_check_model_files", side_effect=fake_check_model):
                with mock.patch.object(main_module, "AudioCapture", FakeAudioCapture):
                    with mock.patch.object(main_module, "Transcriber", FakeTranscriber):
                        with mock.patch.object(main_module, "ContextEngine", FakeContextEngine):
                            with mock.patch.object(main_module, "LLMEngine", FakeLLMEngine):
                                with mock.patch.object(main_module, "EnergyVAD", FakeVAD):
                                    with mock.patch("builtins.open", mock.mock_open(read_data="x" * 20_000_000)):
                                        exit_code = main_module.main(argv=["--benchmark"])

        self.assertEqual(exit_code, 0)

    def test_main_returns_nonzero_when_model_missing(self) -> None:
        self._inject_fake_config()
        try:
            import backend.main as main_module
        finally:
            sys.modules.pop("backend.config", None)

        def fake_detect_cuda():
            return False, "nvidia-smi not found"

        def fake_check_model():
            return False, Path("missing"), "missing model file: missing"

        with mock.patch.object(main_module, "_detect_cuda", side_effect=fake_detect_cuda):
            with mock.patch.object(main_module, "_check_model_files", side_effect=fake_check_model):
                exit_code = main_module.main(argv=[])
        self.assertEqual(exit_code, 1)
