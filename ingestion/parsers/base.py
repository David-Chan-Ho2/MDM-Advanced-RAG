from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    page_number: int
    text: str
    tables: list[str] = field(default_factory=list)  # each table as markdown string


@dataclass
class ParsedDocument:
    document_id: str       # stem of filename, e.g. "product_abc"
    filename: str          # original filename with extension
    file_format: str       # "pdf", "docx", "xlsx", "html", "txt"
    pages: list[ParsedPage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def full_text(self) -> str:
        """Concatenate all page text and tables into a single string."""
        parts = []
        for page in self.pages:
            if page.text.strip():
                parts.append(page.text)
            for table in page.tables:
                parts.append(table)
        return "\n\n".join(parts)


class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Return True if this parser handles the given file."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse file and return a ParsedDocument."""
