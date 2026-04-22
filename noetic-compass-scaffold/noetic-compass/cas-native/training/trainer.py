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
)
from ..model.embedding import (
    CognitiveStateEmbedding,
    CognitiveStateEmbeddingWithRegister,
)
from ..model.register_film import REGISTER_INDEX
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
        self._involution_loss: Optional[InvolutionConstraintLoss] = None
        self._emergent_pipeline: Optional[EmergentRegisterPipeline] = None
        self._production_head: Optional[ProductionSemanticsHead] = None
        self._rust_bridge: Any = None

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

    def _compute_emergent_binding_loss(
        self,
        hidden_states: torch.Tensor,
        omega_labels_batch: list[list[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Cross-entropy over Ω_* registry targets for labeled positions.

        Uses the EmergentRegisterBindingHead output at the pooled hidden-state
        representation. When no examples in the batch carry Ω_* labels, the
        loss is zero (mask-driven).
        """
        if self._emergent_pipeline is None:
            return None
        # Skip when no active Ω_* entries are registered.
        if self._emergent_pipeline.registry.active_size == 0:
            return None

        # Pool over sequence — ER-space bindings are per-example.
        pooled = hidden_states.mean(dim=1)  # (batch, d_model)

        # Synthesize register-modulated states from the pooled hidden state by
        # applying each register's FiLM, producing a (batch, num_registers,
        # d_model) tensor. Only meaningful when register_film is active.
        if self._register_film_module is None:
            return None
        states_per_register = []
        for r_idx in range(self._register_film_module.num_registers):
            # Project pooled to registry d_model if dims match; ADR defaults
            # align at d_model=128.
            state = self._register_film_module.apply_register(pooled, r_idx)
            states_per_register.append(state)
        reg_states = torch.stack(states_per_register, dim=-2)  # (B, R, d)

        bound = self._emergent_pipeline.binding_head(
            reg_states,
            prereq_mask=torch.ones(
                reg_states.shape[:-2],
                device=reg_states.device,
                dtype=torch.bool,
            ),
        )  # (B, d)

        active_emb = self._emergent_pipeline.registry.get_active_embeddings()
        if active_emb.numel() == 0:
            return None

        bind_norm = F.normalize(bound, p=2, dim=-1, eps=1e-12)
        reg_norm = F.normalize(active_emb, p=2, dim=-1, eps=1e-12)
        logits = bind_norm @ reg_norm.transpose(0, 1)  # (B, k)

        active_names = self._emergent_pipeline.registry.get_active_names()
        name_to_slot = {n: i for i, n in enumerate(active_names)}

        # Aggregate labels across batch — use the first Ω_* annotation per
        # example when multiple are present (simplification for v2 scaffold).
        label_targets: list[int] = []
        label_indices: list[int] = []
        for i, omega_list in enumerate(omega_labels_batch):
            if not omega_list:
                continue
            for entry in omega_list:
                name = entry.get("omega_name")
                if name in name_to_slot:
                    label_targets.append(name_to_slot[name])
                    label_indices.append(i)
                    break

        if not label_targets:
            return None

        target_tensor = torch.tensor(
            label_targets, dtype=torch.long, device=logits.device
        )
        selected_logits = logits[label_indices]
        return F.cross_entropy(selected_logits, target_tensor)

    def _compute_production_loss(
        self,
        hidden_states: torch.Tensor,
        production_targets_batch: list[Optional[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Soft yield / efficiency loss from ProductionSemanticsHead.

        Per-example masking: examples without ``production_target`` metadata do
        not contribute.
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
        # Loss: MSE between soft theoretical yield and observed actual yield.
        # This is a PROVISIONAL form — the exact loss shape (MSE vs efficiency
        # regression vs limiting-reagent CE) is a tuning follow-up.
        theoretical = out["theoretical_yield"]
        return F.mse_loss(theoretical, observed_yields)

    def _compute_rule_four_loss(
        self,
        hidden_states: torch.Tensor,
        register_labels_batch: list[list[dict[str, Any]]],
    ) -> Optional[torch.Tensor]:
        """Rule 4 compliance loss via RustValidationBridge.

        Emits a distance-to-valid scalar per batch element using the Rust
        engine's Rule 4 validator. Zero for expressions marked ``valid``,
        constant 1.0 per violation otherwise (provisional — the Rust engine
        does not yet emit a continuous distance-to-valid metric; wiring the
        graded signal is flagged as follow-up work against the Rust queue).
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

        try:
            results = self._rust_bridge.validate_rule_four_batch(
                patterns, call_args=call_args
            )
        except Exception as exc:
            warnings.warn(
                f"RustValidationBridge.validate_rule_four_batch raised {exc!r}; "
                "skipping Rule 4 loss for this batch.",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

        # PROVISIONAL: distance-to-valid treated as 0.0 for "valid", else 1.0.
        # The Rust engine currently returns a categorical kind; the continuous
        # signal is a flagged Rust-queue follow-up (ADR-06 §Continuous
        # validation signal).
        penalties = []
        for r in results:
            kind = getattr(r, "kind", None)
            if kind is None:
                continue
            penalty = 0.0 if kind == "valid" else 1.0
            penalties.append(penalty)

        if not penalties:
            return None

        penalty_tensor = torch.tensor(
            penalties, dtype=hidden_states.dtype, device=hidden_states.device
        )
        return penalty_tensor.mean()

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

        # Forward pass.
        outputs = self.model(input_ids, attention_mask=attention_mask)

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
                d_model_hidden, omega_labels_batch
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

        return {
            "val_loss": total_loss / num_batches,
            "val_rpm_satisfaction": total_rpm_sat / num_batches,
        }

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
                    if val_metrics.get("val_loss", float("inf")) < self.best_val_loss:
                        self.best_val_loss = val_metrics["val_loss"]
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
