"""
EmergentRegisterPipeline: Metric-learning binding for same-Noetic cross-register
integration per CAS v7.7 Clarification 10 (Rule 4) and ADR-02 / ADR-03.

Architecture (ADR-02):
  1. PrerequisiteGate       — pure arithmetic, ZERO parameters. Detects positions
                              where >= 2 registers are co-active above threshold at
                              the same (Noetic, Domain) cell; only such positions
                              license the `x` cross-register integration.
  2. EmergentRegisterBindingHead
                            — Hadamard-product fold across the register axis
                              followed by a single linear projection W: R^d -> R^d
                              (bias=False). Parameter cost is d^2 (= 16,384 at
                              d=128). This is DELIBERATELY Hadamard + Linear, NOT
                              nn.Bilinear(d, d, d), which would cost d^3 (~2.1M).
  3. OmegaRegistry          — lookup table of registered `Omega_*` emergent
                              register embeddings. Capacity 20 by default; current
                              admitted entries synchronized with FULL_MANUSCRIPT.md
                              Appendix I (Omega_presence, Omega_refusal).
                              Hot-swappable at inference time via `add_omega`.
  4. SimilarityActivation   — cosine similarity between the binding-layer output
                              and each registered Omega_*; reports per-name scores
                              and flags novel binding outputs that fall below all
                              registry similarity thresholds.

Legal note: Clarification 10 is a notational refinement. This module does NOT
introduce new CAS primitives. The 40 Cognitive States, 7 Drives, 4 Registers, and
5 Generative Operations remain unchanged. Omega_* entries are emergent registers
produced by `x` integration of canonical registers, not a fifth canonical register.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_NOETICS = 10
NUM_DOMAINS = 4
NUM_REGISTERS = 4  # T (Transcendent), A (Analytical), f (Affective), E (Embodied)

# Register index convention (must be kept in sync with ADR-01 / CognitiveStateEmbeddingWithRegister).
REGISTER_NAMES = ["T", "A", "f", "E"]

DEFAULT_PREREQUISITE_THRESHOLD = 0.1

# Similarity threshold default is a PLACEHOLDER per ADR-03: no empirical basis yet.
# Tuning is flagged as a follow-up against first-training-run validation data.
DEFAULT_SIMILARITY_THRESHOLD = 0.7  # EMPIRICALLY UNTUNED PLACEHOLDER — see ADR-03.

# Registry capacity per ADR-02 / ADR-03 lock (20 slots, k=2 admitted at v1).
DEFAULT_REGISTRY_CAPACITY = 20

# Default model dimension (matches CognitiveStateEmbedding) per cross-cutting locked
# decision in ADR design ledger.
DEFAULT_D_MODEL = 128


# ---------------------------------------------------------------------------
# PrerequisiteGate
# ---------------------------------------------------------------------------


class PrerequisiteGate(nn.Module):
    """Pure-arithmetic gate: ZERO trainable parameters.

    Given a per-register activation tensor shaped
    ``(..., num_noetics, num_domains, num_registers)`` — where an activation is
    the scalar magnitude of the corresponding register instantiation at that
    (Noetic, Domain) cell — returns a boolean mask shaped
    ``(..., num_noetics, num_domains)`` True wherever at least two registers are
    simultaneously active above ``threshold``. Only positions passing this gate
    license the cross-register `x` integration licensed by Clarification 10
    Rule 4.

    Threshold is configurable (default ``0.1``) and is NOT a learned parameter.
    """

    def __init__(self, threshold: float = DEFAULT_PREREQUISITE_THRESHOLD):
        super().__init__()
        self.threshold = float(threshold)

    def forward(self, register_activations: torch.Tensor) -> torch.Tensor:
        """
        Args:
            register_activations: Tensor shaped
                ``(..., num_noetics, num_domains, num_registers)`` carrying
                scalar register magnitudes.

        Returns:
            Boolean tensor shaped ``(..., num_noetics, num_domains)`` True at
            positions where >= 2 registers exceed ``threshold``.
        """
        if register_activations.shape[-1] != NUM_REGISTERS:
            raise ValueError(
                f"Expected last dim {NUM_REGISTERS} registers, got "
                f"{register_activations.shape[-1]}"
            )
        above = register_activations > self.threshold  # (..., N, D, R) bool
        active_count = above.sum(dim=-1)  # (..., N, D)
        return active_count >= 2


# ---------------------------------------------------------------------------
# EmergentRegisterBindingHead
# ---------------------------------------------------------------------------


class EmergentRegisterBindingHead(nn.Module):
    """Hadamard-product fold + single linear projection into ER-space.

    Parameter budget: exactly ``d_model ** 2`` (= 16,384 at d_model=128), all of
    which live in ``self.binding_projection`` (a ``nn.Linear(d, d, bias=False)``
    — d^2 weight parameters, no bias parameters, by ADR-02 spec).

    A full ``nn.Bilinear(d, d, d)`` would cost d^3 (~2.1M at d=128) and is
    deliberately avoided here: the Hadamard fold preserves bilinear-style
    multiplicative interaction between register instances at O(d) composition
    cost, and the projection matrix shapes the downstream ER-space geometry.
    """

    def __init__(self, d_model: int = DEFAULT_D_MODEL):
        super().__init__()
        self.d_model = d_model
        # d^2 parameters — the only parameters in this module.
        self.binding_projection = nn.Linear(d_model, d_model, bias=False)

    def forward(
        self,
        register_modulated_states: torch.Tensor,
        prereq_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            register_modulated_states: Shape ``(..., num_registers, d_model)``.
                Register-modulated state instances at a single (Noetic, Domain)
                cell. Typically produced by applying FiLM (ADR-01) per register.
            prereq_mask: Bool tensor with shape matching the leading dims of
                ``register_modulated_states`` before the register axis — i.e.
                ``(...)`` matching everything before ``num_registers``. True at
                positions licensed for cross-register integration.

        Returns:
            Tensor shaped ``(..., d_model)`` giving the ER-space binding output.
            Positions where ``prereq_mask`` is False are zeroed out (the gate
            suppresses illicit cross-register binding).
        """
        # Hadamard fold across the register axis: (..., R, d) -> (..., d)
        folded = register_modulated_states.prod(dim=-2)
        # Single linear projection shapes ER-space geometry.
        bound = self.binding_projection(folded)
        # Mask out positions not licensed by the prerequisite gate.
        bound = bound * prereq_mask.unsqueeze(-1).to(bound.dtype)
        return bound


# ---------------------------------------------------------------------------
# OmegaRegistry
# ---------------------------------------------------------------------------


class OmegaRegistry(nn.Module):
    """Hot-swappable lookup table of admitted `Omega_*` emergent registers.

    Each slot holds a d_model-dimensional embedding. ``active_size`` tracks the
    count of admitted entries (grows as Appendix I of FULL_MANUSCRIPT.md admits
    new entries). Unused slots remain at random initialization; per ADR-03 a
    follow-up regularizer pulling unused slots toward a "null" point is flagged.

    At INFERENCE time `add_omega` permits hot-swap admission without retraining.
    """

    def __init__(
        self,
        d_model: int = DEFAULT_D_MODEL,
        capacity: int = DEFAULT_REGISTRY_CAPACITY,
    ):
        super().__init__()
        self.d_model = d_model
        self.capacity = capacity
        self.registry = nn.Parameter(torch.randn(capacity, d_model))
        self.registry_names: list[Optional[str]] = [None] * capacity
        self.active_size = 0

    def add_omega(
        self,
        name: str,
        embedding: Optional[torch.Tensor] = None,
        slot: Optional[int] = None,
    ) -> int:
        """Hot-swap admission of a new `Omega_*` entry.

        Args:
            name: Canonical `Omega_*` name (e.g. ``"Omega_presence"``). Must match
                the name recorded in FULL_MANUSCRIPT.md Appendix I.
            embedding: Optional d_model embedding. If omitted, the current
                registry-row random initialization is retained.
            slot: Optional explicit slot index. If omitted, the next free slot
                (i.e. ``active_size``) is used.

        Returns:
            The slot index assigned.
        """
        if slot is None:
            slot = self.active_size
        if slot < 0 or slot >= self.capacity:
            raise ValueError(
                f"slot {slot} out of range [0, {self.capacity})"
            )
        if embedding is not None:
            if embedding.shape != (self.d_model,):
                raise ValueError(
                    f"Expected embedding shape ({self.d_model},), got "
                    f"{tuple(embedding.shape)}"
                )
            with torch.no_grad():
                self.registry[slot].copy_(embedding.to(self.registry.dtype))
        if self.registry_names[slot] is None:
            # New slot — grow active_size. If caller passed an explicit slot
            # equal to active_size, this is the common hot-swap path.
            self.registry_names[slot] = name
            self.active_size = max(self.active_size, slot + 1)
        else:
            # Overwriting an existing slot — update the name but don't bump
            # active_size.
            self.registry_names[slot] = name
        return slot

    def load_from_config(self, path: str | Path) -> None:
        """Populate registry slots from a YAML config per ADR-03.

        The YAML schema matches ``cas-native/config/omega_registry.yaml`` and is
        synchronized with FULL_MANUSCRIPT.md Appendix I.

        Entries WITHOUT an explicit ``embedding`` field retain their current
        (random-init) row embedding but acquire the canonical name and slot.
        """
        import yaml  # local import so module load doesn't require PyYAML

        path = Path(path)
        with path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)

        cfg_capacity = int(config.get("capacity", self.capacity))
        if cfg_capacity != self.capacity:
            raise ValueError(
                f"Config capacity ({cfg_capacity}) does not match registry "
                f"capacity ({self.capacity}). Reinstantiate OmegaRegistry with "
                f"capacity={cfg_capacity} or fix the config."
            )

        admitted = config.get("admitted", [])
        # Re-seed active_size from config; highest slot index + 1 wins.
        for entry in admitted:
            slot = int(entry["slot"])
            name = str(entry["name"])
            emb_list = entry.get("embedding")
            if emb_list is not None:
                emb = torch.tensor(emb_list, dtype=self.registry.dtype)
            else:
                emb = None
            self.add_omega(name=name, embedding=emb, slot=slot)

    def get_active_embeddings(self) -> torch.Tensor:
        """Return the ``(active_size, d_model)`` view of admitted embeddings."""
        return self.registry[: self.active_size]

    def get_active_names(self) -> list[str]:
        """Return the list of admitted Omega_* names (length = active_size)."""
        # Any None in this range is a programming error — defend with assertion.
        names = self.registry_names[: self.active_size]
        assert all(n is not None for n in names), "active_size out of sync"
        return [str(n) for n in names]


# ---------------------------------------------------------------------------
# SimilarityActivation
# ---------------------------------------------------------------------------


class SimilarityActivation(nn.Module):
    """Cosine similarity activation against registered `Omega_*` embeddings.

    Returns a per-name dict of scalar similarity scores plus a novelty flag
    (True when all similarities fall below ``similarity_threshold``). A novelty
    flag marks the binding output as a CANDIDATE emergent register — input to
    the Appendix I admission workflow (Clarification 10 Section 5 six-stage
    process).
    """

    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        super().__init__()
        # EMPIRICALLY UNTUNED PLACEHOLDER per ADR-03: no empirical basis yet.
        # Tuning against first-training-run validation data is a flagged
        # follow-up; too low risks promoting noisy binding outputs to false
        # Omega_* matches, too high risks rejecting genuine emergents.
        self.similarity_threshold = float(similarity_threshold)

    def forward(
        self,
        binding_output: torch.Tensor,
        registry: OmegaRegistry,
    ) -> dict:
        """
        Args:
            binding_output: Shape ``(..., d_model)``. ER-space binding output
                from ``EmergentRegisterBindingHead``.
            registry: The OmegaRegistry to compare against.

        Returns:
            Dict with keys:
              - ``"similarities"``: ``{omega_name: tensor of scores shaped (...)}``
              - ``"candidate"``: bool tensor shaped ``(...)`` True where all
                registered Omega_* similarities fall below
                ``similarity_threshold`` (novel emergent candidate).
        """
        active_embeddings = registry.get_active_embeddings()  # (k, d)
        active_names = registry.get_active_names()

        if active_embeddings.numel() == 0:
            # Empty registry: every binding output is a candidate by definition.
            flat_shape = binding_output.shape[:-1]
            return {
                "similarities": {},
                "candidate": torch.ones(flat_shape, dtype=torch.bool),
            }

        # Cosine similarity per admitted Omega_*:
        #   bind_norm @ reg_norm.T, with L2 norm over d_model.
        bind_norm = F.normalize(binding_output, p=2, dim=-1, eps=1e-12)
        reg_norm = F.normalize(active_embeddings, p=2, dim=-1, eps=1e-12)
        # shape: (..., k)
        sims = torch.matmul(bind_norm, reg_norm.transpose(0, 1))

        similarities = {
            name: sims[..., i] for i, name in enumerate(active_names)
        }
        # Novel candidate where max similarity across registry is below threshold.
        max_sims = sims.amax(dim=-1)
        candidate = max_sims < self.similarity_threshold

        return {
            "similarities": similarities,
            "candidate": candidate,
        }


# ---------------------------------------------------------------------------
# EmergentRegisterPipeline
# ---------------------------------------------------------------------------


class EmergentRegisterPipeline(nn.Module):
    """End-to-end composition of the four ADR-02 / ADR-03 stages.

    Usage:
        pipeline = EmergentRegisterPipeline(d_model=128, registry_capacity=20)
        pipeline.load_registry_config("cas-native/config/omega_registry.yaml")
        out = pipeline(
            register_modulated_states,  # (..., num_registers, d_model)
            register_activations,       # (..., num_noetics, num_domains, num_registers)
        )

    Note: for module simplicity the pipeline assumes the caller has already
    selected a specific (Noetic, Domain) cell for binding (so
    ``register_modulated_states`` is shape ``(..., num_registers, d_model)``).
    Upstream orchestration picks which cell to bind at based on the Noetic /
    Domain position that triggered the prerequisite gate; the pipeline's
    ``prereq_mask`` is the gate result for that same cell (shape ``(...)``).
    """

    def __init__(
        self,
        d_model: int = DEFAULT_D_MODEL,
        registry_capacity: int = DEFAULT_REGISTRY_CAPACITY,
        prerequisite_threshold: float = DEFAULT_PREREQUISITE_THRESHOLD,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        super().__init__()
        self.prerequisite_gate = PrerequisiteGate(threshold=prerequisite_threshold)
        self.binding_head = EmergentRegisterBindingHead(d_model=d_model)
        self.registry = OmegaRegistry(d_model=d_model, capacity=registry_capacity)
        self.similarity = SimilarityActivation(
            similarity_threshold=similarity_threshold
        )

    def load_registry_config(self, path: str | Path) -> None:
        """Populate the OmegaRegistry from YAML config (Appendix I synchronized)."""
        self.registry.load_from_config(path)

    def forward(
        self,
        register_modulated_states: torch.Tensor,
        register_activations: torch.Tensor,
        cell: Optional[tuple[int, int]] = None,
    ) -> dict:
        """Run the full pipeline: gate -> bind -> similarity.

        Args:
            register_modulated_states: ``(..., num_registers, d_model)`` — the
                register-modulated states at a single (Noetic, Domain) cell.
            register_activations: ``(..., num_noetics, num_domains, num_registers)``
                per-register scalar magnitudes. Used by the PrerequisiteGate to
                determine which (..., Noetic, Domain) positions are licensed.
            cell: Optional ``(noetic_idx, domain_idx)`` pair indicating which
                cell ``register_modulated_states`` corresponds to. If provided
                the prereq_mask is sliced at that cell; if None the mask is
                reduced across all (Noetic, Domain) cells via logical-OR (i.e.
                "is ANY cell licensed?").

        Returns:
            Dict with keys ``binding``, ``similarities``, ``candidate``,
            ``prereq_mask_cell``.
        """
        gate_mask = self.prerequisite_gate(register_activations)  # (..., N, D)

        if cell is not None:
            n_idx, d_idx = cell
            prereq_mask_cell = gate_mask[..., n_idx, d_idx]
        else:
            # No cell provided — accept binding if ANY (Noetic, Domain) cell
            # licenses it. This is a convenience fallback; production callers
            # should pass the explicit cell.
            prereq_mask_cell = gate_mask.flatten(start_dim=-2).any(dim=-1)

        bound = self.binding_head(register_modulated_states, prereq_mask_cell)
        sim_out = self.similarity(bound, self.registry)
        return {
            "binding": bound,
            "similarities": sim_out["similarities"],
            "candidate": sim_out["candidate"],
            "prereq_mask_cell": prereq_mask_cell,
        }
