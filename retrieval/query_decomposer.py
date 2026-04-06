from __future__ import annotations

import json
import re

from config.settings import settings

_ATTRIBUTE_PHRASES = [
    "operating temperature",
    "storage temperature",
    "part number",
    "product family",
    "manufacturer",
    "manufacturer name",
    "ip rating",
    "response time",
    "flow rate",
    "pressure rating",
    "current rating",
    "voltage",
    "power consumption",
    "voltage input",
    "voltage output",
    "frequency",
    "accuracy",
    "material",
    "finish",
    "certifications",
    "reach",
    "rohs",
    "length",
    "width",
    "height",
    "depth",
    "weight",
    "diameter",
    "sku",
    "gtin",
    "revision",
]

_SUBJECT_PATTERN = re.compile(r"\b(?:for|of|on)\s+(.+?)(?:\?|$)", re.IGNORECASE)


class QueryDecomposer:
    """Breaks multi-attribute questions into smaller retrieval queries."""

    def __init__(
        self,
        model: str = settings.CLAUDE_EXTRACTION_MODEL,
        max_subqueries: int = settings.QUERY_DECOMPOSITION_MAX_SUBQUERIES,
    ):
        self._model = model
        self._max_subqueries = max_subqueries
        self._client = self._build_client()

    def decompose(self, query: str) -> list[str]:
        query = query.strip()
        if not query:
            return []

        llm_queries = self._decompose_with_llm(query)
        if llm_queries:
            return llm_queries[: self._max_subqueries]

        return self._decompose_heuristically(query)

    def _build_client(self):
        try:
            import anthropic
        except ImportError:
            return None

        from config.settings import settings as runtime_settings

        if not runtime_settings.ANTHROPIC_API_KEY:
            return None

        return anthropic.Anthropic(api_key=runtime_settings.ANTHROPIC_API_KEY)

    def _decompose_with_llm(self, query: str) -> list[str]:
        if self._client is None:
            return []

        prompt = (
            "Decompose the technical product-specification question into at most "
            f"{self._max_subqueries} short retrieval queries. Return JSON with a "
            'single key "queries". Keep exact product codes and part numbers.\n\n'
            f"Question: {query}"
        )

        try:  # pragma: no cover - external API path
            message = self._client.messages.create(
                model=self._model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text
            payload = json.loads(self._extract_json_block(text))
            queries = [
                item.strip()
                for item in payload.get("queries", [])
                if isinstance(item, str) and item.strip()
            ]
            if queries:
                return queries
        except Exception:
            return []

        return []

    def _decompose_heuristically(self, query: str) -> list[str]:
        lowered = query.lower()
        matched_attributes = [
            phrase for phrase in _ATTRIBUTE_PHRASES if phrase in lowered
        ]
        matched_attributes = list(dict.fromkeys(matched_attributes))

        if len(matched_attributes) <= 1:
            return [query]

        subject_match = _SUBJECT_PATTERN.search(query)
        subject = subject_match.group(1).strip() if subject_match else ""

        queries = [query]
        for attribute in matched_attributes:
            if subject:
                queries.append(f"What is the {attribute} for {subject}?")
            else:
                queries.append(f"What is the {attribute}?")

        return queries[: self._max_subqueries]

    @staticmethod
    def _extract_json_block(text: str) -> str:
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return text

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        return text
