from __future__ import annotations

from agents.base_agent import BaseExtractionAgent
from config.schema import ElectricalSpecs


class ElectricalAgent(BaseExtractionAgent):
    name = "electrical_agent"
    section_name = "electrical_specs"
    output_model = ElectricalSpecs
    retrieval_query = "voltage current power frequency ip rating electrical specifications"

    def _heuristic_extract(self, chunks: list[dict]) -> ElectricalSpecs:
        voltage_input = self._extract_measurement(chunks, ["input voltage", "voltage input"])
        voltage_output = self._extract_measurement(chunks, ["output voltage", "voltage output"])
        generic_voltage = self._extract_measurement(chunks, ["voltage"])

        return ElectricalSpecs(
            voltage_input=voltage_input or generic_voltage,
            voltage_output=voltage_output,
            current_rating=self._extract_measurement(chunks, ["current rating", "rated current", "current"]),
            power_consumption=self._extract_measurement(chunks, ["power consumption", "power draw", "power"]),
            frequency=self._extract_measurement(chunks, ["frequency"]),
            ip_rating=self._extract_text_field(
                chunks,
                ["ip rating", "ingress protection", "ip"],
                value_pattern=r"IP[0-9A-Za-z]+",
            ),
        )
