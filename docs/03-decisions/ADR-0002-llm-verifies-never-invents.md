# ADR-0002: The LLM verifies, it never invents

**Status:** Accepted

## Context
LLMs read context well: "transformers" in a grid-equipment plant is not NLP. But free-text generation breaks ADR-0001, has no evidence span, varies per call and costs money for every description.

## Options
1. **LLM as the extractor** for every description.
2. **LLM as a verifier** for the uncertain band only: given candidate ids, their definitions and the text, say present or absent with a quote.
3. **No LLM.**

## Decision
Option 2 (`skilldraft/llm.py`). The request:
- lists only candidate ids, enforced by a JSON-schema enum in `output_config.format`;
- treats the job description as untrusted data inside tags (prompt injection rule in the prompt);
- requires a quote, and a "present" answer whose quote is not in the text is ignored;
- on the Claude API opts into server-side refusal fallbacks; on refusal, truncation or any error, the skill stays in the review band.

The prompt is versioned (`prompts/verify_v1.md`) and pinned by hash in `prompts/lock.json`.

## Consequences
- LLM cost scales with the review band (<!--n:D.review_per_jd-->0.3<!--/n--> items per description offline), not with volume.
- The worst failure is "more work for HR", never "a skill nobody asked for".
- **Not measured yet** against a live model (EVIDENCE.md). Before turning it on: run the review-band items of the dev set through it and require that verified precision ≥ the accept threshold's precision.

## How we would know it was wrong
Verified items are rejected by reviewers more often than suggested ones, or the verifier says "absent" for skills reviewers then add.

## When to revisit
If the review band grows (a weaker embedder on real data), the verifier's value grows. If it shrinks to near zero, remove it.
