"""Lane A apparatus: W0 (embedding-output) pre-speech capture + W0/W1/W8 windows.

Captures the embedding-layer output at the FINAL prompt token position, BEFORE
any autoregressive token is generated — the true "W0 / pre-speech" state the v5
gate specifies. Also captures W1 (after token 1) and W8 (frozen window) so the
temporal-separation control can prove W0 is genuinely pre-generation.

APPARATUS ONLY. Capturing W0 licenses nothing. Whether W0 *predicts* comply vs
refuse beyond surface text is decided by the Lane A evaluator gates
(`evaluate_behavior_v6_matched_prespeech.py`), which a prior Qwen run FAILED
(0.745 < 0.75). This module just makes the capture clean and verifiable.

The pure temporal-validation math (``cosine`` / ``validate_windows``) is testable
without a model; the forward-hook class needs a loaded model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional, Sequence


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Plain cosine similarity between two equal-length vectors."""

    if len(a) != len(b):
        raise ValueError("vectors must be equal length")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def validate_windows(
    w0: Optional[Sequence[float]],
    w1: Optional[Sequence[float]],
    w8: Optional[Sequence[float]] = None,
    *,
    max_self_similarity: float = 0.99,
) -> dict[str, Any]:
    """Prove W0 is genuinely pre-generation by checking it differs from W1.

    If cos(W0, W1) > ``max_self_similarity`` the captured "W0" is not actually a
    distinct pre-speech state and the window is invalid.
    """

    if w0 is None or w1 is None:
        return {"valid": False, "reason": "missing W0 or W1 window"}
    cos_01 = cosine(w0, w1)
    cos_08 = cosine(w0, w8) if w8 is not None else None
    cos_18 = cosine(w1, w8) if w8 is not None else None
    valid = cos_01 < max_self_similarity
    return {
        "valid": valid,
        "cosine_W0_W1": cos_01,
        "cosine_W0_W8": cos_08,
        "cosine_W1_W8": cos_18,
        "interpretation": (
            "W0 is a distinct pre-speech state"
            if valid
            else "W0 ~ W1 (cosine too high) — capture is NOT genuinely pre-generation"
        ),
    }


@dataclass
class CapturedWindows:
    """Plain-float windows for serialization / validation."""

    w0: Optional[list[float]] = None
    w1: Optional[list[float]] = None
    w8: Optional[list[float]] = None

    def validate(self, **kwargs: Any) -> dict[str, Any]:
        return validate_windows(self.w0, self.w1, self.w8, **kwargs)


class W0PreSpeechCapture:
    """Forward hook on the embedding layer; records the final-prompt-token output.

    Usage (needs a loaded HF model)::

        cap = W0PreSpeechCapture(model)
        model(**inputs)          # W0 captured during the prompt forward pass
        w0 = cap.get_w0()        # torch.Tensor [batch, hidden] (last prompt token)
        cap.remove()
    """

    def __init__(self, model: Any):
        self.model = model
        self.w0_state: Any = None
        self._handle: Any = None
        self._register()

    def _register(self) -> None:
        embed = self.model.get_input_embeddings()

        def w0_hook(_module: Any, _inp: Any, output: Any) -> Any:
            # output: [batch, seq_len, hidden] — keep the LAST prompt position only.
            self.w0_state = output[:, -1, :].detach().clone()
            return output

        self._handle = embed.register_forward_hook(w0_hook)

    def get_w0(self) -> Any:
        return self.w0_state

    def get_w0_list(self) -> Optional[list[float]]:
        if self.w0_state is None:
            return None
        return self.w0_state[0].float().tolist()

    def remove(self) -> None:
        if self._handle is not None:
            self._handle.remove()
            self._handle = None
