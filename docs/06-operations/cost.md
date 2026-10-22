# Cost

The pipeline runs in a few milliseconds on a CPU per profile; at enterprise volumes its compute cost rounds to zero next to the service's fixed hosting cost. The cost that scales with use is the optional LLM verifier, and it only sees the review band ([ADR-0002](../03-decisions/ADR-0002-llm-verifies-never-invents.md)).

## Verifier cost (estimate)

From `skilldraft/cost.py`, using the test set's mean job description length and the measured review band (<!--n:D.review_per_jd-->0.3<!--/n--> items per profile):

| | Value |
|---|---|
| Input tokens per verifier call | <!--n:cost.tokens_in-->675<!--/n--> |
| Output tokens per call (decisions + an assumed 300 thinking tokens) | <!--n:cost.tokens_out-->365<!--/n--> |
| Cost per call (claude-opus-5-5, Claude API list price $4 / $20 per million tokens) | <!--n:cost.per_call-->$0.0100<!--/n--> |
| Share of profiles that need a call | <!--n:cost.share-->30%<!--/n--> |
| Cost per profile | <!--n:cost.per_profile-->$0.0030<!--/n--> |
| Haldane's 1,400 roles | <!--n:cost.per_1400-->$4.20<!--/n--> |
| 100,000 profiles a year (a large customer base) | <!--n:cost.per_100k-->$300<!--/n--> |

**What this is not:** a measurement. Token counts are estimated at 4 characters per token and the thinking allowance is an assumption; the first live run replaces both with `usage` from the responses. Bedrock prices differ from the Claude API list and follow the customer's AWS agreement.

## What would change the picture

- A weaker embedder on real data grows the review band, and with it the verifier cost (linearly).
- Running the verifier on *every* profile instead of the band would multiply the cost by roughly 1 / <!--n:cost.share-->30%<!--/n--> and add latency to every request, for skills the scorer is already sure about.
- Person profiles (CVs) are not sent to an LLM at all in this design.
