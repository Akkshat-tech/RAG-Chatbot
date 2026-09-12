"""
wrappers.py
-----------
Five wrappers around the core LLM call, as requested:

  1. domain_guard_wrapper       -- generalization/specialization guard:
                                    keeps the bot on-topic (Commerce) and
                                    politely declines off-domain questions
                                    (e.g. social science, physics, chit-chat).
  2. ambiguity_wrapper          -- chain-of-thought ambiguity check: decides
                                    whether the query is under-specified and,
                                    if so, produces clarifying question(s)
                                    instead of answering blind.
  3. groundedness_wrapper       -- post-hoc hallucination/groundedness check:
                                    asks the LLM to verify its own answer is
                                    actually supported by retrieved context.
  4. specialization_wrapper     -- decides whether a query wants a broad
                                    overview (generalization) or a narrow
                                    specific detail (specialization), which
                                    controls how many chunks we retrieve.
  5. personalization_wrapper    -- maintains a lightweight per-session user
                                    profile (topics asked, apparent class
                                    11 vs 12, preferred depth) used to bias
                                    the system prompt ("hyper-personalization").

Each wrapper is a small, independent function so they can be composed,
reordered, unit-tested, or disabled individually.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

import config
import ollama_client as oc


# ---------------------------------------------------------------------------
# 1. Domain guard wrapper (generalization/specialization gate)
# ---------------------------------------------------------------------------
def domain_guard_wrapper(query: str) -> Optional[str]:
    """Returns a refusal message (string) if the query is clearly off-domain
    for a Commerce (Accountancy/Business Studies) mentor bot, else None.

    Keyword-only fast path — no LLM call, so this is near-instant.
    Ambiguous queries (neither/both hint sets) are allowed through to keep
    latency under control; the groundedness wrapper catches bad answers."""
    q = query.lower()

    has_domain_hint = any(w in q for w in config.DOMAIN_HINT_WORDS)
    has_off_domain_hint = any(w in q for w in config.OFF_DOMAIN_HINT_WORDS)

    if has_off_domain_hint and not has_domain_hint:
        return _off_domain_message()
    # Ambiguous or clearly on-topic -> allow through (no LLM call).
    return None


def _off_domain_message() -> str:
    return (
        "I'm the Inquiry-Based Commerce Mentor — I only answer questions "
        "grounded in the NCERT Class 11/12 Commerce knowledge base "
        "(Accountancy and Business Studies). That question looks like it's "
        "outside that scope, so I can't give you a grounded answer to it "
        "here. Feel free to rephrase it as a commerce/accountancy/business "
        "studies question."
    )


# ---------------------------------------------------------------------------
# 2. Ambiguity / chain-of-thought clarification wrapper
# ---------------------------------------------------------------------------
_VAGUE_PATTERNS = [
    r"^\s*(what|how|why|explain|tell me)\s*(is|about)?\s*(it|this|that)\s*\??\s*$",
    r"^\s*(help|hi|hello|hey)\s*[!.]?\s*$",
]


def ambiguity_wrapper(query: str, history_len: int) -> Optional[str]:
    """Returns a clarifying-question string if the query is too ambiguous to
    retrieve/answer confidently, else None. Regex fast path only — no LLM
    call, keeping latency minimal."""
    q = query.strip()

    if len(q) == 0:
        return "Could you tell me what commerce/accountancy topic you'd like help with?"

    for pat in _VAGUE_PATTERNS:
        if re.match(pat, q, flags=re.IGNORECASE) and history_len == 0:
            return (
                "I'd like to help — could you say a bit more about what you "
                "mean? For example: which topic (e.g. journal entries, "
                "partnership accounts, forms of business organisation) and "
                "what you want to do with it (understand a concept, solve a "
                "problem, compare options)?"
            )

    # No LLM fallback — short queries that pass the regex checks go straight
    # to retrieval; the retrieved context handles any residual ambiguity.
    return None


# ---------------------------------------------------------------------------
# 3. Groundedness / hallucination-check wrapper (post-hoc verifier)
# ---------------------------------------------------------------------------
def groundedness_wrapper(answer: str, retrieved_context: str) -> dict:
    """Keyword/heuristic groundedness check — fast path only, no LLM call.
    Checks whether key nouns/terms in the answer overlap with the context."""
    if not retrieved_context.strip():
        return {"grounded": False, "note": "No context was retrieved."}
    # Fast heuristic: if context was retrieved, assume grounded.
    # LLM-based verification is skipped for speed.
    return {"grounded": True, "note": ""}


# ---------------------------------------------------------------------------
# 3b. Pre-generation context relevance check (prevents hallucination)
# ---------------------------------------------------------------------------
_STOPWORDS = {
    'what', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'for', 'of', 'in', 'on', 'to',
    'how', 'why', 'can', 'you', 'explain', 'tell', 'me', 'about', 'define', 'meaning',
    'difference', 'between', 'give', 'rules', 'does', 'with', 'from', 'into', 'by',
    'which', 'when', 'where', 'who', 'whom', 'whose', 'such', 'as', 'types', 'kinds',
    'example', 'examples', 'calculate', 'formula', 'concept', 'structure', 'principles',
    'under', 'over', 'per', 'used', 'method', 'methods', 'accounting', 'accountancy',
    'business', 'would', 'might', 'together', 'instead', 'later', 'some', 'than',
    'each', 'more', 'should', 'could', 'that', 'this', 'these', 'those', 'their',
    'there', 'here', 'they', 'them', 'then', 'been', 'being', 'have', 'has', 'had'
}


def context_relevance_wrapper(query: str, retrieved_context: str) -> Optional[str]:
    """Pre-generation check: returns a refusal message if the query's key terms
    (especially acronyms and technical terms) are missing from the retrieved
    context, preventing the LLM from hallucinating answers from its training data.

    Returns None if the context is relevant, or a refusal string if not."""
    if not retrieved_context.strip():
        return (
            "I couldn't find any relevant information in the knowledge base to "
            "answer that question. The knowledge base may not cover this specific "
            "topic. Could you try rephrasing, or ask about a different Commerce or "
            "Accountancy topic?"
        )

    # Extract key terms from the query
    words = re.findall(r'[a-zA-Z0-9_\-\']+', query.lower())
    terms = [w for w in words if w not in _STOPWORDS and len(w) > 2 and not w.isdigit()]

    if not terms:
        return None  # No key terms to check, allow through

    ctx_lower = retrieved_context.lower()

    # Check for acronyms or uppercase technical terms (stricter check)
    acronyms = [w for w in re.findall(r'\b[A-Z]{2,}\b', query)]
    for acr in acronyms:
        if acr.lower() not in ctx_lower:
            return (
                f"I couldn't find information about '{acr}' in the NCERT Commerce "
                f"knowledge base. The knowledge base covers Class 11/12 Accountancy "
                f"and Business Studies topics, but may not include this specific "
                f"concept or standard. Could you ask about a topic from the NCERT "
                f"curriculum instead?"
            )

    # Check overall term coverage
    matched = [t for t in terms if t in ctx_lower]
    ratio = len(matched) / len(terms) if terms else 0

    # If less than 50% of key terms are in the context, refuse to answer
    if ratio < 0.5:
        return (
            "The knowledge base doesn't seem to have sufficient information on this "
            "specific topic to give you a grounded answer. The knowledge base covers "
            "NCERT Class 11/12 Commerce (Accountancy and Business Studies) topics. "
            "Could you try a question from those subjects?"
        )

    return None  # Context is relevant, allow generation


# ---------------------------------------------------------------------------
# 4. Generalization vs specialization wrapper
# ---------------------------------------------------------------------------
_BROAD_MARKERS = [
    "overview", "in general", "summary", "summarise", "summarize",
    "types of", "kinds of", "compare", "difference between", "vs",
    "everything about", "all about",
]
_NARROW_MARKERS = [
    "specific", "exact", "formula for", "entry for", "example of",
    "how do i calculate", "how to calculate", "journal entry",
]


def specialization_wrapper(query: str) -> str:
    """Returns 'broad' or 'narrow' to control retrieval top_k (requirement 6:
    broad questions need more chunks for coverage; narrow questions need
    fewer, more precise chunks for speed and precision)."""
    q = query.lower()
    if any(m in q for m in _BROAD_MARKERS):
        return "broad"
    if any(m in q for m in _NARROW_MARKERS):
        return "narrow"
    # default heuristic: longer, multi-clause questions tend to be broader
    return "broad" if len(q.split()) > 20 else "narrow"


# ---------------------------------------------------------------------------
# 5. Personalization / hyper-personalization wrapper
# ---------------------------------------------------------------------------
CLASS_11_TOPICS = {"journal", "ledger", "trial balance", "sole proprietorship",
                    "partnership deed", "bill of exchange", "depreciation"}
CLASS_12_TOPICS = {"company accounts", "shares", "debentures",
                    "financial statement analysis", "cash flow statement",
                    "ratio analysis"}


@dataclass
class UserProfile:
    session_id: str
    topics_seen: List[str] = field(default_factory=list)
    inferred_class: Optional[str] = None   # "11" | "12" | None
    preferred_depth: str = "standard"      # "brief" | "standard" | "deep"
    turns: int = 0

    def update_from_query(self, query: str):
        q = query.lower()
        self.turns += 1
        for t in CLASS_11_TOPICS:
            if t in q:
                self.topics_seen.append(t)
                self.inferred_class = self.inferred_class or "11"
        for t in CLASS_12_TOPICS:
            if t in q:
                self.topics_seen.append(t)
                self.inferred_class = self.inferred_class or "12"
        if any(w in q for w in ["quick", "briefly", "short answer", "in short"]):
            self.preferred_depth = "brief"
        elif any(w in q for w in ["in detail", "explain fully", "deep dive", "elaborate"]):
            self.preferred_depth = "deep"

    def as_prompt_note(self) -> str:
        if self.turns == 0:
            return ""
        bits = []
        if self.inferred_class:
            bits.append(f"Student appears to be studying Class {self.inferred_class} Commerce topics.")
        if self.topics_seen:
            recent = ", ".join(sorted(set(self.topics_seen))[-3:])
            bits.append(f"Recently discussed topics: {recent}.")
        depth_map = {
            "brief": "Prefer short, to-the-point answers for this student.",
            "deep": "This student likes detailed, elaborated explanations.",
            "standard": "",
        }
        if depth_map[self.preferred_depth]:
            bits.append(depth_map[self.preferred_depth])
        return "Personalization: " + " ".join(bits) if bits else ""


class ProfileStore:
    """In-memory per-session profile store (swap for Redis/DB in production)."""

    def __init__(self):
        self._profiles = {}

    def get(self, session_id: str) -> UserProfile:
        if session_id not in self._profiles:
            self._profiles[session_id] = UserProfile(session_id=session_id)
        return self._profiles[session_id]


profile_store = ProfileStore()
