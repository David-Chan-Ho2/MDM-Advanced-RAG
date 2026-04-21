from __future__ import annotations

from rag.chain import BaseRAGChain


class FakeEmbedder:
    def embed_query(self, query: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeIndexer:
    def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict]:
        return [
            {
                "filename": "widget_pro.txt",
                "page_number": 1,
                "chunk_id": "chunk-1",
                "score": 0.9,
                "text": "Manufacturer: Acme\nIP Rating: IP67\nWeight: 2.5 kg",
            }
        ]


def test_base_rag_chain_uses_extractive_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr("rag.chain.settings.ANTHROPIC_API_KEY", "")

    chain = BaseRAGChain(embedder=FakeEmbedder(), indexer=FakeIndexer(), top_k=1)
    result = chain.query("What is the IP rating?")

    assert result["answer"] == "IP Rating: IP67"
    assert result["sources"][0]["chunk_id"] == "chunk-1"
