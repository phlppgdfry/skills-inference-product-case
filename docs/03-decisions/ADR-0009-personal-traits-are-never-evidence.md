# ADR-0009: Sentences about personal traits are never evidence

**Status:** Accepted

## Context
The counterfactual suite (same description, only a pronoun, a contact name or age-coded wording changed) first measured an invariance of 60%. Adding "He will report to the plant manager" or "Je komt terecht in een jong en dynamisch team" moved scores of other skills through weak semantic matches ("team" → shift leadership); a different contact name changed which skills the contact line resembled ([fairness](../04-quality/fairness.md)).

## Options
1. Raise the semantic floor until the effect disappears. Fragile: it depends on the wording of today's test phrases.
2. Exclude **sentences flagged by the coded-language checker** from all evidence, exclude **contact lines** from semantic matching, and allow semantic evidence only in sections that describe the job.
3. Remove names and pronouns before matching (masking). Useful, but it does not cover age-coded wording.

## Decision
Option 2, plus a semantic floor chosen on dev by "best F1 among the values that keep every dev counterfactual unchanged". A sentence about who the candidate is says nothing about what they can do.

## Consequences
- Invariance on the test counterfactuals: <!--n:invariance-->100%<!--/n--> (gender <!--n:invariance.gender-->100%<!--/n-->, name <!--n:invariance.name-->100%<!--/n-->, age <!--n:invariance.age-->100%<!--/n-->); gated at 100%.
- Invariance for coded phrases the lexicon does not know rests on the section and floor rules only. The checker misses <!--n:checker.missed-->15<!--/n--> of <!--n:checker.phrases-->67<!--/n--> coded phrases in the data (by design: they are not in the lexicon).

## How we would know it was wrong
A counterfactual kind we did not think of (nationality in a name, disability wording) changes profiles. Add it to the generator first; the gate then catches it.

## When to revisit
When the checker becomes a model, its own errors become a fairness risk for this rule; evaluate both together.
