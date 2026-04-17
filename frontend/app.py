"""
Streamlit entry point.
Pages are auto-discovered from frontend/pages/*.py
"""

import streamlit as st

st.set_page_config(
    page_title="Cortex-Bench-AI - AI Routing System",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation info
with st.sidebar:
    st.markdown("## 🔀 Cortex-Bench-AI - AI Routing System")
    st.markdown("**Privacy-First · Local · Offline**")
    st.divider()
    st.markdown("### Models Available")
    st.markdown("- ⚡ Phi-3 Mini (coding)")
    st.markdown("- ⚖️ Llama 3.2 3B (balanced)")
    st.markdown("- 🧠 Mistral 7B (reasoning)")
    st.divider()
    st.markdown("### Privacy Shield")
    st.markdown("🛡️ Active — PII masked before inference")
    st.divider()
    st.caption("All inference runs locally via Ollama. Zero external API calls.")

st.title("🔀 Cortex-Bench-AI - Intelligent AI Routing System")
st.markdown("""
Welcome! This system automatically selects the best local LLM for your query
while protecting any sensitive data you enter.

**Navigate using the sidebar** to access:
- 💬 **Chat** — real-time AI assistant with routing transparency
- 🔒 **Privacy Audit** — view PII detection events
- 📊 **Dashboard** — routing statistics and model performance
""")