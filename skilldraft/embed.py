"""Semantic matching between a sentence and a skill.

The default embedder is a hashing embedder on the standard library: word and character
4-gram features, IDF-weighted over the taxonomy, compared with cosine similarity. It is
deterministic, needs no download and runs in the browser demo too.

It is a stand-in for a real sentence encoder. skilldraft/adapters/hf_embedder.py plugs a
multilingual Transformers model into the same interface, and evals/run.py --embedder hf
measures both (EVIDENCE.md lists the results).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from .text import STOPWORDS, fold, tokenize

Vector = dict[int, float] | list[float]


class Embedder(Protocol):
    name: str

    def fit(self, skill_texts: Sequence[str]) -> None: ...

    def encode(self, texts: Sequence[str]) -> list[Vector]: ...

    def similarity(self, a: Vector, b: Vector) -> float: ...


def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for byte in s.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def features(text: str) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    for t in tokenize(fold(text)):
        w = t.text
        if w in STOPWORDS or len(w) < 2:
            continue
        out.append((fnv1a("w:" + w), 1.0))
        padded = "<" + w + ">"
        for i in range(len(padded) - 3):
            out.append((fnv1a("c:" + padded[i:i + 4]), 0.25))
    return out


class HashingEmbedder:
    name = "hashing-v1"
    # Below this a semantic match does not become a candidate. Chosen on the dev split
    # (evals/reports/sweep.hashing-v1.json): best F1; higher values halve the review load
    # at the cost of recall (docs/07-stakeholders/trade-off-memo.md).
    min_similarity = 0.08

    def __init__(self) -> None:
        self.idf: dict[int, float] = {}
        self.default_idf = 1.0

    def fit(self, skill_texts: Sequence[str]) -> None:
        df: dict[int, int] = {}
        for text in skill_texts:
            for key in {k for k, _ in features(text)}:
                df[key] = df.get(key, 0) + 1
        n = len(skill_texts)
        self.idf = {k: math.log((n + 1) / (c + 1)) + 1.0 for k, c in df.items()}
        self.default_idf = math.log(n + 1) + 1.0

    def encode(self, texts: Sequence[str]) -> list[dict[int, float]]:
        out = []
        for text in texts:
            v: dict[int, float] = {}
            for k, w in features(text):
                v[k] = v.get(k, 0.0) + w
            for k in v:
                v[k] = (1.0 + math.log(v[k]) if v[k] >= 1.0 else v[k]) * self.idf.get(k, self.default_idf)
            norm = math.sqrt(sum(x * x for x in v.values()))
            out.append({k: x / norm for k, x in v.items()} if norm else {})
        return out

    def similarity(self, a: dict[int, float], b: dict[int, float]) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b[k] for k, x in a.items() if k in b)
