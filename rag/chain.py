"""
Baseline RAG chain (Week 1).

Flow:
  1. Embed the user query
  2. Search Qdrant for top-K similar chunks
  3. Build a prompt with retrieved context
  4. Call Claude and return the answer
"""

from __future__ import annotations

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
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic is required: pip install anthropic")

        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
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

        # 4. Call Claude
        prompt = _CONTEXT_TEMPLATE.format(context=context, question=question)
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = message.content[0].text

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
