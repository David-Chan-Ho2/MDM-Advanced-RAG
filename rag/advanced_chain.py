"""
Advanced RAG chain (Week 2).

Flow:
  1. Decompose the query into focused sub-queries
  2. Run dense + sparse retrieval
  3. Fuse with RRF and rerank the candidate chunks
  4. Build a context block
  5. Answer with Claude when available, or fall back to extractive context
"""

from __future__ import annotations

from retrieval.hybrid_retriever import HybridRetriever

_SYSTEM_PROMPT = """\
You are a technical product data assistant. Answer using ONLY the retrieved
product specification context. If the answer is not present, say
"Not found in the provided documents." Do not guess.
"""

_CONTEXT_TEMPLATE = """\
### Retrieved context

{context}

### Question

{question}
"""


class AdvancedRAGChain:
    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self._retriever = retriever or HybridRetriever()
        self._model = model
        self._client = self._build_client()

    def query(
        self,
        question: str,
        filters: dict | None = None,
        top_k: int | None = None,
        decompose: bool = True,
    ) -> dict:
        sub_queries = (
            self._retriever.query_decomposer.decompose(question)
            if decompose
            else [question]
        )
        results = self._retriever.search(
            question,
            top_k=top_k,
            filters=filters,
            decompose=decompose,
        )

        if not results:
            return {
                "answer": "No relevant documents found.",
                "sources": [],
                "sub_queries": sub_queries,
            }

        context = self._build_context(results)
        answer = self._answer(question, context, results)

        sources = [
            {
                "filename": result.get("filename"),
                "page_number": result.get("page_number"),
                "chunk_id": result.get("chunk_id"),
                "score": round(float(result.get("score", 0.0)), 4),
                "matched_queries": result.get("matched_queries", []),
                "text": result.get("text", "")[:300],
            }
            for result in results
        ]
        return {"answer": answer, "sources": sources, "sub_queries": sub_queries}

    def _answer(self, question: str, context: str, results: list[dict]) -> str:
        if self._client is None:
            return self._fallback_answer(question, results)

        prompt = _CONTEXT_TEMPLATE.format(context=context, question=question)
        try:  # pragma: no cover - external API path
            message = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception:
            return self._fallback_answer(question, results)

    @staticmethod
    def _build_context(results: list[dict]) -> str:
        context_parts = []
        for index, result in enumerate(results, start=1):
            header = (
                f"[{index}] {result.get('filename', 'unknown')} - "
                f"page {result.get('page_number', '?')}"
            )
            context_parts.append(f"{header}\n{result.get('text', '')}")
        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def _fallback_answer(question: str, results: list[dict]) -> str:
        lowered_question = question.lower()
        for result in results:
            text = result.get("text", "")
            sentences = [sentence.strip() for sentence in text.splitlines() if sentence.strip()]
            for sentence in sentences:
                if any(token in sentence.lower() for token in lowered_question.split()):
                    return sentence

        return results[0].get("text", "Not found in the provided documents.")

    @staticmethod
    def _build_client():
        try:
            import anthropic
        except ImportError:
            return None

        from config.settings import settings

        if not settings.ANTHROPIC_API_KEY:
            return None
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
