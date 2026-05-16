import os
import re
import numpy as np
import faiss
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _client = OpenAI(api_key=api_key)
    return _client


_TIME_MAP = {
    "quick": "less than 30 minutes — a single TV episode or short session is ideal; shows are a great fit here",
    "medium": "1 to 2 hours — a solid session",
    "long": "2 to 4 hours — a long, immersive experience",
    "all_day": "all day — maximum length and immersion",
}
_ENERGY_MAP = {
    "low": "low energy, want something easy and relaxing",
    "medium": "medium energy, ready for comfortable engagement",
    "high": "high energy, pumped and ready for action",
}
_MOOD_MAP = {
    "chill":       "chill and relaxed",
    "adventurous": "adventurous and exploratory",
    "social":      "social, fun, and light-hearted",
    "thoughtful":  "thoughtful and introspective",
    "thrilling":   "thrilled, tense, on the edge of my seat",
    "creative":    "creative and imaginative",
    "uplifting":   "uplifted, inspired, and feel-good",
    "competitive": "competitive and in the zone, ready to win or challenge myself",
    "horror":      "craving something scary, tense, and terrifying",
    "dark_humor":  "in the mood for dark, twisted, or cynical humor",
    "romantic":    "romantic and in the mood for love stories or emotional connection",
    "nostalgic":   "nostalgic, wanting something comforting or classic from the past",
}


def detect_genre(title: str, media_type: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a media database assistant. Given a title and its type (Movie, Show, or Game), "
                    "respond with only the genre — no explanation, no extra punctuation. "
                    "Keep it concise: 1–3 words. Examples: 'Action RPG', 'Romantic Comedy', 'Horror', 'Family'."
                ),
            },
            {"role": "user", "content": f"Title: {title}\nType: {media_type or 'unknown'}"},
        ],
        temperature=0,
        max_tokens=20,
    )
    return response.choices[0].message.content.strip()


class LibraryRAG:
    def __init__(self) -> None:
        self.index: faiss.IndexFlatIP | None = None
        self.items: list[dict] = []

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def _embed(self, texts: list[str]) -> np.ndarray:
        client = _get_client()
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return np.array([e.embedding for e in response.data], dtype=np.float32)

    @staticmethod
    def _item_to_text(item: dict) -> str:
        parts = [item.get("title", ""), item.get("type", "Unknown")]
        if item.get("genre"):
            parts.append(item["genre"])
        if item.get("notes"):
            parts.append(item["notes"])
        return " | ".join(p for p in parts if p)

    @staticmethod
    def _mood_to_query(mood_data: dict) -> str:
        parts = []
        if mood_data.get("time"):
            parts.append(f"Time available: {_TIME_MAP.get(mood_data['time'], mood_data['time'])}")
        if mood_data.get("energy"):
            parts.append(f"Energy: {_ENERGY_MAP.get(mood_data['energy'], mood_data['energy'])}")
        moods = mood_data.get("moods") or ([mood_data["mood"]] if mood_data.get("mood") else [])
        if moods:
            mood_descs = [_MOOD_MAP.get(m, m) for m in moods]
            parts.append(f"Mood: {', and '.join(mood_descs)}")
        if mood_data.get("social"):
            parts.append("solo" if mood_data["social"] == "solo" else "watching/playing with others")
        if mood_data.get("genre_pref"):
            parts.append(f"Genre preference: {mood_data['genre_pref']}")
        if mood_data.get("free_text"):
            parts.append(f"User's own description: {mood_data['free_text']}")
        return ". ".join(parts)

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def build_index(self, items: list[dict]) -> None:
        self.items = items
        texts = [self._item_to_text(item) for item in items]
        embeddings = self._embed(texts)
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.index.add(embeddings)

    def _search(self, query: str, k: int = 5) -> list[dict]:
        if self.index is None or not self.items:
            return []
        query_emb = self._embed([query])
        faiss.normalize_L2(query_emb)
        k_actual = min(k, len(self.items))
        scores, indices = self.index.search(query_emb, k_actual)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({**self.items[idx], "score": float(score)})
        return results

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------

    def get_recommendation(self, mood_data: dict) -> dict:
        query = self._mood_to_query(mood_data)
        top_matches = self._search(query, k=5)

        if not top_matches:
            raise ValueError("No items in library to recommend from.")

        items_text = "\n".join(
            f"- {m['title']} ({m.get('type', 'Unknown')})"
            + (f" | Genre: {m['genre']}" if m.get("genre") else "")
            + (f" | Notes: {m['notes']}" if m.get("notes") else "")
            for m in top_matches
        )

        prompt = (
            "You are helping a user decide what to watch or play from their personal library.\n\n"
            f"User's current situation:\n{query}\n\n"
            f"Best matching options (pre-filtered by semantic search):\n{items_text}\n\n"
            "Pick the single BEST option and explain in 2–3 sentences why it's perfect for their mood right now. "
            "Be warm and specific. Start your reply with the title in bold: **Title Name**."
        )

        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly, enthusiastic entertainment advisor. "
                        "You help people pick the perfect movie, show, or game from their own library based on their mood. "
                        "When reasoning about fit, infer mood compatibility from genres even when not explicitly stated: "
                        "FPS and MOBA → competitive; horror content → horror mood; adult comedy/satire → dark humor; "
                        "romantic/romance → romantic mood; family/animated → uplifting or chill; "
                        "sandbox/casual/creative → chill or creative; talk shows/party/social games → social; "
                        "historical/drama → thoughtful; thriller/action/suspense → thrilling; "
                        "classic/retro titles → nostalgic; feel-good/inspirational → uplifting. "
                        "TIME CONSTRAINT RULE: when the user has less than 30 minutes, strongly prefer Shows — "
                        "a single episode fits perfectly in that window. Only fall back to a movie or game if no shows are available. "
                        "PARTY GAME RULE: party and social deduction games (e.g. Among Us) are only a good fit when the user is playing with others AND the mood is social or fun — "
                        "never recommend them for solo play, competitive, romantic, or family moods."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=220,
        )

        recommendation_text: str = response.choices[0].message.content or ""

        title_match = re.search(r"\*\*(.+?)\*\*", recommendation_text)
        recommended_title = (
            title_match.group(1) if title_match else top_matches[0].get("title", "")
        )

        top_score = top_matches[0]["score"] if top_matches else 1.0
        return {
            "recommendation": recommendation_text,
            "recommended_title": recommended_title,
            "top_matches": [
                {
                    "title": m.get("title", ""),
                    "type": m.get("type", ""),
                    "genre": m.get("genre", ""),
                    "confidence": max(1, round((m["score"] / top_score) * 100)) if top_score > 0 else 0,
                }
                for m in top_matches[:3]
            ],
        }
