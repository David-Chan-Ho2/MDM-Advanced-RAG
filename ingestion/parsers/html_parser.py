from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedPage

# Tags that typically don't contain product content
_NOISE_TAGS = {"nav", "footer", "header", "script", "style", "aside", "noscript"}


def _table_to_markdown(table) -> str:
    rows = []
    for i, tr in enumerate(table.find_all("tr")):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if not cells:
            continue
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


class HTMLParser(BaseParser):
    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in {".html", ".htm"}

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise RuntimeError("beautifulsoup4 is required: pip install beautifulsoup4")

        html = file_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()

        tables = []
        for tbl in soup.find_all("table"):
            md = _table_to_markdown(tbl)
            if md:
                tables.append(md)
            tbl.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return ParsedDocument(
            document_id=file_path.stem,
            filename=file_path.name,
            file_format="html",
            pages=[ParsedPage(page_number=1, text=text, tables=tables)],
            metadata={"table_count": len(tables)},
        )
