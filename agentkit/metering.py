"""SQLite usage metering and analytics."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DATA_DIR = os.environ.get("AGENTKIT_DATA", ".data")
DB_PATH = os.path.join(DATA_DIR, "usage.db")


def _init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                requests INTEGER DEFAULT 1,
                tokens_used INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success',
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_key_time ON usage(api_key, timestamp)
        """)
        conn.commit()


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def record(api_key: str, endpoint: str, tokens: int = 0, latency_ms: int = 0, status: str = "success"):
    _init_db()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO usage (api_key, endpoint, requests, tokens_used, latency_ms, status, timestamp) VALUES (?, ?, 1, ?, ?, ?, ?)",
            (api_key, endpoint, tokens, latency_ms, status, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_stats(api_key: str | None = None, hours: int = 24) -> dict:
    _init_db()
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        if api_key:
            rows = conn.execute(
                "SELECT endpoint, SUM(requests) as total, SUM(tokens_used) as tokens, AVG(latency_ms) as avg_latency FROM usage WHERE api_key = ? AND timestamp > datetime('now', '-{} hours') GROUP BY endpoint".format(hours),
                (api_key,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT endpoint, SUM(requests) as total, SUM(tokens_used) as tokens, AVG(latency_ms) as avg_latency FROM usage WHERE timestamp > datetime('now', '-{} hours') GROUP BY endpoint".format(hours),
            ).fetchall()
        return {
            "period_hours": hours,
            "endpoints": [
                {
                    "endpoint": r["endpoint"],
                    "requests": r["total"],
                    "tokens": r["tokens"],
                    "avg_latency_ms": round(r["avg_latency"] or 0, 1),
                }
                for r in rows
            ],
        }
