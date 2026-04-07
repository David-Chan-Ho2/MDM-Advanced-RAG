# MDM Advanced RAG — Product Attribute Extraction Pipeline

An Advanced RAG pipeline that ingests product specification documents, extracts structured technical attributes using LLMs, and outputs PIM-ready data through a data steward approval workflow.

---

## Overview

Product technical specifications arrive in inconsistent formats (PDF, DOCX, Excel, HTML). This pipeline automates attribute extraction across ~5,000 documents using a multi-agent LLM framework, then routes results through a review UI before export to PIM/E-commerce systems.

```
Documents → Parse → Chunk → Embed → Vector Store
                                         │
                          Query → Hybrid Retrieval → Re-rank
                                         │
                              Multi-Agent Extraction (Claude)
                                         │
                              Validation → ProductRecord
                                         │
                          Streamlit Review UI (approve/edit/reject)
                                         │
                                  PIM Export (CSV / JSON)
```

---

## Team Work Division by Week

### ✅ Week 1 — Foundation: Document Processing & Baseline RAG _(complete)_
> Goal: ingestion pipeline working across all file types + baseline RAG answering queries

| Member | Files | Deliverable |
|--------|-------|-------------|
| **1** ✅ | `config/settings.py`, `config/schema.py`, `ingestion/parsers/`, `ingestion/chunker.py`, `ingestion/pipeline.py`, `embedding/embedder.py` | Multi-format parser, chunker, batched embedding service |
| **2** ✅ | `embedding/indexer.py`, `scripts/ingest_sample.py` | Qdrant vector store — collection creation, upsert, search; ingest script |
| **3** ✅ | `rag/chain.py`, `scripts/query_baseline.py` | Baseline RAG chain (retrieve → prompt → Claude); CLI query script |
| **4** ✅ | `tests/conftest.py`, `tests/test_parsers.py`, `tests/test_chunker.py`, `tests/test_embedder.py` | Unit tests for all Week 1 components |

---

### ✅ Week 2 — Advanced Retrieval & Multi-Agent Extraction _(complete)_
> Goal: hybrid search + 5-agent extraction framework producing structured `ProductRecord`s

| Member | Files | Deliverable |
|--------|-------|-------------|
| **1** | `retrieval/dense_retriever.py`, `retrieval/sparse_retriever.py` | Qdrant ANN dense retriever; BM25 sparse retriever with disk persistence |
| **2** | `retrieval/hybrid_retriever.py`, `retrieval/reranker.py`, `retrieval/query_decomposer.py`, `rag/advanced_chain.py` | RRF fusion, flashrank reranker, LLM query decomposition, advanced RAG chain |
| **3** | `agents/base_agent.py`, `agents/specialized/` (all 5), `agents/validator.py`, `agents/orchestrator.py` | Full multi-agent extraction framework — runs agents in parallel per document, merges into `ProductRecord` |
| **4** | `workflow/review_store.py`, `workflow/batch_runner.py` | SQLite review state; async batch runner with checkpoint/resume for 5K docs |

**Week 2 done when:** `python scripts/run_batch.py --limit 100` processes 100 documents and stores `ProductRecord`s in SQLite with >80% attribute accuracy on manual spot-check.

---

### ✅ Week 3 — Approval Workflow & Final Integration _(complete)_
> Goal: data steward UI, full 5K extraction run, PIM export

| Member | Files | Deliverable |
|--------|-------|-------------|
| **1** | `workflow/exporter.py`, `scripts/run_batch.py` | Flat CSV + JSON PIM exporter; batch CLI script |
| **2** | `ui/app.py`, `ui/pages/01_review_queue.py`, `ui/pages/02_approved.py`, `ui/pages/03_export.py` | Streamlit review UI — approve / edit / reject + download |
| **3** | Full extraction run across all ~5,000 documents, quality validation report | Completed `ProductRecord`s in SQLite ready for review |
| **4** | `tests/test_retrieval.py`, `tests/test_agents.py`, `tests/test_exporter.py`, `README.md` updates | Complete test suite + final documentation |

**Week 3 done when:** Data stewards can open the Streamlit UI, review extractions, and export an approved CSV ready for PIM import.

---

## Project Structure

```
project3/
├── config/
│   ├── settings.py               # All constants: paths, model names, thresholds
│   └── schema.py                 # PIM Pydantic models (ProductRecord, AttributeValue)
├── ingestion/
│   ├── pipeline.py               # IngestionPipeline — selects parser, chunks output
│   ├── chunker.py                # DocumentChunker (RecursiveCharacterTextSplitter)
│   └── parsers/
│       ├── base.py               # BaseParser ABC + ParsedDocument dataclass
│       ├── pdf_parser.py         # pdfplumber (tables as markdown) + pypdf fallback
│       ├── docx_parser.py        # python-docx
│       ├── excel_parser.py       # openpyxl, sheet-per-page
│       ├── html_parser.py        # BeautifulSoup, strips nav/footer noise
│       └── txt_parser.py         # Plain text / Markdown
├── embedding/
│   ├── embedder.py               # EmbeddingService — batched OpenAI calls with retry
│   └── indexer.py                # VectorIndexer — Qdrant upsert + search
├── retrieval/
│   ├── dense_retriever.py        # Vector similarity (Qdrant ANN)
│   ├── sparse_retriever.py       # BM25 (rank-bm25), persisted to disk
│   ├── hybrid_retriever.py       # RRF fusion of dense + sparse → re-rank
│   ├── reranker.py               # flashrank cross-encoder
│   └── query_decomposer.py       # LLM sub-query generation
├── agents/
│   ├── base_agent.py             # BaseExtractionAgent ABC + AgentResult model
│   ├── orchestrator.py           # Runs all agents per doc, merges into ProductRecord
│   ├── validator.py              # Cross-agent consistency + unit normalization
│   └── specialized/
│       ├── identifiers_agent.py  # Part numbers, SKUs, manufacturer
│       ├── dimensions_agent.py   # Physical dimensions + weight
│       ├── electrical_agent.py   # Voltage, current, IP rating
│       ├── materials_agent.py    # Materials, RoHS, certifications
│       └── performance_agent.py  # Temperature, accuracy, flow rate
├── rag/
│   ├── chain.py                  # BaseRAGChain — simple retrieve → Claude call (Week 1)
│   └── advanced_chain.py         # AdvancedRAGChain — hybrid + rerank (Week 2)
├── workflow/
│   ├── review_store.py           # SQLite state (pending/approved/rejected/edited)
│   ├── batch_runner.py           # Async runner with checkpoint/resume for 5K docs
│   └── exporter.py               # PIMExporter → flat CSV + JSON
├── ui/
│   ├── app.py                    # Streamlit entry point
│   └── pages/
│       ├── 01_review_queue.py    # Pending extractions — approve / edit / reject
│       ├── 02_approved.py        # Approved records read-only view
│       └── 03_export.py          # Export controls + download
├── scripts/
│   ├── ingest_sample.py          # Ingest a folder of documents into the vector store
│   ├── query_baseline.py         # Query the baseline RAG from the CLI
│   └── run_batch.py              # Run full batch extraction across all documents
├── tests/
├── data/
│   ├── raw/                      # Original documents (gitignored)
│   ├── processed/                # Intermediate artifacts (gitignored)
│   └── exports/                  # Final CSV/JSON PIM exports
├── .env.example
├── requirements.txt
└── pyproject.toml
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd project3
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   ANTHROPIC_API_KEY=...
#   OPENAI_API_KEY=...
```

### 3. Start Qdrant (vector store)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

> If Docker is unavailable, see [Chroma fallback](#chroma-fallback) below.

---

## Usage

### Week 1 — Ingest and query a sample

```bash
# Place sample documents in data/raw/
python scripts/ingest_sample.py --dir data/raw --limit 20

# Ask a question against the indexed documents
python scripts/query_baseline.py "What is the operating temperature range for product X?"
```

### Week 2 — Run batch extraction

```bash
# Process all documents (resumes automatically if interrupted)
python scripts/run_batch.py --concurrency 5

# Process a limited subset first
python scripts/run_batch.py --limit 100 --concurrency 5
```

### Week 3 — Review and export

```bash
# Launch the data steward review UI
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

- **Review Queue** — approve, edit, or reject extractions one by one
- **Approved** — view all approved records
- **Export** — download CSV or JSON for PIM import

---

## PIM Attribute Schema

Each extracted attribute is an `AttributeValue` carrying the value, unit, confidence level, and source chunk IDs for traceability.

| Group | Attributes |
|-------|-----------|
| **Identifiers** | part_number, sku, gtin, manufacturer_name, product_family, revision |
| **Physical Dimensions** | length, width, height, depth, weight, diameter |
| **Electrical Specs** | voltage_input, voltage_output, current_rating, power_consumption, frequency, ip_rating |
| **Materials & Compliance** | primary_material, finish, rohs_compliant, reach_compliant, certifications |
| **Performance Metrics** | operating_temp_min/max, storage_temp_min/max, accuracy, flow_rate, pressure_rating |

**Confidence levels:**

| Level | Meaning |
|-------|---------|
| `high` | Value appears verbatim and unambiguously in source text |
| `medium` | Value inferred from context or in an unusual format |
| `low` | Best guess — source is ambiguous or partial |

The flat CSV export uses double-underscore column names:
```
physical_dimensions__length__value, physical_dimensions__length__unit, physical_dimensions__length__confidence, ...
```

---

## Architecture Notes

### Why hybrid retrieval?
Dense (vector) search finds semantically similar content. Sparse (BM25) search finds exact keyword matches like part numbers and model codes. Reciprocal Rank Fusion (RRF) merges both ranked lists; the cross-encoder reranker then rescores the merged candidates. Together they outperform either method alone on technical documents.

### Why per-document retrieval in batch mode?
Each extraction agent filters Qdrant by `document_id` so it only sees chunks from the target document. This prevents Product A's specifications from contaminating Product B's extraction.

### Why `instructor`?
The `instructor` library wraps the Anthropic SDK and enforces Pydantic model output from every LLM call. If Claude returns malformed JSON, it automatically retries with an error correction prompt — eliminating a whole class of parsing bugs at scale.

### Why checkpoint-based batch processing?
`BatchExtractionRunner` writes each `ProductRecord` to SQLite immediately after extraction. If a run fails at document 3,000, restarting with `--resume` skips already-processed documents. No work is lost.

---

## Chroma Fallback

If Docker/Qdrant is not available, `VectorIndexer` can be swapped for a Chroma-backed implementation. Both expose the same interface (`upsert`, `search`). Hybrid search is not natively supported in Chroma — the sparse BM25 leg still runs independently and results are fused in Python.

```bash
pip install chromadb
# Set in .env:
VECTOR_BACKEND=chroma
```

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `anthropic` + `instructor` | LLM calls with enforced structured output |
| `openai` | Text embeddings |
| `qdrant-client` | Vector store |
| `pdfplumber`, `python-docx`, `openpyxl`, `beautifulsoup4` | Document parsing |
| `rank-bm25` | Sparse BM25 retrieval |
| `flashrank` | Local cross-encoder reranking |
| `langchain-text-splitters` | Recursive text chunking |
| `pydantic` v2 + `pydantic-settings` | Schema validation and config |
| `streamlit` | Data steward review UI |
| `tenacity` | Retry with exponential backoff |
| `loguru` | Structured logging |
| `tqdm` | Progress bars |

---

## Week-by-Week Milestones

| Week | Status | Goal | Acceptance Criteria |
|------|--------|------|---------------------|
| **1** | ✅ Complete | Foundation | `ingest_sample.py` + `query_baseline.py` working end-to-end on 20 docs |
| **2** | ✅ Complete | Advanced extraction | `run_batch.py` on 500 docs, >80% extraction accuracy on spot-check |
| **3** | ✅ Complete | Approval + export | Data stewards can review and export approved PIM data via Streamlit UI |
