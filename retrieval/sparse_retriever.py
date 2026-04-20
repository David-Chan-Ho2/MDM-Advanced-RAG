from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Iterable

from loguru import logger

from config.settings import settings
from ingestion.chunker import Chunk

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - exercised via runtime guard
    BM25Okapi = None

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text or "")]


class SparseRetriever:
    """BM25 sparse retrieval with simple disk persistence."""

    def __init__(
        self,
        index_path: Path | str = settings.BM25_INDEX_PATH,
        top_k: int = settings.TOP_K_SPARSE,
    ):
        self.index_path = Path(index_path)
        self._top_k = top_k
        self._records: list[dict] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25 = None

    def exists(self) -> bool:
        return self.index_path.exists()

    def build_from_chunks(self, chunks: Iterable[Chunk], persist: bool = True) -> int:
        records = [chunk.to_payload() for chunk in chunks]
        return self.build_from_records(records, persist=persist)

    def build_from_records(self, records: Iterable[dict], persist: bool = True) -> int:
        self._records = [self._coerce_record(record) for record in records if record.get("text")]
        self._tokenized_corpus = [tokenize(record["text"]) for record in self._records]
        self._bm25 = self._create_bm25(self._tokenized_corpus)

        if persist:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "records": self._records}
            with self.index_path.open("wb") as fh:
                pickle.dump(payload, fh)
            logger.info(f"Persisted sparse index with {len(self._records)} chunks to {self.index_path}")

        return len(self._records)

    def load(self) -> int:
        if not self.exists():
            self._records = []
            self._tokenized_corpus = []
            self._bm25 = None
            return 0

        with self.index_path.open("rb") as fh:
            payload = pickle.load(fh)

        self._records = list(payload.get("records", []))
        self._tokenized_corpus = [tokenize(record.get("text", "")) for record in self._records]
        self._bm25 = self._create_bm25(self._tokenized_corpus)
        return len(self._records)

    def delete_index(self) -> None:
        if self.exists():
            self.index_path.unlink()
            logger.warning(f"Deleted sparse index {self.index_path}")
        self._records = []
        self._tokenized_corpus = []
        self._bm25 = None

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        if not query.strip():
            return []

        if not self._records and self.exists():
            self.load()

        if not self._records:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._score(query_tokens)
        results: list[dict] = []

        for record, score in zip(self._records, scores):
            if filters and not self._matches_filters(record, filters):
                continue
            results.append({"score": float(score), **record})

        results.sort(
            key=lambda item: (
                item["score"],
                str(item.get("document_id", "")),
                int(item.get("page_number", 0)),
                int(item.get("chunk_index", 0)),
            ),
            reverse=True,
        )
        return results[: top_k or self._top_k]

    def count(self) -> int:
        if not self._records and self.exists():
            self.load()
        return len(self._records)

    def records(self) -> list[dict]:
        if not self._records and self.exists():
            self.load()
        return list(self._records)

    def _score(self, query_tokens: list[str]) -> list[float]:
        lexical_scores = self._lexical_scores(query_tokens)

        if self._bm25 is not None:
            bm25_scores = list(self._bm25.get_scores(query_tokens))
            min_score = min(bm25_scores, default=0.0)
            if min_score < 0:
                bm25_scores = [score - min_score for score in bm25_scores]
            return [
                float(bm25_score) + lexical_score
                for bm25_score, lexical_score in zip(bm25_scores, lexical_scores)
            ]

        return lexical_scores

    def _lexical_scores(self, query_tokens: list[str]) -> list[float]:
        query_set = set(query_tokens)
        scores: list[float] = []
        for record_tokens, record in zip(self._tokenized_corpus, self._records):
            token_set = set(record_tokens)
            overlap = len(query_set & token_set) / max(len(query_set), 1)
            phrase_bonus = 0.5 if " ".join(query_tokens) in record.get("text", "").lower() else 0.0
            scores.append(overlap + phrase_bonus)
        return scores

    @staticmethod
    def _create_bm25(tokenized_corpus: list[list[str]]):
        if BM25Okapi is None or not tokenized_corpus:
            return None
        return BM25Okapi(tokenized_corpus)

    @staticmethod
    def _coerce_record(record: dict | Chunk) -> dict:
        if isinstance(record, Chunk):
            return record.to_payload()
        return dict(record)

    @staticmethod
    def _matches_filters(record: dict, filters: dict) -> bool:
        for key, value in filters.items():
            record_value = record.get(key)
            if str(record_value).lower() != str(value).lower():
                return False
        return True
