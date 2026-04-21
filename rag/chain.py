"""
Baseline RAG chain (Week 1).

Flow:
  1. Embed the user query
  2. Search Qdrant for top-K similar chunks
  3. Build a prompt with retrieved context
  4. Call Claude and return the answer
"""

from __future__ import annotations

import re

from loguru import logger

from config.settings import settings
from embedding.embedder import EmbeddingService
from embedding.indexer import VectorIndexer

_SYSTEM_PROMPT = """\
You are a technical product data assistant. Answer the user's question using ONLY
the product specification context provided below. If the answer is not present in
the context, say "Not found in the provided documents." Do not guess or fabricate
values.
"""

_CONTEXT_TEMPLATE = """\
### Retrieved context

{context}

### Question

{question}
"""


class BaseRAGChain:
    def __init__(
        self,
        embedder: EmbeddingService | None = None,
        indexer: VectorIndexer | None = None,
        top_k: int = settings.TOP_K_DENSE,
        model: str = settings.CLAUDE_EXTRACTION_MODEL,
    ):
        self._client = self._build_client()
        self._embedder = embedder or EmbeddingService()
        self._indexer = indexer or VectorIndexer()
        self._top_k = top_k
        self._model = model

    def query(self, question: str, filters: dict | None = None) -> dict:
        """
        Run a RAG query.

        Returns:
            {
                "answer": str,
                "sources": [{"filename": str, "page_number": int, "text": str, "score": float}]
            }
        """
        # 1. Embed query
        query_vector = self._embedder.embed_query(question)

        # 2. Retrieve top-K chunks
        results = self._indexer.search(query_vector, top_k=self._top_k, filters=filters)

        if not results:
            return {"answer": "No relevant documents found.", "sources": []}

        # 3. Build context block
        context_parts = []
        for i, r in enumerate(results, start=1):
            header = f"[{i}] {r.get('filename', 'unknown')} — page {r.get('page_number', '?')}"
            context_parts.append(f"{header}\n{r.get('text', '')}")
        context = "\n\n---\n\n".join(context_parts)

        # 4. Answer with Claude when configured; otherwise fall back to retrieved text.
        prompt = _CONTEXT_TEMPLATE.format(context=context, question=question)
        answer = self._answer(question, prompt, results)

        sources = [
            {
                "filename": r.get("filename"),
                "page_number": r.get("page_number"),
                "chunk_id": r.get("chunk_id"),
                "score": round(r.get("score", 0), 4),
                "text": r.get("text", "")[:300],  # truncated preview
            }
            for r in results
        ]

        logger.debug(f"RAG query answered using {len(results)} chunks")
        return {"answer": answer, "sources": sources}

    def _answer(self, question: str, prompt: str, results: list[dict]) -> str:
        if self._client is None:
            return self._fallback_answer(question, results)

        try:  # pragma: no cover - external API path
            message = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as exc:
            logger.warning(f"Claude query failed; falling back to retrieved context: {exc}")
            return self._fallback_answer(question, results)

    @staticmethod
    def _fallback_answer(question: str, results: list[dict]) -> str:
        stopwords = {
            "a",
            "an",
            "and",
            "for",
            "in",
            "is",
            "of",
            "or",
            "product",
            "the",
            "to",
            "what",
        }
        question_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", question.lower())
            if token not in stopwords
        }
        best_line = ""
        best_score = 0

        for result in results:
            text = result.get("text", "")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                line_tokens = set(re.findall(r"[a-z0-9]+", line.lower()))
                score = len(question_tokens & line_tokens)
                if score > best_score:
                    best_score = score
                    best_line = line

        if best_line:
            return best_line

        return results[0].get("text", "Not found in the provided documents.")

    @staticmethod
    def _build_client():
        if not settings.ANTHROPIC_API_KEY:
            return None

        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic is not installed; using extractive fallback answers")
            return None

        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
