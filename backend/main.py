from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

import numpy as np

from backend.audio_capture import AudioCapture
from backend.config import settings
from backend.context_engine import ContextEngine
from backend.llm_engine import LLMEngine
from backend.transcriber import Transcriber
from backend.vad import EnergyVAD

LOG = logging.getLogger("main")
_MIN_MODEL_SIZE = 10_000_000  # 10 MB


@dataclass
class Metrics:
    start_time: float = field(default_factory=time.perf_counter)
    audio_chunks: int = 0
    stt_calls: int = 0
    llm_calls: int = 0
    rag_calls: int = 0
    errors: int = 0
    ui_dispatched: int = 0

    def elapsed_s(self) -> float:
        return time.perf_counter() - self.start_time

    def report(self) -> str:
        t = self.elapsed_s()
        return (
            f"uptime={t:.2f}s"
            f" audio_chunks={self.audio_chunks}"
            f" stt_calls={self.stt_calls}"
            f" llm_calls={self.llm_calls}"
            f" rag_calls={self.rag_calls}"
            f" errors={self.errors}"
            f" ui_dispatched={self.ui_dispatched}"
        )


def _detect_cuda() -> tuple[bool, str]:
    """Detect whether CUDA/Nvidia hardware is available."""
    if shutil.which("nvidia-smi") is None:
        return False, "nvidia-smi not found; assuming CPU compute."
    try:
        res = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return False, "nvidia-smi returned no devices; falling back to CPU."
        gpus = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        detail = gpus[0] if gpus else "GPU present"
        return True, f"CUDA detected: {detail}"
    except Exception as exc:
        LOG.debug("CUDA detection failed: %s", exc)
        return False, f"nvidia-smi check failed: {exc}; falling back to CPU."


def _check_model_files() -> tuple[bool, Optional[Path], str]:
    """Verify LLM model file exists with reasonable size."""
    model_path = Path(settings.LLM_MODEL_PATH)
    if not model_path.is_file():
        return False, model_path, f"missing model file: {model_path}"
    try:
        size = model_path.stat().st_size
    except OSError as exc:
        return False, model_path, f"unable to stat model file: {exc}"
    if size < _MIN_MODEL_SIZE:
        return False, model_path, f"model file too small ({size} bytes): {model_path}"
    return True, model_path, f"model ok: {model_path} ({size / 1_048_576:.1f} MB)"


def _print_startup_report(
    cuda: bool,
    cuda_note: str,
    model_ok: bool,
    model_note: str,
    headless: bool,
    args: list[str],
) -> None:
    print("=== Startup Report ===")
    print(f"argv={' '.join(args)!r}")
    print(f"compute={'CUDA' if cuda else 'CPU'}: {cuda_note}")
    print(f"llm_model={model_note}")
    status = "(exists)" if settings.DOCS_DIR.exists() else "(missing)"
    print(f"docs_dir={settings.DOCS_DIR} {status}")
    print(f"headless={headless}")
    print("======================")


def _run_benchmark(cuda: bool) -> int:
    """Headless benchmark of STT, RAG, and LLM components."""
    LOG.info("Running headless benchmark")
    compute = "cuda" if cuda else "cpu"
    compute_type = "float16" if cuda else "int8"
    model_ok, model_path, model_note = _check_model_files()
    print(model_note)
    if not model_ok:
        return 1

    print(f"device={compute} transcriber_compute={compute_type}")

    # STT benchmark
    try:
        t0 = time.perf_counter()
        stt = Transcriber(
            model_name=settings.MODEL_NAME,
            device=compute,
            compute_type=compute_type,
        )
        audio = np.zeros(int(settings.SAMPLE_RATE * settings.CHUNK_SECONDS), dtype=np.float32)
        text, lang = stt.transcribe(audio)
        stt.close()
        stt_s = time.perf_counter() - t0
        print(f"stt_latency={stt_s:.3f}s lang={lang!r} text={text!r}")
    except Exception as exc:
        LOG.error("STT benchmark failed", exc_info=True)
        print(f"stt_latency=FAILED:{exc}")
        return 1

    # RAG benchmark
    try:
        t0 = time.perf_counter()
        ctx = ContextEngine(
            embedding_model=settings.RAG_EMBEDDING_MODEL,
            docs_dir=settings.DOCS_DIR,
            top_k=settings.RAG_TOP_K,
        )
        hits = ctx.search("benchmark sample query")
        ctx_s = time.perf_counter() - t0
        count = len(hits.splitlines()) if hits else 0
        print(f"rag_latency={ctx_s:.3f}s hits={count}")
    except Exception as exc:
        LOG.error("RAG benchmark failed", exc_info=True)
        print(f"rag_latency=FAILED:{exc}")
        return 1

    # LLM benchmark
    try:
        t0 = time.perf_counter()
        llm = LLMEngine(
            model_path=str(model_path),
            n_ctx=settings.LLM_CONTEXT_SIZE,
            n_gpu_layers=settings.LLM_GPU_LAYERS,
        )
        suggestion = llm.suggest_structured(
            transcript="Hello.",
            max_tokens=16,
            temperature=0.0,
        )
        llm.close()
        llm_s = time.perf_counter() - t0
        print(f"llm_latency={llm_s:.3f}s suggestion={suggestion.text!r}")
    except Exception as exc:
        LOG.error("LLM benchmark failed", exc_info=True)
        print(f"llm_latency=FAILED:{exc}")
        return 1

    print("benchmark complete")
    return 0


def _shutdown(
    app, pipeline, audio, transcriber, llm_engine, window, metrics: Metrics
) -> None:
    """Import-safe shutdown sequence."""
    report = metrics.report()
    LOG.info("Shutdown metrics: %s", report)
    print(f"[metrics] {report}")
    for cleanup in (
        getattr(pipeline, "stop", None),
        getattr(audio, "stop", None),
        getattr(transcriber, "close", None),
        getattr(llm_engine, "close", None),
        getattr(window, "close", None),
    ):
        try:
            if cleanup is not None:
                cleanup()
        except Exception as exc:
            LOG.debug("Shutdown step failed: %s", exc)
    try:
        if app is not None:
            app.quit()
    except Exception:
        pass


def main(argv: Optional[list[str]] = None) -> int:
    """Production-ready launcher. Returns an OS exit code (int)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = list(sys.argv[1:] if argv is None else argv)

    cuda, cuda_note = _detect_cuda()
    model_ok, model_path, model_note = _check_model_files()
    headless = "--benchmark" in args

    _print_startup_report(cuda, cuda_note, model_ok, model_note, headless, args)

    if headless:
        return _run_benchmark(cuda)

    if not model_ok:
        print(f"Fatal: {model_note}")
        print("Hint: run scripts/download_models.py to fetch the LLM model.")
        return 1

    compute = "cuda" if cuda else "cpu"
    compute_type = "float16" if cuda else "int8"

    # Late Qt imports so benchmark mode never touches QApplication.
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    ui_queue: Queue = Queue(maxsize=12)

    try:
        from backend.ui import OverlayWindow

        window = OverlayWindow(ui_queue)
        window.show()
    except Exception as exc:
        print(f"Fatal: UI initialization failed: {exc}")
        try:
            app.quit()
        except Exception:
            pass
        return 1

    metrics = Metrics()

    try:
        audio = AudioCapture(
            sample_rate=settings.SAMPLE_RATE,
            chunk_seconds=settings.CHUNK_SECONDS,
            device_substr=settings.DEVICE_NAME_SUBSTR,
        )
        transcriber = Transcriber(
            model_name=settings.MODEL_NAME,
            device=compute,
            compute_type=compute_type,
        )
        context_engine = ContextEngine(
            embedding_model=settings.RAG_EMBEDDING_MODEL,
            docs_dir=settings.DOCS_DIR,
            top_k=settings.RAG_TOP_K,
        )
        llm_engine = LLMEngine(
            model_path=str(model_path),
            n_ctx=settings.LLM_CONTEXT_SIZE,
            n_gpu_layers=settings.LLM_GPU_LAYERS,
        )
    except Exception as exc:
        LOG.error("Backend initialization failed: %s", exc, exc_info=True)
        print(f"Fatal: Backend initialization failed: {exc}")
        try:
            app.quit()
        except Exception:
            pass
        return 1

    from backend.pipeline import Pipeline

    pipeline = Pipeline(
        audio, transcriber, context_engine, llm_engine, ui_queue, EnergyVAD()
    )

    # Wrap the pipeline worker to collect metrics without modifying pipeline.py.
    original_worker: Callable[[], None] = pipeline._worker  # type: ignore[attr-defined]

    def instrumented_worker() -> None:
        try:
            while not pipeline._stop.is_set():  # type: ignore[attr-defined]
                chunk = audio.read()
                if chunk is None:
                    time.sleep(0.03)
                    continue
                metrics.audio_chunks += 1
                if not bool(pipeline.vad(chunk)):  # type: ignore[attr-defined]
                    continue
                try:
                    text, lang = transcriber.transcribe(chunk)
                    metrics.stt_calls += 1
                except Exception as exc:
                    LOG.debug("STT failed: %s", exc)
                    metrics.errors += 1
                    continue
                text = (text or "").strip()
                if not text:
                    continue
                pipeline.latest_lang = lang or pipeline.latest_lang  # type: ignore[attr-defined]
                pipeline.transcript_buffer.append(text)  # type: ignore[attr-defined]
                window_text = " ".join(pipeline.transcript_buffer[-12:])[-1500:]  # type: ignore[attr-defined]
                try:
                    context_text = context_engine.search(window_text)
                    metrics.rag_calls += 1
                except Exception as exc:
                    LOG.debug("RAG search failed: %s", exc)
                    context_text = ""
                    metrics.errors += 1
                prompt = pipeline._build_prompt(window_text, context_text)  # type: ignore[attr-defined]
                try:
                    suggestion = llm_engine.suggest(prompt, max_tokens=220, temperature=0.15)
                    metrics.llm_calls += 1
                except Exception as exc:
                    LOG.debug("LLM suggest failed: %s", exc)
                    suggestion = ""
                    metrics.errors += 1
                try:
                    ui_queue.put_nowait(
                        {
                            "transcript": window_text,
                            "suggestion": suggestion,
                            "lang": pipeline.latest_lang,  # type: ignore[attr-defined]
                        }
                    )
                    metrics.ui_dispatched += 1
                except Exception as exc:
                    LOG.debug("UI dispatch failed: %s", exc)
        finally:
            pipeline._stop.set()  # type: ignore[attr-defined]

    pipeline._worker = instrumented_worker  # type: ignore[attr-defined]
    pipeline.start()

    def shutdown() -> None:
        _shutdown(app, pipeline, audio, transcriber, llm_engine, window, metrics)

    import atexit

    atexit.register(shutdown)

    try:
        exit_code = app.exec()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        try:
            shutdown()
        except Exception:
            pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
