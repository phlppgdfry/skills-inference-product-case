import unittest

from skilldraft.embed import HashingEmbedder, fnv1a


class EmbedTest(unittest.TestCase):
    def test_fnv1a_reference_values(self):
        # FNV-1a 32-bit test vectors; the JavaScript port must produce the same
        self.assertEqual(fnv1a(""), 0x811C9DC5)
        self.assertEqual(fnv1a("a"), 0xE40C292C)
        self.assertEqual(fnv1a("foobar"), 0xBF9CF968)

    def test_similarity(self):
        e = HashingEmbedder()
        e.fit(["warehouse pallets forklift", "python code tests"])
        a, b, c = e.encode(["move pallets in the warehouse", "pallets in a warehouse", "write python tests"])
        self.assertAlmostEqual(e.similarity(a, a), 1.0, places=6)
        self.assertGreater(e.similarity(a, b), e.similarity(a, c))
        self.assertEqual(e.encode(["de het een"])[0], {})


if __name__ == "__main__":
    unittest.main()
