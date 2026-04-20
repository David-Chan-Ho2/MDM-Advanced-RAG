"""
PIM attribute schema. Every field is an AttributeValue so value, unit,
confidence, and source traceability travel together through the pipeline.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]
"""
high   — value appears verbatim and unambiguously in source text
medium — value inferred from context or in an unusual format
low    — best guess; source is ambiguous or partial
"""


class AttributeValue(BaseModel):
    value: Optional[str] = None
    unit: Optional[str] = None
    confidence: ConfidenceLevel = "low"
    source_chunk_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Attribute groups (one per specialized agent)
# ---------------------------------------------------------------------------


class ProductIdentifiers(BaseModel):
    part_number: Optional[AttributeValue] = None
    sku: Optional[AttributeValue] = None
    gtin: Optional[AttributeValue] = None
    manufacturer_name: Optional[AttributeValue] = None
    product_family: Optional[AttributeValue] = None
    revision: Optional[AttributeValue] = None


class PhysicalDimensions(BaseModel):
    length: Optional[AttributeValue] = None
    width: Optional[AttributeValue] = None
    height: Optional[AttributeValue] = None
    depth: Optional[AttributeValue] = None
    weight: Optional[AttributeValue] = None
    diameter: Optional[AttributeValue] = None


class ElectricalSpecs(BaseModel):
    voltage_input: Optional[AttributeValue] = None
    voltage_output: Optional[AttributeValue] = None
    current_rating: Optional[AttributeValue] = None
    power_consumption: Optional[AttributeValue] = None
    frequency: Optional[AttributeValue] = None
    ip_rating: Optional[AttributeValue] = None


class MaterialsAndCompliance(BaseModel):
    primary_material: Optional[AttributeValue] = None
    finish: Optional[AttributeValue] = None
    rohs_compliant: Optional[AttributeValue] = None
    reach_compliant: Optional[AttributeValue] = None
    certifications: list[AttributeValue] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    operating_temp_min: Optional[AttributeValue] = None
    operating_temp_max: Optional[AttributeValue] = None
    storage_temp_min: Optional[AttributeValue] = None
    storage_temp_max: Optional[AttributeValue] = None
    accuracy: Optional[AttributeValue] = None
    flow_rate: Optional[AttributeValue] = None
    pressure_rating: Optional[AttributeValue] = None
    response_time: Optional[AttributeValue] = None


# ---------------------------------------------------------------------------
# Top-level record
# ---------------------------------------------------------------------------


class ProductRecord(BaseModel):
    document_id: str
    product_id: Optional[str] = None
    document_filename: str
    extraction_timestamp: str = ""

    identifiers: ProductIdentifiers = Field(default_factory=ProductIdentifiers)
    physical_dimensions: PhysicalDimensions = Field(default_factory=PhysicalDimensions)
    electrical_specs: ElectricalSpecs = Field(default_factory=ElectricalSpecs)
    materials_compliance: MaterialsAndCompliance = Field(
        default_factory=MaterialsAndCompliance
    )
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)

    # Audit trail: raw output from each agent before merging
    raw_agent_outputs: dict = Field(default_factory=dict)

    # Workflow state
    review_status: Literal["pending", "approved", "rejected", "edited"] = "pending"
    reviewer: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
