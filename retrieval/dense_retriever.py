from __future__ import annotations

from config.settings import settings
from embedding.embedder import EmbeddingService
from embedding.indexer import VectorIndexer


class DenseRetriever:
    """Dense semantic retrieval backed by the Week 1 embedder + vector indexer."""

    def __init__(
        self,
        embedder: EmbeddingService | None = None,
        indexer: VectorIndexer | None = None,
        top_k: int = settings.TOP_K_DENSE,
    ):
        self._embedder = embedder or EmbeddingService()
        self._indexer = indexer or VectorIndexer()
        self._top_k = top_k

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        if not query.strip():
            return []

        query_vector = self._embedder.embed_query(query)
        return self._indexer.search(
            query_vector=query_vector,
            top_k=top_k or self._top_k,
            filters=filters,
        )
