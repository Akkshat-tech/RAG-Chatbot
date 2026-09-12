"""
Central configuration for the Inquiry-Based Commerce Mentor RAG system.
Change these values to point at your own Ollama server / models / data.
"""

import os

# ---- Ollama connection -------------------------------------------------
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CHAT_MODEL = os.environ.get(
    "CHAT_MODEL", "qwen2.5:3b")      # generation model (3b follows instructions better)
EMBED_MODEL = os.environ.get(
    "EMBED_MODEL", "nomic-embed-text")  # embedding model

# ---- Storage ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_store")
COLLECTION_NAME = "commerce_mentor_kb"

# ---- Chunking -------------------------------------------------------------
CHUNK_SIZE = 900          # characters per chunk
CHUNK_OVERLAP = 150       # characters of overlap between consecutive chunks

# ---- Retrieval ------------------------------------------------------------
TOP_K_DEFAULT = 4          # chunks retrieved for a normal (specific) query
TOP_K_BROAD = 6            # chunks retrieved for a broad/generalization query
MIN_RELEVANCE_SCORE = 0.35  # below this similarity we treat retrieval as "empty"
# (Chroma returns L2 distance by default; we convert
# to a 0-1 similarity score in rag_engine.py)

# ---- Caching / performance --------------------------------------------
EMBED_CACHE_SIZE = 512     # LRU cache size for query embeddings
QUERY_CACHE_SIZE = 128     # LRU cache size for (mode,query)->answer results
CHAT_TIMEOUT_S = 60        # timeout for chat calls
EMBED_TIMEOUT_S = 30
MAX_TOKENS = 350           # cap generation length so answers generate much faster

# ---- Domain guard --------------------------------------------------------
PROJECT_DOMAIN_DESCRIPTION = (
    "NCERT Class 11 and 12 Commerce stream subjects: Accountancy "
    "(book keeping, journal, ledger, trial balance, financial statements, "
    "partnership accounts, company accounts, depreciation, bills of exchange), "
    "Business Studies (nature of business, forms of business organisation, "
    "business services, sources of business finance, small business, "
    "internal trade, marketing, e-business, principles of management), "
    "and basic Economics/Statistics for commerce students."
)

OFF_DOMAIN_HINT_WORDS = [
    "history", "geography", "civics", "political science", "sociology",
    "physics", "chemistry", "biology", "cricket score", "movie", "song lyrics",
    "weather", "recipe", "medical advice", "diagnose", "prescription",
    "relationship advice", "programming", "code review",
]

DOMAIN_HINT_WORDS = [
    "accountancy", "accounting", "journal", "ledger", "trial balance",
    "balance sheet", "profit and loss", "depreciation", "partnership",
    "company accounts", "shares", "debentures", "bill of exchange",
    "business studies", "business organisation", "sole proprietorship",
    "partnership firm", "joint stock company", "cooperative society",
    "marketing", "e-business", "management", "finance", "entrepreneurship",
    "commerce", "trade", "gst", "tax", "bookkeeping", "capital", "revenue",
    "asset", "liability", "cash flow", "ratio analysis", "stock exchange",
]

SESSION_MAX_HISTORY_TURNS = 8   # how many past turns kept in short-term memory
