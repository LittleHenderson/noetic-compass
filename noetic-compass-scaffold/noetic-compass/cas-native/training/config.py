"""
TrainingConfig: Consolidated training configuration for CAS-Native v2.

Loads from YAML. Exposes every v2 hyperparameter and component flag per the
ADR cross-cutting hyperparameter table (see
`docs/architecture/cas_native_v2_adrs.md`).

When all `V2ComponentFlags` are False, the CASTrainer path is byte-equivalent
to the legacy v7.4 trainer; the v2 fields are still parsed but not instantiated.

Schema:
    component_flags:
        use_register_film: bool           # ADR-01
        use_emergent_register: bool       # ADR-02/03
        use_production_semantics: bool    # ADR-04
        use_rust_validation: bool         # ADR-06

    v2_hyperparameters:
        lambda_involution: float          # ADR-01 (default 0.1)
        lambda_emergent_binding: float    # CE loss weight for Ω_* binding
        lambda_production: float          # production-semantics loss weight
        lambda_rule_four: float           # Rule 4 compliance loss weight
        gumbel_tau_initial: float         # ADR-04 (default 10.0)
        gumbel_tau_final: float           # ADR-04 (default 0.1)
        gumbel_tau_anneal_steps: int      # ADR-04 (default 50_000)
        similarity_threshold: float       # ADR-03 (default 0.7, placeholder)
        registry_capacity: int            # ADR-02/03 (default 20)
        rust_cache_capacity: int          # ADR-06 (default 10_000)
        data_mix_cross_register: float    # ADR cross-cutting (0.60)
        data_mix_production: float        # ADR cross-cutting (0.40)

    v7_4_hyperparameters (preserved — legacy scalar knobs):
        lr, warmup_steps, max_steps, grad_clip, checkpoint_every, eval_every,
        target_nccs, checkpoint_dir,
        lambda_operator_balance, lambda_domain_coherence,
        lambda_rpm_satisfaction, lambda_inversion_penalty,
        lambda_cognitive_drift.

    omega_registry_config (optional): path to Ω_* registry YAML
        (defaults to ``cas-native/config/omega_registry.yaml`` when
        ``use_emergent_register`` is True).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Literal, Optional


@dataclass
class V2ComponentFlags:
    """Per-component v2 enable flags (ADR-01 / ADR-02 / ADR-04 / ADR-06)."""

    use_register_film: bool = True            # ADR-01 — FiLM register modulation
    use_emergent_register: bool = True        # ADR-02/03 — Ω_* binding pipeline
    use_production_semantics: bool = True     # ADR-04 — ProductionSemanticsHead
    use_rust_validation: bool = True          # ADR-06 — RustValidationBridge
    # ADR-07 — learned ExpressionProposerHead closes the Rule 4 gradient gap.
    # Default False at introduction (Wave 8A): opt-in for first-training-run
    # stability. Flipping this True instantiates the proposer and routes a
    # gradient-bearing score-based loss into the aggregate — byte-equivalent
    # to the pre-ADR-07 trainer when False.
    use_expression_proposer: bool = False

    def all_off(self) -> bool:
        """True when every v2 component is disabled (v7.4-equivalent path)."""
        return not (
            self.use_register_film
            or self.use_emergent_register
            or self.use_production_semantics
            or self.use_rust_validation
            or self.use_expression_proposer
        )


@dataclass
class V2Hyperparameters:
    """v2 hyperparameter block. Defaults match the ADR cross-cutting table."""

    # ADR-01 — InvolutionConstraintLoss weight on RegisterFiLM parameters.
    lambda_involution: float = 0.1

    # ADR-02/03 — Ω_* binding cross-entropy loss weight (placeholder 1.0).
    lambda_emergent_binding: float = 1.0

    # ADR-04 — production semantics yield / limiting-reagent loss weight.
    # ``lambda_production`` is the outer weight on the aggregated production
    # loss; the three sub-component weights below select how the aggregate
    # is formed from the limiting-reagent CE, theoretical-yield MSE, and
    # efficiency MSE sub-terms (Wave 7B Task 4, ADR-04).
    lambda_production: float = 1.0
    lambda_production_limiting_reagent: float = 1.0  # w_LR — CE over LR distribution
    lambda_production_yield: float = 1.0              # w_Y  — MSE on Y_T prediction
    lambda_production_efficiency: float = 0.5         # w_eff — derived, lower weight

    # ADR-06 — Rule 4 compliance loss weight (distance-to-valid penalty).
    lambda_rule_four: float = 1.0

    # ADR-04 — Gumbel-softmax / soft-min temperature annealing schedule.
    gumbel_tau_initial: float = 10.0
    gumbel_tau_final: float = 0.1
    gumbel_tau_anneal_steps: int = 50_000

    # ADR-03 — Ω_* similarity threshold (empirically untuned placeholder).
    similarity_threshold: float = 0.7

    # ADR-02/03 — Ω_* registry capacity.
    registry_capacity: int = 20

    # ADR-06 — Rust validation cache LRU capacity.
    rust_cache_capacity: int = 10_000

    # ADR cross-cutting — training data mix (sum ≈ 1.0).
    data_mix_cross_register: float = 0.60
    data_mix_production: float = 0.40

    # ADR-07 — ExpressionProposerHead hyperparameters. The outer weight
    # (``lambda_proposer_rule_four``) is applied in the trainer's loss
    # aggregation; the inner component weights (``lambda_proposer_noetic``
    # etc.) are routed to ``ProposerRuleFourLoss`` and weight the five
    # head components (Noetic CE, Domain CE, per-operand Register CE,
    # operand-count smooth-L1, named-emergent CE).
    lambda_proposer_rule_four: float = 0.5
    lambda_proposer_noetic: float = 1.0
    lambda_proposer_domain: float = 1.0
    lambda_proposer_register: float = 1.0
    lambda_proposer_count: float = 0.5
    lambda_proposer_named_emergent: float = 1.0
    # Proposer architecture knobs (see model/expression_proposer.py).
    proposer_bottleneck_dim: int = 32
    proposer_max_operands: int = 4

    # ADR-03 follow-up — null-space regularization for unused Omega_* slots.
    # Low default weight: this is regularization only, not primary signal.
    # v1 strategy is "origin" (pull toward zero vector) per ADR-03 follow-up
    # analysis — simplest, zero extra parameters, clear "pull toward null"
    # semantics. Other strategies available for future tuning:
    #   "learned_anchor"  — adds d_model parameters (one learned anchor)
    #   "mean_inactive"   — collective centering on mean of unused slots
    lambda_null_space_reg: float = 0.01
    null_space_reg_strategy: Literal[
        "origin", "learned_anchor", "mean_inactive"
    ] = "origin"

    def validate(self) -> None:
        """Raise ``ValueError`` on structurally invalid hyperparameters."""
        if self.gumbel_tau_initial <= 0 or self.gumbel_tau_final <= 0:
            raise ValueError(
                "gumbel_tau_initial / gumbel_tau_final must be > 0; got "
                f"{self.gumbel_tau_initial}, {self.gumbel_tau_final}"
            )
        if self.gumbel_tau_anneal_steps < 0:
            raise ValueError(
                f"gumbel_tau_anneal_steps must be >= 0, got "
                f"{self.gumbel_tau_anneal_steps}"
            )
        if not (0.0 <= self.similarity_threshold <= 1.0):
            raise ValueError(
                f"similarity_threshold must be in [0,1], got "
                f"{self.similarity_threshold}"
            )
        if self.registry_capacity <= 0:
            raise ValueError(
                f"registry_capacity must be > 0, got {self.registry_capacity}"
            )
        if self.rust_cache_capacity <= 0:
            raise ValueError(
                f"rust_cache_capacity must be > 0, got {self.rust_cache_capacity}"
            )
        if self.proposer_bottleneck_dim <= 0:
            raise ValueError(
                f"proposer_bottleneck_dim must be > 0, got "
                f"{self.proposer_bottleneck_dim}"
            )
        if self.proposer_max_operands <= 0:
            raise ValueError(
                f"proposer_max_operands must be > 0, got "
                f"{self.proposer_max_operands}"
            )
        mix_sum = self.data_mix_cross_register + self.data_mix_production
        if abs(mix_sum - 1.0) > 1e-3:
            raise ValueError(
                "data_mix_cross_register + data_mix_production should sum to "
                f"1.0, got {mix_sum}"
            )
        if self.lambda_null_space_reg < 0:
            raise ValueError(
                f"lambda_null_space_reg must be >= 0, got "
                f"{self.lambda_null_space_reg}"
            )
        if self.null_space_reg_strategy not in (
            "origin",
            "learned_anchor",
            "mean_inactive",
        ):
            raise ValueError(
                "null_space_reg_strategy must be one of "
                "{'origin', 'learned_anchor', 'mean_inactive'}, got "
                f"{self.null_space_reg_strategy!r}"
            )


@dataclass
class V74Hyperparameters:
    """Preserved v7.4 scalar knobs. Unchanged between v7.4 and v2 trainers."""

    lr: float = 1e-4
    warmup_steps: int = 1000
    max_steps: int = 100_000
    grad_clip: float = 1.0
    checkpoint_every: int = 1000
    eval_every: int = 500
    checkpoint_dir: str = "checkpoints"
    target_nccs: float = 75.0
    # Legacy CognitiveMetricLoss weights (preserved for v7.4 parity).
    lambda_operator_balance: float = 1.0
    lambda_domain_coherence: float = 1.0
    lambda_rpm_satisfaction: float = 1.0
    lambda_inversion_penalty: float = 1.0
    lambda_cognitive_drift: float = 1.0


@dataclass
class TrainingConfig:
    """Top-level training configuration. Consolidates flags + hyperparameters.

    Call ``TrainingConfig.from_yaml(path)`` to parse a YAML template (schema
    above). Call ``to_dict()`` to snapshot into checkpoint state_dict.
    """

    component_flags: V2ComponentFlags = field(default_factory=V2ComponentFlags)
    v2_hyperparameters: V2Hyperparameters = field(default_factory=V2Hyperparameters)
    v7_4_hyperparameters: V74Hyperparameters = field(
        default_factory=V74Hyperparameters
    )
    # Optional path to Ω_* registry YAML (ADR-03).
    omega_registry_config: Optional[str] = None

    # Checkpoint selection metric (Wave 8A v2-aware evaluation extension).
    #   "composite_v2" — 25/25/25/25 weighted composite of the four v2 metrics
    #       (register accuracy, Rule 4 compliance, Omega_* activation,
    #        production accuracy). Used when any v2 component flag is ON.
    #   "nccs"         — classic NCCS composite (v7.4 baseline). Used when
    #       every v2 component flag is OFF, or when callers explicitly want
    #       v7.4-style selection.
    #
    # Default is "composite_v2" because v2 components are on by default; a
    # v7.4-parity caller (all flags OFF) should explicitly set this to "nccs"
    # OR rely on the ``effective_checkpoint_selection_metric`` helper which
    # transparently falls back to "nccs" when all v2 flags are OFF.
    checkpoint_selection_metric: Literal["nccs", "composite_v2"] = "composite_v2"

    # ------------------------------------------------------------------ yaml

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TrainingConfig":
        """Load a training config from a YAML file."""
        import yaml  # local import keeps PyYAML optional at module-load time

        p = Path(path)
        with p.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TrainingConfig":
        """Construct from a (possibly-partial) dict."""
        flags = V2ComponentFlags(**(raw.get("component_flags") or {}))
        v2 = V2Hyperparameters(**(raw.get("v2_hyperparameters") or {}))
        v74 = V74Hyperparameters(**(raw.get("v7_4_hyperparameters") or {}))
        v2.validate()
        omega_cfg = raw.get("omega_registry_config", None)

        # Checkpoint selection metric — default "composite_v2"; accept either
        # top-level key or nested ``checkpoint_selection.metric`` (YAML shape).
        selection_raw: Any = raw.get("checkpoint_selection_metric")
        if selection_raw is None:
            nested = raw.get("checkpoint_selection") or {}
            if isinstance(nested, dict):
                selection_raw = nested.get("metric")
        selection: str = str(selection_raw) if selection_raw is not None else "composite_v2"
        if selection not in ("nccs", "composite_v2"):
            raise ValueError(
                "checkpoint_selection_metric must be 'nccs' or 'composite_v2', "
                f"got {selection!r}"
            )

        return cls(
            component_flags=flags,
            v2_hyperparameters=v2,
            v7_4_hyperparameters=v74,
            omega_registry_config=omega_cfg,
            checkpoint_selection_metric=selection,  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (suitable for JSON / checkpoint)."""
        return {
            "component_flags": asdict(self.component_flags),
            "v2_hyperparameters": asdict(self.v2_hyperparameters),
            "v7_4_hyperparameters": asdict(self.v7_4_hyperparameters),
            "omega_registry_config": self.omega_registry_config,
            "checkpoint_selection_metric": self.checkpoint_selection_metric,
        }

    def effective_checkpoint_selection_metric(self) -> str:
        """Return the metric name to actually use for best-checkpoint logic.

        Transparent backward-compatibility wrapper: when every v2 component
        flag is OFF, no v2 metric is computable (all four metrics would
        return ``None``), so selection must fall back to ``"nccs"`` even if
        the user set ``checkpoint_selection_metric="composite_v2"``.
        """
        if self.component_flags.all_off():
            return "nccs"
        return self.checkpoint_selection_metric

    # ----------------------------------------------------------- legacy view

    def as_legacy_trainer_dict(self) -> dict[str, Any]:
        """Flattened dict mirroring the legacy ``config`` kwarg accepted by
        ``CASTrainer.__init__`` (v7.4 path).
        """
        out: dict[str, Any] = {}
        for f in fields(self.v7_4_hyperparameters):
            out[f.name] = getattr(self.v7_4_hyperparameters, f.name)
        return out


__all__ = [
    "V2ComponentFlags",
    "V2Hyperparameters",
    "V74Hyperparameters",
    "TrainingConfig",
]
