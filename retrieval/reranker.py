from __future__ import annotations

from loguru import logger

from config.settings import settings
from retrieval.sparse_retriever import tokenize

try:
    from flashrank import Ranker, RerankRequest
except ImportError:  # pragma: no cover - exercised via runtime guard
    Ranker = None
    RerankRequest = None


class Reranker:
    """Reranks fused retrieval candidates, preferring Flashrank when available."""

    def __init__(
        self,
        top_k: int = settings.TOP_K_RERANK,
        model_name: str = "ms-marco-TinyBERT-L-2-v2",
    ):
        self._top_k = top_k
        self._model_name = model_name
        self._ranker = None

        if Ranker is not None:
            try:
                self._ranker = Ranker(model_name=model_name)
            except Exception as exc:  # pragma: no cover - network/model cache dependent
                logger.warning(f"Flashrank unavailable, falling back to lexical reranking: {exc}")

    def rerank(self, query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
        if not candidates:
            return []

        limit = top_k or self._top_k

        if self._ranker is not None and RerankRequest is not None:
            try:
                return self._flashrank_rerank(query, candidates, limit)
            except Exception as exc:  # pragma: no cover - depends on local flashrank runtime
                logger.warning(f"Flashrank rerank failed, falling back to lexical reranking: {exc}")

        return self._lexical_rerank(query, candidates, limit)

    def _flashrank_rerank(self, query: str, candidates: list[dict], limit: int) -> list[dict]:
        passages = [
            {
                "id": str(index),
                "text": candidate.get("text", ""),
                "meta": candidate,
            }
            for index, candidate in enumerate(candidates)
        ]
        request = RerankRequest(query=query, passages=passages)
        ranked = self._ranker.rerank(request)

        results: list[dict] = []
        for rank, item in enumerate(ranked, start=1):
            candidate = dict(item.get("meta") or passages[int(item["id"])]["meta"])
            candidate["rerank_score"] = float(item.get("score", 0.0))
            candidate["rank"] = rank
            results.append(candidate)

        return results[:limit]

    def _lexical_rerank(self, query: str, candidates: list[dict], limit: int) -> list[dict]:
        query_tokens = set(tokenize(query))
        reranked: list[dict] = []

        for candidate in candidates:
            text = candidate.get("text", "")
            candidate_tokens = set(tokenize(text))
            overlap = len(query_tokens & candidate_tokens) / max(len(query_tokens), 1)
            phrase_bonus = 0.5 if query.lower() in text.lower() else 0.0
            base_score = float(
                candidate.get("rrf_score")
                or candidate.get("dense_score")
                or candidate.get("sparse_score")
                or candidate.get("score")
                or 0.0
            )
            rerank_score = base_score + overlap + phrase_bonus
            reranked.append(
                {
                    **candidate,
                    "rerank_score": rerank_score,
                }
            )

        reranked.sort(
            key=lambda item: (
                item.get("rerank_score", 0.0),
                item.get("rrf_score", 0.0),
                item.get("dense_score", 0.0),
                item.get("sparse_score", 0.0),
            ),
            reverse=True,
        )

        for rank, item in enumerate(reranked, start=1):
            item["rank"] = rank

        return reranked[:limit]
