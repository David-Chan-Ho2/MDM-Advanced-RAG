from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from config.schema import AttributeValue
from config.settings import settings
from retrieval.hybrid_retriever import HybridRetriever

_NUMBER_PATTERN = r"[+-]?\d+(?:\.\d+)?"


class AgentResult(BaseModel):
    agent_name: str
    section_name: str
    payload: dict = Field(default_factory=dict)
    source_chunk_ids: list[str] = Field(default_factory=list)
    supporting_chunks: list[dict] = Field(default_factory=list)
    notes: str | None = None


class BaseExtractionAgent(ABC):
    name = "base_agent"
    section_name = "base"
    output_model: type[BaseModel]
    retrieval_query = ""

    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        model: str = settings.CLAUDE_EXTRACTION_MODEL,
        top_k: int = settings.TOP_K_RERANK,
        use_llm: bool | None = None,
    ):
        self._retriever = retriever or HybridRetriever()
        self._model = model
        self._top_k = top_k
        self._client = self._build_client()
        self._use_llm = (self._client is not None) if use_llm is None else use_llm

    def build_query(self, document_filename: str | None = None) -> str:
        return self.retrieval_query

    def extract(
        self,
        product_id: str,
        document_filename: str | None = None,
        filters: dict | None = None,
    ) -> AgentResult:
        combined_filters = {"product_id": product_id}
        if filters:
            combined_filters.update(filters)

        chunks = self._retriever.search(
            self.build_query(document_filename=document_filename),
            top_k=self._top_k,
            filters=combined_filters,
            decompose=False,
        )

        payload_model = self._extract_payload(chunks)
        source_chunk_ids = self._collect_source_chunk_ids(payload_model)
        if not source_chunk_ids:
            source_chunk_ids = [chunk.get("chunk_id") for chunk in chunks if chunk.get("chunk_id")]

        return AgentResult(
            agent_name=self.name,
            section_name=self.section_name,
            payload=payload_model.model_dump(mode="json"),
            source_chunk_ids=sorted(set(source_chunk_ids)),
            supporting_chunks=chunks,
        )

    def empty_result(self, notes: str | None = None) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            section_name=self.section_name,
            payload=self.output_model().model_dump(mode="json"),
            notes=notes,
        )

    def _extract_payload(self, chunks: list[dict]) -> BaseModel:
        if self._use_llm and chunks:
            llm_payload = self._extract_with_llm(chunks)
            if llm_payload is not None:
                return llm_payload
        return self._heuristic_extract(chunks)

    @abstractmethod
    def _heuristic_extract(self, chunks: list[dict]) -> BaseModel:
        raise NotImplementedError

    def _extract_with_llm(self, chunks: list[dict]) -> BaseModel | None:
        if self._client is None:
            return None

        context = self._build_context(chunks)
        prompt = (
            "Extract ONLY the attributes for your category from the technical product "
            "document context below. Return JSON matching the provided schema. "
            "Every populated attribute must include source_chunk_ids.\n\n"
            f"Schema:\n{json.dumps(self.output_model.model_json_schema(), indent=2)}\n\n"
            f"Context:\n{context}"
        )

        try:  # pragma: no cover - external API path
            message = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            payload = json.loads(self._extract_json_block(message.content[0].text))
            return self.output_model.model_validate(payload)
        except Exception:
            return None

    @staticmethod
    def _build_client():
        try:
            import anthropic
        except ImportError:
            return None

        if not settings.ANTHROPIC_API_KEY:
            return None
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    @staticmethod
    def _build_context(chunks: list[dict]) -> str:
        context_parts = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            text = chunk.get("text", "")
            context_parts.append(f"[{chunk_id}]\n{text}")
        return "\n\n".join(context_parts)

    @staticmethod
    def _extract_json_block(text: str) -> str:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        return text

    @staticmethod
    def _collect_source_chunk_ids(payload_model: BaseModel) -> list[str]:
        collected: list[str] = []
        for _, field_value in payload_model:
            if isinstance(field_value, AttributeValue):
                collected.extend(field_value.source_chunk_ids)
            elif isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, AttributeValue):
                        collected.extend(item.source_chunk_ids)
        return collected

    def _make_attribute(
        self,
        value: str | None,
        unit: str | None = None,
        source_chunk_ids: list[str] | None = None,
        confidence: str = "high",
    ) -> AttributeValue | None:
        if value is None:
            return None

        cleaned_value = str(value).strip().strip(".,;")
        cleaned_unit = str(unit).strip().strip(".,;") if unit else None
        if not cleaned_value:
            return None

        return AttributeValue(
            value=cleaned_value,
            unit=cleaned_unit or None,
            confidence=confidence,
            source_chunk_ids=sorted(set(source_chunk_ids or [])),
        )

    def _extract_measurement(
        self,
        chunks: list[dict],
        labels: list[str],
        *,
        value_pattern: str = _NUMBER_PATTERN,
    ) -> AttributeValue | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = re.compile(
            rf"(?:{label_pattern})\s*(?:[:\-]|is)?\s*(?P<value>{value_pattern})\s*(?P<unit>[A-Za-z%/0-9.\-]+)?",
            re.IGNORECASE,
        )

        for chunk in chunks:
            match = pattern.search(chunk.get("text", ""))
            if not match:
                continue
            return self._make_attribute(
                match.group("value"),
                unit=match.group("unit"),
                source_chunk_ids=[chunk.get("chunk_id")] if chunk.get("chunk_id") else [],
            )
        return None

    def _extract_text_field(
        self,
        chunks: list[dict],
        labels: list[str],
        *,
        value_pattern: str = r"[^\n|]+",
    ) -> AttributeValue | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = re.compile(
            rf"(?:{label_pattern})\s*(?:[:\-]|is)?\s*(?P<value>{value_pattern})",
            re.IGNORECASE,
        )

        for chunk in chunks:
            match = pattern.search(chunk.get("text", ""))
            if not match:
                continue
            return self._make_attribute(
                match.group("value"),
                source_chunk_ids=[chunk.get("chunk_id")] if chunk.get("chunk_id") else [],
            )
        return None

    def _extract_boolean_field(self, chunks: list[dict], labels: list[str]) -> AttributeValue | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = re.compile(
            rf"(?:{label_pattern})(?:\s+compliant)?\s*(?:[:\-]|is)?\s*"
            r"(?P<value>yes|no|true|false|compliant|not compliant|non-compliant|pass|fail)",
            re.IGNORECASE,
        )

        for chunk in chunks:
            text = chunk.get("text", "")
            match = pattern.search(text)
            if match:
                value = match.group("value").lower()
                normalized = "true" if value in {"yes", "true", "compliant", "pass"} else "false"
                return self._make_attribute(
                    normalized,
                    source_chunk_ids=[chunk.get("chunk_id")] if chunk.get("chunk_id") else [],
                )

            lowered = text.lower()
            if any(label.lower() in lowered for label in labels) and "compliant" in lowered:
                return self._make_attribute(
                    "true",
                    source_chunk_ids=[chunk.get("chunk_id")] if chunk.get("chunk_id") else [],
                    confidence="medium",
                )

        return None

    def _extract_temperature_range(
        self,
        chunks: list[dict],
        labels: list[str],
    ) -> tuple[AttributeValue | None, AttributeValue | None]:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = re.compile(
            rf"(?:{label_pattern})[^\n:]*[:\-]?\s*(?P<min>{_NUMBER_PATTERN})\s*"
            r"(?:\u00b0?\s*(?P<unit1>[CFK]))?\s*(?:to|through|-|\u2013)\s*"
            rf"(?P<max>{_NUMBER_PATTERN})\s*(?:\u00b0?\s*(?P<unit2>[CFK]))?",
            re.IGNORECASE,
        )

        for chunk in chunks:
            match = pattern.search(chunk.get("text", ""))
            if not match:
                continue
            unit = match.group("unit1") or match.group("unit2") or "C"
            source_ids = [chunk.get("chunk_id")] if chunk.get("chunk_id") else []
            return (
                self._make_attribute(match.group("min"), unit=unit, source_chunk_ids=source_ids),
                self._make_attribute(match.group("max"), unit=unit, source_chunk_ids=source_ids),
            )

        return None, None

    def _extract_certifications(self, chunks: list[dict]) -> list[AttributeValue]:
        pattern = re.compile(r"certifications?\s*(?:[:\-]|include)?\s*(?P<value>[^\n]+)", re.IGNORECASE)
        values: list[AttributeValue] = []

        for chunk in chunks:
            match = pattern.search(chunk.get("text", ""))
            if not match:
                continue

            source_ids = [chunk.get("chunk_id")] if chunk.get("chunk_id") else []
            raw_values = re.split(r",|;|/|\band\b", match.group("value"))
            for raw_value in raw_values:
                certification = raw_value.strip().strip(".")
                if certification:
                    attribute = self._make_attribute(certification, source_chunk_ids=source_ids)
                    if attribute is not None:
                        values.append(attribute)

        deduped: dict[str, AttributeValue] = {}
        for value in values:
            deduped.setdefault(value.value.lower(), value)
        return list(deduped.values())
