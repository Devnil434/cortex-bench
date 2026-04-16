"""
Privacy Audit page — shows PII detection events from the audit DB.
"""

import requests
import pandas as pd
import plotly.express as px
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Privacy Audit", page_icon="🔒", layout="wide")
st.title("🔒 Privacy Audit Trail")
st.markdown(
    "All PII is detected and masked **before** reaching any LLM. "
    "Original values are never stored. This page shows anonymized event metadata only."
)

try:
    resp = requests.get(f"{API_BASE}/audit/stats", timeout=5)
    stats = resp.json()
except Exception:
    st.error("Cannot reach API server. Start with: `uvicorn backend.server:app --reload`")
    st.stop()

privacy = stats.get("privacy_summary", {})
col1, col2, col3 = st.columns(3)
col1.metric("Total PII Events", privacy.get("total_pii", 0))
col2.metric("Sensitive Queries", privacy.get("sensitive_count", 0))
col3.metric("PII Detected Queries", privacy.get("total", 0))

st.divider()

# Model usage pie
model_data = stats.get("model_usage", [])
if model_data:
    df = pd.DataFrame(model_data)
    fig = px.pie(df, names="selected_model", values="count", title="Model Usage Distribution")
    st.plotly_chart(fig, use_container_width=True)

st.info(
    "**Privacy Guarantee:** Only masked queries are sent to Ollama. "
    "PII placeholders like `<PERSON_1>` and `<IN_AADHAAR_1>` replace real values. "
    "Original data never leaves this process."
)