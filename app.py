"""
app.py
<<<<<<< HEAD
------
FastAPI server exposing the RAG chat endpoint and serving the static
web UI (Deliverable E).

Run:
    uvicorn app:app --reload --port 8000
Then open http://localhost:8000
"""

import os
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    result = engine.answer(session_id, req.message)
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
    import ingest
    stats = ingest.build_index(verbose=False)
    engine._collection = None  # force reconnect so count() is fresh
    return {"status": "ok", **stats}
=======
Flask backend + simple web UI for the "Inquiry-Based Commerce Mentor" RAG tool.

Run:
    python app.py
Then open http://localhost:5000 in your browser.
"""
from flask import Flask, request, jsonify, render_template
import rag_engine

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    mode = data.get("mode", "tocd")  # "tocd" or "rtao"

    if not query:
        return jsonify({"error": "Empty query"}), 400

    try:
        result = rag_engine.answer_query(query, mode=mode)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
>>>>>>> 941d463eb875b5dce394c8551cf9d5b131bb3ab9
