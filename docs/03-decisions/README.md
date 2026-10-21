# Decisions

| ADR | Decision | Status |
|---|---|---|
| [0001](ADR-0001-taxonomy-grounded-output.md) | Output only taxonomy skills, never free text | Accepted |
| [0002](ADR-0002-llm-verifies-never-invents.md) | The LLM judges uncertain candidates; it never proposes skills | Accepted |
| [0003](ADR-0003-calibrated-score-and-review-band.md) | A calibrated score with an accept threshold and a review band | Accepted |
| [0004](ADR-0004-evidence-or-nothing.md) | No skill without the words it came from | Accepted |
| [0005](ADR-0005-stdlib-core-optional-ml.md) | Standard-library core; PyTorch, Transformers and the LLM as optional adapters | Accepted |
| [0006](ADR-0006-bedrock-for-eu-customers.md) | Claude through Amazon Bedrock (EU region) for customer traffic | Accepted |
| [0007](ADR-0007-evals-are-the-release-gate.md) | Evals are the release gate; docs quote generated numbers | Accepted |
| [0008](ADR-0008-people-decide.md) | People decide: profiles are drafts, matches are lists | Accepted |
| [0009](ADR-0009-personal-traits-are-never-evidence.md) | Sentences about age, gender or origin are never evidence | Accepted |

Format: context, options, decision, consequences, how we would know it was wrong, when to revisit.
