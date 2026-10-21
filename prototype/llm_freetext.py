"""The other half of the day-one spike: ask an LLM for skills as free text.

    pip install "anthropic>=1.0"
    python prototype/llm_freetext.py --n 20                      # Claude API (ant auth login or ANTHROPIC_API_KEY)
    python prototype/llm_freetext.py --n 20 --platform bedrock   # Amazon Bedrock, AWS_REGION=eu-central-1

Deliberately hacky: one prompt, no taxonomy, no schema. It answers one question for the
spike report: if we let a model name the skills, how many of its answers can we even map
to the taxonomy, and how good are the ones we can? It costs money (one call per job
description) and has not been run for this repository (EVIDENCE.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skilldraft.taxonomy import Taxonomy  # noqa: E402
from skilldraft.text import fold, tokenize  # noqa: E402
from skilldraft.train import load_jds  # noqa: E402

PROMPT = "List the skills this job requires, one per line, nothing else.\n\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--platform", choices=["anthropic", "bedrock"], default="anthropic")
    args = ap.parse_args()
    import anthropic

    client = anthropic.AnthropicBedrockMantle(aws_region="eu-central-1") if args.platform == "bedrock" else anthropic.Anthropic()
    model = "anthropic.claude-opus-5-5" if args.platform == "bedrock" else "claude-opus-5-5"
    tax = Taxonomy.load()
    lines = mapped = tp = fp = fn = 0
    for jd in load_jds("test")[: args.n]:
        r = client.messages.create(model=model, max_tokens=1000, output_config={"effort": "low"},
                                   messages=[{"role": "user", "content": PROMPT + jd["text"]}])
        text = next((b.text for b in r.content if b.type == "text"), "")
        got = set()
        for line in [x.strip("-•* ").strip() for x in text.splitlines() if x.strip()]:
            lines += 1
            hits = tax.match(tokenize(fold(line)))
            if hits and len(hits) == 1 and hits[0].start == 0:
                mapped += 1
                got.add(hits[0].skill_id)
        gold = {g["id"] for g in jd["gold"]["skills"]}
        tp, fp, fn = tp + len(got & gold), fp + len(got - gold), fn + len(gold - got)
    print(json.dumps({"model": model, "descriptions": args.n, "lines": lines,
                      "mappable_share": round(mapped / lines, 3) if lines else 0,
                      "precision_of_mapped": round(tp / (tp + fp), 3) if tp + fp else 0,
                      "recall": round(tp / (tp + fn), 3) if tp + fn else 0}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
