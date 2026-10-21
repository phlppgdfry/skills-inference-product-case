import unittest

from skilldraft.scorer import LogisticModel, loss, pick_thresholds, sigmoid, train_logistic


class ScorerTest(unittest.TestCase):
    def test_sigmoid_is_stable(self):
        self.assertAlmostEqual(sigmoid(0), 0.5)
        self.assertGreater(sigmoid(800), 0.999)
        self.assertLess(sigmoid(-800), 0.001)

    def test_training_lowers_the_loss_and_separates(self):
        X = [[0.0], [0.2], [0.4], [0.6], [0.8], [1.0]]
        y = [0, 0, 0, 1, 1, 1]
        w, b = train_logistic(X, y, l2=1e-3)
        self.assertLess(loss(w, b, X, y, 1e-3), loss([0.0], 0.0, X, y, 1e-3))
        m = LogisticModel(w, b, features=["x"])
        self.assertLess(m.predict([0.0]), 0.5)
        self.assertGreater(m.predict([1.0]), 0.5)

    def test_thresholds(self):
        probs = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        labels = [1, 1, 1, 0, 1, 0, 0, 0, 0]
        accept, review = pick_thresholds(probs, labels, target_precision=0.95, min_band_precision=0.25)
        self.assertEqual(accept, 0.7)
        self.assertEqual(review, 0.3)  # band 0.6..0.3 holds 1 real skill in 4; adding 0.2 drops below

    def test_version_follows_the_weights(self):
        a = LogisticModel([1.0, 2.0], 0.5, features=["a", "b"])
        b = LogisticModel.from_json(a.to_json())
        self.assertEqual(a.version, b.version)
        b.weights[0] = 1.5
        self.assertNotEqual(a.version, b.version)


if __name__ == "__main__":
    unittest.main()
