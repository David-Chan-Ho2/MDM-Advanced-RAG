"""
Validate document ingestion without calling embedding or LLM services.

Usage:
    python scripts/validate_ingestion.py --dir data
    python scripts/validate_ingestion.py --dir data --expected-products 5000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from config.settings import settings
from ingestion.pipeline import IngestionPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ingestion coverage and product grouping.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=settings.RAW_DATA_DIR,
        help="Directory containing source documents or CSV datasets",
    )
    parser.add_argument(
        "--expected-products",
        type=int,
        default=None,
        help="Optional expected unique product count, e.g. 5000",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.dir.exists():
        logger.error(f"Directory not found: {args.dir}")
        sys.exit(1)

    pipeline = IngestionPipeline()
    files = [
        path
        for path in args.dir.rglob("*")
        if path.is_file() and any(parser.can_parse(path) for parser in pipeline.parsers)
    ]
    chunks = pipeline.process_directory(args.dir, show_progress=True)
    product_ids = {
        chunk.metadata.get("product_id") or chunk.document_id
        for chunk in chunks
        if chunk.metadata.get("product_id") or chunk.document_id
    }

    logger.info(f"Parseable files: {len(files)}")
    logger.info(f"Chunks produced: {len(chunks)}")
    logger.info(f"Unique product targets: {len(product_ids)}")

    if args.expected_products is not None and len(product_ids) < args.expected_products:
        logger.error(
            f"Expected at least {args.expected_products} products, found {len(product_ids)}"
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
