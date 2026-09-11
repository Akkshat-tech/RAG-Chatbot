"""
rag_engine.py
-------------
Ties everything together:

    User Query -> [domain guard] -> [ambiguity check] -> mode template
        -> Retrieval (Chroma, top_k chosen by specialization wrapper)
        -> Generation (Ollama chat, using TOCD/RTAO/Ultimate/normal prompt)
        -> [groundedness check] -> Response + Sources

Also implements requirement 6 (efficiency): an in-process LRU cache on
(mode, query) -> full response, plus the embedding cache already in
ollama_client.py, so repeated/near-repeated queries are near-instant.
"""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional

import chromadb

import config
import ingest
import ollama_client as oc
import templates
import wrappers


# ---------------------------------------------------------------------------
# Small LRU cache for full query results (requirement 6: speed)
# ---------------------------------------------------------------------------
class _LRUCache(OrderedDict):
    def __init__(self, maxsize):
        super().__init__()
        self.maxsize = maxsize

    def get_or_none(self, key):
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key, value):
        self[key] = value
        self.move_to_end(key)
        if len(self) > self.maxsize:
            self.popitem(last=False)


_response_cache = _LRUCache(config.QUERY_CACHE_SIZE)


@dataclass
class SessionState:
    session_id: str
    mode: str = templates.MODE_NORMAL
    history: List[dict] = field(default_factory=list)   # [{"role","content"}]
    awaiting_clarification: bool = False

    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        max_msgs = config.SESSION_MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history[:] = self.history[-max_msgs:]


class SessionStore:
    def __init__(self):
        self._sessions = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]


sessions = SessionStore()


class RagEngine:
    def __init__(self):
        self._client = None
        self._collection = None

    # -- lazy vector-store connection so the server can boot even before
    #    ingest.py has been run once -----------------------------------
    def _ensure_collection(self):
        if self._collection is None:
            self._client, self._collection = ingest.get_chroma_collection()
        return self._collection

    def retrieve(self, query: str, top_k: int):
        collection = self._ensure_collection()
        count = collection.count()
        if count == 0:
            return [], []
        query_emb = oc.embed_text(query)
        result = collection.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        docs = result["documents"][0] if result["documents"] else []
        metas = result["metadatas"][0] if result["metadatas"] else []
        dists = result["distances"][0] if result["distances"] else []

        # Chroma with cosine space returns distance = 1 - cosine_similarity.
        # Convert to similarity and drop chunks below the relevance floor,
        # so "irrelevant" retrieval is treated the same as "no retrieval".
        kept_docs, kept_metas = [], []
        for doc, meta, dist in zip(docs, metas, dists):
            similarity = 1 - dist
            if similarity >= config.MIN_RELEVANCE_SCORE:
                kept_docs.append(doc)
                kept_metas.append(meta)
        return kept_docs, kept_metas

    def answer(self, session_id: str, user_text: str) -> dict:
        t0 = time.time()
        state = sessions.get(session_id)

        # --- 0. mode switching -------------------------------------------
        requested_mode = templates.parse_mode_switch(user_text)
        if requested_mode == "__help__":
            return self._wrap_meta(templates.HELP_TEXT, state, t0)
        if requested_mode is not None:
            state.mode = requested_mode
            user_text = templates.strip_mode_keyword(user_text)
            if not user_text:
                return self._wrap_meta(
                    f"Switched to **{state.mode.upper()}** mode. "
                    f"Ask your commerce question now.", state, t0,
                )

        query = user_text.strip()
        if not query:
            return self._wrap_meta("Please type a question.", state, t0)

        # --- 1. domain guard wrapper ---------------------------------------
        refusal = wrappers.domain_guard_wrapper(query)
        if refusal:
            state.add_turn("user", query)
            state.add_turn("assistant", refusal)
            return self._wrap_meta(refusal, state, t0, wrapper_trace=["domain_guard:blocked"])

        # --- 2. ambiguity / chain-of-thought wrapper -----------------------
        clarifying_q = wrappers.ambiguity_wrapper(query, history_len=len(state.history))
        if clarifying_q:
            state.add_turn("user", query)
            state.add_turn("assistant", clarifying_q)
            state.awaiting_clarification = True
            return self._wrap_meta(
                clarifying_q, state, t0, wrapper_trace=["ambiguity:clarify_requested"]
            )
        state.awaiting_clarification = False

        # --- 3. cache check --------------------------------------------------
        cache_key = (state.mode, query.lower())
        cached = _response_cache.get_or_none(cache_key)
        if cached:
            state.add_turn("user", query)
            state.add_turn("assistant", cached["answer"])
            cached = dict(cached)
            cached["cached"] = True
            cached["latency_ms"] = round((time.time() - t0) * 1000, 1)
            return cached

        # --- 4. specialization wrapper -> retrieval --------------------------
        breadth = wrappers.specialization_wrapper(query)
        top_k = config.TOP_K_BROAD if breadth == "broad" else config.TOP_K_DEFAULT
        docs, metas = self.retrieve(query, top_k)
        retrieved_context = "\n\n".join(
            f"[{m['source']} #{m['chunk_index']}] {d}" for d, m in zip(docs, metas)
        )
        sources = ", ".join(sorted({m["source"] for m in metas})) or "none"

        # --- 5. personalization wrapper --------------------------------------
        profile = wrappers.profile_store.get(session_id)
        profile.update_from_query(query)
        profile_note = profile.as_prompt_note()

        # --- 6. build system prompt from active mode template ---------------
        sys_ctx = templates.SystemPromptContext(
            domain_description=config.PROJECT_DOMAIN_DESCRIPTION,
            retrieved_context=retrieved_context or "(no relevant context retrieved)",
            sources=sources,
            user_profile_note=profile_note,
        )
        system_prompt = templates.build_system_prompt(state.mode, sys_ctx)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(state.history[-config.SESSION_MAX_HISTORY_TURNS * 2:])
        messages.append({"role": "user", "content": query})

        # --- 7. generation -----------------------------------------------------
        answer_text = oc.chat(messages)

        # --- 8. groundedness / hallucination wrapper --------------------------
        ground = wrappers.groundedness_wrapper(answer_text, retrieved_context)
        if not ground["grounded"]:
            answer_text += (
                "\n\n*(Note: this answer may not be fully grounded in the "
                f"knowledge base{': ' + ground['note'] if ground['note'] else ''}. "
                "Treat it with caution and check the sources above.)*"
            )

        state.add_turn("user", query)
        state.add_turn("assistant", answer_text)

        result = {
            "answer": answer_text,
            "mode": state.mode,
            "sources": sorted({m["source"] for m in metas}),
            "retrieved_chunks": [
                {"source": m["source"], "chunk_index": m["chunk_index"], "text": d}
                for d, m in zip(docs, metas)
            ],
            "grounded": ground["grounded"],
            "breadth": breadth,
            "cached": False,
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }
        _response_cache.put(cache_key, result)
        return result

    @staticmethod
    def _wrap_meta(text: str, state: SessionState, t0: float, wrapper_trace=None) -> dict:
        return {
            "answer": text,
            "mode": state.mode,
            "sources": [],
            "retrieved_chunks": [],
            "grounded": None,
            "breadth": None,
            "cached": False,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "wrapper_trace": wrapper_trace or [],
        }


engine = RagEngine()
