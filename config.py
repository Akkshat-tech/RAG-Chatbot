# config.py
# Edit these two model names to match whatever `ollama list` shows on YOUR machine.

OLLAMA_HOST = "http://localhost:11434"

CHAT_MODEL = "llama3.1:8b"            # any chat/instruct model you have pulled, e.g. "llama3.1", "mistral", "gemma2"
EMBED_MODEL = "nomic-embed-text"   # an embedding model, e.g. "nomic-embed-text", "mxbai-embed-large"

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 120   # character overlap between consecutive chunks
TOP_K = 4             # how many chunks to retrieve per query

DATA_DIR = "data"
STORE_PATH = "store/vector_store.json"
