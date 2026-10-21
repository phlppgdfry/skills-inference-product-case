# Spike plan (time box: two days)

A spike answers questions; it does not ship. These were the questions, written before any code, with the cheapest experiment for each.

| # | Question | Cheapest experiment | Decision it unblocks |
|---|---|---|---|
| Q1 | Can we get any useful signal from job descriptions at all? | Match skill **labels** anywhere in the text (config A) | Whether to continue |
| Q2 | If a model names skills freely, can we map its answers to a taxonomy? | One free-text prompt per description ([`prototype/llm_freetext.py`](../../prototype/llm_freetext.py)) | Generative vs taxonomy-grounded design |
| Q3 | How much do sections, negation and company talk matter? | Alias matcher with hand rules (config B) | Whether structure-awareness is worth building |
| Q4 | How many skills are only *described*? | Count gold surfaces; add a semantic matcher (config C) | Whether we need embeddings in v1 |
| Q5 | Can we say how sure we are? | Logistic scorer on a few features, reliability table (config D) | Whether a review band is possible |

**Hacky on purpose:** Q1 and Q2 are throwaway code. **Robust from the start:** the data generator and the eval harness, because every later decision depends on being able to measure.

**Out of the time box:** API, UI, LLM verifier, PyTorch, Transformers. They come after the design decision, not before.
