"""
CASTrainer: Training loop for the CAS-Native model.

Features:
  - Adam optimizer with cosine LR schedule (warmup 1000 steps)
  - Gradient clipping at 1.0
  - Checkpoint saving every 1000 steps
  - Optional W&B logging (WANDB_ENABLED env var)
  - Evaluation every 500 steps
  - Training target: NCCS >= 75 (Gold certification)

v2 extensions (ADR-01 / ADR-02 / ADR-04 / ADR-06):
  - Optional RegisterFiLM + InvolutionConstraintLoss (ADR-01)
  - Optional EmergentRegisterPipeline + Ω_* binding CE loss (ADR-02/03)
  - Optional ProductionSemanticsHead + soft yield loss (ADR-04)
  - Optional RustValidationBridge for per-batch Rule 4 compliance (ADR-06)
  - Gumbel-softmax temperature annealing via DifferentiableStoichiometry
  - Checkpoint state_dict includes v2 components + TrainingConfig snapshot

When all ``V2ComponentFlags`` are False, the trainer path is byte-equivalent
to the legacy v7.4 trainer (regression-tested). Backward compatibility with
the legacy ``config: dict`` kwarg is preserved.
"""

from __future__ import annotations

import os
import time
import warnings
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional, Union

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from torch.utils.data import DataLoader

from ..model.cas_native_model import CASNativeModel, CASNativeConfig
from ..model.loss import (
    CognitiveMetricLoss,
    InvolutionConstraintLoss,
    NullSpaceRegularizationLoss,
    ProposerRuleFourLoss,
)
from ..model.expression_proposer import (
    ExpressionProposerHead,
    OPERAND_COUNT_BUCKETS,
)
from ..model.embedding import (
    CognitiveStateEmbedding,
    CognitiveStateEmbeddingWithRegister,
    NUM_COGNITIVE_STATES,
)
from ..model.register_film import NUM_REGISTERS, REGISTER_INDEX
from ..model.emergent_register import EmergentRegisterPipeline
from ..model.production_semantics import ProductionSemanticsHead
from .config import TrainingConfig, V2ComponentFlags

try:  # RustValidationBridge depends on the validation package being importable.
    from ..validation.rust_bridge import RustValidationBridge
    from ..validation.structural_hash import StructuralPattern
except Exception:  # pragma: no cover - defensive
    RustValidationBridge = None  # type: ignore[assignment]
    StructuralPattern = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# CASTrainer
# ---------------------------------------------------------------------------


class CASTrainer:
    """Training loop for the CAS-Native model.

    Manages the full training lifecycle: optimizer setup, scheduling,
    gradient clipping, checkpointing, logging, and evaluation.

    Accepts either a legacy v7.4 ``config: dict`` OR a v2 ``TrainingConfig``
    dataclass. When a ``TrainingConfig`` is supplied, v2 component flags gate
    instantiation and loss aggregation. When all flags are False, behavior is
    byte-equivalent to the legacy v7.4 trainer.
    """

    def __init__(
        self,
        model: CASNativeModel,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        config: Optional[Union[dict[str, Any], TrainingConfig]] = None,
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader

        # ------------------------------------------------------------------
        # Config handling — legacy dict and v2 TrainingConfig both supported.
        # ------------------------------------------------------------------
        self.training_config: Optional[TrainingConfig] = None
        legacy_cfg: dict[str, Any]
        if isinstance(config, TrainingConfig):
            self.training_config = config
            legacy_cfg = config.as_legacy_trainer_dict()
            self.v2_flags = config.component_flags
            self.v2_hp = config.v2_hyperparameters
        else:
            legacy_cfg = dict(config or {})
            self.v2_flags = V2ComponentFlags(
                use_register_film=False,
                use_emergent_register=False,
                use_production_semantics=False,
                use_rust_validation=False,
                use_expression_proposer=False,  # ADR-07 off in legacy path
            )
            self.v2_hp = TrainingConfig().v2_hyperparameters  # defaults only

        cfg = legacy_cfg
        self.lr = cfg.get("lr", 1e-4)
        self.warmup_steps = cfg.get("warmup_steps", 1000)
        self.max_steps = cfg.get("max_steps", 100000)
        self.grad_clip = cfg.get("grad_clip", 1.0)
        self.checkpoint_every = cfg.get("checkpoint_every", 1000)
        self.eval_every = cfg.get("eval_every", 500)
        self.checkpoint_dir = Path(cfg.get("checkpoint_dir", "checkpoints"))
        self.target_nccs = cfg.get("target_nccs", 75.0)

        # Loss function (v7.4 baseline; unchanged in v2 path).
        self.loss_fn = CognitiveMetricLoss(
            lambda_operator_balance=cfg.get("lambda_operator_balance", 1.0),
            lambda_domain_coherence=cfg.get("lambda_domain_coherence", 1.0),
            lambda_rpm_satisfaction=cfg.get("lambda_rpm_satisfaction", 1.0),
            lambda_inversion_penalty=cfg.get("lambda_inversion_penalty", 1.0),
            lambda_cognitive_drift=cfg.get("lambda_cognitive_drift", 1.0),
        )

        # ------------------------------------------------------------------
        # v2 components — conditionally instantiated. Registered as submodules
        # so they participate in parameters() / state_dict() automatically.
        # ------------------------------------------------------------------
        self._register_film_module: Optional[nn.Module] = None
        self._register_film_dmodel_module: Optional[nn.Module] = None
        self._involution_loss: Optional[InvolutionConstraintLoss] = None
        self._emergent_pipeline: Optional[EmergentRegisterPipeline] = None
        self._production_head: Optional[ProductionSemanticsHead] = None
        self._rust_bridge: Any = None
        # ADR-03 follow-up null-space regularization module — lazily created
        # on first call in ``_compute_null_space_reg_loss``.
        self._null_space_loss_module: Optional[NullSpaceRegularizationLoss] = None
        # ADR-07 — learned ExpressionProposerHead + score-based loss.
        self._expression_proposer: Optional[ExpressionProposerHead] = None
        self._proposer_loss_fn: Optional[ProposerRuleFourLoss] = None

        # v2 sub-modules live on a container attached to the model so
        # state_dict() round-trip captures them without needing trainer-side
        # serialization logic.
        if not hasattr(self.model, "v2_components"):
            self.model.v2_components = nn.ModuleDict()

        self._init_v2_components()

        # Optimizer — created AFTER v2 components so their parameters are
        # included in the optimizer param groups.
        self.optimizer = Adam(
            self.model.parameters(),
            lr=self.lr,
            betas=(0.9, 0.98),
            eps=1e-9,
        )

        # LR schedule: linear warmup then cosine annealing.
        warmup_scheduler = LinearLR(
            self.optimizer,
            start_factor=1e-8 / self.lr if self.lr > 0 else 1.0,
            end_factor=1.0,
            total_iters=self.warmup_steps,
        )
        cosine_scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=max(self.max_steps - self.warmup_steps, 1),
            eta_min=self.lr * 0.01,
        )
        self.scheduler = SequentialLR(
            self.optimizer,
            schedulers=[warmup_scheduler, cosine_scheduler],
            milestones=[self.warmup_steps],
        )

        # W&B logging (optional).
        self.wandb_enabled = os.environ.get("WANDB_ENABLED", "false").lower() == "true"
        self._wandb = None
        if self.wandb_enabled:
            try:
                import wandb
                self._wandb = wandb
            except ImportError:
                self.wandb_enabled = False

        # Training state.
        self.global_step = 0
        self.best_val_loss = float("inf")
        # Wave 8A v2-aware checkpoint selection — composite_v2 is in [0, 1]
        # higher-is-better, so ``best`` starts at -inf and is bumped on each
        # improvement. ``best_val_loss`` remains tracked for the nccs /
        # v7.4-parity path.
        self.best_composite_v2: float = float("-inf")
        self.device = next(model.parameters()).device

        # Gumbel-softmax current temperature — annealed per step.
        self.current_tau: float = float(self.v2_hp.gumbel_tau_initial)

    # ------------------------------------------------------------------ v2

    def _init_v2_components(self) -> None:
        """Instantiate v2 components gated by ``self.v2_flags``.

        Components are attached to ``self.model.v2_components`` so the base
        ``state_dict`` round-trip captures them. Disabled components remain
        ``None`` on the trainer and are absent from the ModuleDict.
        """
        flags = self.v2_flags
        hp = self.v2_hp

        # ADR-01 — RegisterFiLM + involution constraint loss.
        if flags.use_register_film:
            # Wrap the existing cognitive embedding with a register-aware variant
            # (backward-compatible: register_idx=None yields identical outputs
            # to the base embedding).
            d_model = self.model.config.d_model
            reg_emb = CognitiveStateEmbeddingWithRegister(d_model=d_model)
            # Copy base projection weights so neutral-register forward matches
            # the pre-existing embedding at init (byte-compat check relies on
            # register_idx=None short-circuit — not on weight copy).
            self.model.v2_components["register_embedding"] = reg_emb
            self._register_film_module = reg_emb.register_film
            # Base-d_model FiLM is the surface binding heads consume — keeping
            # it separate from the 40-dim simplex FiLM ensures emergent-binding
            # aligns with `CASNativeConfig.d_model` at any width (not just 128).
            self._register_film_dmodel_module = reg_emb.register_film_dmodel
            self._involution_loss = InvolutionConstraintLoss(
                lambda_involution=hp.lambda_involution,
            )

        # ADR-02/03 — EmergentRegisterPipeline.
        if flags.use_emergent_register:
            pipeline = EmergentRegisterPipeline(
                d_model=self.model.config.d_model,
                registry_capacity=hp.registry_capacity,
                similarity_threshold=hp.similarity_threshold,
            )
            # Populate Ω_* registry from YAML config when present.
            if (
                self.training_config is not None
                and self.training_config.omega_registry_config is not None
            ):
                registry_path = Path(self.training_config.omega_registry_config)
                if registry_path.exists():
                    try:
                        pipeline.load_registry_config(registry_path)
                    except Exception as exc:  # pragma: no cover - defensive
                        warnings.warn(
                            f"EmergentRegisterPipeline: failed to load registry "
                            f"config {registry_path}: {exc}",
                            RuntimeWarning,
                            stacklevel=2,
                        )
            self.model.v2_components["emergent_register"] = pipeline
            self._emergent_pipeline = pipeline

        # ADR-04 — ProductionSemanticsHead.
        if flags.use_production_semantics:
            head = ProductionSemanticsHead(
                d_model=self.model.config.d_model,
                tau_initial=hp.gumbel_tau_initial,
                tau_final=hp.gumbel_tau_final,
                tau_anneal_steps=hp.gumbel_tau_anneal_steps,
            )
            self.model.v2_components["production_semantics"] = head
            self._production_head = head

        # ADR-06 — RustValidationBridge (not an nn.Module; lives on trainer).
        if flags.use_rust_validation and RustValidationBridge is not None:
            self._rust_bridge = RustValidationBridge(
                cache_capacity=hp.rust_cache_capacity,
            )

        # ADR-07 — learned ExpressionProposerHead + ProposerRuleFourLoss.
        if flags.use_expression_proposer:
            proposer = ExpressionProposerHead(
                d_model=self.model.config.d_model,
                bottleneck_dim=hp.proposer_bottleneck_dim,
                max_operands=hp.proposer_max_operands,
            )
            self.model.v2_components["expression_proposer"] = proposer
            self._expression_proposer = proposer
            self._proposer_loss_fn = ProposerRuleFourLoss(
                lambda_noetic=hp.lambda_proposer_noetic,
                lambda_domain=hp.lambda_proposer_domain,
                lambda_register=hp.lambda_proposer_register,
                lambda_count=hp.lambda_proposer_count,
                lambda_named_emergent=hp.lambda_proposer_named_emergent,
            )

    # ------------------------------------------------------------------ v2 props

    @property
    def register_film(self):
        return self._register_film_module

    @property
    def emergent_pipeline(self):
        return self._emergent_pipeline

    @property
    def production_head(self):
        return self._production_head

    @property
    def rust_bridge(self):
        return self._rust_bridge

    @property
    def expression_proposer(self):
        """Access the ADR-07 ExpressionProposerHead (None when disabled)."""
        return self._expression_proposer

    @property
    def proposer_loss_fn(self):
        """Access the ADR-07 ProposerRuleFourLoss (None when disabled)."""
        return self._proposer_loss_fn

    # ------------------------------------------------------------------ checkpoints

    def _save_checkpoint(self, tag: str = "step") -> Path:
        """Save a model checkpoint."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        ckpt_path = self.checkpoint_dir / f"cas_native_{tag}_{self.global_step}.pt"
        payload: dict[str, Any] = {
            "global_step": self.global_step,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "best_val_loss": self.best_val_loss,
            "best_composite_v2": self.best_composite_v2,
            "current_tau": self.current_tau,
        }
        if self.training_config is not None:
            payload["training_config"] = self.training_config.to_dict()
        torch.save(payload, ckpt_path)
        return ckpt_path

    def load_checkpoint(self, ckpt_path: str | Path) -> None:
        """Load a model checkpoint.

        Missing keys are tolerated so a v7.4-style checkpoint (no v2 entries)
        can be loaded into a v2 trainer; the absent v2 submodules retain their
        random initialization.
        """
        ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        # ``strict=False`` supports v7.4 -> v2 checkpoint upgrade per ADR-05.
        self.model.load_state_dict(ckpt["model_state_dict"], strict=False)
        if "optimizer_state_dict" in ckpt:
            try:
                self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
            except (ValueError, KeyError):
                # Optimizer state may not align when param shape changes
                # (e.g. v7.4 -> v2). Skip optimizer restoration in that case.
                warnings.warn(
                    "Optimizer state incompatible with current model; "
                    "continuing with freshly-initialized optimizer.",
                    RuntimeWarning,
                    stacklevel=2,
                )
        if "scheduler_state_dict" in ckpt:
            try:
                self.scheduler.load_state_dict(ckpt["scheduler_state_dict"])
            except (ValueError, KeyError):
                pass
        self.global_step = ckpt.get("global_step", 0)
        self.best_val_loss = ckpt.get("best_val_loss", float("inf"))
        self.best_composite_v2 = float(
            ckpt.get("best_composite_v2", float("-inf"))
        )
        self.current_tau = float(
            ckpt.get("current_tau", self.v2_hp.gumbel_tau_initial)
        )

    # ------------------------------------------------------------------ targets

    @staticmethod
    def _normalize_score_list(
        raw_scores: Any,
        expected_len: int,
        scale_hint: float = 10.0,
    ) -> Optional[torch.Tensor]:
        """Normalize score lists that may arrive in 0-1 or 0-10 form."""
        if not isinstance(raw_scores, (list, tuple)) or len(raw_scores) != expected_len:
            return None

        tensor = torch.tensor(raw_scores, dtype=torch.float32)
        if torch.isnan(tensor).any():
            return None

        max_score = float(tensor.max().item())
        if max_score > 1.0:
            tensor = tensor / scale_hint

        return tensor.clamp(min=1e-6, max=1.0)

    def _build_sample_target_state(self, cas_scores: dict[str, Any]) -> torch.Tensor:
        """Construct a 40-state simplex target from labeled CAS scores.

        Operator scores shape the within-domain distribution. Domain scores, when
        present, weight the four domains. If no structured labels are available,
        the fallback is uniform.
        """
        operator_scores = self._normalize_score_list(
            cas_scores.get("operator_scores"),
            expected_len=10,
        )
        domain_scores = self._normalize_score_list(
            cas_scores.get("domain_scores"),
            expected_len=4,
        )

        if operator_scores is None:
            return torch.ones(40, device=self.device) / 40.0

        if domain_scores is None:
            domain_scores = torch.ones(4, dtype=torch.float32)

        target = domain_scores.unsqueeze(-1) * operator_scores.unsqueeze(0)
        target = target.reshape(-1).to(self.device)
        target = target / target.sum().clamp_min(1e-8)
        return target

    def _generate_target_cognitive_state(
        self,
        cas_scores_batch: list[dict[str, Any]],
        seq_len: int,
    ) -> torch.Tensor:
        """Generate per-sample target cognitive states on the open simplex."""
        if not cas_scores_batch:
            return torch.ones(0, seq_len, 40, device=self.device)

        sample_targets = [self._build_sample_target_state(scores) for scores in cas_scores_batch]
        target = torch.stack(sample_targets, dim=0).unsqueeze(1).repeat(1, seq_len, 1)
        return target

    # ------------------------------------------------------------------ v2 losses

    def _compute_involution_loss(self) -> Optional[torch.Tensor]:
        """Soft involution regularizer on RegisterFiLM parameters (ADR-01)."""
        if self._involution_loss is None or self._register_film_module is None:
            return None
        return self._involution_loss.involution_loss(self._register_film_module)

    # -------------------------------------------------- register activations

    def _build_register_activations(
        self,
        register_labels_batch: list[list[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Build a ``(batch, 40, 4)`` bool activation tensor from label lists.

        Training data (`data_format.md`) stores per-example register_labels
        as ``[{"position": int, "register": str}, ...]``. Position indexes
        into the 40 cognitive-state slots (not sequence positions). This
        helper buckets those labels into a dense per-position per-register
        mask suitable for the model's forward-path FiLM routing (Task 1).

        Labels with out-of-range positions or unrecognized registers are
        silently skipped — the trainer's scaffold data pipeline validates
        upstream, and defensive tolerance here keeps a malformed batch from
        crashing the training loop.

        Returns None when the batch carries zero register labels — that
        signal lets the forward pass short-circuit to the byte-equivalent
        v7.4 path.
        """
        batch_size = len(register_labels_batch)
        if batch_size == 0:
            return None

        any_labels = any(bool(lst) for lst in register_labels_batch)
        if not any_labels:
            return None

        acts = torch.zeros(
            batch_size,
            NUM_COGNITIVE_STATES,
            NUM_REGISTERS,
            dtype=torch.bool,
            device=self.device,
        )
        for i, labels in enumerate(register_labels_batch):
            for entry in labels or []:
                pos = entry.get("position")
                reg = entry.get("register")
                if pos is None or reg is None:
                    continue
                if not (0 <= int(pos) < NUM_COGNITIVE_STATES):
                    continue
                r_idx = REGISTER_INDEX.get(reg)
                if r_idx is None:
                    continue
                acts[i, int(pos), r_idx] = True
        return acts

    def _compute_emergent_binding_loss(
        self,
        hidden_states: torch.Tensor,
        omega_labels_batch: list[list[dict[str, Any]]],
        register_labels_batch: Optional[list[list[dict[str, Any]]]] = None,
    ) -> Optional[torch.Tensor]:
        """Per-position Ω_* binding loss (Wave 7B Task 3, ADR-02).

        Upgrade path from Wave 6B's pooled-hidden-state approximation to a
        per-position signal:

        1. For each example `b` with both ``omega_labels`` and
           ``register_labels`` entries, identify the Rule 4 integration
           positions: positions `p` where **at least two** distinct
           registers are marked active AND a named Ω_* emergent is present.
        2. For each such `(b, p)`, apply the d_model-width
           ``register_film_dmodel`` per register to the pooled hidden state,
           producing the per-register modulated states that the binding
           head consumes. (An earlier alternative — apply FiLM to the
           per-position 40-dim slot — is architecturally mismatched against
           Agent 27's binding head, which lives in d_model-space per ADR-02.)
        3. Run the binding head on the stack of register-modulated states
           with the prerequisite mask True, and compute the cosine-distance
           loss ``1 - cos(binding_output, target_Ω)`` where the target is
           the registry embedding for the named Ω_*.
        4. Mean over matched positions; batch-mean is a weighted-mean by
           the count of positions per example (simple averaging across the
           flattened (example, position) pairs).

        Backward compatibility: when no examples have Rule 4 integration
        positions (no co-active ≥2 registers AND no Ω_* label at those
        positions), the loss is None and contributes zero to the trainer
        aggregate (same zero-contribution pattern as other v2 losses).
        """
        if self._emergent_pipeline is None:
            return None
        if self._emergent_pipeline.registry.active_size == 0:
            return None

        # Pool over sequence — ER-space bindings are per-example at each of
        # the 40 cognitive-state positions. The register-modulated states
        # ride on the pooled hidden state (d_model-width) rather than the
        # simplex slot because the binding head / Ω_* registry live in
        # d_model-space.
        pooled = hidden_states.mean(dim=1)  # (batch, d_model)

        film = self._register_film_dmodel_module
        if film is None:
            return None
        if pooled.shape[-1] != film.d_model:
            raise RuntimeError(
                "Emergent-binding dim mismatch: pooled last-dim "
                f"{pooled.shape[-1]} != register_film_dmodel.d_model "
                f"{film.d_model}; this indicates broken dim propagation "
                "from CASNativeConfig.d_model."
            )

        # Index-accelerated lookup: per example, what registers are active
        # at what positions? Build position-keyed register sets.
        batch_size = pooled.shape[0]
        register_labels_batch = register_labels_batch or [[] for _ in range(batch_size)]
        active_registers_by_example: list[dict[int, set[int]]] = []
        for reg_list in register_labels_batch:
            per_pos: dict[int, set[int]] = {}
            for entry in reg_list or []:
                pos = entry.get("position")
                reg = entry.get("register")
                if pos is None or reg is None:
                    continue
                try:
                    pos_int = int(pos)
                except (TypeError, ValueError):
                    continue
                if not (0 <= pos_int < NUM_COGNITIVE_STATES):
                    continue
                r_idx = REGISTER_INDEX.get(reg)
                if r_idx is None:
                    continue
                per_pos.setdefault(pos_int, set()).add(r_idx)
            active_registers_by_example.append(per_pos)

        # Identify Rule 4 integration positions: Ω_* label present AND >=2
        # registers active at the SAME position.
        active_names = self._emergent_pipeline.registry.get_active_names()
        name_to_slot = {n: i for i, n in enumerate(active_names)}
        registry_emb = self._emergent_pipeline.registry.get_active_embeddings()
        if registry_emb.numel() == 0:
            return None

        # Collect (example_idx, position, target_slot) per integration point.
        integration_points: list[tuple[int, int, int]] = []
        for i, omega_list in enumerate(omega_labels_batch):
            if not omega_list:
                continue
            active_at = active_registers_by_example[i] if i < len(active_registers_by_example) else {}
            for entry in omega_list:
                name = entry.get("omega_name")
                pos = entry.get("position")
                if name is None or pos is None:
                    continue
                try:
                    pos_int = int(pos)
                except (TypeError, ValueError):
                    continue
                slot = name_to_slot.get(name)
                if slot is None:
                    continue
                regs_here = active_at.get(pos_int, set())
                # Rule 4: same-Noetic multi-register integration requires
                # >= 2 registers co-active at the same position, else the
                # named emergent is not licensed.
                if len(regs_here) < 2:
                    continue
                integration_points.append((i, pos_int, slot))

        if not integration_points:
            return None

        # For each integration point, build the per-register modulated
        # state stack (num_registers, d_model) by running every register's
        # FiLM on the pooled hidden state for example `b`. This produces
        # the input shape the binding head expects.
        states_per_register = []
        for r_idx in range(film.num_registers):
            states_per_register.append(film.apply_register(pooled, r_idx))
        reg_states_full = torch.stack(states_per_register, dim=-2)  # (B, R, d)

        # Gather per-integration-point register stacks — shape (P, R, d).
        example_indices = torch.tensor(
            [p[0] for p in integration_points],
            dtype=torch.long,
            device=pooled.device,
        )
        reg_states = reg_states_full.index_select(0, example_indices)  # (P, R, d)

        bound = self._emergent_pipeline.binding_head(
            reg_states,
            prereq_mask=torch.ones(
                reg_states.shape[:-2],
                device=reg_states.device,
                dtype=torch.bool,
            ),
        )  # (P, d)

        target_slots = torch.tensor(
            [p[2] for p in integration_points],
            dtype=torch.long,
            device=pooled.device,
        )
        targets = registry_emb.index_select(0, target_slots)  # (P, d)

        # Cosine-distance loss: 1 - cos(binding_out, target). Monotone in
        # the arc-length; differentiable and bounded. Chose cosine over MSE
        # so the loss is insensitive to Ω_* embedding magnitude (cosine
        # similarity is the same metric the ADR-02 SimilarityActivation
        # uses at inference, keeping training + inference on the same
        # geometric signal).
        cos = F.cosine_similarity(bound, targets, dim=-1, eps=1e-12)  # (P,)
        return (1.0 - cos).mean()

    def _compute_production_loss(
        self,
        hidden_states: torch.Tensor,
        production_targets_batch: list[Optional[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Multi-component production loss (Wave 7B Task 4, ADR-04).

        Three sub-losses:

        - ``L_limiting_reagent``: cross-entropy over the soft-argmin LR
          distribution against ``target_limiting_reagent_index``. Produces
          the primary gradient signal for the recipe head's identification
          of which prerequisite bottlenecks yield.
        - ``L_yield``: MSE on soft-min theoretical yield against
          ``target_theoretical_yield``.
        - ``L_efficiency``: MSE on `Y_A / Y_T` efficiency against
          ``target_efficiency``.

        Aggregate::

            L_production = w_LR * L_LR + w_Y * L_Y + w_eff * L_eff

        with weights from ``V2Hyperparameters.lambda_production_*``.

        Per-example per-component masking: if a specific target field is
        absent from an example's ``production_target`` dict, that component
        is zero-weighted for that example; the other components still
        compute.

        Backward compatibility with the Wave 6B provisional MSE loss:
        examples whose ``production_target`` dict only carries the legacy
        fields (``prereqs``, ``leakages``, ``observed_yield``) produce
        zero loss from the new LR/yield/efficiency paths. Callers retain
        the old MSE path by reading ``out["theoretical_yield"]`` directly;
        the new loss is an additive upgrade that does not break old
        configurations — but the provisional MSE form is no longer the
        default, since it trained against ``observed_yield`` (= Y_A), not
        ``target_theoretical_yield`` (= ground-truth Y_T).
        """
        if self._production_head is None:
            return None

        labelled_indices = [
            i for i, t in enumerate(production_targets_batch) if t is not None
        ]
        if not labelled_indices:
            return None

        pooled = hidden_states.mean(dim=1)
        pooled_sub = pooled[labelled_indices]
        targets_sub = [production_targets_batch[i] for i in labelled_indices]

        observed_yields = torch.tensor(
            [float(t.get("observed_yield", 1.0)) for t in targets_sub],
            dtype=pooled_sub.dtype,
            device=pooled_sub.device,
        )

        out = self._production_head(
            pooled_sub,
            mode="training",
            tau=max(self.current_tau, 1e-3),
            actual_yield=observed_yields,
        )

        theoretical = out["theoretical_yield"]              # (N,)
        lr_weights = out["limiting_reagent_weights"]        # (N, max_prereq)
        efficiency_pred = out.get("efficiency")             # (N,) or None

        w_lr = float(self.v2_hp.lambda_production_limiting_reagent)
        w_y = float(self.v2_hp.lambda_production_yield)
        w_eff = float(self.v2_hp.lambda_production_efficiency)

        device = pooled_sub.device
        dtype = pooled_sub.dtype
        aggregate = torch.zeros((), device=device, dtype=dtype)
        any_component = False

        # Limiting-reagent CE — per-example masked.
        lr_indices: list[int] = []
        lr_targets: list[int] = []
        max_prereq = lr_weights.shape[-1]
        for i, t in enumerate(targets_sub):
            idx = t.get("target_limiting_reagent_index")
            if idx is None:
                continue
            try:
                idx_int = int(idx)
            except (TypeError, ValueError):
                continue
            if not (0 <= idx_int < max_prereq):
                continue
            lr_indices.append(i)
            lr_targets.append(idx_int)
        if lr_indices:
            sel = torch.tensor(lr_indices, dtype=torch.long, device=device)
            lr_soft = lr_weights.index_select(0, sel)           # (m, max_prereq)
            lr_true = torch.tensor(lr_targets, dtype=torch.long, device=device)
            # soft_argmin output already sums to 1 across last dim; take log
            # and compute NLL. F.cross_entropy expects logits, so feed
            # log-probabilities via F.nll_loss on safe-logged probs.
            log_probs = torch.log(lr_soft.clamp_min(1e-12))
            lr_loss = F.nll_loss(log_probs, lr_true)
            aggregate = aggregate + w_lr * lr_loss
            any_component = True

        # Theoretical-yield MSE — per-example masked.
        y_indices: list[int] = []
        y_targets: list[float] = []
        for i, t in enumerate(targets_sub):
            val = t.get("target_theoretical_yield")
            if val is None:
                continue
            try:
                y_targets.append(float(val))
                y_indices.append(i)
            except (TypeError, ValueError):
                continue
        if y_indices:
            sel = torch.tensor(y_indices, dtype=torch.long, device=device)
            y_pred = theoretical.index_select(0, sel)
            y_true = torch.tensor(y_targets, dtype=dtype, device=device)
            y_loss = F.mse_loss(y_pred, y_true)
            aggregate = aggregate + w_y * y_loss
            any_component = True

        # Efficiency MSE — per-example masked. Efficiency is only defined
        # when the head computed it (i.e. actual_yield was fed), which we
        # do unconditionally above so efficiency_pred is available.
        if efficiency_pred is not None:
            eff_indices: list[int] = []
            eff_targets: list[float] = []
            for i, t in enumerate(targets_sub):
                val = t.get("target_efficiency")
                if val is None:
                    continue
                try:
                    eff_targets.append(float(val))
                    eff_indices.append(i)
                except (TypeError, ValueError):
                    continue
            if eff_indices:
                sel = torch.tensor(eff_indices, dtype=torch.long, device=device)
                eff_pred_sub = efficiency_pred.index_select(0, sel)
                eff_true = torch.tensor(eff_targets, dtype=dtype, device=device)
                eff_loss = F.mse_loss(eff_pred_sub, eff_true)
                aggregate = aggregate + w_eff * eff_loss
                any_component = True

        if not any_component:
            # None of LR / Y_T / efficiency targets were supplied for any
            # labelled example — legacy-only payload (prereqs/observed_yield).
            # Fall back to the provisional MSE signal (backward-compat).
            return F.mse_loss(theoretical, observed_yields)

        return aggregate

    def _compute_rule_four_loss(
        self,
        hidden_states: torch.Tensor,
        register_labels_batch: list[list[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Rule 4 compliance loss via RustValidationBridge (ADR-06).

        Wave 7B Task 2 upgrade: prefer the continuous distance-to-valid
        signal (``rule_four_distance_batch``) over the binary 0.0/1.0
        categorical. Wheel 0.1.1 emits a severity-weighted scalar (0.0 for
        Valid, 1.0 for 2-register violation, 1.5 for 3-register, 2.0 for
        4-register) which is the loss magnitude directly. For older wheels
        without the continuous API the trainer falls back to the binary
        signal (backward-compat; visible as a RuntimeWarning).

        Gradient-flow note: the loss scalar itself is gradient-bearing only
        through whatever activations upstream fed into the expression-building
        machinery. The Rust validator is not differentiable; the distance
        metric is used as a fixed target-magnitude for the loss. In the
        current scaffold, expression-building is derived from labels, so
        ``rule_four_loss`` contributes to the model's total-loss scalar but
        does not pass gradient through the validator. Full end-to-end
        gradient wiring awaits a learned "expression proposer" head which
        is scheduled beyond Wave 7B.
        """
        if self._rust_bridge is None:
            return None
        if StructuralPattern is None:
            return None

        # Synthesize validation patterns from register_labels_batch. Each
        # example yields at most one expression (multi-position annotation
        # is a scaffold simplification).
        patterns: list[StructuralPattern] = []
        call_args: list[Any] = []
        example_indices: list[int] = []
        for i, reg_list in enumerate(register_labels_batch):
            if not reg_list:
                continue
            regs = [entry.get("register") for entry in reg_list if "register" in entry]
            regs = [r for r in regs if r in REGISTER_INDEX]
            if len(regs) < 2:
                continue
            # Build a same-Noetic same-Domain expression with no named
            # emergent result (force Rule 4 violation unless model provides
            # one — scaffold default is to flag the illicit combination).
            operands = [(3, 0, None, r) for r in regs]  # ^3^P | R
            pattern = StructuralPattern(
                noetics=(3,),
                domains=("P",),
                drives=tuple(),
                registers=tuple(sorted(set(regs))),
                register_sets=(tuple(sorted(regs)),),
                emergent_register_name=None,
                recipe_shape=None,
                validation_kind="rule_four",
            )
            patterns.append(pattern)
            call_args.append((operands, None))
            example_indices.append(i)

        if not patterns:
            return None

        bridge = self._rust_bridge
        distances: Optional[list[float]] = None

        # Prefer the continuous signal when the wheel exposes it.
        if bridge.has_rule_four_distance():
            try:
                distances = bridge.rule_four_distance_batch(
                    patterns, call_args=call_args
                )
            except Exception as exc:
                warnings.warn(
                    f"RustValidationBridge.rule_four_distance_batch raised "
                    f"{exc!r}; falling back to binary validator.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                distances = None

        if distances is None:
            # Fallback: binary signal from the categorical validator.
            try:
                results = bridge.validate_rule_four_batch(
                    patterns, call_args=call_args
                )
            except Exception as exc:
                warnings.warn(
                    f"RustValidationBridge.validate_rule_four_batch raised "
                    f"{exc!r}; skipping Rule 4 loss for this batch.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return None

            distances = []
            for r in results:
                kind = getattr(r, "kind", None)
                if kind is None:
                    continue
                distances.append(0.0 if kind == "valid" else 1.0)

        if not distances:
            return None

        tensor = torch.tensor(
            distances, dtype=hidden_states.dtype, device=hidden_states.device
        )
        return tensor.mean()

    # ----------------------------------------------- null-space regularization
    # ADR-03 follow-up: unused Omega_* registry slots drift toward noise
    # patterns that can accidentally match real Omega_* at inference. Pull
    # them toward a "null" point to preserve separation.

    def _compute_null_space_reg_loss(self) -> Optional[torch.Tensor]:
        """Null-space regularization over unused Omega_* registry slots.

        Returns:
          - ``None`` when ``use_emergent_register`` is False (no registry to
            regularize).
          - ``None`` when the registry is fully saturated (zero unused slots).
          - Otherwise: a scalar tensor equal to
            ``NullSpaceRegularizationLoss(strategy, lambda_null)`` applied to
            ``registry.unused_slot_embeddings()``.

        The underlying ``NullSpaceRegularizationLoss`` module is instantiated
        lazily on first call so the strategy / lambda combination from
        ``V2Hyperparameters`` is respected even when the hyperparameter
        block is mutated after trainer construction (uncommon but legal).
        """
        if not self.v2_flags.use_emergent_register:
            return None
        if self._emergent_pipeline is None:
            return None

        registry = self._emergent_pipeline.registry
        unused = registry.unused_slot_embeddings()
        if unused.numel() == 0:
            return None

        if getattr(self, "_null_space_loss_module", None) is None:
            strategy = getattr(
                self.v2_hp, "null_space_reg_strategy", "origin"
            )
            lambda_null = float(
                getattr(self.v2_hp, "lambda_null_space_reg", 0.01)
            )
            # ``lambda_null`` in the loss module is the scalar applied inside
            # the loss. We pass 1.0 here and multiply by the configured
            # lambda in the aggregation step — this keeps the loss module's
            # output numerically comparable when we inspect it via
            # ``extras["null_space_reg_loss"]``.
            self._null_space_loss_module = NullSpaceRegularizationLoss(
                strategy=strategy,
                lambda_null=1.0,
                d_model=(
                    registry.d_model if strategy == "learned_anchor" else None
                ),
            )
            self._null_space_loss_module.to(registry.registry.device)
            # Register on the model's v2_components so its learned anchor (if
            # any) participates in state_dict serialization.
            if strategy == "learned_anchor":
                self.model.v2_components["null_space_reg"] = (
                    self._null_space_loss_module
                )

        return self._null_space_loss_module(unused)

    # ---------------------------------------- ADR-07 proposer score-based loss

    def _compute_proposer_rule_four_loss(
        self,
        hidden_states: torch.Tensor,
        register_labels_batch: list[list[dict[str, Any]]],
        omega_labels_batch: list[list[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Score-based proposer loss for the learned ExpressionProposerHead
        (ADR-07).

        This method closes the gradient-flow gap identified by Codex 5.4 in
        the Wave 7B panel review. Unlike ``_compute_rule_four_loss`` — which
        builds expression operands from **labels** and wraps Rust-returned
        floats in a non-gradient-bearing tensor — this method:

        1. Runs the learned ``ExpressionProposerHead`` on the model's hidden
           states (the proposer is a submodule of the model, so its
           parameters are in the optimizer and its forward is on the graph).
        2. Derives per-example label targets from the register / Ω_* label
           streams already carried by the training batch (see
           ``training/data_format.md``).
        3. Computes a weighted sum of five component losses (Noetic CE,
           Domain CE, per-operand Register CE, operand-count smooth-L1,
           named-emergent CE) against those targets.

        Because the proposer logits are produced by a linear projection of
        the hidden states, the loss is gradient-bearing to every model
        component upstream of the proposer's input. This is the critical
        property the legacy ``_compute_rule_four_loss`` lacked.

        Label derivation rules:

        * **Noetic / Domain target**: the scaffold data pipeline carries
          per-position register labels but does not yet emit explicit
          noetic/domain expression labels. The v1 proposer loss derives
          a surrogate target from the omega_labels_batch when present
          (``target_noetic`` / ``target_domain`` keys on the omega entry),
          OR uses a neutral target (``noetic=3, domain=0`` — the Rule 4
          ``^3^P|…`` template encoded in ``_compute_rule_four_loss``) when
          only register labels are available.
        * **Per-operand Register target**: from the ordered register list
          at each labelled example's first Rule-4-eligible position
          (position with >= 2 distinct registers active). Operand slots
          beyond the label count are masked out of the CE.
        * **Operand-count target**: the count of distinct registers at the
          chosen position.
        * **Named-emergent target**: 1 when the example carries any omega
          label at that position, else 0.

        Masking: examples with zero register labels contribute zero to
        every proposer component. ``None`` is returned only when NO
        example in the batch has any proposer-trainable label (same
        zero-contribution pattern as the other v2 losses).

        Args:
            hidden_states: (B, seq_len, d_model) or (B, d_model) — the
                same d_model-width hidden-state tensor the other v2
                losses consume.
            register_labels_batch: per-example list of register
                annotations (see ``training/data_format.md``).
            omega_labels_batch: per-example list of Ω_* annotations.

        Returns:
            Scalar loss tensor (gradient-bearing to model params via the
            proposer head), or ``None`` when no example is trainable.
        """
        if self._expression_proposer is None or self._proposer_loss_fn is None:
            return None

        batch_size = hidden_states.shape[0]
        if batch_size == 0:
            return None

        # Derive per-example targets from the label streams.
        noetic_targets: list[int] = []
        domain_targets: list[int] = []
        operand_count_targets: list[int] = []
        named_emergent_targets: list[int] = []
        register_targets_rows: list[list[int]] = []
        matched_indices: list[int] = []

        max_operands = self._expression_proposer.max_operands
        count_to_bucket = {c: i for i, c in enumerate(OPERAND_COUNT_BUCKETS)}
        max_bucket = len(OPERAND_COUNT_BUCKETS) - 1

        for i in range(batch_size):
            reg_list = (
                register_labels_batch[i]
                if i < len(register_labels_batch)
                else []
            )
            if not reg_list:
                continue

            # Group registers by position.
            by_pos: dict[int, list[int]] = {}
            for entry in reg_list:
                pos = entry.get("position")
                reg = entry.get("register")
                if pos is None or reg is None:
                    continue
                r_idx = REGISTER_INDEX.get(reg)
                if r_idx is None:
                    continue
                try:
                    pos_int = int(pos)
                except (TypeError, ValueError):
                    continue
                by_pos.setdefault(pos_int, []).append(r_idx)

            if not by_pos:
                continue

            # Pick the position with the largest register set — this is
            # the Rule-4-eligible position for the example.
            chosen_pos = max(by_pos.keys(), key=lambda p: (len(by_pos[p]), -p))
            regs_at_pos = by_pos[chosen_pos]

            # Noetic / Domain targets — prefer explicit labels on the omega
            # entry when present, else fall back to the Rule 4 template
            # (^3^P | …) encoded in ``_compute_rule_four_loss``.
            target_noetic = 3
            target_domain = 0
            has_named = 0
            omega_list = (
                omega_labels_batch[i]
                if i < len(omega_labels_batch)
                else []
            )
            for omega_entry in omega_list or []:
                try:
                    omega_pos = int(omega_entry.get("position", -1))
                except (TypeError, ValueError):
                    continue
                if omega_pos != chosen_pos:
                    continue
                has_named = 1
                if "target_noetic" in omega_entry:
                    try:
                        target_noetic = int(omega_entry["target_noetic"])
                    except (TypeError, ValueError):
                        pass
                if "target_domain" in omega_entry:
                    try:
                        target_domain = int(omega_entry["target_domain"])
                    except (TypeError, ValueError):
                        pass
                break

            target_noetic = max(0, min(target_noetic, 9))
            target_domain = max(0, min(target_domain, 3))

            # Deduplicate + truncate register sequence to max_operands.
            seen: set[int] = set()
            ordered_regs: list[int] = []
            for r in regs_at_pos:
                if r in seen:
                    continue
                seen.add(r)
                ordered_regs.append(r)
                if len(ordered_regs) >= max_operands:
                    break

            if not ordered_regs:
                continue

            count = len(ordered_regs)
            count_bucket = count_to_bucket.get(count)
            if count_bucket is None:
                count_bucket = max_bucket

            matched_indices.append(i)
            noetic_targets.append(target_noetic)
            domain_targets.append(target_domain)
            operand_count_targets.append(count_bucket)
            named_emergent_targets.append(has_named)
            register_targets_rows.append(ordered_regs)

        if not matched_indices:
            return None

        device = hidden_states.device

        # Run the proposer on matched examples only. ``index_select`` is
        # differentiable so the graph remains connected.
        idx_tensor = torch.tensor(
            matched_indices, dtype=torch.long, device=device
        )
        matched_hidden = hidden_states.index_select(0, idx_tensor)
        proposer_out = self._expression_proposer(
            matched_hidden,
            mode="training",
            tau=max(self.current_tau, 1e-3),
        )

        n_tgt = torch.tensor(noetic_targets, dtype=torch.long, device=device)
        d_tgt = torch.tensor(domain_targets, dtype=torch.long, device=device)
        c_tgt = torch.tensor(
            operand_count_targets, dtype=torch.long, device=device
        )
        e_tgt = torch.tensor(
            named_emergent_targets, dtype=torch.long, device=device
        )

        K = len(matched_indices)
        reg_tgt = torch.zeros((K, max_operands), dtype=torch.long, device=device)
        reg_mask = torch.zeros((K, max_operands), dtype=torch.bool, device=device)
        for k, row in enumerate(register_targets_rows):
            for slot, r in enumerate(row[:max_operands]):
                reg_tgt[k, slot] = r
                reg_mask[k, slot] = True

        return self._proposer_loss_fn(
            proposer_out,
            noetic_targets=n_tgt,
            domain_targets=d_tgt,
            register_targets=reg_tgt,
            register_target_mask=reg_mask,
            operand_count_targets=c_tgt,
            named_emergent_targets=e_tgt,
        )

    # ------------------------------------------------------------------ step

    def _anneal_tau_for_step(self, step: int) -> float:
        """Linear Gumbel-softmax schedule across ``gumbel_tau_anneal_steps``."""
        t0 = float(self.v2_hp.gumbel_tau_initial)
        t1 = float(self.v2_hp.gumbel_tau_final)
        n = int(self.v2_hp.gumbel_tau_anneal_steps)
        if n <= 0:
            return t1
        if step <= 0:
            return t0
        if step >= n:
            return t1
        frac = step / n
        return t0 + (t1 - t0) * frac

    def _train_step(self, batch: dict[str, Any]) -> dict[str, float]:
        """Execute a single training step."""
        self.model.train()

        input_ids = batch["input_ids"].to(self.device)
        targets = batch["targets"].to(self.device)
        attention_mask = batch.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        cas_scores = batch.get("cas_scores", [])

        # v2 label payloads — all optional, default to [] per example.
        register_labels_batch = batch.get(
            "register_labels", [[] for _ in range(input_ids.size(0))]
        )
        omega_labels_batch = batch.get(
            "omega_labels", [[] for _ in range(input_ids.size(0))]
        )
        production_targets_batch = batch.get(
            "production_target", [None for _ in range(input_ids.size(0))]
        )

        # Build the per-position register-activation tensor used by the
        # forward-path FiLM routing (Wave 7B Task 1). Returns None when no
        # example in the batch has any register labels — that signal lets
        # the forward pass short-circuit to the byte-equivalent v7.4 path.
        register_activations = None
        if self.v2_flags.use_register_film:
            register_activations = self._build_register_activations(
                register_labels_batch
            )

        # Forward pass.
        outputs = self.model(
            input_ids,
            attention_mask=attention_mask,
            register_activations=register_activations,
        )

        # Generate target cognitive state.
        batch_size, seq_len = input_ids.shape
        target_cog = self._generate_target_cognitive_state(cas_scores, seq_len)

        # Build RPM satisfaction dict from scalar.
        rpm_sat_dict = {"mean": outputs["rpm_satisfaction"].unsqueeze(0)}

        # Compute base loss (v7.4 path).
        total_loss, components = self.loss_fn(
            logits=outputs["logits"],
            targets=targets,
            cognitive_state=outputs["cognitive_state"],
            target_cognitive_state=target_cog,
            rpm_satisfaction=rpm_sat_dict,
            inversion_scores=outputs["inversion_flags"],
        )

        # -------------------- v2 loss components --------------------
        hidden_states = outputs["cognitive_state"]  # (B, S, 40) on simplex
        # For v2 component losses that need d_model hidden states, recover
        # via the final cognitive_state; pooled hidden states on the simplex
        # suffice for scaffold wiring (production + emergent heads are tested
        # for shape/grad-flow, not for full-dimensional representation).
        # Production / emergent heads expect (..., d_model) — we build a
        # synthetic pooled hidden tensor of the right shape when d_model
        # differs from 40.
        d_model = self.model.config.d_model
        if d_model != 40:
            # Project via the token embedding output + final_norm path.
            tok = self.model.token_embedding(input_ids)
            tok = self.model.pos_encoding(tok)
            if attention_mask is not None:
                tok = tok * attention_mask.unsqueeze(-1).float()
            d_model_hidden = tok
        else:
            d_model_hidden = hidden_states

        extras: dict[str, torch.Tensor] = {}

        if self.v2_flags.use_register_film:
            inv_loss = self._compute_involution_loss()
            if inv_loss is not None:
                total_loss = total_loss + inv_loss
                extras["involution_loss"] = inv_loss

        if self.v2_flags.use_emergent_register:
            binding_loss = self._compute_emergent_binding_loss(
                d_model_hidden,
                omega_labels_batch,
                register_labels_batch=register_labels_batch,
            )
            if binding_loss is not None:
                weighted = self.v2_hp.lambda_emergent_binding * binding_loss
                total_loss = total_loss + weighted
                extras["emergent_binding_loss"] = binding_loss

        if self.v2_flags.use_production_semantics:
            prod_loss = self._compute_production_loss(
                d_model_hidden, production_targets_batch
            )
            if prod_loss is not None:
                weighted = self.v2_hp.lambda_production * prod_loss
                total_loss = total_loss + weighted
                extras["production_loss"] = prod_loss

        if self.v2_flags.use_rust_validation:
            rule_four_loss = self._compute_rule_four_loss(
                d_model_hidden, register_labels_batch
            )
            if rule_four_loss is not None:
                weighted = self.v2_hp.lambda_rule_four * rule_four_loss
                total_loss = total_loss + weighted
                extras["rule_four_loss"] = rule_four_loss

        # ADR-07 expression proposer loss aggregation
        # Score-based CE + smooth-L1 loss for the learned
        # ``ExpressionProposerHead``. Gradient-bearing via the proposer's
        # direct projection of d_model hidden states — this is the
        # gradient-flow gap closure for Rule 4 identified by Codex 5.4.
        # Returns None when no example in the batch has any register
        # labels (zero-contribution pattern matching the other v2 losses).
        if self.v2_flags.use_expression_proposer:
            proposer_loss = self._compute_proposer_rule_four_loss(
                d_model_hidden,
                register_labels_batch,
                omega_labels_batch,
            )
            if proposer_loss is not None:
                weighted = (
                    self.v2_hp.lambda_proposer_rule_four * proposer_loss
                )
                total_loss = total_loss + weighted
                extras["proposer_rule_four_loss"] = proposer_loss

        # ADR-03 follow-up null-space regularization aggregation
        # Pulls unused Omega_* registry slots toward a null point (strategy
        # "origin" by default) so they don't drift toward patterns that match
        # real Omega_* at inference. Low weight by default (0.01) — this is
        # regularization only, not primary signal. Returns None when emergent
        # register flag is off or the registry is fully saturated, in which
        # case the total_loss is unchanged (backward compat guard).
        null_space_loss = self._compute_null_space_reg_loss()
        if null_space_loss is not None:
            weighted = self.v2_hp.lambda_null_space_reg * null_space_loss
            total_loss = total_loss + weighted
            extras["null_space_reg_loss"] = null_space_loss

        # Update component dict with any v2 extras.
        for k, v in extras.items():
            components[k] = v
        components["total"] = total_loss

        # Backward pass.
        self.optimizer.zero_grad()
        total_loss.backward()

        # Gradient clipping.
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)

        # Optimizer step.
        self.optimizer.step()
        self.scheduler.step()

        # Anneal Gumbel-softmax temperature.
        self.current_tau = self._anneal_tau_for_step(self.global_step)

        # Return metrics.
        metrics = {k: v.item() for k, v in components.items() if isinstance(v, torch.Tensor)}
        metrics["lr"] = self.scheduler.get_last_lr()[0]
        metrics["current_tau"] = self.current_tau
        return metrics

    @torch.no_grad()
    def evaluate(self) -> dict[str, float]:
        """Evaluate the model on the validation set."""
        if self.val_loader is None:
            return {}

        self.model.eval()
        total_loss = 0.0
        total_rpm_sat = 0.0
        num_batches = 0

        for batch in self.val_loader:
            input_ids = batch["input_ids"].to(self.device)
            targets = batch["targets"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)
            cas_scores = batch.get("cas_scores", [])

            outputs = self.model(input_ids, attention_mask=attention_mask)

            batch_size, seq_len = input_ids.shape
            target_cog = self._generate_target_cognitive_state(cas_scores, seq_len)

            rpm_sat_dict = {"mean": outputs["rpm_satisfaction"].unsqueeze(0)}

            loss, components = self.loss_fn(
                logits=outputs["logits"],
                targets=targets,
                cognitive_state=outputs["cognitive_state"],
                target_cognitive_state=target_cog,
                rpm_satisfaction=rpm_sat_dict,
                inversion_scores=outputs["inversion_flags"],
            )

            total_loss += loss.item()
            total_rpm_sat += outputs["rpm_satisfaction"].item()
            num_batches += 1

        if num_batches == 0:
            return {}

        out: dict[str, float] = {
            "val_loss": total_loss / num_batches,
            "val_rpm_satisfaction": total_rpm_sat / num_batches,
        }

        # Wave 8A v2-aware evaluation: compute composite_v2 when the
        # configured metric is ``composite_v2`` and v2 flags are on. This
        # lets the best-checkpoint logic consult a v2-native score.
        if self._use_composite_v2_selection():
            try:
                composite_info = self._compute_composite_v2_for_val()
            except Exception as exc:  # pragma: no cover - defensive
                warnings.warn(
                    f"composite_v2 computation raised {exc!r}; falling back "
                    "to val_loss-based best-checkpoint selection.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                composite_info = None
            if composite_info is not None:
                composite_value = composite_info.get("composite")
                if composite_value is not None:
                    out["composite_v2"] = float(composite_value)
                    # Surface the component scores individually too — useful
                    # for W&B dashboards and eyeballing regressions.
                    for k, v in composite_info.get("components", {}).items():
                        out[f"composite_v2.{k}"] = float(v)

        return out

    # ------------------------------------------------------------------
    # Wave 8A checkpoint selection helpers.
    # ------------------------------------------------------------------

    def _use_composite_v2_selection(self) -> bool:
        """True when best-checkpoint should use composite_v2 (not val_loss).

        Uses ``TrainingConfig.effective_checkpoint_selection_metric`` when a
        TrainingConfig was passed, else falls back to the legacy val_loss
        path (backward compat for ``config: dict`` callers).
        """
        if self.training_config is None:
            return False
        return self.training_config.effective_checkpoint_selection_metric() == "composite_v2"

    def _compute_composite_v2_for_val(self) -> Optional[dict[str, Any]]:
        """Compute composite_v2 against ``self.val_loader``.

        Instantiates a ``CASEvaluator`` bound to the trainer's model and
        injects the trainer's ``rust_bridge`` so Rule 4 compliance uses the
        same cache that produced training signal. Returns the dict from
        ``CASEvaluator.composite_v2_score`` or ``None`` when no val loader
        is configured.
        """
        if self.val_loader is None:
            return None
        # Local import to avoid circular import at module load.
        from ..evaluation.evaluate import CASEvaluator

        evaluator = CASEvaluator(self.model, device=self.device)
        return evaluator.composite_v2_score(
            self.val_loader, rust_bridge=self._rust_bridge
        )

    def _should_save_best_checkpoint(self, val_metrics: dict[str, float]) -> bool:
        """Decide whether to save a ``best``-tagged checkpoint.

        Selection rule:
          - When the configured metric is ``composite_v2`` AND a composite_v2
            score is present in ``val_metrics``, higher-is-better comparison
            against ``self.best_composite_v2`` determines the save.
          - Otherwise the legacy ``val_loss`` lower-is-better comparison
            against ``self.best_val_loss`` applies.

        Both tracking scalars are updated on improvement so switching the
        selection metric mid-run doesn't falsely trigger a "first improvement"
        on the new metric.
        """
        saved = False

        if (
            self._use_composite_v2_selection()
            and "composite_v2" in val_metrics
        ):
            score = float(val_metrics["composite_v2"])
            if score > self.best_composite_v2:
                self.best_composite_v2 = score
                saved = True
        else:
            # Legacy / nccs path.
            if val_metrics.get("val_loss", float("inf")) < self.best_val_loss:
                self.best_val_loss = float(val_metrics["val_loss"])
                saved = True

        return saved

    def train(self) -> dict[str, Any]:
        """Run the full training loop.

        Returns:
            Dict with training summary.
        """
        print(f"Starting CAS-Native training for {self.max_steps} steps")
        print(f"  Target NCCS: {self.target_nccs} (Gold certification)")
        print(f"  Checkpoint dir: {self.checkpoint_dir}")
        print(f"  W&B logging: {self.wandb_enabled}")
        print(f"  v2 flags: {asdict(self.v2_flags)}")

        if self.wandb_enabled and self._wandb is not None:
            self._wandb.init(project="cas-native", config={"max_steps": self.max_steps})

        training_log: list[dict[str, Any]] = []
        start_time = time.time()

        data_iter = iter(self.train_loader)

        while self.global_step < self.max_steps:
            # Get next batch (cycle through data).
            try:
                batch = next(data_iter)
            except StopIteration:
                data_iter = iter(self.train_loader)
                batch = next(data_iter)

            # Training step.
            metrics = self._train_step(batch)
            self.global_step += 1

            # Log.
            if self.global_step % 100 == 0:
                elapsed = time.time() - start_time
                print(
                    f"Step {self.global_step}/{self.max_steps} | "
                    f"Loss: {metrics['total']:.4f} | "
                    f"LR: {metrics['lr']:.2e} | "
                    f"Time: {elapsed:.1f}s"
                )

            if self.wandb_enabled and self._wandb is not None:
                self._wandb.log(metrics, step=self.global_step)

            # Evaluation.
            if self.global_step % self.eval_every == 0:
                val_metrics = self.evaluate()
                if val_metrics:
                    print(f"  Eval @ step {self.global_step}: {val_metrics}")

                    # Wave 8A: consult the configured checkpoint-selection
                    # metric. ``_should_save_best_checkpoint`` inspects the
                    # training config and val_metrics to decide; when the
                    # configured metric is ``composite_v2`` and no v2 score
                    # is available, it transparently falls back to val_loss.
                    if self._should_save_best_checkpoint(val_metrics):
                        self._save_checkpoint(tag="best")

                    if self.wandb_enabled and self._wandb is not None:
                        self._wandb.log(val_metrics, step=self.global_step)

            # Checkpointing.
            if self.global_step % self.checkpoint_every == 0:
                ckpt_path = self._save_checkpoint(tag="step")
                print(f"  Checkpoint saved: {ckpt_path}")

            training_log.append({"step": self.global_step, **metrics})

        # Final checkpoint.
        self._save_checkpoint(tag="final")

        elapsed = time.time() - start_time
        summary = {
            "total_steps": self.global_step,
            "total_time_seconds": elapsed,
            "best_val_loss": self.best_val_loss,
            "final_metrics": training_log[-1] if training_log else {},
        }

        if self.wandb_enabled and self._wandb is not None:
            self._wandb.finish()

        return summary
