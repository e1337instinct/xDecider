import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())

# Per-session in-memory RAG store
rag_store: dict = {}


@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/library", methods=["POST"])
def set_library():
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])

        if not items:
            return jsonify({"error": "Please add at least one item to your library."}), 400

        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        session_id = session["session_id"]

        from rag import LibraryRAG

        rag = LibraryRAG()
        rag.build_index(items)
        rag_store[session_id] = rag

        return jsonify({"success": True, "count": len(items)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/genre-detect", methods=["POST"])
def genre_detect():
    try:
        data = request.get_json(silent=True) or {}
        title = data.get("title", "").strip()
        media_type = data.get("type", "")
        if not title:
            return jsonify({"genre": ""})
        from rag import detect_genre
        genre = detect_genre(title, media_type)
        return jsonify({"genre": genre})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/recommend", methods=["POST"])
def recommend():
    try:
        session_id = session.get("session_id")
        rag = rag_store.get(session_id) if session_id else None

        if not rag:
            return jsonify({"error": "Library not found. Please re-add your library."}), 400

        data = request.get_json(silent=True) or {}
        mood_data = data.get("mood", {})

        result = rag.get_recommendation(mood_data)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True)
