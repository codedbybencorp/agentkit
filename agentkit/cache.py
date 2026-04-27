"""Redis-backed caching for AgentKit."""

import hashlib
import json
import os
from typing import Any

import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

_pool: redis.Redis | None = None


async def _redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(REDIS_URL, decode_responses=True)
    return _pool


def _hash_key(prefix: str, data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return f"agentkit:{prefix}:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"


async def get(prefix: str, data: Any) -> dict | None:
    try:
        r = await _redis()
        key = _hash_key(prefix, data)
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def set(prefix: str, data: Any, result: dict, ttl: int = 3600):
    try:
        r = await _redis()
        key = _hash_key(prefix, data)
        await r.setex(key, ttl, json.dumps(result, default=str))
    except Exception:
        pass
