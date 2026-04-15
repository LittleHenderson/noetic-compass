"""
PrerequisiteGateLayer: neural RPM-style gating for A0 -> D -> W -> P.

What is explicit here:
  - There are four ordered gates matching the RPM chain stages.
  - The model uses separate eta/epsilon parameter paths rather than a single
    symmetric transform.
  - Satisfaction is cached from the forward pass only.

What is *not* enforced here:
  - The section law epsilon ∘ eta = id is not hard-constrained.
  - This module should therefore be read as an RPM-inspired neural
    approximation, not as a literal implementation of the formal monadic
    construction.
"""

import torch
import torch.nn as nn


class SoftGate(nn.Module):
    """A single differentiable soft gate.

    Computes a satisfaction score in [0, 1] via sigmoid, then element-wise
    multiplies the input. Below-threshold signals are attenuated, not
    hard-blocked, preserving gradient flow.
    """

    def __init__(self, d_model: int, threshold: float = 0.5):
        super().__init__()
        self.gate_proj = nn.Linear(d_model, d_model)
        self.threshold = threshold

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Input tensor of shape (..., d_model)

        Returns:
            Tuple of (gated_output, satisfaction_scores)
            - gated_output: x * gate_score, shape (..., d_model)
            - satisfaction_scores: sigmoid outputs in [0, 1], shape (..., d_model)
        """
        satisfaction = torch.sigmoid(self.gate_proj(x))
        gated = x * satisfaction
        return gated, satisfaction


class PrerequisiteGateLayer(nn.Module):
    """Differentiable RPM-style prerequisite gate.

    The chain order is explicit, but the categorical section-retraction law
    is only approximated architecturally via separate eta/epsilon maps.
    """

    def __init__(self, d_model: int, threshold: float = 0.5):
        super().__init__()
        self.d_model = d_model
        self.threshold = threshold

        # 4 sequential soft gates: A0, Drive, Wisdom, Proficiency
        self.gate_a0 = SoftGate(d_model, threshold)
        self.gate_drive = SoftGate(d_model, threshold)
        self.gate_wisdom = SoftGate(d_model, threshold)
        self.gate_proficiency = SoftGate(d_model, threshold)

        # Forward embedding path (eta): embeds into prerequisite space
        self.eta = nn.Linear(d_model, d_model)

        # Retraction path (epsilon): separate, non-inverse of eta
        # epsilon . eta = id (section-retraction property)
        # BUT eta . epsilon != id (information loss possible)
        self.epsilon = nn.Linear(d_model, d_model)

        # Cache for forward satisfaction scores (CORRECTION 2)
        self._cached_satisfaction: dict[str, torch.Tensor] = {}

    def _clear_cache(self) -> None:
        """Clear cached satisfaction scores."""
        self._cached_satisfaction.clear()

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """
        Args:
            x: Input tensor of shape (batch, seq, d_model)

        Returns:
            Tuple of (output, satisfaction_dict)
            - output: Gated output, shape (batch, seq, d_model)
            - satisfaction_dict: Dict mapping gate names to satisfaction tensors
        """
        self._clear_cache()

        # Forward embedding (eta)
        embedded = self.eta(x)

        # Sequential gating: A0 -> Drive -> Wisdom -> Proficiency
        out_a0, sat_a0 = self.gate_a0(embedded)
        out_drive, sat_drive = self.gate_drive(out_a0)
        out_wisdom, sat_wisdom = self.gate_wisdom(out_drive)
        out_prof, sat_prof = self.gate_proficiency(out_wisdom)

        # Cache satisfaction scores (one-directional, forward only)
        self._cached_satisfaction = {
            "a0": sat_a0.detach(),
            "drive": sat_drive.detach(),
            "wisdom": sat_wisdom.detach(),
            "proficiency": sat_prof.detach(),
        }

        # Retraction (epsilon): project back from prerequisite space
        # Note: epsilon is NOT the inverse of eta (CORRECTION 2)
        output = self.epsilon(out_prof)

        satisfaction_dict = {
            "a0": sat_a0,
            "drive": sat_drive,
            "wisdom": sat_wisdom,
            "proficiency": sat_prof,
        }

        return output, satisfaction_dict

    def get_mean_satisfaction(self) -> torch.Tensor:
        """Get the mean satisfaction across all gates from the last forward pass.

        Returns:
            Scalar tensor with the mean satisfaction score.
        """
        if not self._cached_satisfaction:
            return torch.tensor(0.0)

        all_sats = torch.stack([s.mean() for s in self._cached_satisfaction.values()])
        return all_sats.mean()


# ---------------------------------------------------------------------------
# Recursive RPM Resolution Modules
# ---------------------------------------------------------------------------


class ExposureLoop(nn.Module):
    """CO-1/CO-4/CO-7 iterative loop for desire cultivation.

    NOT recursive — iterative. Desire cannot be acquired through rational
    sub-chains. It must be CULTIVATED through repeated exposure:
    CO-1 (observe) → CO-4 (intensify) → CO-7 (repeat) → loop.
    """

    def __init__(self, d_model: int, max_cycles: int = 10):
        super().__init__()
        self.observe = nn.Linear(d_model, d_model)      # CO-1
        self.intensify = nn.Linear(d_model, d_model)     # CO-4
        self.entrain = nn.Linear(d_model, d_model)       # CO-7
        self.threshold_check = nn.Linear(d_model, 1)
        self.max_cycles = max_cycles

    def forward(self, state: torch.Tensor) -> tuple[torch.Tensor, int]:
        """Run the exposure loop until desire threshold is met.

        Returns (modified_state, cycles_used).
        """
        cycles = 0
        for _ in range(self.max_cycles):
            state = torch.relu(self.observe(state))
            state = torch.relu(self.intensify(state))
            state = torch.relu(self.entrain(state))
            cycles += 1
            if torch.sigmoid(self.threshold_check(state)).mean() > 0.5:
                break
        return state, cycles


class CausalResolver(nn.Module):
    """CO-8/CO-9 resolution for blocked Power nodes.

    CO-8 scans for conditions that could CAUSE the resource to appear.
    CO-9 identifies the specific solution that RESULTS from the causal scan.
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.causal_scan = nn.Linear(d_model, d_model)     # CO-8
        self.effect_identify = nn.Linear(d_model, d_model)  # CO-9
        self.norm = nn.LayerNorm(d_model)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        cause = torch.relu(self.causal_scan(state))
        effect = torch.relu(self.effect_identify(cause))
        return self.norm(effect + state)  # residual


class KnowledgeReceptor(nn.Module):
    """CO-5 resolution for blocked Wisdom — find embodied knowledge source.

    "Find someone who EMBODIES the knowledge — a person whose experience
    includes it, a text that encodes it, a situation that demonstrates it."
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.search = nn.Linear(d_model, d_model)  # CO-5
        self.absorb = nn.Linear(d_model, d_model)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        source = torch.relu(self.search(state))
        absorbed = torch.relu(self.absorb(source))
        return self.norm(absorbed + state)


class KnowledgeDecomposer(nn.Module):
    """CO-6 resolution for blocked Wisdom — decompose into components.

    "Break the complex knowledge gap into smaller independently acquirable
    components. Each component spawns its own child chain."
    """

    def __init__(self, d_model: int, max_components: int = 4):
        super().__init__()
        self.max_components = max_components
        self.decompose = nn.Linear(d_model, d_model * max_components)
        self.component_gate = nn.Linear(d_model, 1)
        self.assemble = nn.Linear(d_model * max_components, d_model)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, state: torch.Tensor) -> tuple[list[torch.Tensor], torch.Tensor]:
        """Decompose state into components and reassemble.

        Returns (components, assembled_state).
        """
        raw = self.decompose(state)
        components = raw.chunk(self.max_components, dim=-1)
        # Filter to active components
        active = [c for c in components if torch.sigmoid(self.component_gate(c)).mean() > 0.3]
        if not active:
            active = list(components[:1])
        # Reassemble
        padded = torch.cat(active + [torch.zeros_like(active[0])] * (self.max_components - len(active)), dim=-1)
        assembled = self.norm(self.assemble(padded) + state)
        return active, assembled


class RecursiveRPMGate(nn.Module):
    """Recursive RPM gate with resolution mechanisms for each blocked node.

    When D/W/P nodes are blocked, specific CO pairs activate:
    - Desire blocked → CO-1/CO-4/CO-7 exposure loop (iterative)
    - Wisdom blocked → CO-5 reception or CO-6 decomposition (recursive)
    - Power blocked → CO-8/CO-9 causal search (recursive)

    Preserves the existing PrerequisiteGateLayer interface while adding
    recursive resolution capability.
    """

    def __init__(self, d_model: int, max_depth: int = 5, threshold: float = 0.5):
        super().__init__()
        self.max_depth = max_depth
        self.threshold = threshold

        # Base gates (same as PrerequisiteGateLayer)
        self.gate_desire = SoftGate(d_model, threshold)
        self.gate_wisdom = SoftGate(d_model, threshold)
        self.gate_power = SoftGate(d_model, threshold)

        # Resolution modules
        self.exposure_loop = ExposureLoop(d_model)
        self.causal_resolver = CausalResolver(d_model)
        self.knowledge_receptor = KnowledgeReceptor(d_model)
        self.knowledge_decomposer = KnowledgeDecomposer(d_model)

        # Operator activation extractors
        self.co1_ext = nn.Linear(d_model, 1)
        self.co4_ext = nn.Linear(d_model, 1)
        self.co5_ext = nn.Linear(d_model, 1)
        self.co6_ext = nn.Linear(d_model, 1)
        self.co7_ext = nn.Linear(d_model, 1)
        self.co8_ext = nn.Linear(d_model, 1)
        self.co9_ext = nn.Linear(d_model, 1)

        # Section-retraction paths
        self.eta = nn.Linear(d_model, d_model)
        self.epsilon = nn.Linear(d_model, d_model)

    def forward(
        self,
        x: torch.Tensor,
        depth: int = 0,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        embedded = self.eta(x)
        satisfaction: dict[str, torch.Tensor] = {}

        # --- Desire gate ---
        out_d, sat_d = self.gate_desire(embedded)
        satisfaction["desire"] = sat_d
        if sat_d.mean() < self.threshold and depth < self.max_depth:
            co1 = torch.sigmoid(self.co1_ext(embedded)).mean()
            co4 = torch.sigmoid(self.co4_ext(embedded)).mean()
            co7 = torch.sigmoid(self.co7_ext(embedded)).mean()
            if (co1 + co4 + co7) / 3.0 > 0.3:
                out_d, _cycles = self.exposure_loop(out_d)
                _, sat_d = self.gate_desire(out_d)
                satisfaction["desire"] = sat_d
                satisfaction["desire_exposure_activated"] = torch.tensor(1.0)

        # --- Wisdom gate ---
        out_w, sat_w = self.gate_wisdom(out_d)
        satisfaction["wisdom"] = sat_w
        if sat_w.mean() < self.threshold and depth < self.max_depth:
            co5 = torch.sigmoid(self.co5_ext(out_d)).mean()
            co6 = torch.sigmoid(self.co6_ext(out_d)).mean()
            if co5 > co6 and co5 > 0.3:
                out_w = self.knowledge_receptor(out_w)
                _, sat_w = self.gate_wisdom(out_w)
                satisfaction["wisdom"] = sat_w
                satisfaction["wisdom_reception_activated"] = torch.tensor(1.0)
            elif co6 > 0.3:
                _components, assembled = self.knowledge_decomposer(out_w)
                out_w = assembled
                _, sat_w = self.gate_wisdom(out_w)
                satisfaction["wisdom"] = sat_w
                satisfaction["wisdom_decomposition_activated"] = torch.tensor(1.0)

        # --- Power gate ---
        out_p, sat_p = self.gate_power(out_w)
        satisfaction["power"] = sat_p
        if sat_p.mean() < self.threshold and depth < self.max_depth:
            co8 = torch.sigmoid(self.co8_ext(out_w)).mean()
            co9 = torch.sigmoid(self.co9_ext(out_w)).mean()
            if co8 > 0.3 and co9 > 0.3:
                resolved = self.causal_resolver(out_p)
                # Recursive call on the resolved state
                sub_out, sub_sat = self.forward(resolved, depth + 1)
                out_p = sub_out
                _, sat_p = self.gate_power(out_p)
                satisfaction["power"] = sat_p
                satisfaction["power_causal_activated"] = torch.tensor(1.0)

        output = self.epsilon(out_p)
        return output, satisfaction
