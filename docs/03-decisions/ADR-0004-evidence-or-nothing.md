# ADR-0004: No skill without evidence

**Status:** Accepted

## Context
Every interviewee asked "why". Reviewing a suggestion with its sentence is a glance; without it, re-reading the whole description.

## Decision
Every skill in a profile carries one to three evidence spans (character offsets into the original text, plus the quote), exact matches first. Text folding keeps one character per character so offsets survive accent stripping (`skilldraft/text.py::fold`). The LLM verifier must return a quote that exists in the text.

## Consequences
- The UI can highlight. The API test checks `text[start:end] == quote` for every skill.
- Evidence accuracy is a gated metric: the first evidence of a correct skill overlaps a gold sentence for <!--n:D.evidence-->100%<!--/n--> of correct skills on test.
- Some correct inferences without a quotable sentence (pure world knowledge) are impossible. That is intended.

## How we would know it was wrong
Reviewers accept skills but report the highlighted sentence as irrelevant.

## When to revisit
Never for suggested skills. A future "skills you might also want" feature could relax it, clearly labelled.
