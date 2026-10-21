# ADR-0006: Claude through Amazon Bedrock for customer traffic

**Status:** Accepted

## Context
Haldane's security team requires that job descriptions stay in AWS in the EU, under their existing AWS agreements. Orveda's internal tooling uses the Claude API directly.

## Options
1. **Claude API** for everything.
2. **Amazon Bedrock** (eu-central-1) for customer traffic; Claude API for internal experiments.
3. **Self-hosted open model.** No dependency on a vendor, but we would own GPU operations and a weaker model for a narrow task.

## Decision
Option 2. One verifier class, two platforms: `anthropic.AnthropicBedrockMantle(aws_region=...)` with model `anthropic.claude-opus-5-5`, or `anthropic.Anthropic()` with `claude-opus-5-5`. Same request body. The server-side refusal fallback exists only on the Claude API; on Bedrock a refusal leaves the item for review, which is safe.

## Consequences
- IAM, region and model access are configured in the customer's AWS account; the service needs `bedrock:InvokeModel` on one model only.
- Feature differences between platforms are handled in one place (`ClaudeVerifier.request`) and tested with a fake client.
- Effort is set to `low`: the task is a short classification with a quote.

## How we would know it was wrong
Latency or cost per verified item on Bedrock is far from the Claude API for the same request, or a needed feature lags on Bedrock.

## When to revisit
When the review band grows enough that cost matters: measure a smaller model on the dev review band before changing the default.
