"""A multilingual sentence encoder from Hugging Face Transformers, behind the Embedder interface.

    pip install ".[ml]"
    python -m skilldraft train --embedder hf
    python -m evals.run --embedder hf

Mean pooling over the last hidden state with the attention mask, then L2 normalisation, so
cosine similarity is a dot product. The default model is small (118M parameters), covers
Dutch and English, and runs on a laptop CPU.
"""

from __future__ import annotations

from collections.abc import Sequence

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class HFEmbedder:
    # Cosine similarities from a trained encoder sit higher than from the hashing embedder;
    # this floor was picked on the dev split by the same rule (evals/reports/sweep.<name>.json).
    min_similarity = 0.40

    def __init__(self, model_name: str = DEFAULT_MODEL, batch_size: int = 32, device: str | None = None):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.model_name = model_name
        self.name = "hf-" + model_name.split("/")[-1]
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device).eval()
        self._cache: dict[str, list[float]] = {}

    def fit(self, skill_texts: Sequence[str]) -> None:
        """Nothing to fit: the encoder is pretrained. Kept for the interface."""

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        torch = self.torch
        for i in range(0, len(missing), self.batch_size):
            batch = missing[i:i + self.batch_size]
            enc = self.tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt").to(self.device)
            with torch.no_grad():
                hidden = self.model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            for text, vec in zip(batch, pooled.cpu().tolist()):
                self._cache[text] = vec
        return [self._cache[t] for t in texts]

    def similarity(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))
