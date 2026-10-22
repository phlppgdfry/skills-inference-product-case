# SkillDraft: from an ambiguous ask to a skills service people trust

**An AI product engineering case.** A product manager asks: *"Customers say building skill profiles for their roles takes forever and the profiles are wrong. Can we use AI?"* This repository goes from that sentence through discovery, a measured two-day spike and the design decisions, to a shipped service: a job description goes in, and a draft skill profile comes out. Every skill is a taxonomy skill, points at the sentence it came from and carries a calibrated confidence. A person reviews it.

[![CI](https://github.com/phlppgdfry/skills-inference-product-case/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

> Fictional setting. Orveda (an HR-tech scale-up) and Haldane Group (an industrial customer) are invented; the interviews are synthetic and the job descriptions are generated. Every number below comes from the eval suite and is rewritten by `scripts/build.py`, so no page can quote a stale one. [EVIDENCE.md](EVIDENCE.md) separates what is executed, simulated and not done.

## The answer in one paragraph

The slow and error-prone part of a skill profile is not judgment; it is **vocabulary** ("heftruck", "reach truck" and "forklift licence" are one skill) and **noise** (about-us, benefits, "no experience with X needed"). SkillDraft maps text to a bilingual taxonomy with structure-aware rules, finds skills that are only described with a semantic matcher, and decides with a calibrated scorer that has a small review band. An LLM (Claude, on Amazon Bedrock for EU customers) may only confirm uncertain candidates, with a quote that must exist in the text. People accept, reject or add skills, and those verdicts become the next training set.

## What the spike and the evals show

| Question | Result (test set, <!--n:test.descriptions-->100<!--/n--> job descriptions, <!--n:test.gold-->849<!--/n--> gold skills) | Decision |
|---|---|---|
| Is the day-one hack a product? | Label matching: F1 <!--n:A.f1-->0.515<!--/n-->, and it suggests the skill from "Training in lean manufacturing" in <!--n:A.distractor.offer-->48.1%<!--/n--> of the offer mentions. No. | [Spike report](docs/01-prototype/spike-report.md) |
| Where does quality come from? | Aliases, sections, negation and company voice alone: precision <!--n:B.precision-->1.000<!--/n-->, recall <!--n:B.recall-->0.762<!--/n-->. Boring engineering does most of the work. | [ADR-0001](docs/03-decisions/ADR-0001-taxonomy-grounded-output.md) |
| What about skills that are only described? | <!--n:surface.paraphrase-->200<!--/n--> of <!--n:test.gold-->849<!--/n--> gold skills. The shipped config finds <!--n:D.paraphrase_recall-->80%<!--/n--> of them, at precision <!--n:D.precision-->0.963<!--/n--> and recall <!--n:D.recall-->0.953<!--/n--> overall (F1 <!--n:D.f1-->0.958<!--/n-->). | [ADR-0003](docs/03-decisions/ADR-0003-calibrated-score-and-review-band.md) |
| Can a reviewer trust the confidence? | Expected calibration error <!--n:ece-->0.061<!--/n-->; <!--n:D.review_per_jd-->0.3<!--/n--> "please check" items per profile. | [Model card](docs/04-quality/model-card.md) |
| Does wording about people change the profile? | First eval run: only 60% of he/she, name and age-wording variants left the profile unchanged. After three design fixes: <!--n:invariance-->100%<!--/n--> of <!--n:variants-->400<!--/n-->, gated in CI. | [Fairness](docs/04-quality/fairness.md), [ADR-0009](docs/03-decisions/ADR-0009-personal-traits-are-never-evidence.md) |
| Dutch as good as English? | F1 <!--n:D.f1_nl-->0.971<!--/n--> vs <!--n:D.f1_en-->0.951<!--/n-->. With a generic multilingual encoder the gap grows to <!--n:hf.D.lang_gap-->0.051<!--/n-->. | [Eval plan](docs/04-quality/eval-plan.md) |
| Do better profiles give better shortlists? | Internal-mobility ranking nDCG@5: <!--n:A.ndcg-->0.744<!--/n--> (spike) → <!--n:D.ndcg-->0.994<!--/n--> (shipped). | [Hypotheses](docs/00-discovery/hypotheses.md) |
| Can it read people's CVs without exposing them? (phase 2, flagged) | Personal data is masked before anything reads the CV: <!--n:cv.pii_masked-->100%<!--/n--> of <!--n:cv.pii_spans-->262<!--/n--> spans, <!--n:cv.pii_leaks-->0<!--/n--> values in any response, profile unchanged for another name or birth year (<!--n:cv.invariance-->100%<!--/n-->). Skills from CVs: precision <!--n:cv.precision-->0.953<!--/n-->, recall <!--n:cv.recall-->0.925<!--/n-->; "I would like to learn X" is not a skill. | [ADR-0010](docs/03-decisions/ADR-0010-person-profiles-mask-first.md) |
| What does it cost to run? | The LLM verifier only sees the review band: about <!--n:cost.per_profile-->$0.0030<!--/n--> per profile, <!--n:cost.per_1400-->$4.20<!--/n--> for Haldane's 1,400 roles (estimate). | [Cost](docs/06-operations/cost.md) |
| Does a real sentence encoder help? | Not this one: <!--n:hf.name-->paraphrase-multilingual-MiniLM-L12-v2<!--/n--> finds <!--n:hf.D.paraphrase_recall-->66%<!--/n--> of described skills (F1 <!--n:hf.D.f1-->0.936<!--/n-->). A generic encoder is not a skills encoder; the next step is one trained on reviewer feedback. | [EVIDENCE](EVIDENCE.md) |

## Read it by role

| You are | Start with | Then |
|---|---|---|
| Product manager (5 min) | [Problem brief](docs/00-discovery/problem-brief.md) | [Hypotheses](docs/00-discovery/hypotheses.md) · [user stories](docs/00-discovery/user-stories.md) · [trade-off memo](docs/07-stakeholders/trade-off-memo.md) |
| HR stakeholder | [One-pager](docs/07-stakeholders/one-pager-for-hr.md) | [the demo](site/demo/index.html) · [people demo](site/people/index.html) · [fairness](docs/04-quality/fairness.md) |
| Engineer (30 min) | [Technical design](docs/02-design/tech-design.md) | [`skilldraft/pipeline.py`](skilldraft/pipeline.py) · [API](docs/02-design/api.md) · [10 ADRs](docs/03-decisions/README.md) |
| ML / applied scientist | [Eval plan](docs/04-quality/eval-plan.md) | [model card](docs/04-quality/model-card.md) · [`evals/run.py`](evals/run.py) · [`training/train_torch.py`](training/train_torch.py) |
| Legal / DPO | [AI Act classification](docs/04-quality/ai-act.md) | [ADR-0008 people decide](docs/03-decisions/ADR-0008-people-decide.md) |
| Delivery lead | [Delivery plan](docs/05-delivery/delivery-plan.md) | [risk register](docs/05-delivery/risk-register.md) · [launch plan](docs/05-delivery/launch-plan.md) · [impact measurement](docs/05-delivery/impact-measurement.md) |

## Run it

Python 3.11 or newer; the core has no dependencies.

```bash
python -m unittest discover -s tests -t .              # unit, API and contract tests
python -m evals.run --gate                             # all eval suites + the release gate
python -m skilldraft infer data/samples/maintenance-technician.txt
python -m skilldraft match JD-201                      # rank 60 fictional employees for a test role
python -m skilldraft infer --kind cv data/samples/cv/cv-en.txt   # a person's skills, personal data masked
SKILLDRAFT_ENV=dev python -m skilldraft serve          # HTTP API on :8080 (contract: docs/02-design/openapi.yaml)
python scripts/build.py                                # retrain, re-pick thresholds, refresh reports, site data and every number in the docs
node tests/js/parity.mjs                               # the browser port gives the same profiles as Python
```

With the ML extras (`pip install ".[ml]"`: PyTorch, Transformers):

```bash
python -m training.train_torch --check                 # same scorer with PyTorch; must match the shipped weights
python -m skilldraft train --embedder hf               # scorer for the Transformers sentence encoder
python -m evals.run --embedder hf --write              # the suites with that encoder
```

The same API on FastAPI (`pip install ".[api]"`): `uvicorn skilldraft.adapters.fastapi_app:app` (typed requests, docs at `/docs`; `tests/test_fastapi.py` checks it answers like the stdlib server).

With an LLM (`pip install ".[llm]"`): `SKILLDRAFT_VERIFIER=bedrock AWS_REGION=eu-central-1 python -m skilldraft serve` sends the review band to Claude on Bedrock; `SKILLDRAFT_VERIFIER=anthropic` uses the Claude API. Both cost money per call.

The site (`site/`) is static: open `site/index.html` through any static server, e.g. `python -m http.server -d site`.

## What is in the box

```
docs/
  00-discovery/     problem brief, interview synthesis, opportunity tree, hypotheses with kill criteria,
                    user stories with acceptance criteria, success metrics
  01-prototype/     spike plan, spike report (configs A–D), prototype → production
  02-design/        technical design (RFC), OpenAPI 3.1 contract, API guide
  03-decisions/     10 ADRs
  04-quality/       eval plan, fairness, EU AI Act classification, model card
  05-delivery/      delivery plan with PERT estimates, risk register, launch plan, pilot impact design
  06-operations/    observability (logs, metrics, SLOs, drift), runbook, cost
  07-stakeholders/  HR one-pager, trade-off memo, demo script
skilldraft/         the service: text, taxonomy, embedder, pipeline, scorer, checker, match, LLM verifier, API, obs,
                    personal-data masking, development plans, cost model
  adapters/         Transformers sentence encoder, FastAPI app
training/           PyTorch trainer for the scorer
evals/              eval suites, release gate thresholds, reports
data/               taxonomy (71 skills, EN+NL), 300 generated job descriptions, 160 fictional CVs, counterfactuals, people, samples
prompts/            versioned verifier prompt + lock file
prototype/          the throwaway free-text LLM spike
scripts/            data generator, build
site/               case page, evals, browser demo with a guided tour, people demo (JS port of the pipeline)
tests/              unit, API, contract, data, PyTorch parity, JS parity
```

## Engineering practice shown

- **Discovery before code:** hypotheses with kill criteria written before the spike; every acceptance criterion names the test that checks it.
- **Hacky where it is cheap, robust where it matters:** the spike was throwaway; the data generator and eval harness were built properly first, because every later decision depends on them.
- **Measured trade-offs:** each design step (A → D) is an eval column; the review band and the semantic floor are explicit product decisions with numbers ([trade-off memo](docs/07-stakeholders/trade-off-memo.md)).
- **Splits kept clean:** weights on train, thresholds on dev, reporting on test.
- **Two implementations checking each other:** stdlib vs PyTorch trainer; Python vs JavaScript pipeline.
- **No number without a source:** `scripts/build.py --check` fails CI when a document quotes a number the code does not produce.
- **Operable:** OpenAPI contract test, RFC 9457 errors, auth, limits, JSON logs without text, Prometheus metrics, versioned model and taxonomy in every response.

## License

MIT. The company names are fictional; any resemblance to real organisations is unintended.
