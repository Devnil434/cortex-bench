"""
Routing Dashboard — latency, throughput, model selection stats.
"""

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Routing Dashboard", page_icon="📊", layout="wide")
st.title("📊 Routing Dashboard")

try:
    resp = requests.get(f"{API_BASE}/audit/stats", timeout=5)
    stats = resp.json()
except Exception:
    st.error("Cannot reach API server.")
    st.stop()

routing = stats.get("routing_by_intent", [])
model_usage = stats.get("model_usage", [])

if not routing:
    st.info("No routing data yet. Start chatting to generate stats!")
    st.stop()

df = pd.DataFrame(routing)

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(
        df, x="intent", y="count",
        title="Queries by Intent",
        color="intent",
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(
        df, x="intent", y="avg_tps",
        title="Avg Tokens/sec by Intent",
        color="intent",
    )
    st.plotly_chart(fig, use_container_width=True)

# Latency heatmap
st.subheader("Avg Latency by Intent")
fig = px.bar(df, x="intent", y="avg_latency", title="Average Response Latency (ms)")
st.plotly_chart(fig, use_container_width=True)

# Model usage
if model_usage:
    df_m = pd.DataFrame(model_usage)
    fig = px.pie(df_m, names="selected_model", values="count", title="Model Selection Distribution")
    st.plotly_chart(fig, use_container_width=True)