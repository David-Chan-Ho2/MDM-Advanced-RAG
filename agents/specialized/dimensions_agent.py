from __future__ import annotations

from agents.base_agent import BaseExtractionAgent
from config.schema import PhysicalDimensions


class DimensionsAgent(BaseExtractionAgent):
    name = "dimensions_agent"
    section_name = "physical_dimensions"
    output_model = PhysicalDimensions
    retrieval_query = "dimensions length width height depth diameter weight measurements"

    def _heuristic_extract(self, chunks: list[dict]) -> PhysicalDimensions:
        return PhysicalDimensions(
            length=self._extract_measurement(chunks, ["length", "overall length"]),
            width=self._extract_measurement(chunks, ["width", "overall width"]),
            height=self._extract_measurement(chunks, ["height", "overall height"]),
            depth=self._extract_measurement(chunks, ["depth", "overall depth"]),
            weight=self._extract_measurement(chunks, ["weight", "mass", "shipping weight"]),
            diameter=self._extract_measurement(chunks, ["diameter", "outer diameter", "od"]),
        )
