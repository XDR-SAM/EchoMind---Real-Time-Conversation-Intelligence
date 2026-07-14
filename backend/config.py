from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    MODEL_DIR: Path = BASE_DIR / "models"
    DOCS_DIR: Path = BASE_DIR / "docs_ingested"

    # Audio
    SAMPLE_RATE: int = 16000
    CHUNK_SECONDS: float = 2.0
    VAD_AGGRESSIVENESS: int = 2
    DEVICE_NAME_SUBSTR: str = "speakers"

    # Runtime
    MODEL_NAME: str = "small"  # "tiny", "small", "base", "medium.en"
    TRANSCRIBE_DEVICE: str = "cpu"
    TRANSCRIBE_COMPUTE_TYPE: str = "int8"
    LLM_BACKEND: str = "local"  # "local" or "openai_compat"
    LLM_MODEL_PATH: str = str(MODEL_DIR / "NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf")
    LLM_CONTEXT_SIZE: int = 2048
    LLM_GPU_LAYERS: int = 35
    OPENAI_API_BASE: str = "http://localhost:1234/v1"
    OPENAI_API_KEY: str = "lm-studio"
    OPENAI_MODEL: str = "nvidia-nemotron-3-nano-4b-instruct"
    RAG_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 3
    MAX_TRANSCRIPT_CHARS: int = 1200

    # Overlay
    OVERLAY_OPACITY: float = 0.92
    OVERLAY_WIDTH: int = 520
    OVERLAY_HEIGHT: int = 420

    class Config:
        env_file = BASE_DIR / ".env"


settings = Settings()
settings.MODEL_DIR.mkdir(exist_ok=True)
settings.DOCS_DIR.mkdir(exist_ok=True)


def compute_for_stt() -> tuple[str, str]:
    """Return device/compute_type for Faster-Whisper based on Settings."""
    device = settings.TRANSCRIBE_DEVICE
    if device == "cuda":
        return "cuda", "float16"
    return "cpu", settings.TRANSCRIBE_COMPUTE_TYPE
