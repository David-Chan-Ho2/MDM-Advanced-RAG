from pathlib import Path
from .base import BaseParser, ParsedDocument, ParsedPage


class TxtParser(BaseParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in {".txt", ".text", ".md"}

    def parse(self, file_path: Path) -> ParsedDocument:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return ParsedDocument(
            document_id=file_path.stem,
            filename=file_path.name,
            file_format="txt",
            pages=[ParsedPage(page_number=1, text=text)],
            metadata={"file_size_bytes": file_path.stat().st_size},
        )
