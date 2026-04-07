"""
Approved Records — read-only table view of all approved/edited product records.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from config.schema import AttributeValue, ProductRecord
from workflow.review_store import ReviewStore

st.set_page_config(page_title="Approved Records", layout="wide")

if "store" not in st.session_state:
    st.session_state.store = ReviewStore()
store: ReviewStore = st.session_state.store

st.title("Approved Records")


def _val(attr: AttributeValue | None) -> str:
    if attr is None or attr.value is None:
        return ""
    return f"{attr.value} {attr.unit or ''}".strip()


def _records_to_df(records: list[ProductRecord]) -> pd.DataFrame:
    rows = []
    for r in records:
        certs = r.materials_compliance.certifications or []
        rows.append(
            {
                "Filename": r.document_filename,
                "Status": r.review_status,
                "Part #": _val(r.identifiers.part_number),
                "Manufacturer": _val(r.identifiers.manufacturer_name),
                "Family": _val(r.identifiers.product_family),
                "L×W×H": " × ".join(
                    v
                    for v in [
                        _val(r.physical_dimensions.length),
                        _val(r.physical_dimensions.width),
                        _val(r.physical_dimensions.height),
                    ]
                    if v
                ),
                "Weight": _val(r.physical_dimensions.weight),
                "Voltage In": _val(r.electrical_specs.voltage_input),
                "Power": _val(r.electrical_specs.power_consumption),
                "IP Rating": _val(r.electrical_specs.ip_rating),
                "Material": _val(r.materials_compliance.primary_material),
                "RoHS": _val(r.materials_compliance.rohs_compliant),
                "Certifications": ", ".join(c.value for c in certs if c.value),
                "Op Temp": (
                    f"{_val(r.performance_metrics.operating_temp_min)} "
                    f"to {_val(r.performance_metrics.operating_temp_max)}"
                ).strip("to "),
                "Reviewer": r.reviewer or "",
                "Reviewed At": r.reviewed_at or "",
            }
        )
    return pd.DataFrame(rows)


# Fetch approved + edited records
approved = store.list_records(review_status="approved")
edited = store.list_records(review_status="edited")
all_approved = approved + edited

if not all_approved:
    st.info("No approved records yet. Go to the Review Queue to approve extractions.")
    st.stop()

st.markdown(f"**{len(all_approved)} records approved** ({len(approved)} clean, {len(edited)} with edits)")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Filters")
    status_filter = st.multiselect(
        "Status",
        ["approved", "edited"],
        default=["approved", "edited"],
    )
    search = st.text_input("Search filename / part number")

filtered = [
    r for r in all_approved
    if r.review_status in status_filter
    and (
        not search
        or search.lower() in r.document_filename.lower()
        or search.lower() in (r.identifiers.part_number.value or "").lower()
    )
]

st.caption(f"Showing {len(filtered)} of {len(all_approved)} records")

df = _records_to_df(filtered)
st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Detail view — click a row to expand
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Record Detail")

if filtered:
    selected_fn = st.selectbox("Select a record for full detail", [r.document_filename for r in filtered])
    detail: ProductRecord = next(r for r in filtered if r.document_filename == selected_fn)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Identifiers**")
        st.json(
            {k: v for k, v in detail.identifiers.model_dump(mode="json").items() if v},
            expanded=False,
        )
        st.markdown("**Physical Dimensions**")
        st.json(
            {k: v for k, v in detail.physical_dimensions.model_dump(mode="json").items() if v},
            expanded=False,
        )
        st.markdown("**Electrical Specs**")
        st.json(
            {k: v for k, v in detail.electrical_specs.model_dump(mode="json").items() if v},
            expanded=False,
        )

    with col2:
        st.markdown("**Materials & Compliance**")
        st.json(
            {k: v for k, v in detail.materials_compliance.model_dump(mode="json").items() if v},
            expanded=False,
        )
        st.markdown("**Performance Metrics**")
        st.json(
            {k: v for k, v in detail.performance_metrics.model_dump(mode="json").items() if v},
            expanded=False,
        )
        st.markdown("**Review Info**")
        st.json(
            {
                "status": detail.review_status,
                "reviewer": detail.reviewer,
                "notes": detail.reviewer_notes,
                "reviewed_at": detail.reviewed_at,
            },
            expanded=True,
        )
