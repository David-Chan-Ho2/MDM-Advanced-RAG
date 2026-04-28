"""
Run the Week 2 batch extraction pipeline with checkpoint/resume support.

Usage:
    python scripts/run_batch.py --limit 100
    python scripts/run_batch.py --concurrency 5
    python scripts/run_batch.py --dir data/raw --reindex
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from config.settings import settings
from workflow.batch_runner import BatchExtractionRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch extraction across product documents.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=settings.RAW_DATA_DIR,
        help="Directory containing source documents",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of documents to process",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=settings.BATCH_CONCURRENCY,
        help="Number of documents to process concurrently",
    )
    parser.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        help="Skip documents already stored in SQLite (default)",
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Process all discovered documents, even if they already exist in SQLite",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Rebuild dense and sparse indexes before extraction",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write the extracted JSON output (e.g. data/extraction_output.json)",
    )
    parser.set_defaults(resume=True)
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> dict:
    runner = BatchExtractionRunner(raw_dir=args.dir)
    return await runner.run(
        limit=args.limit,
        concurrency=args.concurrency,
        resume=args.resume,
        force_reindex=args.reindex,
        output_path=args.output,
    )


def main() -> None:
    args = parse_args()

    if not args.dir.exists():
        logger.error(f"Directory not found: {args.dir}")
        sys.exit(1)

    summary = asyncio.run(_run(args))
    logger.info(
        "Batch extraction summary: "
        f"total={summary['total_documents']} "
        f"queued={summary['queued_documents']} "
        f"processed={summary['processed_documents']} "
        f"skipped={summary['skipped_documents']} "
        f"failed={summary['failed_documents']}"
    )


if __name__ == "__main__":
    main()
