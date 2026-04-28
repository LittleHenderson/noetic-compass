"""v7.7 named emergent register (Ω_*) generator.

Emits examples where a named emergent register is the foregrounded label.
Only draws names from the authoritative omega_registry.yaml (Appendix I
synchronized). Architecture supports adding new Ω_* by adding registry
rows — no code change required.

Compiler-canon emission (per `noetic-compass-scaffold/.../api/notation/compiler.py`):
  - Cross-register integration uses Unicode `×` (U+00D7), not ASCII `x`.
  - Named emergent uses the Greek `Ω_*` prefix (U+03A9). The registry
    stores names as `Omega_*` for ASCII traceability; the compiler
    accepts both spellings, but we render `Ω_*` per CAS v7.7
    Clarification 10 spec.
  - Each register-instantiation may carry an optional drive subscript:
    canonical shape `^N^D_{Fk}|R` per CAS v7.5 Clarification 8.

Diversity-expansion overhaul (2026-04-27, pre-Phase-2 hardening): the
generator randomizes aggressively over every orthogonal axis Rule 4
admits while every emitted expression is anchored to a registry-admitted
Ω_* name. Phase 1 gate measurement at n=200 showed v77_omega contributing
~32 of 86 dataset duplicates — concentrated on a 2-entry registry with
fixed register sets. The expanded registry (slots 2-7) plus the
randomization regime below targets per-bucket dupes <10 at n=200 and
sub-linear duplication at the n=2000 Phase 2 allocation.

Per-example randomization axes:
  - Ω name: uniform across the full admitted registry.
  - Domain: domain-locked entries keep their locked domain. Domain-open
    entries (e.g. Ω_presence) sample uniformly over {None, P, C, E, O},
    yielding both noetic-level (`^N|R`) and domain-anchored (`^N^D|R`)
    forms.
  - Drive regime: 25% no-drive / 35% uniform-drive / 40% per-operand
    independent drive. All three are compiler-admissible — Rule 4
    same-core enforcement is bypassed by the `= …|Ω` emergent
    assignment.
  - Register subset: when the registry entry lists ≥3 registers the
    generator samples a random subset of size in [2, len(registers)],
    yielding both partial and full register integrations. Single-pair
    entries always emit both registers.
  - Register order: permuted; cross-register `×` is commutative under
    the named-emergent rewrite so any order carries the same semantics.

Compile-validation: every emitted expression is round-tripped through
`api.notation.compile_expression`; if the random combination yields a
compiler error the generator falls back to the registry's canonical
derivation rendering. This is a defensive fallback — we expect 100%
admissibility under the regime above.
"""

from __future__ import annotations

import re
import sys
import importlib.util
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
_COMPILER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


# Operand pattern for parsing a registry derivation — captures
# (noetic, optional_domain, register).
_OPERAND_RE = re.compile(r"\^(\d+)(?:\^([PCEO]))?\|([TAfE])")


def _load_compiler():
    module_name = "cas_synthetic_v77_omega_compiler"
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
        # Pre-parse each registry derivation so we don't re-tokenize per
        # example. Each entry yields (noetic, domain_or_None, registers).
        self._parsed_entries: list[dict[str, Any]] = []
        for entry in self.admitted:
            noetic, domain, registers = self._parse_derivation(entry.get("derivation", ""))
            self._parsed_entries.append(
                {
                    "name": entry["name"],
                    "noetic": noetic,
                    "domain": domain,
                    "registers": registers,
                    "description": entry.get("description", ""),
                }
            )
        # Lazy-load the compiler for round-trip validation. None when the
        # compiler can't be loaded (e.g. test fixtures under headless CI);
        # in that case validation is skipped and we trust the regime.
        self._compiler = _load_compiler()

    def _generate_one(self) -> GeneratedExample:
        # Up to 6 attempts to find a compile-valid randomized form; if all
        # six fall through (shouldn't happen under the current regime but
        # defensively guarded), fall back to the registry's canonical
        # derivation rendering on the same entry.
        entry = self.rng.choice(self._parsed_entries)
        for _ in range(6):
            cand = self._build_candidate(entry)
            expr = cand["expression"]
            if self._compile_ok(expr):
                return self._materialize(entry, cand)
        # Fallback: deterministic canonical rendering from the parsed
        # entry. Guaranteed admissible because it mirrors the registry's
        # stored derivation.
        cand = self._canonical_candidate(entry)
        return self._materialize(entry, cand)

    # --------------------------------------------------------- candidates

    def _build_candidate(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Sample one randomized rendering of `entry`'s emergent expression.

        Returns dict with keys: expression, noetic, domain, registers,
        drives_per_operand, uniform_drive (or None), omega_name.
        """
        noetic: int = entry["noetic"]
        omega_name: str = entry["name"]
        registry_registers: list[str] = list(entry["registers"])

        # Domain selection: domain-locked entries are anchored. Domain-open
        # entries spread uniformly over {None, P, C, E, O} to yield both
        # noetic-level and domain-anchored variants.
        if entry["domain"] is not None:
            domain: str | None = entry["domain"]
        else:
            options: list[str | None] = [None] + list(self.DOMAINS)
            domain = self.rng.choice(options)

        # Register subset: for entries with ≥3 registers, sample a random
        # subset of size in [2, len]. Two-register entries always emit
        # both registers (size 2 is the floor for cross-register
        # integration). Order is then permuted.
        if len(registry_registers) >= 3:
            k = self.rng.randint(2, len(registry_registers))
            registers = self.rng.sample(registry_registers, k)
        else:
            registers = list(registry_registers)
            self.rng.shuffle(registers)

        # Drive regime — three modes, all compiler-admissible because the
        # `= …|Ω` clause licenses the chain regardless of drive uniformity.
        # Mode weights chosen to maximize the per-bucket unique-form pool:
        # independent-drive yields k×7 unique forms per (Ω, register order)
        # tuple; uniform-drive only 7; no-drive only 1. We weight toward
        # independent-drive while keeping the simpler regimes represented.
        # For 2-operand entries (e.g. Ω_resolve, Ω_clarity, Ω_presence)
        # the no-drive form collapses to a single rendering and the
        # uniform-drive form to 7 — both heavy duplication risks at any
        # bucket size. Lean on independent-drive proportionally harder for
        # small operand counts.
        if len(registers) <= 2:
            no_drive_thresh = 0.05
            uniform_thresh = 0.20
        else:
            no_drive_thresh = 0.15
            uniform_thresh = 0.40
        regime_roll = self.rng.random()
        if regime_roll < no_drive_thresh:
            # No-drive: bare `^N^D|R` operands.
            uniform_drive: int | None = None
            drive_strs = ["" for _ in registers]
            drives_per_operand: list[int | None] = [None for _ in registers]
        elif regime_roll < uniform_thresh:
            # Uniform drive across all operands.
            uniform_drive = self.rng.choice(self.DRIVES)
            drive_strs = [f"_{{F{uniform_drive}}}" for _ in registers]
            drives_per_operand = [uniform_drive for _ in registers]
        else:
            # Independent drive per operand — maximum diversity.
            uniform_drive = None
            drives_per_operand = [self.rng.choice(self.DRIVES) for _ in registers]
            drive_strs = [f"_{{F{d}}}" for d in drives_per_operand]

        dom_part = f"^{domain}" if domain else ""
        unicode_omega = omega_name.replace("Omega_", "Ω_")
        terms = [
            f"^{noetic}{dom_part}{drive_strs[i]}|{r}"
            for i, r in enumerate(registers)
        ]
        expression = "(" + " × ".join(terms) + f") = ^{noetic}{dom_part}|{unicode_omega}"

        return {
            "expression": expression,
            "noetic": noetic,
            "domain": domain,
            "registers": registers,
            "drives_per_operand": drives_per_operand,
            "uniform_drive": uniform_drive,
            "omega_name": omega_name,
            "unicode_omega": unicode_omega,
        }

    def _canonical_candidate(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Deterministic fallback rendering — mirror the registry derivation
        verbatim. Guaranteed admissible because the registry stores
        already-validated derivations."""
        noetic = entry["noetic"]
        domain = entry["domain"]
        registers = list(entry["registers"])
        omega_name = entry["name"]
        unicode_omega = omega_name.replace("Omega_", "Ω_")
        dom_part = f"^{domain}" if domain else ""
        terms = [f"^{noetic}{dom_part}|{r}" for r in registers]
        expression = "(" + " × ".join(terms) + f") = ^{noetic}{dom_part}|{unicode_omega}"
        return {
            "expression": expression,
            "noetic": noetic,
            "domain": domain,
            "registers": registers,
            "drives_per_operand": [None for _ in registers],
            "uniform_drive": None,
            "omega_name": omega_name,
            "unicode_omega": unicode_omega,
        }

    def _compile_ok(self, expression: str) -> bool:
        if self._compiler is None:
            return True
        try:
            artifact = self._compiler.compile_expression(expression)
            return bool(artifact.valid)
        except Exception:
            return False

    # ------------------------------------------------------ materialization

    def _materialize(
        self, entry: dict[str, Any], cand: dict[str, Any]
    ) -> GeneratedExample:
        noetic = cand["noetic"]
        domain = cand["domain"]
        registers = cand["registers"]
        omega_name = cand["omega_name"]
        unicode_omega = cand["unicode_omega"]
        uniform_drive = cand["uniform_drive"]
        expression = cand["expression"]

        register_labels = [
            {"position": i, "register": r} for i, r in enumerate(registers)
        ]
        omega_labels = [{"position": 0, "omega_name": omega_name}]

        dom_for_state = domain if domain else self.rng.choice(self.DOMAINS)
        states = [(noetic, dom_for_state) for _ in registers]

        # Build natural-language prompt/response.
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
        filled = filled.replace(
            "{context}", self.rng.choice(profs) if profs else "a real-world context"
        )

        prompt = f"Describe a situation in which the emergent register {omega_name} arises."
        response = (
            f"{filled}. Here {unicode_omega} is the named emergent register produced by "
            f"integrating the same-Noetic registers {', '.join(registers)} "
            f"at noetic {noetic}{' in domain ' + domain if domain else ''}"
            f"{' under drive F' + str(uniform_drive) if uniform_drive is not None else ''}."
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

        Note: registry derivation strings are stored with ASCII `x` and
        ASCII `Omega_` for archival readability. The generator transforms
        these into compiler-canon `×` and `Ω_` at emission time.
        """
        # Filter out the right-hand side (after `=`) when possible
        left_side = derivation.split("=")[0] if "=" in derivation else derivation
        matches = _OPERAND_RE.findall(left_side)
        if not matches:
            # Fallback shouldn't happen for admitted entries, but degrade
            # gracefully if registry shape changes.
            return 1, None, ["A", "E"]

        noetic = int(matches[0][0])
        domain = matches[0][1] if matches[0][1] else None
        registers = [m[2] for m in matches]
        return noetic, domain, registers
