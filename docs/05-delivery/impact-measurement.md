# Measuring impact in the pilot

Offline evals say the model is good on generated data. They cannot say the product saves time. The pilot can.

## Design

- **Before:** the two pilot HR partners each write 10 profiles the current way (with the consultant's template), timed.
- **After:** the same partners review 20 drafts each, timed per profile by the review screen (open → submit).
- **Assignment:** roles randomly split so both conditions get the same mix of families and languages.
- **Quality check:** a third HR partner blind-rates 10 profiles from each condition on completeness and correctness (1–4).

## Metrics and decision rule

| Metric | Decision |
|---|---|
| Median minutes per profile (after vs before) | Ship to all of Haldane if ≤ 10 and at most a quarter of "before" |
| Blind quality rating | "After" must not be lower than "before" |
| Accept rate of suggested skills | ≥ 90%, or the threshold moves up |
| Skills added per profile | ≤ 1, or the taxonomy or encoder needs work (R1, R5) |
| Reviewer comments | Read every one; tag them; top 3 themes go into the next iteration |

## What it costs

Two HR partners for about 4 hours each in the "before" week and spread over 4 weeks after. The data science cost is the 40-description labelling for the shadow run (about a day for two people).

## What we will not claim

No time saving per year until the pilot measured it. The business case in the [one-pager](../07-stakeholders/one-pager-for-hr.md) is labelled as an assumption until then.
