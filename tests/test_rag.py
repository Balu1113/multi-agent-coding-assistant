import pytest
from src.rag.embeddings import EmbeddingGenerator
from src.rag.vector_store import VectorStore
from src.rag.retriever import RAGRetriever


@pytest.mark.asyncio
async def test_embeddings_generate():
    gen = EmbeddingGenerator()
    emb = await gen.generate("hello world")
    assert len(emb) == 384
    assert all(isinstance(v, float) for v in emb)


def test_vector_store_add_search():
    store = VectorStore()
    store.add("doc1", [1.0, 0.0, 0.0], "content about cats", {"type": "doc"})
    store.add("doc2", [0.0, 1.0, 0.0], "content about dogs", {"type": "doc"})

    results = store.search([1.0, 0.1, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] > results[1]["score"]


def test_vector_store_empty():
    store = VectorStore()
    results = store.search([1.0, 0.0, 0.0])
    assert results == []


def test_vector_store_remove():
    store = VectorStore()
    store.add("doc1", [1.0, 0.0], "content")
    assert store.count() == 1
    store.remove("doc1")
    assert store.count() == 0


@pytest.mark.asyncio
async def test_retriever_retrieve():
    retriever = RAGRetriever()
    await retriever.index_document("doc1", "Python is a programming language", {"topic": "python"})
    results = await retriever.retrieve("programming", top_k=1)
    assert len(results) == 1
    assert "programming" in results[0]["content"]
