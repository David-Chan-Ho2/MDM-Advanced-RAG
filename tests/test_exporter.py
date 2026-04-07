"""
Unit tests for workflow/exporter.py — PIMExporter CSV and JSON output.
"""

from __future__ import annotations

import csv
import json
from io import StringIO

import pytest

from config.schema import (
    AttributeValue,
    ElectricalSpecs,
    MaterialsAndCompliance,
    PerformanceMetrics,
    PhysicalDimensions,
    ProductIdentifiers,
    ProductRecord,
)
from workflow.exporter import PIMExporter, _flatten_record


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _av(value: str, unit: str | None = None, confidence: str = "high") -> AttributeValue:
    return AttributeValue(value=value, unit=unit, confidence=confidence)


@pytest.fixture
def full_record() -> ProductRecord:
    return ProductRecord(
        document_id="doc-001",
        document_filename="widget_pro.pdf",
        extraction_timestamp="2026-04-06T12:00:00Z",
        review_status="approved",
        reviewer="Alice",
        reviewer_notes="Looks good",
        reviewed_at="2026-04-06T13:00:00Z",
        identifiers=ProductIdentifiers(
            part_number=_av("WP-1234"),
            sku=_av("SKU-9999"),
            manufacturer_name=_av("Acme Corp"),
            product_family=_av("Widget Series"),
        ),
        physical_dimensions=PhysicalDimensions(
            length=_av("150", "mm"),
            width=_av("80", "mm"),
            height=_av("40", "mm"),
            weight=_av("2.5", "kg"),
        ),
        electrical_specs=ElectricalSpecs(
            voltage_input=_av("24", "V"),
            power_consumption=_av("10", "W"),
            ip_rating=_av("IP67"),
        ),
        materials_compliance=MaterialsAndCompliance(
            primary_material=_av("Aluminum"),
            rohs_compliant=_av("Yes", confidence="high"),
            certifications=[_av("CE"), _av("UL")],
        ),
        performance_metrics=PerformanceMetrics(
            operating_temp_min=_av("-20", "°C"),
            operating_temp_max=_av("85", "°C"),
            accuracy=_av("±0.5", "%"),
        ),
    )


@pytest.fixture
def empty_record() -> ProductRecord:
    return ProductRecord(
        document_id="doc-002",
        document_filename="empty.pdf",
        extraction_timestamp="2026-04-06T12:00:00Z",
    )


@pytest.fixture
def exporter() -> PIMExporter:
    return PIMExporter()


# ---------------------------------------------------------------------------
# _flatten_record
# ---------------------------------------------------------------------------

class TestFlattenRecord:
    def test_metadata_fields_present(self, full_record):
        row = _flatten_record(full_record)
        assert row["document_id"] == "doc-001"
        assert row["document_filename"] == "widget_pro.pdf"
        assert row["review_status"] == "approved"
        assert row["reviewer"] == "Alice"

    def test_identifier_value(self, full_record):
        row = _flatten_record(full_record)
        assert row["identifiers__part_number__value"] == "WP-1234"
        assert row["identifiers__part_number__confidence"] == "high"

    def test_dimension_with_unit(self, full_record):
        row = _flatten_record(full_record)
        assert row["physical_dimensions__length__value"] == "150"
        assert row["physical_dimensions__length__unit"] == "mm"
        assert row["physical_dimensions__length__confidence"] == "high"

    def test_certifications_joined(self, full_record):
        row = _flatten_record(full_record)
        assert row["materials_compliance__certifications__value"] == "CE, UL"

    def test_missing_attr_is_empty_string(self, full_record):
        row = _flatten_record(full_record)
        assert row["identifiers__gtin__value"] == ""
        assert row["identifiers__gtin__confidence"] == ""

    def test_empty_record_all_blanks(self, empty_record):
        row = _flatten_record(empty_record)
        assert row["identifiers__part_number__value"] == ""
        assert row["physical_dimensions__weight__unit"] == ""
        assert row["performance_metrics__accuracy__confidence"] == ""

    def test_no_certifications_empty_string(self, empty_record):
        row = _flatten_record(empty_record)
        assert row["materials_compliance__certifications__value"] == ""


# ---------------------------------------------------------------------------
# PIMExporter.to_csv
# ---------------------------------------------------------------------------

class TestToCSV:
    def test_empty_list_returns_empty_string(self, exporter):
        assert exporter.to_csv([]) == ""

    def test_csv_has_header_row(self, exporter, full_record):
        csv_str = exporter.to_csv([full_record])
        reader = csv.DictReader(StringIO(csv_str))
        headers = reader.fieldnames or []
        assert "document_id" in headers
        assert "identifiers__part_number__value" in headers
        assert "physical_dimensions__length__unit" in headers

    def test_csv_data_row_values(self, exporter, full_record):
        csv_str = exporter.to_csv([full_record])
        reader = csv.DictReader(StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["identifiers__part_number__value"] == "WP-1234"
        assert rows[0]["physical_dimensions__length__value"] == "150"
        assert rows[0]["physical_dimensions__length__unit"] == "mm"
        assert rows[0]["electrical_specs__ip_rating__value"] == "IP67"

    def test_csv_multiple_records(self, exporter, full_record, empty_record):
        csv_str = exporter.to_csv([full_record, empty_record])
        reader = csv.DictReader(StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["document_filename"] == "widget_pro.pdf"
        assert rows[1]["document_filename"] == "empty.pdf"

    def test_csv_certifications_comma_joined(self, exporter, full_record):
        csv_str = exporter.to_csv([full_record])
        reader = csv.DictReader(StringIO(csv_str))
        row = next(reader)
        assert row["materials_compliance__certifications__value"] == "CE, UL"

    def test_csv_confidence_blank_when_no_value(self, exporter, full_record):
        # GTIN was not set — confidence should be blank
        csv_str = exporter.to_csv([full_record])
        reader = csv.DictReader(StringIO(csv_str))
        row = next(reader)
        assert row["identifiers__gtin__confidence"] == ""


# ---------------------------------------------------------------------------
# PIMExporter.to_json
# ---------------------------------------------------------------------------

class TestToJSON:
    def test_empty_list_returns_empty_array(self, exporter):
        result = json.loads(exporter.to_json([]))
        assert result == []

    def test_json_contains_document_id(self, exporter, full_record):
        result = json.loads(exporter.to_json([full_record]))
        assert len(result) == 1
        assert result[0]["document_id"] == "doc-001"

    def test_json_nested_structure_preserved(self, exporter, full_record):
        result = json.loads(exporter.to_json([full_record]))
        rec = result[0]
        assert rec["identifiers"]["part_number"]["value"] == "WP-1234"
        assert rec["physical_dimensions"]["length"]["unit"] == "mm"

    def test_json_multiple_records(self, exporter, full_record, empty_record):
        result = json.loads(exporter.to_json([full_record, empty_record]))
        assert len(result) == 2

    def test_json_review_fields_present(self, exporter, full_record):
        result = json.loads(exporter.to_json([full_record]))
        rec = result[0]
        assert rec["review_status"] == "approved"
        assert rec["reviewer"] == "Alice"
        assert rec["reviewer_notes"] == "Looks good"
