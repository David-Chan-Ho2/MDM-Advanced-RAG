from pathlib import Path

from loguru import logger

from .base import BaseParser, ParsedDocument, ParsedPage


def _table_to_markdown(table: list[list[str | None]]) -> str:
    """Convert a pdfplumber table (list of rows) to a markdown string."""
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(cell or "").replace("\n", " ").strip() for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


class PDFParser(BaseParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("pdfplumber is required: pip install pdfplumber")

        pages: list[ParsedPage] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    tables = []
                    for raw_table in page.extract_tables():
                        md = _table_to_markdown(raw_table)
                        if md:
                            tables.append(md)
                    pages.append(ParsedPage(page_number=i, text=text, tables=tables))
        except Exception as exc:
            logger.warning(f"pdfplumber failed for {file_path.name}: {exc}. Falling back to pypdf.")
            pages = self._fallback_pypdf(file_path)

        return ParsedDocument(
            document_id=file_path.stem,
            filename=file_path.name,
            file_format="pdf",
            pages=pages,
            metadata={"page_count": len(pages)},
        )

    def _fallback_pypdf(self, file_path: Path) -> list[ParsedPage]:
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("pypdf is required: pip install pypdf")

        reader = PdfReader(str(file_path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(ParsedPage(page_number=i, text=text))
        return pages
