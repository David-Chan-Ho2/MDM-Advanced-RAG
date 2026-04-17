from __future__ import annotations

from config.schema import AttributeValue, ProductRecord

_FIELD_LABELS = [
    ("identifiers", "part_number", "Part Number"),
    ("identifiers", "sku", "SKU"),
    ("identifiers", "gtin", "GTIN"),
    ("identifiers", "manufacturer_name", "Brand"),
    ("identifiers", "product_family", "Product Family"),
    ("identifiers", "revision", "Revision"),
    ("physical_dimensions", "length", "Overall Length"),
    ("physical_dimensions", "width", "Overall Width"),
    ("physical_dimensions", "height", "Overall Height"),
    ("physical_dimensions", "depth", "Overall Depth"),
    ("physical_dimensions", "weight", "Weight"),
    ("physical_dimensions", "diameter", "Diameter"),
    ("electrical_specs", "voltage_input", "Input Voltage"),
    ("electrical_specs", "voltage_output", "Output Voltage"),
    ("electrical_specs", "current_rating", "Current Rating"),
    ("electrical_specs", "power_consumption", "Power Consumption"),
    ("electrical_specs", "frequency", "Supply Voltage Frequency"),
    ("electrical_specs", "ip_rating", "Enclosure Rating"),
    ("materials_compliance", "primary_material", "Primary Material"),
    ("materials_compliance", "finish", "Finish"),
    ("materials_compliance", "rohs_compliant", "RoHS Compliant"),
    ("materials_compliance", "reach_compliant", "REACH Compliant"),
    ("performance_metrics", "operating_temp_min", "Minimum Operating Ambient Temperature"),
    ("performance_metrics", "operating_temp_max", "Maximum Operating Ambient Temperature"),
    ("performance_metrics", "storage_temp_min", "Minimum Storage Temperature"),
    ("performance_metrics", "storage_temp_max", "Maximum Storage Temperature"),
    ("performance_metrics", "accuracy", "Accuracy"),
    ("performance_metrics", "flow_rate", "Flow Rate"),
    ("performance_metrics", "pressure_rating", "Pressure Rating"),
    ("performance_metrics", "response_time", "Response Time"),
]


class SampleOutputFormatter:
    """Formats ProductRecords into the sample JSON shape: product_id -> attribute list."""

    def format_record(self, record: ProductRecord) -> dict[str, list[dict[str, str]]]:
        product_key = record.product_id or record.document_id
        output_attributes: list[dict[str, str]] = []

        for group_name, field_name, label in _FIELD_LABELS:
            group = getattr(record, group_name)
            attribute = getattr(group, field_name)
            if isinstance(attribute, AttributeValue) and attribute.value is not None:
                output_attributes.append({label: self._format_value(attribute)})

        if record.materials_compliance.certifications:
            certifications = [
                self._format_value(attribute)
                for attribute in record.materials_compliance.certifications
                if attribute.value is not None
            ]
            if certifications:
                output_attributes.append(
                    {"Certificates and Standards": ", ".join(certifications)}
                )

        return {product_key: output_attributes}

    def format_records(self, records: list[ProductRecord]) -> dict[str, list[dict[str, str]]]:
        formatted: dict[str, list[dict[str, str]]] = {}
        for record in records:
            for product_id, attributes in self.format_record(record).items():
                formatted.setdefault(product_id, []).extend(attributes)
        return formatted

    @staticmethod
    def _format_value(attribute: AttributeValue) -> str:
        if attribute.unit:
            return f"{attribute.value} {attribute.unit}"
        return str(attribute.value)
