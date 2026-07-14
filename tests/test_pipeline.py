"""Pipeline contract tests using lightweight fake implementations."""
from __future__ import annotations

import threading
from queue import Queue
from unittest import TestCase

import numpy as np

from backend.pipeline import Pipeline


class FakeAudio:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._idx = 0

    def read(self):
        if self._idx >= len(self._chunks):
            return None
        chunk = self._chunks[self._idx]
        self._idx += 1
        return chunk

    def start(self):
        return None

    def stop(self):
        return None


class FakeTranscriber:
    def __init__(self, texts):
        self._texts = list(texts)
        self._idx = 0

    def transcribe(self, audio):
        text = self._texts[self._idx % len(self._texts)]
        self._idx += 1
        return text, "en"

    def close(self):
        return None


class FakeContextEngine:
    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0

    def search(self, query):
        resp = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return resp


class FakeLLMEngine:
    def __init__(self, suggestions):
        self._suggestions = list(suggestions)
        self._idx = 0

    def suggest(self, prompt, max_tokens=0, temperature=0.0):
        s = self._suggestions[self._idx % len(self._suggestions)]
        self._idx += 1
        return s

    def close(self):
        return None


class FakeVAD:
    def __init__(self, flags):
        self._flags = list(flags)
        self._idx = 0

    def __call__(self, chunk):
        flag = self._flags[self._idx % len(self._flags)]
        self._idx += 1
        return bool(flag)

    def reset(self):
        return None


class PipelineContractTests(TestCase):
    def _make_pipeline(self, vad_flags, texts, context_responses, llm_suggestions, max_chunks=8):
        chunks = [np.ones(320, dtype=np.float32) for _ in range(max_chunks)]
        audio = FakeAudio(chunks)
        transcriber = FakeTranscriber(texts)
        context = FakeContextEngine(context_responses)
        llm = FakeLLMEngine(llm_suggestions)
        vad = FakeVAD(vad_flags)
        ui_queue = Queue(maxsize=8)
        return Pipeline(audio, transcriber, context, llm, ui_queue, vad), ui_queue

    def test_pipeline_drains_on_stop_without_infinite_loop(self) -> None:
        pipeline, _ = self._make_pipeline(
            vad_flags=[False],
            texts=["hello"],
            context_responses=[""],
            llm_suggestions=["hi"],
            max_chunks=1,
        )
        pipeline.start()
        pipeline.stop()
        self.assertIsNotNone(pipeline._thread)
        pipeline._thread.join(timeout=2)
        self.assertFalse(pipeline._thread.is_alive())

    def test_stop_is_idempotent_when_not_started(self) -> None:
        pipeline, _ = self._make_pipeline(
            vad_flags=[True],
            texts=["hello"],
            context_responses=[""],
            llm_suggestions=["hi"],
            max_chunks=1,
        )
        pipeline.stop()

    def test_transcript_and_suggestion_dispatched_to_ui_queue(self) -> None:
        pipeline, ui_queue = self._make_pipeline(
            vad_flags=[True, False],
            texts=["hello world"],
            context_responses=["ctx1"],
            llm_suggestions=["Try saying hello back."],
            max_chunks=2,
        )
        pipeline.start()
        pipeline.stop()
        pipeline._thread.join(timeout=3)
        self.assertFalse(pipeline._thread.is_alive())
        self.assertGreaterEqual(ui_queue.qsize(), 1)
        item = ui_queue.get_nowait()
        self.assertIn("transcript", item)
        self.assertIn("suggestion", item)
        self.assertIn("lang", item)
        self.assertEqual(item["suggestion"], "Try saying hello back.")

    def test_empty_transcript_does_not_dispatch(self) -> None:
        pipeline, ui_queue = self._make_pipeline(
            vad_flags=[True],
            texts=["   "],
            context_responses=["ctx"],
            llm_suggestions=["x"],
            max_chunks=1,
        )
        pipeline.start()
        pipeline.stop()
        pipeline._thread.join(timeout=3)
        self.assertEqual(ui_queue.qsize(), 0)

    def test_non_speech_frames_skip_transcription(self) -> None:
        transcriber = FakeTranscriber(["should not matter"])
        context = FakeContextEngine(["ctx"])
        llm = FakeLLMEngine(["x"])
        audio = FakeAudio([np.zeros(320, dtype=np.float32)])
        vad = FakeVAD([False])
        ui_queue = Queue(maxsize=4)
        pipeline = Pipeline(audio, transcriber, context, llm, ui_queue, vad)
        pipeline.start()
        pipeline.stop()
        pipeline._thread.join(timeout=3)
        self.assertEqual(ui_queue.qsize(), 0)

    def test_build_prompt_format(self) -> None:
        pipeline, _ = self._make_pipeline(
            vad_flags=[False],
            texts=[],
            context_responses=[],
            llm_suggestions=[],
            max_chunks=1,
        )
        prompt = pipeline._build_prompt("hello", "memory snippet")
        self.assertIn("<s>[INST]", prompt)
        self.assertIn("<<SYS>>", prompt)
        self.assertIn("concise meeting assistant", prompt)
        self.assertIn("concise, actionable inline suggestions", prompt)
        self.assertIn("Reply suggestion:", prompt)
        self.assertIn("Transcript:", prompt)
        self.assertIn("Context:", prompt)
        self.assertIn("hello", prompt)
        self.assertIn("memory snippet", prompt)
        self.assertIn("[/INST]", prompt)
