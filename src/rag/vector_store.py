from __future__ import annotations

import logging
from typing import Any

import numpy as np

from src.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._embeddings: dict[str, list[float]] = {}

    def add(self, doc_id: str, embedding: list[float], content: str, metadata: dict[str, Any] | None = None) -> None:
        self._documents[doc_id] = {"content": content, "metadata": metadata or {}}
        self._embeddings[doc_id] = embedding
        logger.debug("Added document %s to vector store", doc_id)

    def search(self, query_embedding: list[float], top_k: int = 3) -> list[dict[str, Any]]:
        if not self._embeddings:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)
        scores: list[tuple[float, str]] = []

        for doc_id, emb in self._embeddings.items():
            doc_vec = np.array(emb, dtype=np.float32)
            similarity = float(np.dot(query_vec, doc_vec))
            scores.append((similarity, doc_id))

        scores.sort(key=lambda x: x[0], reverse=True)
        top = scores[:top_k]

        results = []
        for score, doc_id in top:
            doc = self._documents[doc_id]
            results.append({
                "id": doc_id,
                "score": score,
                "content": doc["content"],
                "metadata": doc["metadata"],
            })
        return results

    def remove(self, doc_id: str) -> None:
        self._documents.pop(doc_id, None)
        self._embeddings.pop(doc_id, None)

    def count(self) -> int:
        return len(self._documents)
