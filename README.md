# Real-Time AI Meeting Copilot

Production-ready Windows desktop application that listens to system audio, transcribes speech with automatic Bangla/English/mixed-language support, retrieves context from uploaded documents, and displays AI-generated reply suggestions in a lightweight floating overlay.

## System Architecture

```
WASAPI Loopback System Audio
           ↓
      EnergyVAD Filter
           ↓
     2s Rolling Chunk
           ↓
    Faster-Whisper small → text + language
           ↓
   Rolling Transcript Buffer
           ↓
   Sentence-Transformers → FAISS Query
           ↓
   Llama-2-7B-Chat Q4 GPU
           ↓
   PyQt6 Always-On-Top Overlay
```

## Requirements

- **OS:** Windows 10/11 64-bit
- **GPU:** NVIDIA CUDA-capable GPU
  - Minimum: GeForce GTX 1660
  - Recommended: RTX 2060 or better
- **RAM:** 16GB minimum, 32GB recommended
- **Python:** 3.10–3.11

## Installation

### 1. Clone and Install Dependencies

```bash
cd G:\hermes-files\real-time-ai-copilot
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Note on `llama-cpp-python`**: The requirements file points to a CUDA 12.1 wheel.
> If you hit build issues, instead install the CPU fallback first:
> `pip install llama-cpp-python`
> Then track the repo wheel manually if needed.

### 2. Download Models

```bash
python scripts\download_models.py
```

Downloaded files:
- `models/llama-2-7b-chat.Q4_K_M.gguf` (~4.1GB)
- Whisper small model (~500MB, auto-cached by faster-whisper)

### 3. Add Context Documents

Drop `.txt`, `.md`, or `.csv` files into:
```
G:\hermes-files\real-time-ai-copilot\backend\docs_ingested\
```
The app builds a FAISS index from these at startup.

## Usage

```bash
# Run the floating overlay copilot
python backend\main.py
```

Controls:
- **Drag** the title bar to move the overlay.
- **Microphone checkbox** switches to mic input for testing.
- **Unpin/Exit** buttons on the bottom.

## Configuration

Edit `backend\config.py` before running:

```python
MODEL_NAME: str = "small"             # "tiny", "small", "base", "medium.en"
CHUNK_SECONDS: float = 2.0            # Lower = lower latency, higher = more reliable
DEVICE_NAME_SUBSTR: str = "speakers"  # Windows WASAPI loopback source
VAD_AGGRESSIVENESS: int = 2           # 0-3
RAG_TOP_K: int = 3                    # docs retrieved per chunk
MAX_TRANSCRIPT_CHARS: int = 1200      # context window fed to the LLM
```

## Project Structure

```
real-time-ai-copilot/
├── backend/
│   ├── __init__.py
│   ├── audio_capture.py     # WASAPI loopback via soundcard
│   ├── backend.config.py    # typed config, env loading
│   ├── backend.context_engine.py  # Sentence-Transformers + FAISS
│   ├── backend.llm_engine.py      # llama-cpp-python wrapper
│   ├── backend.main.py            # application entrypoint
│   ├── backend.pipeline.py        # async inference pipeline
│   ├── backend.transcriber.py     # faster-whisper wrapper
│   ├── backend.ui.py              # PyQt6 floating overlay
│   └── backend.vad.py             # lightweight energy-based VAD
├── scripts/
│   ├── download_models.py
│   └── run.py
├── docs/
│   └── engineering.md
├── requirements.txt
└── README.md
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| **No audio device found** | Open Windows Sound Settings → Recording → enable `Stereo Mix`. Then set `DEVICE_NAME_SUBSTR`. |
| **CUDA out of memory** | Set `LLM_GPU_LAYERS` to `20` in `config.py`, or disable GPU inference temporarily. |
| **Whisper slow on CPU** | Set `MODEL_NAME="tiny"` for fastest inference. |
| **Poor Bangla transcription** | Use `small` model instead of `tiny`; Bangla improves meaningfully at small+. |
| **No suggestions generated** | Ensure `models/llama-2-7b-chat.Q4_K_M.gguf` is fully downloaded. |

## Performance Targets

| Metric | Target (RTX 2060) |
|---|---|
| Audio-to-text latency | < 400 ms |
| End-to-end suggestion latency | < 1.2 s |
| RAM usage | < 3.5 GB |
| VRAM usage | < 4 GB |

## License

Private / Commercial – modify freely for production use.
