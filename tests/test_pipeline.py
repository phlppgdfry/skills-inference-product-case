import unittest

from skilldraft import default_pipeline
from skilldraft.train import load_jds

JD = """Maintenance Technician
About Haldane
Our plants run on SAP.
Your role
You find the cause of faults in wiring, motors and control cabinets.
You will work daily with PLC programming.
Your profile
No prior experience with welding is required.
You speak fluent Dutch.
Nice to have
Experience with hydraulics is a plus.
What we offer
Training in lean manufacturing.
Questions? Contact Ann Peeters, our HR partner."""


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = default_pipeline()
        cls.out = cls.p.infer(JD)
        cls.by_id = {s["id"]: s for s in cls.out["skills"]}

    def test_finds_named_and_described_skills(self):
        for sid in ("plc-programming", "dutch", "hydraulics-pneumatics"):
            self.assertEqual(self.by_id[sid]["status"], "suggested", sid)
        self.assertIn("electrical-troubleshooting", self.by_id)  # only described, never named

    def test_ignores_company_talk_offer_and_negation(self):
        for sid in ("sap-logistics", "lean-manufacturing", "welding"):
            self.assertNotEqual(self.by_id.get(sid, {}).get("status"), "suggested", sid)

    def test_importance(self):
        self.assertEqual(self.by_id["hydraulics-pneumatics"]["importance"], "preferred")
        self.assertEqual(self.by_id["plc-programming"]["importance"], "required")

    def test_every_suggestion_points_at_the_text(self):
        for s in self.out["skills"]:
            self.assertIn(s["id"], self.p.taxonomy.by_id)
            self.assertTrue(s["evidence"])
            for e in s["evidence"]:
                self.assertEqual(JD[e["start"]:e["end"]], e["quote"])

    def test_deterministic(self):
        a, b = self.p.infer(JD), self.p.infer(JD)
        a["meta"].pop("latency_ms"), b["meta"].pop("latency_ms")
        self.assertEqual(a, b)

    def test_meta(self):
        m = self.out["meta"]
        self.assertEqual((m["config"], m["language"], m["embedder"]), ("D", "en", "hashing-v1"))
        self.assertTrue(m["model_version"].startswith("scorer-"))

    def test_flagged_sentence_is_never_evidence(self):
        base = self.p.infer(JD)
        changed = self.p.infer(JD.replace("Your role\n", "Your role\nJoin our young and dynamic team.\n"))
        sig = lambda o: {s["id"]: (s["status"], s["confidence"]) for s in o["skills"]}  # noqa: E731
        self.assertEqual(sig(base), sig(changed))
        self.assertEqual(changed["language_flags"][0]["category"], "age")

    def test_all_configs_run_on_the_data(self):
        jd = load_jds("test")[0]
        for c in "ABC":
            out = default_pipeline(c).infer(jd["text"])
            self.assertEqual(out["meta"]["config"], c)


if __name__ == "__main__":
    unittest.main()
