"""
ingest.py
Document Processing Pipeline:
    Documents (PDF/TXT in data/) -> Cleaning -> Chunking -> Embedding (Ollama) -> Vector Store (JSON)

Run this whenever you add/change files in data/:
    python ingest.py
"""
import os
import re
import json
import requests
from pathlib import Path
from pypdf import PdfReader

import config


def load_documents(data_dir: str):
    """Read every .pdf and .txt file in data_dir. Returns list of (source_name, page_or_none, raw_text)."""
    docs = []
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(
            f"'{data_dir}' folder not found. Create it and put your NCERT Commerce "
            f"PDFs/notes inside before running ingest.py"
        )

    files = list(data_path.glob("*.pdf")) + list(data_path.glob("*.txt"))
    if not files:
        raise ValueError(f"No .pdf or .txt files found in '{data_dir}'. Add your knowledge base files first.")

    for f in files:
        if f.suffix.lower() == ".pdf":
            reader = PdfReader(str(f))
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    docs.append((f.name, page_num, text))
        elif f.suffix.lower() == ".txt":
            text = f.read_text(encoding="utf-8", errors="ignore")
            docs.append((f.name, None, text))

    print(f"Loaded {len(files)} file(s), {len(docs)} page/section unit(s).")
    return docs


def clean_text(text: str) -> str:
    """Basic cleaning: collapse whitespace, drop empty lines, strip page-number-only lines."""
    text = text.replace("\x00", " ")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not re.fullmatch(r"\d{1,4}", ln)]  # drop bare page numbers
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, chunk_size: int, overlap: int):
    """Simple sliding-window chunker over cleaned text."""
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # try not to cut mid-word
        if end < n:
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed(text: str):
    """Call Ollama's embeddings endpoint for a single piece of text."""
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/embeddings",
        json={"model": config.EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def build_store():
    docs = load_documents(config.DATA_DIR)

    records = []
    for source_name, page, raw_text in docs:
        cleaned = clean_text(raw_text)
        if not cleaned:
            continue
        for chunk in chunk_text(cleaned, config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            records.append({
                "source": source_name,
                "page": page,
                "text": chunk,
            })

    print(f"Created {len(records)} chunk(s). Embedding with model '{config.EMBED_MODEL}' ...")

    for i, rec in enumerate(records, start=1):
        rec["embedding"] = embed(rec["text"])
        if i % 10 == 0 or i == len(records):
            print(f"  embedded {i}/{len(records)}")

    os.makedirs(os.path.dirname(config.STORE_PATH), exist_ok=True)
    with open(config.STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f)

    print(f"Saved vector store -> {config.STORE_PATH}")


if __name__ == "__main__":
    build_store()
