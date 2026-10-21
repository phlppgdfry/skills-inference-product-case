import unittest

from skilldraft.taxonomy import Taxonomy
from skilldraft.text import fold, tokenize


class TaxonomyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Taxonomy.load()

    def test_every_alias_belongs_to_one_skill(self):
        owner = {}
        for s in self.t.skills:
            for a in s["aliases"]:
                key = tuple(tok.text for tok in tokenize(fold(a["text"])))
                self.assertIn(owner.setdefault(key, s["id"]), (s["id"],), f"{a['text']!r} is used by two skills")

    def test_every_skill_is_defined_in_both_languages(self):
        for s in self.t.skills:
            self.assertTrue(s["definition"]["en"] and s["definition"]["nl"], s["id"])
            for r in s["related"]:
                self.assertIn(r, self.t.by_id)

    def test_longest_match_wins(self):
        toks = tokenize(fold("Experience with SAP SuccessFactors and SAP."))
        hits = self.t.match(toks)
        self.assertEqual([(h.skill_id, h.ambiguous) for h in hits], [("hris", False), ("sap-logistics", True)])

    def test_java_is_not_javascript(self):
        ids = [h.skill_id for h in self.t.match(tokenize(fold("Java and JavaScript")))]
        self.assertEqual(ids, ["java", "javascript"])

    def test_word_boundaries(self):
        self.assertEqual(self.t.match(tokenize(fold("excellent communication"))), [])

    def test_search(self):
        self.assertEqual(self.t.search("k8s")[0]["id"], "kubernetes")
        self.assertEqual(self.t.search("heftruck")[0]["id"], "forklift")


if __name__ == "__main__":
    unittest.main()
