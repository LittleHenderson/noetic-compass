"""v7.7 named emergent register (Ω_*) generator.

Emits examples where a named emergent register is the foregrounded label.
Only draws names from the authoritative omega_registry.yaml (Appendix I
synchronized). Architecture supports adding new Ω_* by adding registry
rows — no code change required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "v77_omega_templates.yaml"
_OMEGA_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "cas-native"
    / "config"
    / "omega_registry.yaml"
)


class V77OmegaGenerator(BaseGenerator):
    BUCKET = "v77_omega"

    def __init__(
        self,
        seed: int | None = None,
        llm_provider: Any = None,
        template_path: Path | None = None,
        omega_registry_path: Path | None = None,
    ) -> None:
        super().__init__(seed=seed, llm_provider=llm_provider)
        with open(template_path or _TEMPLATE_PATH, encoding="utf-8") as f:
            self.templates = yaml.safe_load(f)
        with open(omega_registry_path or _OMEGA_REGISTRY_PATH, encoding="utf-8") as f:
            self.omega_registry = yaml.safe_load(f)
        self.admitted = self.omega_registry.get("admitted", [])
        if not self.admitted:
            raise RuntimeError(
                "omega_registry.yaml has no admitted entries — v77 omega "
                "generator cannot produce examples without admitted names."
            )

    def _generate_one(self) -> GeneratedExample:
        entry = self.rng.choice(self.admitted)
        omega_name = entry["name"]
        derivation = entry.get("derivation", "")

        # Extract noetic/domain/registers from derivation string
        # e.g. "(^1|A x ^1|E) = ^1|Omega_presence"
        #      "(^3^P|A x ^3^P|f x ^3^P|T) = ^3^P|Omega_refusal"
        noetic, domain, registers = self._parse_derivation(derivation)

        # Expression — reproduce derivation
        expression = derivation

        register_labels = [
            {"position": i, "register": r} for i, r in enumerate(registers)
        ]
        omega_labels = [{"position": 0, "omega_name": omega_name}]

        dom_for_state = domain if domain else self.rng.choice(self.DOMAINS)
        states = [(noetic, dom_for_state) for _ in registers]

        # Build natural-language prompt/response
        scaffolds = self.templates.get("scaffolds", [])
        profs = self.templates.get("professions", [])
        sits = self.templates.get("situations", [])
        scenario_lines = self.templates.get("omega_scenarios", {}).get(omega_name, [])

        if scenario_lines:
            scenario = self.rng.choice(scenario_lines)
        else:
            scenario = f"A scene in which {omega_name} emerges"
        scaffold_tmpl = self.rng.choice(scaffolds) if scaffolds else "{omega_description}"
        filled = scaffold_tmpl
        for key, pool in (("profession", profs), ("situation", sits)):
            if "{" + key + "}" in filled and pool:
                filled = filled.replace("{" + key + "}", self.rng.choice(pool))
        filled = filled.replace("{omega_description}", scenario.lower())
        filled = filled.replace("{context}", self.rng.choice(profs) if profs else "a real-world context")

        prompt = f"Describe a situation in which the emergent register {omega_name} arises."
        response = (
            f"{filled}. Here {omega_name} is the named emergent register produced by "
            f"integrating the same-Noetic registers {', '.join(registers)} "
            f"at noetic {noetic}{' in domain ' + domain if domain else ''}."
        )

        return GeneratedExample(
            prompt=prompt,
            response=response,
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=omega_labels,
            production_target=None,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )

    # ---------------------------------------------------------- parsing

    def _parse_derivation(self, derivation: str) -> tuple[int, str | None, list[str]]:
        """Extract (noetic, domain or None, list-of-registers) from a derivation
        string like `(^1|A x ^1|E) = ^1|Omega_presence` or
        `(^3^P|A x ^3^P|f x ^3^P|T) = ^3^P|Omega_refusal`.
        """
        import re

        # Match operand patterns like ^N^D|R or ^N|R
        operand_pattern = re.compile(r"\^(\d+)(?:\^([PCEO]))?\|([TAfE])")
        matches = operand_pattern.findall(derivation)
        if not matches:
            # Fallback
            return 1, None, ["A", "E"]

        # Filter out the right-hand side (after `=`) when possible
        left_side = derivation.split("=")[0] if "=" in derivation else derivation
        matches = operand_pattern.findall(left_side)

        noetic = int(matches[0][0])
        domain = matches[0][1] if matches[0][1] else None
        registers = [m[2] for m in matches]
        return noetic, domain, registers
