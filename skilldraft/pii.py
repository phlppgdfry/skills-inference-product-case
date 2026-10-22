"""Mask personal data in a CV before anything else reads it (ADR-0010).

Masking keeps the length of the text: every character of a detected item becomes "•",
which is not a token character, so offsets of skills evidence stay valid and no quote in
a response can contain a name, an address or a birth date. The response reports what was
masked by kind and count, never the values.

Detectors are patterns for Belgian CVs: e-mail, phone, birth date, national register
number, street address, and the name on the first line (plus every later repeat of it).
The eval suite measures coverage against the generator's personal-data spans and checks
that no gold value appears anywhere in a response.
"""

from __future__ import annotations

import re

MASK = "•"
# In order of priority: when two patterns cover the same characters, the earlier kind wins
# ("03/04/1988" also looks like a phone number to the phone pattern).
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("national_id", re.compile(r"\b\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}\b")),
    ("birthdate", re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b")),
    ("phone", re.compile(r"(?:\+32\s?|0)4\d{2}(?:[\s./]?\d{2}){3}\b|(?:\+32\s?|0)\d{1,2}(?:[\s./]?\d{2,3}){3}\b")),
    ("address", re.compile(r"\b[A-Z][a-zà-ÿ]+(?:straat|laan|weg|plein|steenweg|dreef|lei|kaai|street|road|avenue)\s\d{1,4}[a-z]?,?\s\d{4}\s[A-Z][a-zà-ÿ-]+")),
]
NAME_WORD = re.compile(r"^(?:[A-Z][a-zà-ÿ']+(?:-[A-Z][a-zà-ÿ']+)*|[Vv]an|[Dd]e|[Dd]er|[Ee]l|[Ll]e|[Bb]en)$")  # incl. double names


def first_line_name(text: str) -> tuple[int, int] | None:
    """The CV's first non-empty line, if it looks like a name (2 to 4 capitalised words)."""
    pos = 0
    for line in text.split("\n"):
        if line.strip():
            words = line.split()
            if 2 <= len(words) <= 4 and all(NAME_WORD.match(w) for w in words) and words[0][0].isupper():
                start = pos + len(line) - len(line.lstrip())
                return start, start + len(line.strip())
            return None
        pos += len(line) + 1
    return None


def find(text: str) -> list[dict]:
    spans: list[dict] = []
    name = first_line_name(text)
    if name:
        value = text[name[0]:name[1]]
        spans += [{"kind": "name", "start": m.start(), "end": m.end(), "rank": -1} for m in re.finditer(re.escape(value), text)]
    for rank, (kind, pattern) in enumerate(PATTERNS):
        spans += [{"kind": kind, "start": m.start(), "end": m.end(), "rank": rank} for m in pattern.finditer(text)]
    spans.sort(key=lambda s: (s["start"], s["rank"], -s["end"]))
    merged: list[dict] = []
    for s in spans:
        if merged and s["start"] < merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], s["end"])
            continue
        merged.append({k: v for k, v in s.items() if k != "rank"})
    return merged


def mask(text: str) -> tuple[str, dict[str, int]]:
    """Return the text with personal data replaced by "•" (same length) and counts per kind."""
    chars = list(text)
    counts: dict[str, int] = {}
    for s in find(text):
        for i in range(s["start"], s["end"]):
            if not chars[i].isspace():
                chars[i] = MASK
        counts[s["kind"]] = counts.get(s["kind"], 0) + 1
    return "".join(chars), dict(sorted(counts.items()))
