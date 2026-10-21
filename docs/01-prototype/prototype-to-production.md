# From prototype to production

What changed between the spike code and the service, and why each change was worth its cost.

| Concern | Spike (config A) | Production (config D) | Why the change |
|---|---|---|---|
| Vocabulary | Skill labels | Bilingual alias trie, longest match, ambiguity flags | Recall ×2.6; "SAP SuccessFactors" is not "SAP" |
| Structure | None | Sections from headings, cues without headings, negation scope, company voice | Removes the distractors that break trust |
| Described skills | Not found | Semantic candidates (top 2 per sentence, floor chosen on dev) behind an `Embedder` interface | <!--n:surface.paraphrase-->200<!--/n--> of <!--n:test.gold-->849<!--/n--> gold skills are only described |
| Decision | Found = suggested | Calibrated logistic score, accept threshold for 95% precision, review band ≥ 25% real | A reviewer can trust the order of the list |
| Evidence | Character offset of the label | Up to three evidence spans, exact first; flagged sentences never count | Review in a glance; fairness by construction |
| Determinism | Yes | Yes, and a test for it | Same input, same profile, same audit trail |
| Interface | Function call | HTTP API with OpenAPI contract, problem details, auth, limits | Integrations with HRIS systems |
| Learning loop | None | `/v1/feedback` stores verdicts with model version, no text | Next training set comes from reviewers |
| Quality | Eyeballing | Eval suite, release gate in CI, numbers in docs generated from reports | No release on vibes |
| Observability | print | JSON logs without text, Prometheus metrics, spans with request id | Operate it, support it |
| Portability | Python only | JavaScript port with a parity test (100/100) | The demo runs the real pipeline in the browser |
| Training stack | n/a | Standard-library trainer + PyTorch trainer, checked against each other | Move to GPU or a neural head without changing what the score means |

## What stayed hacky on purpose

- The coded-language checker is a lexicon. It is explainable and has zero false alarms on the set; a model would need its own fairness evaluation.
- Related skills are neighbours in the taxonomy family. Good enough for "close to learn" hints, not for a career path engine.
- No database: the taxonomy is a versioned JSON file and feedback is a JSONL file. Both are interfaces that a real store replaces without touching the pipeline.
