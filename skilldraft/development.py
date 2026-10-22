"""Development plan: what a person could learn next for a role.

Input: a reviewed role profile and the skills a person holds (from a reviewed CV profile or
the HR system). Output: coverage, the skills they already have, and the gaps in a suggested
order: required before nice-to-have, and within each, gaps next to a skill the person
already holds first ("close to learn"), because those are the cheapest to close.

It is a conversation starter for the person and their manager, not an assessment: it says
nothing about how well someone masters a skill, and it never ranks people (ADR-0010).
"""

from __future__ import annotations

from .match import WEIGHT


def plan(role_skills: list[dict], person_skills: list[str], taxonomy) -> dict:
    have = set(person_skills)
    role = [s for s in role_skills if s.get("status", "suggested") == "suggested"]
    total = sum(WEIGHT[s["importance"]] for s in role)
    covered = sum(WEIGHT[s["importance"]] for s in role if s["id"] in have)
    gaps = []
    for s in role:
        if s["id"] in have:
            continue
        sk = taxonomy.by_id[s["id"]]
        near = sorted(r for r in sk["related"] if r in have)
        gaps.append({"id": s["id"], "label": sk["label"], "importance": s["importance"],
                     "close_to": [{"id": r, "label": taxonomy.by_id[r]["label"]} for r in near],
                     "why": (f"close to {', '.join(taxonomy.by_id[r]['label'] for r in near)}, which you already have"
                             if near else "new for you")})
    gaps.sort(key=lambda g: (g["importance"] != "required", not g["close_to"], g["label"]))
    for i, g in enumerate(gaps, start=1):
        g["order"] = i
    return {"coverage": round(covered / total, 3) if total else 0.0,
            "have": sorted(s["id"] for s in role if s["id"] in have), "gaps": gaps,
            "note": "A starting point for a development conversation, not an assessment of the person."}
