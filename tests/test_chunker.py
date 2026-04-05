"""Tests for DocumentChunker."""

import pytest
from ingestion.chunker import DocumentChunker, Chunk
from ingestion.parsers.base import ParsedDocument, ParsedPage


def make_doc(text: str, tables: list[str] | None = None) -> ParsedDocument:
    return ParsedDocument(
        document_id="test_doc",
        filename="test_doc.txt",
        file_format="txt",
        pages=[ParsedPage(page_number=1, text=text, tables=tables or [])],
    )


class TestDocumentChunker:
    def setup_method(self):
        self.chunker = DocumentChunker(chunk_size=200, chunk_overlap=20)

    def test_returns_list_of_chunks(self):
        doc = make_doc("This is a short product spec. " * 5)
        chunks = self.chunker.chunk(doc)
        assert isinstance(chunks, list)
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_ids_are_unique(self):
        doc = make_doc("word " * 300)
        chunks = self.chunker.chunk(doc)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_metadata_populated(self):
        doc = make_doc("word " * 100)
        chunks = self.chunker.chunk(doc)
        for chunk in chunks:
            assert chunk.document_id == "test_doc"
            assert chunk.filename == "test_doc.txt"
            assert chunk.file_format == "txt"
            assert chunk.page_number == 1

    def test_chunk_index_sequential(self):
        doc = make_doc("word " * 300)
        chunks = self.chunker.chunk(doc)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_doc_returns_no_chunks(self):
        doc = make_doc("   ")
        chunks = self.chunker.chunk(doc)
        assert chunks == []

    def test_table_content_included(self):
        doc = make_doc("Spec sheet intro.", tables=["| Col1 | Col2 |\n|---|---|\n| IP67 | 24V |"])
        chunks = self.chunker.chunk(doc)
        all_text = " ".join(c.text for c in chunks)
        assert "IP67" in all_text

    def test_long_text_produces_multiple_chunks(self):
        doc = make_doc("word " * 500)
        chunks = self.chunker.chunk(doc)
        assert len(chunks) > 1

    def test_payload_contains_required_keys(self):
        doc = make_doc("test content " * 10)
        chunks = self.chunker.chunk(doc)
        required_keys = {"chunk_id", "document_id", "filename", "file_format", "page_number", "chunk_index", "text"}
        for chunk in chunks:
            assert required_keys.issubset(chunk.to_payload().keys())
