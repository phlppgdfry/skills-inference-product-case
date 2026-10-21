"""LLM verifier for the review band (ADR-0002).

The LLM never proposes skills. It only judges candidates that the scorer already found but
was unsure about, and it can only answer with ids from that list (a JSON schema enum). Its
quote must appear in the job description, or the answer is ignored. If anything goes wrong
(refusal, truncation, invalid quote, network), the skill simply stays in the review band
for a person: the failure mode is "more work for HR", never "a skill nobody asked for".

Two ways to reach Claude, same request body:
    platform="anthropic"  anthropic.Anthropic()                       model "claude-opus-5-5"
    platform="bedrock"    anthropic.AnthropicBedrockMantle(aws_region) model "anthropic.claude-opus-5-5"

On the Claude API the request also opts into server-side refusal fallbacks
(fallbacks="default"). Bedrock does not offer that parameter; a refusal there leaves the
skills for review, which is the safe outcome anyway.

Not run in CI against a live model; tests/test_llm.py checks the request and the parsing
with a fake client (EVIDENCE.md).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "verify_v1.md"
PROMPT_VERSION = "verify_v1"
MODELS = {"anthropic": "claude-opus-5-5", "bedrock": "anthropic.claude-opus-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def prompt_hash() -> str:
    return hashlib.sha256(prompt().encode("utf-8")).hexdigest()


def schema(ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "enum": ids},
                        "present": {"type": "boolean"},
                        "quote": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["skill_id", "present", "quote", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["decisions"],
        "additionalProperties": False,
    }


def user_message(text: str, candidates: list[dict]) -> str:
    lines = [f"- {c['id']}: {c['label']}. {c['definition']}" for c in candidates]
    return ("<candidates>\n" + "\n".join(lines) + "\n</candidates>\n\n"
            "<job_description>\n" + text + "\n</job_description>")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


class ClaudeVerifier:
    def __init__(self, client=None, platform: str = "anthropic", model: str | None = None,
                 aws_region: str | None = None, effort: str = "low"):
        if platform not in MODELS:
            raise ValueError("platform must be 'anthropic' or 'bedrock'")
        self.platform = platform
        self.model = model or os.environ.get("SKILLDRAFT_LLM_MODEL") or MODELS[platform]
        self.effort = effort
        if client is None:
            import anthropic
            client = (anthropic.AnthropicBedrockMantle(aws_region=aws_region or os.environ.get("AWS_REGION", "eu-central-1"))
                      if platform == "bedrock" else anthropic.Anthropic())
        self.client = client

    def request(self, text: str, candidates: list[dict]) -> dict:
        body = {
            "model": self.model,
            "max_tokens": 4000,
            "system": prompt(),
            "messages": [{"role": "user", "content": user_message(text, candidates)}],
            "output_config": {"effort": self.effort,
                              "format": {"type": "json_schema", "schema": schema([c["id"] for c in candidates])}},
        }
        if self.platform == "anthropic":
            body |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return body

    def verify(self, text: str, candidates: list[dict]) -> dict[str, dict]:
        body = self.request(text, candidates)
        try:
            create = self.client.beta.messages.create if self.platform == "anthropic" else self.client.messages.create
            response = create(**body)
        except Exception:  # network, rate limit, auth: the skills stay for review
            return {}
        if response.stop_reason in ("refusal", "max_tokens"):
            return {}
        raw = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            decisions = json.loads(raw)["decisions"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return {}
        ids = {c["id"] for c in candidates}
        haystack = _norm(text)
        model = getattr(response, "model", self.model)
        out: dict[str, dict] = {}
        for d in decisions:
            sid = d.get("skill_id")
            if sid not in ids or sid in out:
                continue
            quote = _norm(d.get("quote", ""))
            if d.get("present") and (len(quote) < 3 or quote not in haystack):
                continue  # an ungrounded "yes" is ignored, not trusted
            out[sid] = {"present": bool(d.get("present")), "quote": quote, "reason": d.get("reason", ""),
                        "model": model, "prompt": PROMPT_VERSION}
        return out
