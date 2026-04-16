-- Routing audit log
CREATE TABLE IF NOT EXISTS routing_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    session_id  TEXT,
    intent      TEXT    NOT NULL,
    complexity  TEXT    NOT NULL,
    selected_model  TEXT NOT NULL,
    fallback_model  TEXT NOT NULL,
    capability_score REAL,
    router_latency_ms REAL,
    total_latency_ms  REAL,
    tokens_generated  INTEGER,
    tokens_per_sec    REAL
);

-- Privacy firewall events
CREATE TABLE IF NOT EXISTS privacy_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    session_id  TEXT,
    pii_count   INTEGER NOT NULL,
    entity_types TEXT,           -- JSON array of entity type strings
    is_sensitive INTEGER NOT NULL, -- 0 or 1
    sensitivity_score REAL,
    firewall_latency_ms REAL
);

-- Query history (masked queries only — never store originals)
CREATE TABLE IF NOT EXISTS query_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    session_id  TEXT,
    masked_query TEXT   NOT NULL,   -- NEVER store original with PII
    model_used  TEXT,
    intent      TEXT,
    response_length INTEGER,
    success     INTEGER NOT NULL DEFAULT 1
);