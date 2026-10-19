from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "all-MiniLM-L6-v2"
        self._model = None

    async def generate(self, text: str) -> list[float]:
        try:
            return await self._generate_with_model(text)
        except ImportError:
            return self._generate_fallback(text)

    async def _generate_with_model(self, text: str) -> list[float]:
        from sentence_transformers import SentenceTransformer
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def _generate_fallback(self, text: str) -> list[float]:
        """Simple hash-based embedding fallback when sentence-transformers is not installed."""
        cleaned = text.lower().strip()
        seed = int(hashlib.md5(cleaned.encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.randn(384)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.generate(t) for t in texts]
