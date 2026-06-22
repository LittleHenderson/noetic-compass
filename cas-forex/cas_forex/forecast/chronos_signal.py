"""Chronos directional-signal adapter for the backtest engine.

Wraps Amazon Chronos-Bolt (loaded once, CPU) into a tiny callable the
BacktestEngine can use as a drop-in directional signal: given the close series,
forecast the next step and return (Direction, confidence) or None when the
predicted move is too small to act on.

This produces ONLY a direction + confidence. The engine sets ATR-based SL/TP
identically for every signal source, so a Chronos-vs-SMA comparison isolates the
forecaster's contribution.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from cas_forex.schemas.forecast import Direction

_PIPELINES: dict = {}


def _get_pipeline(model_id: str):
    if model_id in _PIPELINES:
        return _PIPELINES[model_id]
    import torch
    from chronos import BaseChronosPipeline

    pipe = BaseChronosPipeline.from_pretrained(
        model_id,
        device_map="cpu",
        torch_dtype=torch.float32,
    )
    _PIPELINES[model_id] = pipe
    return pipe


def make_chronos_signal_fn(
    model_id: str = "amazon/chronos-bolt-tiny",
    context_len: int = 256,
    prediction_length: int = 1,
    min_move_bps: float = 2.0,
    max_confidence: float = 0.9,
) -> Callable[[List[float]], Optional[Tuple[Direction, float]]]:
    """Build a signal function backed by Chronos-Bolt.

    Args:
        model_id: HuggingFace Chronos model (bolt-tiny/small/base).
        context_len: how many trailing closes to feed the model.
        prediction_length: steps ahead to forecast (direction read at final step).
        min_move_bps: ignore predicted moves smaller than this (basis points).
        max_confidence: cap on emitted confidence.
    """
    import torch

    pipe = _get_pipeline(model_id)

    def signal_fn(closes: List[float]) -> Optional[Tuple[Direction, float]]:
        if len(closes) < 8:
            return None
        current = closes[-1]
        if current <= 0:
            return None
        ctx = closes[-context_len:]
        context = torch.tensor(ctx, dtype=torch.float32)
        with torch.inference_mode():
            quantiles, _mean = pipe.predict_quantiles(
                context,
                prediction_length=prediction_length,
                quantile_levels=[0.1, 0.5, 0.9],
            )
        # quantiles: [num_series=1, prediction_length, num_quantiles=3]
        median = float(quantiles[0, -1, 1])
        move = (median - current) / current
        move_bps = abs(move) * 10_000.0
        if move_bps < min_move_bps:
            return None
        direction = Direction.LONG if move > 0 else Direction.SHORT
        confidence = min(max_confidence, 0.3 + move_bps / 20.0)
        return direction, round(confidence, 4)

    return signal_fn
