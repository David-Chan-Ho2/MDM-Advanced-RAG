"""
PIM Exporter — flattens ProductRecord objects into CSV and JSON formats.

CSV column naming: {group}__{field}__{property}
e.g. identifiers__part_number__value, physical_dimensions__length__unit
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

from config.schema import AttributeValue, ProductRecord

# ---------------------------------------------------------------------------
# Column definitions — order matters for the CSV output
# ---------------------------------------------------------------------------

_ATTRIBUTE_COLUMNS: list[tuple[str, str, str]] = [
    # (group, field, property)
    ("identifiers", "part_number", "value"),
    ("identifiers", "part_number", "unit"),
    ("identifiers", "part_number", "confidence"),
    ("identifiers", "sku", "value"),
    ("identifiers", "sku", "confidence"),
    ("identifiers", "gtin", "value"),
    ("identifiers", "gtin", "confidence"),
    ("identifiers", "manufacturer_name", "value"),
    ("identifiers", "manufacturer_name", "confidence"),
    ("identifiers", "product_family", "value"),
    ("identifiers", "product_family", "confidence"),
    ("identifiers", "revision", "value"),
    ("identifiers", "revision", "confidence"),
    ("physical_dimensions", "length", "value"),
    ("physical_dimensions", "length", "unit"),
    ("physical_dimensions", "length", "confidence"),
    ("physical_dimensions", "width", "value"),
    ("physical_dimensions", "width", "unit"),
    ("physical_dimensions", "width", "confidence"),
    ("physical_dimensions", "height", "value"),
    ("physical_dimensions", "height", "unit"),
    ("physical_dimensions", "height", "confidence"),
    ("physical_dimensions", "depth", "value"),
    ("physical_dimensions", "depth", "unit"),
    ("physical_dimensions", "depth", "confidence"),
    ("physical_dimensions", "weight", "value"),
    ("physical_dimensions", "weight", "unit"),
    ("physical_dimensions", "weight", "confidence"),
    ("physical_dimensions", "diameter", "value"),
    ("physical_dimensions", "diameter", "unit"),
    ("physical_dimensions", "diameter", "confidence"),
    ("electrical_specs", "voltage_input", "value"),
    ("electrical_specs", "voltage_input", "unit"),
    ("electrical_specs", "voltage_input", "confidence"),
    ("electrical_specs", "voltage_output", "value"),
    ("electrical_specs", "voltage_output", "unit"),
    ("electrical_specs", "voltage_output", "confidence"),
    ("electrical_specs", "current_rating", "value"),
    ("electrical_specs", "current_rating", "unit"),
    ("electrical_specs", "current_rating", "confidence"),
    ("electrical_specs", "power_consumption", "value"),
    ("electrical_specs", "power_consumption", "unit"),
    ("electrical_specs", "power_consumption", "confidence"),
    ("electrical_specs", "frequency", "value"),
    ("electrical_specs", "frequency", "unit"),
    ("electrical_specs", "frequency", "confidence"),
    ("electrical_specs", "ip_rating", "value"),
    ("electrical_specs", "ip_rating", "confidence"),
    ("materials_compliance", "primary_material", "value"),
    ("materials_compliance", "primary_material", "confidence"),
    ("materials_compliance", "finish", "value"),
    ("materials_compliance", "finish", "confidence"),
    ("materials_compliance", "rohs_compliant", "value"),
    ("materials_compliance", "rohs_compliant", "confidence"),
    ("materials_compliance", "reach_compliant", "value"),
    ("materials_compliance", "reach_compliant", "confidence"),
    ("materials_compliance", "certifications", "value"),
    ("performance_metrics", "operating_temp_min", "value"),
    ("performance_metrics", "operating_temp_min", "unit"),
    ("performance_metrics", "operating_temp_min", "confidence"),
    ("performance_metrics", "operating_temp_max", "value"),
    ("performance_metrics", "operating_temp_max", "unit"),
    ("performance_metrics", "operating_temp_max", "confidence"),
    ("performance_metrics", "storage_temp_min", "value"),
    ("performance_metrics", "storage_temp_min", "unit"),
    ("performance_metrics", "storage_temp_min", "confidence"),
    ("performance_metrics", "storage_temp_max", "value"),
    ("performance_metrics", "storage_temp_max", "unit"),
    ("performance_metrics", "storage_temp_max", "confidence"),
    ("performance_metrics", "accuracy", "value"),
    ("performance_metrics", "accuracy", "unit"),
    ("performance_metrics", "accuracy", "confidence"),
    ("performance_metrics", "flow_rate", "value"),
    ("performance_metrics", "flow_rate", "unit"),
    ("performance_metrics", "flow_rate", "confidence"),
    ("performance_metrics", "pressure_rating", "value"),
    ("performance_metrics", "pressure_rating", "unit"),
    ("performance_metrics", "pressure_rating", "confidence"),
    ("performance_metrics", "response_time", "value"),
    ("performance_metrics", "response_time", "unit"),
    ("performance_metrics", "response_time", "confidence"),
]

_GROUP_ATTR_MAP = {
    "identifiers": "identifiers",
    "physical_dimensions": "physical_dimensions",
    "electrical_specs": "electrical_specs",
    "materials_compliance": "materials_compliance",
    "performance_metrics": "performance_metrics",
}


def _col(group: str, field: str, prop: str) -> str:
    return f"{group}__{field}__{prop}"


def _flatten_record(record: ProductRecord) -> dict[str, Any]:
    """Flatten a single ProductRecord into a dict of CSV-ready key/value pairs."""
    row: dict[str, Any] = {
        "document_id": record.document_id,
        "document_filename": record.document_filename,
        "extraction_timestamp": record.extraction_timestamp,
        "review_status": record.review_status,
        "reviewer": record.reviewer or "",
        "reviewer_notes": record.reviewer_notes or "",
        "reviewed_at": record.reviewed_at or "",
    }

    for group, field, prop in _ATTRIBUTE_COLUMNS:
        col_name = _col(group, field, prop)
        group_obj = getattr(record, _GROUP_ATTR_MAP[group], None)

        # certifications is a list[AttributeValue]
        if field == "certifications":
            certs = getattr(group_obj, "certifications", []) or []
            row[col_name] = ", ".join(
                c.value for c in certs if isinstance(c, AttributeValue) and c.value
            )
            continue

        attr: AttributeValue | None = getattr(group_obj, field, None) if group_obj else None
        if attr is None:
            row[col_name] = ""
        elif prop == "value":
            row[col_name] = attr.value or ""
        elif prop == "unit":
            row[col_name] = attr.unit or ""
        elif prop == "confidence":
            row[col_name] = attr.confidence if attr.value else ""

    return row


class PIMExporter:
    """Export a list of ProductRecords to CSV or JSON."""

    def to_csv(self, records: list[ProductRecord]) -> str:
        """Return a UTF-8 CSV string suitable for download."""
        if not records:
            return ""

        rows = [_flatten_record(r) for r in records]
        headers = list(rows[0].keys())

        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    def to_json(self, records: list[ProductRecord]) -> str:
        """Return a pretty-printed JSON string of the full ProductRecord payloads."""
        return json.dumps(
            [r.model_dump(mode="json") for r in records],
            indent=2,
            ensure_ascii=False,
        )
