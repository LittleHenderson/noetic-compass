"""Tests for the lightweight semantic reranker."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch.nn")

from cas_native.inference.semantic_reranker import (  # noqa: E402
    SemanticReranker,
    SemanticRerankerConfig,
    encode_text_batch,
    load_semantic_reranker,
    save_semantic_reranker,
    score_candidates,
)


class TinyTokenizer:
    PAD_ID = 0
    UNK_ID = 1
    BOS_ID = 2
    EOS_ID = 3
    vocab_size = 64

    def __init__(self) -> None:
        self._ids: dict[str, int] = {}

    def pad_id(self) -> int:
        return self.PAD_ID

    def encode(self, text: str, max_length: int = 512, *, add_special: bool = True) -> list[int]:
        ids: list[int] = []
        if add_special:
            ids.append(self.BOS_ID)
        for token in str(text).split():
            if token not in self._ids:
                self._ids[token] = 4 + (len(self._ids) % (self.vocab_size - 4))
            ids.append(self._ids[token])
        if add_special:
            ids.append(self.EOS_ID)
        return ids[:max_length]


def test_encode_text_batch_shapes() -> None:
    tokenizer = TinyTokenizer()
    device = torch.device("cpu")

    ids, mask = encode_text_batch(
        tokenizer,
        ["alpha beta", "gamma"],
        device=device,
        max_length=8,
        add_special=False,
    )

    assert ids.shape == mask.shape
    assert ids.shape[0] == 2
    assert mask.sum().item() == 3


def test_semantic_reranker_scores_candidates() -> None:
    tokenizer = TinyTokenizer()
    device = torch.device("cpu")
    model = SemanticReranker(SemanticRerankerConfig(vocab_size=tokenizer.vocab_size, d_model=16, hidden_dim=32)).to(device)

    scored = score_candidates(
        model,
        tokenizer,
        "[TASK_EXPR] [PROMPT] alpha [RESPONSE]",
        ["^2 in Noetics", "Product(Noetics, Domains)"],
        device=device,
        batch_size=1,
    )

    assert len(scored) == 2
    assert set(scored[0]) == {"candidate", "semantic_score"}
    assert scored[0]["semantic_score"] >= scored[1]["semantic_score"]


def test_semantic_reranker_save_load_roundtrip(tmp_path) -> None:
    try:
        (tmp_path / "probe.txt").write_text("ok", encoding="utf-8")
    except PermissionError:
        pytest.skip("workspace tmp path is not writable in this environment")

    tokenizer = TinyTokenizer()
    device = torch.device("cpu")
    model = SemanticReranker(SemanticRerankerConfig(vocab_size=tokenizer.vocab_size, d_model=16, hidden_dim=32)).to(device)
    path = save_semantic_reranker(tmp_path / "reranker.pt", model, metadata={"source": "test"})

    loaded, metadata = load_semantic_reranker(path, device=device)

    assert metadata["source"] == "test"
    assert loaded.config.vocab_size == tokenizer.vocab_size
