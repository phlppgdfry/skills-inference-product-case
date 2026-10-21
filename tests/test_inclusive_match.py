import unittest

from skilldraft.inclusive import check
from skilldraft.match import ndcg_at_k, rank


class InclusiveTest(unittest.TestCase):
    def test_flags_with_offsets(self):
        text = "Join our young and dynamic team. He will report to Ann. Je bent maximaal 30 jaar."
        flags = check(text)
        self.assertEqual([f["category"] for f in flags], ["age", "gender", "age"])
        for f in flags:
            self.assertEqual(text[f["start"]:f["end"]], f["quote"])
        self.assertEqual(flags[0]["quote"], "young and dynamic")

    def test_no_false_alarm_on_neutral_text(self):
        self.assertEqual(check("You lead a team that moves fast. The help desk answers."), [])


class MatchTest(unittest.TestCase):
    people = [{"id": "a", "skills": ["x", "y"]}, {"id": "b", "skills": ["x"]}, {"id": "c", "skills": []}]

    def test_rank_weights_required_over_preferred(self):
        role = [{"id": "x", "importance": "required"}, {"id": "y", "importance": "preferred"}]
        r = rank(role, self.people, use_confidence=False, related={"y": ["x"]})
        self.assertEqual([p["person_id"] for p in r], ["a", "b", "c"])
        self.assertAlmostEqual(r[1]["score"], 1 / 1.5, places=4)
        self.assertEqual(r[1]["learnable"], ["y"])

    def test_review_items_do_not_rank_people(self):
        role = [{"id": "x", "importance": "required", "status": "needs_review", "confidence": 0.3}]
        self.assertTrue(all(p["score"] == 0 for p in rank(role, self.people)))

    def test_ndcg(self):
        rel = {"a": 1.0, "b": 0.5, "c": 0.0}
        self.assertAlmostEqual(ndcg_at_k(["a", "b", "c"], rel, 3), 1.0)
        self.assertLess(ndcg_at_k(["c", "b", "a"], rel, 3), 1.0)


if __name__ == "__main__":
    unittest.main()
