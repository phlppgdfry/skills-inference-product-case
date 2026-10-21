"""The skills taxonomy and the alias matcher.

The taxonomy is the product's vocabulary: every skill SkillDraft can suggest has an id here.
Nothing outside it can be suggested (ADR-0001), which is what makes the output comparable
across roles, customers and model versions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .text import Token, fold, tokenize

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "taxonomy.json"


@dataclass(frozen=True)
class AliasHit:
    skill_id: str
    alias: str
    first: int  # token index
    last: int
    start: int  # char offsets
    end: int
    ambiguous: bool


class Taxonomy:
    def __init__(self, data: dict):
        self.version: str = data["version"]
        self.skills: list[dict] = data["skills"]
        self.by_id: dict[str, dict] = {s["id"]: s for s in self.skills}
        self.trie: dict = {}
        for s in self.skills:
            for a in s["aliases"]:
                words = [t.text for t in tokenize(fold(a["text"]))]
                node = self.trie
                for w in words:
                    node = node.setdefault(w, {})
                # one alias text can only belong to one skill; the taxonomy test guards this
                node["$"] = (s["id"], a["text"], a["ambiguous"])

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> Taxonomy:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def profile_text(self, skill_id: str) -> str:
        """The text that represents a skill for semantic matching: label, aliases, definitions."""
        s = self.by_id[skill_id]
        parts = [s["label"], *(a["text"] for a in s["aliases"]), s["definition"]["en"], s["definition"]["nl"]]
        return ". ".join(parts)

    def match(self, tokens: list[Token]) -> list[AliasHit]:
        """Longest alias match at each position, scanning left to right without overlaps."""
        hits: list[AliasHit] = []
        i = 0
        while i < len(tokens):
            node, j, best = self.trie, i, None
            while j < len(tokens) and tokens[j].text in node:
                node = node[tokens[j].text]
                if "$" in node:
                    best = (j, node["$"])
                j += 1
            if best:
                last, (sid, alias, amb) = best
                hits.append(AliasHit(sid, alias, i, last, tokens[i].start, tokens[last].end, amb))
                i = last + 1
            else:
                i += 1
        return hits

    def search(self, query: str, limit: int = 10) -> list[dict]:
        q = fold(query).strip()
        scored = []
        for s in self.skills:
            names = [fold(s["label"])] + [fold(a["text"]) for a in s["aliases"]]
            if any(n == q for n in names):
                scored.append((0, s["label"], s))
            elif any(n.startswith(q) for n in names):
                scored.append((1, s["label"], s))
            elif any(q in n for n in names):
                scored.append((2, s["label"], s))
        return [s for _, _, s in sorted(scored, key=lambda x: (x[0], x[1]))[:limit]]
