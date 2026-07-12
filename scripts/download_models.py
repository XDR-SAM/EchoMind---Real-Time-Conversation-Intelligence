#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path

MODELS = {
    "llm": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf",
    "whisper": "small",
}


def download_file(url: str, target: Path):
    print(f"Downloading {url} -> {target}")
    try:
        import requests

        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if chunk:
                        f.write(chunk)
        print("Saved", target)
        return
    except Exception as exc:
        print("requests failed:", exc)

    if shutil.which("curl"):
        print("Falling back to curl...")
        subprocess.check_call(["curl", "-L", url, "-o", str(target)])
        return
    if shutil.which("powershell"):
        print("Falling back to PowerShell...")
        subprocess.check_call([
            "powershell",
            "-Command",
            "Invoke-WebRequest",
            "-Uri",
            url,
            "-OutFile",
            str(target),
        ])
        return
    raise SystemExit("No downloader available. Install requests or curl.")


def main():
    root = Path(__file__).resolve().parent.parent / "backend"
    models_dir = root.parent / "models"
    models_dir.mkdir(exist_ok=True)

    # Faster-Whisper downloads models automatically.
    print(f"Whisper model: {MODELS['whisper']}. Faster-whisper will cache it.")

    llm_path = models_dir / "llama-2-7b-chat.Q4_K_M.gguf"
    if not llm_path.exists() or llm_path.stat().st_size < 10_000_000:
        download_file(MODELS["llm"], llm_path)
    else:
        print("LLM model exists:", llm_path)


if __name__ == "__main__":
    main()