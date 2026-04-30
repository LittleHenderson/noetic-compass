"""CAS Transformer structured-prediction head.

This is the first Step-7 model surface: given pooled model hidden states, predict
the typed CAS structure needed before rendering. It is intentionally separate
from the existing ExpressionProposerHead because this head targets CAS
Transformer turns and recoverable Level 3 eval labels, not only v7.7 Rule-4
expression proposals.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


TURN_TYPE_LABELS: tuple[str, ...] = (
    "OPEN",
    "ACK",
    "MIRROR",
    "CLARIFY",
    "EMPATHIZE",
    "ANSWER",
    "PLAN",
    "REFUSE",
    "REFUSE_CLAIM",
    "REPAIR",
    "CLOSE",
)

EXPRESSION_FAMILY_LABELS: tuple[str, ...] = (
    "state",
    "register_state",
    "production",
    "rule_four",
    "omega",
    "meta_logic",
)

TRANSITION_KIND_LABELS: tuple[str, ...] = (
    "state",
    "relation",
    "membership",
    "subset",
    "cluster_update",
    "rpm_gate",
    "production",
    "omega_bind",
    "inversion_check",
    "meta_logic_move",
    "surface_act",
    "ask_clarify",
    "repair",
)

DOMAIN_LABELS: tuple[str, ...] = ("P", "C", "E", "O")
DRIVE_LABELS: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
REGISTER_LABELS: tuple[str, ...] = ("T", "A", "f", "E")
REGISTER_MODE_LABELS: tuple[str, ...] = (
    "none",
    "single",
    "set_spec",
    "co_presence",
    "integration",
)
META_RELATION_LABELS: tuple[str, ...] = (
    "membership",
    "subset",
    "product",
    "cover",
    "partition",
    "pullback",
    "authority",
    "evidence",
    "trace_nesting",
)
AUTHORITY_LABELS: tuple[str, ...] = ("none", "admitted", "blocked")


@dataclass(frozen=True)
class StructuredPrediction:
    """Discrete inference result from the structured-prediction head."""

    turn_type: str
    expression_family: str
    transition_kind: str
    noetic: int
    domain: str
    drive: str
    registers: tuple[str, ...]
    register_mode: str
    authority: str
    has_omega: bool
    has_meta_logic: bool


class StructuredPredictionHead(nn.Module):
    """Predict CAS Transformer structure from hidden states.

    Args:
        d_model: input hidden dimension.
        bottleneck_dim: shared low-rank hidden width.

    Input shape:
        ``(B, d_model)`` or ``(B, seq_len, d_model)``. Sequence input is
        mean-pooled, optionally with an attention mask.
    """

    def __init__(self, d_model: int, bottleneck_dim: int = 64) -> None:
        super().__init__()
        if d_model <= 0:
            raise ValueError(f"d_model must be > 0, got {d_model}")
        if bottleneck_dim <= 0:
            raise ValueError(f"bottleneck_dim must be > 0, got {bottleneck_dim}")

        self.d_model = d_model
        self.bottleneck_dim = bottleneck_dim
        self.backbone = nn.Sequential(
            nn.Linear(d_model, bottleneck_dim),
            nn.GELU(),
            nn.LayerNorm(bottleneck_dim),
        )

        self.turn_type_head = nn.Linear(bottleneck_dim, len(TURN_TYPE_LABELS))
        self.expression_family_head = nn.Linear(
            bottleneck_dim, len(EXPRESSION_FAMILY_LABELS)
        )
        self.transition_kind_head = nn.Linear(
            bottleneck_dim, len(TRANSITION_KIND_LABELS)
        )
        self.noetic_head = nn.Linear(bottleneck_dim, 10)
        self.domain_head = nn.Linear(bottleneck_dim, len(DOMAIN_LABELS))
        self.drive_head = nn.Linear(bottleneck_dim, len(DRIVE_LABELS))
        self.register_head = nn.Linear(bottleneck_dim, len(REGISTER_LABELS))
        self.register_mode_head = nn.Linear(
            bottleneck_dim, len(REGISTER_MODE_LABELS)
        )
        self.meta_relation_head = nn.Linear(
            bottleneck_dim, len(META_RELATION_LABELS)
        )
        self.authority_head = nn.Linear(bottleneck_dim, len(AUTHORITY_LABELS))
        self.omega_head = nn.Linear(bottleneck_dim, 2)
        self.meta_logic_head = nn.Linear(bottleneck_dim, 2)

    @property
    def parameter_count(self) -> int:
        return sum(param.numel() for param in self.parameters())

    def _pool(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if hidden_states.dim() == 2:
            return hidden_states
        if hidden_states.dim() != 3:
            raise ValueError(
                "StructuredPredictionHead expects 2-D or 3-D hidden states; "
                f"got shape {tuple(hidden_states.shape)}"
            )
        if attention_mask is None:
            return hidden_states.mean(dim=1)
        weights = attention_mask.to(hidden_states.dtype).unsqueeze(-1)
        return (hidden_states * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        pooled = self._pool(hidden_states, attention_mask)
        z = self.backbone(pooled)
        return {
            "turn_type_logits": self.turn_type_head(z),
            "expression_family_logits": self.expression_family_head(z),
            "transition_kind_logits": self.transition_kind_head(z),
            "noetic_logits": self.noetic_head(z),
            "domain_logits": self.domain_head(z),
            "drive_logits": self.drive_head(z),
            "register_logits": self.register_head(z),
            "register_mode_logits": self.register_mode_head(z),
            "meta_relation_logits": self.meta_relation_head(z),
            "authority_logits": self.authority_head(z),
            "omega_logits": self.omega_head(z),
            "meta_logic_logits": self.meta_logic_head(z),
        }

    def propose(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        register_threshold: float = 0.0,
        meta_threshold: float = 0.0,
    ) -> list[StructuredPrediction]:
        outputs = self(hidden_states, attention_mask=attention_mask)
        batch = outputs["turn_type_logits"].shape[0]
        register_active = outputs["register_logits"] > register_threshold
        meta_active = outputs["meta_relation_logits"] > meta_threshold
        proposals: list[StructuredPrediction] = []
        for i in range(batch):
            registers = tuple(
                REGISTER_LABELS[j]
                for j in range(len(REGISTER_LABELS))
                if bool(register_active[i, j].item())
            )
            if not registers:
                registers = (
                    REGISTER_LABELS[int(outputs["register_logits"][i].argmax().item())],
                )
            proposals.append(
                StructuredPrediction(
                    turn_type=_argmax_label(outputs["turn_type_logits"][i], TURN_TYPE_LABELS),
                    expression_family=_argmax_label(
                        outputs["expression_family_logits"][i],
                        EXPRESSION_FAMILY_LABELS,
                    ),
                    transition_kind=_argmax_label(
                        outputs["transition_kind_logits"][i],
                        TRANSITION_KIND_LABELS,
                    ),
                    noetic=int(outputs["noetic_logits"][i].argmax().item()),
                    domain=_argmax_label(outputs["domain_logits"][i], DOMAIN_LABELS),
                    drive=_argmax_label(outputs["drive_logits"][i], DRIVE_LABELS),
                    registers=registers,
                    register_mode=_argmax_label(
                        outputs["register_mode_logits"][i],
                        REGISTER_MODE_LABELS,
                    ),
                    authority=_argmax_label(outputs["authority_logits"][i], AUTHORITY_LABELS),
                    has_omega=bool(outputs["omega_logits"][i].argmax().item()),
                    has_meta_logic=bool(outputs["meta_logic_logits"][i].argmax().item())
                    or bool(meta_active[i].any().item()),
                )
            )
        return proposals


def structured_prediction_loss(
    outputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    *,
    lambda_register: float = 1.0,
    lambda_meta_relation: float = 1.0,
) -> torch.Tensor:
    """Multi-head supervised loss for structured prediction targets."""

    loss = torch.tensor(0.0, device=next(iter(outputs.values())).device)
    ce_pairs = (
        ("turn_type_logits", "turn_type"),
        ("expression_family_logits", "expression_family"),
        ("transition_kind_logits", "transition_kind"),
        ("noetic_logits", "noetic"),
        ("domain_logits", "domain"),
        ("drive_logits", "drive"),
        ("register_mode_logits", "register_mode"),
        ("authority_logits", "authority"),
        ("omega_logits", "has_omega"),
        ("meta_logic_logits", "has_meta_logic"),
    )
    for logit_key, target_key in ce_pairs:
        if target_key in targets:
            loss = loss + F.cross_entropy(outputs[logit_key], targets[target_key])
    if "registers" in targets:
        loss = loss + lambda_register * F.binary_cross_entropy_with_logits(
            outputs["register_logits"],
            targets["registers"].to(outputs["register_logits"].dtype),
        )
    if "meta_relations" in targets:
        loss = loss + lambda_meta_relation * F.binary_cross_entropy_with_logits(
            outputs["meta_relation_logits"],
            targets["meta_relations"].to(outputs["meta_relation_logits"].dtype),
        )
    return loss


def _argmax_label(logits: torch.Tensor, labels: tuple[str, ...]) -> str:
    return labels[int(logits.argmax().item())]

