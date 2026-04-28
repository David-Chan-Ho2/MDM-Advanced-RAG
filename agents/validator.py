from __future__ import annotations

from datetime import datetime, timezone

from config.schema import (
    AttributeValue,
    ElectricalSpecs,
    MaterialsAndCompliance,
    PerformanceMetrics,
    PhysicalDimensions,
    ProductIdentifiers,
    ProductRecord,
)

_UNIT_ALIASES = {
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "lb": "lb",
    "lbs": "lb",
    "mm": "mm",
    "millimeter": "mm",
    "millimeters": "mm",
    "cm": "cm",
    "m": "m",
    "v": "V",
    "vdc": "VDC",
    "vac": "VAC",
    "a": "A",
    "ma": "mA",
    "w": "W",
    "kw": "kW",
    "hz": "Hz",
    "khz": "kHz",
    "mhz": "MHz",
    "c": "C",
    "°c": "C",
    "f": "F",
    "°f": "F",
    "bar": "bar",
    "psi": "psi",
    "pa": "Pa",
    "mpa": "MPa",
    "ms": "ms",
    "s": "s",
    "l/min": "L/min",
    "lpm": "L/min",
}

_BOOLEAN_TRUE = {"true", "yes", "compliant", "pass", "passed"}
_BOOLEAN_FALSE = {"false", "no", "non-compliant", "not compliant", "fail", "failed"}


class ExtractionValidator:
    def merge(
        self,
        product_id: str,
        document_filename: str,
        agent_results: list,
    ) -> ProductRecord:
        payload_map = {result.section_name: result.payload for result in agent_results}

        record = ProductRecord(
            document_id=product_id,
            product_id=product_id,
            document_filename=document_filename,
            extraction_timestamp=datetime.now(timezone.utc).isoformat(),
            identifiers=ProductIdentifiers.model_validate(payload_map.get("identifiers", {})),
            physical_dimensions=PhysicalDimensions.model_validate(
                payload_map.get("physical_dimensions", {})
            ),
            electrical_specs=ElectricalSpecs.model_validate(
                payload_map.get("electrical_specs", {})
            ),
            materials_compliance=MaterialsAndCompliance.model_validate(
                payload_map.get("materials_compliance", {})
            ),
            performance_metrics=PerformanceMetrics.model_validate(
                payload_map.get("performance_metrics", {})
            ),
            raw_agent_outputs={
                result.agent_name: result.payload
                for result in agent_results
            },
        )

        return self.validate(record)

    def validate(self, record: ProductRecord) -> ProductRecord:
        self._normalize_group_units(record.physical_dimensions)
        self._normalize_group_units(record.electrical_specs)
        self._normalize_group_units(record.performance_metrics)
        self._normalize_boolean(record.materials_compliance.rohs_compliant)
        self._normalize_boolean(record.materials_compliance.reach_compliant)
        self._dedupe_certifications(record.materials_compliance)
        self._normalize_temperature_range(
            record.performance_metrics.operating_temp_min,
            record.performance_metrics.operating_temp_max,
        )
        self._normalize_temperature_range(
            record.performance_metrics.storage_temp_min,
            record.performance_metrics.storage_temp_max,
        )
        return record

    def _normalize_group_units(self, group) -> None:
        for field_name in getattr(group.__class__, "model_fields", {}):
            value = getattr(group, field_name)
            if isinstance(value, AttributeValue):
                self._normalize_unit(value)

    @staticmethod
    def _normalize_unit(attribute: AttributeValue | None) -> None:
        if attribute is None or not attribute.unit:
            return
        normalized = _UNIT_ALIASES.get(attribute.unit.lower())
        if normalized:
            attribute.unit = normalized
        attribute.source_chunk_ids = sorted(set(attribute.source_chunk_ids))

    @staticmethod
    def _normalize_boolean(attribute: AttributeValue | None) -> None:
        if attribute is None or attribute.value is None:
            return
        lowered = attribute.value.lower()
        if lowered in _BOOLEAN_TRUE:
            attribute.value = "true"
        elif lowered in _BOOLEAN_FALSE:
            attribute.value = "false"
        attribute.source_chunk_ids = sorted(set(attribute.source_chunk_ids))

    @staticmethod
    def _dedupe_certifications(materials: MaterialsAndCompliance) -> None:
        deduped: dict[str, AttributeValue] = {}
        for certification in materials.certifications:
            key = certification.value.lower() if certification.value else ""
            if not key:
                continue
            certification.source_chunk_ids = sorted(set(certification.source_chunk_ids))
            deduped.setdefault(key, certification)
        materials.certifications = list(deduped.values())

    @staticmethod
    def _normalize_temperature_range(
        minimum: AttributeValue | None,
        maximum: AttributeValue | None,
    ) -> None:
        if minimum is None or maximum is None:
            return

        try:
            min_value = float(minimum.value)
            max_value = float(maximum.value)
        except (TypeError, ValueError):
            return

        if min_value > max_value:
            minimum.value, maximum.value = maximum.value, minimum.value
            minimum.unit, maximum.unit = maximum.unit, minimum.unit
