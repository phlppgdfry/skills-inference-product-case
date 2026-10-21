"""From a job description to a skill profile.

    text ─► sentences + sections ─► candidates (alias matches + semantic matches)
         ─► features per skill ─► calibrated score ─► suggested / needs review / dropped
         ─► (optional) LLM verifier on the review band ─► profile with evidence

Configurations, so the evals can show what each step buys (docs/01-prototype/spike-report.md):
    A  spike: the skill's label anywhere in the text (the day-one prototype)
    B  alias matcher + hand rules (sections, negation, ambiguous aliases)
    C  B + semantic matches above a fixed similarity
    D  all candidates, learned calibrated scorer, review band     (production default)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from .embed import Embedder, HashingEmbedder
from .inclusive import check as check_language
from .scorer import FEATURES, LogisticModel
from .taxonomy import Taxonomy
from .text import GOOD_SECTIONS, Sentence, detect_language, fold, negated_at, segment

SEMANTIC_TOP_K = 2


@dataclass
class Evidence:
    kind: str          # "exact" | "semantic"
    start: int
    end: int
    sentence: int
    section: str       # effective section (a "nice to have" cue turns a sentence into "pref")
    negated: bool
    ambiguous: bool = False
    similarity: float = 0.0
    margin: float = 0.0
    voice: str = "neutral"
    alias: str = ""


@dataclass
class Candidate:
    skill_id: str
    evidence: list[Evidence] = field(default_factory=list)
    features: list[float] = field(default_factory=list)
    score: float = 0.0


@dataclass
class Analysis:
    text: str
    sentences: list[Sentence]
    excluded: list[int]
    has_headings: bool
    candidates: dict[str, Candidate]
    language: str


def effective_section(s: Sentence) -> str:
    """The section a sentence counts for. Headings decide; without a heading, cues do:
    "is a plus" reads as nice-to-have, "training in" as the offer, and a "we/our" sentence
    that asks nothing of the candidate as company talk."""
    if s.preferred_cue and s.section in ("unknown", "req", "resp"):
        return "pref"
    if s.section == "unknown":
        if s.offer_cue:
            return "offer"
        if s.voice == "we":
            return "about"
    return s.section


def feature_vector(c: Candidate, has_headings: bool) -> list[float]:
    live = [e for e in c.evidence if not e.negated]
    exact = [e for e in live if e.kind == "exact"]
    sem = [e for e in live if e.kind == "semantic"]
    good = lambda e: e.section in GOOD_SECTIONS  # noqa: E731
    exact_good = any(good(e) for e in exact)
    sem_good = [e for e in sem if good(e)]
    best_sem = max(sem_good, key=lambda e: e.similarity, default=None)
    ranked = sorted(live, key=lambda e: (e.kind != "exact", not good(e), -e.similarity))
    best = ranked[0] if ranked else None
    f = {
        "exact_good": 1.0 if exact_good else 0.0,
        "exact_bad": 1.0 if exact and not exact_good else 0.0,
        "negated": 1.0 if not live and any(e.negated for e in c.evidence) else 0.0,
        "sem_good": best_sem.similarity if best_sem else 0.0,
        "sem_margin": best_sem.margin if best_sem else 0.0,
        "ambiguous_only": 1.0 if exact and all(e.ambiguous for e in exact) else 0.0,
        "mentions": math.log1p(len(live)),
        "in_pref": 1.0 if best and best.section == "pref" else 0.0,
        "in_title": 1.0 if any(e.section == "title" for e in exact) else 0.0,
        "company_voice": 1.0 if live and all(e.voice == "we" for e in live) else 0.0,
        "no_headings": 0.0 if has_headings else 1.0,
    }
    return [round(f[name], 6) for name in FEATURES]


def importance(c: Candidate) -> str:
    live = [e for e in c.evidence if not e.negated and e.section in GOOD_SECTIONS]
    return "preferred" if live and all(e.section == "pref" for e in live) else "required"


class Pipeline:
    def __init__(self, taxonomy: Taxonomy, embedder: Embedder | None = None, model: LogisticModel | None = None,
                 config: str = "D", semantic_threshold: float = 0.3, verifier=None, min_similarity: float | None = None):
        self.taxonomy = taxonomy
        self.embedder = embedder or HashingEmbedder()
        self.skill_ids = [s["id"] for s in taxonomy.skills]
        texts = [taxonomy.profile_text(sid) for sid in self.skill_ids]
        self.embedder.fit(texts)
        self.skill_vectors = self.embedder.encode(texts)
        self.model = model
        self.config = config
        self.semantic_threshold = semantic_threshold
        self.min_similarity = min_similarity if min_similarity is not None else getattr(self.embedder, "min_similarity", 0.05)
        self.verifier = verifier
        if config == "D" and model is None:
            raise ValueError("configuration D needs a trained model (python -m skilldraft train)")

    # ---------------------------------------------------------------- candidates
    def analyse(self, text: str) -> Analysis:
        sentences, has_headings = segment(text)
        cands: dict[str, Candidate] = {}
        # A sentence about who the candidate is (age, gender, origin) is never evidence for
        # what they can do. Without this rule, "Je komt terecht in een jong en dynamisch team"
        # was a weak semantic match for shift leadership and moved its score.
        flagged = [(f["start"], f["end"]) for f in check_language(text)]
        body = [s for s in sentences if not s.heading and not any(a < s.end and s.start < b for a, b in flagged)]
        vectors = self.embedder.encode([s.text for s in body]) if body else []
        for s, vec in zip(body, vectors):
            section = effective_section(s)
            for hit in self.taxonomy.match(s.tokens):
                cands.setdefault(hit.skill_id, Candidate(hit.skill_id)).evidence.append(Evidence(
                    "exact", hit.start, hit.end, s.index, section, negated_at(s.tokens, hit.first, hit.last),
                    ambiguous=hit.ambiguous, voice=s.voice, alias=hit.alias))
            # Semantic matching only where the text talks about the job. Company talk, the offer
            # and contact lines can hold exact mentions (which the scorer learns to discount), but
            # a vague similarity there is noise, and noise that moved other skills' scores when a
            # sentence like "Join our young and dynamic team" was added (docs/04-quality/fairness.md).
            if s.section == "title" or s.contact or section not in GOOD_SECTIONS:
                continue
            sims = sorted(((self.embedder.similarity(vec, sv), sid) for sid, sv in zip(self.skill_ids, self.skill_vectors)), reverse=True)
            for rank, (sim, sid) in enumerate(sims[:SEMANTIC_TOP_K]):
                if sim < self.min_similarity:
                    break
                other = sims[1][0] if rank == 0 else sims[0][0]
                cands.setdefault(sid, Candidate(sid)).evidence.append(Evidence(
                    "semantic", s.start, s.end, s.index, section, s.requirement_negated,
                    similarity=round(sim, 6), margin=round(sim - other, 6), voice=s.voice))
        for c in cands.values():
            c.features = feature_vector(c, has_headings)
        excluded = [s.index for s in sentences if not s.heading and s not in body]
        return Analysis(text, sentences, excluded, has_headings, cands, detect_language(text))

    # ---------------------------------------------------------------- decisions
    def decide(self, c: Candidate) -> str | None:
        """'suggested', 'needs_review' or None (dropped)."""
        f = dict(zip(FEATURES, c.features))
        if self.config == "B":
            ok = f["exact_good"] and not f["ambiguous_only"] and not f["company_voice"]
            return "suggested" if ok else None
        if self.config == "C":
            ok = (f["exact_good"] and not f["ambiguous_only"] and not f["company_voice"]) or f["sem_good"] >= self.semantic_threshold
            return "suggested" if ok else None
        c.score = self.model.predict(c.features)
        if c.score >= self.model.accept_at:
            return "suggested"
        if c.score >= self.model.review_at:
            return "needs_review"
        return None

    def infer(self, text: str) -> dict:
        t0 = time.perf_counter()
        if self.config == "A":
            return self._spike(text, t0)
        a = self.analyse(text)
        skills = []
        for c in a.candidates.values():
            status = self.decide(c)
            if status:
                skills.append(self._skill(a, c, status))
        if self.verifier is not None:
            skills = self._verify(a, skills)
        skills.sort(key=lambda s: (s["status"] != "suggested", s["importance"] != "required", -s["confidence"], s["id"]))
        covered = {e["sentence"] for s in skills for e in s["evidence"]}
        uncovered = [{"start": s.start, "end": s.end, "text": s.text} for s in a.sentences
                     if not s.heading and s.section in ("req", "resp") and s.index not in covered and not s.requirement_negated]
        return {
            "skills": skills,
            "uncovered_requirements": uncovered,
            "language_flags": check_language(text),
            "meta": self._meta(a.language, t0),
        }

    def _skill(self, a: Analysis, c: Candidate, status: str) -> dict:
        s = self.taxonomy.by_id[c.skill_id]
        live = sorted((e for e in c.evidence if not e.negated),
                      key=lambda e: (e.kind != "exact", e.section not in GOOD_SECTIONS, -e.similarity, e.start))
        conf = c.score if self.config == "D" else 1.0
        return {
            "id": c.skill_id, "label": s["label"], "status": status, "importance": importance(c),
            "confidence": round(conf, 3),
            "evidence": [{"start": e.start, "end": e.end, "quote": a.text[e.start:e.end], "kind": e.kind,
                          "section": e.section, "sentence": e.sentence} for e in live[:3]],
        }

    def _verify(self, a: Analysis, skills: list[dict]) -> list[dict]:
        review = [s for s in skills if s["status"] == "needs_review"]
        if not review:
            return skills
        decisions = self.verifier.verify(a.text, [
            {"id": s["id"], "label": s["label"], "definition": self.taxonomy.by_id[s["id"]]["definition"]["en"],
             "evidence": [e["quote"] for e in s["evidence"]]} for s in review])
        out = []
        for s in skills:
            d = decisions.get(s["id"]) if s["status"] == "needs_review" else None
            if d is None:
                out.append(s)
            elif d["present"]:
                out.append({**s, "status": "suggested", "verified_by": d["model"], "verifier_quote": d["quote"]})
            # present == False: the verifier found no support in the text; drop the skill
        return out

    def _spike(self, text: str, t0: float) -> dict:
        folded = fold(text)
        skills = []
        for s in self.taxonomy.skills:
            label = fold(s["label"])
            i = folded.find(label)
            while i >= 0:
                before = folded[i - 1] if i > 0 else " "
                after = folded[i + len(label)] if i + len(label) < len(folded) else " "
                if not before.isalnum() and not after.isalnum():
                    skills.append({"id": s["id"], "label": s["label"], "status": "suggested", "importance": "required",
                                   "confidence": 1.0, "evidence": [{"start": i, "end": i + len(label), "quote": text[i:i + len(label)],
                                                                    "kind": "exact", "section": "unknown", "sentence": -1}]})
                    break
                i = folded.find(label, i + 1)
        return {"skills": skills, "uncovered_requirements": [], "language_flags": [], "meta": self._meta(detect_language(text), t0)}

    def _meta(self, language: str, t0: float) -> dict:
        return {
            "config": self.config, "taxonomy_version": self.taxonomy.version, "embedder": self.embedder.name,
            "model_version": self.model.version if self.model and self.config == "D" else None,
            "language": language, "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
