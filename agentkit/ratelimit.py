"""Simple in-memory rate limiting."""

import time
from collections import defaultdict
from typing import Dict, Tuple

# endpoint -> max requests per window
LIMITS: Dict[str, Tuple[int, int]] = {
    "/research": (60, 60),
    "/memory/write": (100, 60),
    "/memory/query": (100, 60),
    "/vision": (30, 60),
    "/sandbox": (10, 60),
    "/scrape": (60, 60),
}

_buckets: dict = defaultdict(lambda: defaultdict(list))


def check(api_key: str, endpoint: str) -> Tuple[bool, int, int]:
    """Returns (allowed, remaining, retry_after)."""
    limit, window = LIMITS.get(endpoint, (60, 60))
    now = time.time()
    bucket = _buckets[api_key][endpoint]

    # Remove old entries outside window
    bucket[:] = [t for t in bucket if now - t < window]

    if len(bucket) >= limit:
        retry_after = int(window - (now - bucket[0]))
        return False, 0, max(retry_after, 1)

    bucket.append(now)
    remaining = limit - len(bucket)
    return True, remaining, 0
