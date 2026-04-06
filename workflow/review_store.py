from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from config.schema import ProductRecord
from config.settings import settings


class ReviewStore:
    """SQLite persistence for extracted ProductRecords and review state."""

    def __init__(self, db_path: str | Path = settings.REVIEW_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def upsert_record(self, record: ProductRecord) -> None:
        payload_json = json.dumps(record.model_dump(mode="json"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO extractions (
                    document_id,
                    document_filename,
                    review_status,
                    extraction_timestamp,
                    payload_json,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(document_id) DO UPDATE SET
                    document_filename = excluded.document_filename,
                    review_status = excluded.review_status,
                    extraction_timestamp = excluded.extraction_timestamp,
                    payload_json = excluded.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    record.document_id,
                    record.document_filename,
                    record.review_status,
                    record.extraction_timestamp,
                    payload_json,
                ),
            )
            conn.commit()

    def has_record(self, document_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM extractions WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return row is not None

    def get_record(self, document_id: str) -> ProductRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM extractions WHERE document_id = ?",
                (document_id,),
            ).fetchone()

        if row is None:
            return None
        return ProductRecord.model_validate(json.loads(row["payload_json"]))

    def list_records(
        self,
        review_status: str | None = None,
        limit: int | None = None,
    ) -> list[ProductRecord]:
        query = "SELECT payload_json FROM extractions"
        params: list = []

        if review_status:
            query += " WHERE review_status = ?"
            params.append(review_status)

        query += " ORDER BY updated_at DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            ProductRecord.model_validate(json.loads(row["payload_json"]))
            for row in rows
        ]

    def list_processed_document_ids(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT document_id FROM extractions").fetchall()
        return {row["document_id"] for row in rows}

    def count_by_status(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT review_status, COUNT(*) AS total FROM extractions GROUP BY review_status"
            ).fetchall()
        return {row["review_status"]: row["total"] for row in rows}

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS extractions (
                    document_id TEXT PRIMARY KEY,
                    document_filename TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    extraction_timestamp TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_extractions_status ON extractions(review_status)"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
