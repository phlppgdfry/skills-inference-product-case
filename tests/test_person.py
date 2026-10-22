import json
import unittest

from skilldraft import default_pipeline
from skilldraft.development import plan
from skilldraft.pii import mask
from skilldraft.taxonomy import Taxonomy
from skilldraft.train import load_cvs

CV = """Ann Peeters-Claes
Kerkstraat 12, 9000 Gent · 0478 12 34 56 · ann.peeters@mail.example
Born 03/04/1988
National register number: 88.04.03-123.45
Profile
Maintenance technician with 9 years of experience.
I would like to learn welding.
Experience
Electromechanic · Leiedal Metaal · 2018–2026
- Worked daily with PLC programming.
- Find the cause of faults in wiring, motors and control cabinets.
No hands-on experience with hydraulics yet.
Skills
TIA Portal, preventive maintenance
Languages
Dutch (native), French (good)
Interests
Cycling, cooking and photography."""


class PiiTest(unittest.TestCase):
    def test_masks_every_kind_and_keeps_length(self):
        masked, counts = mask(CV)
        self.assertEqual(len(masked), len(CV))
        for value in ("Ann Peeters-Claes", "Kerkstraat 12, 9000 Gent", "0478 12 34 56", "ann.peeters@mail.example", "03/04/1988", "88.04.03-123.45"):
            self.assertNotIn(value, masked)
        self.assertEqual(counts, {"address": 1, "birthdate": 1, "email": 1, "name": 1, "national_id": 1, "phone": 1})
        self.assertIn("Worked daily with PLC programming.", masked)

    def test_other_phone_formats(self):
        for phone in ("+32 9 123 45 67", "09/123.45.67", "+32 478 12 34 56"):
            self.assertNotIn(phone, mask(f"Bel me op {phone} na vijf uur.")[0], phone)

    def test_known_limit_year_only(self):
        # a year alone is not masked: it is too often a project or diploma year (EVIDENCE.md)
        self.assertIn("1988", mask("Geboren in 1988.")[0])


class PersonProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = default_pipeline(kind="cv")
        cls.out = cls.p.infer(CV)
        cls.ids = {s["id"]: s for s in cls.out["skills"]}

    def test_finds_held_skills(self):
        for sid in ("plc-programming", "preventive-maintenance", "dutch", "french"):
            self.assertEqual(self.ids[sid]["status"], "suggested", sid)
        self.assertTrue(all(s["importance"] == "held" for s in self.out["skills"]))

    def test_aspirations_and_negations_are_not_skills(self):
        for sid in ("welding", "hydraulics-pneumatics"):
            self.assertNotEqual(self.ids.get(sid, {}).get("status"), "suggested", sid)

    def test_no_personal_data_in_the_response(self):
        blob = json.dumps(self.out, ensure_ascii=False)
        for value in ("Ann", "Peeters", "Kerkstraat", "0478", "mail.example", "1988", "88.04.03"):
            self.assertNotIn(value, blob)
        self.assertEqual(sum(self.out["redactions"].values()), 6)

    def test_same_profile_for_another_name_and_age(self):
        other = CV.replace("Ann Peeters-Claes", "Fatima El Amrani").replace("ann.peeters", "fatima.elamrani").replace("1988", "1966")
        sig = lambda o: {s["id"]: (s["status"], s["confidence"]) for s in o["skills"]}  # noqa: E731
        self.assertEqual(sig(self.p.infer(other)), sig(self.out))

    def test_data_spans_are_masked(self):
        for cv in load_cvs("test")[:10]:
            masked = mask(cv["text"])[0]
            for g in cv["gold"]["pii"]:
                self.assertTrue(all(c in "• " for c in masked[g["start"]:g["end"]]), (cv["id"], g["kind"]))


class DevelopmentPlanTest(unittest.TestCase):
    def test_order_and_coverage(self):
        tax = Taxonomy.load()
        role = [{"id": "plc-programming", "importance": "required"}, {"id": "preventive-maintenance", "importance": "required"},
                {"id": "electrical-troubleshooting", "importance": "required"}, {"id": "welding", "importance": "preferred"},
                {"id": "sql", "importance": "required", "status": "needs_review"}]
        out = plan(role, ["plc-programming", "hydraulics-pneumatics"], tax)
        self.assertAlmostEqual(out["coverage"], 1 / 3.5, places=3)
        # required first; both required gaps sit next to a held skill, so alphabetical; then the preferred one
        self.assertEqual([g["id"] for g in out["gaps"]], ["electrical-troubleshooting", "preventive-maintenance", "welding"])
        self.assertEqual([c["id"] for c in out["gaps"][0]["close_to"]], ["hydraulics-pneumatics"])
        self.assertEqual([c["id"] for c in out["gaps"][1]["close_to"]], ["plc-programming"])
        self.assertEqual(out["gaps"][2]["importance"], "preferred")
        self.assertTrue(all(g["why"] == "new for you" for g in plan(role, ["sql"], tax)["gaps"]))
        self.assertNotIn("sql", [g["id"] for g in out["gaps"]])


if __name__ == "__main__":
    unittest.main()
