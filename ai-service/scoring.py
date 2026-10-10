"""Ranks colleges for a free-text request.

final score = A * priority_fit + B * wording_fit + C * location_fit      (each part is 0 to 1)

  priority_fit  how well the college does on the things the student cares about
                = w_fees * fee_score + w_place * placement_score + w_rating * rating_score
                The weights w_* come from the transformer: the request is compared with example sentences
                for each priority, and the similarities are turned into weights that add up to 1.
  wording_fit   cosine similarity between the request and the college text (name, city, type, description),
                stretched to 0..1 across the colleges being compared.
  location_fit  1 if the request names the college's city, otherwise 0.

  A, B, C       0.70 / 0.30 / 0.00 normally; 0.55 / 0.20 / 0.25 when a city is named in the request.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

# Example sentences for each priority. The request is compared against these.
PRIORITY_EXAMPLES: dict[str, list[str]] = {
    "low_fees": [
        "I want low fees",
        "affordable and cheap college",
        "budget friendly, low tuition cost",
        "I cannot spend much on education",
    ],
    "high_placements": [
        "good placements",
        "high salary package after graduation",
        "strong campus recruitment and jobs",
        "I want a high paying job from campus placements",
    ],
    "top_rated": [
        "top rated college with good reviews",
        "best reputation and quality of education",
        "highly rated by students",
        "good academics and campus experience",
    ],
}

TEMPERATURE = 0.15  # lower = the strongest priority dominates more
MIN_SIGNAL = 0.25  # if the request is not close to any priority, treat all three as equally important

PARTS_NORMAL = {"priorities": 0.70, "wording": 0.30, "location": 0.00}
PARTS_WITH_CITY = {"priorities": 0.55, "wording": 0.20, "location": 0.25}


@dataclass
class Candidate:
    id: int
    name: str
    city: str
    state: str
    type: str | None
    fees_per_year: float
    avg_placement_lpa: float | None
    rating: float | None
    description: str | None


def softmax(values: list[float], temperature: float) -> np.ndarray:
    z = np.asarray(values, dtype=np.float64) / temperature
    z -= z.max()
    e = np.exp(z)
    return e / e.sum()


def scale(value: float, low: float, high: float) -> float:
    """Min-max scaling to 0..1. If every value is the same, everyone gets 1."""
    return 1.0 if high == low else (value - low) / (high - low)


def college_text(c: Candidate) -> str:
    parts = [c.name, c.city, c.state, f"{c.type or ''} engineering college", c.description or ""]
    return ", ".join(p for p in parts if p).strip()


def rupees(value: float) -> str:
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if value >= 100_000:
        return f"₹{value / 100_000:.2f} L".replace(".00 L", " L")
    return f"₹{int(round(value)):,}"


class Ranker:
    def __init__(self, embedder):
        self.embedder = embedder
        self.model_name = embedder.name
        self._examples = {p: embedder.encode(texts) for p, texts in PRIORITY_EXAMPLES.items()}
        self._cache: dict[str, np.ndarray] = {}

    # ---- embeddings -------------------------------------------------------------------------------------
    def _embed(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            for text, vec in zip(missing, self.embedder.encode(missing)):
                self._cache[text] = vec
        return np.stack([self._cache[t] for t in texts])

    # ---- step 1: what does the student care about? ------------------------------------------------------
    def priority_weights(self, query_vec: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
        similarity = {p: float(np.max(vectors @ query_vec)) for p, vectors in self._examples.items()}
        if max(similarity.values()) < MIN_SIGNAL:
            weights = {p: 1 / len(similarity) for p in similarity}
        else:
            soft = softmax(list(similarity.values()), TEMPERATURE)
            weights = {p: float(w) for p, w in zip(similarity, soft)}
        return weights, similarity

    # ---- step 2: did they name a city? ------------------------------------------------------------------
    @staticmethod
    def find_places(query: str, colleges: list[Candidate]) -> list[str]:
        text = query.lower()
        found: list[str] = []
        # longest names first so "Greater Noida" is taken before "Noida"
        for city in sorted({c.city for c in colleges}, key=len, reverse=True):
            pattern = r"\b" + re.escape(city.lower()) + r"\b"
            if re.search(pattern, text):
                found.append(city)
                text = re.sub(pattern, " ", text)
        return found

    # ---- step 3: score every college --------------------------------------------------------------------
    def rank(self, query: str, colleges: list[Candidate], limit: int = 10) -> dict:
        if not colleges:
            return self._empty(query)

        query_vec = self._embed([query])[0]
        weights, similarity = self.priority_weights(query_vec)
        places = self.find_places(query, colleges)
        parts = PARTS_WITH_CITY if places else PARTS_NORMAL

        wording_raw = self._embed([college_text(c) for c in colleges]) @ query_vec
        w_lo, w_hi = float(wording_raw.min()), float(wording_raw.max())

        fees = [c.fees_per_year for c in colleges]
        placements = [c.avg_placement_lpa or 0.0 for c in colleges]
        f_lo, f_hi = min(fees), max(fees)
        p_lo, p_hi = min(placements), max(placements)

        scored = []
        for i, c in enumerate(colleges):
            fee_score = 1.0 - scale(c.fees_per_year, f_lo, f_hi)
            placement_score = scale(placements[i], p_lo, p_hi)
            rating_score = (c.rating or 0.0) / 5.0

            priority_fit = (
                weights["low_fees"] * fee_score
                + weights["high_placements"] * placement_score
                + weights["top_rated"] * rating_score
            )
            wording_fit = scale(float(wording_raw[i]), w_lo, w_hi)
            location_fit = 1.0 if c.city in places else 0.0

            final = (
                parts["priorities"] * priority_fit
                + parts["wording"] * wording_fit
                + parts["location"] * location_fit
            )
            scored.append((final, i, priority_fit, wording_fit, location_fit))

        scored.sort(key=lambda row: (-row[0], colleges[row[1]].name))

        results = []
        for final, i, priority_fit, wording_fit, location_fit in scored[:limit]:
            c = colleges[i]
            results.append(
                {
                    "id": c.id,
                    "score": int(round(final * 100)),
                    "reasons": self._reasons(c, colleges, weights, wording_fit, location_fit),
                    "breakdown": {
                        "priorities": round(priority_fit, 3),
                        "wording": round(wording_fit, 3),
                        "location": round(location_fit, 3),
                    },
                }
            )

        return {
            "model": self.model_name,
            "priority_weights": {p: round(w, 3) for p, w in weights.items()},
            "priority_similarity": {p: round(s, 3) for p, s in similarity.items()},
            "part_weights": parts,
            "matched_places": places,
            "results": results,
        }

    # ---- plain-language reasons -------------------------------------------------------------------------
    @staticmethod
    def _reasons(c, colleges, weights, wording_fit, location_fit) -> list[str]:
        reasons: list[str] = []
        others = len(colleges) - 1

        if weights["low_fees"] >= 0.25:
            text = f"Fees {rupees(c.fees_per_year)} per year"
            if others > 0:
                cheaper_than = sum(1 for o in colleges if o.fees_per_year > c.fees_per_year)
                text += f", lower than {round(100 * cheaper_than / others)}% of the colleges compared"
            reasons.append(text)

        if weights["high_placements"] >= 0.25:
            if c.avg_placement_lpa is None:
                reasons.append("Placement data not available")
            else:
                reasons.append(f"Average package {c.avg_placement_lpa:g} LPA")

        if weights["top_rated"] >= 0.25:
            reasons.append("No student rating available" if c.rating is None else f"Student rating {c.rating:.1f} out of 5")

        if location_fit == 1.0:
            reasons.append(f"Located in {c.city}, which you asked for")

        if wording_fit >= 0.8:
            reasons.append("Its name and description closely match your wording")

        return reasons

    def _empty(self, query: str) -> dict:
        return {
            "model": self.model_name,
            "priority_weights": {},
            "priority_similarity": {},
            "part_weights": PARTS_NORMAL,
            "matched_places": [],
            "results": [],
        }
