from __future__ import annotations

from agents.orchestrator import ExtractionOrchestrator
from agents.specialized import (
    DimensionsAgent,
    ElectricalAgent,
    IdentifiersAgent,
    MaterialsAgent,
    PerformanceAgent,
)
from agents.validator import ExtractionValidator


class StubRetriever:
    def __init__(self, chunks: list[dict]):
        self._chunks = chunks

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
        decompose: bool = True,
    ) -> list[dict]:
        results = []
        for chunk in self._chunks:
            if filters and any(str(chunk.get(key)).lower() != str(value).lower() for key, value in filters.items()):
                continue
            results.append(dict(chunk))
        return results[: top_k or len(results)]


def build_chunks() -> list[dict]:
    return [
        {
            "chunk_id": "chunk-1",
            "document_id": "widget_pro",
            "filename": "widget_pro.txt",
            "page_number": 1,
            "chunk_index": 0,
            "text": (
                "Manufacturer: Acme Industrial\n"
                "Part Number: WP-1234\n"
                "Product Family: Widget Pro\n"
                "Revision: B\n"
                "Weight: 2.5 kg\n"
                "Length: 150 mm\n"
                "Width: 40 mm\n"
                "Voltage: 24V DC\n"
                "Current Rating: 2 A\n"
                "IP Rating: IP67\n"
            ),
        },
        {
            "chunk_id": "chunk-2",
            "document_id": "widget_pro",
            "filename": "widget_pro.txt",
            "page_number": 2,
            "chunk_index": 1,
            "text": (
                "Primary Material: Stainless Steel\n"
                "Finish: Powder Coated\n"
                "RoHS: Compliant\n"
                "REACH: Yes\n"
                "Certifications: CE, UL\n"
                "Operating Temperature: -20 C to 85 C\n"
                "Storage Temperature: -40 C to 90 C\n"
                "Flow Rate: 5 L/min\n"
                "Pressure Rating: 10 bar\n"
                "Response Time: 50 ms\n"
            ),
        },
    ]


def test_specialized_agents_extract_structured_attributes():
    retriever = StubRetriever(build_chunks())

    identifiers = IdentifiersAgent(retriever=retriever, use_llm=False).extract("widget_pro", "widget_pro.txt")
    dimensions = DimensionsAgent(retriever=retriever, use_llm=False).extract("widget_pro", "widget_pro.txt")
    electrical = ElectricalAgent(retriever=retriever, use_llm=False).extract("widget_pro", "widget_pro.txt")
    materials = MaterialsAgent(retriever=retriever, use_llm=False).extract("widget_pro", "widget_pro.txt")
    performance = PerformanceAgent(retriever=retriever, use_llm=False).extract("widget_pro", "widget_pro.txt")

    assert identifiers.payload["part_number"]["value"] == "WP-1234"
    assert dimensions.payload["weight"]["unit"] == "kg"
    assert electrical.payload["ip_rating"]["value"] == "IP67"
    assert materials.payload["rohs_compliant"]["value"] == "true"
    assert performance.payload["operating_temp_min"]["value"] == "-20"
    assert performance.payload["response_time"]["unit"] == "ms"


def test_orchestrator_merges_agent_outputs_into_product_record():
    retriever = StubRetriever(build_chunks())
    orchestrator = ExtractionOrchestrator(
        agents=[
            IdentifiersAgent(retriever=retriever, use_llm=False),
            DimensionsAgent(retriever=retriever, use_llm=False),
            ElectricalAgent(retriever=retriever, use_llm=False),
            MaterialsAgent(retriever=retriever, use_llm=False),
            PerformanceAgent(retriever=retriever, use_llm=False),
        ],
        validator=ExtractionValidator(),
    )

    record = orchestrator.extract_document("widget_pro", "widget_pro.txt")

    assert record.identifiers.part_number.value == "WP-1234"
    assert record.physical_dimensions.length.unit == "mm"
    assert record.electrical_specs.voltage_input.unit == "V"
    assert record.materials_compliance.primary_material.value == "Stainless Steel"
    assert record.performance_metrics.flow_rate.value == "5"
    assert sorted(cert.value for cert in record.materials_compliance.certifications) == ["CE", "UL"]
