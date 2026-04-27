"""Web research engine with DuckDuckGo + LLM synthesis."""

import asyncio
import json
import os
import re
import textwrap
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class Source:
    url: str
    title: str
    snippet: str
    text: str = ""
    domain: str = ""

    def __post_init__(self):
        self.domain = urlparse(self.url).netloc.replace("www.", "")


async def search_duckduckgo(query: str, limit: int = 8) -> list[Source]:
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as http:
        r = await http.post(url, data={"q": query, "kl": "us-en"}, headers=headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

    results = []
    for res in soup.select(".result"):
        a = res.select_one(".result__a")
        snippet_el = res.select_one(".result__snippet")
        if not a:
            continue
        href = a.get("href", "")
        if href.startswith("/"):
            continue
        title = a.get_text(strip=True)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        results.append(Source(url=href, title=title, snippet=snippet))
        if len(results) >= limit:
            break
    return results


async def extract_text(source: Source) -> Source:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as http:
            r = await http.get(source.url, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            main = soup.find("article") or soup.find("main") or soup.find("body")
            text = main.get_text(separator="\n", strip=True) if main else ""
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" +", " ", text)
            source.text = text[:4000]
    except Exception:
        source.text = source.snippet
    return source


async def synthesize(query: str, sources: list[Source], system_prompt: str | None = None) -> str:
    import time
    t0 = time.time()

    context_parts = []
    for i, s in enumerate(sources[:4], 1):
        context_parts.append(f"[Source {i}] {s.title}\n{s.text[:3000]}")
    context = "\n\n---\n\n".join(context_parts)

    system = system_prompt or textwrap.dedent("""\
        You are a research assistant. Read the sources and write a concise,
        fact-checked answer. Cite sources with [1], [2], etc. Be factual.
    """)
    user = f"Question: {query}\n\nSources:\n{context}"

    # Try Ollama first, then OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return resp.choices[0].message.content or ""
    else:
        # Ollama fallback
        async with httpx.AsyncClient(timeout=60) as http:
            r = await http.post("http://localhost:11434/api/generate", json={
                "model": "gemma-4-e4b",
                "prompt": f"{system}\n\n{user}",
                "stream": False,
                "options": {"temperature": 0.3, "num_ctx": 8192},
            })
            return r.json().get("response", "")
