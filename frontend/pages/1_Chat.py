"""
Chat page — SSE token streaming with routing + privacy metadata display.
"""

import json
import time
import uuid
import requests
import sseclient
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")
st.title("💬 Chat")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "privacy_log" not in st.session_state:
    st.session_state.privacy_log = []


# ── Sidebar Settings ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
    show_routing = st.toggle("Show routing info", value=True)
    show_privacy = st.toggle("Show privacy badge", value=True)
    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

MODEL_COLORS = {
    "phi3:mini": "#4a9eed",
    "llama3.2:3b": "#22c55e",
    "mistral:7b": "#8b5cf6",
}

MODEL_ICONS = {
    "phi3:mini": "⚡",
    "llama3.2:3b": "⚖️",
    "mistral:7b": "🧠",
}

INTENT_ICONS = {
    "coding": "💻",
    "reasoning": "🧮",
    "summarization": "📝",
    "factual_qa": "❓",
    "creative": "🎨",
    "sensitive": "🔒",
    "unknown": "❔",
}


def privacy_badge(privacy_info: dict) -> str:
    if privacy_info.get("is_sensitive"):
        types = ", ".join(privacy_info.get("entity_types", []))
        return f"🔴 **PII Detected** `{privacy_info['pii_count']} entities` — {types}"
    elif privacy_info.get("pii_count", 0) > 0:
        return f"🟡 **PII Masked** `{privacy_info['pii_count']} entities`"
    else:
        return "🟢 **No PII Detected**"


def model_badge(routing_info: dict) -> str:
    model = routing_info.get("model", "unknown")
    icon = MODEL_ICONS.get(model, "🤖")
    intent = routing_info.get("intent", "unknown")
    intent_icon = INTENT_ICONS.get(intent, "❔")
    return (
        f"{icon} **{model}** · "
        f"{intent_icon} intent: `{intent}` · "
        f"complexity: `{routing_info.get('complexity', '?')}`"
    )


def stream_chat(query: str, session_id: str, temperature: float):
    """
    Stream tokens from SSE endpoint.
    Yields (token, meta_event_or_None, done_event_or_None).
    """
    url = (
        f"{API_BASE}/chat/stream"
        f"?query={requests.utils.quote(query)}"
        f"&session_id={session_id}"
        f"&temperature={temperature}"
    )
    try:
        response = requests.get(url, stream=True, timeout=120)
        client = sseclient.SSEClient(response)
        for event in client.events():
            if not event.data:
                continue
            data = json.loads(event.data)
            yield data
    except requests.exceptions.ConnectionError:
        yield {"type": "error", "message": "Cannot reach API server. Is it running?"}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


# ── Chat History ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and show_routing and "routing" in msg:
            with st.expander("🔀 Routing & Privacy Info", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Routing Decision**")
                    st.markdown(model_badge(msg["routing"]))
                    st.caption(msg["routing"].get("reasoning", "")[:200])
                with col2:
                    st.markdown("**Privacy Status**")
                    if show_privacy:
                        st.markdown(privacy_badge(msg.get("privacy", {})))
                if "metrics" in msg:
                    m = msg["metrics"]
                    st.caption(
                        f"⏱ {m.get('total_latency_ms', 0):.0f}ms · "
                        f"🔤 {m.get('tokens_per_sec', 0):.1f} tok/s · "
                        f"📊 {m.get('tokens_generated', 0)} tokens"
                    )


# ── Chat Input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask anything... (your data stays local)"):
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Stream assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        routing_placeholder = st.empty()
        full_response = ""
        meta = {}
        done_metrics = {}

        for event in stream_chat(prompt, st.session_state.session_id, temperature):
            etype = event.get("type")

            if etype == "meta":
                meta = event
                if show_routing:
                    routing_placeholder.info(
                        f"🔀 Routing to **{event['routing']['model']}** · "
                        f"intent: `{event['routing']['intent']}`"
                    )
                if show_privacy and event["privacy"]["pii_count"] > 0:
                    st.warning(privacy_badge(event["privacy"]))

            elif etype == "token":
                full_response += event["content"]
                placeholder.markdown(full_response + "▌")

            elif etype == "done":
                done_metrics = event.get("metrics", {})
                placeholder.markdown(full_response)
                routing_placeholder.empty()

            elif etype == "error":
                st.error(f"Error: {event['message']}")
                break

        # Store message with metadata
        msg_record = {
            "role": "assistant",
            "content": full_response,
            "routing": meta.get("routing", {}),
            "privacy": meta.get("privacy", {}),
            "metrics": done_metrics,
        }
        st.session_state.messages.append(msg_record)

        # Show routing summary
        if show_routing and meta.get("routing"):
            with st.expander("🔀 Routing & Privacy Info", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Routing Decision**")
                    st.markdown(model_badge(meta["routing"]))
                with col2:
                    st.markdown("**Privacy Status**")
                    if show_privacy:
                        st.markdown(privacy_badge(meta.get("privacy", {})))
                if done_metrics:
                    st.caption(
                        f"⏱ {done_metrics.get('total_latency_ms', 0):.0f}ms · "
                        f"🔤 {done_metrics.get('tokens_per_sec', 0):.1f} tok/s"
                    )
                    