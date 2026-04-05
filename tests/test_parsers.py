"""Tests for document parsers."""

import pytest
from pathlib import Path

from ingestion.parsers.txt_parser import TxtParser
from ingestion.parsers.docx_parser import DocxParser
from ingestion.parsers.excel_parser import ExcelParser
from ingestion.parsers.html_parser import HTMLParser
from ingestion.parsers.base import ParsedDocument


# ---------------------------------------------------------------------------
# TxtParser
# ---------------------------------------------------------------------------

class TestTxtParser:
    def setup_method(self):
        self.parser = TxtParser()

    def test_can_parse_txt(self, tmp_txt):
        assert self.parser.can_parse(tmp_txt)

    def test_cannot_parse_pdf(self, tmp_path):
        assert not self.parser.can_parse(tmp_path / "file.pdf")

    def test_returns_parsed_document(self, tmp_txt):
        doc = self.parser.parse(tmp_txt)
        assert isinstance(doc, ParsedDocument)
        assert doc.file_format == "txt"
        assert doc.filename == "sample.txt"

    def test_text_contains_content(self, tmp_txt):
        doc = self.parser.parse(tmp_txt)
        assert "Widget Pro" in doc.full_text()
        assert "WP-1234" in doc.full_text()

    def test_single_page(self, tmp_txt):
        doc = self.parser.parse(tmp_txt)
        assert len(doc.pages) == 1


# ---------------------------------------------------------------------------
# DocxParser
# ---------------------------------------------------------------------------

class TestDocxParser:
    def setup_method(self):
        self.parser = DocxParser()

    def test_can_parse_docx(self, tmp_docx):
        assert self.parser.can_parse(tmp_docx)

    def test_returns_parsed_document(self, tmp_docx):
        doc = self.parser.parse(tmp_docx)
        assert isinstance(doc, ParsedDocument)
        assert doc.file_format == "docx"

    def test_text_contains_paragraphs(self, tmp_docx):
        doc = self.parser.parse(tmp_docx)
        assert "WP-1234" in doc.full_text()

    def test_tables_extracted_as_markdown(self, tmp_docx):
        doc = self.parser.parse(tmp_docx)
        full = doc.full_text()
        assert "IP67" in full
        assert "|" in full  # markdown table


# ---------------------------------------------------------------------------
# ExcelParser
# ---------------------------------------------------------------------------

class TestExcelParser:
    def setup_method(self):
        self.parser = ExcelParser()

    def test_can_parse_xlsx(self, tmp_xlsx):
        assert self.parser.can_parse(tmp_xlsx)

    def test_returns_parsed_document(self, tmp_xlsx):
        doc = self.parser.parse(tmp_xlsx)
        assert isinstance(doc, ParsedDocument)
        assert doc.file_format == "xlsx"

    def test_sheet_content_present(self, tmp_xlsx):
        doc = self.parser.parse(tmp_xlsx)
        full = doc.full_text()
        assert "150" in full
        assert "2.5" in full

    def test_one_page_per_sheet(self, tmp_xlsx):
        doc = self.parser.parse(tmp_xlsx)
        assert len(doc.pages) == 1  # fixture has one sheet


# ---------------------------------------------------------------------------
# HTMLParser
# ---------------------------------------------------------------------------

class TestHTMLParser:
    def setup_method(self):
        self.parser = HTMLParser()

    def test_can_parse_html(self, tmp_html):
        assert self.parser.can_parse(tmp_html)

    def test_returns_parsed_document(self, tmp_html):
        doc = self.parser.parse(tmp_html)
        assert isinstance(doc, ParsedDocument)
        assert doc.file_format == "html"

    def test_nav_stripped(self, tmp_html):
        doc = self.parser.parse(tmp_html)
        assert "Nav content to ignore" not in doc.full_text()

    def test_table_extracted_as_markdown(self, tmp_html):
        doc = self.parser.parse(tmp_html)
        full = doc.full_text()
        assert "IP67" in full
        assert "|" in full

    def test_body_text_present(self, tmp_html):
        doc = self.parser.parse(tmp_html)
        assert "WP-1234" in doc.full_text()
