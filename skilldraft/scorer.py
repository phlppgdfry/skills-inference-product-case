"""The calibrated scorer: logistic regression over a dozen readable features.

Why not a bigger model: the features are few and meaningful, the label set is small, and a
product owner can read the weights (docs/04-quality/model-card.md prints them). A logistic
model is also well calibrated out of the box, which the review band depends on (ADR-0003).

The trainer is plain gradient descent on the standard library. training/train_torch.py fits
the same objective with PyTorch; tests/test_torch_parity.py checks both land on the same
weights.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

FEATURES = [
    "exact_good",      # alias match, not negated, in title/role/profile/nice-to-have/unknown
    "exact_bad",       # alias match only in "about us" or "what we offer"
    "negated",         # only negated alias matches ("no experience with X needed")
    "sem_good",        # best semantic similarity in a good section
    "sem_margin",      # how far that sentence prefers this skill over the next best
    "ambiguous_only",  # every alias match was an ambiguous alias (SAP, lean, safety)
    "mentions",        # log(1 + number of non-negated pieces of evidence)
    "in_pref",         # the best evidence reads as nice-to-have
    "in_title",        # an alias in the job title
    "company_voice",   # all evidence is "we/our" talk, none addresses the candidate
    "no_headings",     # the description has no recognisable sections
]


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


@dataclass
class LogisticModel:
    weights: list[float]
    bias: float
    features: list[str] = field(default_factory=lambda: list(FEATURES))
    accept_at: float = 0.5
    review_at: float = 0.3
    embedder: str = "hashing-v1"
    trained_on: str = ""
    l2: float = 0.0

    def predict(self, x: Sequence[float]) -> float:
        return sigmoid(self.bias + sum(w * v for w, v in zip(self.weights, x)))

    @property
    def version(self) -> str:
        blob = json.dumps([round(w, 6) for w in self.weights] + [round(self.bias, 6), self.accept_at, self.review_at, self.embedder])
        return "scorer-" + hashlib.sha256(blob.encode()).hexdigest()[:8]

    def to_json(self) -> dict:
        return {
            "version": self.version, "embedder": self.embedder, "features": self.features,
            "weights": [round(w, 6) for w in self.weights], "bias": round(self.bias, 6),
            "accept_at": self.accept_at, "review_at": self.review_at, "l2": self.l2, "trained_on": self.trained_on,
        }

    @classmethod
    def from_json(cls, d: dict) -> LogisticModel:
        return cls(d["weights"], d["bias"], d["features"], d["accept_at"], d["review_at"], d["embedder"], d.get("trained_on", ""), d.get("l2", 0.0))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=1) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> LogisticModel:
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))


def loss(weights: Sequence[float], bias: float, X: Sequence[Sequence[float]], y: Sequence[int], l2: float) -> float:
    total = 0.0
    for xi, yi in zip(X, y):
        p = min(max(sigmoid(bias + sum(w * v for w, v in zip(weights, xi))), 1e-12), 1 - 1e-12)
        total -= yi * math.log(p) + (1 - yi) * math.log(1 - p)
    return total / len(X) + 0.5 * l2 * sum(w * w for w in weights)


def train_logistic(X: Sequence[Sequence[float]], y: Sequence[int], l2: float = 1e-3, lr: float = 1.0,
                   epochs: int = 4000, tol: float = 1e-9) -> tuple[list[float], float]:
    """Full-batch gradient descent on mean log loss + (l2/2)·||w||² (bias not penalised).

    The objective is convex, so any optimiser that converges lands on the same weights.
    """
    d = len(X[0])
    w, b = [0.0] * d, 0.0
    n = len(X)
    prev = float("inf")
    for _ in range(epochs):
        gw, gb = [0.0] * d, 0.0
        for xi, yi in zip(X, y):
            err = sigmoid(b + sum(wj * xj for wj, xj in zip(w, xi))) - yi
            gb += err
            for j in range(d):
                gw[j] += err * xi[j]
        w = [wj - lr * (g / n + l2 * wj) for wj, g in zip(w, gw)]
        b -= lr * gb / n
        cur = loss(w, b, X, y, l2) if _ % 50 == 0 else prev
        if _ % 50 == 0:
            if prev - cur < tol:
                break
            prev = cur
    return w, b


def pick_thresholds(probs: Sequence[float], labels: Sequence[int], positives: int,
                    target_precision: float = 0.95, target_recall: float = 0.95) -> tuple[float, float]:
    """accept_at: the lowest threshold whose accepted set reaches the precision target.
    review_at: the highest threshold at which accepted + review still reach the recall target.

    `positives` counts every gold skill, including those that never became a candidate, so
    recall is measured against the job descriptions and not against the candidates.
    """
    pairs = sorted(zip(probs, labels), reverse=True)
    accept_at, review_at = 1.0, 1.0
    tp = fp = 0
    best_recall_threshold = None
    for p, y in pairs:
        tp += y
        fp += 1 - y
        if tp / (tp + fp) >= target_precision:
            accept_at = p
        if best_recall_threshold is None and tp / positives >= target_recall:
            best_recall_threshold = p
    review_at = best_recall_threshold if best_recall_threshold is not None else min(p for p, _ in pairs)
    accept_at = round(accept_at, 3)
    review_at = round(min(review_at, accept_at), 3)
    return accept_at, max(review_at, 0.05)
