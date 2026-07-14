# Conceptual Data-Flow Diagram

> **Status:** Conceptual / optional.
> There is no database, SQLite, PostgreSQL, or ORM in this project.
> This diagram documents in-memory data-flow artifacts created by the pipeline,
> not persistent tables or rows.

> Render locally with one command:
>
> \`\`\`bash
> npx -y @mermaid-js/mermaid-cli mmdc -i docs/diagrams/er.md -o docs/diagrams/er.png
> \`\`\`

```mermaid
erDiagram
    AUDIO_CHUNK {
        np.ndarray audio
        str speaker_device
        float chunk_seconds
    }

    TRANSCRIPT {
        str text
        str lang
        int char_count
    }

    CONTEXT_SNIPPET {
        str text
        list sources
    }

    SUGGESTION_CANDIDATE {
        str candidate
        str source
        bool validated
    }

    UI_PAYLOAD {
        str transcript
        str suggestion
        str lang
    }

    AUDIO_CHUNK ||--|{ TRANSCRIPT : "transcribe"
    TRANSCRIPT ||--|| CONTEXT_SNIPPET : "retrieval"
    TRANSCRIPT }|--|| SUGGESTION_CANDIDATE : "reasoning"
    SUGGESTION_CANDIDATE ||--|| UI_PAYLOAD : "emit"
    TRANSCRIPT ||--|| UI_PAYLOAD : "emit"
```

## How to read this

- These entities represent transient state objects, especially \`PipelineState\` fields.
- "Relationships" above represent pipeline phases and data handoff, not foreign keys.
- RAG metadata exists in \`index.metadata\` inside \`ContextEngine\`, but it is in-memory only.
- Document ingestion reads flat files from \`docs_ingested/\`; ingestion state is not persisted to disk.
