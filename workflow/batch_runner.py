from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from agents.orchestrator import ExtractionOrchestrator
from config.settings import settings
from embedding.embedder import EmbeddingService
from embedding.indexer import VectorIndexer
from ingestion.pipeline import IngestionPipeline
from retrieval.sparse_retriever import SparseRetriever
from workflow.review_store import ReviewStore


class BatchExtractionRunner:
    """Indexes documents when needed, extracts records, and checkpoints to SQLite."""

    def __init__(
        self,
        raw_dir: Path | str = settings.RAW_DATA_DIR,
        pipeline: IngestionPipeline | None = None,
        embedder: EmbeddingService | None = None,
        indexer: VectorIndexer | None = None,
        sparse_retriever: SparseRetriever | None = None,
        orchestrator: ExtractionOrchestrator | None = None,
        review_store: ReviewStore | None = None,
    ):
        self.raw_dir = Path(raw_dir)
        self.pipeline = pipeline or IngestionPipeline()
        self.embedder = embedder or EmbeddingService()
        self.indexer = indexer or VectorIndexer()
        self.sparse_retriever = sparse_retriever or SparseRetriever()
        self.orchestrator = orchestrator or ExtractionOrchestrator()
        self.review_store = review_store or ReviewStore()

    async def run(
        self,
        *,
        limit: int | None = None,
        concurrency: int = settings.BATCH_CONCURRENCY,
        resume: bool = True,
        force_reindex: bool = False,
    ) -> dict:
        files = self._discover_files()
        if not files:
            return {
                "total_documents": 0,
                "total_products": 0,
                "queued_documents": 0,
                "processed_documents": 0,
                "skipped_documents": 0,
                "failed_documents": 0,
            }

        await asyncio.to_thread(self._ensure_indexes, files, force_reindex)

        targets = self._build_targets(files=files, limit=limit)
        processed_ids = self.review_store.list_processed_document_ids() if resume else set()
        pending_targets = [
            target for target in targets if target["document_id"] not in processed_ids
        ]

        summary = {
            "total_documents": len(targets),
            "total_products": len(targets),
            "indexed_files": len(files),
            "queued_documents": len(pending_targets),
            "processed_documents": 0,
            "skipped_documents": len(targets) - len(pending_targets),
            "failed_documents": 0,
        }

        semaphore = asyncio.Semaphore(max(concurrency, 1))

        async def run_one(target: dict):
            async with semaphore:
                return await asyncio.to_thread(self._process_target, target)

        results = await asyncio.gather(
            *(run_one(target) for target in pending_targets),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                summary["failed_documents"] += 1
                logger.exception(f"Batch extraction failed: {result}")
                continue

            if result["status"] == "processed":
                summary["processed_documents"] += 1
            else:
                summary["failed_documents"] += 1

        return summary

    def _discover_files(self) -> list[Path]:
        if not self.raw_dir.exists():
            logger.warning(f"Raw data directory not found: {self.raw_dir}")
            return []

        files = [
            path
            for path in self.raw_dir.rglob("*")
            if path.is_file() and any(parser.can_parse(path) for parser in self.pipeline.parsers)
        ]
        files.sort()
        return files

    def _build_targets(self, files: list[Path], limit: int | None = None) -> list[dict]:
        records_attr = getattr(self.sparse_retriever, "records", None)
        if callable(records_attr):
            records = records_attr()
        elif isinstance(records_attr, list):
            records = list(records_attr)
        else:
            records = []

        targets: dict[str, dict] = {}
        for record in records:
            product_id = record.get("product_id") or record.get("document_id")
            if not product_id:
                continue

            document_id = str(product_id)
            target = targets.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "document_filename": record.get("filename") or f"{document_id}.txt",
                    "filters": {"document_id": document_id},
                    "source_document_ids": set(),
                },
            )

            if record.get("product_id"):
                target["filters"]["product_id"] = document_id
            if record.get("source_document_id"):
                target["source_document_ids"].add(str(record["source_document_id"]))

        if not targets:
            for file_path in files:
                document_id = file_path.stem
                targets[document_id] = {
                    "document_id": document_id,
                    "document_filename": file_path.name,
                    "filters": {"document_id": document_id},
                    "source_document_ids": set(),
                }

        ordered_targets = []
        for target in targets.values():
            target["source_document_ids"] = sorted(target["source_document_ids"])
            ordered_targets.append(target)

        ordered_targets.sort(key=lambda item: item["document_id"])
        return ordered_targets[:limit] if limit is not None else ordered_targets

    def _ensure_indexes(self, files: list[Path], force_reindex: bool = False) -> None:
        dense_ready = False
        sparse_ready = self.sparse_retriever.exists() or self.sparse_retriever.count() > 0

        try:
            dense_ready = self.indexer.count() > 0
        except Exception as exc:
            logger.warning(f"Dense index not ready yet: {exc}")

        if force_reindex:
            self.sparse_retriever.delete_index()
            if isinstance(self.indexer, VectorIndexer):
                try:
                    self.indexer.delete_collection()
                    self.indexer = VectorIndexer()
                except Exception as exc:
                    logger.warning(f"Could not reset dense collection cleanly: {exc}")
            elif hasattr(self.indexer, "points"):
                self.indexer.points = []
            dense_ready = False
            sparse_ready = False

        if dense_ready and sparse_ready:
            logger.info("Dense and sparse indexes already available; skipping rebuild.")
            return

        self._build_indexes(files)

    def _build_indexes(self, files: list[Path]) -> None:
        sparse_records: list[dict] = []
        chunk_buffer = []
        flush_size = settings.INDEX_FLUSH_BATCH_SIZE

        logger.info(f"Building indexes for {len(files)} documents")

        for file_path in files:
            chunks = self.pipeline.process_file(file_path)
            sparse_records.extend(chunk.to_payload() for chunk in chunks)
            chunk_buffer.extend(chunks)

            while len(chunk_buffer) >= flush_size:
                self._flush_chunk_batch(chunk_buffer[:flush_size])
                chunk_buffer = chunk_buffer[flush_size:]

        if chunk_buffer:
            self._flush_chunk_batch(chunk_buffer)

        self.sparse_retriever.build_from_records(sparse_records)

    def _flush_chunk_batch(self, chunks: list) -> None:
        if not chunks:
            return
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_texts(texts)
        self.indexer.upsert(chunks, embeddings)

    def _process_target(self, target: dict) -> dict:
        document_id = target["document_id"]
        try:
            record = self.orchestrator.extract_document(
                document_id=document_id,
                document_filename=target["document_filename"],
                filters=target.get("filters"),
            )
            self.review_store.upsert_record(record)
            return {"status": "processed", "document_id": document_id}
        except Exception as exc:
            logger.exception(f"Failed to process {document_id}: {exc}")
            return {"status": "failed", "document_id": document_id, "error": str(exc)}
