# ADR-0005: Standard-library core, ML as optional adapters

**Status:** Accepted

## Context
The service must start in milliseconds, run in CI without GPUs or downloads, and run in a browser for the demo. The team's ML stack (PyTorch, Transformers, an LLM) must still be first-class.

## Decision
- Core on the Python standard library: text, taxonomy, hashing embedder, scorer, API, evals.
- `Embedder` interface with a Transformers adapter (`adapters/hf_embedder.py`, mean pooling, L2-normalised).
- Scorer trainable with the stdlib or PyTorch (`training/train_torch.py`, L-BFGS on the same objective); CI checks they agree within 0.02 per weight.
- LLM verifier through the official `anthropic` SDK, optional.
- A JavaScript port of the core with a parity test, for the browser demo.

## Consequences
- `pip install .` has no dependencies; `pip install ".[ml]"` and `".[llm]"` add the heavy parts.
- Two implementations (Python, JS) must stay in sync; `tests/js/parity.mjs` fails CI if one profile differs.
- The hashing embedder is a weak stand-in for a real encoder; the HF eval keeps that honest.

## How we would know it was wrong
Product needs force the core to depend on a heavy library anyway (e.g. a trained encoder becomes mandatory). Then the default flips and the hashing embedder becomes the fallback.

## When to revisit
When a skills-specific encoder is trained (see tech design, alternatives).
