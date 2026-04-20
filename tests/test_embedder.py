"""
Tests for EmbeddingService.

These tests mock the embedding backend so they run without API keys or model downloads.
"""

from unittest.mock import MagicMock, patch

import pytest

from config.settings import settings


@pytest.fixture
def mock_embedder():
    """Return an EmbeddingService with the local sentence-transformer mocked out."""
    with patch("sentence_transformers.SentenceTransformer") as MockSentenceTransformer:

        def fake_encode(input, show_progress_bar=False):
            return MagicMock(
                tolist=lambda: [[0.1 * i] * settings.EMBEDDING_DIMENSIONS for i in range(len(input))]
            )

        MockSentenceTransformer.return_value.encode.side_effect = fake_encode

        from embedding.embedder import EmbeddingService

        yield EmbeddingService()


class TestEmbeddingService:
    def test_embed_texts_returns_list(self, mock_embedder):
        texts = ["product spec one", "product spec two"]
        embeddings = mock_embedder.embed_texts(texts)
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2

    def test_embedding_dimension(self, mock_embedder):
        embeddings = mock_embedder.embed_texts(["test text"])
        assert len(embeddings[0]) == settings.EMBEDDING_DIMENSIONS

    def test_embed_query_returns_single_vector(self, mock_embedder):
        vector = mock_embedder.embed_query("What is the IP rating?")
        assert isinstance(vector, list)
        assert len(vector) == settings.EMBEDDING_DIMENSIONS

    def test_empty_input_returns_empty(self, mock_embedder):
        result = mock_embedder.embed_texts([])
        assert result == []

    def test_each_text_gets_an_embedding(self, mock_embedder):
        texts = ["a", "b", "c"]
        embeddings = mock_embedder.embed_texts(texts)
        assert len(embeddings) == len(texts)

    def test_batching_handles_large_input(self, mock_embedder):
        # 250 texts should be processed in 3 batches (batch_size=100)
        texts = [f"product spec {i}" for i in range(250)]
        embeddings = mock_embedder.embed_texts(texts)
        assert len(embeddings) == 250
