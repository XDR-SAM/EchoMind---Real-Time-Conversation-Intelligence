# Installation Guide

This is the end-to-end Windows setup path for EchoMind.
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
If you don't see it in recording devices, enable it in:
> Control Panel → Sound → Recording tab → right-click → Show Disabled Devices → enable **Stereo Mix**.

## 2) Clone the repository

Clone to a path you can write to, then open a terminal in that folder.

```powershell
git clone https://github.com/XDR-SAM/EchoMind---Real-Time-Conversation-Intelligence.git
cd real-time-ai-copilot
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

### CUDA-capable GPU

Use `requirements_windows.txt`, which points to the CUDA 12.1 wheel index for `llama-cpp-python` and the CUDA PyTorch index:

```powershell
python -m pip install --upgrade pip
pip install -r requirements_windows.txt
```

The file includes:

- PyTorch / torchaudio / triton from `https://download.pytorch.org/whl/cu121`
- `llama-cpp-python` CUDA 12.1 wheel via `https://abetlen.github.io/llama-cpp-python/whl/cu121`

If the `llama-cpp-python` CUDA wheel is unavailable for your Python version, replace it with the CPU wheel before install:

```powershell
pip install llama-cpp-python==0.2.90
```

### API provider mode (no local LLM download)

If you run against an OpenAI-compatible API instead of a local GGUF model, you still need STT and backend dependencies, and `.env` must provide the endpoint auth:

```powershell
python -m pip install --upgrade pip
pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper==1.0.3
pip install soundcard==0.4.0
pip install numpy==1.26.4 scipy==1.13.1
pip install PyQt6==6.6.1 PyQt6-WebKit==6.6.0
pip install pydantic==2.5.3 PyYAML==6.0.1
pip install sentence-transformers==2.7.0
pip install faiss-cpu==1.8.0
```

Do **not** install `llama-cpp-python` in this mode. Use `requirements_windows.txt` only if you intend to run local inference.

> **Model download note:** in API provider mode, skip the local model download step in Section 6. Configure `.env` instead.

## 5) Verify imports

Quick health check before loading models/provider:

```powershell
python -c "import faster_whisper, soundcard, torch, PyQt6; print('imports ok')"
```

If `soundcard` fails, review your Windows recording devices and Stereo Mix status.

## 6) Configure provider mode

Create `.env` in the repo root with provider settings, and skip the local model download step:

```env
LLM_BACKEND=openai_compat
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
OPENAI_MODEL=nvidia-nemotron-3-nano-4b-instruct
TRANSCRIBE_DEVICE=cuda
TRANSCRIBE_COMPUTE_TYPE=float16
```

This sends LLM requests to an OpenAI-compatible backend such as LM Studio, Ollama, or a hosted API. `OPENAI_API_BASE` and `OPENAI_MODEL` are the main knobs; update them to match your provider.

## 7) Add context documents

Place `.txt`, `.md`, or `.csv` files into:

```text
backend\docs_ingested\
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
- Provider mode vs local model mode
- Benchmark latencies for STT, RAG, and LLM

## What's next

- See **docs/usage.md** for first-run behavior, controls, session naming, export, tray behavior, and provider-mode operation.
- See **docs/deployment.md** for configuration reference, provider setup, CPU/CUDA tuning, upgrade paths, and troubleshooting.
