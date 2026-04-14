# MDM Advanced RAG — Product Attribute Extraction Pipeline

An Advanced RAG pipeline that ingests product specification documents, extracts structured technical attributes using LLMs, and outputs PIM-ready data through a data steward approval workflow.

---

## Overview

Product technical specifications arrive in inconsistent formats (PDF, DOCX, Excel, HTML, TXT, CSV). This pipeline automates attribute extraction across ~5,000 documents using a multi-agent LLM framework, then routes results through a review UI before export to PIM/E-commerce systems.

```
Documents → Parse → Chunk → Embed → Vector Store
                                         │
                          Query → Hybrid Retrieval → Re-rank
                                         │
                              Multi-Agent Extraction (Claude)
                                         │
                              Validation → ProductRecord (JSON)
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
| **1** ✅ | `config/settings.py`, `config/schema.py`, `ingestion/parsers/`, `ingestion/chunker.py`, `ingestion/pipeline.py`, `embedding/embedder.py` | Multi-format parser (PDF, DOCX, Excel, HTML, TXT, CSV), chunker, batched embedding service |
| **2** ✅ | `embedding/indexer.py`, `scripts/ingest_sample.py` | Qdrant vector store — collection creation, upsert, search; ingest script |
| **3** ✅ | `rag/chain.py`, `scripts/query_baseline.py` | Baseline RAG chain (retrieve → prompt → Claude); CLI query script |
| **4** ✅ | `tests/conftest.py`, `tests/test_parsers.py`, `tests/test_chunker.py`, `tests/test_embedder.py` | Unit tests for all Week 1 components |

---

### Week 2 — Advanced Retrieval & Multi-Agent Extraction _(up next)_
> Goal: hybrid search + 5-agent extraction framework producing structured `ProductRecord`s (JSON)

| Member | Files | Deliverable |
|--------|-------|-------------|
| **1** | `retrieval/dense_retriever.py`, `retrieval/sparse_retriever.py` | Qdrant ANN dense retriever; BM25 sparse retriever with disk persistence |
| **2** | `retrieval/hybrid_retriever.py`, `retrieval/reranker.py`, `retrieval/query_decomposer.py`, `rag/advanced_chain.py` | RRF fusion, flashrank reranker, LLM query decomposition, advanced RAG chain |
| **3** | `agents/base_agent.py`, `agents/specialized/` (all 5), `agents/validator.py`, `agents/orchestrator.py` | Full multi-agent extraction framework — runs agents in parallel per document, merges into `ProductRecord` |
| **4** | `workflow/review_store.py`, `workflow/batch_runner.py` | SQLite review state; async batch runner with checkpoint/resume for 5K docs |

**Week 2 done when:** `python scripts/run_batch.py --limit 100` processes 100 documents and stores `ProductRecord`s in SQLite with >80% attribute accuracy on manual spot-check.

---

### Week 3 — Approval Workflow & Final Integration
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
│       ├── csv_parser.py         # CSV dataset files — one doc per row via file_content column
│       └── txt_parser.py         # Plain text / Markdown
├── embedding/
│   ├── embedder.py               # EmbeddingService — local (sentence-transformers) or OpenAI
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
│   ├── generate_test_docs.py     # Generate synthetic product spec docs for local testing
│   ├── ingest_sample.py          # Ingest a folder of documents into the vector store
│   ├── query_baseline.py         # Query the baseline RAG from the CLI
│   └── run_batch.py              # Run full batch extraction across all documents
├── tests/
├── data/
│   ├── raw/                      # Original documents (gitignored)
│   ├── processed/                # Intermediate artifacts (gitignored)
│   └── exports/                  # Final CSV/JSON PIM exports
├── .env
├── requirements.txt
└── pyproject.toml
```

---

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for Qdrant)

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd MDM-Advanced-RAG
uv sync
```

### 2. Configure environment variables

```bash
# Edit .env and add your API key:
#   ANTHROPIC_API_KEY=...
#
# OPENAI_API_KEY is not required — embeddings use a local model by default.
```

### 3. Start Qdrant (vector store)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

---

## Usage

### Quick start — synthetic test documents

Generate one spec doc per supported format, then run the full ingest → query loop.

```bash
# 1. Generate 5 synthetic product spec documents (PDF, DOCX, Excel, HTML, TXT)
uv run scripts/generate_test_docs.py
# Output written to data/raw/

# 2. Ingest the generated documents into the vector store
uv run scripts/ingest_sample.py --dir data/raw --reset

# 3. Ask a question against the indexed documents
uv run scripts/query_baseline.py "What is the operating temperature range for product X?"
uv run scripts/query_baseline.py "What certifications does the pressure sensor have?" --show-sources
```

### Ingesting the sample dataset

The provided CSV files contain pre-extracted document text (one row per product document).

```bash
# Copy a CSV dataset into data/raw/ then ingest normally
cp data/100_sample_advanced_rag.csv data/raw/
uv run scripts/ingest_sample.py --dir data/raw --reset
```

### Running the tests

```bash
# Full unit test suite (no API keys or Qdrant required)
uv run pytest tests/ -v
```

### Week 2 — Run batch extraction

```bash
uv run scripts/run_batch.py --limit 100 --concurrency 5
```

### Week 3 — Review and export

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Embeddings

Embeddings use a **local sentence-transformers model** (`all-MiniLM-L6-v2`, 384 dimensions) by default — no OpenAI quota required. The model (~90 MB) is downloaded automatically on first run and cached locally.

To switch to OpenAI embeddings, set in `.env`:

```
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
OPENAI_API_KEY=sk-...
```

> If switching models, run `ingest_sample.py --reset` to recreate the Qdrant collection at the correct vector size.

---

## Input Data Formats

| Format | Parser | Notes |
|--------|--------|-------|
| `.pdf` | `PDFParser` | pdfplumber with pypdf fallback; tables extracted as markdown |
| `.docx` | `DocxParser` | python-docx |
| `.xlsx` | `ExcelParser` | openpyxl, one page per sheet |
| `.html` | `HTMLParser` | BeautifulSoup, nav/footer stripped |
| `.csv` | `CsvParser` | Dataset files with a `file_content` column — one doc per row |
| `.txt` / `.md` | `TxtParser` | Plain text |

---

## PIM Attribute Schema

Each extracted attribute is an `AttributeValue` carrying the value, unit, confidence level, and source chunk IDs for traceability. Structured output is produced by the Week 2 multi-agent extraction framework.

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

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `anthropic` + `instructor` | LLM calls with enforced structured output |
| `sentence-transformers` | Local text embeddings (default, no API key needed) |
| `openai` | Optional OpenAI text embeddings |
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
| **1** | ✅ Complete | Foundation | `ingest_sample.py` + `query_baseline.py` working end-to-end |
| **2** | 🔄 In progress | Advanced extraction | `run_batch.py` on 500 docs, >80% extraction accuracy on spot-check |
| **3** | ⏳ Pending | Approval + export | Data stewards can review and export approved PIM data via Streamlit UI |
