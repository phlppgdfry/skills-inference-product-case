"""Compare a freshly computed eval report with the committed one.

    python scripts/compare_report.py evals/reports/offline.hf-*.json /tmp/fresh.json --tolerance 0.01

Used by the CI job 'ml' for the Transformers run, whose floats can differ slightly across
platforms and library versions, so an exact file comparison would be too strict.
"""

from __future__ import annotations

import argparse
import json
import sys


def headline(r: dict) -> dict[str, float]:
    D = r["configs"]["D"]
    return {"D.f1": D["suggested"]["f1"], "D.precision": D["suggested"]["precision"], "D.recall": D["suggested"]["recall"],
            "D.paraphrase_recall": D["recall_by_surface"]["paraphrase"], "D.language_f1_gap": D["language_f1_gap"],
            "invariance": r["fairness"]["invariance"], "ece": r["calibration"]["ece"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("committed")
    ap.add_argument("fresh")
    ap.add_argument("--tolerance", type=float, default=0.01)
    a = ap.parse_args()
    old, new = (headline(json.load(open(p, encoding="utf-8"))) for p in (a.committed, a.fresh))
    bad = [f"{k}: committed {old[k]} vs fresh {new[k]}" for k in old if abs(old[k] - new[k]) > a.tolerance]
    for k in old:
        print(f"{k:<22} {old[k]:.4f}  {new[k]:.4f}")
    for b in bad:
        print("✗", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
