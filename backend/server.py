"""
FastAPI server — main orchestration layer.
Exposes:
  POST /chat          — full response
  GET  /chat/stream   — SSE token stream
  GET  /health        — system health
  GET  /audit/stats   — routing + privacy statistics
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from .privacy.firewall import PrivacyFirewall
from .intent_classifier import IntentClassifier
from .router import SmartRouter
from .models.ollama_client import stream_generate, generate_sync, InferenceMetrics
from .db.audit_logger import init_db, log_routing_event, log_privacy_event, log_query
from .db.audit_logger import DB_PATH


# ── Startup / Shutdown ────────────────────────────────────────────────────────

firewall: PrivacyFirewall
intent_clf: IntentClassifier
router: SmartRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    global firewall, intent_clf, router
    logger.info("Initializing AI Routing System...")
    await init_db()
    firewall = PrivacyFirewall(model_name="en_core_web_lg")
    intent_clf = IntentClassifier()
    router = SmartRouter()
    logger.info("All components ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Routing System with Privacy Firewall",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    force_model: str | None = None   # override routing (for testing)


class RoutingInfo(BaseModel):
    selected_model: str
    fallback_model: str
    intent: str
    complexity: str
    capability_score: float
    reasoning: str


class PrivacyInfo(BaseModel):
    pii_detected: bool
    pii_count: int
    entity_types: list[str]
    is_sensitive: bool
    sensitivity_score: float


class ChatResponse(BaseModel):
    response: str
    session_id: str
    routing: RoutingInfo
    privacy: PrivacyInfo
    metrics: dict
    masked_query: str   # for transparency — never the original if PII found


# ── Full Response Endpoint ────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    t_start = time.perf_counter()

    # Step 1: Privacy Firewall
    fw_result = firewall.scan(req.query)

    # Step 2: Intent Classification (on masked query)
    intent_result = intent_clf.classify(
        fw_result.masked_query,
        is_sensitive=fw_result.is_sensitive,
    )

    # Step 3: Smart Routing
    decision = router.route(intent_result, fw_result.masked_query)
    model = req.force_model or decision.selected_model

    # Step 4: LLM Inference
    try:
        response_text, metrics = await generate_sync(
            model=model,
            prompt=fw_result.masked_query,
            temperature=req.temperature,
        )
    except Exception as e:
        logger.warning(f"Primary model {model} failed, trying fallback: {e}")
        response_text, metrics = await generate_sync(
            model=decision.fallback_model,
            prompt=fw_result.masked_query,
            temperature=req.temperature,
        )
        model = decision.fallback_model

    total_ms = round((time.perf_counter() - t_start) * 1000, 2)

    # Audit logging (fire-and-forget, don't block response)
    import asyncio
    asyncio.create_task(log_privacy_event(
        req.session_id, fw_result.pii_count,
        [e["type"] for e in fw_result.entities_found],
        fw_result.is_sensitive, fw_result.sensitivity_score,
        fw_result.processing_time_ms,
    ))
    asyncio.create_task(log_routing_event(
        req.session_id, decision.intent, decision.complexity,
        model, decision.fallback_model, decision.capability_score,
        decision.latency_ms, total_ms,
        metrics.tokens_generated, metrics.tokens_per_sec,
    ))
    asyncio.create_task(log_query(
        req.session_id, fw_result.masked_query, model,
        decision.intent, len(response_text),
    ))
    router.record_inference(model, metrics.tokens_per_sec)

    return ChatResponse(
        response=response_text,
        session_id=req.session_id,
        masked_query=fw_result.masked_query,
        routing=RoutingInfo(
            selected_model=model,
            fallback_model=decision.fallback_model,
            intent=decision.intent,
            complexity=decision.complexity,
            capability_score=decision.capability_score,
            reasoning=decision.reasoning,
        ),
        privacy=PrivacyInfo(
            pii_detected=fw_result.pii_count > 0,
            pii_count=fw_result.pii_count,
            entity_types=[e["type"] for e in fw_result.entities_found],
            is_sensitive=fw_result.is_sensitive,
            sensitivity_score=fw_result.sensitivity_score,
        ),
        metrics={
            "tokens_generated": metrics.tokens_generated,
            "tokens_per_sec": metrics.tokens_per_sec,
            "time_to_first_token_ms": metrics.time_to_first_token_ms,
            "total_latency_ms": total_ms,
            "firewall_ms": fw_result.processing_time_ms,
            "router_ms": decision.latency_ms,
        },
    )


# ── SSE Streaming Endpoint ────────────────────────────────────────────────────

@app.get("/chat/stream")
async def chat_stream(
    query: str = Query(..., min_length=1),
    session_id: str = Query(default_factory=lambda: str(uuid.uuid4())),
    temperature: float = Query(default=0.7),
):
    """
    Server-Sent Events stream.
    Events:
      data: {"type":"meta","routing":{...},"privacy":{...}}
      data: {"type":"token","content":"..."}
      data: {"type":"done","metrics":{...}}
    """
    fw_result = firewall.scan(query)
    intent_result = intent_clf.classify(fw_result.masked_query, fw_result.is_sensitive)
    decision = router.route(intent_result, fw_result.masked_query)
    model = decision.selected_model

    async def event_generator() -> AsyncIterator[dict]:
        # First event: routing metadata
        yield {
            "data": json.dumps({
                "type": "meta",
                "routing": {
                    "model": model,
                    "intent": decision.intent,
                    "complexity": decision.complexity,
                },
                "privacy": {
                    "pii_count": fw_result.pii_count,
                    "is_sensitive": fw_result.is_sensitive,
                    "entity_types": [e["type"] for e in fw_result.entities_found],
                },
            })
        }

        # Stream tokens
        collected = []
        final_metrics = None
        async for token, metrics in stream_generate(
            model=model,
            prompt=fw_result.masked_query,
            temperature=temperature,
        ):
            collected.append(token)
            yield {"data": json.dumps({"type": "token", "content": token})}
            if metrics:
                final_metrics = metrics

        # Final event: metrics
        if final_metrics:
            router.record_inference(model, final_metrics.tokens_per_sec)
            yield {
                "data": json.dumps({
                    "type": "done",
                    "metrics": {
                        "tokens_per_sec": final_metrics.tokens_per_sec,
                        "total_latency_ms": final_metrics.total_latency_ms,
                        "tokens_generated": final_metrics.tokens_generated,
                    },
                })
            }

    return EventSourceResponse(event_generator())


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    import ollama as _ollama
    try:
        models_resp = _ollama.list()
        models = [m["name"] for m in models_resp.get("models", [])]
        ollama_ok = True
    except Exception as e:
        models = []
        ollama_ok = False

    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": ollama_ok,
        "available_models": models,
        "firewall": "ok",
        "db": str(DB_PATH),
    }


# ── Audit Stats ───────────────────────────────────────────────────────────────

@app.get("/audit/stats")
async def audit_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT intent, COUNT(*) as count, AVG(tokens_per_sec) as avg_tps, "
            "AVG(total_latency_ms) as avg_latency FROM routing_events GROUP BY intent"
        )
        routing = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT COUNT(*) as total, SUM(pii_count) as total_pii, "
            "SUM(is_sensitive) as sensitive_count FROM privacy_events"
        )
        privacy = dict(await cursor.fetchone())

        cursor = await db.execute(
            "SELECT selected_model, COUNT(*) as count FROM routing_events GROUP BY selected_model"
        )
        model_usage = [dict(r) for r in await cursor.fetchall()]

    return {
        "routing_by_intent": routing,
        "privacy_summary": privacy,
        "model_usage": model_usage,
    }
