from __future__ import annotations

from agents.base_agent import BaseExtractionAgent
from config.schema import PerformanceMetrics


class PerformanceAgent(BaseExtractionAgent):
    name = "performance_agent"
    section_name = "performance_metrics"
    output_model = PerformanceMetrics
    retrieval_query = "operating temperature storage temperature accuracy flow rate pressure rating response time performance"

    def _heuristic_extract(self, chunks: list[dict]) -> PerformanceMetrics:
        operating_min, operating_max = self._extract_temperature_range(
            chunks,
            ["operating temperature", "operating temp", "ambient temperature"],
        )
        storage_min, storage_max = self._extract_temperature_range(
            chunks,
            ["storage temperature", "storage temp"],
        )

        return PerformanceMetrics(
            operating_temp_min=operating_min,
            operating_temp_max=operating_max,
            storage_temp_min=storage_min,
            storage_temp_max=storage_max,
            accuracy=self._extract_measurement(
                chunks,
                ["accuracy"],
                value_pattern=r"[+-]?\d+(?:\.\d+)?",
            ),
            flow_rate=self._extract_measurement(chunks, ["flow rate", "max flow", "flow"]),
            pressure_rating=self._extract_measurement(
                chunks,
                ["pressure rating", "rated pressure", "pressure"],
            ),
            response_time=self._extract_measurement(chunks, ["response time"]),
        )
