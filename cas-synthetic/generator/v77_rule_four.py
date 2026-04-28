"""v7.7 Rule 4 generator — same-Noetic multi-register expressions.

Emits two sub-types:
  compliant (80%): either `+` co-presence, or `×` with named emergent result
                   drawn from the authoritative omega_registry.yaml.
  violation (20%): same-Noetic `×` WITHOUT a named emergent result —
                   deliberate Rule 4 violations for supervised compliance loss.

Every example carries register_labels. Violations carry `is_valid=false`
and a `distance_to_valid` value populated via the Rust engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import BaseGenerator, GeneratedExample


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "v77_rule_four_templates.yaml"
_OMEGA_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "cas-native"
    / "config"
    / "omega_registry.yaml"
)


class V77RuleFourGenerator(BaseGenerator):
    BUCKET = "v77_rule_four"

    # Violation rate within this bucket — 20% per directive
    VIOLATION_RATE: float = 0.20

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
        # Build lookup of admitted Omega names
        self.admitted_omega_names = {
            entry["name"] for entry in self.omega_registry.get("admitted", [])
        }

    def _generate_one(self) -> GeneratedExample:
        if self.rng.random() < self.VIOLATION_RATE:
            return self._generate_violation()
        return self._generate_compliant()

    # ---------------------------------------------------- compliant branch

    def _generate_compliant(self) -> GeneratedExample:
        scenarios = self.templates["scenarios"]
        # 50/50 split: + co-presence OR × with valid named emergent
        use_copresence = self.rng.random() < 0.5

        if use_copresence:
            # Build `^n^D_{Fk}|R1 + ^n^D_{Fk}|R2 [+ ^n^D_{Fk}|R3]` —
            # same-Noetic co-presence. Drive subscript precedes the register
            # pipe suffix per CAS v7.5 Clarification 8 / compiler grammar.
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            k = self.rng.choice([2, 3])
            registers = self.rng.sample(self.REGISTERS, k)
            drive = self.rng.choice(self.DRIVES)
            terms = [f"^{noetic}^{domain}_{{F{drive}}}|{r}" for r in registers]
            expression = " + ".join(terms)
            register_labels = [
                {"position": i, "register": r} for i, r in enumerate(registers)
            ]
            states = [(noetic, domain) for _ in registers]
            omega_labels: list[dict[str, Any]] = []
            response = (
                f"{self.rng.choice(scenarios)} holds the same Noetic as {k} co-present manifestations: "
                f"{', '.join(registers[:-1])}{' and ' if len(registers) > 1 else ''}{registers[-1]} registers simultaneously, "
                "each a distinct expression of the same underlying state."
            )
        else:
            # Pick a valid emergent combination from templates
            combo = self.rng.choice(self.templates["valid_emergent_combinations"])
            noetic = combo["noetic"]
            domain = combo["domain"] if combo.get("domain") else self.rng.choice(self.DOMAINS)
            registers = list(combo["registers"])
            self.rng.shuffle(registers)  # any register-order permutation is admissible
            omega_name = combo["omega_name"]
            if omega_name not in self.admitted_omega_names:
                # Registry admits this name; fallback to co-presence if not
                return self._generate_compliant()
            dom_part = f"^{domain}" if combo.get("domain") else ""
            # Per-register drive sampling regime — always include drive
            # subscripts to avoid the degenerate small-pool cases for
            # Ω_presence (k! = 2 without domain) and Ω_refusal (k! = 6
            # with domain locked to P).
            #   40% uniform drive across operands
            #   60% independent drive per operand (maximum diversity)
            if self.rng.random() < 0.4:
                d = self.rng.choice(self.DRIVES)
                drive_strs = [f"_{{F{d}}}" for _ in registers]
            else:
                drive_strs = [
                    f"_{{F{self.rng.choice(self.DRIVES)}}}" for _ in registers
                ]
            # Compiler-canon: Unicode `×` for cross-register integration; the
            # named emergent uses the Greek `Ω_*` prefix (the omega registry
            # stores names with the ASCII `Omega_` spelling for traceability,
            # but the lexer accepts both — we render Unicode `Ω_` here per
            # CAS v7.7 Clarification 10 spec).
            unicode_omega = omega_name.replace("Omega_", "Ω_")
            terms = [
                f"^{noetic}{dom_part}{drive_strs[i]}|{r}"
                for i, r in enumerate(registers)
            ]
            expression = "(" + " × ".join(terms) + f") = ^{noetic}{dom_part}|{unicode_omega}"
            register_labels = [
                {"position": i, "register": r} for i, r in enumerate(registers)
            ]
            omega_labels = [{"position": 0, "omega_name": omega_name}]
            # Use original domain or fallback
            dom_for_state = combo["domain"] or domain
            states = [(noetic, dom_for_state) for _ in registers]
            response = (
                f"{self.rng.choice(scenarios)} integrates {len(registers)} register manifestations of the same Noetic "
                f"into the named emergent state {omega_name}: {combo['description']}."
            )

        prompt = "Describe the register structure of this state."

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

    # ---------------------------------------------------- violation branch

    def _generate_violation(self) -> GeneratedExample:
        scenarios = self.templates["scenarios"]
        pattern = self.rng.choice(self.templates["violation_patterns"])
        noetic = pattern["noetic"]
        domain = pattern["domain"]
        registers = list(pattern["registers"])
        drive = self.rng.choice(self.DRIVES)

        # Drive subscript precedes the register pipe suffix per the CAS v7.5
        # canonical compound shape; the violation is the use of `×` to join
        # same-Noetic register manifestations WITHOUT a named emergent result
        # (Clarification 10 §4 admissibility rule). The compiler rejects
        # these at typecheck — that is the supervised-loss signal.
        terms = [f"^{noetic}^{domain}_{{F{drive}}}|{r}" for r in registers]
        expression = " × ".join(terms)  # no emergent result — deliberate violation

        register_labels = [
            {"position": i, "register": r} for i, r in enumerate(registers)
        ]
        states = [(noetic, domain) for _ in registers]

        # Severity-weighted distance approximation — Rust engine returns
        # 1.0 / 1.5 / 2.0 for 2- / 3- / 4-register violations. Populated
        # precisely by composite validator using cas_engine; the generator
        # pre-populates an approximate value so the example round-trips
        # even before Rust validation.
        n_reg = len(registers)
        approx_distance = {2: 1.0, 3: 1.5, 4: 2.0}.get(n_reg, 1.0)

        response = (
            f"{self.rng.choice(scenarios)}: {pattern['description']}. "
            "This expression crosses same-Noetic registers without naming the emergent result — a Rule 4 violation."
        )
        prompt = "Analyze the register structure of this expression."

        return GeneratedExample(
            prompt=prompt,
            response=response,
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=False,
            violation_type="same_noetic_cross_no_emergent",
            distance_to_valid=approx_distance,
        )
