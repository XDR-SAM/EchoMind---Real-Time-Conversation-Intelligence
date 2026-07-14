# Docker development / CI image for EchoMind.
#
# This container gives you a clean, reproducible Linux environment for:
# - headless benchmarking
# - running unit tests
# - validating imports and config parsing
#
# It does NOT provide a Windows desktop GUI or WASAPI loopback audio.
# For the full local experience, run natively on Windows 10/11.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# System deps needed by some wheels / runtime checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY requirements.txt requirements_windows.txt* ./

# CPU-only install suitable for Linux containers. CUDA path is ignored here.
RUN python -m pip install --upgrade pip \
    && pip install \
        faster-whisper==1.0.3 \
        soundcard==0.4.0 \
        numpy==1.26.4 \
        scipy==1.13.1 \
        PyQt6==6.6.1 \
        pydantic==2.5.3 \
        PyYAML==6.0.1 \
        sentence-transformers==2.7.0 \
        faiss-cpu==1.8.0 \
        llama-cpp-python==0.2.90

# Copy source
COPY . .

# Default to an interactive shell; override with a command like:
#   docker compose run --rm echomind python -m unittest discover -s tests
CMD ["bash"]
