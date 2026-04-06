from __future__ import annotations

from config.settings import settings
from retrieval.dense_retriever import DenseRetriever
from retrieval.query_decomposer import QueryDecomposer
from retrieval.reranker import Reranker
from retrieval.sparse_retriever import SparseRetriever


class HybridRetriever:
    """Hybrid dense + sparse retrieval with query decomposition and reranking."""

    def __init__(
        self,
        dense_retriever: DenseRetriever | None = None,
        sparse_retriever: SparseRetriever | None = None,
        reranker: Reranker | None = None,
        query_decomposer: QueryDecomposer | None = None,
        top_k_dense: int = settings.TOP_K_DENSE,
        top_k_sparse: int = settings.TOP_K_SPARSE,
        top_k_final: int = settings.TOP_K_RERANK,
        rrf_k: int = settings.RRF_K,
        candidate_pool: int = settings.HYBRID_CANDIDATE_POOL,
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.reranker = reranker or Reranker()
        self.query_decomposer = query_decomposer or QueryDecomposer()
        self._top_k_dense = top_k_dense
        self._top_k_sparse = top_k_sparse
        self._top_k_final = top_k_final
        self._rrf_k = rrf_k
        self._candidate_pool = candidate_pool

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
        decompose: bool = True,
    ) -> list[dict]:
        sub_queries = (
            self.query_decomposer.decompose(query)
            if decompose
            else [query]
        )

        fused: dict[str, dict] = {}
        for sub_query in sub_queries:
            dense_results = self.dense_retriever.search(
                sub_query,
                top_k=self._top_k_dense,
                filters=filters,
            )
            sparse_results = self.sparse_retriever.search(
                sub_query,
                top_k=self._top_k_sparse,
                filters=filters,
            )
            self._accumulate(fused, dense_results, sub_query, source="dense")
            self._accumulate(fused, sparse_results, sub_query, source="sparse")

        if not fused:
            return []

        candidates = sorted(
            fused.values(),
            key=lambda item: (
                item.get("rrf_score", 0.0),
                item.get("dense_score", 0.0),
                item.get("sparse_score", 0.0),
            ),
            reverse=True,
        )
        pool_size = max(
            (top_k or self._top_k_final) * 3,
            self._candidate_pool,
        )

        reranked = self.reranker.rerank(query, candidates[:pool_size], top_k=top_k or self._top_k_final)
        results = reranked or candidates[: top_k or self._top_k_final]

        for item in results:
            item.setdefault("matched_queries", sub_queries)
            item["score"] = item.get("rerank_score", item.get("rrf_score", item.get("score", 0.0)))

        return results

    def _accumulate(
        self,
        fused: dict[str, dict],
        results: list[dict],
        sub_query: str,
        source: str,
    ) -> None:
        for rank, result in enumerate(results, start=1):
            key = self._result_key(result)
            entry = fused.setdefault(
                key,
                {
                    **result,
                    "rrf_score": 0.0,
                    "dense_score": 0.0,
                    "sparse_score": 0.0,
                    "matched_queries": [],
                },
            )

            entry["rrf_score"] += self.reciprocal_rank_fusion(rank, self._rrf_k)
            entry["matched_queries"] = sorted(set(entry["matched_queries"] + [sub_query]))

            score_key = f"{source}_score"
            entry[score_key] = max(float(result.get("score", 0.0)), float(entry.get(score_key, 0.0)))

            for payload_key, payload_value in result.items():
                entry.setdefault(payload_key, payload_value)

    @staticmethod
    def reciprocal_rank_fusion(rank: int, rrf_k: int) -> float:
        return 1.0 / (rrf_k + rank)

    @staticmethod
    def _result_key(result: dict) -> str:
        if result.get("chunk_id"):
            return str(result["chunk_id"])
        return "|".join(
            [
                str(result.get("document_id", "")),
                str(result.get("page_number", "")),
                str(result.get("chunk_index", "")),
                str(result.get("text", ""))[:64],
            ]
        )
