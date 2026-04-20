"""
Export — download approved records as CSV or JSON for PIM import.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from config.schema import ProductRecord
from config.settings import settings
from workflow.exporter import PIMExporter
from workflow.review_store import ReviewStore

st.set_page_config(page_title="Export", layout="wide")

if "store" not in st.session_state:
    st.session_state.store = ReviewStore()
store: ReviewStore = st.session_state.store
exporter = PIMExporter()

st.title("Export to PIM")

# ---------------------------------------------------------------------------
# Fetch records
# ---------------------------------------------------------------------------
approved = store.list_records(review_status="approved")
edited = store.list_records(review_status="edited")
all_records: list[ProductRecord] = approved + edited

counts = store.count_by_status()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ready to export", len(all_records))
col2.metric("Pending review", counts.get("pending", 0))
col3.metric("Rejected", counts.get("rejected", 0))
col4.metric("Total in DB", sum(counts.values()))

st.markdown("---")

if not all_records:
    st.warning("No approved records to export. Review and approve extractions first.")
    st.stop()

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
st.subheader("Filter records for export")

col_a, col_b = st.columns(2)
with col_a:
    include_edited = st.checkbox("Include edited records", value=True)
with col_b:
    search = st.text_input("Filter by filename or part number")

export_records = [
    r for r in all_records
    if (include_edited or r.review_status == "approved")
    and (
        not search
        or search.lower() in r.document_filename.lower()
        or search.lower() in (r.identifiers.part_number.value or "").lower()
    )
]

st.caption(f"{len(export_records)} records selected for export")

if not export_records:
    st.info("No records match the current filter.")
    st.stop()

# ---------------------------------------------------------------------------
# Preview table
# ---------------------------------------------------------------------------
with st.expander("Preview selected records", expanded=False):
    preview_data = [
        {
            "Filename": r.document_filename,
            "Status": r.review_status,
            "Part #": r.identifiers.part_number.value if r.identifiers.part_number else "",
            "Manufacturer": r.identifiers.manufacturer_name.value if r.identifiers.manufacturer_name else "",
            "Reviewer": r.reviewer or "",
        }
        for r in export_records
    ]
    st.dataframe(preview_data, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Download buttons
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Download")

col_csv, col_json = st.columns(2)

with col_csv:
    st.markdown("**CSV** — flat column format for PIM import")
    st.caption("Columns: `group__field__value`, `group__field__unit`, `group__field__confidence`")
    csv_data = exporter.to_csv(export_records)
    st.download_button(
        label=f"Download CSV ({len(export_records)} records)",
        data=csv_data,
        file_name="pim_export.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

with col_json:
    st.markdown("**JSON** — full nested ProductRecord payloads")
    st.caption("Includes all attribute fields, confidence levels, and source chunk IDs")
    json_data = exporter.to_json(export_records)
    st.download_button(
        label=f"Download JSON ({len(export_records)} records)",
        data=json_data,
        file_name="pim_export.json",
        mime="application/json",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Save to disk option
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Save to server")
st.caption(f"Writes files to `{settings.EXPORTS_DIR}/`")

col_save, _ = st.columns([1, 3])
with col_save:
    if st.button("Save CSV + JSON to exports folder", use_container_width=True):
        exports_dir = Path(settings.EXPORTS_DIR)
        exports_dir.mkdir(parents=True, exist_ok=True)

        csv_path = exports_dir / "pim_export.csv"
        json_path = exports_dir / "pim_export.json"

        csv_path.write_text(exporter.to_csv(export_records), encoding="utf-8")
        json_path.write_text(exporter.to_json(export_records), encoding="utf-8")

        st.success(f"Saved {len(export_records)} records to `{exports_dir}/`")
        st.code(f"{csv_path}\n{json_path}")
