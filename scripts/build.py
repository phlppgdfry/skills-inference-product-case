"""One command keeps model, evals, docs and site consistent.

    python3 scripts/build.py           # regenerate everything
    python3 scripts/build.py --check   # CI: fail if anything is stale

Steps
1. model: retrain the scorer on the train split; it must equal models/scorer.hashing-v1.json
2. sweep: re-pick the semantic floor on dev; it must equal HashingEmbedder.min_similarity
3. evals: evals/reports/offline.hashing-v1.json (test split)
4. prompt lock: prompts/lock.json pins every prompt body to its version
5. site data: site/data/*.json (taxonomy, model, samples, eval tables, parity fixtures)
6. numbers: every <!--n:key-->value<!--/n--> marker in README, docs and site is rewritten
   from the reports, so no page can quote a number the code does not produce.

The Transformers report (evals/reports/offline.hf-*.json) comes from the ml CI job or from
`python -m evals.run --embedder hf --write`; this script reads it but does not rebuild it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.run import build_report, sweep  # noqa: E402
from skilldraft import default_pipeline  # noqa: E402
from skilldraft.embed import HashingEmbedder  # noqa: E402
from skilldraft.llm import PROMPT_PATH, PROMPT_VERSION  # noqa: E402
from skilldraft.pipeline import Pipeline  # noqa: E402
from skilldraft.taxonomy import Taxonomy  # noqa: E402
from skilldraft.text import detect_language  # noqa: E402
from skilldraft.train import load_jds, model_path, train  # noqa: E402

MARKER = re.compile(r"<!--n:([\w.\-]+)-->(.*?)<!--/n-->", re.S)
REPORTS = ROOT / "evals" / "reports"
SAMPLES = ["JD-267", "JD-203", "JD-251", "JD-236", "JD-219", "JD-207"]


def pct(x: float) -> str:
    v = x * 100
    return f"{v:.0f}%" if abs(v - round(v)) < 0.05 else f"{v:.1f}%"


def dec(x: float, n: int = 3) -> str:
    return f"{x:.{n}f}"


def numbers(r: dict, sw: dict, hf: dict | None, hf_sweep: dict | None) -> dict[str, str]:
    n: dict[str, str] = {
        "test.descriptions": str(r["test_descriptions"]), "test.gold": str(r["gold_skills"]),
        "skills": str(len(Taxonomy.load().skills)), "jds": str(len(load_jds())),
        "accept_at": dec(r["thresholds"]["accept_at"]), "review_at": dec(r["thresholds"]["review_at"]),
        "c_threshold": dec(r["thresholds"]["config_C_similarity"], 2), "model_version": r["model_version"],
    }
    for c, v in r["configs"].items():
        s = v["suggested"]
        n |= {f"{c}.precision": dec(s["precision"]), f"{c}.recall": dec(s["recall"]), f"{c}.f1": dec(s["f1"]),
              f"{c}.fp": str(s["fp"]), f"{c}.fn": str(s["fn"]),
              f"{c}.paraphrase_recall": pct(v["recall_by_surface"].get("paraphrase", 0.0)),
              f"{c}.alias_recall": pct(v["recall_by_surface"].get("alias", 0.0)),
              f"{c}.label_recall": pct(v["recall_by_surface"].get("label", 0.0)),
              f"{c}.ndcg": dec(v["match_ndcg_at_5"]), f"{c}.evidence": pct(v["evidence_accuracy"]),
              f"{c}.importance": pct(v["importance_accuracy"]), f"{c}.lang_gap": dec(v["language_f1_gap"]),
              f"{c}.f1_en": dec(v["by_language"]["en"]["f1"]), f"{c}.f1_nl": dec(v["by_language"]["nl"]["f1"]),
              f"{c}.review_per_jd": f"{v['review']['per_description']:.1f}",
              f"{c}.recall_with_review": dec(v["review"]["recall_with_review"]),
              f"{c}.review_precision": pct(v["review"]["precision_in_band"]),
              f"{c}.missed": str(v["missed"]), f"{c}.missed_flagged": pct(v["missed_but_flagged_uncovered"])}
        for kind, rate in v["distractor_suggested_rate"].items():
            n[f"{c}.distractor.{kind}"] = pct(rate)
    for kind, count in r["configs"]["D"]["surface_counts"].items():
        n[f"surface.{kind}"] = str(count)
    for kind, count in r["configs"]["D"]["distractor_counts"].items():
        n[f"distractors.{kind}"] = str(count)
    cal, fa, lg = r["calibration"], r["fairness"], r["language"]
    n |= {"ece": dec(cal["ece"]), "brier": dec(cal["brier"]), "candidates": str(cal["candidates"]),
          "invariance": pct(fa["invariance"]), "variants": str(fa["variants"]),
          "checker.recall": pct(lg["recall"]), "checker.recall_known": pct(lg["recall_known_phrases"]),
          "checker.phrases": str(lg["coded_phrases"]), "checker.missed": str(lg["missed"]), "checker.false_alarms": str(lg["false_alarms"])}
    for k, v in fa["invariance_by_kind"].items():
        n[f"invariance.{k}"] = pct(v)
    for name, w in r["weights"].items():
        n[f"w.{name}"] = f"{w:+.2f}"
    n["sweep.chosen"] = dec(sw["chosen"], 2)
    for row in sw["rows"]:
        k = f"sweep.{row['min_similarity']:.2f}"
        n |= {f"{k}.f1": dec(row["f1"]), f"{k}.rwr": dec(row["recall_with_review"]), f"{k}.review": f"{row['review_per_description']:.1f}",
              f"{k}.para": pct(row["paraphrase_recall"])}
    if hf:
        D, C = hf["configs"]["D"], hf["configs"]["C"]
        n |= {"hf.name": hf["embedder"].removeprefix("hf-"), "hf.D.f1": dec(D["suggested"]["f1"]), "hf.D.precision": dec(D["suggested"]["precision"]),
              "hf.D.recall": dec(D["suggested"]["recall"]), "hf.D.paraphrase_recall": pct(D["recall_by_surface"]["paraphrase"]),
              "hf.C.f1": dec(C["suggested"]["f1"]), "hf.D.lang_gap": dec(D["language_f1_gap"]), "hf.D.f1_nl": dec(D["by_language"]["nl"]["f1"]),
              "hf.D.f1_en": dec(D["by_language"]["en"]["f1"]), "hf.ece": dec(hf["calibration"]["ece"]),
              "hf.invariance": pct(hf["fairness"]["invariance"]), "hf.D.review_per_jd": f"{D['review']['per_description']:.1f}"}
    if hf_sweep:
        n["hf.sweep.chosen"] = dec(hf_sweep["chosen"], 2)
    return n


def site_data(r: dict, sw: dict, hf: dict | None) -> dict[str, str]:
    pipe = default_pipeline()
    model = pipe.model.to_json() | {"min_similarity": HashingEmbedder.min_similarity}
    jds = {j["id"]: j for j in load_jds()}
    samples = [{"id": f.stem, "title": f.read_text(encoding="utf-8").split("\n", 1)[0], "lang": detect_language(f.read_text(encoding="utf-8")),
                "text": f.read_text(encoding="utf-8").strip(), "gold": None} for f in sorted((ROOT / "data" / "samples").glob("*.txt"))]
    samples += [{"id": i, "title": jds[i]["title"], "lang": jds[i]["lang"], "text": jds[i]["text"],
                 "gold": [{"id": g["id"], "importance": g["importance"]} for g in jds[i]["gold"]["skills"]]} for i in SAMPLES]
    parity = []
    for j in load_jds("test"):
        out = pipe.infer(j["text"])
        parity.append({"id": j["id"], "skills": [[s["id"], s["status"], s["importance"], s["confidence"], s["evidence"][0]["start"]] for s in out["skills"]],
                       "uncovered": len(out["uncovered_requirements"]), "flags": len(out["language_flags"])})
    evals = {k: r[k] for k in ("embedder", "model_version", "test_descriptions", "gold_skills", "thresholds", "configs", "calibration", "fairness", "language")}
    evals["sweep"] = sw
    evals["hf"] = {k: hf[k] for k in ("embedder", "configs", "calibration", "fairness")} if hf else None
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n"  # noqa: E731
    return {
        "site/data/taxonomy.json": (ROOT / "data" / "taxonomy.json").read_text(encoding="utf-8"),
        "site/data/model.json": json.dumps(model, indent=1) + "\n",
        "site/data/samples.json": dump(samples),
        "site/data/evals.json": dump(evals),
        "tests/js/parity.json": dump(parity),
    }


def render(text: str, n: dict[str, str], where: str, missing: set[str]) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in n:
            missing.add(f"{where}: {key}")
            return m.group(0)
        return f"<!--n:{key}-->{n[key]}<!--/n-->"
    return MARKER.sub(sub, text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    outputs: dict[str, str] = {}
    problems: list[str] = []

    model = train(Pipeline(Taxonomy.load(), HashingEmbedder(), None, config="C"))
    outputs[str(model_path("hashing-v1").relative_to(ROOT))] = json.dumps(model.to_json(), indent=1) + "\n"
    sw = sweep("hashing")
    if sw["chosen"] != HashingEmbedder.min_similarity:
        problems.append(f"HashingEmbedder.min_similarity is {HashingEmbedder.min_similarity}, the dev sweep picks {sw['chosen']}")
    outputs["evals/reports/sweep.hashing-v1.json"] = json.dumps(sw, indent=1) + "\n"

    if not args.check:  # the report below must read the model we just trained
        model_path("hashing-v1").write_text(outputs[str(model_path("hashing-v1").relative_to(ROOT))], encoding="utf-8")
    report = build_report("hashing")
    outputs["evals/reports/offline.hashing-v1.json"] = json.dumps(report, indent=1) + "\n"

    body = PROMPT_PATH.read_text(encoding="utf-8")
    lock = {PROMPT_VERSION: {"file": PROMPT_PATH.name, "sha256": hashlib.sha256(body.encode()).hexdigest()}}
    outputs["prompts/lock.json"] = json.dumps(lock, indent=1) + "\n"

    hf_files = sorted(REPORTS.glob("offline.hf-*.json"))
    hf = json.loads(hf_files[0].read_text(encoding="utf-8")) if hf_files else None
    hfs_files = sorted(REPORTS.glob("sweep.hf-*.json"))
    hf_sweep = json.loads(hfs_files[0].read_text(encoding="utf-8")) if hfs_files else None
    outputs |= site_data(report, sw, hf)

    n = numbers(report, sw, hf, hf_sweep)
    missing: set[str] = set()
    docs = [p for p in (ROOT / "README.md", ROOT / "EVIDENCE.md") if p.exists()]
    docs += [*sorted((ROOT / "docs").rglob("*.md")), *sorted((ROOT / "site").rglob("*.html"))]
    for path in docs:
        rel = str(path.relative_to(ROOT))
        current = path.read_text(encoding="utf-8")
        outputs[rel] = render(current, n, rel, missing)
    problems += sorted(f"unknown number key {m}" for m in missing)

    stale = []
    for rel, content in outputs.items():
        path = ROOT / rel
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    for p in problems:
        print("✗", p)
    if stale:
        print("stale (run python3 scripts/build.py):\n  " + "\n  ".join(stale))
    if problems or stale:
        return 1
    print(f"{'up to date' if args.check else 'built'}: {len(outputs)} files, {len(n)} numbers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
