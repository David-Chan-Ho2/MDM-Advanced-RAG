from __future__ import annotations

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

_OPENAI_MODELS = {"text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"}


class EmbeddingService:
    def __init__(self, model: str = settings.EMBEDDING_MODEL):
        self.model = model
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        self._use_openai = model in _OPENAI_MODELS

        if self._use_openai:
            try:
                from openai import OpenAI
            except ImportError:
                raise RuntimeError("openai is required: pip install openai")
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise RuntimeError("sentence-transformers is required: pip install sentence-transformers")
            logger.info(f"Loading local embedding model '{model}' (first run downloads ~90 MB)")
            self._st_model = SentenceTransformer(model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
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
        cleaned = [t if t.strip() else "." for t in texts]
        if self._use_openai:
            response = self._client.embeddings.create(model=self.model, input=cleaned)
            return [item.embedding for item in response.data]
        else:
            return self._st_model.encode(cleaned, show_progress_bar=False).tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
