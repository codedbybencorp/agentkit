"""Vision / image analysis via LLM."""

import base64
import os

import httpx


async def describe(image_base64: str | None, image_url: str | None, prompt: str) -> str:
    """Describe an image using the configured LLM."""
    if image_url:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(image_url)
            image_base64 = base64.b64encode(r.content).decode()

    if not image_base64:
        return "No image provided."

    # OpenAI vision
    if os.environ.get("OPENAI_API_KEY"):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ],
            }],
            max_tokens=1000,
        )
        return resp.choices[0].message.content or ""

    # Ollama vision (if model supports it)
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            r = await http.post("http://localhost:11434/api/generate", json={
                "model": "gemma-4-e4b",
                "prompt": f"{prompt}\n\n[Image data: base64,{image_base64[:200]}...]",
                "stream": False,
            })
            return r.json().get("response", "")
    except Exception:
        return "Vision not available. Set OPENAI_API_KEY or use an Ollama vision model."
