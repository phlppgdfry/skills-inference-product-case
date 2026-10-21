"""Internal mobility: rank people for a role profile and explain the gaps.

score(person) = Σ w·c over the role's skills the person has / Σ w·c over all the role's skills
    w = 1 for required, 0.5 for preferred; c = confidence of the suggestion (1 for gold)

Only suggested skills count. A skill still waiting for review does not decide who gets
shown for a job (ADR-0008).

The ranking is a suggestion for a person to look at, never a decision. Under the AI Act
this part of the product is high-risk (docs/04-quality/ai-act.md), so it stays behind
human review and keeps an explanation per person.
"""

from __future__ import annotations

import math

WEIGHT = {"required": 1.0, "preferred": 0.5}


def role_weights(skills: list[dict], use_confidence: bool = True) -> dict[str, float]:
    out = {}
    for s in skills:
        if s.get("status", "suggested") != "suggested":
            continue
        c = s.get("confidence", 1.0) if use_confidence else 1.0
        out[s["id"]] = WEIGHT[s["importance"]] * c
    return out


def rank(skills: list[dict], people: list[dict], use_confidence: bool = True, related: dict[str, list[str]] | None = None) -> list[dict]:
    weights = role_weights(skills, use_confidence)
    total = sum(weights.values())
    rows = []
    for p in people:
        have = set(p["skills"])
        score = sum(w for sid, w in weights.items() if sid in have) / total if total else 0.0
        gaps = [sid for sid in weights if sid not in have]
        row = {"person_id": p["id"], "score": round(score, 4), "matched": sorted(weights.keys() & have), "gaps": gaps}
        if related is not None:
            row["learnable"] = [g for g in gaps if any(r in have for r in related.get(g, []))]
        rows.append(row)
    rows.sort(key=lambda r: (-r["score"], r["person_id"]))
    return rows


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, float], k: int = 5) -> float:
    dcg = sum(relevance.get(pid, 0.0) / math.log2(i + 2) for i, pid in enumerate(ranked_ids[:k]))
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal))
    return dcg / idcg if idcg else 0.0
