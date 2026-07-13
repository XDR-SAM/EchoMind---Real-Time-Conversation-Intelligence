"""Static checks for backend modules: import safety, AST-level API surface, and syntax validity."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from unittest import TestCase


class StaticModuleTests(TestCase):
    module_dir = Path(__file__).resolve().parents[1] / "backend"

    def test_expected_python_modules_exist(self) -> None:
        expected = {
            "audio_capture.py",
            "config.py",
            "context_engine.py",
            "llm_engine.py",
            "main.py",
            "pipeline.py",
            "transcriber.py",
            "ui.py",
            "vad.py",
        }
        actual = {p.name for p in self.module_dir.glob("*.py")}
        missing = sorted(expected - actual)
        self.assertEqual(missing, [], f"Missing backend modules: {missing}")

    def test_no_hardcoded_pyqt_imports_outside_ui_or_main(self) -> None:
        illegal = []
        for path in self.module_dir.glob("*.py"):
            name = path.name
            if name in {"ui.py", "main.py", "__init__.py"}:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = (node.module or "").lower()
                    if "pyqt" in mod or mod.startswith("qt"):
                        illegal.append((name, node.module, node.lineno))
                        break
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "pyqt" in alias.name.lower() or alias.name.lower().startswith("qt"):
                            illegal.append((name, alias.name, node.lineno))
                            break
        self.assertEqual(illegal, [], f"Unexpected Qt/PyQt imports: {illegal}")

    def test_config_expected_settings_are_declared(self) -> None:
        text = (self.module_dir / "config.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        settings_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Settings":
                settings_class = node
                break
        self.assertIsNotNone(settings_class, "Settings class not found in config.py")
        expected_names = {
            "SAMPLE_RATE",
            "CHUNK_SECONDS",
            "MODEL_NAME",
            "LLM_MODEL_PATH",
            "LLM_CONTEXT_SIZE",
            "LLM_GPU_LAYERS",
            "RAG_EMBEDDING_MODEL",
            "RAG_TOP_K",
            "OVERLAY_WIDTH",
            "OVERLAY_HEIGHT",
        }
        declared = {
            assign.targets[0].id
            for assign in settings_class.body
            if isinstance(assign, ast.Assign) and assign.targets and isinstance(assign.targets[0], ast.Name)
        }
        self.assertTrue(
            expected_names.issubset(declared),
            f"Missing expected settings: {sorted(expected_names - declared)}",
        )

    def test_sibling_backend_files_are_syntactically_valid(self) -> None:
        failed = []
        for path in self.module_dir.glob("*.py"):
            if path.name == "ui.py":
                continue
            text = path.read_text(encoding="utf-8")
            try:
                ast.parse(text)
            except SyntaxError as exc:
                failed.append(f"{path.name}: {exc}")
        self.assertEqual(failed, [], f"Syntax errors: {failed}")
