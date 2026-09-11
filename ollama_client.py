"""
ollama_client.py
----------------
Thin wrapper around the local Ollama HTTP API, with an LRU cache on
embeddings (requirement 6: fast, accurate retrieval -- repeated / similar
queries should not re-pay the embedding cost).
"""

import functools
import json
import requests

import config


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict, timeout: int) -> dict:
    url = f"{config.OLLAMA_HOST}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as e:
        raise OllamaError(
            f"Could not reach Ollama at {config.OLLAMA_HOST}. "
            f"Is `ollama serve` running and have you pulled "
            f"'{config.CHAT_MODEL}' and '{config.EMBED_MODEL}'? ({e})"
        ) from e
    except requests.exceptions.Timeout as e:
        raise OllamaError(f"Ollama request to {path} timed out.") from e
    except requests.exceptions.HTTPError as e:
        raise OllamaError(f"Ollama returned an error for {path}: {e}") from e


@functools.lru_cache(maxsize=config.EMBED_CACHE_SIZE)
def _embed_cached(text: str, model: str) -> tuple:
    data = _post(
        "/api/embeddings",
        {"model": model, "prompt": text},
        timeout=config.EMBED_TIMEOUT_S,
    )
    vec = data.get("embedding")
    if not vec:
        raise OllamaError(f"No embedding returned for text: {text[:60]!r}")
    return tuple(vec)  # tuple so it's hashable for lru_cache reuse elsewhere


def embed_text(text: str, model: str = None) -> list:
    """Return an embedding vector for `text`. Cached by exact text match,
    which is very effective for repeated user queries and for re-ingesting
    unchanged document chunks."""
    model = model or config.EMBED_MODEL
    return list(_embed_cached(text, model))


def embed_batch(texts: list, model: str = None) -> list:
    return [embed_text(t, model) for t in texts]


def chat(messages: list, model: str = None, temperature: float = 0.2) -> str:
    """messages: list of {"role": "system"|"user"|"assistant", "content": str}"""
    model = model or config.CHAT_MODEL
    data = _post(
        "/api/chat",
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=config.CHAT_TIMEOUT_S,
    )
    msg = data.get("message", {})
    return msg.get("content", "").strip()


def health_check() -> dict:
    """Best-effort check of whether Ollama is reachable and models exist."""
    try:
        resp = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        tags = [m["name"] for m in resp.json().get("models", [])]
        return {
            "reachable": True,
            "models_available": tags,
            "chat_model_pulled": any(config.CHAT_MODEL.split(":")[0] in t for t in tags),
            "embed_model_pulled": any(config.EMBED_MODEL.split(":")[0] in t for t in tags),
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}
