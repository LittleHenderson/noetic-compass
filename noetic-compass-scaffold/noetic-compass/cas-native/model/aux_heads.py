"""v1e Phase C — auxiliary supervision heads attached to the encoder pool
and the NL decoder hidden states.

Four heads per the design doc
(``docs/working/v1e_phase_c_aux_heads_design_2026_05_11.md``):

  - ``CardinalityHead`` (H_card)   — predicts K = # of fractal slots
                                     from pooled encoder state.
  - ``PerPositionNoeticHead`` (H_pos) — predicts the Noetic class
                                       (0-9) at each position 0..K_max-1.
  - ``StopCompleteHead`` (H_stop)  — per-decoder-position binary
                                     classifier "all slots committed?",
                                     used both as training signal AND
                                     inference-time dynamic EOS bias.
  - ``ClusterMembershipHead`` (H_cluster) — per-cluster multi-label
                                            Noetic membership for
                                            meta-logic relations.

All four are SMALL relative to the backbone (~213k total params,
< 0.4% of the 50M-param encoder+head). Their training signal
shapes the encoder's pool to "know" the source CAS structure, so
the LM head's prose generation has explicit cardinality / position /
stop / cluster supervision rather than implicit-from-LM-only.

Per ``feedback_postprocessor_policy_line`` and the v1e design audit:
these heads modify the model, NOT the postprocessor. Stop signal in
particular is the structural fix β2 named — model learns to stop
after N slots, replacing the blunt static EOS bias that produced
fragments in Task #139.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import torch
from torch import nn


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Maximum fractal slots and meta-logic clusters supported. Sized for the
# v1c training corpus + the Phase 1B eval suite (k up to 8 with headroom).
DEFAULT_K_MAX: int = 16
DEFAULT_C_MAX: int = 6
NUM_NOETICS: int = 10


@dataclass(frozen=True)
class AuxHeadsConfig:
    """Hyperparameter bundle for the four aux heads.

    All dimensions sized for the v1c VALIDTOK 5ep checkpoint
    (``d_model=512``). The defaults match the design doc's
    cost-summary param counts.
    """

    d_model: int = 512
    k_max: int = DEFAULT_K_MAX
    c_max: int = DEFAULT_C_MAX
    num_noetics: int = NUM_NOETICS

    # Per-head hidden / output sizes (match design doc §2).
    cardinality_hidden: int = 128
    stop_hidden: int = 64

    # When True, the heads are weight-tied to a shared linear
    # preprojection. Default False — keep heads independent for
    # Phase C; revisit if param budget becomes a concern.
    share_preprojection: bool = False


# ---------------------------------------------------------------------------
# Cardinality head (H_card)
# ---------------------------------------------------------------------------

class CardinalityHead(nn.Module):
    """Predict K = expected fractal slot count from pooled encoder state.

    Output: ``(B, K_max + 1)`` logits over classes ``{0, 1, ..., K_max}``.
    Class 0 is the "non-fractal / no expected slots" target for
    non-fractal records (used jointly with a sample-weight mask in
    the loss term).
    """

    def __init__(self, config: AuxHeadsConfig) -> None:
        super().__init__()
        self.config = config
        self.fc1 = nn.Linear(config.d_model, config.cardinality_hidden)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(config.cardinality_hidden, config.k_max + 1)

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        """Args:
            pooled: ``(B, d_model)`` encoder masked-mean pool.

        Returns:
            ``(B, K_max + 1)`` logits.
        """
        h = self.act(self.fc1(pooled))
        return self.fc2(h)


# ---------------------------------------------------------------------------
# Per-position Noetic head (H_pos)
# ---------------------------------------------------------------------------

class PerPositionNoeticHead(nn.Module):
    """Predict the Noetic class at each position 0..K_max-1.

    Output: ``(B, K_max, num_noetics)`` logits. Per-position softmax
    over the 10 Noetic classes. Loss uses ``ignore_index=-100`` for
    positions ``i >= K_actual``, so non-fractal records contribute
    zero loss when paired with a sample weight of 0.

    Architecture: a single linear projection from pooled state to
    ``K_max × num_noetics`` reshaped to ``(B, K_max, num_noetics)``.
    This is the highest-leverage aux head — it directly trains the
    encoder pool to "know" the ordered Noetic sequence at each slot.
    """

    def __init__(self, config: AuxHeadsConfig) -> None:
        super().__init__()
        self.config = config
        self.k_max = config.k_max
        self.num_noetics = config.num_noetics
        self.proj = nn.Linear(
            config.d_model, config.k_max * config.num_noetics,
        )

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        """Args:
            pooled: ``(B, d_model)`` encoder masked-mean pool.

        Returns:
            ``(B, K_max, num_noetics)`` logits.
        """
        flat = self.proj(pooled)
        return flat.view(-1, self.k_max, self.num_noetics)


# ---------------------------------------------------------------------------
# Stop / complete head (H_stop)
# ---------------------------------------------------------------------------

class StopCompleteHead(nn.Module):
    """Per-decoder-position binary classifier "all expected slots committed?".

    Output: ``(B, L_dec, 2)`` logits per decoder position. Class 1
    ("stop") means "all expected fractal slots have been committed
    up to this position; EOS is appropriate." Class 0 ("continue")
    means more content is expected.

    This head is the structural fix β2 named: the model LEARNS
    where to stop, so inference can apply a dynamic EOS bias derived
    from this head's "stop" probability instead of the blunt static
    ``fractal_decoder_eos_bias`` that produced fragments in Task #139.

    Attaches to decoder hidden states (post-FiLM-modulated decoder
    output), NOT the encoder pool. Forward takes ``(B, L, d_model)``
    and returns ``(B, L, 2)``.
    """

    def __init__(self, config: AuxHeadsConfig) -> None:
        super().__init__()
        self.config = config
        self.fc1 = nn.Linear(config.d_model, config.stop_hidden)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(config.stop_hidden, 2)

    def forward(self, decoder_hidden: torch.Tensor) -> torch.Tensor:
        """Args:
            decoder_hidden: ``(B, L, d_model)`` decoder hidden states.

        Returns:
            ``(B, L, 2)`` logits over [continue, stop].
        """
        h = self.act(self.fc1(decoder_hidden))
        return self.fc2(h)


# ---------------------------------------------------------------------------
# Cluster membership head (H_cluster)
# ---------------------------------------------------------------------------

class ClusterMembershipHead(nn.Module):
    """Predict per-cluster Noetic multi-label membership for meta-logic.

    Output: ``(B, C_max, num_noetics)`` logits. Per-cluster sigmoid
    multi-label classification — each cluster slot independently
    predicts which Noetics are members (0..N memberships allowed
    per cluster).

    Used for meta-logic source CAS like
    ``PartitionOf(Noetics, NoeticCluster{^5}, NoeticCluster{^1,^2,^3})``.
    Loss is BCE-with-logits, masked by ``aux_cluster_mask``
    (which cluster slots are valid for the record) and gated by
    ``aux_cluster_sample_weight`` (1.0 for meta-logic, 0.0 otherwise).
    """

    def __init__(self, config: AuxHeadsConfig) -> None:
        super().__init__()
        self.config = config
        self.c_max = config.c_max
        self.num_noetics = config.num_noetics
        self.proj = nn.Linear(
            config.d_model, config.c_max * config.num_noetics,
        )

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        """Args:
            pooled: ``(B, d_model)`` encoder masked-mean pool.

        Returns:
            ``(B, C_max, num_noetics)`` logits.
        """
        flat = self.proj(pooled)
        return flat.view(-1, self.c_max, self.num_noetics)


# ---------------------------------------------------------------------------
# Builder / container
# ---------------------------------------------------------------------------

class AuxHeads(nn.Module):
    """Container module holding all four aux heads.

    Stored on ``CASNativeModel`` via ``attach_aux_heads()`` so the
    model owns the parameters for optimizer + state-dict round-trips.
    Forward is NOT defined on this container — callers invoke the
    individual heads with the appropriate input (encoder pool for
    H_card/H_pos/H_cluster; decoder hidden states for H_stop).
    """

    def __init__(self, config: AuxHeadsConfig) -> None:
        super().__init__()
        self.config = config
        self.cardinality = CardinalityHead(config)
        self.per_position = PerPositionNoeticHead(config)
        self.stop_complete = StopCompleteHead(config)
        self.cluster_membership = ClusterMembershipHead(config)
        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier init for Linear weights, zero bias. Matches the
        existing ``CASNativeModel._init_weights`` style."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, *args, **kwargs) -> Dict[str, torch.Tensor]:
        """Convenience: forward all four heads at once.

        Args:
            pooled: ``(B, d_model)`` encoder masked-mean pool.
            decoder_hidden: ``(B, L, d_model)`` decoder hidden states.
                Required when stop head is being used; otherwise
                may be None to skip the stop forward.

        Returns dict with keys:
            ``card_logits``: ``(B, K_max+1)``
            ``pos_logits``:  ``(B, K_max, num_noetics)``
            ``stop_logits``: ``(B, L, 2)`` or None
            ``cluster_logits``: ``(B, C_max, num_noetics)``
        """
        pooled: torch.Tensor = kwargs.get("pooled")
        decoder_hidden: Optional[torch.Tensor] = kwargs.get("decoder_hidden")
        if pooled is None and args:
            pooled = args[0]
        if pooled is None:
            raise ValueError("AuxHeads.forward requires `pooled` kwarg")
        out: Dict[str, torch.Tensor] = {
            "card_logits": self.cardinality(pooled),
            "pos_logits": self.per_position(pooled),
            "cluster_logits": self.cluster_membership(pooled),
        }
        if decoder_hidden is not None:
            out["stop_logits"] = self.stop_complete(decoder_hidden)
        else:
            out["stop_logits"] = None  # type: ignore[assignment]
        return out


def build_aux_heads(config: Optional[AuxHeadsConfig] = None) -> AuxHeads:
    """Factory for ``AuxHeads`` matching a given config. Default config
    matches the v1c VALIDTOK 5ep checkpoint (d_model=512, K_max=16,
    C_max=6)."""
    return AuxHeads(config if config is not None else AuxHeadsConfig())


__all__ = [
    "AuxHeads",
    "AuxHeadsConfig",
    "CardinalityHead",
    "ClusterMembershipHead",
    "DEFAULT_C_MAX",
    "DEFAULT_K_MAX",
    "NUM_NOETICS",
    "PerPositionNoeticHead",
    "StopCompleteHead",
    "build_aux_heads",
]
