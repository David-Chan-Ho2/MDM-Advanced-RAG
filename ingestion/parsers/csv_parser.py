from __future__ import annotations

import ast
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

                source_document_id = (
                    row.get("id")
                    or row.get("p_id")
                    or f"{file_path.stem}_row{reader.line_num}"
                )
                product_ids = self._parse_product_ids(row.get("product_id"))
                if not product_ids:
                    product_ids = [source_document_id]
                filename = row.get("file_name") or f"{source_document_id}.txt"

                for product_id in product_ids:
                    metadata = {
                        k: row[k]
                        for k in (
                            "title",
                            "document_type",
                            "document_subtype",
                            "product_family",
                            "target_audience",
                            "sbg",
                            "sbe",
                            "url",
                        )
                        if row.get(k)
                    }
                    metadata.update(
                        {
                            "product_id": product_id,
                            "source_document_id": source_document_id,
                            "source_p_id": row.get("p_id"),
                            "source_row_number": reader.line_num - 1,
                            "source_file": file_path.name,
                        }
                    )

                    docs.append(
                        ParsedDocument(
                            document_id=product_id,
                            filename=filename,
                            file_format="csv",
                            pages=[ParsedPage(page_number=1, text=text)],
                            metadata=metadata,
                        )
                    )
        return docs

    @staticmethod
    def _parse_product_ids(raw_value: str | None) -> list[str]:
        raw_value = (raw_value or "").strip()
        if not raw_value:
            return []

        try:
            parsed = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError):
            parsed = raw_value

        if isinstance(parsed, str):
            values = parsed.strip("[]").split(",")
        elif isinstance(parsed, (list, tuple, set)):
            values = parsed
        else:
            values = [parsed]

        product_ids = []
        for value in values:
            product_id = str(value).strip().strip("'\"")
            if product_id:
                product_ids.append(product_id)

        return list(dict.fromkeys(product_ids))
