"""Coded-language checker for job descriptions.

Job ads that say "young and dynamic team", "he will report to" or "native speaker" put
off qualified people and, in Belgium, can breach the anti-discrimination laws of 2007
(age, gender, origin). The checker flags the phrase and suggests neutral wording; HR
decides. It is a lexicon on purpose: every flag is explainable, and the evals measure
what it misses (data/job_descriptions.jsonl holds coded phrases it does not know).
"""

from __future__ import annotations

from .text import fold, tokenize

# (category, token pattern, suggestion). "#" matches any number.
LEXICON: list[tuple[str, list[str], str]] = [
    ("age", ["young", "and", "dynamic"], "Describe the team's way of working instead of its age: 'an energetic team that moves fast'."),
    ("age", ["young", "dynamic"], "Describe the way of working instead of age."),
    ("age", ["digital", "native"], "Name the skill: 'comfortable with digital tools'."),
    ("age", ["jong", "en", "dynamisch"], "Beschrijf de manier van werken, niet de leeftijd: 'een energiek team'."),
    ("age", ["jong", "dynamisch"], "Beschrijf de manier van werken, niet de leeftijd."),
    ("age", ["maximaal", "#", "jaar"], "Een leeftijdsgrens is in België verboden, tenzij wettelijk vereist."),
    ("age", ["maximum", "#", "years", "old"], "An age limit is unlawful in Belgium unless the law requires it."),
    ("gender", ["he"], "Address the candidate as 'you'."),
    ("gender", ["she"], "Address the candidate as 'you'."),
    ("gender", ["guy"], "Use a neutral word: 'person', 'colleague'."),
    ("gender", ["salesman"], "Use 'salesperson' or 'sales representative'."),
    ("gender", ["hij"], "Spreek de kandidaat aan met 'je'."),
    ("gender", ["vakman"], "Gebruik 'vakkracht' of 'vakspecialist'."),
    ("origin", ["native", "speaker"], "Ask for the level you need: 'fluent (C1) Dutch'."),
    ("origin", ["native", "speakers"], "Ask for the level you need: 'fluent (C1)'."),
    ("origin", ["moedertaal"], "Vraag het niveau dat je nodig hebt: 'vlot Nederlands (C1)'."),
]


def check(text: str) -> list[dict]:
    toks = tokenize(fold(text))
    words = [t.text for t in toks]
    flags = []
    i = 0
    while i < len(words):
        hit = None
        for category, pattern, suggestion in LEXICON:
            n = len(pattern)
            window = words[i:i + n]
            if len(window) == n and all(p == w or (p == "#" and w.isdigit()) for p, w in zip(pattern, window)):
                if hit is None or n > len(hit[1]):
                    hit = (category, pattern, suggestion)
        if hit:
            n = len(hit[1])
            start, end = toks[i].start, toks[i + n - 1].end
            flags.append({"category": hit[0], "start": start, "end": end, "quote": text[start:end], "suggestion": hit[2]})
            i += n
        else:
            i += 1
    return flags
