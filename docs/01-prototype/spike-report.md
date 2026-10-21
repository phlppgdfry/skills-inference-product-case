# Spike report

*Measured on the <!--n:test.descriptions-->100<!--/n--> test job descriptions (<!--n:test.gold-->849<!--/n--> gold skills) of the generated data set. Numbers are refreshed by `scripts/build.py` from `evals/reports/offline.hashing-v1.json`.*

## Result in one table

| Config | What it does | Precision | Recall | F1 | Described-only skills found | "About us" / offer / "not needed" suggested |
|---|---|---|---|---|---|---|
| **A** spike | Skill label anywhere in the text | <!--n:A.precision-->0.892<!--/n--> | <!--n:A.recall-->0.362<!--/n--> | <!--n:A.f1-->0.515<!--/n--> | <!--n:A.paraphrase_recall-->0%<!--/n--> | <!--n:A.distractor.about-->15.5%<!--/n--> / <!--n:A.distractor.offer-->48.1%<!--/n--> / <!--n:A.distractor.negated-->39.5%<!--/n--> |
| **B** | Bilingual alias matcher + sections, negation, company voice | <!--n:B.precision-->1.000<!--/n--> | <!--n:B.recall-->0.762<!--/n--> | <!--n:B.f1-->0.865<!--/n--> | <!--n:B.paraphrase_recall-->0%<!--/n--> | <!--n:B.distractor.about-->0%<!--/n--> / <!--n:B.distractor.offer-->0%<!--/n--> / <!--n:B.distractor.negated-->0%<!--/n--> |
| **C** | B + semantic matches above a fixed similarity (<!--n:c_threshold-->0.14<!--/n-->, best on dev) | <!--n:C.precision-->0.929<!--/n--> | <!--n:C.recall-->0.928<!--/n--> | <!--n:C.f1-->0.929<!--/n--> | <!--n:C.paraphrase_recall-->69.5%<!--/n--> | <!--n:C.distractor.about-->3.5%<!--/n--> / <!--n:C.distractor.offer-->0%<!--/n--> / <!--n:C.distractor.negated-->5.3%<!--/n--> |
| **D** | All candidates, learned calibrated scorer, review band | <!--n:D.precision-->0.963<!--/n--> | <!--n:D.recall-->0.953<!--/n--> | <!--n:D.f1-->0.958<!--/n--> | <!--n:D.paraphrase_recall-->80%<!--/n--> | <!--n:D.distractor.about-->3.5%<!--/n--> / <!--n:D.distractor.offer-->0%<!--/n--> / <!--n:D.distractor.negated-->2.6%<!--/n--> |

## Answers

**Q1: Is there signal?** Yes, but the naive version is not a product. Label matching finds only a third of the skills (<!--n:A.recall-->0.362<!--/n-->) because people write "heftruck", "K8s" or "TIA Portal", not the taxonomy label. Worse for trust: it suggests the skill from "Training in lean manufacturing" in <!--n:A.distractor.offer-->48.1%<!--/n--> of the offer mentions, and from "no experience with X needed" in <!--n:A.distractor.negated-->39.5%<!--/n--> of them. It is also much worse in Dutch (F1 <!--n:A.f1_nl-->0.351<!--/n--> vs <!--n:A.f1_en-->0.583<!--/n-->) because the labels are English.

**Q2: Can free-text LLM output be mapped?** Not measured here. The script is in `prototype/llm_freetext.py` and needs an API key or Bedrock access (see [EVIDENCE](../../EVIDENCE.md)). The design does not depend on its answer: whatever the mappable share turns out to be, free text gives every customer a different vocabulary and no evidence span, which the interviews ruled out. The LLM moved to a narrower job ([ADR-0002](../03-decisions/ADR-0002-llm-verifies-never-invents.md)).

**Q3: Does structure matter?** A lot. Going from A to B, with a bilingual alias list and the section, negation and company-voice rules, removes every distractor and doubles recall, at precision <!--n:B.precision-->1.000<!--/n-->. Most of the product's quality comes from boring engineering, not from a model.

**Q4: How many skills are only described?** <!--n:surface.paraphrase-->200<!--/n--> of <!--n:test.gold-->849<!--/n--> gold skills on the test set ("you keep our workloads scaled across clusters"). B cannot find them by construction. A semantic matcher finds <!--n:C.paraphrase_recall-->69.5%<!--/n--> with a fixed threshold. The cost is precision, which drops from <!--n:B.precision-->1.000<!--/n--> to <!--n:C.precision-->0.929<!--/n-->.

**Q5: Can we say how sure we are?** Yes. Eleven readable features and a logistic model give a calibrated score (ECE <!--n:ece-->0.061<!--/n-->). The score buys back precision (<!--n:D.precision-->0.963<!--/n-->) and recall (<!--n:D.recall-->0.953<!--/n-->) at the same time, and it makes a review band possible.

## Decision

Build D as the product: a taxonomy-grounded, section-aware extractor with a calibrated scorer and mandatory evidence. Add an LLM only to judge the uncertain band, and a sentence encoder behind an interface so it can be swapped. Recorded as [ADR-0001](../03-decisions/ADR-0001-taxonomy-grounded-output.md) to [ADR-0004](../03-decisions/ADR-0004-evidence-or-nothing.md).

## What the spike does not prove

These numbers come from generated text whose paraphrases and taxonomy definitions were written by the same person. The hashing embedder benefits from the shared words. A generic multilingual encoder finds fewer described skills (<!--n:hf.D.paraphrase_recall-->66%<!--/n-->) and is weaker in Dutch. The real test is 40 Haldane descriptions labelled by two HR partners ([impact-measurement](../05-delivery/impact-measurement.md)).
