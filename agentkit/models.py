"""Shared Pydantic models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_sources: int = Field(default=8, ge=1, le=20)
    synthesize: bool = Field(default=True)
    system_prompt: Optional[str] = None


class ResearchResponse(BaseModel):
    query: str
    answer: str
    sources: list[dict]
    search_time: float
    read_time: float
    model: str = "ollama/gemma-4-e4b"


class MemoryWriteRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    namespace: str = Field(default="default")
    text: str = Field(..., min_length=1)
    metadata: dict = Field(default_factory=dict)


class MemoryQueryRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    namespace: str = Field(default="default")
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class MemoryResult(BaseModel):
    text: str
    distance: float
    metadata: dict
    created_at: Optional[str] = None


class VisionRequest(BaseModel):
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    prompt: str = Field(default="Describe this image in detail.")


class VisionResponse(BaseModel):
    description: str
    model: str


class SandboxRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field(default="python")
    timeout: int = Field(default=30, ge=1, le=300)


class SandboxResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float


class ScrapeRequest(BaseModel):
    url: str = Field(..., min_length=1)
    format: str = Field(default="markdown")
    wait_for: Optional[str] = None


class ScrapeResponse(BaseModel):
    url: str
    title: str
    content: str
    links: list[str]


class UsageRecord(BaseModel):
    api_key: str
    endpoint: str
    tokens_used: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
