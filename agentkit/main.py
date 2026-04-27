"""AgentKit API — tools for AI agents."""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentkit.models import (
    MemoryQueryRequest,
    MemoryWriteRequest,
    ResearchRequest,
    SandboxRequest,
    ScrapeRequest,
    VisionRequest,
)
from agentkit import memory, research, sandbox, scrape, vision

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
    description="Tools for AI agents: research, memory, vision, sandbox, scrape.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──
@app.get("/")
def root():
    return {"name": "AgentKit", "version": "0.1.0", "endpoints": [
        "/research", "/memory/write", "/memory/query",
        "/vision", "/sandbox", "/scrape",
    ]}


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Research ──
@app.post("/research")
async def do_research(req: ResearchRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    t0 = time.time()
    sources = await research.search_duckduckgo(req.query, req.max_sources)
    search_time = time.time() - t0

    read_tasks = [research.extract_text(s) for s in sources[:4]]
    read_sources = await __import__("asyncio").gather(*read_tasks)
    read_time = time.time() - t0 - search_time

    answer = ""
    if req.synthesize:
        answer = await research.synthesize(req.query, list(read_sources), req.system_prompt)

    return {
        "query": req.query,
        "answer": answer,
        "sources": [{"url": s.url, "title": s.title, "domain": s.domain, "text": s.text[:500]} for s in read_sources],
        "search_time": round(search_time, 2),
        "read_time": round(read_time, 2),
    }


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
    desc = await vision.describe(req.image_base64, req.image_url, req.prompt)
    return {"description": desc, "model": "gpt-4o-mini or ollama"}


# ── Sandbox ──
@app.post("/sandbox")
async def do_sandbox(req: SandboxRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    result = await sandbox.run(req.code, req.language, req.timeout)
    return result


# ── Scrape ──
@app.post("/scrape")
async def do_scrape(req: ScrapeRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_key(api_key)
    result = await scrape.scrape_page(req.url, req.format)
    return result


# ── Middleware: usage tracking ──
@app.middleware("http")
async def track_usage(request: Request, call_next):
    if request.url.path in ["/", "/health"]:
        return await call_next(request)
    start = time.time()
    response = await call_next(request)
    # Simple console logging — replace with DB in production
    print(f"[{request.method}] {request.url.path} — {round((time.time()-start)*1000)}ms")
    return response
