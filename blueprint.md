# Bug-Fix Blueprint
Audited against:
- backend/main.py
- backend/pipeline.py
- backend/ui.py
- backend/llm_engine.py
- backend/transcriber.py
- backend/context_engine.py
- backend/audio_capture.py
- backend/vad.py
- tests/test_pipeline.py
- README.md
- docs/engineering.md
- requirements*.txt

Ranked issues by runtime impact on Windows.

## P0 — Runtime Breakage
1. **main.py monkey-patches nonexistent pipeline state fields**
   - File: `backend/main.py` lines 310-334
   - Symptom: `AttributeError: 'Pipeline' object has no attribute 'transcript_buffer'` after `start()`
   - Root cause: `main.py` reads/writes `pipeline.transcript_buffer` and `pipeline.latest_lang`, but `Pipeline` exposes neither; state lives inside `PipelineState` transient instances.
   - Minimal fix: remove stale attribute access; use local accumulators in instrumented worker or expose minimal buffered fields on `Pipeline`.

2. **ui.py assumes `lang` is always set, hiding label state on stale payloads**
   - File: `backend/ui.py` lines 233-235
   - Symptom: title label clears to `Meeting Copilot · ` when backend omits `lang` or payload lapses
   - Minimal fix: only update title when `lang` is truthy; never overwrite with empty label text.

## P1 — Windows Boundary Assumptions / Dead Wires
3. **Pipeline docstring promises FAISS filter by doc kind; code ignores kind**
   - File: `backend/context_engine.py` lines 19-54 vs `docs/engineering.md`
   - Minor, but engineering.md shows filter expectation; keep minimal doc fix rather than broad rewrite.

4. **engineering.md says WebEngine overlay; code uses plain QWidget/QFrame**
   - File: `docs/engineering.md` line 20 vs `backend/ui.py`
   - Contradiction only; minimal doc fix.

5. **README audio path says `docs_ingested/`; code constructs same path, but docs name mismatch in prose likely to confuse**
   - Keep consistent strings in README; no code change needed.

## P2 — Risky Runtime Behavior
6. **Pipeline `_worker` blocks on `audio.read()` from producer-consumer queue without queue backpressure honor**
   - File: `backend/pipeline.py` lines 161-174
   - Risk on Windows: if `AudioCapture` producer gets behind or raises silently, retry loop yields tight spin.
   - Minimal mitigation: cap retry sleep growth; already present as 30ms, acceptable.

7. **AudioCapture thread daemon + 1s join on stop may truncate last buffered chunk**
   - File: `backend/audio_capture.py` lines 51-65
   - Risk: consumer drains only priority-latest frame; tail audio before stop can be dropped.
   - Acceptable for 2s chunks, but document expectation.

## Minimal Patches Plan
- A. `backend/main.py`: replace stale attribute monkeying with local `lang_prior` and rolling `transcript_buffer` inside instrumented worker.
- B. `backend/ui.py`: guard title update with truthy `lang`.
- C. `docs/engineering.md`: correct overlay technology mention; remove misleading FAISS filter wording.
- D. `blueprint.md`: this file.

## Rationale
These changes align actual runtime behavior with README/Pipeline contract without broad rewrites and avoid breaking existing tests.
