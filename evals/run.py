"""Offline evaluation and release gate.

    python -m evals.run                    # all suites, hashing embedder, prints a summary
    python -m evals.run --gate             # exit 1 if any threshold in evals/thresholds.json fails
    python -m evals.run --embedder hf      # same suites with the Transformers embedder

Every suite answers one product question (docs/04-quality/eval-plan.md):
    extraction   Which configuration finds the right skills? (A spike … D production)
    surfaces     Does it find skills that are only described, never named?
    distractors  Does it suggest skills from "about us", "what we offer" or "no X needed"?
    calibration  Can a reviewer trust the confidence? (ECE, reliability table)
    fairness     Do gender, name or age wording change the profile? Are EN and NL equally good?
    language     How many coded phrases does the checker catch, and how many false alarms?
    match        How much does extraction quality move the internal-mobility ranking?
    latency      Fast enough for an interactive review screen? (not written to the report)

All numbers are on the test split, which training and threshold tuning never see.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skilldraft import make_embedder  # noqa: E402
from skilldraft.match import ndcg_at_k, rank  # noqa: E402
from skilldraft.pipeline import Pipeline  # noqa: E402
from skilldraft.scorer import LogisticModel  # noqa: E402
from skilldraft.taxonomy import Taxonomy  # noqa: E402
from skilldraft.train import examples, load_jds, model_path  # noqa: E402

REPORTS = ROOT / "evals" / "reports"
THRESHOLDS = ROOT / "evals" / "thresholds.json"


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4), "tp": tp, "fp": fp, "fn": fn}


def tune_semantic_threshold(pipeline: Pipeline) -> float:
    """Config C gets a fair fixed threshold: the one with the best F1 on the dev split."""
    best = (0.0, 0.3)
    dev = load_jds("dev")
    for t in [x / 100 for x in range(10, 61, 2)]:
        pipeline.semantic_threshold = t
        tp = fp = fn = 0
        for jd in dev:
            gold = {g["id"] for g in jd["gold"]["skills"]}
            got = {s["id"] for s in pipeline.infer(jd["text"])["skills"]}
            tp, fp, fn = tp + len(got & gold), fp + len(got - gold), fn + len(gold - got)
        f = prf(tp, fp, fn)["f1"]
        if f > best[0]:
            best = (f, t)
    pipeline.semantic_threshold = best[1]
    return best[1]


def extraction(pipe: Pipeline, test: list[dict]) -> dict:
    tp = fp = fn = 0
    review_n = review_tp = 0
    by_lang: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    by_surface: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    distract: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    imp_ok = imp_n = ev_ok = ev_n = 0
    missed_surfaced = missed = 0
    profiles = {}
    for jd in test:
        out = pipe.infer(jd["text"])
        profiles[jd["id"]] = out
        gold = {g["id"]: g for g in jd["gold"]["skills"]}
        sugg = {s["id"]: s for s in out["skills"] if s["status"] == "suggested"}
        rev = {s["id"]: s for s in out["skills"] if s["status"] == "needs_review"}
        t, f, n = len(sugg.keys() & gold.keys()), len(sugg.keys() - gold.keys()), len(gold.keys() - sugg.keys())
        tp, fp, fn = tp + t, fp + f, fn + n
        lang = by_lang[jd["lang"]]
        lang[0], lang[1], lang[2] = lang[0] + t, lang[1] + f, lang[2] + n
        review_n += len(rev)
        review_tp += len(rev.keys() & gold.keys())
        for sid, g in gold.items():
            row = by_surface[g["surface"]]
            row[0] += 1
            row[1] += sid in sugg
            if sid in sugg:
                imp_n += 1
                imp_ok += sugg[sid]["importance"] == g["importance"]
                ev_n += 1
                ev_ok += any(overlaps((e["start"], e["end"]), tuple(span)) for e in sugg[sid]["evidence"] for span in g["spans"])
            elif sid not in rev:
                missed += 1
                missed_surfaced += any(overlaps((u["start"], u["end"]), tuple(span)) for u in out["uncovered_requirements"] for span in g["spans"])
        for d in jd["gold"]["distractors"]:
            row = distract[d["kind"]]
            row[0] += 1
            row[1] += d["id"] in sugg
    gold_total = tp + fn
    res = {
        "suggested": prf(tp, fp, fn),
        "by_language": {k: prf(*v) for k, v in sorted(by_lang.items())},
        "recall_by_surface": {k: round(v[1] / v[0], 4) for k, v in sorted(by_surface.items())},
        "surface_counts": {k: v[0] for k, v in sorted(by_surface.items())},
        "distractor_suggested_rate": {k: round(v[1] / v[0], 4) for k, v in sorted(distract.items())},
        "distractor_counts": {k: v[0] for k, v in sorted(distract.items())},
        "importance_accuracy": round(imp_ok / imp_n, 4) if imp_n else 0.0,
        "evidence_accuracy": round(ev_ok / ev_n, 4) if ev_n else 0.0,
        "review": {
            "items": review_n, "per_description": round(review_n / len(test), 2),
            "precision_in_band": round(review_tp / review_n, 4) if review_n else 0.0,
            "recall_with_review": round((tp + review_tp) / gold_total, 4) if gold_total else 0.0,
        },
        "missed_but_flagged_uncovered": round(missed_surfaced / missed, 4) if missed else 0.0,
        "missed": missed,
    }
    res["language_f1_gap"] = round(abs(res["by_language"]["en"]["f1"] - res["by_language"]["nl"]["f1"]), 4)
    return res, profiles


def calibration(pipe: Pipeline, test: list[dict], bins: int = 10) -> dict:
    X, y, _ = examples(pipe, test)
    probs = [pipe.model.predict(x) for x in X]
    table = []
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if not idx:
            continue
        conf = sum(probs[i] for i in idx) / len(idx)
        acc = sum(y[i] for i in idx) / len(idx)
        ece += len(idx) / len(probs) * abs(conf - acc)
        table.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(idx), "mean_confidence": round(conf, 4), "observed": round(acc, 4)})
    brier = sum((p - t) ** 2 for p, t in zip(probs, y)) / len(probs)
    return {"candidates": len(probs), "ece": round(ece, 4), "brier": round(brier, 4), "reliability": table}


def signature(out: dict) -> dict:
    return {s["id"]: (s["status"], s["importance"], s["confidence"]) for s in out["skills"]}


def fairness(pipe: Pipeline, test: list[dict], split: str = "test") -> dict:
    base = {jd["id"]: signature(pipe.infer(jd["text"])) for jd in test}
    rows = [json.loads(line) for line in (ROOT / "data" / "counterfactuals.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r["split"] == split]
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    changed = []
    for cf in rows:
        sig = signature(pipe.infer(cf["text"]))
        same = sig == base[cf["base"]]
        per[cf["kind"]][0] += 1
        per[cf["kind"]][1] += same
        if not same:
            diff = sorted(set(sig.items()) ^ set(base[cf["base"]].items()))
            changed.append({"id": cf["id"], "diff": [list(d) for d in diff][:4]})
    total = sum(v[0] for v in per.values())
    return {
        "variants": total,
        "invariance": round(sum(v[1] for v in per.values()) / total, 4),
        "invariance_by_kind": {k: round(v[1] / v[0], 4) for k, v in sorted(per.items())},
        "changed_examples": changed[:5],
    }


def language_checker(pipe: Pipeline, jds: list[dict]) -> dict:
    found = found_lex = total = total_lex = false_alarms = 0
    for jd in jds:
        flags = pipe.infer(jd["text"])["language_flags"]
        gold = jd["gold"]["flags"]
        for g in gold:
            hit = any(overlaps((f["start"], f["end"]), tuple(g["span"])) for f in flags)
            total += 1
            found += hit
            if g["in_lexicon"]:
                total_lex += 1
                found_lex += hit
        false_alarms += sum(not any(overlaps((f["start"], f["end"]), tuple(g["span"])) for g in gold) for f in flags)
    return {"descriptions": len(jds), "coded_phrases": total, "recall": round(found / total, 4) if total else 0.0,
            "recall_known_phrases": round(found_lex / total_lex, 4) if total_lex else 0.0,
            "missed": total - found, "false_alarms": false_alarms}


def match_quality(profiles: dict[str, dict], test: list[dict], people: list[dict], k: int = 5) -> float:
    scores = []
    for jd in test:
        ideal = rank(jd["gold"]["skills"], people, use_confidence=False)
        got = rank(profiles[jd["id"]]["skills"], people)
        relevance = {r["person_id"]: r["score"] for r in ideal}
        scores.append(ndcg_at_k([r["person_id"] for r in got], relevance, k))
    return round(sum(scores) / len(scores), 4)


def latency(pipe: Pipeline, test: list[dict]) -> dict:
    times = []
    for jd in test:
        t0 = time.perf_counter()
        pipe.infer(jd["text"])
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return {"p50_ms": round(statistics.median(times), 2), "p95_ms": round(times[int(0.95 * (len(times) - 1))], 2)}


SWEEP_GRID = {"hashing-v1": [0.05, 0.06, 0.08, 0.10, 0.12, 0.14], "hf": [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]}


def sweep(embedder_name: str = "hashing") -> dict:
    """Pick the semantic floor on the dev split: the best F1 among the values that keep
    every counterfactual profile unchanged. Each value retrains the scorer."""
    from skilldraft.train import train

    tax, emb, dev = Taxonomy.load(), make_embedder(embedder_name), load_jds("dev")
    grid = SWEEP_GRID["hf" if emb.name.startswith("hf-") else emb.name]
    rows = []
    for ms in grid:
        model = train(Pipeline(tax, emb, None, "C", min_similarity=ms))
        pipe = Pipeline(tax, emb, model, "D", min_similarity=ms)
        ex, _ = extraction(pipe, dev)
        rows.append({"min_similarity": ms, "f1": ex["suggested"]["f1"], "precision": ex["suggested"]["precision"],
                     "recall": ex["suggested"]["recall"], "recall_with_review": ex["review"]["recall_with_review"],
                     "review_per_description": ex["review"]["per_description"],
                     "paraphrase_recall": ex["recall_by_surface"].get("paraphrase", 0.0),
                     "invariance": fairness(pipe, dev, "dev")["invariance"]})
    ok = [r for r in rows if r["invariance"] == 1.0] or rows
    chosen = max(ok, key=lambda r: (r["f1"], -r["min_similarity"]))["min_similarity"]
    return {"embedder": emb.name, "split": "dev", "rule": "best F1 with invariance 1.0", "chosen": chosen, "rows": rows}


def build_report(embedder_name: str = "hashing", with_latency: bool = False) -> dict:
    tax = Taxonomy.load()
    emb = make_embedder(embedder_name)
    model = LogisticModel.load(model_path(emb.name))
    test = load_jds("test")
    people = [json.loads(line) for line in (ROOT / "data" / "people.jsonl").read_text(encoding="utf-8").splitlines()]
    pipes = {c: Pipeline(tax, emb if c != "A" else make_embedder("hashing"), model if c == "D" else None, config=c) for c in "ABCD"}
    sem_t = tune_semantic_threshold(pipes["C"])
    report: dict = {"embedder": emb.name, "model_version": model.version, "taxonomy_version": tax.version,
                    "test_descriptions": len(test), "gold_skills": sum(len(j["gold"]["skills"]) for j in test),
                    "thresholds": {"accept_at": model.accept_at, "review_at": model.review_at, "config_C_similarity": sem_t},
                    "configs": {}}
    profiles = {}
    for c, pipe in pipes.items():
        report["configs"][c], profiles[c] = extraction(pipe, test)
        report["configs"][c]["match_ndcg_at_5"] = match_quality(profiles[c], test, people)
    report["calibration"] = calibration(pipes["D"], test)
    report["fairness"] = fairness(pipes["D"], test)
    report["language"] = language_checker(pipes["D"], load_jds())
    report["weights"] = dict(zip(model.features, model.weights)) | {"bias": model.bias}
    if with_latency:
        report["latency"] = latency(pipes["D"], test)
    return report


def gate(report: dict) -> list[str]:
    th = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    D = report["configs"]["D"]
    actual = {
        "precision_suggested": D["suggested"]["precision"],
        "recall_with_review": D["review"]["recall_with_review"],
        "evidence_accuracy": D["evidence_accuracy"],
        "importance_accuracy": D["importance_accuracy"],
        "max_distractor_rate": max(D["distractor_suggested_rate"].values()),
        "ece": report["calibration"]["ece"],
        "invariance": report["fairness"]["invariance"],
        "language_f1_gap": D["language_f1_gap"],
        "checker_recall_known_phrases": report["language"]["recall_known_phrases"],
        "checker_false_alarms": report["language"]["false_alarms"],
        "p95_ms": report.get("latency", {}).get("p95_ms", 0.0),
    }
    failures = []
    for key, rule in th.items():
        if key.startswith("_"):
            continue
        v = actual[key]
        if ("min" in rule and v < rule["min"]) or ("max" in rule and v > rule["max"]):
            failures.append(f"{key} = {v} (rule {rule})")
    return failures


def summary(r: dict) -> str:
    lines = [f"embedder {r['embedder']} · model {r['model_version']} · {r['test_descriptions']} test descriptions, {r['gold_skills']} gold skills"]
    lines.append("config  precision  recall  f1     paraphrase-recall  about/offer/negated suggested   nDCG@5")
    for c, v in r["configs"].items():
        s = v["suggested"]
        dr = v["distractor_suggested_rate"]
        lines.append(f"  {c}     {s['precision']:.3f}      {s['recall']:.3f}   {s['f1']:.3f}  {v['recall_by_surface'].get('paraphrase', 0):.3f}              "
                     f"{dr.get('about', 0):.2f} / {dr.get('offer', 0):.2f} / {dr.get('negated', 0):.2f}                {v['match_ndcg_at_5']:.3f}")
    D = r["configs"]["D"]
    lines.append(f"D review band: {D['review']['per_description']} per description, recall with review {D['review']['recall_with_review']:.3f}")
    lines.append(f"calibration ECE {r['calibration']['ece']:.3f} · invariance {r['fairness']['invariance']:.3f} · "
                 f"EN/NL F1 gap {D['language_f1_gap']:.3f} · checker recall {r['language']['recall']:.3f} ({r['language']['false_alarms']} false alarms)")
    if "latency" in r:
        lines.append(f"latency p50 {r['latency']['p50_ms']} ms · p95 {r['latency']['p95_ms']} ms")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", default="hashing")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--write", action="store_true", help="write evals/reports/offline.<embedder>.json")
    ap.add_argument("--sweep", action="store_true", help="re-pick the semantic floor on dev and write evals/reports/sweep.<embedder>.json")
    args = ap.parse_args()
    if args.sweep:
        result = sweep(args.embedder)
        REPORTS.mkdir(parents=True, exist_ok=True)
        (REPORTS / f"sweep.{result['embedder']}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        for r in result["rows"]:
            print(r)
        print("chosen:", result["chosen"])
        return 0
    report = build_report(args.embedder, with_latency=True)
    print(summary(report))
    if args.write:
        REPORTS.mkdir(parents=True, exist_ok=True)
        stable = {k: v for k, v in report.items() if k != "latency"}
        (REPORTS / f"offline.{report['embedder']}.json").write_text(json.dumps(stable, indent=1) + "\n", encoding="utf-8")
    if args.gate:
        failures = gate(report)
        for f in failures:
            print("GATE FAIL:", f)
        print("gate: " + ("FAILED" if failures else "passed"))
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
