# AgentKit — Tools for AI Agents

> **The API platform that gives your AI agent superpowers.**

AgentKit provides research, memory, vision, sandbox, and scraping tools that any AI agent can call via a simple REST API. Think of it as "AWS for agents" — infrastructure your agent doesn't have to build.

## API Endpoints

| Endpoint | What it does | Use case |
|----------|-------------|----------|
| `POST /research` | Search web + synthesize cited answer | Your agent needs to know something |
| `POST /memory/write` | Store text in vector memory | Your agent needs to remember |
| `POST /memory/query` | Query vector memory by similarity | Your agent needs to recall |
| `POST /vision` | Describe images via LLM | Your agent sees an image |
| `POST /sandbox` | Execute code in Docker | Your agent needs to run code |
| `POST /scrape` | Extract clean text from URLs | Your agent needs to read a page |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/codedbybencorp/agentkit.git
cd agentkit

# 2. Set API keys (optional — Ollama works locally)
export OPENAI_API_KEY=sk-...
export AGENTKIT_API_KEYS=my-secret-key

# 3. Run
docker compose up -d

# 4. Test
curl -H "X-API-Key: my-secret-key" \
  -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "latest rust programming features"}'
```

## Usage from Python

```python
import httpx

API_KEY = "my-secret-key"
BASE = "http://localhost:8000"

# Research
r = httpx.post(f"{BASE}/research",
    headers={"X-API-Key": API_KEY},
    json={"query": "benefits of meditation"})
print(r.json()["answer"])

# Memory
httpx.post(f"{BASE}/memory/write",
    headers={"X-API-Key": API_KEY},
    json={"agent_id": "agent-1", "text": "User prefers concise answers."})

mem = httpx.post(f"{BASE}/memory/query",
    headers={"X-API-Key": API_KEY},
    json={"agent_id": "agent-1", "query": "user preference"})
print(mem.json()["results"])

# Sandbox
result = httpx.post(f"{BASE}/sandbox",
    headers={"X-API-Key": API_KEY},
    json={"code": "print('hello from sandbox')", "language": "python"})
print(result.json()["stdout"])
```

## Self-Hosted vs Hosted

| | Self-Hosted | Hosted (coming) |
|---|---|---|
| **Cost** | Free (your server) | $19/mo |
| **Setup** | Docker | One click |
| **Data** | Stays on your machine | Encrypted at rest |
| **Scale** | Your hardware | Auto-scaling |
| **Support** | Community | Priority |

## Architecture

```
Your Agent → HTTP + X-API-Key → AgentKit
                                      ├── /research → DuckDuckGo + LLM
                                      ├── /memory → ChromaDB (vector)
                                      ├── /vision → OpenAI/Ollama
                                      ├── /sandbox → Docker (isolated)
                                      └── /scrape → BeautifulSoup
```

## Environment Variables

| Var | Default | Description |
|-----|---------|-------------|
| `OPENAI_API_KEY` | — | For GPT-4o-mini synthesis & vision |
| `AGENTKIT_API_KEYS` | `test-key-123` | Comma-separated valid API keys |
| `AGENTKIT_DATA` | `.data` | Persistent data directory |

## Monetization Model

AgentKit is designed to be both self-hosted (free) and hosted (paid):

| Tier | Price | Limits |
|------|-------|--------|
| **Self-Hosted** | Free | Your own hardware |
| **Starter** | $19/mo | 10K requests/mo + email support |
| **Pro** | $49/mo | 100K requests/mo + priority + custom tools |
| **Enterprise** | $199/mo | Unlimited + dedicated infra + SLA |

**Why agents pay for this:**
- Building web search + memory + sandbox yourself takes weeks
- Agents need reliable infrastructure, not DIY scripts
- Per-request billing aligns with agent usage patterns
- Multi-agent memory sharing unlocks team workflows

## What's Next

- [ ] Stripe billing with usage-based pricing
- [ ] MCP (Model Context Protocol) server wrapper
- [ ] Agent dashboard (view usage, manage keys, inspect memory)
- [ ] WebSocket streaming for real-time research
- [ ] Scheduled research jobs (cron for agents)

## License

MIT
