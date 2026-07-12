from llama_cpp import Llama


class LLMEngine:
    def __init__(self, model_path, n_ctx=2048, n_gpu_layers=-1, n_threads=6):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads,
            verbose=False,
        )

    def suggest(self, prompt: str, max_tokens: int = 220, temperature: float = 0.2, stop=None):
        out = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or ["\nUser:", "\n\nQuestion:"],
            echo=False,
        )
        return out["choices"][0]["text"].strip()

    def close(self):
        try:
            del self.llm
        except Exception:
            pass
