# Project Context — EchoMind

Owner: Sami
Repo: https://github.com/XDR-SAM/EchoMind---Real-Time-Conversation-Intelligence
Primary language: Python 3.10/3.11
Platform: Windows 10/11 desktop
Current backend: PyQt6 overlay, faster-whisper, llama-cpp, sentence-transformers, FAISS, soundcard

## Current State
- Pipeline refactored into phased orchestration with structured outputs
- Benchmark path uses `suggest_structured()`
- Windows launcher: `scripts/run.py`
- Docs: installation.md, usage.md, deployment.md, diagrams, roadmap.md
- README badges, screenshots/assets, architecture diagram, cloned by real URL
- License: MIT
- Author: Sami

## Live Work Log
- 2026-07-14: Added README polish, CLI launcher, structured LLM output, layered docs, MIT license, real clone URL, screenshots section
- 2026-07-14: Updated README anchors, added explicit model download commands, fixed installation.md and usage.md
- 2026-07-14: Added session persistence (session.py, session_store.py), Exporter (exporter.py)
- 2026-07-14: Added ActionItem + `suggest_action_items(transcript)` in llm_engine.py
- 2026-07-14: Added Dockerfile, docker-compose.yml, .dockerignore for headless/test/benchmark container support

## Backend Session Worklog
- backend/session_store.py: SQLite-backed session persistence
- backend/session.py: Session lifecycle manager
- backend/exporter.py: JSON/CSV export helpers
- backend/llm_engine.py: ActionItem dataclass + extract_action_items() method