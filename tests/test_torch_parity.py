"""Runs where PyTorch is installed (CI job 'ml'); skipped on the stdlib-only job."""
import unittest

try:
    import torch  # noqa: F401
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "PyTorch not installed")
class TorchParityTest(unittest.TestCase):
    def test_torch_and_stdlib_reach_the_same_weights(self):
        from skilldraft.embed import HashingEmbedder
        from skilldraft.pipeline import Pipeline
        from skilldraft.scorer import LogisticModel
        from skilldraft.taxonomy import Taxonomy
        from skilldraft.train import examples, load_jds, model_path
        from training.train_torch import fit

        X, y, _ = examples(Pipeline(Taxonomy.load(), HashingEmbedder(), None, config="C"), load_jds("train"))
        w, b = fit(X, y)
        shipped = LogisticModel.load(model_path("hashing-v1"))
        for a, s in zip(w + [b], shipped.weights + [shipped.bias]):
            self.assertAlmostEqual(a, s, delta=0.02)


if __name__ == "__main__":
    unittest.main()
