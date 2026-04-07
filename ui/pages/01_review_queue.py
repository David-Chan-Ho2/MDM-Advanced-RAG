"""
Review Queue — inspect pending extractions and approve / edit / reject them.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from config.schema import AttributeValue, ProductRecord
from workflow.review_store import ReviewStore

st.set_page_config(page_title="Review Queue", layout="wide")

# ---------------------------------------------------------------------------
# Shared store
# ---------------------------------------------------------------------------
if "store" not in st.session_state:
    st.session_state.store = ReviewStore()
store: ReviewStore = st.session_state.store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attr_display(attr: AttributeValue | None) -> str:
    if attr is None or attr.value is None:
        return ""
    parts = [attr.value]
    if attr.unit:
        parts.append(attr.unit)
    return " ".join(parts)


def _confidence_badge(attr: AttributeValue | None) -> str:
    if attr is None or attr.value is None:
        return ""
    colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
    return colors.get(attr.confidence, "")


def _render_attr_row(label: str, attr: AttributeValue | None) -> tuple[str, str]:
    """Render a two-column row for an attribute. Returns (value_display, confidence)."""
    val = _attr_display(attr)
    conf = _confidence_badge(attr)
    return val, conf


def _edit_attr(key: str, attr: AttributeValue | None, show_unit: bool = True) -> dict:
    """Render editable fields for a single attribute. Returns updated field dict."""
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        value = st.text_input("Value", value=attr.value or "" if attr else "", key=f"{key}_val")
    with col2:
        if show_unit:
            unit = st.text_input("Unit", value=attr.unit or "" if attr else "", key=f"{key}_unit")
        else:
            unit = attr.unit if attr else ""
    with col3:
        confidence = st.selectbox(
            "Confidence",
            ["high", "medium", "low"],
            index=["high", "medium", "low"].index(attr.confidence if attr else "low"),
            key=f"{key}_conf",
        )
    return {"value": value or None, "unit": unit or None, "confidence": confidence}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Review Queue")

pending = store.list_records(review_status="pending")
counts = store.count_by_status()

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Pending", counts.get("pending", 0))
col_b.metric("Approved", counts.get("approved", 0))
col_c.metric("Edited", counts.get("edited", 0))
col_d.metric("Rejected", counts.get("rejected", 0))

st.markdown("---")

if not pending:
    st.success("All caught up — no pending extractions.")
    st.stop()

# ---------------------------------------------------------------------------
# Record selector
# ---------------------------------------------------------------------------
filenames = [r.document_filename for r in pending]
selected_filename = st.selectbox(
    f"Select a record to review ({len(pending)} pending)",
    filenames,
    key="selected_record",
)

record: ProductRecord = next(r for r in pending if r.document_filename == selected_filename)

st.markdown(f"### {record.document_filename}")
st.caption(f"Document ID: `{record.document_id}` · Extracted: {record.extraction_timestamp}")

# ---------------------------------------------------------------------------
# Attribute display — read-only summary table
# ---------------------------------------------------------------------------
with st.expander("Extracted Attributes (read-only summary)", expanded=True):
    def _row(label: str, attr: AttributeValue | None) -> None:
        val, conf = _render_attr_row(label, attr)
        c1, c2, c3 = st.columns([3, 3, 1])
        c1.write(f"**{label}**")
        c2.write(val if val else "_not found_")
        c3.write(conf)

    st.markdown("**Identifiers**")
    _row("Part Number", record.identifiers.part_number)
    _row("SKU", record.identifiers.sku)
    _row("GTIN", record.identifiers.gtin)
    _row("Manufacturer", record.identifiers.manufacturer_name)
    _row("Product Family", record.identifiers.product_family)
    _row("Revision", record.identifiers.revision)

    st.markdown("**Physical Dimensions**")
    _row("Length", record.physical_dimensions.length)
    _row("Width", record.physical_dimensions.width)
    _row("Height", record.physical_dimensions.height)
    _row("Depth", record.physical_dimensions.depth)
    _row("Weight", record.physical_dimensions.weight)
    _row("Diameter", record.physical_dimensions.diameter)

    st.markdown("**Electrical Specs**")
    _row("Voltage Input", record.electrical_specs.voltage_input)
    _row("Voltage Output", record.electrical_specs.voltage_output)
    _row("Current Rating", record.electrical_specs.current_rating)
    _row("Power Consumption", record.electrical_specs.power_consumption)
    _row("Frequency", record.electrical_specs.frequency)
    _row("IP Rating", record.electrical_specs.ip_rating)

    st.markdown("**Materials & Compliance**")
    _row("Primary Material", record.materials_compliance.primary_material)
    _row("Finish", record.materials_compliance.finish)
    _row("RoHS Compliant", record.materials_compliance.rohs_compliant)
    _row("REACH Compliant", record.materials_compliance.reach_compliant)
    certs = record.materials_compliance.certifications
    cert_str = ", ".join(c.value for c in certs if c.value) if certs else "_none_"
    c1, c2, _ = st.columns([3, 3, 1])
    c1.write("**Certifications**")
    c2.write(cert_str)

    st.markdown("**Performance Metrics**")
    _row("Operating Temp Min", record.performance_metrics.operating_temp_min)
    _row("Operating Temp Max", record.performance_metrics.operating_temp_max)
    _row("Storage Temp Min", record.performance_metrics.storage_temp_min)
    _row("Storage Temp Max", record.performance_metrics.storage_temp_max)
    _row("Accuracy", record.performance_metrics.accuracy)
    _row("Flow Rate", record.performance_metrics.flow_rate)
    _row("Pressure Rating", record.performance_metrics.pressure_rating)
    _row("Response Time", record.performance_metrics.response_time)

# ---------------------------------------------------------------------------
# Edit form (optional — only shown if reviewer wants to correct values)
# ---------------------------------------------------------------------------
with st.expander("Edit attributes before approving (optional)"):
    st.caption("Leave fields blank to keep the extracted value. Changes are saved when you click Approve (Edited).")

    edited: dict[str, dict] = {}

    st.markdown("**Identifiers**")
    edited["identifiers__part_number"] = _edit_attr("id_pn", record.identifiers.part_number, show_unit=False)
    edited["identifiers__sku"] = _edit_attr("id_sku", record.identifiers.sku, show_unit=False)
    edited["identifiers__manufacturer_name"] = _edit_attr("id_mfr", record.identifiers.manufacturer_name, show_unit=False)
    edited["identifiers__product_family"] = _edit_attr("id_fam", record.identifiers.product_family, show_unit=False)

    st.markdown("**Physical Dimensions**")
    edited["physical_dimensions__length"] = _edit_attr("pd_len", record.physical_dimensions.length)
    edited["physical_dimensions__width"] = _edit_attr("pd_wid", record.physical_dimensions.width)
    edited["physical_dimensions__height"] = _edit_attr("pd_hgt", record.physical_dimensions.height)
    edited["physical_dimensions__weight"] = _edit_attr("pd_wgt", record.physical_dimensions.weight)

    st.markdown("**Electrical Specs**")
    edited["electrical_specs__voltage_input"] = _edit_attr("es_vi", record.electrical_specs.voltage_input)
    edited["electrical_specs__voltage_output"] = _edit_attr("es_vo", record.electrical_specs.voltage_output)
    edited["electrical_specs__current_rating"] = _edit_attr("es_cr", record.electrical_specs.current_rating)
    edited["electrical_specs__power_consumption"] = _edit_attr("es_pc", record.electrical_specs.power_consumption)
    edited["electrical_specs__ip_rating"] = _edit_attr("es_ip", record.electrical_specs.ip_rating, show_unit=False)

# ---------------------------------------------------------------------------
# Reviewer notes + action buttons
# ---------------------------------------------------------------------------
st.markdown("---")
reviewer_name = st.text_input("Your name (reviewer)", key="reviewer_name")
notes = st.text_area("Notes (optional)", key="reviewer_notes")

col_approve, col_edit_approve, col_reject, _ = st.columns([1, 1, 1, 3])

now_iso = datetime.now(timezone.utc).isoformat()


def _apply_edits(rec: ProductRecord, edits: dict[str, dict]) -> ProductRecord:
    """Apply edited field values back onto the record."""
    data = rec.model_dump(mode="json")
    group_map = {
        "identifiers": "identifiers",
        "physical_dimensions": "physical_dimensions",
        "electrical_specs": "electrical_specs",
        "materials_compliance": "materials_compliance",
        "performance_metrics": "performance_metrics",
    }
    for key, field_data in edits.items():
        parts = key.split("__")
        if len(parts) != 2:
            continue
        group, field = parts
        db_group = group_map.get(group)
        if db_group and field in data.get(db_group, {}):
            existing = data[db_group][field] or {}
            # Only overwrite if the reviewer actually typed something
            if field_data.get("value"):
                existing.update(field_data)
                data[db_group][field] = existing
    return ProductRecord.model_validate(data)


with col_approve:
    if st.button("Approve", type="primary", use_container_width=True):
        record.review_status = "approved"
        record.reviewer = reviewer_name or None
        record.reviewer_notes = notes or None
        record.reviewed_at = now_iso
        store.upsert_record(record)
        st.success(f"Approved: {record.document_filename}")
        st.rerun()

with col_edit_approve:
    if st.button("Approve (Edited)", use_container_width=True):
        record = _apply_edits(record, edited)
        record.review_status = "edited"
        record.reviewer = reviewer_name or None
        record.reviewer_notes = notes or None
        record.reviewed_at = now_iso
        store.upsert_record(record)
        st.success(f"Saved edits and approved: {record.document_filename}")
        st.rerun()

with col_reject:
    if st.button("Reject", type="secondary", use_container_width=True):
        record.review_status = "rejected"
        record.reviewer = reviewer_name or None
        record.reviewer_notes = notes or None
        record.reviewed_at = now_iso
        store.upsert_record(record)
        st.warning(f"Rejected: {record.document_filename}")
        st.rerun()
