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

    Uses a cheap keyword check first (fast path); only falls back to an LLM
    judgement call for genuinely unclear cases, to keep the bot responsive."""
    q = query.lower()

    has_domain_hint = any(w in q for w in config.DOMAIN_HINT_WORDS)
    has_off_domain_hint = any(w in q for w in config.OFF_DOMAIN_HINT_WORDS)

    if has_domain_hint and not has_off_domain_hint:
        return None  # clearly on-topic, fast path, no LLM call needed
    if has_off_domain_hint and not has_domain_hint:
        return _off_domain_message()

    # Ambiguous case (neither/both hint sets matched) -> ask the LLM once.
    verdict = oc.chat(
        [
            {
                "role": "system",
                "content": (
                    "You are a strict topic classifier for a Commerce "
                    "(Accountancy/Business Studies, NCERT 11-12) tutoring "
                    "bot. Reply with exactly one word: 'ON_TOPIC' if the "
                    "user's message is about commerce/accountancy/business "
                    "studies (or is a greeting/meta question about the bot "
                    "itself), or 'OFF_TOPIC' if it is about something else "
                    "entirely (other school subjects, general chit-chat "
                    "unrelated to commerce, coding help, etc.)."
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0.0,
    )
    if "OFF_TOPIC" in verdict.upper():
        return _off_domain_message()
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
    retrieve/answer confidently, else None. Cheap regex fast path first,
    LLM-based chain-of-thought check as fallback for short/vague queries."""
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

    # Only bother with an LLM ambiguity check for short queries; long,
    # detailed queries are very unlikely to need clarification, and skipping
    # the LLM call here keeps the system fast (requirement 6).
    if len(q.split()) > 6:
        return None

    verdict = oc.chat(
        [
            {
                "role": "system",
                "content": (
                    "Think step by step about whether this short message "
                    "from a commerce student gives enough context to search "
                    "a knowledge base and answer confidently. Consider: is "
                    "the topic named? Is the specific sub-concept clear? "
                    "Then reply with exactly one line: "
                    "'CLEAR' or 'CLARIFY: <one short clarifying question>'."
                ),
            },
            {"role": "user", "content": q},
        ],
        temperature=0.0,
    )
    if verdict.upper().startswith("CLARIFY"):
        question = verdict.split(":", 1)[1].strip() if ":" in verdict else (
            "Could you clarify which specific topic you mean?"
        )
        return question
    return None


# ---------------------------------------------------------------------------
# 3. Groundedness / hallucination-check wrapper (post-hoc verifier)
# ---------------------------------------------------------------------------
def groundedness_wrapper(answer: str, retrieved_context: str) -> dict:
    """Asks the LLM to verify, independently, whether `answer` is supported
    by `retrieved_context`. Returns {"grounded": bool, "note": str}.
    If retrieved_context is empty, short-circuits to ungrounded (fast path,
    no LLM call needed)."""
    if not retrieved_context.strip():
        return {"grounded": False, "note": "No context was retrieved."}

    verdict = oc.chat(
        [
            {
                "role": "system",
                "content": (
                    "You are a strict fact-checker. Given RETRIEVED_CONTEXT "
                    "and a candidate ANSWER, decide if every factual claim "
                    "in the ANSWER is supported by the RETRIEVED_CONTEXT. "
                    "Reply with exactly one line: 'GROUNDED' or "
                    "'UNGROUNDED: <short reason>'."
                ),
            },
            {
                "role": "user",
                "content": f"RETRIEVED_CONTEXT:\n{retrieved_context}\n\nANSWER:\n{answer}",
            },
        ],
        temperature=0.0,
    )
    if verdict.upper().startswith("GROUNDED"):
        return {"grounded": True, "note": ""}
    reason = verdict.split(":", 1)[1].strip() if ":" in verdict else verdict
    return {"grounded": False, "note": reason}


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
