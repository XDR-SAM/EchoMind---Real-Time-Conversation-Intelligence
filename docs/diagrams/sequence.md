# Sequence Diagram

> Render locally with one command:
>
> \`\`\`bash
> npx -y @mermaid-js/mermaid-cli mmdc -i docs/diagrams/sequence.md -o docs/diagrams/sequence.png
> \`\`\`

```mermaid
sequenceDiagram
    participant Main
    participant AudioCapture
    participant Pipeline
    participant VAD
    participant Transcriber
    participant ContextEngine
    participant LLMEngine
    participant Overlay

    Main->>AudioCapture: start thread loopback capture
    Main->>Pipeline: start thread worker
    loop for each audio chunk
        Pipeline->>AudioCapture: read() -> np.ndarray or None
        alt no audio
            Pipeline->>Pipeline: sleep backoff
        else audio present
            Pipeline->>VAD: (audio) speech bool
            alt speech detected
                Pipeline->>Transcriber: transcribe(audio_chunk) -> text, lang
                Pipeline->>ContextEngine: search(transcript_window) -> context_snippet
                Pipeline->>LLMEngine: suggest(prompt) -> raw suggestion
                Pipeline->>Pipeline: run guardrails -> validated suggestion
                Pipeline->>Overlay: ui_queue.put_nowait(
                      transcript,
                      suggestion,
                      lang
                    )
            else no speech
                Pipeline-->>Pipeline: skip iteration
            end
        end
    end
```

## Notes

- \`AudioCapture.read()\` returns a mono \`np.ndarray\` or \`None\` when no chunk is available yet.
- \`ContextEngine.search\` builds and queries a FAISS index over embedded text files; it is not a SQL or relational lookup.
- Only successful iterations and guarded LLM outputs are emitted to the overlay.
