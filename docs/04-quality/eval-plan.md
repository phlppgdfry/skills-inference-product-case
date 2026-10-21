# Evaluation plan

## Data and splits

`scripts/make_data.py` generates <!--n:jds-->300<!--/n--> job descriptions (EN about two thirds, NL one third) across eight role families, with gold labels written by the generator, not the pipeline:

- **gold skills** with importance (required, preferred), evidence spans and how they were written: label <!--n:surface.label-->121<!--/n-->, alias <!--n:surface.alias-->521<!--/n-->, described only <!--n:surface.paraphrase-->200<!--/n-->, title <!--n:surface.title-->7<!--/n--> (test split counts);
- **distractors**: skills mentioned in about-us (<!--n:distractors.about-->58<!--/n-->), the offer (<!--n:distractors.offer-->27<!--/n-->) or as not required (<!--n:distractors.negated-->38<!--/n-->);
- **coded phrases** (age, gender, origin), some deliberately outside the checker's lexicon;
- **counterfactuals**: four variants per dev and test description (he, she, other contact name, age-coded sentence).

Every rendered sentence is checked by an independent alias scan in the generator: a sentence may only contain the aliases it was meant to contain. Described-only sentences (paraphrases) exist only in the generator, never in the taxonomy.

| Split | Size | Used for |
|---|---|---|
| train | 150 | scorer weights |
| dev | 50 | accept/review thresholds, semantic floor, config C threshold |
| test | 100 | every number in the docs |

## Suites

| Suite | Question | Metric | Gate |
|---|---|---|---|
| extraction | Right skills? | micro precision / recall / F1 of *suggested* skills | precision ≥ 0.93; recall with review ≥ 0.93 |
| surfaces | Described skills found? | recall per surface | reported |
| distractors | Company talk, offer, "not needed" kept out? | share suggested per kind | each ≤ 10% |
| importance | Required vs nice-to-have right? | accuracy on true positives | ≥ 93% |
| evidence | Points at the right sentence? | first evidence overlaps a gold span | ≥ 98% |
| calibration | Does 0.9 mean 90%? | ECE (10 bins), Brier, reliability table | ECE ≤ 0.08 |
| fairness | Personal wording changes nothing? | counterfactual invariance (skills, status, importance, confidence) | 100% |
| language parity | EN and NL equally good? | F1 gap | ≤ 0.05 |
| checker | Coded phrases caught, no false alarms? | recall on known phrases, false alarms | 100%, 0 |
| match | Better profiles → better shortlist? | nDCG@5 of the people ranking vs the gold-profile ranking | reported |
| latency | Interactive? | p50 / p95 in process | p95 ≤ 250 ms |

Thresholds live in `evals/thresholds.json`. Latency is gated but not written to the committed report, because it depends on the machine.

## Current results (test)

| | A spike | B rules | C fixed semantic | **D production** |
|---|---|---|---|---|
| Precision | <!--n:A.precision-->0.892<!--/n--> | <!--n:B.precision-->1.000<!--/n--> | <!--n:C.precision-->0.929<!--/n--> | <!--n:D.precision-->0.963<!--/n--> |
| Recall | <!--n:A.recall-->0.362<!--/n--> | <!--n:B.recall-->0.762<!--/n--> | <!--n:C.recall-->0.928<!--/n--> | <!--n:D.recall-->0.953<!--/n--> |
| F1 | <!--n:A.f1-->0.515<!--/n--> | <!--n:B.f1-->0.865<!--/n--> | <!--n:C.f1-->0.929<!--/n--> | <!--n:D.f1-->0.958<!--/n--> |
| F1 EN / NL | <!--n:A.f1_en-->0.583<!--/n--> / <!--n:A.f1_nl-->0.351<!--/n--> | <!--n:B.f1_en-->0.869<!--/n--> / <!--n:B.f1_nl-->0.856<!--/n--> | <!--n:C.f1_en-->0.929<!--/n--> / <!--n:C.f1_nl-->0.928<!--/n--> | <!--n:D.f1_en-->0.951<!--/n--> / <!--n:D.f1_nl-->0.971<!--/n--> |
| Importance accuracy | <!--n:A.importance-->78.8%<!--/n--> | <!--n:B.importance-->97.2%<!--/n--> | <!--n:C.importance-->96.8%<!--/n--> | <!--n:D.importance-->96.9%<!--/n--> |
| nDCG@5 of the shortlist | <!--n:A.ndcg-->0.744<!--/n--> | <!--n:B.ndcg-->0.957<!--/n--> | <!--n:C.ndcg-->0.990<!--/n--> | <!--n:D.ndcg-->0.994<!--/n--> |

D also: <!--n:D.review_per_jd-->0.3<!--/n--> review items per description, <!--n:D.review_precision-->16.7%<!--/n--> of them real skills, recall with review <!--n:D.recall_with_review-->0.959<!--/n-->; ECE <!--n:ece-->0.061<!--/n-->, Brier <!--n:brier-->0.036<!--/n--> over <!--n:candidates-->1156<!--/n--> candidates; counterfactual invariance <!--n:invariance-->100%<!--/n--> over <!--n:variants-->400<!--/n--> variants.

## Known blind spots

- **Generated text.** Templates are cleaner than real job ads; the same author wrote paraphrases and definitions. Mitigation: the Transformers run (EVIDENCE.md) and a labelled real sample in the pilot.
- **One paraphrase per skill and language.** Fine for a feature-based scorer; it rules out training any sentence-level model on this data.
- **Micro averages** favour frequent skills. Per-skill recall is in the JSON report for the families that matter to a customer.
- **The verifier is not evaluated** against a live model.
