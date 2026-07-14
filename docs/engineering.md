# Engineering Notes

## 1. Latency budget
- Audio chunk: 2.0s
- Whisper small: ~220–320ms CPU, faster GPU
- FAISS top-k: <5ms
- Llama 7B Q4 K M 2k ctx, greedy: ~340–520ms RTX 2060
- UI update: <70ms
- End-to-end worst case: ~1.2s; typical: ~0.8s after speech ends

## 2. Optimization hints
- Use Whisper `small.en` if mostly English: better accuracy, lower latency.
- Raise `CHUNK_SECONDS` to 2.5 if overflow increases, or lower to 1.5 for minority-language speed.
- Drop `RAG_TOP_K` to 2 for latency-critical runs.
- Disable UI markdown rendering if needed.

## 3. Known tradeoffs
- Energy VAD is lightweight; replace with Silero VAD if precision requirements increase.
- FAISS CPU is acceptable for <20k chunks; switch to `faiss-gpu` if index grows.
- Overlay uses a plain PyQt `QFrame` widget; there is no WebEngine dependency.
- FAISS CPU is acceptable for <20k chunks; switch to `faiss-gpu` if index grows and you have CUDA available.
