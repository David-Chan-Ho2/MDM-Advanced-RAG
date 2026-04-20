from __future__ import annotations

import asyncio
from pathlib import Path

from config.schema import AttributeValue, MaterialsAndCompliance, ProductIdentifiers, ProductRecord
from ingestion.pipeline import IngestionPipeline
from workflow.batch_runner import BatchExtractionRunner
from workflow.review_store import ReviewStore
from workflow.sample_output import SampleOutputFormatter


class FakeEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeIndexer:
    def __init__(self):
        self.points = []

    def upsert(self, chunks, embeddings):
        self.points.extend(zip(chunks, embeddings))

    def count(self) -> int:
        return len(self.points)


class FakeSparseRetriever:
    def __init__(self):
        self.records = []

    def exists(self) -> bool:
        return bool(self.records)

    def count(self) -> int:
        return len(self.records)

    def delete_index(self) -> None:
        self.records = []

    def build_from_records(self, records):
        self.records = list(records)
        return len(self.records)


class FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def extract_document(self, document_id: str, document_filename: str, filters: dict | None = None):
        self.calls.append({"document_id": document_id, "filters": filters or {}})
        return ProductRecord(
            document_id=document_id,
            product_id=document_id,
            document_filename=document_filename,
            extraction_timestamp="2026-04-06T00:00:00+00:00",
            identifiers=ProductIdentifiers(),
        )


def test_review_store_roundtrip(tmp_path: Path):
    store = ReviewStore(db_path=tmp_path / "review.db")
    record = ProductRecord(
        document_id="widget_pro",
        document_filename="widget_pro.txt",
        extraction_timestamp="2026-04-06T00:00:00+00:00",
    )

    store.upsert_record(record)

    loaded = store.get_record("widget_pro")
    assert loaded is not None
    assert loaded.document_filename == "widget_pro.txt"
    assert store.count_by_status()["pending"] == 1


def test_batch_runner_resumes_completed_documents(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "doc1.txt").write_text("Part Number: DOC-1\nWeight: 1 kg")
    (raw_dir / "doc2.txt").write_text("Part Number: DOC-2\nWeight: 2 kg")

    review_store = ReviewStore(db_path=tmp_path / "review.db")
    runner = BatchExtractionRunner(
        raw_dir=raw_dir,
        pipeline=IngestionPipeline(),
        embedder=FakeEmbedder(),
        indexer=FakeIndexer(),
        sparse_retriever=FakeSparseRetriever(),
        orchestrator=FakeOrchestrator(),
        review_store=review_store,
    )

    first_summary = asyncio.run(runner.run(concurrency=2, resume=True))
    second_summary = asyncio.run(runner.run(concurrency=2, resume=True))

    assert first_summary["processed_documents"] == 2
    assert second_summary["processed_documents"] == 0
    assert second_summary["skipped_documents"] == 2
    assert review_store.has_record("doc1")
    assert review_store.has_record("doc2")


def test_batch_runner_processes_csv_product_targets(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "dataset.csv").write_text(
        "id,file_name,file_content,product_id\n"
        'doc-1,spec.pdf,"Part Number: ABC-1","[""P1"",""P2""]"\n'
    )

    review_store = ReviewStore(db_path=tmp_path / "review.db")
    orchestrator = FakeOrchestrator()
    runner = BatchExtractionRunner(
        raw_dir=raw_dir,
        pipeline=IngestionPipeline(),
        embedder=FakeEmbedder(),
        indexer=FakeIndexer(),
        sparse_retriever=FakeSparseRetriever(),
        orchestrator=orchestrator,
        review_store=review_store,
    )

    summary = asyncio.run(runner.run(concurrency=2, resume=True))

    assert summary["total_products"] == 2
    assert summary["processed_documents"] == 2
    assert review_store.has_record("P1")
    assert review_store.has_record("P2")
    assert all(call["filters"]["product_id"] in {"P1", "P2"} for call in orchestrator.calls)


def test_sample_output_formatter_matches_product_key_shape():
    record = ProductRecord(
        document_id="P1",
        product_id="P1",
        document_filename="spec.pdf",
        identifiers=ProductIdentifiers(
            part_number=AttributeValue(value="ABC-1"),
            manufacturer_name=AttributeValue(value="Honeywell"),
        ),
        materials_compliance=MaterialsAndCompliance(
            certifications=[
                AttributeValue(value="UL873"),
                AttributeValue(value="CE"),
            ]
        ),
    )

    formatted = SampleOutputFormatter().format_record(record)

    assert formatted == {
        "P1": [
            {"Part Number": "ABC-1"},
            {"Brand": "Honeywell"},
            {"Certificates and Standards": "UL873, CE"},
        ]
    }
