"""
Ingest documents from a directory into the vector store.

Usage:
    python scripts/ingest_sample.py --dir data/raw
    python scripts/ingest_sample.py --dir data/raw --limit 20
    python scripts/ingest_sample.py --dir data/raw --reset
"""

import argparse
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from tqdm import tqdm

from config.settings import settings
from embedding.embedder import EmbeddingService
from embedding.indexer import VectorIndexer
from ingestion.chunker import Chunk
from ingestion.pipeline import IngestionPipeline
from retrieval.sparse_retriever import SparseRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest documents into the vector store.")
    parser.add_argument("--dir", type=Path, default=settings.RAW_DATA_DIR,
                        help="Directory containing source documents")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of files to process (useful for testing)")
    parser.add_argument("--reset", action="store_true",
                        help="Delete and recreate the Qdrant collection before ingesting")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.dir.exists():
        logger.error(f"Directory not found: {args.dir}")
        sys.exit(1)

    # --- Setup ---
    pipeline = IngestionPipeline()
    embedder = EmbeddingService()
    indexer = VectorIndexer()
    sparse_retriever = SparseRetriever()

    if args.reset:
        logger.warning("--reset: deleting existing collection")
        indexer.delete_collection()
        indexer = VectorIndexer()  # recreate
        sparse_retriever.delete_index()

    # --- Collect files ---
    all_files = [f for f in args.dir.rglob("*") if f.is_file()]
    if args.limit:
        all_files = all_files[: args.limit]
    logger.info(f"Processing {len(all_files)} files from {args.dir}")

    # --- Ingest ---
    all_chunks: list[Chunk] = []
    for file_path in tqdm(all_files, desc="Parsing"):
        chunks = pipeline.process_file(file_path)
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("No chunks produced — check that documents are readable.")
        return

    logger.info(f"Total chunks: {len(all_chunks)}")

    sparse_retriever.build_from_chunks(all_chunks)

    # --- Embed and index in batches ---
    batch_size = settings.INDEX_FLUSH_BATCH_SIZE
    for i in tqdm(range(0, len(all_chunks), batch_size), desc="Embedding & indexing"):
        batch = all_chunks[i : i + batch_size]
        texts = [c.text for c in batch]
        embeddings = embedder.embed_texts(texts)
        indexer.upsert(batch, embeddings)

    logger.info(f"Done. {indexer.count()} total vectors in '{settings.QDRANT_COLLECTION}'.")
    logger.info(f"Sparse index persisted to {sparse_retriever.index_path}.")


if __name__ == "__main__":
    main()
