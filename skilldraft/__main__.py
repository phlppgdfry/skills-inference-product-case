"""Command line.

    python -m skilldraft infer data/samples/maintenance-technician.txt
    python -m skilldraft infer - < job.txt            # read from stdin
    python -m skilldraft match JD-201                  # rank the 60 employees for a test role
    python -m skilldraft train [--embedder hf]
    python -m skilldraft serve [--port 8080]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import default_pipeline, make_embedder


def _read(path: str) -> str:
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")


def cmd_infer(args) -> int:
    pipe = default_pipeline(args.config, args.embedder)
    out = pipe.infer(_read(args.file))
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    for s in out["skills"]:
        mark = "✓" if s["status"] == "suggested" else "?"
        quote = s["evidence"][0]["quote"] if s["evidence"] else ""
        print(f"{mark} {s['label']:<34} {s['importance']:<9} {s['confidence']:.2f}  “{quote[:60]}”")
    for u in out["uncovered_requirements"]:
        print(f"· not mapped to the taxonomy: “{u['text'][:80]}”")
    for f in out["language_flags"]:
        print(f"! {f['category']}: “{f['quote']}”: {f['suggestion']}")
    print(json.dumps(out["meta"]))
    return 0


def cmd_match(args) -> int:
    from .match import rank
    from .train import ROOT, load_jds

    jd = next(j for j in load_jds() if j["id"] == args.jd)
    people = [json.loads(line) for line in (ROOT / "data" / "people.jsonl").read_text(encoding="utf-8").splitlines()]
    pipe = default_pipeline()
    profile = pipe.infer(jd["text"])
    related = {s["id"]: s["related"] for s in pipe.taxonomy.skills}
    print(f"{jd['title']} ({jd['id']})")
    for r in rank(profile["skills"], people, related=related)[: args.top]:
        print(f"  {r['person_id']}  {r['score']:.2f}  has {len(r['matched'])}, gaps {', '.join(r['gaps'][:4]) or '-'}"
              + (f"; close to learn: {', '.join(r['learnable'])}" if r["learnable"] else ""))
    return 0


def cmd_train(args) -> int:
    from .pipeline import Pipeline
    from .taxonomy import Taxonomy
    from .train import model_path, train

    emb = make_embedder(args.embedder)
    model = train(Pipeline(Taxonomy.load(), emb, None, config="C"))
    path = model_path(emb.name)
    model.save(path)
    print(f"wrote {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}: {model.version}, "
          f"accept ≥ {model.accept_at}, review ≥ {model.review_at}")
    return 0


def cmd_serve(args) -> int:
    from .api import serve
    serve(args.host, args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="skilldraft")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("infer")
    p.add_argument("file")
    p.add_argument("--config", default="D", choices=list("ABCD"))
    p.add_argument("--embedder", default="hashing")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_infer)
    p = sub.add_parser("match")
    p.add_argument("jd")
    p.add_argument("--top", type=int, default=5)
    p.set_defaults(fn=cmd_match)
    p = sub.add_parser("train")
    p.add_argument("--embedder", default="hashing")
    p.set_defaults(fn=cmd_train)
    p = sub.add_parser("serve")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.set_defaults(fn=cmd_serve)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
