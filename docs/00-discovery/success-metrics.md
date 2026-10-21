# Success metrics

One outcome metric, a few product metrics that move it, and guardrails that stop a release. Offline numbers come from `evals/run.py` on the generated test set; pilot numbers do not exist yet.

## Outcome

**Reviewed role profiles per HR business partner per week.** Today: ~9 (45 min each, 7 hours of focused time; illustrative). Target for the Haldane pilot: ≥ 40.

## Product metrics

| Metric | Why | Offline today | Pilot target |
|---|---|---|---|
| Median review time per profile | H3: the whole value case | n/a | ≤ 10 min |
| Accept rate of "suggested" skills | H4: is the confidence trustworthy? | proxy: precision <!--n:D.precision-->0.963<!--/n--> | ≥ 90% |
| Skills added by reviewers per profile | What we miss, as felt by the user | proxy: <!--n:D.fn-->40<!--/n--> missed skills on <!--n:test.descriptions-->100<!--/n--> descriptions | ≤ 1 |
| "Please check" items per profile | Review load | <!--n:D.review_per_jd-->0.3<!--/n--> | ≤ 2 |
| Uncovered requirement sentences per profile | Taxonomy gaps | in the API response | trend down per taxonomy release |

## Guardrails (release blockers)

These are in `evals/thresholds.json`; CI fails if one is crossed.

- Precision of suggested skills ≥ 0.93
- Evidence points at the right sentence for ≥ 98% of correct skills
- Each distractor kind suggested ≤ 10%
- Counterfactual invariance = 100%
- EN/NL F1 gap ≤ 0.05
- Expected calibration error ≤ 0.08
- p95 latency ≤ 250 ms in process

## Metrics we chose not to use

- **"Number of skills extracted."** More is not better; it rewards noise.
- **F1 alone.** It hides the precision/recall split that users feel very differently (interview pattern 1).
