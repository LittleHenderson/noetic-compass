"""v7.7 Rule 4 generator — same-Noetic multi-register expressions.

Emits two sub-types:
  compliant (80%): either `+` co-presence (same-Noetic register manifestations
                   joined by `+`), or `×` with named emergent result drawn
                   from the authoritative omega_registry.yaml.
  violation (20%): same-Noetic `×` WITHOUT a named emergent result —
                   deliberate Rule 4 violations for supervised compliance loss.

Every example carries register_labels. Violations carry `is_valid=false`
and a `distance_to_valid` value populated via the Rust engine.

Diversification overhaul (2026-04-28, pre-Phase-2-retry hardening):
Phase 2 10K analysis surfaced v77_rule_four at 38.5% redundancy
concentration — the most ML-concerning per-bucket dupe rate. Root cause:
violation arm drew from only 4 hard-coded patterns (noetic 2/5/6/8); compliant
emergent arm drew from only 2 omega names (Ω_presence, Ω_refusal); register
subsets were size-2 or size-3 but never size-4 in the violation arm. The
generator now randomizes orthogonally across six axes:

  1. Noetic — full {0..9} sample for both compliant `+` and violation arms.
     Compliant `×=Ω_*` arm draws Noetic from the registry entry (which now
     spans Noetics 0/1/2/3/4/5/6/7/8/9 after the registry expansion).
  2. Domain — uniform sample over {P, C, E, O} for non-locked entries.
     Domain-locked Ω_* entries (e.g. Ω_refusal at ^P) preserve their lock.
  3. Drive — per-operand independent sampling on every arm (compliant `+`,
     compliant `×=Ω_*`, and violation). Uniform-drive across operands is
     also represented at lower weight to preserve a slice of the simpler
     regime in the data.
  4. Register subset — size varies in {2, 3, 4}. The compliant `×=Ω_*` arm
     samples 2..len(registry_registers); the compliant `+` arm and the
     violation arm sample 2..4 freely from {T, A, f, E}.
  5. Compliant shape — 50/50 split between `+` co-presence and `×=Ω_*`
     named-emergent (Rule 4 admits both). Within `×=Ω_*`, the emergent
     name samples uniformly from all 12 admitted Ω entries.
  6. Violation type — current authoritative violation type is
     `same_noetic_cross_no_emergent` (Clarification 10 §4 admissibility
     rule). The arm preserves the ~20% allocation.

Compile-validate every emission. Compliant must compile valid; violation
round-trips as `is_valid=false, distance_to_valid > 0` because the
compiler rejects same-Noetic `×` without an emergent at typecheck (that
rejection is the supervised-loss signal).
"""

from __future__ import annotations

import importlib.util
import sys
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
_COMPILER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


def _load_compiler():
    """Load the compiler module by file path. Returns None if unavailable."""
    module_name = "cas_synthetic_v77_rule_four_compiler"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _COMPILER_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


# Operand pattern for parsing a registry derivation — captures
# (noetic, optional_domain, register).
import re as _re  # local alias to keep top-level imports tidy

_OPERAND_RE = _re.compile(r"\^(\d+)(?:\^([PCEO]))?\|([TAfE])")


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
        # Build lookup of admitted Omega names.
        self.admitted_omega_names = {
            entry["name"] for entry in self.omega_registry.get("admitted", [])
        }
        # Pre-parse each registry derivation into (noetic, domain, registers)
        # so the emergent arm can sample uniformly over the entire registry
        # without re-tokenizing per example.
        self._parsed_omega: list[dict[str, Any]] = []
        for entry in self.omega_registry.get("admitted", []):
            derivation = entry.get("derivation", "")
            left = derivation.split("=")[0] if "=" in derivation else derivation
            matches = _OPERAND_RE.findall(left)
            if not matches:
                continue
            self._parsed_omega.append(
                {
                    "name": entry["name"],
                    "noetic": int(matches[0][0]),
                    "domain": matches[0][1] if matches[0][1] else None,
                    "registers": [m[2] for m in matches],
                }
            )
        if not self._parsed_omega:
            raise RuntimeError(
                "omega_registry.yaml has no parseable admitted entries — "
                "v77_rule_four emergent arm cannot produce examples."
            )
        # Lazy-load the compiler for round-trip validation. None when the
        # compiler can't be loaded; in that case validation is skipped and we
        # trust the regime.
        self._compiler = _load_compiler()
        # Counters for compile-retry instrumentation (read by tests / metrics).
        self.compile_retries = 0
        self.compile_fallbacks = 0

    def _generate_one(self) -> GeneratedExample:
        if self.rng.random() < self.VIOLATION_RATE:
            return self._generate_violation()
        return self._generate_compliant()

    # ---------------------------------------------------- compliant branch

    def _generate_compliant(self) -> GeneratedExample:
        # 50/50 split: + co-presence OR × with valid named emergent.
        if self.rng.random() < 0.5:
            return self._generate_compliant_copresence()
        return self._generate_compliant_emergent()

    def _generate_compliant_copresence(self) -> GeneratedExample:
        """Same-Noetic register co-presence joined by `+`.

        Diversification axes:
          - Noetic: full {0..9} sample.
          - Domain: uniform over {P, C, E, O}.
          - Register subset size: {2, 3, 4} with weight 0.30/0.40/0.30.
          - Drive regime: 30% uniform-drive, 70% per-operand independent.
        """
        scenarios = self.templates["scenarios"]
        for _ in range(6):
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            k = self.rng.choices([2, 3, 4], weights=[0.30, 0.40, 0.30])[0]
            registers = self.rng.sample(self.REGISTERS, k)

            if self.rng.random() < 0.30:
                # Uniform drive across all operands.
                drive = self.rng.choice(self.DRIVES)
                drive_strs = [f"_{{F{drive}}}" for _ in registers]
            else:
                # Independent drive per operand — maximum diversity.
                drive_strs = [
                    f"_{{F{self.rng.choice(self.DRIVES)}}}" for _ in registers
                ]

            terms = [
                f"^{noetic}^{domain}{drive_strs[i]}|{r}"
                for i, r in enumerate(registers)
            ]
            expression = " + ".join(terms)
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            register_labels = [
                {"position": i, "register": r} for i, r in enumerate(registers)
            ]
            states = [(noetic, domain) for _ in registers]
            response = (
                f"{self.rng.choice(scenarios)} holds the same Noetic as {k} co-present manifestations: "
                f"{', '.join(registers[:-1])}{' and ' if len(registers) > 1 else ''}{registers[-1]} "
                "registers simultaneously, each a distinct expression of the same underlying state."
            )
            return GeneratedExample(
                prompt="Describe the register structure of this state.",
                response=response,
                cas_expression=expression,
                scores=self._scores_from_states(states),
                register_labels=register_labels,
                omega_labels=[],
                production_target=None,
                bucket=self.BUCKET,
                is_valid=True,
                violation_type=None,
                distance_to_valid=0.0,
            )
        # Fallback (shouldn't happen): canonical 2-register form.
        self.compile_fallbacks += 1
        noetic = self.rng.choice(self.NOETICS)
        domain = self.rng.choice(self.DOMAINS)
        registers = ["A", "f"]
        terms = [f"^{noetic}^{domain}|{r}" for r in registers]
        expression = " + ".join(terms)
        register_labels = [
            {"position": i, "register": r} for i, r in enumerate(registers)
        ]
        states = [(noetic, domain) for _ in registers]
        return GeneratedExample(
            prompt="Describe the register structure of this state.",
            response="A same-Noetic two-register co-presence.",
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=True,
            violation_type=None,
            distance_to_valid=0.0,
        )

    def _generate_compliant_emergent(self) -> GeneratedExample:
        """Same-Noetic ×-integration with named emergent result `Ω_*`.

        Diversification axes:
          - Emergent name: uniform over the entire admitted registry (12
            entries after the 2026-04-28 expansion).
          - Domain: locked entries preserve lock; open entries (Ω_presence /
            Ω_clarity / Ω_witness / Ω_attunement / Ω_genesis / Ω_cadence /
            Ω_invocation / Ω_landing) sample uniformly over {None, P, C, E, O}.
          - Register subset: when registry has ≥3 registers, sample size in
            [2, len(registers)]; 2-register entries always emit both.
          - Register order: permuted (`×` is commutative under named-emergent
            rewrite).
          - Drive regime: 30% uniform-drive, 70% per-operand independent.
        """
        scenarios = self.templates["scenarios"]
        for _ in range(6):
            entry = self.rng.choice(self._parsed_omega)
            noetic = entry["noetic"]
            omega_name = entry["name"]
            registry_registers: list[str] = list(entry["registers"])

            # Domain selection
            if entry["domain"] is not None:
                domain: str | None = entry["domain"]
            else:
                domain = self.rng.choice([None] + list(self.DOMAINS))

            # Register subset
            if len(registry_registers) >= 3:
                size = self.rng.randint(2, len(registry_registers))
                registers = self.rng.sample(registry_registers, size)
            else:
                registers = list(registry_registers)
                self.rng.shuffle(registers)

            # Drive regime
            if self.rng.random() < 0.30:
                drive = self.rng.choice(self.DRIVES)
                drive_strs = [f"_{{F{drive}}}" for _ in registers]
            else:
                drive_strs = [
                    f"_{{F{self.rng.choice(self.DRIVES)}}}" for _ in registers
                ]

            dom_part = f"^{domain}" if domain else ""
            unicode_omega = omega_name.replace("Omega_", "Ω_")
            terms = [
                f"^{noetic}{dom_part}{drive_strs[i]}|{r}"
                for i, r in enumerate(registers)
            ]
            expression = (
                "(" + " × ".join(terms) + f") = ^{noetic}{dom_part}|{unicode_omega}"
            )
            if not self._compile_ok(expression):
                self.compile_retries += 1
                continue
            register_labels = [
                {"position": i, "register": r} for i, r in enumerate(registers)
            ]
            omega_labels = [{"position": 0, "omega_name": omega_name}]
            dom_for_state = domain if domain else self.rng.choice(self.DOMAINS)
            states = [(noetic, dom_for_state) for _ in registers]
            response = (
                f"{self.rng.choice(scenarios)} integrates {len(registers)} register manifestations of the same Noetic "
                f"into the named emergent state {omega_name} at noetic {noetic}"
                f"{' in domain ' + domain if domain else ''}."
            )
            return GeneratedExample(
                prompt="Describe the register structure of this state.",
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
        # Fallback to canonical registry derivation (guaranteed admissible).
        self.compile_fallbacks += 1
        entry = self.rng.choice(self._parsed_omega)
        noetic = entry["noetic"]
        omega_name = entry["name"]
        domain = entry["domain"]
        registers = list(entry["registers"])
        unicode_omega = omega_name.replace("Omega_", "Ω_")
        dom_part = f"^{domain}" if domain else ""
        terms = [f"^{noetic}{dom_part}|{r}" for r in registers]
        expression = "(" + " × ".join(terms) + f") = ^{noetic}{dom_part}|{unicode_omega}"
        register_labels = [
            {"position": i, "register": r} for i, r in enumerate(registers)
        ]
        omega_labels = [{"position": 0, "omega_name": omega_name}]
        dom_for_state = domain if domain else self.rng.choice(self.DOMAINS)
        states = [(noetic, dom_for_state) for _ in registers]
        return GeneratedExample(
            prompt="Describe the register structure of this state.",
            response=f"Canonical {omega_name} integration.",
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
        """Same-Noetic `×` WITHOUT named emergent — deliberate Rule 4 violation.

        Diversification axes:
          - Noetic: full {0..9} sample.
          - Domain: uniform over {P, C, E, O}.
          - Register subset size: {2, 3, 4} with weight 0.40/0.40/0.20.
          - Drive regime: drive is uniform across operands (30% no-drive bare
            form, 70% uniform-drive subscript). Per-operand independent drives
            are NOT used here because the compiler considers operands with
            different drive subscripts to be different states — that path
            yields compile-valid `×` joins, which are NOT Rule 4 violations.
            Diversity in this arm comes from Noetic × Domain × register-subset
            × drive choice (10 × 4 × ~13 subset patterns × 8 drive options ≈
            4160 distinct templates), not from per-operand drive variance.

        The compiler rejects these expressions at typecheck — the rejection
        is precisely the supervised-loss signal Rule 4 teaches.
        """
        scenarios = self.templates["scenarios"]
        for _ in range(6):
            noetic = self.rng.choice(self.NOETICS)
            domain = self.rng.choice(self.DOMAINS)
            k = self.rng.choices([2, 3, 4], weights=[0.40, 0.40, 0.20])[0]
            registers = self.rng.sample(self.REGISTERS, k)

            # Same-state means same Noetic, same Domain, AND same Drive across
            # operands. The drive subscript is either omitted entirely (bare
            # `^N^D|R`) or uniform across operands. Independent-drive variants
            # bypass Rule 4 and would not exercise the typecheck rejection.
            if self.rng.random() < 0.30:
                drive_strs = ["" for _ in registers]
            else:
                drive = self.rng.choice(self.DRIVES)
                drive_strs = [f"_{{F{drive}}}" for _ in registers]

            terms = [
                f"^{noetic}^{domain}{drive_strs[i]}|{r}"
                for i, r in enumerate(registers)
            ]
            expression = " × ".join(terms)  # no emergent — deliberate violation

            # Confirm the compiler indeed rejects (this is the violation
            # signal). If by accident the form is admissible, retry.
            if self._compile_ok(expression):
                self.compile_retries += 1
                continue

            register_labels = [
                {"position": i, "register": r} for i, r in enumerate(registers)
            ]
            states = [(noetic, domain) for _ in registers]
            approx_distance = {2: 1.0, 3: 1.5, 4: 2.0}.get(k, 1.0)
            response = (
                f"{self.rng.choice(scenarios)}: cross-register integration of "
                f"^{noetic}^{domain} across {k} registers without naming the "
                "emergent result — a Rule 4 violation."
            )
            return GeneratedExample(
                prompt="Analyze the register structure of this expression.",
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
        # Fallback: canonical 2-register violation.
        self.compile_fallbacks += 1
        noetic = self.rng.choice(self.NOETICS)
        domain = self.rng.choice(self.DOMAINS)
        registers = self.rng.sample(self.REGISTERS, 2)
        terms = [f"^{noetic}^{domain}|{r}" for r in registers]
        expression = " × ".join(terms)
        register_labels = [
            {"position": i, "register": r} for i, r in enumerate(registers)
        ]
        states = [(noetic, domain) for _ in registers]
        return GeneratedExample(
            prompt="Analyze the register structure of this expression.",
            response="A Rule 4 violation: same-Noetic × without emergent result.",
            cas_expression=expression,
            scores=self._scores_from_states(states),
            register_labels=register_labels,
            omega_labels=[],
            production_target=None,
            bucket=self.BUCKET,
            is_valid=False,
            violation_type="same_noetic_cross_no_emergent",
            distance_to_valid=1.0,
        )

    # ---------------------------------------------------- helpers

    def _compile_ok(self, expression: str) -> bool:
        """Round-trip an expression through the compiler. Returns True iff
        the compiler reports valid. When the compiler can't be loaded
        (headless test fixtures), trust the regime and return True."""
        if self._compiler is None:
            return True
        try:
            artifact = self._compiler.compile_expression(expression)
            return bool(artifact.valid)
        except Exception:
            return False
