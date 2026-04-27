"""AgentKit API — production-ready tools for AI agents."""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agentkit import cache, memory, metering, ratelimit, research, sandbox, scrape, vision
from agentkit.errors import (
    AgentKitError,
    InvalidQueryError,
    RateLimitedError,
    TimeoutError,
    UpstreamError,
    to_response,
)
from agentkit.models import (
    MemoryQueryRequest,
    MemoryWriteRequest,
    ResearchRequest,
    SandboxRequest,
    ScrapeRequest,
    VisionRequest,
)

API_KEYS = set(os.environ.get("AGENTKIT_API_KEYS", "test-key-123").split(","))


def verify_key(x_api_key: str | None = Header(None, alias="X-API-Key")):
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.environ.get("AGENTKIT_DATA", ".data"), exist_ok=True)
    yield


app = FastAPI(
    title="AgentKit",
    description="Production tools for AI agents: research, memory, vision, sandbox, scrape.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handler ──
@app.exception_handler(AgentKitError)
async def agentkit_exception_handler(request: Request, exc: AgentKitError):
    return to_response(exc)


# ── Health ──
@app.get("/")
def root():
    return {
        "name": "AgentKit",
        "version": "0.2.0",
        "endpoints": ["/research", "/memory/write", "/memory/query", "/vision", "/sandbox", "/scrape", "/usage"],
        "features": ["streaming", "caching", "metering", "ratelimiting"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Middleware: rate limiting + metering ──
@app.middleware("http")
async def middleware(request: Request, call_next):
    if request.url.path in ["/", "/health"]:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key", "anonymous")
    allowed, remaining, retry_after = ratelimit.check(api_key, request.url.path)

    if not allowed:
        metering.record(api_key, request.url.path, status="rate_limited")
        return to_response(RateLimitedError(retry_after))

    start = time.time()
    status = "success"
    try:
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
    except AgentKitError as e:
        status = e.code.lower()
        raise
    except Exception:
        status = "error"
        raise
    finally:
        latency_ms = int((time.time() - start) * 1000)
        metering.record(api_key, request.url.path, latency_ms=latency_ms, status=status)


# ── Streaming Research ──
@app.post("/research")
async def do_research(req: ResearchRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)

    if not req.query or len(req.query) > 500:
        raise InvalidQueryError("Query must be 1-500 characters.")

    # Check cache
    cached = await cache.get("research", {"query": req.query, "max": req.max_sources})
    if cached and req.synthesize:
        cached["cached"] = True
        return cached

    async def event_stream():
        t0 = time.time()
        yield f"event: status\ndata: {json.dumps({'step': 'search', 'message': 'Searching the web...'})}\n\n"

        try:
            sources = await research.search_duckduckgo(req.query, req.max_sources)
        except Exception:
            yield f"event: error\ndata: {json.dumps({'error_code': 'UPSTREAM_ERROR', 'message': 'Search failed'})}\n\n"
            return

        yield f"event: sources\ndata: {json.dumps({'count': len(sources)})}\n\n"
        search_time = time.time() - t0

        yield f"event: status\ndata: {json.dumps({'step': 'read', 'message': f'Reading {min(4, len(sources))} sources...'})}\n\n"
        read_tasks = [research.extract_text(s) for s in sources[:4]]
        try:
            read_sources = await asyncio.wait_for(asyncio.gather(*read_tasks), timeout=20)
        except asyncio.TimeoutError:
            yield f"event: error\ndata: {json.dumps({'error_code': 'TIMEOUT', 'message': 'Reading sources timed out'})}\n\n"
            return

        read_time = time.time() - t0 - search_time

        answer = ""
        if req.synthesize:
            yield f"event: status\ndata: {json.dumps({'step': 'synthesize', 'message': 'Synthesizing answer...'})}\n\n"
            try:
                answer = await asyncio.wait_for(
                    research.synthesize(req.query, list(read_sources), req.system_prompt),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                yield f"event: error\ndata: {json.dumps({'error_code': 'TIMEOUT', 'message': 'Synthesis timed out'})}\n\n"
                return

        result = {
            "query": req.query,
            "answer": answer,
            "sources": [{"url": s.url, "title": s.title, "domain": s.domain} for s in read_sources],
            "search_time": round(search_time, 2),
            "read_time": round(read_time, 2),
        }

        # Cache result
        await cache.set("research", {"query": req.query, "max": req.max_sources}, result, ttl=3600)

        yield f"event: done\ndata: {json.dumps(result)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── Memory ──
@app.post("/memory/write")
async def memory_write(req: MemoryWriteRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    doc_id = memory.write(req.agent_id, req.namespace, req.text, req.metadata)
    return {"id": doc_id, "status": "stored"}


@app.post("/memory/query")
async def memory_query(req: MemoryQueryRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    results = memory.query(req.agent_id, req.namespace, req.query, req.top_k)
    return {"results": results}


# ── Vision ──
@app.post("/vision")
async def do_vision(req: VisionRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    try:
        desc = await asyncio.wait_for(vision.describe(req.image_base64, req.image_url, req.prompt), timeout=30)
        return {"description": desc, "model": "gpt-4o-mini or ollama"}
    except asyncio.TimeoutError:
        raise TimeoutError()


# ── Sandbox ──
@app.post("/sandbox")
async def do_sandbox(req: SandboxRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    try:
        result = await asyncio.wait_for(sandbox.run(req.code, req.language, req.timeout), timeout=req.timeout + 5)
        return result
    except asyncio.TimeoutError:
        raise TimeoutError()


# ── Scrape ──
@app.post("/scrape")
async def do_scrape(req: ScrapeRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)

    # Check cache
    cached = await cache.get("scrape", {"url": req.url})
    if cached:
        cached["cached"] = True
        return cached

    try:
        result = await asyncio.wait_for(scrape.scrape_page(req.url, req.format), timeout=15)
        await cache.set("scrape", {"url": req.url}, result, ttl=1800)
        return result
    except asyncio.TimeoutError:
        raise TimeoutError()
    except Exception:
        raise UpstreamError("Failed to fetch page")


# ── Usage ──
@app.get("/usage")
def get_usage(api_key: str = Header(..., alias="X-API-Key"), hours: int = 24):
    verify_key(api_key)
    return metering.get_stats(api_key, hours)
