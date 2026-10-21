# Hypotheses and kill criteria

Each hypothesis has a measurable signal and a result that would make us stop or change course, written *before* the spike. Status shows what the offline evals say; pilot hypotheses are open until a real pilot runs.

| # | Hypothesis | Signal | Kill / change criterion | Status |
|---|---|---|---|---|
| H1 | Most required skills in a job description are **named** with a word our taxonomy can know | Recall of alias matching (config B) | B recall < 60% → the taxonomy approach is wrong; go generative | **Holds offline.** B recall <!--n:B.recall-->0.762<!--/n--> at precision <!--n:B.precision-->1.000<!--/n--> |
| H2 | The rest are **described**, and a semantic match can find enough of them to matter | Paraphrase recall of C/D | D paraphrase recall < 50% → invest in a trained encoder before launch | **Holds offline** with a caveat: <!--n:D.paraphrase_recall-->80%<!--/n--> with the hashing embedder, <!--n:hf.D.paraphrase_recall-->66%<!--/n--> with a generic multilingual encoder ([EVIDENCE](../../EVIDENCE.md)) |
| H3 | A reviewer checks a draft profile in **under 10 minutes** (vs ~45 to write one) | Median review time in the pilot | > 20 minutes → the draft is not saving time; rethink the review screen | **Open.** Needs the pilot ([impact-measurement](../05-delivery/impact-measurement.md)) |
| H4 | Reviewers **trust** the confidence enough to skip checking high-confidence skills | Accept rate of suggested skills ≥ 90%, and time spent per suggested skill | Accept rate < 80% → recalibrate or raise the threshold | **Proxy holds offline:** precision of suggested <!--n:D.precision-->0.963<!--/n-->, ECE <!--n:ece-->0.061<!--/n-->. Real accept rate is a pilot metric |
| H5 | Company boilerplate and coded language do **not** leak into profiles | Distractor rate; counterfactual invariance | Any distractor kind > 10%, or invariance < 100% → block release | **Holds offline** after two fixes found by the evals ([fairness](../04-quality/fairness.md)) |
| H6 | Better role profiles give a **better internal-mobility shortlist** | nDCG@5 of the people ranking vs the oracle | D not better than B → extraction quality is not the bottleneck for matching | **Holds offline:** nDCG@5 <!--n:B.ndcg-->0.957<!--/n--> (B) → <!--n:D.ndcg-->0.994<!--/n--> (D) |

## What would change the plan

- If H3 fails in the pilot while H1/H2/H4 hold, the model is not the problem: the review screen is. Next experiment: a keyboard-only review flow, then measure again.
- If H2 fails on real Haldane descriptions (likely, see the encoder result), the next investment is a skills-specific encoder trained on reviewer feedback, not a bigger LLM.
