# Inquiry-Based Commerce Mentor: RAG Prototype

A Retrieval-Augmented Generation tutor for NCERT Class 11/12 Commerce
(Accountancy + Business Studies), built for the "Design and Develop a
RAG-Based Tool Using the TOCD Framework" homework, running entirely on a
local Ollama server + ChromaDB — no external API keys needed.

See `docs/TOCD_SPECIFICATION.md`, `docs/TOCD_PROMPT.md`,
`docs/architecture_diagram.svg` and `docs/REFLECTION.md` for the written
deliverables, and `eval/` for the evaluation harness.

## 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- Two models pulled:
  ```bash
  ollama pull llama3.1:8b
  ollama pull nomic-embed-text
  ```
  (You can swap these for `mistral`, `gemma2`, etc. — just update
  `CHAT_MODEL`/`EMBED_MODEL` at the top of `config.py`.)

## 2. Setup

```bash
cd commerce_mentor_rag
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

Make sure Ollama is running in another terminal:
```bash
ollama serve
```

## 3. Build the vector store (Document Processing Pipeline)

Curate/edit the files under `knowledge_base/*.txt` (the shipped files are
original demo notes on core Accountancy/Business Studies topics — replace or
extend them with your own group's curated material, e.g. FAQs, policy
excerpts, or your own class notes, before submitting).

```bash
python ingest.py
```

This cleans, chunks, embeds and stores everything in a local `chroma_store/`
folder. Re-run it any time you change the knowledge base (there's also a
"Rebuild knowledge base index" button in the web UI, which calls the same
pipeline via `POST /reindex`).

## 4. Run the app

```bash
uvicorn app:app --reload --port 8000
```

Open **http://localhost:8000** in a browser.

## 5. Using the chat modes

Type one of these as the first word of a message to switch how answers are
structured for the rest of the session (there are also buttons in the UI):

| Keyword      | Mode                                                          |
|--------------|----------------------------------------------------------------|
| `:normal`    | Plain grounded Q&A (Task/Objective/Context/Deliverable, terse) |
| `:tocd`      | Full TOCD structure + inquiry-cycle guided reasoning           |
| `:rtao`      | Reverse-interaction: Identify → Engage → Analyze → Respond      |
| `:ultimate`  | The "Ultimate Prompt Template" skeleton (Role/Context/Goal/…)   |
| `:modes`     | Shows this list inside the chat                                 |

Example: `:tocd what is depreciation?`

## 6. What's implemented, mapped to the homework's requirements

| Requirement | Where |
|---|---|
| TOCD / RTAO / Ultimate templates, switchable by keyword | `templates.py`, `rag_engine.py` |
| Domain guard wrapper (generalization/specialization gate, keeps bot on-topic) | `wrappers.py::domain_guard_wrapper` |
| Chain-of-thought ambiguity wrapper (asks clarifying questions) | `wrappers.py::ambiguity_wrapper` |
| Groundedness / hallucination-check wrapper | `wrappers.py::groundedness_wrapper` |
| Broad-vs-narrow retrieval wrapper | `wrappers.py::specialization_wrapper` |
| Personalization / hyper-personalization | `wrappers.py::UserProfile`, `ProfileStore` |
| Reverse-interaction cycle (Identify/Engage/Analyze/Respond & iterate) | `:rtao` mode in `templates.py` |
| Efficient retrieval (fast + accurate) | embedding cache + query-result cache in `ollama_client.py`/`rag_engine.py`, cosine top-k in Chroma, relevance floor to skip irrelevant chunks |
| Document Processing Pipeline (clean → chunk → embed → vector store) | `ingest.py` |
| Web UI, source/grounding display | `static/`, `app.py` |
| Evaluation harness (15 test questions across 4 categories) | `eval/test_questions.json`, `eval/run_eval.py` |

## 7. Running the evaluation

Once `ingest.py` has been run and Ollama is up:
```bash
python -m eval.run_eval
```
This writes `eval/evaluation_report.md` with the 15 test questions
(5 straightforward, 5 complex, 3 insufficient-information, 2
hallucination-probes) run against the live system, including retrieved
sources and the automatic groundedness verdict. `eval/SAMPLE_evaluation_report_MOCKED.md`
shows the expected shape of this report from an offline dry run with a
mocked model — regenerate the real one before submitting.

## 8. Notes / honest limitations

- The shipped `knowledge_base/*.txt` files are original demo notes written
  for this prototype (not copied from the NCERT textbooks) — swap in your
  own group's curated material for the real submission.
- The domain guard, ambiguity check and groundedness check each make an
  extra LLM call in the unclear/ambiguous case; the fast paths (keyword
  matching) avoid this for the common case, but a local 8B model on CPU can
  still be slow — GPU acceleration or a smaller model will help.
- `MIN_RELEVANCE_SCORE` in `config.py` may need tuning once you swap in your
  own knowledge base or embedding model.
