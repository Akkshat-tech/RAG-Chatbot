"""
app.py
------
FastAPI server exposing the RAG chat endpoint and serving the static
web UI (Deliverable E).

Run:
    uvicorn app:app --reload --port 8000
Then open http://localhost:8000
"""

import json
import os
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import ollama_client as oc
from rag_engine import engine

app = FastAPI(title="Inquiry-Based Commerce Mentor - RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    mode: str
    sources: list
    grounded: bool | None
    breadth: str | None
    cached: bool
    latency_ms: float


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    ollama_status = oc.health_check()
    try:
        collection = engine._ensure_collection()
        kb_chunks = collection.count()
    except Exception as e:
        kb_chunks = f"error: {e}"
    return {
        "ollama": ollama_status,
        "knowledge_base_chunks": kb_chunks,
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
    }


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    def event_generator():
        try:
            for item in engine.answer_stream(session_id, req.message):
                if item["type"] == "meta":
                    item["data"]["session_id"] = session_id
                yield json.dumps(item) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "error": str(e), "session_id": session_id}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    try:
        result = engine.answer(session_id, req.message)
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=502,
            content={
                "session_id": session_id,
                "answer": f"Backend error: {e}",
                "mode": "normal",
                "sources": [],
                "grounded": None,
                "breadth": None,
                "cached": False,
                "latency_ms": 0.0,
            },
        )
    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        mode=result["mode"],
        sources=result.get("sources", []),
        grounded=result.get("grounded"),
        breadth=result.get("breadth"),
        cached=result.get("cached", False),
        latency_ms=result.get("latency_ms", 0.0),
    )


@app.post("/reindex")
def reindex():
    """Convenience endpoint to rebuild the vector store from knowledge_base/."""
    try:
        import ingest
        stats = ingest.build_index(verbose=False)
        engine._collection = None  # force reconnect so count() is fresh
        return {"status": "ok", **stats}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
