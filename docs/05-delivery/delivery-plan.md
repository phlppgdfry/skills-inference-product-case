# Delivery plan

From the validated spike to the Haldane pilot. Estimates are three-point (optimistic / likely / pessimistic, in engineer-days); the plan uses the PERT mean `(o + 4m + p) / 6` and a buffer equal to the summed standard deviation `(p - o) / 6` for the critical path. Illustrative, for a team of one AI product engineer, one backend engineer and half a frontend engineer.

| # | Milestone | Scope | o / m / p | PERT | Depends on | Exit criterion |
|---|---|---|---|---|---|---|
| M1 | Data and eval harness | Generator, gold labels, splits, eval suites, gate in CI | 3 / 5 / 9 | 5.3 | – | Gate runs on every push |
| M2 | Extractor v1 (config B) | Sections, negation, alias trie, bilingual taxonomy | 3 / 4 / 7 | 4.3 | M1 | B precision ≥ 0.98 |
| M3 | Scorer and review band (D) | Semantic candidates, features, calibrated scorer, thresholds | 4 / 6 / 10 | 6.3 | M2 | Gate passes |
| M4 | API and observability | Contract, auth, limits, feedback, logs, metrics | 3 / 5 / 8 | 5.2 | M3 | Contract test, load test p95 < 250 ms |
| M5 | Review screen (demo → product) | Highlighted evidence, keyboard accept/reject | 5 / 8 / 14 | 8.5 | M4 | Usability test with 2 HR partners |
| M6 | Verifier (optional) | Claude on Bedrock, grounded, offline eval on dev band | 2 / 3 / 6 | 3.3 | M3 | Verified precision ≥ accept precision |
| M7 | Shadow run on Haldane data | 40 real descriptions labelled by 2 HR partners | 3 / 5 / 10 | 5.5 | M4 | Real-data report; go/no-go |
| M8 | Pilot | 2 HR partners, flag on, measure H3/H4 | 10 / 10 / 15 | 10.8 | M5, M7 | Pilot report |

**Critical path:** M1 → M2 → M3 → M4 → M5 → M8, about 40 engineer-days PERT plus a buffer of about 6 days. M6 and M7 run in parallel with M5.

## How scope is managed

- **Fixed:** the guardrails (precision, distractors, invariance, evidence). Missing one moves the date, not the bar.
- **Flexible, in this order of cutting:** the verifier (M6), French aliases, the "close to learn" hints, the match endpoint UI.
- **Weekly:** burn-down against the PERT plan, the risk register top 5, and the latest eval report. A risk that moves to "likely" gets an owner and a date the same day.

## What the PM gets each week

One paragraph: what shipped, what the evals say (the README table, regenerated), the top risk and what is being done about it, and the decision needed from them, if any.
