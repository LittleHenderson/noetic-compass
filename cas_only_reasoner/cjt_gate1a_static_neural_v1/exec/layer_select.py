"""layer_select.py -- the FROZEN S0-only layer-selection law.

L* is chosen ONCE: train S0 (seed 11) on activations from each candidate layer
{6, 12, 18, 24} (decoder blocks 1-indexed, hidden-state OUTPUT of block L) and
pick the layer with the highest VALIDATION exact match. Deterministic tie-break:
the LOWEST layer index. Every other arm and seed reuses L*. Recorded in the
execution receipt before any non-S0 training starts.
"""
from __future__ import annotations

CANDIDATE_LAYERS = (6, 12, 18, 24)
SELECTION_SEED = 11
SELECTION_ARM = "S0"


def select_layer(val_accuracy_by_layer: dict) -> int:
    """{layer_int: validation_accuracy_float} -> L*. Pure and deterministic."""
    if sorted(val_accuracy_by_layer) != sorted(CANDIDATE_LAYERS):
        raise ValueError(f"LAYER_SELECTION_FAILURE: need exactly {CANDIDATE_LAYERS}")
    best = max(val_accuracy_by_layer.values())
    return min(l for l, a in val_accuracy_by_layer.items() if a == best)
