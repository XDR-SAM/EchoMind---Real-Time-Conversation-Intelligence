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

### CPU-only fallback

If you don't have an NVIDIA GPU or CUDA wheels fail:

```powershell
python -m pip install --upgrade pip
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

> **Python version note:** use Python 3.10 or 3.11. Some CUDA wheels are less reliable on 3.12+ for this stack.

## 5) Verify imports

Quick health check before loading models:

```powershell
python -c "import faster_whisper, llama_cpp, soundcard, torch, PyQt6; print('imports ok')"
```

If `soundcard` fails, review your Windows recording devices and Stereo Mix status.

## 6) Download models

The app needs two model categories:

1. **LLM:** `llama-2-7b-chat.Q4_K_M.gguf`
2. **Whisper:** `small` model via `faster-whisper` (auto-cached)

Download with:

```powershell
python scripts\download_models.py
```

This saves the GGUF file to:

- `backend\models\llama-2-7b-chat.Q4_K_M.gguf`

You can also fetch the GGUF directly:

```powershell
powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf' -OutFile 'backend\models\llama-2-7b-chat.Q4_K_M.gguf'"
```

Or with `curl`:

```powershell
curl -L "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf" -o backend\models\llama-2-7b-chat.Q4_K_M.gguf
```

Whisper's `small` model downloads automatically on first run (~500MB) into the Hugging Face cache under `%USERPROFILE%\.cache\huggingface\hub\`.

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
- LLM model path and size
- Benchmark latencies for STT, RAG, and LLM

If the model file is missing, the launcher exits cleanly with a hint to run `scripts\download_models.py`.

## What's next

- See **docs/usage.md** for first-run behavior, controls, session naming, export, and tray behavior.
- See **docs/deployment.md** for configuration reference, upgrade paths, and troubleshooting.
