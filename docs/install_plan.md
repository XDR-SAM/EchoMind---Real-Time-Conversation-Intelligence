# Windows Installation Plan — Real-Time AI Meeting Copilot

This document captures the tested, Windows-safe pip install sequence for the
`real-time-ai-copilot` stack, plus fallbacks when CUDA wheels are unavailable.
No repository code changes are required; only dependency changes are noted.

## 1) Exact pip install commands

Create and use a dedicated virtual environment first:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Then install in this order so that CUDA-specific wheels are attempted first.

### Primary Windows + CUDA 12.1 path
```powershell
pip install --upgrade pip

# PyTorch / CUDA 12.1 runtime + audio
pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
pip install triton==2.3.1

# Whisper transcription via faster-whisper (CTranslate2-backed, CUDA-capable)
pip install faster-whisper==1.0.3

# LLM runtime with CUDA-offloaded layers
pip install llama-cpp-python==0.2.90 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# Audio capture on Windows
pip install soundcard==0.4.0

# Remaining pure-Python / well-supported wheels
pip install numpy==1.26.4 scipy==1.13.1
pip install PyQt6==6.6.1 PyQt6-WebKit==6.6.0
pip install pydantic==2.5.3 PyYAML==6.0.1
pip install sentence-transformers==2.7.0
pip install faiss-cpu==1.8.0
```

Notes:
- `llama-cpp-python` pulls in the prebuilt CUDA runtime from the
  `abetlen` extra index for `cu121`. If that index is temporarily down, fall
  back to the CPU wheel or the official prebuilt/GGML source path described
  in section 2.
- `soundcard` uses PortAudio; the maintainer-known Windows caveats are in
  section 4.

### CPU-only Windows fallback
If your GPU has no compatible CUDA wheel or you want to force CPU:

```powershell
pip install --upgrade pip

# CPU-only PyTorch
pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu

# Use CPU compute for Whisper
pip install faster-whisper==1.0.3

# CPU-only llama inference
pip install llama-cpp-python==0.2.90

# Audio capture
pip install soundcard==0.4.0

# Remaining pure-Python / well-supported wheels
pip install numpy==1.26.4 scipy==1.13.1
pip install PyQt6==6.6.1 PyQt6-WebKit==6.6.0
pip install pydantic==2.5.3 PyYAML==6.0.1
pip install sentence-transformers==2.7.0
pip install faiss-cpu==1.8.0
```

## 2) Fallbacks if CUDA wheels fail

### faster-whisper / CTranslate2
- `faster-whisper` depends on `ctranslate2`. On Windows, official CUDA wheels
  for `ctranslate2` are often limited by the `cuda-version` tag.
- **First fallback:** install the generic Windows wheel and run on CPU:
  ```powershell
  pip install ctranslate2
  pip install faster-whisper==1.0.3
  ```
  Then run the transcriber with `device="cpu"` and `compute_type="int8"`.
- **Second fallback:** pin a known-good `ctranslate2`/CUDA build if your
  PyTorch CUDA stack diverges, e.g.:
  ```powershell
  pip install ctranslate2==3.24.0
  pip install faster-whisper==1.0.3
  ```
  Adjust `ctranslate2` to match the fastest compatible build for your Python
  and CUDA toolkit; keep `faster-whisper` at `1.0.3` unless issues arise.

### llama-cpp-python CUDA
- **Fallback A:** CPU wheel
  ```powershell
  pip uninstall -y llama-cpp-python
  pip install llama-cpp-python==0.2.90
  ```
  Set `n_gpu_layers=0` to avoid GPU usage.
- **Fallback B:** build from source against your local CUDA toolkit.
  This requires Visual Studio Build Tools and CUDA toolkit installed.
  ```powershell
  pip uninstall -y llama-cpp-python
  set CMAKE_ARGS=-DGGML_CUDA=on
  pip install llama-cpp-python==0.2.90 --no-cache-dir --force-reinstall
  ```
  Building from source is slower and can fail if MSVC/CUDA mismatch; prefer
  the CPU wheel unless GPU offload is required.

### torch / torchaudio / triton CUDA
- If `cu121` fails due to driver mismatch or wheel absence, switch to CPU
  wheels as shown in section 1. Triton is not required for CPU inference,
  but leaving it installed rarely causes issues. Uninstall only if import
  errors occur:
  ```powershell
  pip uninstall -y triton
  ```

## 3) faster-whisper + CTranslate2 notes

- `faster-whisper==1.0.3` is a wrapper around `ctranslate2`. It does not use
  PyTorch-CUDA directly; it loads a separate CTranslate2 CUDA runtime.
- The application code (`Transcriber`) only uses `device` and `compute_type`.
  Mapping `device="cuda"` → `transcribe(..., device="cuda", compute_type="float16")`
  works only when `ctranslate2` exposes CUDA.
- If Windows wheel resolution is the blocker, the safest operational config
  is:
  ```python
  WhisperModel(model_name, device="cpu", compute_type="int8")
  ```
- Do **not** upgrade `faster-whisper` beyond `1.0.3` unless you validate
  the `VADFilter`/`vad_parameters` API remains compatible with
  `backend/transcriber.py`.

## 4) soundcard on Windows notes

- The app captures loopback audio via `soundcard.all_microphones(include_loopback=True)`.
- On Windows, loopback devices are created by the audio driver; ensure
  **Stereo Mix / What U Hear / WASAPI loopback** is enabled in Sound settings
  (Control Panel → Sound → Recording). If no loopback device appears, you
  may need to enable "Listen to this device" on your playback endpoint or
  use a driver like VB-Audio Cable.
- `soundcard` depends on PortAudio; wheels are usually bundled, but if you
  see a PortAudio-related build/install error, verify the wheel is available
  for your Python version rather than attempting a source build.
- If the app cannot find a device whose name contains `"speakers"`, either:
  - rename the active loopback device to match the substring, or
  - change `device_substr` in `AudioCapture(...)` from `"speakers"` to a
    substring present in your Windows recording device names.

## 5) Validation

After install, run a minimal import/assertion script before launching the
full app:

```powershell
python -c "import faster_whisper, llama_cpp, soundcard, torch, PyQt6; print('imports ok')"
```

If `soundcard` fails, review Windows audio endpoints manually in Sound
settings. If `faster_whisper` fails, fall back to CPU `compute_type="int8"`
per section 3.
