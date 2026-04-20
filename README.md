# MDM Advanced RAG - Product Attribute Extraction Pipeline

An Advanced RAG pipeline that ingests product specification documents, extracts structured technical attributes using LLMs, and outputs PIM-ready data through a data steward approval workflow.

## Overview

Product technical specifications arrive in inconsistent formats such as PDF, DOCX, Excel, HTML, TXT, and CSV. This project automates extraction across a full-scale dataset of roughly 5,000 documents using hybrid retrieval, re-ranking, and a multi-agent extraction framework.

The Week 2 branch has now been merged into `week-3`, so this branch has the full Week 2 retrieval and extraction foundation needed for Week 3 approval workflow work.

```text
Documents -> Parse -> Product-ID Grouping -> Chunk -> Embed -> Vector Store
                                                 |
Query/Product -> Hybrid Retrieval -> Re-rank -> Multi-Agent Extraction
                                                 |
Validation -> ProductRecord -> Review Store -> Steward UI -> PIM Export
```

## Project Status

| Week | Status | Goal | Acceptance Criteria |
|------|--------|------|---------------------|
| 1 | Complete | Foundation document processing and baseline RAG | `ingest_sample.py` and `query_baseline.py` work end to end |
| 2 | Complete | Advanced retrieval and multi-agent extraction | Hybrid search, re-ranking, product-level extraction, orchestration, and full-scale ingestion validation |
| 3 | Ready / In progress | Approval workflow and final integration | Data stewards can review, approve/edit/reject, and export approved PIM data |

## Week 2 Deliverables

The Week 2 implementation includes the required advanced RAG and extraction work:

| Area | Files | Deliverable |
|------|-------|-------------|
| Product-level ingestion | `ingestion/parsers/csv_parser.py`, `ingestion/chunker.py`, `ingestion/pipeline.py` | CSV rows are exploded and indexed by individual `product_id`, with source document tracing preserved |
| Dense + sparse retrieval | `retrieval/dense_retriever.py`, `retrieval/sparse_retriever.py` | Qdrant dense retrieval plus persisted BM25 sparse retrieval |
| Hybrid retrieval and re-ranking | `retrieval/hybrid_retriever.py`, `retrieval/reranker.py`, `retrieval/query_decomposer.py`, `rag/advanced_chain.py` | RRF fusion, optional Flashrank re-ranking, metadata filtering, and query decomposition |
| Multi-agent extraction | `agents/base_agent.py`, `agents/specialized/`, `agents/validator.py`, `agents/orchestrator.py` | Specialized extraction agents route, merge, validate, and normalize technical attributes |
| Batch workflow | `workflow/review_store.py`, `workflow/batch_runner.py`, `scripts/run_batch.py` | Async batch extraction with checkpoint/resume and review-store writes |
| Output formatting | `workflow/sample_output.py` | Final sample-style JSON output layer while preserving internal confidence/source tracing |
| Scale validation | `scripts/validate_ingestion.py` | Confirms the full dataset can be parsed, chunked, and grouped into product targets |

## Week 1 Feedback Addressed

The instructor feedback from Week 1 has been incorporated into the Week 2 foundation:

| Feedback | Implementation |
|----------|----------------|
| Product-ID grouping | CSV documents are exploded/indexed by individual `product_id` instead of only `document_id` |
| Scale ingestion | `scripts/validate_ingestion.py --dir data --expected-products 5000` validates full dataset parse/chunk/product coverage |
| Output format | `workflow/sample_output.py` provides a final JSON-style output shape compatible with the sample format |

## Project Structure

```text
config/
  settings.py                 Project constants, model names, vector-store settings
  schema.py                   PIM Pydantic models
ingestion/
  pipeline.py                 Parser selection and chunk generation
  chunker.py                  Recursive text chunking with stable source-aware chunk IDs
  parsers/                    PDF, DOCX, Excel, HTML, CSV, TXT parsers
embedding/
  embedder.py                 Local sentence-transformer embeddings by default, OpenAI optional
  indexer.py                  Qdrant collection creation, upsert, and search
retrieval/
  dense_retriever.py          Qdrant ANN dense retriever
  sparse_retriever.py         BM25 sparse retriever with disk persistence
  hybrid_retriever.py         Dense/sparse fusion
  reranker.py                 Flashrank when available, lexical fallback otherwise
  query_decomposer.py         LLM-assisted sub-query generation
rag/
  chain.py                    Baseline Week 1 RAG chain
  advanced_chain.py           Week 2 hybrid/re-ranked RAG chain
agents/
  base_agent.py               Agent base classes and result model
  specialized/                Identifier, dimension, electrical, materials, performance agents
  orchestrator.py             Agent routing and merge orchestration
  validator.py                Cross-agent validation and normalization
workflow/
  review_store.py             SQLite approval/review state
  batch_runner.py             Async product extraction runner
  sample_output.py            Sample-compatible JSON formatter
  exporter.py                 Week 3 PIM CSV/JSON exporter
ui/
  app.py                      Streamlit review app
  pages/                      Review queue, approved records, export pages
scripts/
  ingest_sample.py            Ingest documents into Qdrant/BM25
  query_baseline.py           Baseline RAG query CLI
  run_batch.py                Batch extraction CLI
  validate_ingestion.py       Full-scale ingestion validation
tests/
  test_*.py                   Unit tests for ingestion, retrieval, agents, workflow, exports
```

## Setup

### Prerequisites

- Python 3.12+
- Qdrant running locally for vector search
- Anthropic API key for LLM extraction

### Install Dependencies

```bash
python -m pip install -e ".[dev]"
```

### Configure Environment

Create or update `.env`:

```bash
ANTHROPIC_API_KEY=your_key_here
```

Embeddings use the local `all-MiniLM-L6-v2` model by default. To use OpenAI embeddings instead:

```bash
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
OPENAI_API_KEY=your_key_here
```

### Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## Usage

### Generate and Ingest Sample Documents

```bash
python scripts/generate_test_docs.py
python scripts/ingest_sample.py --dir data/raw --reset
```

### Query the Baseline RAG Chain

```bash
python scripts/query_baseline.py "What is the operating temperature range?"
python scripts/query_baseline.py "What certifications does this product have?" --show-sources
```

### Validate Full-Scale Ingestion

```bash
python scripts/validate_ingestion.py --dir data --expected-products 5000
```

This parses supported files, chunks the documents, and reports unique product targets discovered from `product_id` metadata.

### Run Week 2 Batch Extraction

```bash
python scripts/run_batch.py --dir data --limit 100 --concurrency 5
```

This requires Qdrant on `localhost:6333` and writes product records to the SQLite review store.

### Launch Week 3 Review UI

```bash
streamlit run ui/app.py
```

Open `http://localhost:8501` to approve, edit, reject, and export product records.

## PIM Attribute Schema

Each extracted attribute is represented as an `AttributeValue` with:

- `value`
- `unit`
- `confidence`
- `source_chunk_ids`
- `source_text`

The main `ProductRecord` groups attributes into:

| Group | Attributes |
|-------|------------|
| Identifiers | part_number, sku, gtin, manufacturer_name, product_family, revision |
| Physical dimensions | length, width, height, depth, weight, diameter |
| Electrical specs | voltage_input, voltage_output, current_rating, power_consumption, frequency, ip_rating |
| Materials and compliance | primary_material, finish, rohs_compliant, reach_compliant, certifications |
| Performance metrics | operating_temp_min/max, storage_temp_min/max, accuracy, flow_rate, pressure_rating |

`workflow/sample_output.py` can format approved records into the sample JSON-style output while the internal workflow preserves confidence scores and source tracing for review.

## Testing

```bash
python -m pytest -q
python -m ruff check .
```

The `run_batch.py` acceptance command requires Qdrant. Unit tests and linting do not require external services.
