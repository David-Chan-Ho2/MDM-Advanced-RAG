from __future__ import annotations

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from ingestion.chunker import Chunk


class VectorIndexer:
    """Wraps Qdrant — creates the collection on first run, upserts chunks, searches."""

    def __init__(
        self,
        host: str = settings.QDRANT_HOST,
        port: int = settings.QDRANT_PORT,
        collection: str = settings.QDRANT_COLLECTION,
        vector_size: int = settings.EMBEDDING_DIMENSIONS,
    ):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError:
            raise RuntimeError("qdrant-client is required: pip install qdrant-client")

        self._client = QdrantClient(host=host, port=port)
        self.collection = collection
        self.vector_size = vector_size
        self._ensure_collection(vector_size)

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def _ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = [c.name for c in self._client.get_collections().collections]
        if self.collection not in existing:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection '{self.collection}'")
        else:
            logger.debug(f"Qdrant collection '{self.collection}' already exists")

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upload chunk embeddings with payload metadata to Qdrant."""
        from qdrant_client.models import PointStruct

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")

        points = [
            PointStruct(
                id=self._chunk_id_to_int(chunk.chunk_id),
                vector=embedding,
                payload=chunk.to_payload(),
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        batch_size = 256
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self._upsert_batch(batch)
            logger.debug(f"Upserted batch {i // batch_size + 1}: {len(batch)} points")

        logger.info(f"Indexed {len(points)} chunks into '{self.collection}'")

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _upsert_batch(self, points: list) -> None:
        self._client.upsert(collection_name=self.collection, points=points)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        top_k: int = settings.TOP_K_DENSE,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        Returns list of payload dicts, each with an added 'score' key.
        filters: e.g. {"document_id": "product_abc"} — exact match on payload field.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        response = self._client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [{"score": r.score, **r.payload} for r in response.points]

    def count(self) -> int:
        return self._client.count(collection_name=self.collection).count

    def delete_collection(self) -> None:
        self._client.delete_collection(collection_name=self.collection)
        logger.warning(f"Deleted Qdrant collection '{self.collection}'")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_id_to_int(chunk_id: str) -> int:
        """UUID → stable integer ID for Qdrant (which requires integer or UUID point IDs)."""
        import uuid
        return uuid.UUID(chunk_id).int % (2**63)
