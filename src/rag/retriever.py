"""RAG (Retrieval-Augmented Generation) system.

Lets agents pull answers from documentation instead of hallucinating.
"""
from __future__ import annotations

import logging
from typing import Any

from src.rag.embeddings import EmbeddingGenerator
from src.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGRetriever:
    def __init__(self) -> None:
        self.embeddings = EmbeddingGenerator()
        self.store = VectorStore()

    async def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        query_embedding = await self.embeddings.generate(query)
        results = self.store.search(query_embedding, top_k=top_k)
        logger.debug("RAG retrieved %d results for query: %s", len(results), query[:50])
        return results

    async def index_document(self, doc_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        embedding = await self.embeddings.generate(content)
        self.store.add(doc_id, embedding, content, metadata or {})

    async def index_codebase(self, root_path: str) -> int:
        import pathlib
        count = 0
        for path in pathlib.Path(root_path).rglob("*.py"):
            if path.name.startswith("__"):
                continue
            try:
                content = path.read_text(encoding="utf-8")
                await self.index_document(
                    doc_id=str(path),
                    content=content,
                    metadata={"file": str(path), "type": "code"},
                )
                count += 1
            except Exception as exc:
                logger.warning("Failed to index %s: %s", path, exc)
        logger.info("Indexed %d files from %s", count, root_path)
        return count

    async def retrieve_code_context(self, query: str, top_k: int = 2) -> str:
        results = await self.retrieve(query, top_k=top_k)
        if not results:
            return ""
        sections = []
        for r in results:
            sections.append(f"File: {r['metadata'].get('file', 'unknown')}")
            sections.append(r["content"][:500])
            sections.append("---")
        return "\n".join(sections)
