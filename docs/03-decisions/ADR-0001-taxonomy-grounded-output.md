# ADR-0001: Output only taxonomy skills

**Status:** Accepted

## Context
Customers compare roles, people and markets across sites and companies. That only works if "forklift", "heftruck" and "reach truck" become the same skill. Interview pattern 3: vocabulary is the slow part of writing profiles.

## Options
1. **Free-text skills**, normalised later. Flexible, but every model call can invent a new string; normalisation becomes the product anyway.
2. **Taxonomy-grounded output**: the pipeline can only emit ids from a versioned taxonomy; aliases in EN and NL map surface words to ids.
3. **Customer-specific taxonomies.** Fits each customer, kills comparison across customers.

## Decision
Option 2. The alias trie, the semantic matcher and the LLM verifier can all only produce taxonomy ids (the verifier through a JSON-schema enum). Anything that cannot be mapped is returned as an *uncovered requirement* for a person to see, not dropped silently.

## Consequences
- Recall is capped by the taxonomy. The uncovered list makes that cap visible: it shows the sentence for <!--n:D.missed_flagged-->45.7%<!--/n--> of the skills D misses entirely.
- Taxonomy releases become product releases (versioned, evaluated).
- Hallucinated skills are impossible by construction; wrong skills are still possible.

## How we would know it was wrong
Reviewers add skills that do not exist in the taxonomy more than once per profile, or uncovered requirements do not go down after two taxonomy releases.

## When to revisit
When a customer needs skills outside the shared taxonomy (custom skills as an extension with their own ids, not free text).
