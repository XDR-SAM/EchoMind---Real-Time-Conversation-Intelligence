# Usage Guide

How to launch, control, and operate EchoMind on Windows.

## First-run checklist

After installation and model download, make sure:

- [ ] `backend\models\llama-2-7b-chat.Q4_K_M.gguf` exists and is roughly 4GB
- [ ] `backend\docs_ingested\` exists
- [ ] Windows recording device matching `DEVICE_NAME_SUBSTR` is present
- [ ] Optional: `python backend\main.py --benchmark` passes

## Running the app

### Normal launch

```powershell
python backend\main.py
```

This starts the floating overlay and backend pipeline together.

### Background-first tray launch

To start minimized to tray instead:

```powershell
python scripts\run.py
```

The overlay stays hidden until you use the tray icon.

> If `scripts/tray_launcher.py` is referenced elsewhere but missing in this checkout, use `scripts/run.py` as the supported launcher.

## Controls

|| Control | Location | Action |
|---|---|---|
| Drag | Overlay body | Move window |
| Microphone | Header checkbox | Toggle mic vs system audio |
| Unpin / Pin | Bottom button | Toggle always-on-top |
| Exit | Bottom button | Quit the app |
| Tray icon | Taskbar | Single-click or double-click to restore/hide |
| Tray menu | Right-click tray icon | Restore, Pin, Quit |

## Session controls

The app tracks named recording sessions so you can organize work without restarting.

### Start / stop / name

- **Start session:** begin capturing transcript and suggestions. The session starts with an empty/default title.
- **Set session name:** change the current session title so saved records are easier to identify later.
- **Stop session:** end the active session and persist its metadata. You can start another session afterward.

### Export

Export saves the current session's transcripts and metadata to disk for later review.

Use `backend/exporter.py` from the UI or backend layer. Supported formats:

- **JSON:** structured transcripts and session metadata
- **CSV:** flattened transcript rows for spreadsheet review

Example paths you can pass to export:

```powershell
backend\exports\session.json
backend\exports\session.csv
```

> If export is not available in your build, the Export action is hidden automatically.

## Microphone vs system audio

The app defaults to system audio capture through Windows WASAPI loopback.
Check the **Microphone** checkbox to switch to mic input for testing or one-person setups.

## Windows audio setup

If the app cannot find a loopback device:

1. Open Windows Sound settings.
2. Go to the **Recording** tab.
3. Enable **Stereo Mix** or the equivalent loopback device.
4. Press **Set as default device** if required.
5. If the name doesn't match the default `DEVICE_NAME_SUBSTR`, edit `backend\config.py` to match a substring of the enabled recording device name.
6. Restart the app.

If Stereo Mix is hidden:
- right-click in the Recording tab and choose **Show Disabled Devices**, **Show Disconnected Devices**.

## CPU vs CUDA operation

- If `nvidia-smi` is present and returns a GPU, the app prefers `cuda` for the LLM and optional Whisper.
- If not, it falls back to `cpu` automatically and uses `int8` quantization.
- You can force CPU anyway by editing `backend\config.py`:
  - `TRANSCRIBE_DEVICE = "cpu"`
  - `TRANSCRIBE_COMPUTE_TYPE = "int8"`
  - `LLM_GPU_LAYERS = 0`

## Tray behavior

- Closing the overlay window hides it to the system tray instead of exiting.
- Use the tray icon to restore the overlay.
- Right-click the tray icon for **Restore**, **Pin/Unpin**, and **Quit**.
- If the system tray is unavailable, closing the overlay exits the app.

## Pin and Unpin

- **Pin**: the overlay stays on top of other windows.
- **Unpin**: lets the overlay sit behind full-screen apps. Unpin before gaming or full-screen presentation.
- The pin state is per-session; reopening the overlay starts pinned by default.

## Model download workflow

Run once before first start:

```powershell
python scripts\download_models.py
```

What gets downloaded:
- `backend\models\llama-2-7b-chat.Q4_K_M.gguf` (~4.1GB)
- Whisper `small` model on first transcription (auto-cached)

Re-run the script if the LLM file is missing or truncated.

## Docs ingestion workflow

1. Collect source files in `.txt`, `.md`, or `.csv` format.
2. Copy them into `backend\docs_ingested\`.
3. Restart the app to rebuild the FAISS index.
4. The index is rebuilt from all files in that directory on startup.

Notes:
- Rename or delete files between runs to keep the index aligned.
- Very large single files are truncated down to the usable context window.
- Non-supported formats are ignored silently.

## First-run expectations

- Startup prints a report with compute mode, model path, docs directory, and headless flag.
- Latency depends on CPU vs CUDA and model size.
- If no suggestions appear, check transcript output and model file first.
