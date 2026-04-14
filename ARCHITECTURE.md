# Architecture Notes

## Week 1

**Parsing:** `pdfplumber` is used for PDFs because it retains tables as markdown, preserving structured attribute data that plain text extraction would lose. A `pypdf` fallback handles encrypted or malformed PDFs. The CSV parser treats each row as a separate `ParsedDocument` via the `file_content` column, allowing the provided Honeywell dataset files to be ingested directly without re-extracting text.

**Chunking:** `RecursiveCharacterTextSplitter` (chunk size 800, overlap 100) is used to keep attribute groups intact within a single chunk. A hard split on characters is preferred over sentence splitting because spec sheets contain dense tabular data that does not follow sentence boundaries.

**Embeddings:** `sentence-transformers` with `all-MiniLM-L6-v2` (384 dimensions) is the default — no external API key or quota required. The model is downloaded once and cached locally. OpenAI `text-embedding-3-small` (1536 dimensions) can be substituted via `.env`; switching models requires recreating the Qdrant collection since vector dimensions must match.

**Vector store:** Qdrant is chosen over alternatives (Chroma, Pinecone) because it supports payload filtering natively, which is needed in Week 2 so each extraction agent processes only one document's chunks at a time without mixing information across products. It also supports hybrid dense+sparse search natively, avoiding the need for a separate BM25 index merge layer.

**Baseline RAG:** Week 1 uses dense-only retrieval (cosine similarity via `query_points`). Hybrid search (dense + BM25 + RRF + reranker) is deferred to Week 2 since it requires additional infrastructure and the baseline is sufficient to validate the ingestion pipeline end-to-end.

## Week 2


## Week 3