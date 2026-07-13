"""Benchmark harness for fake-audio→text inference and end-to-end synthetic pipeline measurements."""
from __future__ import annotations

import time
from unittest import TestCase

import numpy as np

from backend.config import settings


class FakeEngine:
    def __init__(self, latency_s: float, response: str):
        self._latency = latency_s
        self._response = response
        self.close_called = False

    def suggest(self, prompt: str, max_tokens: int = 220, temperature: float = 0.0):
        time.sleep(self._latency)
        return self._response

    def close(self):
        self.close_called = True


class FakeTranscriber:
    def __init__(self, latency_s: float, output: tuple[str, str]):
        self._latency = latency_s
        self._output = output
        self.close_called = False

    def transcribe(self, audio_np):
        time.sleep(self._latency)
        return self._output

    def close(self):
        self.close_called = True


class BenchmarkTests(TestCase):
    def test_transcriber_benchmark_measures_latency(self) -> None:
        latency = 0.05
        expected_text = "hello benchmark"
        fake_transcriber = FakeTranscriber(latency_s=latency, output=(expected_text, "en"))
        audio = np.zeros(int(settings.SAMPLE_RATE * settings.CHUNK_SECONDS), dtype=np.float32)
        t0 = time.perf_counter()
        text, lang = fake_transcriber.transcribe(audio)
        measured = time.perf_counter() - t0
        self.assertEqual(text, expected_text)
        self.assertEqual(lang, "en")
        self.assertGreaterEqual(measured, latency - 1e-3)

    def test_llm_benchmark_measures_latency_and_output(self) -> None:
        latency = 0.01
        suggestion = "benchmark suggestion"
        fake_llm = FakeEngine(latency_s=latency, response=suggestion)
        t0 = time.perf_counter()
        out = fake_llm.suggest("prompt", max_tokens=16, temperature=0.0)
        measured = time.perf_counter() - t0
        self.assertEqual(out, suggestion)
        self.assertGreaterEqual(measured, latency - 1e-3)

    def test_end_to_end_fake_audio_text_report_format(self) -> None:
        fake_transcriber = FakeTranscriber(latency_s=0.0, output=("fake speech", "en"))
        fake_llm = FakeEngine(latency_s=0.0, response="fake reply")
        audio = np.ones(320, dtype=np.float32)
        t0 = time.perf_counter()
        text, lang = fake_transcriber.transcribe(audio)
        suggestion = fake_llm.suggest(text, max_tokens=16, temperature=0.0)
        total = time.perf_counter() - t0
        report = {
            "text": text,
            "lang": lang,
            "suggestion": suggestion,
            "total_s": total,
        }
        self.assertEqual(report["text"], "fake speech")
        self.assertEqual(report["suggestion"], "fake reply")
        self.assertGreaterEqual(report["total_s"], 0.0)
