import json
import unittest
from types import SimpleNamespace

from skilldraft import default_pipeline
from skilldraft.llm import FALLBACK_BETA, ClaudeVerifier, prompt
from skilldraft.train import load_jds


class FakeMessages:
    def __init__(self, reply, stop_reason="end_turn"):
        self.reply, self.stop_reason, self.calls = reply, stop_reason, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, model=kwargs["model"],
                               content=[SimpleNamespace(type="text", text=json.dumps(self.reply))])


def fake_client(reply, stop_reason="end_turn"):
    m = FakeMessages(reply, stop_reason)
    return SimpleNamespace(messages=m, beta=SimpleNamespace(messages=m)), m


TEXT = "Planner\nYou keep stock levels right so we never run out.\nOur plants run on SAP."
CANDS = [{"id": "inventory-management", "label": "Inventory management", "definition": "d", "evidence": []},
         {"id": "sap-logistics", "label": "SAP", "definition": "d", "evidence": []}]


class VerifierTest(unittest.TestCase):
    def test_request_on_the_claude_api(self):
        client, m = fake_client({"decisions": []})
        ClaudeVerifier(client).verify(TEXT, CANDS)
        req = m.calls[0]
        self.assertEqual(req["model"], "claude-opus-5-5")
        self.assertEqual((req["betas"], req["fallbacks"]), ([FALLBACK_BETA], "default"))
        self.assertEqual(req["system"], prompt())
        enum = req["output_config"]["format"]["schema"]["properties"]["decisions"]["items"]["properties"]["skill_id"]["enum"]
        self.assertEqual(enum, ["inventory-management", "sap-logistics"])
        self.assertIn("<job_description>\n" + TEXT, req["messages"][0]["content"])
        self.assertNotIn("thinking", req)
        self.assertNotIn("temperature", req)

    def test_request_on_bedrock(self):
        client, m = fake_client({"decisions": []})
        ClaudeVerifier(client, platform="bedrock").verify(TEXT, CANDS)
        req = m.calls[0]
        self.assertEqual(req["model"], "anthropic.claude-opus-5-5")
        self.assertNotIn("fallbacks", req)

    def test_grounded_answers_only(self):
        client, _ = fake_client({"decisions": [
            {"skill_id": "inventory-management", "present": True, "quote": "You keep stock levels right", "reason": "r"},
            {"skill_id": "sap-logistics", "present": True, "quote": "You must know SAP", "reason": "invented quote"},
        ]})
        out = ClaudeVerifier(client).verify(TEXT, CANDS)
        self.assertTrue(out["inventory-management"]["present"])
        self.assertNotIn("sap-logistics", out)

    def test_refusal_and_garbage_leave_everything_for_review(self):
        for client, _ in (fake_client({"decisions": []}, "refusal"), fake_client("not json")):
            self.assertEqual(ClaudeVerifier(client).verify(TEXT, CANDS), {})

    def test_pipeline_promotes_or_drops_review_items(self):
        base = default_pipeline()
        text, review = next((jd["text"], r) for jd in load_jds("test")
                            if len(r := [s for s in base.infer(jd["text"])["skills"] if s["status"] == "needs_review"]) >= 2)
        quote = review[0]["evidence"][0]["quote"]
        decisions = [{"skill_id": s["id"], "present": i == 0, "quote": quote if i == 0 else "",
                      "reason": "r"} for i, s in enumerate(review)]
        client, _ = fake_client({"decisions": decisions})
        out = default_pipeline(verifier=ClaudeVerifier(client)).infer(text)
        by_id = {s["id"]: s for s in out["skills"]}
        self.assertEqual(by_id[review[0]["id"]]["status"], "suggested")
        self.assertEqual(by_id[review[0]["id"]]["verified_by"], "claude-opus-5-5")
        for s in review[1:]:
            self.assertNotIn(s["id"], by_id)


if __name__ == "__main__":
    unittest.main()
