from __future__ import annotations

from pathlib import Path

from retrieval.hybrid_retriever import HybridRetriever
from retrieval.query_decomposer import QueryDecomposer
from retrieval.sparse_retriever import SparseRetriever


class StaticDenseRetriever:
    def __init__(self, results: list[dict]):
        self._results = results

    def search(self, query: str, top_k: int | None = None, filters: dict | None = None) -> list[dict]:
        filtered = []
        for result in self._results:
            if filters and any(str(result.get(key)).lower() != str(value).lower() for key, value in filters.items()):
                continue
            filtered.append(dict(result))
        return filtered[: top_k or len(filtered)]


class StaticReranker:
    def rerank(self, query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
        for rank, candidate in enumerate(candidates, start=1):
            candidate["rerank_score"] = candidate.get("rrf_score", 0.0)
            candidate["rank"] = rank
        return candidates[: top_k or len(candidates)]


class StaticDecomposer:
    def decompose(self, query: str) -> list[str]:
        return [query]


def test_sparse_retriever_persists_and_filters(tmp_path: Path):
    retriever = SparseRetriever(index_path=tmp_path / "bm25.pkl", top_k=5)
    records = [
        {
            "chunk_id": "c1",
            "document_id": "widget_pro",
            "filename": "widget_pro.txt",
            "page_number": 1,
            "chunk_index": 0,
            "text": "Part Number: WP-1234\nWeight: 2.5 kg\nVoltage: 24V DC",
        },
        {
            "chunk_id": "c2",
            "document_id": "sensor_plus",
            "filename": "sensor_plus.txt",
            "page_number": 1,
            "chunk_index": 0,
            "text": "Part Number: SP-9999\nFlow Rate: 5 L/min\nPressure Rating: 10 bar",
        },
    ]

    assert retriever.build_from_records(records) == 2
    assert retriever.exists()

    results = retriever.search("WP-1234 weight", filters={"document_id": "widget_pro"})
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"

    reloaded = SparseRetriever(index_path=tmp_path / "bm25.pkl", top_k=5)
    assert reloaded.load() == 2
    assert reloaded.search("flow rate")[0]["document_id"] == "sensor_plus"


def test_query_decomposer_splits_multi_attribute_question():
    decomposer = QueryDecomposer(max_subqueries=4)
    queries = decomposer.decompose("What are the weight and voltage for Widget Pro?")
    assert len(queries) >= 1
    all_text = " ".join(queries).lower()
    assert "weight" in all_text
    assert "voltage" in all_text


def test_hybrid_retriever_fuses_dense_and_sparse_results(tmp_path: Path):
    sparse = SparseRetriever(index_path=tmp_path / "bm25.pkl", top_k=5)
    sparse.build_from_records(
        [
            {
                "chunk_id": "shared",
                "document_id": "widget_pro",
                "filename": "widget_pro.txt",
                "page_number": 1,
                "chunk_index": 0,
                "text": "Weight: 2.5 kg\nVoltage: 24V DC\nIP Rating: IP67",
            },
            {
                "chunk_id": "sparse_only",
                "document_id": "widget_pro",
                "filename": "widget_pro.txt",
                "page_number": 1,
                "chunk_index": 1,
                "text": "Flow Rate: 5 L/min",
            },
        ]
    )

    dense = StaticDenseRetriever(
        [
            {
                "chunk_id": "dense_only",
                "document_id": "widget_pro",
                "filename": "widget_pro.txt",
                "page_number": 1,
                "chunk_index": 2,
                "text": "Manufacturer: Acme",
                "score": 0.9,
            },
            {
                "chunk_id": "shared",
                "document_id": "widget_pro",
                "filename": "widget_pro.txt",
                "page_number": 1,
                "chunk_index": 0,
                "text": "Weight: 2.5 kg\nVoltage: 24V DC\nIP Rating: IP67",
                "score": 0.8,
            },
        ]
    )

    retriever = HybridRetriever(
        dense_retriever=dense,
        sparse_retriever=sparse,
        reranker=StaticReranker(),
        query_decomposer=StaticDecomposer(),
        top_k_final=3,
    )

    results = retriever.search("weight voltage", filters={"document_id": "widget_pro"})
    assert results[0]["chunk_id"] == "shared"
    assert results[0]["dense_score"] > 0
    assert results[0]["sparse_score"] > 0
