# Fairness

SkillDraft v1 describes **roles**, not people. The fairness risks are therefore (1) that wording about people in a job ad changes the role profile, (2) that the product works better in one language, and (3) that it lets exclusionary wording through. Phase 2 (matching people) adds outcome fairness, covered at the end.

## What is measured

| Risk | Test | Result (test split) | Gate |
|---|---|---|---|
| A pronoun changes the profile | Same description with "He will report…" and "She will report…" | <!--n:invariance.gender-->100%<!--/n--> unchanged | 100% |
| The contact person's name changes the profile | Swap the contact name for a name from another background | <!--n:invariance.name-->100%<!--/n--> unchanged | 100% |
| Age-coded wording changes the profile | Add "Join our young and dynamic team" / "jong en dynamisch team" | <!--n:invariance.age-->100%<!--/n--> unchanged | 100% |
| Dutch descriptions get worse profiles | F1 EN vs NL | <!--n:D.f1_en-->0.951<!--/n--> vs <!--n:D.f1_nl-->0.971<!--/n--> (gap <!--n:D.lang_gap-->0.020<!--/n-->) | gap ≤ 0.05 |
| Coded wording goes unnoticed | Checker recall on phrases in its lexicon; false alarms | <!--n:checker.recall_known-->100%<!--/n-->, <!--n:checker.false_alarms-->0<!--/n--> false alarms | 100%, 0 |
| … including phrases it does not know | Recall on all coded phrases | <!--n:checker.recall-->77.6%<!--/n--> (<!--n:checker.missed-->15<!--/n--> of <!--n:checker.phrases-->67<!--/n--> missed) | reported |

"Unchanged" means the same skills, with the same status, importance and confidence to three decimals.

## What the suite caught during the build

The first full eval run reported **60% counterfactual invariance** (gender 42%, age 63%, name 94%). No unit test had noticed. Three causes, three fixes:

1. **Weak semantic matches from neutral sentences.** "He will report to the plant manager" was a 0.065 match for forklift operation; the floor was 0.05, so it became evidence and moved the score. *Fix:* the floor is chosen on dev with invariance as a hard constraint (now <!--n:sweep.chosen-->0.08<!--/n-->).
2. **Contact lines.** "Contact Fatima El Amrani, our HR partner" and "Contact Pieter Claes, …" resembled different skills. *Fix:* contact lines never get semantic matching.
3. **The coded sentence itself.** "Je komt terecht in een jong en dynamisch team" addresses the candidate, so it counted as a job sentence, and "team" resembled shift leadership. *Fix:* a sentence flagged as coded language is never evidence ([ADR-0009](../03-decisions/ADR-0009-personal-traits-are-never-evidence.md)).

The same rules hold with the Transformers encoder: invariance <!--n:hf.invariance-->100%<!--/n-->, but only above its own dev-chosen floor (<!--n:hf.sweep.chosen-->0.40<!--/n-->). Below 0.35 invariance drops again (`evals/reports/sweep.hf-*.json`), which shows the floor matters for every embedder.

## Language parity, honestly

With the hashing embedder Dutch does slightly *better* than English; with the generic multilingual encoder Dutch is worse (F1 <!--n:hf.D.f1_nl-->0.902<!--/n--> vs <!--n:hf.D.f1_en-->0.953<!--/n-->, gap <!--n:hf.D.lang_gap-->0.051<!--/n-->, just over the gate). If a trained encoder replaces the hashing one, the language gate is the one most likely to fail first. That is the point of having it.

## The coded-language checker

A lexicon of 16 patterns in EN and NL (age, gender, origin), with a neutral suggestion per pattern. The Belgian anti-discrimination laws of 10 May 2007 cover age, gender and origin among other grounds; an age limit in a job ad is unlawful unless a legal exception applies. The checker *suggests*; HR decides. It is a lexicon so every flag can be explained; it misses paraphrased coded wording ("Recent graduates are preferred", "Je bent een jonge starter") by design, and the eval counts those misses.

## Phase 2: matching people

When the product ranks employees, the fairness question becomes "do people with the same skills get the same rank regardless of group?". Plan:

- Group fairness audits on a consented, pseudonymised sample with self-declared attributes, held by the customer's HR, not by Orveda (GDPR art. 9 data). Selection-rate ratios per group as a *screening* signal (the four-fifths heuristic), followed by a look at why, never as a pass/fail.
- Counterfactual tests on people: same skills, different name or age in the record → same rank (the API ranks on skill ids only, so this holds by construction today; the test keeps it that way).
- Explanations per person (matched skills, gaps) are already in the response.
