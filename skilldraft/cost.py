"""What SkillDraft costs to run, per profile and per customer.

The pipeline itself runs in milliseconds on a CPU; its cost is a rounding error. The cost
that scales is the optional LLM verifier, which only sees the review band. Prices are the
Claude API list prices for claude-opus-5-5 (USD per million tokens, October 2026); Bedrock
has its own price list, so the Bedrock column is a placeholder until the customer's
contract prices are known. Token counts are estimated at 4 characters per token; the real
count comes from `usage` in the API response once the verifier runs live (EVIDENCE.md).
"""

from __future__ import annotations

PRICE_PER_MTOK = {"claude-opus-5-5": {"input": 4.00, "output": 20.00}}
CHARS_PER_TOKEN = 4
PROMPT_TOKENS = 450          # prompts/verify_v1.md plus the candidate list framing
TOKENS_PER_CANDIDATE_IN = 40  # id, label and definition
TOKENS_PER_CANDIDATE_OUT = 45 # one decision with a quote and a reason
THINKING_TOKENS = 300         # assumption: Opus 5.5 always thinks a little, even at effort "low"; billed as output


def verifier_call_tokens(text_chars: int, candidates: int) -> tuple[int, int]:
    tokens_in = PROMPT_TOKENS + text_chars // CHARS_PER_TOKEN + candidates * TOKENS_PER_CANDIDATE_IN
    return tokens_in, candidates * TOKENS_PER_CANDIDATE_OUT + 20 + THINKING_TOKENS


def cost_usd(tokens_in: int, tokens_out: int, model: str = "claude-opus-5-5") -> float:
    p = PRICE_PER_MTOK[model]
    return tokens_in / 1e6 * p["input"] + tokens_out / 1e6 * p["output"]


def per_profile(mean_chars: float, review_items_per_profile: float, model: str = "claude-opus-5-5") -> dict:
    """Expected verifier cost per profile: a call only when the band is not empty. Upper bound:
    assume every profile with a review item has the average number of items in one call."""
    share_with_call = min(1.0, review_items_per_profile)
    items = review_items_per_profile / share_with_call if share_with_call else 0.0
    tin, tout = verifier_call_tokens(int(mean_chars), max(1, round(items)))
    per_call = cost_usd(tin, tout, model)
    return {"tokens_in_per_call": tin, "tokens_out_per_call": tout, "usd_per_call": round(per_call, 5),
            "share_of_profiles_with_a_call": round(share_with_call, 3), "usd_per_profile": round(per_call * share_with_call, 5)}
