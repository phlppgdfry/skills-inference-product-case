"""SkillDraft: draft skill profiles from job descriptions, with evidence, for people to review."""

from __future__ import annotations

from pathlib import Path

__version__ = "1.0.0"


def make_embedder(name: str = "hashing"):
    if name in ("hashing", "hashing-v1"):
        from .embed import HashingEmbedder
        return HashingEmbedder()
    if name == "hf" or name.startswith("hf:"):
        from .adapters.hf_embedder import HFEmbedder
        return HFEmbedder(name.split(":", 1)[1]) if ":" in name else HFEmbedder()
    raise ValueError(f"unknown embedder {name!r}")


def default_pipeline(config: str = "D", embedder: str = "hashing", verifier=None, kind: str = "jd"):
    """The production pipeline: taxonomy + embedder + the trained scorer for that embedder."""
    from .pipeline import Pipeline
    from .scorer import LogisticModel
    from .taxonomy import Taxonomy
    from .train import model_path

    emb = make_embedder(embedder)
    model = None
    if config == "D":
        path = model_path(emb.name, kind)
        if not Path(path).exists():
            raise FileNotFoundError(f"{path} is missing: run python -m skilldraft train --embedder {embedder}")
        model = LogisticModel.load(path)
    return Pipeline(Taxonomy.load(), emb, model, config=config, verifier=verifier, kind=kind)
