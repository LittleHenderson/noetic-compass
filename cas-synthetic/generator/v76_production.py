"""v7.6 production semantics generator.

Emits examples with a `production_target` dict per data_format.md containing
prereqs (list of [state_id, coefficient]), optional leakages, and
observed_yield. Architecture preserves ability to extract theoretical yield
and limiting reagent from the Rust engine when running through the composite
validator.
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

    def _generate_one(self) -> GeneratedExample:
        archetypes = self.templates["recipe_archetypes"]
        scenarios = self.templates["scenarios"]
        archetype = self.rng.choice(archetypes)

        prereqs = [
            [int(p["state_id"]), float(p["coefficient"])]
            for p in archetype["prereqs"]
        ]
        leakages = [
            [int(l["state_id"]), float(l["magnitude"])]
            for l in archetype.get("leakages", [])
        ]
        # Slight per-example noise in observed_yield to diversify training
        base_yield = float(archetype["observed_yield"])
        observed_yield = round(max(0.0, base_yield + self.rng.gauss(0, 0.05)), 4)

        production_target = {
            "prereqs": prereqs,
            "leakages": leakages,
            "observed_yield": observed_yield,
        }

        # Reconstruct a list of (noetic, domain) from state_ids for scores.
        states: list[tuple[int, str]] = []
        for state_id, _coef in prereqs:
            dom_idx = state_id // 10
            noetic = state_id % 10
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

        # CAS expression is a symbolic recipe form
        prereq_expr_terms = [
            f"{coef:g}*state_{sid}" for sid, coef in prereqs
        ]
        expression = (
            "Theta(" + archetype["name"] + ") = "
            + " + ".join(prereq_expr_terms)
            + " -> " + archetype["name"]
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
