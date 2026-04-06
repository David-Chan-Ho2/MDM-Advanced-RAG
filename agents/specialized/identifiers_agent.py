from __future__ import annotations

from agents.base_agent import BaseExtractionAgent
from config.schema import ProductIdentifiers


class IdentifiersAgent(BaseExtractionAgent):
    name = "identifiers_agent"
    section_name = "identifiers"
    output_model = ProductIdentifiers
    retrieval_query = "part number sku gtin manufacturer product family revision identifiers"

    def _heuristic_extract(self, chunks: list[dict]) -> ProductIdentifiers:
        return ProductIdentifiers(
            part_number=self._extract_text_field(
                chunks,
                ["part number", "part no", "part #", "p/n", "model number"],
                value_pattern=r"[A-Za-z0-9._/-]+",
            ),
            sku=self._extract_text_field(
                chunks,
                ["sku", "stock keeping unit"],
                value_pattern=r"[A-Za-z0-9._/-]+",
            ),
            gtin=self._extract_text_field(
                chunks,
                ["gtin", "ean", "upc"],
                value_pattern=r"\d{8,14}",
            ),
            manufacturer_name=self._extract_text_field(
                chunks,
                ["manufacturer", "mfr", "brand"],
            ),
            product_family=self._extract_text_field(
                chunks,
                ["product family", "series", "family"],
            ),
            revision=self._extract_text_field(
                chunks,
                ["revision", "rev"],
                value_pattern=r"[A-Za-z0-9._/-]+",
            ),
        )
