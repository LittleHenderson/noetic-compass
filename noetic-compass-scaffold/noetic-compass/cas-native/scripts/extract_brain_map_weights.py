"""Extract real weights from a CAS-Native checkpoint, downsampled to 32x32
representative grids, and emit a JSON file the dashboard brain map ships.

Phase 2a of the Mode 7 brain-map track. The close-view renderer (phase 2c)
paints these grids when the camera zooms into a layer, so the visualization
is anchored to actual trained values from the v0.2 checkpoint (model_final.pt).

Usage:
    python extract_brain_map_weights.py \\
        --checkpoint /path/to/model_final.pt \\
        --out /path/to/cas_brain_weights.json \\
        --checkpoint-id 30019a89-f75a-42f1-816b-f29f2df7fe4b \\
        --model-checkpoint stage4a_v02_20260514T200413Z

Fallback:
    python extract_brain_map_weights.py --fallback --out /path/to/out.json

The fallback path synthesizes Gaussian random weights against the known
v0.2 architecture's named tensor list (std=0.02), marks
``model_checkpoint == "FALLBACK_SYNTHETIC"`` so the brain map can show a
warning, and unblocks downstream renderer work when no checkpoint is
reachable.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


GRID = 32  # downsample-target grid size (per spec contract)
SCHEMA_VERSION = "cas_brain_weights.v1"

# Float precision for emitted grid values. The renderer maps values to
# colors so 3 sig figs is plenty for visualization; this halves payload
# size vs Python's default 17-digit repr while keeping stats accurate to
# 5 figures (see ``_round_scalar``).
GRID_FLOAT_PRECISION = 3
STATS_FLOAT_PRECISION = 5


# ---------------------------------------------------------------------------
# Classification of state-dict keys into (layer_key, sub_matrix_name, family).
# ---------------------------------------------------------------------------

# Tensors whose canonical projection is "Q, K, V" packed into a single matrix.
# For PyTorch's nn.MultiheadAttention this is named `in_proj_weight` and is
# laid out [3*d_model, d_model] = [Q; K; V]. We unpack into three sub-matrices
# so the brain-map renderer can show attention heads separately.
PACKED_QKV_SUFFIXES = ("self_attn.in_proj_weight", "cross_attn.in_proj_weight")
PACKED_QKV_BIAS_SUFFIXES = ("self_attn.in_proj_bias", "cross_attn.in_proj_bias")


_ENCODER_LAYER_RE = re.compile(r"^layers\.(\d+)\.([^.]+)(?:\.(.*))?$")
_DECODER_LAYER_RE = re.compile(r"^nl_gen_head\.layers\.(\d+)\.([^.]+)(?:\.(.*))?$")


def classify_key(key: str) -> tuple[str, str, str]:
    """Return (layer_key, sub_matrix_name, family) for a state-dict key.

    layer_key   — parent grouping the dashboard renders as one "layer card"
                  (e.g. ``encoder.layers.0.domain_attn``).
    sub_matrix  — short label for the matrix within the card (e.g. ``Q``, ``K``,
                  ``V``, ``O``, ``weight``, ``bias``, ``ffn_up.weight``).
    family      — coarse-grained category used by the renderer's color theme.
    """
    # ---- top-level embeddings ----
    if key == "token_embedding.weight":
        return "encoder.token_embedding", "weight", "embedding"
    if key == "pos_encoding.pe":
        return "encoder.pos_encoding", "pe", "positional"
    if key.startswith("cognitive_embedding."):
        return (
            "encoder.cognitive_embedding",
            key[len("cognitive_embedding.") :],
            "cognitive_embedding",
        )

    # ---- encoder transformer layers ----
    m = _ENCODER_LAYER_RE.match(key)
    if m is not None:
        layer_idx, sub_module, rest = m.group(1), m.group(2), m.group(3) or ""
        parent = f"encoder.layers.{layer_idx}.{sub_module}"
        if sub_module == "domain_attn":
            return parent, rest or "weight", "encoder_attn"
        if sub_module == "fractal_attn":
            return parent, rest or "weight", "encoder_fractal"
        if sub_module == "rpm_gate":
            return parent, rest or "weight", "encoder_rpm"
        if sub_module == "ffn":
            return parent, rest or "weight", "encoder_ffn"
        if sub_module in {"norm1", "norm2", "norm3", "norm4"}:
            return parent, rest or "weight", "encoder_norm"
        if sub_module == "fractal_gate":
            return parent, "scalar", "encoder_gate"
        return parent, rest or "weight", "encoder_other"

    # ---- final norm + lm head + non-layer top-level heads ----
    if key.startswith("final_norm."):
        return (
            "encoder.final_norm",
            key[len("final_norm.") :],
            "encoder_norm",
        )
    if key.startswith("lm_head."):
        return "lm_head", key[len("lm_head.") :], "lm_head"

    if key.startswith("topos_reasoner."):
        return "topos_reasoner", key[len("topos_reasoner.") :], "topos"
    if key.startswith("inversion_detector."):
        return (
            "inversion_detector",
            key[len("inversion_detector.") :],
            "inversion",
        )
    if key.startswith("generative_head."):
        return "generative_head", key[len("generative_head.") :], "generative"
    if key.startswith("lacunarity_gate."):
        return "lacunarity_gate", key[len("lacunarity_gate.") :], "lacunarity"
    if key.startswith("lacunarity_head."):
        return "lacunarity_head", key[len("lacunarity_head.") :], "lacunarity"

    # ---- nl gen head ----
    if key == "nl_gen_head.token_embedding.weight":
        return "decoder.token_embedding", "weight", "embedding"
    if key.startswith("nl_gen_head.pos_embedding."):
        return (
            "decoder.pos_embedding",
            key[len("nl_gen_head.pos_embedding.") :],
            "positional",
        )
    if key.startswith("nl_gen_head.soft_prefix_proj."):
        return (
            "decoder.soft_prefix_proj",
            key[len("nl_gen_head.soft_prefix_proj.") :],
            "decoder_proj",
        )
    if key.startswith("nl_gen_head.final_norm."):
        return (
            "decoder.final_norm",
            key[len("nl_gen_head.final_norm.") :],
            "decoder_norm",
        )
    if key.startswith("nl_gen_head.lm_head."):
        return (
            "decoder.lm_head",
            key[len("nl_gen_head.lm_head.") :],
            "lm_head",
        )
    if key.startswith("nl_gen_head.register_film."):
        return (
            "decoder.register_film",
            key[len("nl_gen_head.register_film.") :],
            "register_film",
        )

    m = _DECODER_LAYER_RE.match(key)
    if m is not None:
        layer_idx, sub_module, rest = m.group(1), m.group(2), m.group(3) or ""
        parent = f"decoder.layers.{layer_idx}.{sub_module}"
        if sub_module == "self_attn":
            return parent, rest or "weight", "decoder_self_attn"
        if sub_module == "cross_attn":
            return parent, rest or "weight", "decoder_cross_attn"
        if sub_module == "ffn":
            return parent, rest or "weight", "decoder_ffn"
        if sub_module in {"norm_self", "norm_cross", "norm_ffn"}:
            return parent, rest or "weight", "decoder_norm"
        return parent, rest or "weight", "decoder_other"

    # ---- catch-all ----
    return f"other.{key}", "weight", "other"


# ---------------------------------------------------------------------------
# Downsampling helpers.
# ---------------------------------------------------------------------------


def _block_mean_2d(matrix: np.ndarray, grid: int = GRID) -> np.ndarray:
    """Downsample a 2D matrix to ``(grid, grid)`` via block-mean.

    Uses ``np.array_split`` along both axes so shapes that aren't multiples
    of ``grid`` still partition cleanly (sizes differ by at most one row/col
    between blocks).
    """
    if matrix.ndim != 2:
        raise ValueError(f"expected 2D matrix, got shape {matrix.shape}")
    rows = np.array_split(matrix, grid, axis=0)
    out_rows = np.empty((grid, grid), dtype=np.float32)
    for i, row_block in enumerate(rows):
        col_chunks = np.array_split(row_block, grid, axis=1)
        for j, chunk in enumerate(col_chunks):
            out_rows[i, j] = float(chunk.mean()) if chunk.size > 0 else 0.0
    return out_rows


def _downsample_1d(vec: np.ndarray, grid: int = GRID) -> np.ndarray:
    """Downsample a 1D vector to ``(1, min(grid, size))`` via block-mean.

    Small 1D tensors (e.g. ``compose_bias`` (10,), ``inversion_detector`` bias
    (7,)) are emitted at their native size to avoid wasting bytes padding to
    ``grid``. Larger vectors are downsampled to ``(1, grid)``.
    """
    if vec.ndim != 1:
        raise ValueError(f"expected 1D vector, got shape {vec.shape}")
    if vec.size == 0:
        return np.zeros((1, 1), dtype=np.float32)
    if vec.size <= grid:
        return vec.astype(np.float32).reshape(1, -1)
    chunks = np.array_split(vec, grid)
    return np.array([[float(c.mean()) for c in chunks]], dtype=np.float32)


def _round_grid(grid: np.ndarray) -> list[list[float]]:
    """Round each float to GRID_FLOAT_PRECISION sig figs to shrink JSON size.

    Uses scientific-rounding via numpy.format_float_positional → float, which
    keeps the JSON repr short while preserving visualization-grade accuracy.
    """
    out: list[list[float]] = []
    for row in grid:
        out_row: list[float] = []
        for v in row:
            f = float(v)
            if f == 0.0 or not math.isfinite(f):
                out_row.append(f)
                continue
            # round to N significant figures
            mag = math.floor(math.log10(abs(f)))
            digits = GRID_FLOAT_PRECISION - 1 - mag
            out_row.append(round(f, max(0, digits)))
        out.append(out_row)
    return out


def downsample(tensor: np.ndarray) -> tuple[list[list[float]], tuple[int, int]]:
    """Return (grid, shape) for a tensor of arbitrary rank.

    - 0D (scalar): returns 1x1 grid with the scalar value.
    - 1D: returns 1x32 (norms, biases, scalars-per-token).
    - 2D: returns 32x32.
    - >2D: flatten leading dims into rows, last dim is cols, then block-mean
           to 32x32. This handles ``pos_encoding.pe`` (1, 2048, 512) and
           the few 3D tensors like ``generative_head.composition.compose_bias``.
    """
    arr = np.asarray(tensor, dtype=np.float32)
    if arr.ndim == 0:
        val = float(arr)
        return _round_grid(np.array([[val]])), (1, 1)
    if arr.ndim == 1:
        out = _downsample_1d(arr)
        return _round_grid(out), (out.shape[0], out.shape[1])
    if arr.ndim == 2:
        out = _block_mean_2d(arr)
        return _round_grid(out), (GRID, GRID)
    # rank >= 3: collapse all-but-last dim into rows
    rows = int(np.prod(arr.shape[:-1]))
    cols = arr.shape[-1]
    flat = arr.reshape(rows, cols)
    out = _block_mean_2d(flat)
    return _round_grid(out), (GRID, GRID)


def _round_scalar(f: float, sig: int = STATS_FLOAT_PRECISION) -> float:
    if f == 0.0 or not math.isfinite(f):
        return f
    mag = math.floor(math.log10(abs(f)))
    digits = sig - 1 - mag
    return round(f, max(0, digits))


def stats(tensor: np.ndarray) -> dict[str, float]:
    arr = np.asarray(tensor, dtype=np.float64)
    if arr.size == 0:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}
    return {
        "min": _round_scalar(float(arr.min())),
        "max": _round_scalar(float(arr.max())),
        "mean": _round_scalar(float(arr.mean())),
        "std": _round_scalar(float(arr.std())),
    }


# ---------------------------------------------------------------------------
# QKV / OUT unpacking helpers.
# ---------------------------------------------------------------------------


def _unpack_qkv(weight: np.ndarray) -> dict[str, np.ndarray]:
    """Split a PyTorch packed in_proj_weight into Q / K / V."""
    if weight.ndim != 2:
        return {"weight": weight}
    rows = weight.shape[0]
    if rows % 3 != 0:
        return {"weight": weight}
    chunk = rows // 3
    return {
        "Q": weight[:chunk],
        "K": weight[chunk : 2 * chunk],
        "V": weight[2 * chunk :],
    }


def _unpack_qkv_bias(bias: np.ndarray) -> dict[str, np.ndarray]:
    if bias.ndim != 1:
        return {"bias": bias}
    n = bias.shape[0]
    if n % 3 != 0:
        return {"bias": bias}
    c = n // 3
    return {"Q_bias": bias[:c], "K_bias": bias[c : 2 * c], "V_bias": bias[2 * c :]}


# ---------------------------------------------------------------------------
# Iteration over state_dict, producing per-layer entries.
# ---------------------------------------------------------------------------


@dataclass
class SubMatrix:
    name: str
    full_shape: tuple[int, ...]
    grid: list[list[float]]
    downsampled_shape: tuple[int, int]
    min: float
    max: float
    mean: float
    std: float
    full_param_count: int


def _materialize_sub(name: str, arr: np.ndarray) -> SubMatrix:
    grid, ds_shape = downsample(arr)
    st = stats(arr)
    return SubMatrix(
        name=name,
        full_shape=tuple(int(x) for x in arr.shape) if arr.ndim > 0 else (),
        grid=grid,
        downsampled_shape=ds_shape,
        min=st["min"],
        max=st["max"],
        mean=st["mean"],
        std=st["std"],
        full_param_count=int(arr.size) if arr.ndim > 0 else 1,
    )


def build_layers(state_dict: dict[str, np.ndarray]) -> tuple[dict[str, dict], dict[str, float]]:
    """Group state_dict entries by layer_key and emit the JSON-ready dict.

    Also returns the global stats over all parameters.
    """
    layers: dict[str, dict[str, Any]] = {}

    # global accumulators (use chunked sums for memory safety + speed)
    total_params = 0
    global_min = math.inf
    global_max = -math.inf
    # Parallel-Welford accumulator over tensor-sized chunks.
    n = 0
    mean = 0.0
    M2 = 0.0

    for key in state_dict:
        arr = np.asarray(state_dict[key], dtype=np.float32)
        layer_key, sub_name, family = classify_key(key)

        if layer_key not in layers:
            layers[layer_key] = {
                "family": family,
                "full_param_count": 0,
                "sub_matrices": [],
            }

        # Compose / unpack into one or more SubMatrices.
        sub_pieces: list[tuple[str, np.ndarray]] = []
        if any(key.endswith(s) for s in PACKED_QKV_SUFFIXES):
            for sub_label, mat in _unpack_qkv(arr).items():
                sub_pieces.append((sub_label, mat))
        elif any(key.endswith(s) for s in PACKED_QKV_BIAS_SUFFIXES):
            for sub_label, mat in _unpack_qkv_bias(arr).items():
                sub_pieces.append((sub_label, mat))
        else:
            # Rename out_proj.weight / out_proj.bias to O / O_bias for attention parents
            label = sub_name
            if sub_name == "out_proj.weight":
                label = "O"
            elif sub_name == "out_proj.bias":
                label = "O_bias"
            sub_pieces.append((label, arr))

        for sub_label, sub_arr in sub_pieces:
            sm = _materialize_sub(sub_label, sub_arr)
            layers[layer_key]["sub_matrices"].append(
                {
                    "name": sm.name,
                    "full_shape": list(sm.full_shape),
                    "downsampled_shape": list(sm.downsampled_shape),
                    "grid": sm.grid,
                    "min": sm.min,
                    "max": sm.max,
                    "mean": sm.mean,
                    "std": sm.std,
                    "full_param_count": sm.full_param_count,
                }
            )
            layers[layer_key]["full_param_count"] += sm.full_param_count

        # Update global accumulators using the raw tensor (pre-unpack equals sum).
        size = int(arr.size) if arr.ndim > 0 else 1
        total_params += size
        if size > 0:
            global_min = min(global_min, float(arr.min()))
            global_max = max(global_max, float(arr.max()))
            # Parallel-Welford combine: treat each tensor as one chunk with
            # known n_k, mean_k, M2_k. The pairwise combine formula:
            #   delta = mean_b - mean_a
            #   M2 = M2_a + M2_b + delta^2 * n_a * n_b / (n_a + n_b)
            #   mean = (n_a * mean_a + n_b * mean_b) / (n_a + n_b)
            flat = arr.reshape(-1).astype(np.float64)
            n_b = int(flat.size)
            mean_b = float(flat.mean())
            # variance population: var = mean((x - mean)^2)
            var_b = float(((flat - mean_b) ** 2).mean()) if n_b > 0 else 0.0
            M2_b = var_b * n_b
            if n == 0:
                n, mean, M2 = n_b, mean_b, M2_b
            else:
                delta = mean_b - mean
                new_n = n + n_b
                M2 = M2 + M2_b + (delta * delta) * n * n_b / new_n
                mean = (n * mean + n_b * mean_b) / new_n
                n = new_n

    # Top-level full shape on each layer: for layers with a single named
    # 2D sub-matrix, propagate full_shape to the parent (handy for renderer).
    for lkey, layer in layers.items():
        # pick the largest 2D sub-matrix's full_shape as the headline shape
        best = None
        for sm in layer["sub_matrices"]:
            if len(sm["full_shape"]) >= 2 and (
                best is None or sm["full_param_count"] > best["full_param_count"]
            ):
                best = sm
        if best is not None:
            layer["full_shape"] = list(best["full_shape"])

    global_std = math.sqrt(M2 / n) if n > 1 else 0.0
    return layers, {
        "total_params": total_params,
        "min_weight": global_min if global_min != math.inf else 0.0,
        "max_weight": global_max if global_max != -math.inf else 0.0,
        "mean_weight": mean,
        "std_weight": global_std,
    }


# ---------------------------------------------------------------------------
# Fallback: synthesize plausible random weights matching the v0.2 architecture.
# ---------------------------------------------------------------------------


def _fallback_state_dict() -> dict[str, np.ndarray]:
    """Synthesize a state-dict that matches the v0.2 architecture's named
    tensor list. Used only when checkpoint access fails."""
    rng = np.random.default_rng(0xCA5BEEF)

    def rn(shape: tuple[int, ...]) -> np.ndarray:
        return rng.normal(0.0, 0.02, size=shape).astype(np.float32)

    def zeros(shape: tuple[int, ...]) -> np.ndarray:
        return np.zeros(shape, dtype=np.float32)

    def ones(shape: tuple[int, ...]) -> np.ndarray:
        return np.ones(shape, dtype=np.float32)

    d = 512
    vocab = 24388
    num_enc = 6
    num_dec = 6

    sd: dict[str, np.ndarray] = {}
    sd["token_embedding.weight"] = rn((vocab, d))
    sd["pos_encoding.pe"] = rn((1, 2048, d))
    sd["cognitive_embedding.projection.0.weight"] = rn((256, d))
    sd["cognitive_embedding.projection.0.bias"] = zeros((256,))
    sd["cognitive_embedding.projection.2.weight"] = rn((40, 256))
    sd["cognitive_embedding.projection.2.bias"] = zeros((40,))

    for i in range(num_enc):
        p = f"layers.{i}"
        sd[f"{p}.fractal_gate"] = np.array(0.0, dtype=np.float32)
        sd[f"{p}.domain_attn.domain_mask"] = zeros((40, 40))
        for tag in ("q_proj", "k_proj", "v_proj", "out_proj", "feedback_proj"):
            sd[f"{p}.domain_attn.{tag}.weight"] = rn((d, d))
            sd[f"{p}.domain_attn.{tag}.bias"] = zeros((d,))
        sd[f"{p}.norm1.weight"] = ones((d,))
        sd[f"{p}.norm1.bias"] = zeros((d,))
        sd[f"{p}.fractal_attn.depth_weights"] = ones((3,))
        for tag in ("q_proj", "k_proj", "v_proj", "out_proj"):
            sd[f"{p}.fractal_attn.{tag}.weight"] = rn((d, d))
            sd[f"{p}.fractal_attn.{tag}.bias"] = zeros((d,))
        for depth in range(3):
            for m in range(4):
                sd[f"{p}.fractal_attn.hutchinson_ops.{depth}.maps.{m}._ratio_logit"] = (
                    np.array(0.0, dtype=np.float32)
                )
                sd[f"{p}.fractal_attn.hutchinson_ops.{depth}.maps.{m}.affine.weight"] = rn(
                    (64, 64)
                )
                sd[f"{p}.fractal_attn.hutchinson_ops.{depth}.maps.{m}.affine.bias"] = zeros(
                    (64,)
                )
        sd[f"{p}.norm2.weight"] = ones((d,))
        sd[f"{p}.norm2.bias"] = zeros((d,))
        for tag in ("gate_a0", "gate_drive", "gate_wisdom", "gate_proficiency"):
            sd[f"{p}.rpm_gate.{tag}.gate_proj.weight"] = rn((d, d))
            sd[f"{p}.rpm_gate.{tag}.gate_proj.bias"] = zeros((d,))
        sd[f"{p}.rpm_gate.eta.weight"] = rn((d, d))
        sd[f"{p}.rpm_gate.eta.bias"] = zeros((d,))
        sd[f"{p}.rpm_gate.epsilon.weight"] = rn((d, d))
        sd[f"{p}.rpm_gate.epsilon.bias"] = zeros((d,))
        sd[f"{p}.norm3.weight"] = ones((d,))
        sd[f"{p}.norm3.bias"] = zeros((d,))
        sd[f"{p}.ffn.0.weight"] = rn((2048, d))
        sd[f"{p}.ffn.0.bias"] = zeros((2048,))
        sd[f"{p}.ffn.3.weight"] = rn((d, 2048))
        sd[f"{p}.ffn.3.bias"] = zeros((d,))
        sd[f"{p}.norm4.weight"] = ones((d,))
        sd[f"{p}.norm4.bias"] = zeros((d,))

    sd["final_norm.weight"] = ones((d,))
    sd["final_norm.bias"] = zeros((d,))
    sd["lm_head.weight"] = rn((vocab, d))

    sd["topos_reasoner.proposition_proj.weight"] = rn((3584, d))
    sd["topos_reasoner.proposition_proj.bias"] = zeros((3584,))
    for i in range(7):
        sd[f"topos_reasoner.truth_classifiers.{i}.0.weight"] = rn((128, d))
        sd[f"topos_reasoner.truth_classifiers.{i}.0.bias"] = zeros((128,))
        sd[f"topos_reasoner.truth_classifiers.{i}.2.weight"] = rn((3, 128))
        sd[f"topos_reasoner.truth_classifiers.{i}.2.bias"] = zeros((3,))
    sd["topos_reasoner.counit.weight"] = rn((d, d))
    sd["topos_reasoner.counit.bias"] = zeros((d,))
    sd["inversion_detector.detector.0.weight"] = rn((256, d))
    sd["inversion_detector.detector.0.bias"] = zeros((256,))
    sd["inversion_detector.detector.2.weight"] = rn((7, 256))
    sd["inversion_detector.detector.2.bias"] = zeros((7,))
    sd["generative_head.merge.0.weight"] = rn((d, 2 * d))
    sd["generative_head.merge.0.bias"] = zeros((d,))
    sd["generative_head.merge.2.weight"] = ones((d,))
    sd["generative_head.merge.2.bias"] = zeros((d,))
    sd["generative_head.composition.compose_bias"] = rn((10, 10, 10))
    sd["generative_head.composition.slot_to_operator.weight"] = rn((10, d))
    sd["generative_head.composition.slot_to_operator.bias"] = zeros((10,))
    sd["generative_head.to_state.weight"] = rn((40, d))
    sd["generative_head.to_state.bias"] = zeros((40,))
    sd["lacunarity_gate.rebalance.weight"] = rn((40, 40))
    sd["lacunarity_gate.rebalance.bias"] = zeros((40,))
    sd["lacunarity_gate.gate.weight"] = rn((1, 40))
    sd["lacunarity_gate.gate.bias"] = zeros((1,))
    sd["lacunarity_head.lacunarity_predictor.0.weight"] = rn((256, d))
    sd["lacunarity_head.lacunarity_predictor.0.bias"] = zeros((256,))
    sd["lacunarity_head.lacunarity_predictor.2.weight"] = rn((5, 256))
    sd["lacunarity_head.lacunarity_predictor.2.bias"] = zeros((5,))
    sd["lacunarity_head.gap_detector.0.weight"] = rn((256, d))
    sd["lacunarity_head.gap_detector.0.bias"] = zeros((256,))
    sd["lacunarity_head.gap_detector.2.weight"] = rn((40, 256))
    sd["lacunarity_head.gap_detector.2.bias"] = zeros((40,))
    sd["lacunarity_head.confidence_estimator.0.weight"] = rn((128, d))
    sd["lacunarity_head.confidence_estimator.0.bias"] = zeros((128,))
    sd["lacunarity_head.confidence_estimator.2.weight"] = rn((4, 128))
    sd["lacunarity_head.confidence_estimator.2.bias"] = zeros((4,))

    sd["nl_gen_head.token_embedding.weight"] = rn((vocab, d))
    sd["nl_gen_head.pos_embedding.weight"] = rn((d, d))
    sd["nl_gen_head.soft_prefix_proj.weight"] = rn((2048, 64))
    sd["nl_gen_head.soft_prefix_proj.bias"] = zeros((2048,))
    for i in range(num_dec):
        p = f"nl_gen_head.layers.{i}"
        sd[f"{p}.self_attn.in_proj_weight"] = rn((3 * d, d))
        sd[f"{p}.self_attn.in_proj_bias"] = zeros((3 * d,))
        sd[f"{p}.self_attn.out_proj.weight"] = rn((d, d))
        sd[f"{p}.self_attn.out_proj.bias"] = zeros((d,))
        sd[f"{p}.norm_self.weight"] = ones((d,))
        sd[f"{p}.norm_self.bias"] = zeros((d,))
        sd[f"{p}.cross_attn.in_proj_weight"] = rn((3 * d, d))
        sd[f"{p}.cross_attn.in_proj_bias"] = zeros((3 * d,))
        sd[f"{p}.cross_attn.out_proj.weight"] = rn((d, d))
        sd[f"{p}.cross_attn.out_proj.bias"] = zeros((d,))
        sd[f"{p}.norm_cross.weight"] = ones((d,))
        sd[f"{p}.norm_cross.bias"] = zeros((d,))
        sd[f"{p}.ffn.0.weight"] = rn((2048, d))
        sd[f"{p}.ffn.0.bias"] = zeros((2048,))
        sd[f"{p}.ffn.3.weight"] = rn((d, 2048))
        sd[f"{p}.ffn.3.bias"] = zeros((d,))
        sd[f"{p}.norm_ffn.weight"] = ones((d,))
        sd[f"{p}.norm_ffn.bias"] = zeros((d,))
    sd["nl_gen_head.final_norm.weight"] = ones((d,))
    sd["nl_gen_head.final_norm.bias"] = zeros((d,))
    sd["nl_gen_head.lm_head.weight"] = rn((vocab, d))
    sd["nl_gen_head.register_film.gamma"] = ones((4, d))
    sd["nl_gen_head.register_film.beta"] = zeros((4, d))
    return sd


# ---------------------------------------------------------------------------
# Main entry.
# ---------------------------------------------------------------------------


def _load_state_dict(ckpt_path: Path) -> dict[str, np.ndarray]:
    """Load a torch state-dict to numpy without importing torch unless needed."""
    import torch  # local import — fallback path doesn't need torch.

    raw = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    if isinstance(raw, dict) and "model" in raw and isinstance(raw["model"], dict):
        state = raw["model"]
    elif isinstance(raw, dict):
        state = raw
    else:
        raise RuntimeError(f"unrecognized checkpoint container: {type(raw).__name__}")
    return {k: v.detach().cpu().numpy() for k, v in state.items()}


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--checkpoint-id",
        type=str,
        default="30019a89-f75a-42f1-816b-f29f2df7fe4b",
    )
    parser.add_argument(
        "--model-checkpoint",
        type=str,
        default="stage4a_v02_20260514T200413Z",
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Skip checkpoint loading; synthesize plausible random weights.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    used_fallback = args.fallback or args.checkpoint is None or not args.checkpoint.exists()
    if used_fallback:
        if not args.fallback:
            print(
                f"[warn] checkpoint {args.checkpoint} not found; using FALLBACK_SYNTHETIC",
                file=sys.stderr,
            )
        sd = _fallback_state_dict()
        ckpt_sha = ""
        model_ckpt_label = "FALLBACK_SYNTHETIC"
        ckpt_id = "FALLBACK"
    else:
        sd = _load_state_dict(args.checkpoint)
        ckpt_sha = _sha256_of(args.checkpoint)
        model_ckpt_label = args.model_checkpoint
        ckpt_id = args.checkpoint_id

    layers, global_stats = build_layers(sd)

    out = {
        "schema_version": SCHEMA_VERSION,
        "model_checkpoint": model_ckpt_label,
        "checkpoint_id": ckpt_id,
        "checkpoint_sha256": ckpt_sha,
        "extracted_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "downsample_grid": GRID,
        "global_stats": global_stats,
        "layers": layers,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Compact (no indent) keeps the bundle small. Use ensure_ascii so the
    # output is safe to ship as a TS-imported JSON.
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, separators=(",", ":"))

    # Verification: re-parse, check structure.
    with args.out.open("r", encoding="utf-8") as f:
        parsed = json.load(f)
    assert parsed["schema_version"] == SCHEMA_VERSION
    assert isinstance(parsed["layers"], dict)
    assert len(parsed["layers"]) >= 30, f"too few layers: {len(parsed['layers'])}"
    size_kb = args.out.stat().st_size / 1024.0
    print(
        f"wrote {args.out} "
        f"({size_kb:.1f} KB, {len(parsed['layers'])} layers, "
        f"total_params={parsed['global_stats']['total_params']}, "
        f"fallback={used_fallback})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
