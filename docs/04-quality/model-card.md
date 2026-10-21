# Model card: SkillDraft scorer <!--n:model_version-->scorer-dcf5b308<!--/n-->

## What it is
A logistic regression that turns 11 features of a (job description, skill) candidate into the probability that the skill belongs in the role's profile. Trained on the train split, thresholds on dev, reported on test. File: `models/scorer.hashing-v1.json`.

## Intended use
Ranking and filtering candidate skills for a **draft** role profile that a person reviews. Not for: evaluating people, deciding about candidates, or any use without review.

## Features and weights

| Feature | Meaning | Weight |
|---|---|---|
| exact_good | alias match, not negated, in a job section | <!--n:w.exact_good-->+3.29<!--/n--> |
| exact_bad | alias match only in about-us or the offer | <!--n:w.exact_bad-->-2.48<!--/n--> |
| negated | only negated mentions ("no X needed") | <!--n:w.negated-->-1.51<!--/n--> |
| sem_good | best semantic similarity in a job section | <!--n:w.sem_good-->+2.86<!--/n--> |
| sem_margin | how much that sentence prefers this skill over the next | <!--n:w.sem_margin-->+6.66<!--/n--> |
| ambiguous_only | every alias match was ambiguous (SAP, lean, safety) | <!--n:w.ambiguous_only-->-1.53<!--/n--> |
| mentions | log(1 + pieces of evidence) | <!--n:w.mentions-->+1.91<!--/n--> |
| in_pref | best evidence reads as nice-to-have | <!--n:w.in_pref-->-0.23<!--/n--> |
| in_title | alias in the job title | <!--n:w.in_title-->+0.21<!--/n--> |
| company_voice | all evidence is "we/our" talk | <!--n:w.company_voice-->-0.75<!--/n--> |
| no_headings | the description has no sections | <!--n:w.no_headings-->-0.52<!--/n--> |
| bias | | <!--n:w.bias-->-1.73<!--/n--> |

Reading it: an alias in a job section is strong evidence; the same alias only in company talk is strong counter-evidence; a semantic match counts mostly when the sentence clearly prefers this skill over others (the margin weight is the largest).

## Thresholds
accept ≥ <!--n:accept_at-->0.425<!--/n--> (95% precision on dev); review ≥ <!--n:review_at-->0.344<!--/n--> (band at least 25% real skills on dev).

## Performance (test)
Precision <!--n:D.precision-->0.963<!--/n-->, recall <!--n:D.recall-->0.953<!--/n-->, F1 <!--n:D.f1-->0.958<!--/n-->; described-only skills found <!--n:D.paraphrase_recall-->80%<!--/n-->; ECE <!--n:ece-->0.061<!--/n-->; Brier <!--n:brier-->0.036<!--/n-->; F1 EN <!--n:D.f1_en-->0.951<!--/n-->, NL <!--n:D.f1_nl-->0.971<!--/n-->. Reliability table: `evals/reports/offline.hashing-v1.json` and the [evals page](../../site/index.html#evals).

With the Transformers embedder (<!--n:hf.name-->paraphrase-multilingual-MiniLM-L12-v2<!--/n-->, separately trained scorer): F1 <!--n:hf.D.f1-->0.936<!--/n-->, described-only skills <!--n:hf.D.paraphrase_recall-->66%<!--/n-->, ECE <!--n:hf.ece-->0.059<!--/n-->.

## Limitations
- Trained and tested on generated job descriptions; real ads are messier.
- The semantic feature inherits the embedder's blind spots; the hashing embedder rewards word overlap.
- Two languages. French and German job descriptions will be read with English and Dutch aliases only.

## Training reproducibility
`python -m skilldraft train` (standard library, gradient descent) and `python -m training.train_torch` (PyTorch, L-BFGS) fit the same objective and agree within 0.007 per weight; CI checks within 0.02.
