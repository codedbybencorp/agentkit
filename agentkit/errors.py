"""Structured error responses."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class AgentKitError(Exception):
    def __init__(self, code: str, message: str, retry_after: int = 0, suggestion: str = ""):
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.suggestion = suggestion


class RateLimitedError(AgentKitError):
    def __init__(self, retry_after: int):
        super().__init__(
            "RATE_LIMITED",
            f"Too many requests. Retry after {retry_after}s.",
            retry_after,
            "Slow down your request rate or upgrade your plan.",
        )


class TimeoutError(AgentKitError):
    def __init__(self):
        super().__init__(
            "TIMEOUT",
            "Request timed out.",
            5,
            "Try again with a shorter query or increase timeout.",
        )


class InvalidQueryError(AgentKitError):
    def __init__(self, detail: str = ""):
        super().__init__(
            "INVALID_QUERY",
            f"Invalid query. {detail}".strip(),
            0,
            "Check your request format and try again.",
        )


class UpstreamError(AgentKitError):
    def __init__(self, detail: str = ""):
        super().__init__(
            "UPSTREAM_ERROR",
            f"External service failed. {detail}".strip(),
            10,
            "Wait a moment and retry.",
        )


def to_response(exc: AgentKitError) -> JSONResponse:
    body = {
        "error": exc.message,
        "error_code": exc.code,
        "retry_after": exc.retry_after,
        "suggestion": exc.suggestion,
    }
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(status_code=429 if exc.code == "RATE_LIMITED" else 500, content=body, headers=headers)
