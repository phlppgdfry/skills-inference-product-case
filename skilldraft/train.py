"""Train the scorer on the train split and pick thresholds on the dev split.

    python -m skilldraft train                 # hashing embedder → models/scorer.hashing-v1.json
    python -m skilldraft train --embedder hf   # Transformers embedder (needs the [ml] extra)

The test split is never touched here; evals/run.py reports on it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .pii import mask
from .scorer import LogisticModel, pick_thresholds, train_logistic

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MODELS = ROOT / "models"
L2 = 1e-3


def load_jds(split: str | None = None) -> list[dict]:
    rows = [json.loads(line) for line in (DATA / "job_descriptions.jsonl").read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if split is None or r["split"] == split]


def load_cvs(split: str | None = None) -> list[dict]:
    rows = [json.loads(line) for line in (DATA / "cvs.jsonl").read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if split is None or r["split"] == split]


def load_docs(kind: str, split: str | None = None) -> list[dict]:
    return load_cvs(split) if kind == "cv" else load_jds(split)


def examples(pipeline, jds: list[dict]) -> tuple[list[list[float]], list[int], int]:
    """Candidate feature vectors with labels (1 = the skill is in the gold profile)."""
    X, y, positives = [], [], 0
    for jd in jds:
        gold = {g["id"] for g in jd["gold"]["skills"]}
        positives += len(gold)
        text = mask(jd["text"])[0] if pipeline.kind == "cv" else jd["text"]
        for sid, c in sorted(pipeline.analyse(text).candidates.items()):
            X.append(c.features)
            y.append(1 if sid in gold else 0)
    return X, y, positives


def model_path(embedder_name: str, kind: str = "jd") -> Path:
    return MODELS / (f"scorer.{embedder_name}.json" if kind == "jd" else f"scorer.{kind}.{embedder_name}.json")


def train(pipeline, l2: float = L2) -> LogisticModel:
    train_jds, dev_jds = load_docs(pipeline.kind, "train"), load_docs(pipeline.kind, "dev")
    X, y, _ = examples(pipeline, train_jds)
    w, b = train_logistic(X, y, l2=l2)
    model = LogisticModel(w, b, embedder=pipeline.embedder.name, l2=l2,
                          trained_on="train split: " + hashlib.sha256(json.dumps(train_jds, sort_keys=True).encode()).hexdigest()[:12])
    Xd, yd, _ = examples(pipeline, dev_jds)
    model.accept_at, model.review_at = pick_thresholds([model.predict(x) for x in Xd], yd)
    return model
