"""Provider-mode smoke tests for OpenAI-compatible LLM backend."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from unittest import TestCase
from unittest import mock


def _inject_settings(**overrides):
    defaults = dict(
        SAMPLE_RATE=16000,
        CHUNK_SECONDS=2.0,
        MODEL_NAME="base",
        MODEL_DIR=Path("models"),
        DOCS_DIR=Path("docs_ingested"),
        LLM_MODEL_PATH="NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
        LLM_CONTEXT_SIZE=2048,
        LLM_GPU_LAYERS=35,
        RAG_EMBEDDING_MODEL="all-MiniLM-L6-v2",
        RAG_TOP_K=3,
        MAX_TRANSCRIPT_CHARS=1200,
        OVERLAY_OPACITY=0.92,
        OVERLAY_WIDTH=520,
        OVERLAY_HEIGHT=420,
        DEVICE_NAME_SUBSTR="speakers",
        LLM_BACKEND="openai_compat",
        OPENAI_API_BASE="http://localhost:1234/v1",
        OPENAI_API_KEY="redacted-test-key",
        OPENAI_MODEL="provider-model-id",
    )
    defaults.update(overrides)
    fake_mod = type(sys)("backend.config")
    fake_mod.settings = type("settings", (), defaults)()
    sys.modules["backend.config"] = fake_mod


class ProviderOpenAICompatTests(TestCase):
    def setUp(self):
        self._prev = sys.modules.get("backend.config")
        _inject_settings()

    def tearDown(self):
        if self._prev is not None:
            sys.modules["backend.config"] = self._prev
        else:
            sys.modules.pop("backend.config", None)

    def _make_engine(self):
        from backend.llm_engine import LLMEngine

        return LLMEngine(
            model_path="NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
            n_ctx=2048,
            n_gpu_layers=35,
        )

    def _fake_openai_response(self, content="Hello from provider"):
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1699000000,
            "model": "provider-model-id",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    def test_suggest_structured_returns_llm_suggestion(self):
        engine = self._make_engine()
        fake_response = self._fake_openai_response("Test suggestion")

        with mock.patch("backend.llm_engine.urlopen") as mock_urlopen:
            fake_resp = mock.Mock()
            fake_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
            fake_resp.__enter__ = mock.Mock(return_value=fake_resp)
            fake_resp.__exit__ = mock.Mock(return_value=False)
            mock_urlopen.return_value = fake_resp

            suggestion = engine.suggest_structured(transcript="Hello.", current="Hi")

        self.assertIsInstance(suggestion.text, str)
        self.assertIsInstance(suggestion.language, str)
        self.assertIsInstance(suggestion.token_count, int)
        self.assertIsInstance(suggestion.source, str)
        self.assertEqual(suggestion.source, "llm")
        self.assertIn("Test suggestion", suggestion.text)

    def test_suggest_structured_does_not_load_llama_model(self):
        engine = self._make_engine()
        self.assertEqual(engine._backend, "openai_compat")
        self.assertIsNone(engine._model)

    def test_openai_chat_uses_correct_api_base_and_path(self):
        engine = self._make_engine()
        fake_response = self._fake_openai_response("ok")

        with mock.patch("backend.llm_engine.urlopen") as mock_urlopen:
            fake_resp = mock.Mock()
            fake_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
            fake_resp.__enter__ = mock.Mock(return_value=fake_resp)
            fake_resp.__exit__ = mock.Mock(return_value=False)
            mock_urlopen.return_value = fake_resp

            result = engine._openai_chat("Say ok")

        self.assertEqual(result, "ok")
        called_request = mock_urlopen.call_args[0][0]
        self.assertIn("/chat/completions", str(called_request.full_url))
        self.assertEqual(called_request.get_method(), "POST")
        headers = dict(called_request.header_items())
        self.assertIn("Authorization", headers)
        self.assertIn("Bearer", headers["Authorization"])

    def test_openai_chat_payload_shape(self):
        engine = self._make_engine()
        fake_response = self._fake_openai_response("x")

        with mock.patch("backend.llm_engine.urlopen") as mock_urlopen:
            fake_resp = mock.Mock()
            fake_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
            fake_resp.__enter__ = mock.Mock(return_value=fake_resp)
            fake_resp.__exit__ = mock.Mock(return_value=False)
            mock_urlopen.return_value = fake_resp

            engine._openai_chat("prompt", generation_kwargs={"temperature": 0.5})

        called_request = mock_urlopen.call_args[0][0]
        payload = json.loads(called_request.data.decode("utf-8"))
        self.assertIn("model", payload)
        self.assertEqual(payload["model"], "provider-model-id")
        self.assertIn("messages", payload)
        self.assertEqual(payload["messages"], [{"role": "user", "content": "prompt"}])
        self.assertEqual(payload["temperature"], 0.5)

    def test_suggest_action_items_validates_json_array_shape(self):
        engine = self._make_engine()
        fake_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                {"text": "Review PR", "owner": "Alice", "due": "Fri"},
                                {"text": "Deploy", "owner": "", "due": ""},
                            ]
                        )
                    }
                }
            ],
            "usage": {},
        }

        with mock.patch("backend.llm_engine.urlopen") as mock_urlopen:
            fake_resp = mock.Mock()
            fake_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
            fake_resp.__enter__ = mock.Mock(return_value=fake_resp)
            fake_resp.__exit__ = mock.Mock(return_value=False)
            mock_urlopen.return_value = fake_resp

            items = engine.suggest_action_items("Alice will review PR. Bob will deploy.")

        self.assertEqual(len(items), 2)
        for item in items:
            self.assertIsInstance(item.text, str)
            self.assertTrue(item.text)
            self.assertIn(item.owner, ("Alice", None))
            self.assertIn(item.due, ("Fri", None))
            self.assertGreaterEqual(item.confidence, 0.0)
            self.assertLessEqual(item.confidence, 1.0)

    def test_suggest_action_items_returns_empty_on_bad_json(self):
        engine = self._make_engine()
        fake_response = {"choices": [{"message": {"content": "Not valid JSON here"}}], "usage": {}}

        with mock.patch("backend.llm_engine.urlopen") as mock_urlopen:
            fake_resp = mock.Mock()
            fake_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
            fake_resp.__enter__ = mock.Mock(return_value=fake_resp)
            fake_resp.__exit__ = mock.Mock(return_value=False)
            mock_urlopen.return_value = fake_resp

            items = engine.suggest_action_items("Some discussion")

        self.assertEqual(items, [])

    def test_suggest_structured_fallback_on_http_error(self):
        engine = self._make_engine()

        with mock.patch(
            "backend.llm_engine.urlopen", side_effect=Exception("boom")
        ):
            suggestion = engine.suggest_structured(transcript="x", current="y")

        self.assertEqual(suggestion.source, "fallback")
        self.assertEqual(suggestion.text, "")

    def test_openai_chat_returns_empty_on_empty_choices(self):
        engine = self._make_engine()
        fake_response = {"choices": []}

        with mock.patch("backend.llm_engine.urlopen") as mock_urlopen:
            fake_resp = mock.Mock()
            fake_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
            fake_resp.__enter__ = mock.Mock(return_value=fake_resp)
            fake_resp.__exit__ = mock.Mock(return_value=False)
            mock_urlopen.return_value = fake_resp

            result = engine._openai_chat("x")

        self.assertEqual(result, "")
