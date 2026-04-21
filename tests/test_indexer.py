from __future__ import annotations

from embedding.indexer import VectorIndexer
from ingestion.chunker import Chunk


def test_vector_indexer_falls_back_to_local_storage_when_remote_unavailable(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "embedding.indexer.settings.QDRANT_LOCAL_PATH", tmp_path / "qdrant_local"
    )

    indexer = VectorIndexer(
        host="127.0.0.1",
        port=65530,
        collection="test_product_docs",
        vector_size=3,
    )

    chunk = Chunk(
        chunk_id="12345678-1234-5678-1234-567812345678",
        document_id="widget_pro",
        filename="widget_pro.txt",
        file_format="txt",
        page_number=1,
        chunk_index=0,
        text="Weight: 2.5 kg\nVoltage: 24V DC",
        metadata={"product_id": "widget_pro"},
    )

    indexer.upsert([chunk], [[0.1, 0.2, 0.3]])

    results = indexer.search([0.1, 0.2, 0.3], filters={"document_id": "widget_pro"})

    assert indexer.count() == 1
    assert results
    assert results[0]["document_id"] == "widget_pro"

    second_indexer = VectorIndexer(
        host="127.0.0.1",
        port=65530,
        collection="test_product_docs",
        vector_size=3,
    )
    second_indexer.reset_collection()
    assert second_indexer.count() == 0
