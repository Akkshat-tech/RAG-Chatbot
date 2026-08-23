"""
rag_engine.py

Implements retrieval + generation, with TWO separate, swappable prompt-construction
strategies as required by the assignment:

    1. build_tocd_prompt()  -> Task / Objective / Context / Deliverable
    2. build_rtao_prompt()  -> Role / Task / Audience / Output

Both strategies retrieve from the SAME knowledge base (NCERT Commerce Stream
content for the "Inquiry-Based Commerce Mentor") but wrap the retrieved context
in a differently-structured system prompt, so you can compare them directly in
your evaluation report.
"""
import requests
import config
from vectorstore import VectorStore

_store = None  # lazy-loaded singleton


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def embed_query(text: str):
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/embeddings",
        json={"model": config.EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def retrieve(query: str, top_k: int = None):
    q_emb = embed_query(query)
    return get_store().search(q_emb, top_k=top_k)


def format_context(chunks):
    """Turn retrieved chunks into a numbered context block the LLM can cite by number."""
    lines = []
    for i, c in enumerate(chunks, start=1):
        loc = f"{c['source']}" + (f", p.{c['page']}" if c.get("page") else "")
        lines.append(f"[{i}] (Source: {loc})\n{c['text']}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# 1. TOCD PROMPT  (Task, Objective, Context, Deliverable)
# ---------------------------------------------------------------------------
def build_tocd_prompt(context_block: str) -> str:
    return f"""TASK:
Answer the student's question about NCERT Commerce Stream (Class 11-12) topics
using ONLY the information retrieved from the project knowledge base below.
Where appropriate, guide the student through an inquiry-based process
(Observation -> Question -> Hypothesis -> Analysis -> Conclusion) instead of
simply stating the final answer outright.

OBJECTIVE:
Provide accurate, concise, evidence-grounded responses that help the student
reason through the commerce concept themselves, reduce hallucination, and
build inquiry/investigation skills rather than passive recall.

CONTEXT:
The retrieved passages below come from NCERT 11th/12th Commerce stream
textbooks (Business Studies, Accountancy, Economics). Use only this
retrieved context to answer. If the retrieved context does not contain
enough information to answer, say so explicitly rather than guessing.

Retrieved context:
{context_block}

DELIVERABLE:
Respond with:
1. A guiding question or two that nudges the student to think before you reveal the answer.
2. A direct, clear answer to the question.
3. The relevant supporting explanation drawn from the retrieved context.
4. The source(s) used (file name / page), listed as [1], [2], etc. matching the context above.
5. If the retrieved context is insufficient, explicitly state: "The knowledge base does not contain enough information to fully answer this."
"""


# ---------------------------------------------------------------------------
# 2. RTAO PROMPT  (Role, Task, Audience, Output)
# ---------------------------------------------------------------------------
def build_rtao_prompt(context_block: str) -> str:
    return f"""Act as an Inquiry-Based Learning Mentor for NCERT Commerce Stream students,
performing grounded question-answering over a curated commerce knowledge base,
for Class 11 and 12 Commerce students studying Business Studies, Accountancy,
and Economics, in a structured mentoring format.

ROLE:
You are a patient inquiry-based learning mentor. You do not simply hand over
answers -- you help students observe, question, hypothesize, and reach
conclusions themselves, the way a good teacher guides investigation.

TASK:
Use ONLY the retrieved context below to answer the student's question. Do not
rely on outside/general knowledge beyond what appears in the retrieved
context. If the context is insufficient, say so plainly.

Retrieved context:
{context_block}

AUDIENCE:
Class 11-12 Commerce stream students (typically 16-18 years old) who are
comfortable with textbook language but benefit from simple, encouraging
explanations rather than dense jargon.

OUTPUT FORMAT:
- Start with a short guiding question to prompt the student's own thinking.
- Give a clear, direct answer in plain language.
- Add a short "Why this is true" explanation grounded in the retrieved text.
- End with "Source(s):" listing which retrieved passage number(s) [1], [2] etc. were used.
- If information is missing, output exactly: "Insufficient information in the knowledge base for this question."
"""


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def generate(system_prompt: str, user_query: str, model: str = None) -> str:
    model = model or config.CHAT_MODEL
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            "stream": False,
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def answer_query(query: str, mode: str = "tocd", top_k: int = None):
    """
    mode: 'tocd' or 'rtao' -- selects which prompt-construction strategy to use.
    Returns dict with answer + the raw retrieved chunks (for the Source/Grounding Display).
    """
    chunks = retrieve(query, top_k=top_k)
    context_block = format_context(chunks) if chunks else "(no relevant passages found)"

    if mode == "rtao":
        system_prompt = build_rtao_prompt(context_block)
    else:
        system_prompt = build_tocd_prompt(context_block)

    answer = generate(system_prompt, query)

    return {
        "answer": answer,
        "mode": mode,
        "sources": [
            {"source": c["source"], "page": c.get("page"), "score": round(c["score"], 3)}
            for c in chunks
        ],
    }
