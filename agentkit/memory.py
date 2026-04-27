"""Vector memory for agents using ChromaDB."""

import os
import uuid
from datetime import datetime

import chromadb
from chromadb.config import Settings

DATA_DIR = os.environ.get("AGENTKIT_DATA", ".data")

def _client():
    return chromadb.PersistentClient(
        path=os.path.join(DATA_DIR, "chroma"),
        settings=Settings(anonymized_telemetry=False),
    )


def _collection(agent_id: str, namespace: str):
    client = _client()
    name = f"{agent_id}_{namespace}"
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def write(agent_id: str, namespace: str, text: str, metadata: dict | None = None):
    coll = _collection(agent_id, namespace)
    doc_id = str(uuid.uuid4())
    meta = metadata or {}
    meta["created_at"] = datetime.utcnow().isoformat()
    coll.add(documents=[text], metadatas=[meta], ids=[doc_id])
    return doc_id


def query(agent_id: str, namespace: str, query_text: str, top_k: int = 5):
    coll = _collection(agent_id, namespace)
    results = coll.query(query_texts=[query_text], n_results=top_k)
    out = []
    for i in range(len(results["documents"][0])):
        out.append({
            "text": results["documents"][0][i],
            "distance": results["distances"][0][i] if results["distances"] else 0,
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
        })
    return out


def delete_collection(agent_id: str, namespace: str):
    client = _client()
    name = f"{agent_id}_{namespace}"
    try:
        client.delete_collection(name=name)
    except Exception:
        pass
