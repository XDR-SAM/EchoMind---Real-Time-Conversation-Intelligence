# Deployment Guide

Operational reference for running, configuring, and maintaining Real-Time AI Meeting Copilot on Windows 10/11.

## Configuration reference

Edit `backend\config.py` before first run if defaults need adjustment:

| Setting | Default | Purpose |
|---|---|---|
| `MODEL_NAME` | `small` | Whisper model: `tiny`, `small`, `base`, `medium.en` |
| `CHUNK_SECONDS` | `2.0` | Audio chunk length; lower = lower latency |
| `DEVICE_NAME_SUBSTR` | `speakers` | Substring matched against Windows recording devices |
| `TRANSCRIBE_DEVICE` | `cpu` | `cpu` or `cuda` |
| `TRANSCRIBE_COMPUTE_TYPE` | `int8` | `int8` on CPU, `float16` on CUDA |
| `LLM_MODEL_PATH` | `models\llama-2-7b-chat.Q4_K_M.gguf` | GGUF model file location |
| `LLM_CONTEXT_SIZE` | `2048` | LLM context window |
| `LLM_GPU_LAYERS` | `35` | GPU offloaded layers for RTX 2060 6GB |
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `RAG_TOP_K` | `3` | Number of retrieved doc chunks |
| `MAX_TRANSCRIPT_CHARS` | `1200` | Transcript context fed to the LLM |
| `OVERLAY_OPACITY` | `0.92` | Overlay background opacity |
| `OVERLAY_WIDTH` | `520` | Overlay width in px |
| `OVERLAY_HEIGHT` | `420` | Overlay height in px |

### Environment overrides

`backend\config.py` uses `pydantic_settings` and loads values from `.env` in the repo root if present. This is the safest way to change settings without editing source.

#### Local GGUF mode

Example `.env`:

```env
LLM_BACKEND=local
TRANSCRIBE_DEVICE=cuda
TRANSCRIBE_COMPUTE_TYPE=float16
DEVICE_NAME_SUBSTR=stereo mix
LLM_GPU_LAYERS=20
LLM_MODEL_PATH=models/llama-2-7b-chat.Q4_K_M.gguf
```

#### API provider mode

Set `LLM_BACKEND=openai_compat` and point settings at your OpenAI-compatible endpoint:

```env
LLM_BACKEND=openai_compat
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
OPENAI_MODEL=nvidia-nemotron-3-nano-4b-instruct
TRANSCRIBE_DEVICE=cuda
TRANSCRIBE_COMPUTE_TYPE=float16
DEVICE_NAME_SUBSTR=stereo mix
```

In provider mode, `LLM_MODEL_PATH` and `LLM_GPU_LAYERS` are not used for inference. Audio and RAG still run locally.

## API provider validation

- Start the provider server so `$OPENAI_API_BASE/chat/completions` is reachable.
- Configure settings in `.env` with `LLM_BACKEND=openai_compat`.
- Run `python backend\main.py --benchmark`. If provider latency is too high, lower `MAX_TRANSCRIPT_CHARS` or inspect your model's hosted context window.
- Common provider errors:
  - `openai_http_error` / `openai_url_error`: verify `OPENAI_API_BASE`, port, and API key.
  ## Running on CPU vs CUDA

  ### Automatic detection

  `backend\main.py` checks for `nvidia-smi` at startup and prints compute mode in the startup report. If CUDA is unavailable, it falls back to CPU automatically.

  ### Provider mode

  - In provider mode, local GPU layers are not used for the LLM, but STT can still use CUDA with `TRANSCRIBE_DEVICE=cuda`.
  - Latency now depends on provider response time; benchmark with `python backend\main.py --benchmark`.
  - If suggestions are slower than expected, truncate context with `MAX_TRANSCRIPT_CHARS` or use a faster hosted model.

  ### CPU mode

- Use CPU if no NVIDIA GPU is present.
- Set `TRANSCRIBE_DEVICE=cpu` and `TRANSCRIBE_COMPUTE_TYPE=int8` in `.env` or `config.py`.
- Set `LLM_GPU_LAYERS=0` to keep LLM on CPU.
- Increase `CHUNK_SECONDS` slightly if latency feels tight, or drop `RAG_TOP_K` to `2`.

### CUDA mode

- CUDA 12.1 wheels are pinned in `requirements_windows.txt`.
- `TRANSCRIBE_DEVICE=cuda`, `TRANSCRIBE_COMPUTE_TYPE=float16`.
- `LLM_GPU_LAYERS` defaults to `35`, tuned for RTX 2060 6GB.
- If you hit out-of-memory, reduce `LLM_GPU_LAYERS` to `20` or smaller.

## Windows audio setup

### Enabling Stereo Mix

1. Open **Control Panel → Sound → Recording**.
2. Right-click and enable **Show Disabled Devices** and **Show Disconnected Devices**.
3. Find **Stereo Mix** (or equivalent like “What U Hear”).
4. Right-click → **Enable**.
5. Optionally **Set as Default Device** for recording.

### Matching the device name

The app finds the loopback device by substring (`DEVICE_NAME_SUBSTR`). Default is `speakers`.

If your loopback device is named `Stereo Mix (Realtek Audio)`:
- Set `DEVICE_NAME_SUBSTR=stereo mix` in `.env`.
- Restart the app.

If no loopback device appears:
- Some drivers require **Listen to this device** on the playback endpoint.
- Alternatively, use VB-Audio Cable or similar virtual audio driver.

## Tray behavior

- The overlay is wrapped by a system tray icon when available.
- **Close button** hides the overlay to tray instead of exiting.
- **Tray icon**:
  - Single-click or double-click to restore/hide overlay.
  - Right-click for **Restore**, **Pin/Unpin**, **Quit**.
- If tray is unavailable, closing the overlay exits the app.

## Pin and Unpin

- Default state is **Pinned** (`WindowStaysOnTopHint`).
- Press **Unpin** before launching full-screen apps or while screen sharing.
- Press **Pin** to restore always-on-top behavior.
- Pin state is not persisted between launches.

## Model download workflow

```powershell
python scripts\download_models.py
```

What it stores:
- `models\llama-2-7b-chat.Q4_K_M.gguf` (LLM)
- Whisper model is auto-cached by faster-whisper on first transcription

Re-run if the LLM file is missing or smaller than 10 MB.

## Docs ingestion workflow

1. Drop `.txt`, `.md`, or `.csv` files into `backend\docs_ingested\`.
2. Restart the app.
3. Startup rebuilds the FAISS index from all supported files.
4. The engine retrieves top-k chunks per query.

Notes:
- Old files removed from the directory are not removed from the index until the next restart rebuilds it.
- Non-supported formats are ignored silently.
- Encoding failures fall back to `utf-8` with errors ignored.

## Upgrade paths

### Dependency upgrades

When updating Python packages:
- Keep `faster-whisper==1.0.3` unless you validate `VADFilter` compatibility.
- Keep `llama-cpp-python==0.2.90` unless rebuilding from source with a matched CUDA toolkit.
- After changes, rerun `python backend\main.py --benchmark` to validate latency.

### Model upgrades

- Whisper: bump `MODEL_NAME` in `config.py`. Valid values: `tiny`, `small`, `base`, `medium.en`.
- LLM: replace `models\llama-2-7b-chat.Q4_K_M.gguf` with another GGUF model and update `LLM_MODEL_PATH`.
- Re-run `scripts\download_models.py` only if fetching the known default model again.

### OS upgrades

- Windows 10/11 are supported. DPI scaling may reset overlay sharpness; restart the app after changing display scaling.

## Troubleshooting matrix

| Symptom | Likely cause | Fix |
|---|---|---|
| `No audio device found` | Stereo Mix disabled or wrong device name | Enable Stereo Mix, check `DEVICE_NAME_SUBSTR` |
| No transcript appears | Loopback captures silence or VAD filters too aggressively | Verify playback audio is active; raise `CHUNK_SECONDS` |
| Whisper slow on CPU | Using `small` or larger model | Drop to `tiny` for speed, sacrifice accuracy |
| CUDA out of memory | GPU layers too high for VRAM | Set `LLM_GPU_LAYERS=20` or lower |
| Out-of-sync or blurry overlay | DPI scaling changed after launch | Restart app; set scaling to 100% if blurry persists |
| Import error for `soundcard` | Wheel missing for Python version | Use supported Python 3.10/3.11; reinstall `soundcard==0.4.0` |
| No suggestions generated | Missing or truncated LLM model | Re-run `scripts\download_models.py` |
| Tray actions do nothing | No tray available in session | Some Windows Server/core installs lack tray; overlay close quits |
| Bangla transcription weak | Model too small | Use `MODEL_NAME=small` instead of `tiny` |
| `llama-cpp-python` build fails | CUDA index down or driver mismatch | Install CPU wheel and set `LLM_GPU_LAYERS=0` |

## Performance targets

| Metric | Target (RTX 2060) | Notes |
|---|---|---|
| Audio-to-text latency | < 400 ms | Measured from chunk end |
| End-to-end suggestion latency | < 1.2 s | Speech end to overlay update |
| RAM usage | < 3.5 GB | Steady state |
| VRAM usage | < 4 GB | With 35 layers offloaded |

## Upgrade paths

### Minor updates

- Change settings in `.env` or `backend\config.py`.
- Drop or replace docs in `backend\docs_ingested\`.
- Restart the app.

### Major dependency rotation

- Update `requirements_windows.txt`.
- Reinstall into the same `.venv`.
- Benchmark with `python backend\main.py --benchmark`.
- If `faster-whisper` or `llama-cpp-python` APIs changed, update `backend\transcriber.py` and `backend\llm_engine.py` before full launch.

### Full reinstall

```powershell
cd G:\hermes-files\real-time-ai-copilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements_windows.txt
python scripts\download_models.py
python backend\main.py --benchmark
```

If CUDA fails during reinstall, use the CPU fallback block from `docs/installation.md`.
