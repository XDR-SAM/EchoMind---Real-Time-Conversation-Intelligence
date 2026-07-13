#!/usr/bin/env python3
"""Verification script for the Windows real-time copilot test suite.

Runs unittest-based tests under tests/ and prints a concise PASS/FAIL summary.
Exit code:
  0 if all test classes pass
  1 if any class fails or loading errors occur
  2 on unexpected script error
"""
from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path
from unittest import TestLoader, TestResult, TextTestRunner

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = PROJECT_ROOT / "tests"
sys.path.insert(0, str(PROJECT_ROOT))

TEST_CLASSES = [
    "tests.test_static.StaticModuleTests",
    "tests.test_startup_simulation.StartupSimulationTests",
    "tests.test_pipeline.PipelineContractTests",
    "tests.test_vad.VADBehaviorTests",
    "tests.test_benchmark_harness.BenchmarkTests",
]


def load_class(dotted: str):
    module_path, _, class_name = dotted.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def main() -> int:
    loader = TestLoader()
    suites = []
    missing_modules = []
    for dotted in TEST_CLASSES:
        try:
            cls = load_class(dotted)
        except Exception as exc:
            missing_modules.append((dotted, str(exc)))
            continue
        suites.append((dotted, loader.loadTestsFromTestCase(cls)))

    if missing_modules:
        print("[FAIL] Could not load test classes:")
        for dotted, exc in missing_modules:
            print(f"  - {dotted}: {exc}")
        return 1

    runner = TextTestRunner(stream=sys.stdout, verbosity=1)
    result = TestResult()
    print("=== Verification Run ===")
    print(f"Targets: {len(suites)}")
    print("-------------------------------")
    for dotted, tests in suites:
        print(f"[INFO] Running {dotted} ...")
        runner.run(tests, result)
    print("-------------------------------")
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped
    print(f"tests_run={total} passed={passed} failures={failures} errors={errors} skipped={skipped}")
    if failures or errors:
        print("[FAIL] Verification finished with failures/errors above.")
        return 1
    print("[PASS] Verification passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[FAIL] Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(2)
