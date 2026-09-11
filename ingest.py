"""
ingest.py
---------
Document Processing Pipeline (Deliverable B):

    Documents (knowledge_base/*.txt)
        -> Cleaning (whitespace/encoding normalisation)
        -> Chunking (fixed-size, overlapping, sentence-aware)
        -> Embedding (Ollama nomic-embed-text)
        -> Vector Store (ChromaDB, persisted on disk)

Run directly to (re)build the vector store:
    python ingest.py
"""

import glob
import os
import re
import sys

import chromadb

import config
import ollama_client as oc


def clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list:
    """Sentence-aware sliding-window chunking: we try to break on sentence
    boundaries near the target chunk_size so chunks stay semantically
    coherent, then apply a character overlap between consecutive chunks so
    context isn't lost at chunk edges."""
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= chunk_size:
            current = f"{current} {sent}".strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk, carrying the overlap tail of the previous one
            tail = current[-overlap:] if overlap and current else ""
            current = f"{tail} {sent}".strip()
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def load_documents(kb_dir: str = None) -> list:
    kb_dir = kb_dir or config.KNOWLEDGE_BASE_DIR
    docs = []
    for path in sorted(glob.glob(os.path.join(kb_dir, "*.txt"))):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        docs.append({"source": os.path.basename(path), "text": clean_text(raw)})
    return docs


def get_chroma_collection():
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return client, collection


def build_index(kb_dir: str = None, verbose: bool = True) -> dict:
    docs = load_documents(kb_dir)
    if not docs:
        raise RuntimeError(
            f"No .txt documents found in {kb_dir or config.KNOWLEDGE_BASE_DIR}. "
            "Add your curated knowledge base files there first."
        )

    client, collection = get_chroma_collection()
    # Wipe and rebuild for a clean, reproducible index each run.
    existing_ids = collection.get()["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)

    ids, texts, metadatas = [], [], []
    for doc in docs:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            ids.append(f"{doc['source']}::{i}")
            texts.append(chunk)
            metadatas.append({"source": doc["source"], "chunk_index": i})
        if verbose:
            print(f"  {doc['source']}: {len(chunks)} chunks")

    if verbose:
        print(f"Embedding {len(texts)} chunks with '{config.EMBED_MODEL}' ...")
    embeddings = oc.embed_batch(texts)

    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    if verbose:
        print(f"Indexed {len(texts)} chunks from {len(docs)} documents into "
              f"Chroma collection '{config.COLLECTION_NAME}' at {config.CHROMA_DIR}")
    return {"documents": len(docs), "chunks": len(texts)}


if __name__ == "__main__":
    try:
        stats = build_index()
        print("Done:", stats)
    except Exception as e:
        print(f"Ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
