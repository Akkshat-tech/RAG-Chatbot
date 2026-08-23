"""
vectorstore.py
A minimal vector store: loads the JSON file produced by ingest.py and does
cosine-similarity search in memory with numpy. No external vector DB needed,
which keeps the retrieval mechanism transparent for your evaluation report.
"""
import json
import numpy as np
import config


def load_store(path: str = None):
    path = path or config.STORE_PATH
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    if not records:
        raise ValueError("Vector store is empty. Did you run ingest.py?")
    matrix = np.array([r["embedding"] for r in records], dtype=np.float32)
    # pre-normalize for fast cosine similarity
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1e-8
    normalized = matrix / norms
    return records, normalized


class VectorStore:
    def __init__(self, path: str = None):
        self.records, self.normalized_matrix = load_store(path)

    def search(self, query_embedding, top_k: int = None):
        top_k = top_k or config.TOP_K
        q = np.array(query_embedding, dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-8)
        sims = self.normalized_matrix @ q_norm  # cosine similarity to every chunk
        top_idx = np.argsort(-sims)[:top_k]
        results = []
        for idx in top_idx:
            rec = self.records[idx]
            results.append({
                "text": rec["text"],
                "source": rec["source"],
                "page": rec.get("page"),
                "score": float(sims[idx]),
            })
        return results
