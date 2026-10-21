"""Fit the scorer with PyTorch instead of the standard-library trainer.

    pip install ".[ml]"
    python -m training.train_torch            # print the weights next to the shipped model
    python -m training.train_torch --check    # exit 1 if they differ by more than 0.02

Same features, same objective (mean binary cross-entropy + (l2/2)·||w||², bias not
penalised), different optimiser (L-BFGS). Because the problem is convex, both must land on
the same weights. The point is not speed: it shows the production model can move to a
PyTorch training stack (a GPU, a bigger feature set, a neural head) without changing what
it means, and that the two implementations check each other.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402

from skilldraft.embed import HashingEmbedder  # noqa: E402
from skilldraft.pipeline import Pipeline  # noqa: E402
from skilldraft.scorer import FEATURES, LogisticModel  # noqa: E402
from skilldraft.taxonomy import Taxonomy  # noqa: E402
from skilldraft.train import L2, examples, load_jds, model_path  # noqa: E402


class Scorer(torch.nn.Module):
    def __init__(self, n_features: int):
        super().__init__()
        self.linear = torch.nn.Linear(n_features, 1, dtype=torch.float64)
        torch.nn.init.zeros_(self.linear.weight)
        torch.nn.init.zeros_(self.linear.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x).squeeze(-1)  # logits; the sigmoid lives in the loss


def fit(X: list[list[float]], y: list[int], l2: float = L2, steps: int = 200) -> tuple[list[float], float]:
    xt = torch.tensor(X, dtype=torch.float64)
    yt = torch.tensor(y, dtype=torch.float64)
    model = Scorer(xt.shape[1])
    bce = torch.nn.BCEWithLogitsLoss()
    opt = torch.optim.LBFGS(model.parameters(), lr=1.0, max_iter=steps, tolerance_grad=1e-10,
                            tolerance_change=1e-12, history_size=20, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = bce(model(xt), yt) + 0.5 * l2 * model.linear.weight.pow(2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    return model.linear.weight.detach().squeeze(0).tolist(), float(model.linear.bias.detach())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tolerance", type=float, default=0.02)
    args = ap.parse_args()
    pipe = Pipeline(Taxonomy.load(), HashingEmbedder(), None, config="C")
    X, y, _ = examples(pipe, load_jds("train"))
    w, b = fit(X, y)
    shipped = LogisticModel.load(model_path("hashing-v1"))
    worst = max([abs(b - shipped.bias)] + [abs(a - s) for a, s in zip(w, shipped.weights)])
    print(f"{len(X)} training candidates, torch {torch.__version__}")
    print(f"{'feature':<16} {'torch':>9} {'stdlib':>9}")
    for name, a, s in zip(FEATURES + ["bias"], w + [b], shipped.weights + [shipped.bias]):
        print(f"{name:<16} {a:>9.4f} {s:>9.4f}")
    print(f"largest difference: {worst:.5f}")
    if args.check and worst > args.tolerance:
        print("parity check FAILED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
