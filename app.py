"""
app.py
Flask backend + simple web UI for the "Inquiry-Based Commerce Mentor" RAG tool.

Run:
    python app.py
Then open http://localhost:5000 in your browser.
"""
from flask import Flask, request, jsonify, render_template
import rag_engine

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    mode = data.get("mode", "tocd")  # "tocd" or "rtao"

    if not query:
        return jsonify({"error": "Empty query"}), 400

    try:
        result = rag_engine.answer_query(query, mode=mode)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
