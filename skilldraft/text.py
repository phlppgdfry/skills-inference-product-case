"""Text handling: folding, tokens with offsets, sentences, sections, negation, voice.

Everything here keeps character offsets into the original text, because every skill the
product suggests must point at the words it came from (ADR-0004). The JavaScript port in
site/assets/skilldraft.mjs mirrors this file line for line; tests/js/parity.mjs checks it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

TOKEN = re.compile(r"[a-z0-9+#]+")
SENTENCE_END = re.compile(r"[.!?;](?=\s)")

# Section keywords, checked in this order (the first match wins).
SECTION_KEYWORDS: list[tuple[str, list[list[str]]]] = [
    ("offer", [["what", "we", "offer"], ["our", "offer"], ["we", "offer"], ["wat", "wij", "bieden"], ["ons", "aanbod"], ["aanbod"], ["benefits"]]),
    ("pref", [["nice", "to", "have"], ["bonus"], ["a", "plus"], ["pluspunten"], ["een", "plus"], ["troeven"]]),
    ("req", [["what", "you", "bring"], ["your", "profile"], ["requirements"], ["profile"], ["jouw", "profiel"], ["profiel"],
             ["wat", "breng", "je", "mee"], ["vereisten"], ["who", "you", "are"]]),
    ("resp", [["your", "role"], ["responsibilities"], ["what", "you", "will", "do"], ["jouw", "rol"], ["takenpakket"],
              ["wat", "ga", "je", "doen"], ["functie"]]),
    ("about", [["about"], ["who", "we", "are"], ["over"], ["wie", "zijn", "we"], ["bedrijf"], ["company"]]),
]
GOOD_SECTIONS = ("title", "resp", "req", "pref", "unknown", "profile", "experience", "skills", "languages", "education")

# CVs have their own sections. Lines before the first CV heading are the personal header.
CV_SECTION_KEYWORDS: list[tuple[str, list[list[str]]]] = [
    ("experience", [["experience"], ["work", "experience"], ["werkervaring"], ["ervaring"], ["employment"]]),
    ("skills", [["skills"], ["vaardigheden"], ["competenties"]]),
    ("languages", [["languages"], ["talen"]]),
    ("education", [["education"], ["courses"], ["opleiding"], ["opleidingen"], ["certificates"]]),
    ("profile", [["profile"], ["about", "me"], ["profiel"], ["over", "mij"], ["summary"]]),
    ("interests", [["interests"], ["hobbies"], ["interesses"], ["hobby", "s"]]),
]
# "I would like to learn X" says what someone does not have yet.
ASPIRATION_CUES = [["would", "like", "to", "learn"], ["want", "to", "learn"], ["next", "step"], ["hope", "to"],
                   ["wil", "graag"], ["volgende", "stap"], ["wil", "leren"]]

# A sentence that reads like a "nice to have" even without a heading.
PREFERRED_CUES = [["a", "plus"], ["bonus"], ["nice"], ["pluspunt"], ["troef"], ["meegenomen"], ["would", "be", "nice"]]

# Negation: a cue close to an alias negates that mention.
NEGATION_CUES = {"no", "not", "t", "without", "never", "geen", "niet", "zonder", "hoeft", "nooit"}
# After the alias only a predicate negates ("X is not needed", "X is geen vereiste");
# "Python experience and no fear of change" does not.
NEGATION_AFTER_CUES = {"not", "t", "geen", "niet"}
NEG_BEFORE, NEG_AFTER = 5, 3
# For semantic (whole-sentence) evidence only an explicit "not required" pattern negates,
# because "without delays" or "never run out" do not negate the skill.
REQUIREMENT_NEGATIONS = [["no", "hands"], ["nog", "geen"], ["not", "necessary"], ["not", "required"], ["no", "prior"],
                         ["don", "t", "need"], ["geen", "vereiste"], ["niet", "nodig"], ["hoeft"]]

YOU = {"you", "your", "je", "jij", "jouw", "u"}
WE = {"we", "our", "us", "wij", "onze", "ons"}
# "We expect experience with X" talks about the candidate even though it says "we".
ASKS = {"expect", "looking", "need", "require", "seek", "verwachten", "zoeken", "vragen"}

# Without headings, these words mark a sentence as part of the offer ("Training in lean").
OFFER_CUES = [["training"], ["course"], ["opleiding"], ["opleidingsbudget"], ["salary"], ["loon"], ["meal", "vouchers"],
              ["maaltijdcheques"], ["company", "car"], ["bedrijfswagen"], ["days", "off"], ["verlofdagen"], ["lessons"], ["lessen"]]
# Contact and application lines carry names and no skills; they get no semantic matching.
CONTACT_CUES = [["contact"], ["questions"], ["apply"], ["vragen"], ["solliciteer"], ["neem", "contact"]]

STOPWORDS = set("""
a an the and or of to in on at for with by from as is are be will you your we our us it its this that these those
who what which can our than then into across per every each all any our more most very also not no
de het een en of te in op aan voor met door van als is zijn wordt je jij jouw we wij onze ons dit dat deze die
wie wat welke kan dan naar over per elke elk alle meer zeer ook niet geen er
""".split())


def fold(text: str) -> str:
    """Lowercase and strip accents, one character in, one character out, so offsets survive."""
    out = []
    for ch in text:
        d = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)).lower()
        out.append(d[:1] if d else " ")
    return "".join(out)


@dataclass
class Token:
    text: str
    start: int
    end: int


@dataclass
class Sentence:
    index: int
    start: int
    end: int
    text: str
    tokens: list[Token]
    section: str
    heading: bool = False
    voice: str = "neutral"
    preferred_cue: bool = False
    offer_cue: bool = False
    contact: bool = False
    aspiration: bool = False
    requirement_negated: bool = False
    meta: dict = field(default_factory=dict)


def tokenize(folded: str, offset: int = 0) -> list[Token]:
    return [Token(m.group(), m.start() + offset, m.end() + offset) for m in TOKEN.finditer(folded)]


def contains(words: list[str], seq: list[str]) -> bool:
    n = len(seq)
    return any(words[i:i + n] == seq for i in range(len(words) - n + 1))


def section_of(words: list[str], table=None) -> str | None:
    for section, patterns in table or SECTION_KEYWORDS:
        if any(contains(words, p) for p in patterns):
            return section
    return None


def is_heading(line: str, words: list[str], table=None) -> str | None:
    stripped = line.strip()
    if not words or len(words) > 6 or stripped[-1:] in ".!?":
        return None
    return section_of(words, table)


def split_line(line: str, start: int) -> list[tuple[int, int]]:
    """Sentence spans inside one line (absolute offsets), trimmed of whitespace and bullets."""
    spans, s = [], 0
    for m in SENTENCE_END.finditer(line):
        spans.append((s, m.end()))
        s = m.end()
    spans.append((s, len(line)))
    out = []
    for a, b in spans:
        while a < b and (line[a].isspace() or line[a] in "-•*·"):
            a += 1
        while b > a and line[b - 1].isspace():
            b -= 1
        if b > a:
            out.append((start + a, start + b))
    return out


def segment(text: str, kind: str = "jd") -> tuple[list[Sentence], bool]:
    """Split a job description (or a CV, kind="cv") into sentences with a section label each.

    Returns the sentences and whether the text had any recognised heading.
    """
    cv = kind == "cv"
    table = CV_SECTION_KEYWORDS if cv else None
    folded = fold(text)
    sentences: list[Sentence] = []
    section = "header" if cv else "unknown"
    seen_heading = False
    pos = 0
    first_line = True
    for line in text.split("\n"):
        start = pos
        pos += len(line) + 1
        words = [t.text for t in tokenize(folded[start:start + len(line)])]
        if not words:
            continue
        heading = is_heading(line, words, table)
        if heading:
            section, seen_heading = heading, True
            a = start + (len(line) - len(line.lstrip()))
            sentences.append(Sentence(len(sentences), a, start + len(line.rstrip()), line.strip(),
                                      tokenize(folded[start:start + len(line)], start), heading, heading=True))
            first_line = False
            continue
        if first_line and not cv and len(words) <= 8 and line.strip()[-1:] not in ".!?":
            sentences.append(Sentence(len(sentences), start, start + len(line.rstrip()), line.strip(),
                                      tokenize(folded[start:start + len(line)], start), "title"))
            first_line = False
            continue
        first_line = False
        for a, b in split_line(line, start):
            toks = tokenize(folded[a:b], a)
            if not toks:
                continue
            words_s = [t.text for t in toks]
            sentences.append(Sentence(
                len(sentences), a, b, text[a:b], toks, section,
                voice="neutral" if cv else voice(words_s),
                preferred_cue=any(contains(words_s, c) for c in PREFERRED_CUES),
                offer_cue=any(contains(words_s, c) for c in OFFER_CUES),
                contact=any(contains(words_s, c) for c in CONTACT_CUES),
                aspiration=cv and any(contains(words_s, c) for c in ASPIRATION_CUES),
                requirement_negated=any(contains(words_s, c) for c in REQUIREMENT_NEGATIONS),
            ))
    return sentences, seen_heading


def voice(words: list[str]) -> str:
    w = set(words)
    if w & YOU or w & ASKS:
        return "you"
    if w & WE:
        return "we"
    return "neutral"


def negated_at(tokens: list[Token], first: int, last: int) -> bool:
    """Is the alias occupying tokens[first..last] negated by a nearby cue?"""
    before = tokens[max(0, first - NEG_BEFORE):first]
    after = tokens[last + 1:last + 1 + NEG_AFTER]
    return any(t.text in NEGATION_CUES for t in before) or any(t.text in NEGATION_AFTER_CUES for t in after)


def detect_language(text: str) -> str:
    words = [t.text for t in tokenize(fold(text))]
    nl = sum(w in {"je", "jij", "jouw", "het", "een", "van", "met", "wij", "onze", "ervaring", "kennis", "en"} for w in words)
    en = sum(w in {"you", "your", "the", "a", "of", "with", "we", "our", "experience", "knowledge", "and"} for w in words)
    return "nl" if nl > en else "en"
