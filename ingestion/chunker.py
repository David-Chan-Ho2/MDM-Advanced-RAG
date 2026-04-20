from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings
from ingestion.parsers.base import ParsedDocument


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    filename: str
    file_format: str
    page_number: int
    chunk_index: int
    text: str
    metadata: dict = field(default_factory=dict)

    def to_payload(self) -> dict:
        """Qdrant payload dict — everything except the text vector."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "filename": self.filename,
            "file_format": self.file_format,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "text": self.text,
            **self.metadata,
        }


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0

        for page in doc.pages:
            # Combine page text and tables into one block for this page
            page_parts = []
            if page.text.strip():
                page_parts.append(page.text)
            for table in page.tables:
                page_parts.append(table)
            page_text = "\n\n".join(page_parts)

            if not page_text.strip():
                continue

            splits = self._splitter.split_text(page_text)
            for split in splits:
                if not split.strip():
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=self._make_chunk_id(
                            document_id=doc.document_id,
                            source_key=(
                                doc.metadata.get("source_document_id")
                                or doc.metadata.get("source_path")
                                or doc.filename
                            ),
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                        ),
                        document_id=doc.document_id,
                        filename=doc.filename,
                        file_format=doc.file_format,
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        text=split,
                        metadata=dict(doc.metadata),
                    )
                )
                chunk_index += 1

        return chunks

    @staticmethod
    def _make_chunk_id(
        document_id: str,
        source_key: str,
        page_number: int,
        chunk_index: int,
    ) -> str:
        seed = f"{document_id}:{source_key}:{page_number}:{chunk_index}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
