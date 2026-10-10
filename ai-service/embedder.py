"""Turns text into vectors.

Real model: sentence-transformers "all-MiniLM-L6-v2" (384 numbers per sentence, runs on CPU).
Fallback:   a simple hashing embedder, used only if the model cannot be loaded (for example no internet
            for the first download). It matches shared words, not meaning, so results are weaker.

Every vector returned is L2-normalised, so the dot product of two vectors equals their cosine similarity.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re

import numpy as np

log = logging.getLogger("embedder")

DIM = 384


class SentenceEmbedder:
    def __init__(self, model, name: str):
        self._model = model
        self.name = name

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)


class HashingEmbedder:
    """Bag of words and character trigrams hashed into a fixed-size vector."""

    name = "hashing-fallback"

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                self._add(out[row], "w:" + word, 1.0)
                padded = f"#{word}#"
                for i in range(len(padded) - 2):
                    self._add(out[row], "c:" + padded[i : i + 3], 0.3)
            norm = np.linalg.norm(out[row])
            if norm > 0:
                out[row] /= norm
        return out

    @staticmethod
    def _add(vec: np.ndarray, token: str, weight: float) -> None:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[index] += sign * weight


def load_embedder():
    """AI_EMBEDDER=hash forces the fallback. AI_MODEL changes the model name."""
    if os.getenv("AI_EMBEDDER", "").lower() == "hash":
        log.warning("AI_EMBEDDER=hash: using the hashing fallback instead of a transformer model")
        return HashingEmbedder()

    model_name = os.getenv("AI_MODEL", "all-MiniLM-L6-v2")
    try:
        from sentence_transformers import SentenceTransformer

        log.info("Loading transformer model %s (first run downloads about 90 MB)", model_name)
        return SentenceEmbedder(SentenceTransformer(model_name), model_name)
    except Exception as exc:  # noqa: BLE001 - any failure should fall back, not crash the service
        log.warning("Could not load %s (%s). Falling back to the hashing embedder.", model_name, exc)
        return HashingEmbedder()
