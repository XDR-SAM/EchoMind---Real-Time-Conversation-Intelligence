import os
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class ContextEngine:
    def __init__(self, embedding_model="all-MiniLM-L6-v2", docs_dir=None, top_k=3):
        self.embedder = SentenceTransformer(embedding_model)
        self.docs_dir = Path(docs_dir) if docs_dir else None
        self.top_k = top_k
        self.index: faiss.IndexFlatL2 | None = None
        self.metadata: list[dict] = []
        if self.docs_dir and self.docs_dir.exists():
            self.ingest_directory(self.docs_dir)

    def ingest_directory(self, directory: Path):
        texts, metas = [], []
        for path in directory.rglob("*"):
            if path.is_file():
                suffix = path.suffix.lower()
                if suffix in {".txt", ".md", ".csv"}:
                    try:
                        txt = path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    if txt.strip():
                        texts.append(txt)
                        metas.append({"source": str(path), "kind": suffix})

        if not texts:
            return
        embeddings = self.embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        d = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(d)
        self.index.add(embeddings)
        self.metadata = metas
        self._texts = texts

    def search(self, query: str):
        if not self.index:
            return ""
        q = self.embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        dists, idxs = self.index.search(q, self.top_k)
        hits = []
        for score, idx in zip(dists[0], idxs[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            snippet = self._texts[idx][:500]
            hits.append(f"[{meta['source']}] {snippet}")
        return "\n\n".join(hits)
