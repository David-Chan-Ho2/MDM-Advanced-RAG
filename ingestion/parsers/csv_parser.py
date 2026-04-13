from __future__ import annotations

import csv
from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedPage


class CsvParser(BaseParser):
    """
    Parses CSV dataset files where each row is a separate product document.

    Expects a `file_content` column containing the document text.
    Optional metadata columns: id, title, file_name, document_type,
    document_subtype, product_family, product_id.
    """

    _REQUIRED_COLUMN = "file_content"

    def can_parse(self, file_path: Path) -> bool:
        if file_path.suffix.lower() != ".csv":
            return False
        # Peek at the header to confirm it's a document dataset CSV
        try:
            with file_path.open(encoding="utf-8", errors="replace") as f:
                header = f.readline()
            return self._REQUIRED_COLUMN in header
        except OSError:
            return False

    def parse(self, file_path: Path) -> ParsedDocument:
        # Fallback for the single-doc interface: return first row only
        docs = self.parse_many(file_path)
        if not docs:
            raise ValueError(f"No parseable rows found in {file_path.name}")
        return docs[0]

    def parse_many(self, file_path: Path) -> list[ParsedDocument]:
        docs: list[ParsedDocument] = []
        with file_path.open(encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = (row.get("file_content") or "").strip()
                if not text:
                    continue

                doc_id = (
                    row.get("id")
                    or row.get("p_id")
                    or f"{file_path.stem}_row{reader.line_num}"
                )
                filename = row.get("file_name") or f"{doc_id}.txt"

                metadata = {
                    k: row[k]
                    for k in ("title", "document_type", "document_subtype",
                              "product_family", "product_id", "url")
                    if row.get(k)
                }

                docs.append(ParsedDocument(
                    document_id=doc_id,
                    filename=filename,
                    file_format="csv",
                    pages=[ParsedPage(page_number=1, text=text)],
                    metadata=metadata,
                ))
        return docs
