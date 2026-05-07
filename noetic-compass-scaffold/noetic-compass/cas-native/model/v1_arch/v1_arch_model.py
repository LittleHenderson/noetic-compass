"""V1ArchModel — Path C-1 v1-arch test variant.

Wires :class:`SimplexStateEncoder` + :class:`FisherRaoLoss` +
:class:`RPMGateStub` on top of the EXISTING transformer decoder
(:class:`cas_native.model.cas_native_model.CASNativeModel`). The
architectural change in C-1 is on the ENCODER side — the decoder is
preserved verbatim so existing tokenizer / checkpoint formats and
existing CASNativeModel callers are unaffected.

Forward signature::

    out = v1_arch(input_ids, attention_mask=None, transition_op=None)

Returns dict (load-bearing for Mode 7 trace):

    {
        # Simplex-side (the architectural delta)
        "p_state_init":   (B, 40),
        "p_state_trace":  (B, S, 40),
        "p_state_final":  (B, 40),

        # RPM stub
        "rpm_gate_result": RPMGateResult(passed, broken_at, evidence),

        # Existing CASNativeModel head outputs (decoder side)
        "logits":          (B, S, vocab_size),
        "hidden_states":   (B, S, d_model),
        "pooled_hidden_state": (B, d_model),
        "cognitive_state": (B, S, 40),  # legacy decoder simplex
        "raw_cognitive_state": (B, S, 40),
        "rpm_satisfaction": scalar,    # legacy soft-gate signal
        "inversion_flags": (B, 7),
        "topos_truth_values": (B, num_props, 3),
        "lacunarity_scores": ...,
        "lacunarity_meta":   ...,
    }

C-1 design notes:

- The simplex encoder runs IN PARALLEL to the CASNativeModel decoder,
  not as a replacement of its embedding stack. Why: the falsification
  gate ("within 5-10pp of K=9 on CAS prediction; better trace
  quality") demands we measure the simplex encoder's prediction
  signal independently of whatever the legacy decoder produces. If we
  spliced the simplex encoder into the decoder's embedding pipeline
  we'd lose that ablation surface.
- The simplex encoder consumes ``input_ids`` and emits ``p_state_*``;
  the legacy CASNativeModel also consumes ``input_ids`` and emits its
  own ``cognitive_state`` (still a 40-d simplex via the legacy
  ``CognitiveStateEmbedding``). Both surfaces are returned. The
  Path D training script picks whichever to optimize against the
  Fisher-Rao loss.
- For C-1 tests we compute RPM gate evidence on
  ``(p_state_init, p_state_final)`` of the simplex encoder. For
  arbitrary token positions (per-step admissibility) the C-2/C-3
  follow-up will need to call the gate on consecutive trace frames.

Hard rules (CLAUDE.md, ``feedback_no_foreign_architecture_cas_only``):
- No foreign pretrained weights. CASNativeModel is project-native.
- Δ°₃₉ open simplex preserved (CAS Correction 4).
- Drive / Register stay non-simplex (Path C §3.1.3a/b) — but C-1 only
  ships the base manifold; those heads come in C-2/C-3.
- Compiler is the source of admissibility truth (consumed via
  RPMGateStub, which delegates to ``api.notation.compiler._is_admissible``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Union

import torch
import torch.nn as nn

from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel

from .fisher_rao_loss import FisherRaoLoss
from .rpm_gate_stub import RPMGateResult, RPMGateStub
from .simplex_state_encoder import (
    NUM_COGNITIVE_STATES,
    SimplexStateEncoder,
    SimplexStateEncoderConfig,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class V1ArchConfig:
    """Config for the C-1 v1-arch test variant.

    Attributes
    ----------
    simplex_encoder:
        :class:`SimplexStateEncoderConfig`. ``vocab_size`` MUST match
        the legacy decoder's vocab (the same input_ids are routed to
        both).
    cas_native:
        :class:`CASNativeConfig`. The legacy transformer decoder.
        Preserved verbatim so existing checkpoint-loading paths are
        unaffected.
    fisher_rao_drift_weight:
        Drift-penalty weight for the FisherRaoLoss. Default 0 (off);
        the trainer enables it during structural-loss warmup.
    fisher_rao_smoothing:
        GT smoothing for the FisherRaoLoss. Default 0.001 per Path C
        C-1 spec.
    """

    simplex_encoder: SimplexStateEncoderConfig = field(
        default_factory=SimplexStateEncoderConfig
    )
    cas_native: CASNativeConfig = field(default_factory=CASNativeConfig)
    fisher_rao_drift_weight: float = 0.0
    fisher_rao_smoothing: float = 0.001

    def __post_init__(self) -> None:
        if self.simplex_encoder.vocab_size != self.cas_native.vocab_size:
            # Make the test-fixture mismatch obvious — the same
            # ``input_ids`` go to both pieces, so vocab sizes must agree.
            raise ValueError(
                f"V1ArchConfig: simplex_encoder.vocab_size="
                f"{self.simplex_encoder.vocab_size} must equal "
                f"cas_native.vocab_size={self.cas_native.vocab_size} — both "
                "modules consume the same input_ids stream."
            )


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class V1ArchModel(nn.Module):
    """Path C-1 v1-arch test variant.

    Wires the simplex encoder, Fisher-Rao loss, RPM stub, and the
    existing transformer decoder (CASNativeModel) into one module.
    """

    def __init__(self, config: Optional[V1ArchConfig] = None) -> None:
        super().__init__()
        if config is None:
            config = V1ArchConfig()
        self.config = config

        # Architectural delta — simplex encoder.
        self.simplex_encoder = SimplexStateEncoder(config.simplex_encoder)

        # RPM stub (no parameters, pure structural check).
        self.rpm_gate_stub = RPMGateStub()

        # Fisher-Rao loss (no parameters; held here for convenience so
        # the trainer can call ``model.fisher_rao_loss(...)`` directly).
        self.fisher_rao_loss = FisherRaoLoss(
            num_classes=NUM_COGNITIVE_STATES,
            epsilon_smooth=config.fisher_rao_smoothing,
            drift_weight=config.fisher_rao_drift_weight,
        )

        # Preserved transformer decoder (legacy CASNativeModel).
        self.cas_native_decoder = CASNativeModel(config.cas_native)

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        *,
        transition_op: Optional[
            Union[int, str, Sequence[Union[int, str]], torch.Tensor]
        ] = None,
        register_activations: Optional[torch.Tensor] = None,
        return_trace: Optional[bool] = None,
    ) -> dict[str, torch.Tensor]:
        """Run the v1-arch end-to-end forward.

        Args:
            input_ids: ``(B, S)`` long tensor.
            attention_mask: Optional ``(B, S)`` mask (1 = real, 0 = pad).
            transition_op: Per-example transition-op identifier
                consumed by the RPM stub. When ``None`` the stub is
                skipped (and ``rpm_gate_result`` is ``None`` in the
                output dict).
            register_activations: Optional ``(B, 40, 4)`` register mask
                forwarded to the legacy decoder; preserves the existing
                forward contract.
            return_trace: Override the simplex encoder's
                ``return_trace`` config. When False, ``p_state_trace``
                is omitted from the output.

        Returns:
            Forward dict (see module docstring).
        """
        if input_ids.dim() != 2:
            raise ValueError(
                f"input_ids must be (B, S); got shape {tuple(input_ids.shape)}."
            )

        # ------- Simplex encoder -------
        enc_out = self.simplex_encoder(
            input_ids,
            attention_mask=attention_mask,
            return_trace=return_trace,
        )

        # ------- RPM gate stub -------
        if transition_op is not None:
            rpm_result: Optional[RPMGateResult] = self.rpm_gate_stub(
                enc_out["p_state_init"],
                enc_out["p_state_final"],
                transition_op,
            )
        else:
            rpm_result = None

        # ------- Legacy transformer decoder -------
        decoder_out = self.cas_native_decoder(
            input_ids,
            attention_mask=attention_mask,
            register_activations=register_activations,
        )

        # ------- Merge and return -------
        out: dict = dict(decoder_out)
        out["p_state_init"] = enc_out["p_state_init"]
        out["p_state_final"] = enc_out["p_state_final"]
        if "p_state_trace" in enc_out:
            out["p_state_trace"] = enc_out["p_state_trace"]
        out["simplex_hidden"] = enc_out["hidden"]
        out["rpm_gate_result"] = rpm_result
        return out

    # ------------------------------------------------------------------
    # Convenience: compute the C-1 training loss.
    # ------------------------------------------------------------------

    def compute_loss(
        self,
        forward_out: dict,
        target_state_index: torch.Tensor,
        *,
        ce_logits: Optional[torch.Tensor] = None,
        ce_labels: Optional[torch.Tensor] = None,
        ce_weight: float = 1.0,
        fr_weight: float = 1.0,
    ) -> dict[str, torch.Tensor]:
        """Compute Fisher-Rao + optional cross-entropy auxiliary.

        This is a convenience entry point for the Path D training
        script. It is NOT called during C-1 tests — those drive the
        components directly. Provided here so the trainer doesn't need
        to know the internal layout of forward_out.

        Args:
            forward_out: dict returned from :meth:`forward`.
            target_state_index: ``(B,)`` integer cognitive-state target.
            ce_logits: Optional ``(B, K)`` logits for an auxiliary
                cross-entropy term (e.g. existing structured-prediction
                head output).
            ce_labels: Required when ``ce_logits`` is provided.
            ce_weight, fr_weight: Loss-component weights.
        """
        fr_pack = self.fisher_rao_loss(
            forward_out["p_state_final"],
            target_state_index,
            target_is_index=True,
            p_state_trace=forward_out.get("p_state_trace"),
        )
        total = fr_weight * fr_pack["loss"]
        ce_loss = torch.zeros((), device=total.device, dtype=total.dtype)
        if ce_logits is not None:
            if ce_labels is None:
                raise ValueError("ce_labels required when ce_logits is provided.")
            ce_loss = nn.functional.cross_entropy(ce_logits, ce_labels)
            total = total + ce_weight * ce_loss

        return {
            "loss": total,
            "fr_distance": fr_pack["distance"],
            "fr_drift": fr_pack["drift"],
            "ce_loss": ce_loss,
        }


__all__ = [
    "V1ArchModel",
    "V1ArchConfig",
]
