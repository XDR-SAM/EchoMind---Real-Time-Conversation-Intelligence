"""
llm_engine.py
Suggested prompt construction optimized for:
- Model: llama-2-7b-chat
- Quant: Q4_K_M
- Context: 2k tokens max
- Hardware: RTX 2060 6GB
- Behavior: inline suggestions only; never speak

Place transcript context first, retrieved docs second, inference input last.
Keep total prompt under ~1800 tokens to reserve generation budget.
"""

SYSTEM_PROMPT = """You are a silent copilot. Output only inline text suggestions.
Rules:
- Do not speak.
- Follow user language exactly: English, Bangla, or mixed.
- Language normalization: mirror the language of the current sentence.
  Prefer English if sentence is English-dominant, Bangla if Bangla-dominant.
- Keep suggestions concise and ready to insert.
"""

TRANSCRIPT_CTX_HEADER = """Transcript context:
"""

RETRIEVED_DOCS_HEADER = """Retrieved docs:
"""

CURRENT_INPUT_HEADER = """Current transcription:
"""

INFERENCE_TEMPLATE = """{system_prompt}{transcript_ctx}{retrieved_docs}{current_input}"""


def build_suggest_prompt(transcript: str, docs: str, current: str, max_doc_tokens: int = 200) -> str:
    """Assemble a compact prompt for low-latency completion."""
    doc_block = (RETRIEVED_DOCS_HEADER + docs.strip())[:max_doc_tokens]
    return INFERENCE_TEMPLATE.format(
        system_prompt=SYSTEM_PROMPT,
        transcript_ctx=TRANSCRIPT_CTX_HEADER + transcript.strip() + "\n",
        retrieved_docs=doc_block + "\n",
        current_input=CURRENT_INPUT_HEADER + current.strip(),
    )
