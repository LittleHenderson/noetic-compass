"""Inference wrapper for the CAS-Native K=9 structured-token baseline.

Loads the v77fix 20-epoch GPU checkpoint plus its persisted
``structured_token_vocab.json`` and exposes a single callable:

    predictor = load_predictor(run_dir)
    prediction = predictor("I can't stand it when people interrupt me")

The prediction shape mirrors the per-sample ``samples[i]["prediction"]`` block
that ``train_structured_prediction.evaluate_structured_token_prediction``
produces during eval, so it can be consumed directly by the CAS expression
renderer.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[2]
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))


import torch  # noqa: E402

from cas_native.model.structured_prediction import (  # noqa: E402
    AUTHORITY_LABELS,
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
    StructuredPredictionHead,
    TRANSITION_KIND_LABELS,
    TURN_TYPE_LABELS,
)
from cas_native.model.structured_token_embedding import (  # noqa: E402
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
)
from cas_native.tokenizer.assembler import tokenize  # noqa: E402
from cas_native.tokenizer.lexicon.schema import CASLexicon, load_seed_lexicon  # noqa: E402
from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary  # noqa: E402
from cas_native.training.structured_token_adapter import (  # noqa: E402
    tokens_to_structured_token_batch,
)


DEFAULT_VOCAB_FILENAME = "structured_token_vocab.json"
DEFAULT_CHECKPOINT_FILENAME = "best_structured_token_model.pt"
DEFAULT_MANIFEST_FILENAME = "manifest.json"


class Predictor:
    """Stateful wrapper around the K=9 structured-token model.

    The model and vocabulary are loaded once. Each ``__call__`` is stateless
    after that: tokenize the prompt, build a single-row batch, run the model,
    decode the 12 head outputs into a prediction dict.
    """

    def __init__(
        self,
        model: StructuredTokenStructuredPredictor,
        vocabulary: StructuredTokenVocabulary,
        lexicon: CASLexicon,
        device: torch.device,
        max_length: int = 256,
    ) -> None:
        self.model = model
        self.vocabulary = vocabulary
        self.lexicon = lexicon
        self.device = device
        self.max_length = max_length
        self.model.eval()

    @torch.no_grad()
    def __call__(self, text: str) -> dict[str, Any]:
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        token_sequence = tokenize(text, lexicon=self.lexicon)
        if not token_sequence:
            # Empty input still needs to produce a tensor row; tokens_to_*
            # rejects empty sequences. Use a single-pass fallback so the
            # call surface stays uniform.
            token_sequence = tokenize(" ", lexicon=self.lexicon)
        batch = tokens_to_structured_token_batch(
            [token_sequence],
            self.vocabulary,
            max_length=self.max_length,
            device=self.device,
        )
        outputs = self.model(batch)
        return _decode_outputs(outputs)


def load_predictor(
    run_dir: str | Path,
    *,
    device: str = "cpu",
    max_length: int | None = None,
) -> Predictor:
    """Load checkpoint, vocabulary, and manifest from ``run_dir``.

    Args:
        run_dir: directory containing ``best_structured_token_model.pt``,
            ``structured_token_vocab.json``, and ``manifest.json``.
        device: torch device string (``"cpu"`` or ``"cuda"``).
        max_length: override max sequence length. Defaults to the value in
            ``manifest.json["config"]["max_length"]`` when present, else 256.

    Returns:
        A ``Predictor`` ready to map English strings to prediction dicts.
    """

    run_path = Path(run_dir)
    if not run_path.exists():
        raise FileNotFoundError(f"run_dir does not exist: {run_path}")

    manifest_path = run_path / DEFAULT_MANIFEST_FILENAME
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = dict(manifest.get("config") or {})

    vocab_path = run_path / DEFAULT_VOCAB_FILENAME
    if not vocab_path.exists():
        raise FileNotFoundError(
            f"vocabulary artifact not found: {vocab_path}; "
            "this checkpoint cannot be safely loaded without its persisted "
            "structured_token_vocab.json (model would index into garbage)."
        )
    vocabulary = StructuredTokenVocabulary.load(vocab_path)

    checkpoint_path = run_path / DEFAULT_CHECKPOINT_FILENAME
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint_path}")

    torch_device = torch.device(device)

    d_model = int(config.get("d_model", 128))
    bottleneck_dim = int(config.get("bottleneck_dim", 64))
    embedding_dropout = float(config.get("embedding_dropout", 0.0))
    resolved_max_length = int(
        max_length if max_length is not None else config.get("max_length", 256)
    )

    expected_vocab_size = int(config.get("vocab_size", len(vocabulary)))
    if expected_vocab_size != len(vocabulary):
        raise ValueError(
            f"manifest vocab_size={expected_vocab_size} does not match "
            f"loaded vocabulary len={len(vocabulary)}; refusing to proceed "
            "rather than mis-index the embedding table."
        )

    embedding = StructuredTokenEmbedding(
        vocab_size=len(vocabulary),
        d_model=d_model,
        dropout=embedding_dropout,
    )
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)
    model = StructuredTokenStructuredPredictor(embedding, head)

    state_dict = torch.load(
        str(checkpoint_path),
        map_location=torch_device,
        weights_only=False,
    )
    if isinstance(state_dict, dict) and "model_state_dict" in state_dict:
        state_dict = state_dict["model_state_dict"]
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing:
        raise RuntimeError(
            f"checkpoint is missing {len(missing)} parameter tensors required by "
            f"the model graph; first few: {list(missing)[:5]}"
        )
    if unexpected:
        # Unexpected keys are not fatal but we surface them.
        sys.stderr.write(
            f"[predict_cas] WARNING: ignoring {len(unexpected)} unexpected "
            f"checkpoint keys (first few: {list(unexpected)[:5]})\n"
        )

    model.to(torch_device)
    model.eval()

    lexicon = load_seed_lexicon()

    return Predictor(
        model=model,
        vocabulary=vocabulary,
        lexicon=lexicon,
        device=torch_device,
        max_length=resolved_max_length,
    )


def _decode_outputs(outputs: dict[str, torch.Tensor]) -> dict[str, Any]:
    """Decode a batch-of-1 head output dict into a prediction dict."""

    def _scalar(key: str, labels: tuple[Any, ...]) -> Any:
        idx = int(outputs[key][0].argmax().item())
        return labels[idx]

    register_probs = torch.sigmoid(outputs["register_logits"][0])
    registers = [
        REGISTER_LABELS[i]
        for i, value in enumerate(register_probs.tolist())
        if value >= 0.5
    ]

    meta_relation_probs = torch.sigmoid(outputs["meta_relation_logits"][0])
    meta_relations = [
        META_RELATION_LABELS[i]
        for i, value in enumerate(meta_relation_probs.tolist())
        if value >= 0.5
    ]

    has_omega = bool(int(outputs["omega_logits"][0].argmax().item()))
    has_meta_logic = bool(int(outputs["meta_logic_logits"][0].argmax().item()))

    return {
        "turn_type": _scalar("turn_type_logits", TURN_TYPE_LABELS),
        "expression_family": _scalar(
            "expression_family_logits", EXPRESSION_FAMILY_LABELS
        ),
        "transition_kind": _scalar(
            "transition_kind_logits", TRANSITION_KIND_LABELS
        ),
        "noetic": int(outputs["noetic_logits"][0].argmax().item()),
        "domain": _scalar("domain_logits", DOMAIN_LABELS),
        "drive": _scalar("drive_logits", DRIVE_LABELS),
        "register_mode": _scalar(
            "register_mode_logits", REGISTER_MODE_LABELS
        ),
        "registers": registers,
        "authority": _scalar("authority_logits", AUTHORITY_LABELS),
        "has_omega": has_omega,
        "has_meta_logic": has_meta_logic,
        "meta_relations": meta_relations,
    }


__all__ = ["Predictor", "load_predictor"]


if __name__ == "__main__":
    # parents[0]=inference, parents[1]=cas-native, parents[2]=noetic-compass.
    # Training runs live under cas-native/training/runs/, hence parents[1].
    run_dir = (
        Path(__file__).resolve().parents[1]
        / "training"
        / "runs"
        / "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
    )
    predictor = load_predictor(run_dir)
    examples = [
        "I can't stand it when people interrupt me",
        "I love the way the morning light comes through the window",
        "I keep practicing the same scale every day",
        "That song struck a chord with me",
        "Tell me you understand consent before we keep going",
    ]
    for text in examples:
        prediction = predictor(text)
        print(f"INPUT:      {text}")
        print(f"PREDICTION: {prediction}")
        print()
