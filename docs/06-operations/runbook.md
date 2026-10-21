# Runbook

## Service does not start
- `models/scorer.<embedder>.json is missing` → run `python -m skilldraft train` (or deploy the model file with the release).
- With `SKILLDRAFT_VERIFIER=bedrock`: the `anthropic` package and AWS credentials must be present; the service still starts without them, but the review band stays for people.

## 401 for every request
`SKILLDRAFT_API_KEYS` is empty in a non-dev environment. That is intended: no keys, no access.

## Latency p95 above 250 ms
1. Check `skilldraft_http_request_duration_ms` per route: profiles or matches?
2. Profiles: is the Transformers embedder on CPU? Expect ~11 ms p50 on a laptop CPU vs ~5 ms for hashing; batch or move to GPU.
3. Matches: people lists close to the 5,000 limit; page on the client side.

## Reject rate up
1. Which family and language? (feedback rows carry the skill id; join to the taxonomy family.)
2. Pull 10 rejected suggestions with their request ids and look at the evidence the reviewer saw.
3. If it is one alias: mark it ambiguous in the taxonomy, add a generated case, run `scripts/build.py`, release.
4. If it is broad: raise `accept_at` temporarily (model file), then retrain with the feedback.

## Uncovered requirements up
Export the sentences (customer-side; the service does not store them), cluster them, propose taxonomy aliases or skills, release a new taxonomy version through the eval gate.

## Verifier misbehaves
Turn it off (`SKILLDRAFT_VERIFIER` unset). Nothing breaks: items stay in the review band.

## A customer asks "why did it suggest X?"
The profile they saved has the evidence span, `model_version` and `taxonomy_version`. Re-run the same text against that model version; the pipeline is deterministic.
