from __future__ import annotations

from pathlib import Path

from loguru import logger
from tqdm import tqdm

from ingestion.chunker import Chunk, DocumentChunker
from ingestion.parsers.base import BaseParser
from ingestion.parsers.pdf_parser import PDFParser
from ingestion.parsers.docx_parser import DocxParser
from ingestion.parsers.excel_parser import ExcelParser
from ingestion.parsers.html_parser import HTMLParser
from ingestion.parsers.txt_parser import TxtParser

_DEFAULT_PARSERS: list[BaseParser] = [
    PDFParser(),
    DocxParser(),
    ExcelParser(),
    HTMLParser(),
    TxtParser(),
]


class IngestionPipeline:
    def __init__(
        self,
        parsers: list[BaseParser] | None = None,
        chunker: DocumentChunker | None = None,
    ):
        self.parsers = parsers or _DEFAULT_PARSERS
        self.chunker = chunker or DocumentChunker()

    def process_file(self, file_path: Path) -> list[Chunk]:
        parser = self._select_parser(file_path)
        if parser is None:
            logger.warning(f"No parser found for {file_path.name} — skipping.")
            return []
        try:
            doc = parser.parse(file_path)
            chunks = self.chunker.chunk(doc)
            logger.debug(f"{file_path.name}: {len(chunks)} chunks")
            return chunks
        except Exception as exc:
            logger.error(f"Failed to process {file_path.name}: {exc}")
            return []

    def process_directory(self, directory: Path, show_progress: bool = True) -> list[Chunk]:
        files = [f for f in directory.rglob("*") if f.is_file()]
        all_chunks: list[Chunk] = []
        iterator = tqdm(files, desc="Ingesting documents") if show_progress else files
        for file_path in iterator:
            chunks = self.process_file(file_path)
            all_chunks.extend(chunks)
        logger.info(f"Ingestion complete: {len(files)} files → {len(all_chunks)} chunks")
        return all_chunks

    def _select_parser(self, file_path: Path) -> BaseParser | None:
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None
