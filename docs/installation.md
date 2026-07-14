# Installation Guide

This is the end-to-end Windows setup path for Real-Time AI Meeting Copilot.
It covers prerequisites, dependency installs, model download, and first verification.

## 1) Prerequisites

- **OS:** Windows 10 or 11 (64-bit)
- **Python:** 3.10 or 3.11
- **GPU:** NVIDIA CUDA-capable GPU recommended (GTX 1660 or better for comfortable latency)
- **RAM:** 16GB minimum, 32GB recommended
- **Audio:** Windows WASAPI loopback-capable audio driver

### Audio prerequisite note

By default, the app captures system audio via a loopback recording device.
On most Windows installs this appears as **Stereo Mix**.
If you don’t see it in recording devices, enable it in:
> Control Panel → Sound → Recording tab → right-click → Show Disabled Devices → enable **Stereo Mix**.

## 2) Clone the repository

Clone to a path you can write to, such as `G:\hermes-files\real-time-ai-copilot`, then open a terminal in that folder.

```powershell
cd G:\hermes-files\real-time-ai-copilot
```

## 3) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks scripts, run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 4) Install dependencies

Use the Windows-optimized requirements file:

```powershell
python -m pip install --upgrade pip
pip install -r requirements_windows.txt
```

If some CUDA wheels fail, see the CPU fallback below and `docs/install_plan.md`.

### CPU-only fallback

If you hit CUDA wheel issues or don’t have an NVIDIA GPU:

```powershell
pip install --upgrade pip
pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
pip install ctranslate2
pip install faster-whisper==1.0.3
pip install llama-cpp-python==0.2.90
pip install soundcard==0.4.0
pip install numpy==1.26.4 scipy==1.13.1
pip install PyQt6==6.6.1 PyQt6-WebKit==6.6.0
pip install pydantic==2.5.3 PyYAML==6.0.1
pip install sentence-transformers==2.7.0
pip install faiss-cpu==1.8.0
```

## 5) Verify imports

Quick health check before loading models:

```powershell
python -c "import faster_whisper, llama_cpp, soundcard, torch, PyQt6; print('imports ok')"
```

If `soundcard` fails, review your Windows recording devices and Stereo Mix status.

## 6) Download models

The app needs two model categories:

1. **LLM:** Llama-2-7B-Chat GGUF
2. **Whisper:** faster-whisper model (auto-cached)

Download the LLM with:

```powershell
python scripts\download_models.py
```

This places `models\llama-2-7b-chat.Q4_K_M.gguf` in the repo.

Whisper’s `small` model downloads automatically on first run (~500MB).

## 7) Add context documents

Place `.txt`, `.md`, or `.csv` files into:

```text
G:\hermes-files\real-time-ai-copilot\backend\docs_ingested\
```

The app indexes these into a local FAISS store at startup.
If the directory does not exist, create it before adding files.

## 8) First run smoke test

Lightweight startup check without the full GUI:

```powershell
python backend\main.py --benchmark
```

Expected outcome:
- A startup report printing compute mode (`CUDA` or `CPU`)
- LLM model path and size
- Benchmark latencies for STT, RAG, and LLM

If the model file is missing, the launcher exits cleanly with a hint to run `scripts\download_models.py`.

## What’s next

- See **docs/usage.md** for first-run behavior, microphone/system audio switching, tray behavior, and controls.
- See **docs/deployment.md** for configuration reference, upgrade paths, and troubleshooting.
