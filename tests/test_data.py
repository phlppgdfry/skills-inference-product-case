import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("make_data", ROOT / "scripts" / "make_data.py")
        cls.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gen)
        cls.jds = [json.loads(line) for line in (ROOT / "data" / "job_descriptions.jsonl").read_text().splitlines()]

    def test_files_are_what_the_generator_produces(self):
        for name, content in self.gen.build().items():
            self.assertEqual((ROOT / "data" / name).read_text(encoding="utf-8"), content, name)

    def test_splits(self):
        sizes = {s: sum(j["split"] == s for j in self.jds) for s in ("train", "dev", "test")}
        self.assertEqual(sizes, {"train": 150, "dev": 50, "test": 100})

    def test_gold_spans_and_distractors_are_consistent(self):
        tax_ids = {s["id"] for s in json.loads((ROOT / "data" / "taxonomy.json").read_text())["skills"]}
        for j in self.jds:
            gold = {g["id"] for g in j["gold"]["skills"]}
            self.assertLessEqual(gold, tax_ids)
            for g in j["gold"]["skills"]:
                for a, b in g["spans"]:
                    self.assertTrue(0 <= a < b <= len(j["text"]))
            for d in j["gold"]["distractors"]:
                self.assertNotIn(d["id"], gold, j["id"])

    def test_paraphrases_never_reach_the_taxonomy(self):
        tax = (ROOT / "data" / "taxonomy.json").read_text()
        for row in self.gen.SKILLS:
            for p in row[7] + row[8]:
                self.assertNotIn(p, tax)


if __name__ == "__main__":
    unittest.main()
