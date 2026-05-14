"""Token -> head attribution and capacity allocation for Mode 7.

Two computations live here:

1. ``compute_per_token_attribution`` — for each of the 12 heads, return a list
   of length ``token_count`` giving the relative contribution each input token
   made to that head's argmax/threshold decision. Sums to 1.0 per head.

2. ``compute_capacity_allocation`` — per-head bottleneck capacity share.
   Computed as the L2-norm of the head's linear weight projection of the
   current bottleneck activation, normalized across heads.

v0 implementations are stubs (uniform attribution, mock-weight capacity); they
return correctly-shaped Python objects and are exercised by the smoke tests.
The real implementations land in Follow-on 1 (see spec §10).
"""

from __future__ import annotations

import math
from typing import Any

from cas_native.trace.activations import (
    HEAD_NAMES,
    ActivationCapture,
    head_logit_widths,
    _pseudo_float,
    _stable_hash,
)


def compute_per_token_attribution(
    capture: ActivationCapture,
    *,
    tokens: list[str],
    method: str = "rollout",
) -> dict[str, list[float]]:
    """Per-head, per-token attribution.

    Args:
        capture: an ``ActivationCapture`` (from ``compute_with_hooks``).
        tokens: the tokenized input. ``len(tokens)`` is the column count
            of the returned attribution matrix.
        method: ``"rollout"`` (v1, attention rollout), ``"ig"`` (follow-on,
            integrated gradients), ``"uniform"`` (v0 stub).

    Returns:
        ``{head_name: [token_0_attr, token_1_attr, ..., token_n-1_attr]}``.
        Each list sums to 1.0 ± 1e-6. If ``len(tokens) == 0``, lists are empty.

    v0 behaviour: returns a per-head distribution that varies across heads but
    is uniform across tokens within a head. The variation across heads ensures
    the dashboard's heatmap renders something non-trivial; the within-head
    uniformity flags the stub.
    """
    if not tokens:
        return {name: [] for name in HEAD_NAMES}

    if method == "uniform":
        return _uniform_attribution(len(tokens))

    if method == "rollout":
        # --- BEGIN: real attention rollout in Follow-on 1 ---
        if capture.attention_matrices:
            return _rollout_attribution(capture, tokens=tokens)
        # Fallback: stub. The diagnostic is added by ``trace_prediction``.
        return _uniform_attribution(len(tokens))
        # --- END ---

    if method == "ig":
        raise NotImplementedError(
            "integrated gradients attribution is a follow-on; "
            "use method='rollout' for v0/v1"
        )

    raise ValueError(
        f"unknown attribution method {method!r}; "
        f"expected one of 'rollout', 'ig', 'uniform'"
    )


def _uniform_attribution(token_count: int) -> dict[str, list[float]]:
    if token_count <= 0:
        return {name: [] for name in HEAD_NAMES}
    share = 1.0 / token_count
    return {name: [share] * token_count for name in HEAD_NAMES}


def _rollout_attribution(
    capture: ActivationCapture,
    *,
    tokens: list[str],
) -> dict[str, list[float]]:
    """Attention rollout (placeholder).

    Real implementation:
      1. Mean-pool attention across attention heads, per layer.
      2. Add identity (residual stream) to each layer's mean attention.
      3. Multiply layers together (rollout).
      4. Take row corresponding to pool position to get per-token contribution.
      5. Re-weight per head via gradient w.r.t. ``z`` (single backward pass).

    v0 stub: collapses ``capture.attention_matrices`` if any are present, else
    delegates to uniform.
    """
    if not capture.attention_matrices:
        return _uniform_attribution(len(tokens))
    rolled = capture.attention_matrices[0]
    if not rolled or not rolled[0]:
        return _uniform_attribution(len(tokens))
    # Take row 0 (placeholder for pool position).
    row = rolled[0]
    total = sum(abs(v) for v in row) or 1.0
    contribs = [abs(v) / total for v in row]
    # Pad/trim to len(tokens).
    if len(contribs) < len(tokens):
        contribs = contribs + [0.0] * (len(tokens) - len(contribs))
    contribs = contribs[: len(tokens)]
    s = sum(contribs) or 1.0
    contribs = [c / s for c in contribs]
    # All heads get the same rollout for v0; per-head re-weighting is follow-on.
    return {name: list(contribs) for name in HEAD_NAMES}


def compute_capacity_allocation(
    capture: ActivationCapture,
    *,
    head_weights: dict[str, list[list[float]]] | None = None,
) -> dict[str, float]:
    """Per-head bottleneck capacity share.

    For each head ``h`` with weight matrix ``W_h: (num_classes_h, bottleneck_dim)``,
    we compute ``||W_h @ z||_2`` and normalize across heads. Sum is 1.0.

    Args:
        capture: source of the post-bottleneck ``z`` vector.
        head_weights: optional ``{head_name: weight_matrix_as_list_of_lists}``.
            If None, a deterministic mock weight matrix is generated from the
            same hash as ``capture`` so smoke tests are reproducible.

    Returns:
        ``{head_name: share}``, share in [0.0, 1.0], sums to 1.0 ± 1e-6.
        If the bottleneck is empty, returns the uniform distribution.
    """
    z = capture.post_bottleneck
    if not z:
        return {name: 1.0 / len(HEAD_NAMES) for name in HEAD_NAMES}

    if head_weights is None:
        head_weights = _mock_head_weights(bottleneck_dim=len(z))

    norms: dict[str, float] = {}
    for name in HEAD_NAMES:
        weight = head_weights.get(name)
        if not weight:
            norms[name] = 0.0
            continue
        # Compute W @ z, then ||.||_2.
        proj = [_dot(row, z) for row in weight]
        norms[name] = math.sqrt(sum(v * v for v in proj))

    total = sum(norms.values())
    if total <= 0.0:
        return {name: 1.0 / len(HEAD_NAMES) for name in HEAD_NAMES}
    return {name: norms[name] / total for name in HEAD_NAMES}


def _dot(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))


def _mock_head_weights(*, bottleneck_dim: int) -> dict[str, list[list[float]]]:
    """Deterministic mock weight matrices, one per head.

    Each weight matrix is shape ``(num_classes_h, bottleneck_dim)`` filled with
    pseudo-random values seeded by the head name. These are NOT trained
    weights; they exist only so the capacity computation has something
    well-shaped to operate on in stub mode.
    """
    widths = head_logit_widths()
    weights: dict[str, list[list[float]]] = {}
    for name in HEAD_NAMES:
        seed = _stable_hash(name)
        n_classes = widths[name]
        rows: list[list[float]] = []
        for r in range(n_classes):
            row = [
                _pseudo_float(seed, r * bottleneck_dim + c, scale=0.5)
                for c in range(bottleneck_dim)
            ]
            rows.append(row)
        weights[name] = rows
    return weights


def compute_per_head_confidence(
    capture: ActivationCapture,
    *,
    threshold: float = 0.0,
) -> dict[str, float]:
    """Softmax-max for scalar heads, mean(sigmoid) over actives for multi-label.

    Operates on the captured per-head logits; no model invocation. Stable on
    stub captures (which generate logits from the same hash).

    Returns one float per head in [0.0, 1.0].
    """
    out: dict[str, float] = {}
    for name in HEAD_NAMES:
        logits = capture.per_head_logits.get(name) or []
        if not logits:
            out[name] = 0.0
            continue
        if name in {"register", "meta_relation"}:
            sig = [_sigmoid(v) for v in logits]
            actives = [s for s, v in zip(sig, logits) if v > threshold]
            if actives:
                out[name] = sum(actives) / len(actives)
            else:
                out[name] = max(sig)
        else:
            sm = _softmax(logits)
            out[name] = max(sm)
    return out


def compute_bottleneck_top_k(
    capture: ActivationCapture,
    *,
    top_k: int = 8,
) -> list[tuple[int, float]]:
    """Top-K (dim_index, signed_activation) sorted by ``|activation|`` desc."""
    z = capture.post_bottleneck
    if not z:
        return []
    indexed = list(enumerate(z))
    indexed.sort(key=lambda pair: abs(pair[1]), reverse=True)
    return [(i, v) for i, v in indexed[:top_k]]


def _softmax(logits: list[float]) -> list[float]:
    if not logits:
        return []
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


# Re-export convenience used by the smoke tests.
def attribution_sums(
    attribution: dict[str, list[float]],
) -> dict[str, float]:
    return {head: sum(values) for head, values in attribution.items()}


def is_normalized(values: list[float], *, atol: float = 1e-6) -> bool:
    if not values:
        return True
    return abs(sum(values) - 1.0) <= atol
