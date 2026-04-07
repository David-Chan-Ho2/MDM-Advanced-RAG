"""
Streamlit entry point — MDM Advanced RAG Review UI.

Run with:
    streamlit run ui/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path regardless of where streamlit is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from workflow.review_store import ReviewStore

st.set_page_config(
    page_title="MDM Product Extraction Review",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Shared ReviewStore instance stored in session state so all pages reuse it
if "store" not in st.session_state:
    st.session_state.store = ReviewStore()

store: ReviewStore = st.session_state.store
counts = store.count_by_status()

# ---------------------------------------------------------------------------
# Sidebar — navigation metrics
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("MDM RAG Review")
    st.markdown("---")
    st.subheader("Queue Summary")
    st.metric("Pending", counts.get("pending", 0))
    st.metric("Approved", counts.get("approved", 0))
    st.metric("Edited", counts.get("edited", 0))
    st.metric("Rejected", counts.get("rejected", 0))
    st.markdown("---")
    st.caption("Navigate using the pages in the sidebar above.")

# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------
st.title("MDM Product Attribute Extraction")
st.markdown(
    """
Welcome to the **MDM Advanced RAG** data steward review interface.

Use the sidebar to navigate:

| Page | Purpose |
|------|---------|
| **01 Review Queue** | Inspect pending extractions — approve, edit, or reject |
| **02 Approved** | View all approved product records |
| **03 Export** | Download approved records as CSV or JSON for PIM import |
"""
)

total = sum(counts.values())
if total == 0:
    st.info("No extractions in the database yet. Run `python scripts/run_batch.py` first.")
else:
    approved = counts.get("approved", 0)
    pct = round(approved / total * 100) if total else 0
    st.progress(pct / 100, text=f"{approved} / {total} records approved ({pct}%)")
