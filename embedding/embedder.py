from __future__ import annotations

import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings


class EmbeddingService:
    def __init__(self, model: str = settings.EMBEDDING_MODEL):
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai is required: pip install openai")

        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, batching automatically."""
        if not texts:
            return []

        batch_size = settings.EMBEDDING_BATCH_SIZE
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self._embed_batch(batch)
            all_embeddings.extend(embeddings)
            logger.debug(f"Embedded batch {i // batch_size + 1}: {len(batch)} texts")

        return all_embeddings

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Replace empty strings to avoid API errors
        cleaned = [t if t.strip() else "." for t in texts]
        response = self._client.embeddings.create(model=self.model, input=cleaned)
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
