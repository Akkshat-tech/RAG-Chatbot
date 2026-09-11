"""
run_eval.py
-----------
Deliverable / Requirement 7 (Evaluation of the RAG tool).

Runs every question in test_questions.json through the live RAG engine
(requires Ollama + the vector store already built via `python ingest.py`)
and writes a filled-in markdown evaluation report to eval/evaluation_report.md

Usage (from the project root, with Ollama running):
    python -m eval.run_eval
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_engine import engine  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def truncate(text: str, n: int = 220) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def run():
    with open(os.path.join(HERE, "test_questions.json"), "r", encoding="utf-8") as f:
        questions = json.load(f)

    rows = []
    for q in questions:
        session_id = f"eval-{q['id']}"
        result = engine.answer(session_id, q["query"])
        retrieved_summary = "; ".join(
            f"{c['source']}#{c['chunk_index']}" for c in result.get("retrieved_chunks", [])
        ) or "(none retrieved)"
        rows.append({
            **q,
            "generated_answer": result["answer"],
            "retrieved_info": retrieved_summary,
            "grounded": result.get("grounded"),
            "latency_ms": result.get("latency_ms"),
        })

    out_path = os.path.join(HERE, "evaluation_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Evaluation Report -- Inquiry-Based Commerce Mentor RAG\n\n")
        f.write(f"Chat model / Embed model: see config.py. Total questions: {len(rows)}\n\n")
        f.write("| ID | Category | Query | Expected Answer | Retrieved Information | Generated Answer | Grounded? |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(
                f"| {r['id']} | {r['category']} | {truncate(r['query'], 80)} | "
                f"{truncate(r['expected_answer_note'], 120)} | {truncate(r['retrieved_info'], 100)} | "
                f"{truncate(r['generated_answer'], 180)} | {r['grounded']} |\n"
            )

        # simple aggregate analysis
        f.write("\n## Aggregate analysis\n\n")
        by_cat = {}
        for r in rows:
            by_cat.setdefault(r["category"], []).append(r)
        for cat, items in by_cat.items():
            grounded_count = sum(1 for i in items if i["grounded"])
            f.write(f"- **{cat}**: {len(items)} questions, {grounded_count} marked grounded by the verifier.\n")

        f.write(
            "\nFill in manual judgement here after reviewing the table above:\n"
            "- Retrieval quality: (did the right document/chunk show up for each question?)\n"
            "- Answer quality: (was the answer actually correct and well-explained?)\n"
            "- Groundedness: (do you agree with the automatic verifier's Yes/No?)\n"
            "- Hallucinations: (for Q14/Q15, did the model invent the 3:1 figure or a page number?)\n"
            "- Failure cases: (list any question the system handled badly and why)\n"
        )

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
