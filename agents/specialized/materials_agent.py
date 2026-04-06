from __future__ import annotations

from agents.base_agent import BaseExtractionAgent
from config.schema import MaterialsAndCompliance


class MaterialsAgent(BaseExtractionAgent):
    name = "materials_agent"
    section_name = "materials_compliance"
    output_model = MaterialsAndCompliance
    retrieval_query = "material finish rohs reach certifications compliance"

    def _heuristic_extract(self, chunks: list[dict]) -> MaterialsAndCompliance:
        return MaterialsAndCompliance(
            primary_material=self._extract_text_field(
                chunks,
                ["primary material", "material", "housing material"],
            ),
            finish=self._extract_text_field(chunks, ["finish", "surface finish", "coating"]),
            rohs_compliant=self._extract_boolean_field(chunks, ["rohs", "rohs compliant"]),
            reach_compliant=self._extract_boolean_field(chunks, ["reach", "reach compliant"]),
            certifications=self._extract_certifications(chunks),
        )
