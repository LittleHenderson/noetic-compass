"""v7.6 production semantics generator.

Emits examples with a `production_target` dict per data_format.md containing
prereqs (list of [state_id, coefficient]), optional leakages, and
observed_yield. Architecture preserves ability to extract theoretical yield
and limiting reagent from the Rust engine when running through the composite
validator.

Compiler-canon emission (per `noetic-compass-scaffold/.../api/notation/compiler.py`):
  - Recipe header uses Unicode `Θ(Ω_<name>)`; the production target inside
    the parentheses is a `Ω_*` literal (the compiler accepts ASCII `Theta`
    / `Omega_` aliases too, but we render the canonical Unicode glyphs).
  - Recipe body uses `+` as the additive prerequisite separator and the
    Unicode arrow `→` (U+2192) before the right-hand-side production
    target (which must match the header target).
  - Each prerequisite is a real state literal (`^N^D_{Fk}|R` with
    optional drive / register annotations) — NOT a `state_N` placeholder
    (the v7.6 grammar admits primary expressions, not bare identifiers,
    as recipe primitives).
  - Optional leakages render as `+ Λ·Ω_<side_name>` on the RHS.

Template-pool diversity: `v76_production_templates.yaml` ships ≥10 named
recipe archetypes covering all four domains, multiple drive axes, both
registered and register-neutral compositions, and several leakage
patterns. Per-example noise on observed_yield further diversifies the
ground-truth signal without changing structural admissibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "v76_production_templates.yaml"


class V76ProductionGenerator(BaseGenerator):
    BUCKET = "v76_production"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        with open(template_path or _TEMPLATE_PATH, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)

    # --------------------------------------------------- helper utilities

    @staticmethod
    def _format_coefficient(coef: float) -> str:
        """Render a recipe coefficient as a compact decimal string.

        The compiler's NUMBER pattern matches both `\\d+` and `\\d+\\.\\d+`,
        so we emit ints when the coefficient is integer-valued and short
        decimals otherwise. The `:g` format yields e.g. `1`, `1.5`, `0.7`
        without trailing zeros.
        """
        return f"{coef:g}"

    def _state_literal(
        self,
        state_id: int,
        drive: int | None,
        register: str | None,
    ) -> str:
        """Render a real CAS state literal from a (state_id, drive, register)
        triple. Compiler grammar requires the drive subscript to precede
        the register pipe suffix (`^N^D_{Fk}|R`), and admissibility for
        bare-domain or bare-noetic forms is preserved.
        """
        dom_idx = state_id // 10
        noetic = state_id % 10
        domain = self.DOMAINS[dom_idx]
        body = f"^{noetic}^{domain}"
        if drive is not None:
            body += f"_{{F{drive}}}"
        if register is not None:
            body += f"|{register}"
        return body

    # --------------------------------------------------- main generator

    def _generate_one(self) -> GeneratedExample:
        archetypes = self.templates["recipe_archetypes"]
        scenarios = self.templates["scenarios"]
        archetype = self.rng.choice(archetypes)

        # Per-example diversification: add small Gaussian noise to each
        # coefficient (clamped strictly positive — the compiler rejects
        # zero/negative recipe coefficients per Clarification 9 §2), and
        # randomly permute the prereq order (recipe `+` is commutative
        # at the notational level, so reordering preserves semantics).
        # This expands the unique-expression count well beyond the
        # template-pool size of 12 archetypes.
        prereqs_dict = list(archetype["prereqs"])
        self.rng.shuffle(prereqs_dict)
        # Per-coefficient noise: ±5% Gaussian, clamped to a minimum of
        # 0.05 so the compiler's "coefficient must be positive" rule
        # always holds, then rounded to two decimals for stable rendering.
        prereqs_dict_noisy: list[dict[str, Any]] = []
        for p in prereqs_dict:
            base = float(p["coefficient"])
            noisy = max(0.05, round(base + self.rng.gauss(0, base * 0.05), 2))
            prereqs_dict_noisy.append({**p, "coefficient": noisy})

        # Prereq (state_id, coefficient) pairs feed both the production_target
        # field (numeric, machine-consumable) and the rendered CAS expression
        # (compiler-canonical state literals).
        prereqs: list[list[float]] = [
            [int(p["state_id"]), float(p["coefficient"])]
            for p in prereqs_dict_noisy
        ]
        leakages_dict = archetype.get("leakages", [])
        leakages: list[list[float]] = [
            [int(l["state_id"]), float(l["magnitude"])]
            for l in leakages_dict
        ]
        # Slight per-example noise in observed_yield to diversify training
        base_yield = float(archetype["observed_yield"])
        observed_yield = round(max(0.0, base_yield + self.rng.gauss(0, 0.05)), 4)

        production_target = {
            "prereqs": prereqs,
            "leakages": leakages,
            "observed_yield": observed_yield,
        }

        # Reconstruct (noetic, domain) for scoring vectors.
        states: list[tuple[int, str]] = []
        for state_id, _coef in prereqs:
            dom_idx = int(state_id) // 10
            noetic = int(state_id) % 10
            domain = self.DOMAINS[dom_idx]
            states.append((noetic, domain))

        scenario = self.rng.choice(scenarios)
        prereq_desc = ", ".join(
            f"state {sid} (×{coef:.2f})" for sid, coef in prereqs
        )
        prompt = f"{scenario}: what recipe produces this outcome?"
        response = (
            f"The recipe for {archetype['name']} requires {prereq_desc}. "
            f"{archetype['description']}. Observed yield: {observed_yield:.2f}."
        )

        # CAS expression: canonical v7.6 recipe shape
        # `Θ(Ω_<name>) = a₁·X₁ + ... + aₙ·Xₙ → Ω_<name> [+ Λ·Ω_<side> ...]`
        omega_name = f"Ω_{archetype['name']}"
        prereq_terms: list[str] = []
        for prereq in prereqs_dict_noisy:
            literal = self._state_literal(
                state_id=int(prereq["state_id"]),
                drive=prereq.get("drive"),
                register=prereq.get("register"),
            )
            coef_str = self._format_coefficient(float(prereq["coefficient"]))
            prereq_terms.append(f"{coef_str}*{literal}")

        leakage_terms: list[str] = []
        for leak in leakages_dict:
            side_name = leak.get("side_name") or f"side_{leak['state_id']}"
            magnitude = float(leak["magnitude"])
            mag_str = self._format_coefficient(magnitude)
            # Compiler accepts both `Λ·Ω_side` and `coeff·Ω_side` shapes;
            # we render the latter as `<mag>*Λ·Ω_<side>` to encode the
            # leakage magnitude on the same term per Clarification 9 §3.
            leakage_terms.append(f"{mag_str}*Λ·Ω_{side_name}")

        rhs = omega_name
        if leakage_terms:
            rhs = omega_name + " + " + " + ".join(leakage_terms)

        expression = (
            f"Θ({omega_name}) = "
            + " + ".join(prereq_terms)
            + f" → {rhs}"
        )

        return GeneratedExample(
            prompt=prompt,
            response=response,
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=[],
            omega_labels=[],
            production_target=production_target,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )
