"""
Tests for EmbeddingService.

These tests mock the OpenAI client so they run without an API key.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_embedder():
    """Return an EmbeddingService with the OpenAI client mocked out."""
    with patch("embedding.embedder.OpenAI") as MockOpenAI:
        # Build a fake embedding response
        def fake_create(model, input):
            response = MagicMock()
            response.data = [
                MagicMock(embedding=[0.1 * i] * 1536) for i in range(len(input))
            ]
            return response

        MockOpenAI.return_value.embeddings.create.side_effect = fake_create

        from embedding.embedder import EmbeddingService
        embedder = EmbeddingService()
        yield embedder


class TestEmbeddingService:
    def test_embed_texts_returns_list(self, mock_embedder):
        texts = ["product spec one", "product spec two"]
        embeddings = mock_embedder.embed_texts(texts)
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2

    def test_embedding_dimension(self, mock_embedder):
        embeddings = mock_embedder.embed_texts(["test text"])
        assert len(embeddings[0]) == 1536

    def test_embed_query_returns_single_vector(self, mock_embedder):
        vector = mock_embedder.embed_query("What is the IP rating?")
        assert isinstance(vector, list)
        assert len(vector) == 1536

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
