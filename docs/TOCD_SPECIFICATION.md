# TOCD Specification — Inquiry-Based Commerce Mentor

## 1. Task

Build a RAG-based tutor that lets NCERT Class 11/12 Commerce students ask
questions about Accountancy (book keeping, financial statements, partnership
and company accounts) and Business Studies (forms of organisation, business
services, marketing, management principles) and receive answers grounded in
a curated, project-specific knowledge base — not the LLM's general knowledge.

- **Users:** Class 11–12 commerce students (and, secondarily, whoever is
  reviewing this project — teachers/evaluators).
- **Problem solved:** Generic LLMs answer confidently even when they don't
  actually know the specific NCERT-style definitions/treatment a student
  needs, and can't show what they based an answer on. This tool restricts
  answers to a specific curated knowledge base and shows its sources.
- **Tasks the user can perform:** ask direct definition questions, ask
  comparison/multi-step questions, ask for the reasoning behind a concept
  (via the inquiry-cycle-guided TOCD mode), and switch how the answer is
  structured (TOCD / RTAO / Ultimate template modes).
- **Information retrieved:** short passages ("chunks") from the curated
  Accountancy/Business Studies notes, each tagged with its source file.
- **When information can't be found:** the system explicitly says the
  knowledge base does not contain enough information, rather than guessing
  (see `templates.py` deliverable format, and the groundedness wrapper).

## 2. Objective

Enable students to obtain reliable, syllabus-scoped answers to commerce
questions by retrieving from the project's curated knowledge base and
generating concise, evidence-grounded responses — reducing hallucination
compared to asking a bare LLM, and improving relevance by keeping the tool
scoped to one domain (with an explicit domain guard) instead of behaving
like a generic chatbot.

## 3. Context

**Knowledge sources:** project-generated, original explanatory notes
(written for this project, in the style of NCERT Commerce topics — not
verbatim textbook text) covering Accountancy fundamentals, financial
statements, partnership accounts, company accounts, business studies
fundamentals, and marketing/management. Stored as plain-text files under
`knowledge_base/`.

**What's included:** core definitions, concepts, and relationships taught in
the syllabus (e.g. what a trial balance is, how the 4 Ps work, forms of
business organisation). **What's excluded:** numeric worked examples/sums,
exact legal statute text, current tax rates (these change over time and
would go stale), and anything outside the Commerce stream. **Organisation:**
one `.txt` file per topic area, each with several self-contained paragraphs.
**Preparation for retrieval:** files are cleaned (whitespace/newline
normalisation), then chunked (see below).

**Retrieval strategy:**
- **Chunking:** sentence-aware sliding window, target ~900 characters per
  chunk with ~150 characters of overlap, so related sentences stay together
  and context isn't lost at a chunk boundary (`ingest.py::chunk_text`).
- **Embeddings:** Ollama's `nomic-embed-text` model, one vector per chunk,
  computed once at ingest time and cached for repeated ingestion.
- **Retrieval mechanism:** ChromaDB persistent collection, cosine-similarity
  nearest-neighbour search.
- **How many chunks:** 4 by default, 6 for questions detected as "broad"
  (comparisons/overviews) by the specialization wrapper — trading off
  coverage vs. speed and precision.
- **Passing to the LLM:** retrieved chunks are concatenated with their
  source filename and chunk index into a `retrieved_context` block, inserted
  into the active mode's system prompt (TOCD/RTAO/Ultimate/normal).

**Response context (instruction given to the LLM):** "Answer the user's
question using only the retrieved context. If the retrieved information is
insufficient, explicitly state that the available knowledge base does not
contain enough information." This exact instruction is embedded in every
prompt template in `templates.py`.

## 4. Deliverable

A functional prototype consisting of: (A) a curated knowledge base
(`knowledge_base/*.txt`); (B) a document processing pipeline
(`ingest.py`: clean → chunk → embed → store in Chroma); (C) a retrieval
component (`rag_engine.py::retrieve`); (D) a generation component (Ollama
chat via `ollama_client.py`, controlled by mode-specific prompts in
`templates.py`); (E) a web-based user interface (FastAPI + static
HTML/CSS/JS in `static/`, served by `app.py`) implementing
User Query → RAG System → Retrieved Context → Generated Response; and
(F) a source/grounding display (the UI shows the source file(s) used and a
"grounded ✓ / check grounding ⚠" tag for every answer).
