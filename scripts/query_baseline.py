"""
Query the baseline RAG system from the CLI.

Usage:
    python scripts/query_baseline.py "What is the operating temperature range?"
    python scripts/query_baseline.py "What certifications does product X have?" --top-k 8
    python scripts/query_baseline.py "..." --doc-id product_abc   # filter to one document
"""

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.chain import BaseRAGChain


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the baseline RAG pipeline.")
    parser.add_argument("question", type=str, help="The question to ask")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Number of chunks to retrieve (default: 5)")
    parser.add_argument("--doc-id", type=str, default=None,
                        help="Restrict retrieval to a single document ID")
    parser.add_argument("--show-sources", action="store_true",
                        help="Print retrieved source chunks after the answer")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    chain = BaseRAGChain(top_k=args.top_k)

    filters = {"document_id": args.doc_id} if args.doc_id else None
    result = chain.query(args.question, filters=filters)

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(result["answer"])

    if args.show_sources:
        print("\n" + "=" * 60)
        print(f"SOURCES ({len(result['sources'])} chunks)")
        print("=" * 60)
        for i, src in enumerate(result["sources"], start=1):
            print(f"\n[{i}] {src['filename']} — page {src['page_number']}  (score: {src['score']})")
            print(src["text"])


if __name__ == "__main__":
    main()
