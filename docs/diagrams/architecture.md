# Architecture Diagram

> Render locally with one command:
>
> \`\`\`bash
> npx -y @mermaid-js/mermaid-cli mmdc -i docs/diagrams/architecture.md -o docs/diagrams/architecture.png
> \`\`\`

```mermaid
flowchart TD
    A[User / Meeting Audio] --> B[AudioCapture]
    B -->|queue[np.ndarray]| P[Pipeline._worker]

    subgraph Backend Launcher
        T[Transcriber\nFaster Whisper]
        C[ContextEngine\nFAISS + sentence-transformers]
        L[LLMEngine\nLlama 2 Qt GGUF]
        V[EnergyVAD]
    end

    P --> V
    P --> T
    P --> C
    P --> L

    P -->|ui_queue payload| O[OverlayWindow\nPyQt6 QFrame]

    M[main.py\nQApplication lifecycle] --> B
    M --> T
    M --> C
    M --> L
    M --> P
    M --> O

    R[Settings\ndocs_ingested/ paths] --> M
```

## Data contracts in code

- \`PipelineState\` carries: \`transcript_window\`, \`latest_lang\`, \`raw_suggestion\`, \`validated_suggestion\`, \`context_snippet\`, \`phase\`.
- Each iteration produces either a completed state or returns \`None\` on failure.
- RAG index is built lazily from flat files in \`docs_ingested/\`; topics are repeated under whisper latency in \`docs/engineering.md\`.

## Important notes

- There is no database, SQLite, or PostgreSQL in this project.
- There is no WebEngine overlay; UI is a plain PyQt \`QFrame\`.
