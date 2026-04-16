"""
Async audit logger — writes routing + privacy events to SQLite.
Uses aiosqlite for non-blocking writes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import aiosqlite
from loguru import logger

DB_PATH = Path(os.getenv("AUDIT_DB_PATH", "data/audit.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db() -> None:
    """Initialize the SQLite database and create tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        schema = SCHEMA_PATH.read_text()
        await db.executescript(schema)
        await db.commit()
    logger.info(f"Audit DB initialized at {DB_PATH}")


async def log_routing_event(
    session_id: str,
    intent: str,
    complexity: str,
    selected_model: str,
    fallback_model: str,
    capability_score: float,
    router_latency_ms: float,
    total_latency_ms: float,
    tokens_generated: int,
    tokens_per_sec: float,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO routing_events
            (session_id, intent, complexity, selected_model, fallback_model,
             capability_score, router_latency_ms, total_latency_ms,
             tokens_generated, tokens_per_sec)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (session_id, intent, complexity, selected_model, fallback_model,
             capability_score, router_latency_ms, total_latency_ms,
             tokens_generated, tokens_per_sec),
        )
        await db.commit()


async def log_privacy_event(
    session_id: str,
    pii_count: int,
    entity_types: list[str],
    is_sensitive: bool,
    sensitivity_score: float,
    firewall_latency_ms: float,
) -> None:
    if pii_count == 0:
        return  # Don't log clean queries to save space
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO privacy_events
            (session_id, pii_count, entity_types, is_sensitive,
             sensitivity_score, firewall_latency_ms)
            VALUES (?,?,?,?,?,?)
            """,
            (session_id, pii_count, json.dumps(entity_types),
             int(is_sensitive), sensitivity_score, firewall_latency_ms),
        )
        await db.commit()


async def log_query(
    session_id: str,
    masked_query: str,
    model_used: str,
    intent: str,
    response_length: int,
    success: bool = True,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO query_history
            (session_id, masked_query, model_used, intent, response_length, success)
            VALUES (?,?,?,?,?,?)
            """,
            (session_id, masked_query, model_used, intent, response_length, int(success)),
        )
        await db.commit()
        