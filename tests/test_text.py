import unittest

from skilldraft.text import fold, negated_at, segment, tokenize


class TextTest(unittest.TestCase):
    def test_fold_keeps_length(self):
        for s in ["Kwaliteitscoördinator", "hygiëne", "Ça va", "ﬁle"]:
            self.assertEqual(len(fold(s)), len(s))
        self.assertEqual(fold("Coördinator"), "coordinator")

    def test_tokens_keep_offsets(self):
        text = "Ervaring met CI/CD en Node.js"
        for t in tokenize(fold(text)):
            self.assertEqual(fold(text)[t.start:t.end], t.text)

    def test_sections_from_headings(self):
        text = "Data Engineer\nAbout Haldane\nWe make things.\nYour profile\nYou know SQL.\nNice to have\nPython is a plus.\nWhat we offer\nA car."
        sections = {s.text: s.section for s in segment(text)[0] if not s.heading}
        self.assertEqual(sections["Data Engineer"], "title")
        self.assertEqual(sections["We make things."], "about")
        self.assertEqual(sections["You know SQL."], "req")
        self.assertEqual(sections["Python is a plus."], "pref")
        self.assertEqual(sections["A car."], "offer")
        self.assertTrue(segment(text)[1])

    def test_no_headings(self):
        sentences, has = segment("Planner\nYou plan orders. You talk to sales.")
        self.assertFalse(has)
        self.assertEqual([s.section for s in sentences], ["title", "unknown", "unknown"])

    def test_long_line_with_keyword_is_not_a_heading(self):
        sentences, has = segment("Planner\nAbout the job: you plan orders for three plants every week.")
        self.assertFalse(has)

    def test_negation_window(self):
        for text, negated in [("No prior experience with Python is required.", True),
                              ("Experience with Python is not necessary.", True),
                              ("Je hoeft Python niet te kennen.", True),
                              ("You have solid Python experience and no fear of change.", False)]:
            toks = tokenize(fold(text))
            i = [t.text for t in toks].index("python")
            self.assertEqual(negated_at(toks, i, i), negated, text)

    def test_cues(self):
        s = {x.text: x for x in segment("Planner\nKnowledge of SAP is a plus. Training in lean. Our plants run on SAP. Questions? Contact Ann.")[0]}
        self.assertTrue(s["Knowledge of SAP is a plus."].preferred_cue)
        self.assertTrue(s["Training in lean."].offer_cue)
        self.assertEqual(s["Our plants run on SAP."].voice, "we")
        self.assertTrue(s["Contact Ann."].contact)


if __name__ == "__main__":
    unittest.main()
