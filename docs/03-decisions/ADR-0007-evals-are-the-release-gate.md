# ADR-0007: Evals are the release gate, and docs quote generated numbers

**Status:** Accepted

## Context
A change to the taxonomy, a cue list, a threshold or the embedder changes behaviour without failing a unit test. The first build of this case shows it: a fairness problem and a useless review band were both invisible to the unit tests ([fairness](../04-quality/fairness.md), ADR-0003).

## Decision
- `python -m evals.run --gate` fails CI when any threshold in `evals/thresholds.json` is crossed. Thresholds only go up; lowering one needs an ADR.
- `scripts/build.py --check` retrains the scorer, re-picks the semantic floor on dev, regenerates the reports, the site data and every `<!--n:key-->` number in the docs, and fails if anything is stale.
- Splits are fixed: train for weights, dev for thresholds and the semantic floor, test for reporting only.

## Consequences
- No document can quote a number the code does not produce.
- CI takes about two minutes longer. Worth it.

## How we would know it was wrong
People start tuning on the test split to pass the gate. The split discipline in `skilldraft/train.py` and code review are the defence; a fresh labelled set per quarter is the real fix.

## When to revisit
When real labelled data arrives: the gate moves to it, and the generated set stays as a regression suite.
