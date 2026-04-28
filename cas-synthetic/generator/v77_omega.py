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

Template-pool diversity: rather than re-emit the registry's `derivation`
string verbatim (which yields only ~2 unique expressions for the
currently-admitted entries), the generator varies the orthogonal axes
the registry leaves free:
  - Register order permutation within the entry's register set.
  - Optional drive subscript per register-instantiation.
  - Domain choice when the registry entry leaves domain open
    (e.g. Ω_presence, which lives at the noetic level).
This yields well over the directive's ≥10 unique expressions per bucket
even at the current capacity-2 admitted registry.
"""

from __future__ import annotations

import re
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


# Operand pattern for parsing a registry derivation — captures
# (noetic, optional_domain, register).
_OPERAND_RE = re.compile(r"\^(\d+)(?:\^([PCEO]))?\|([TAfE])")


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

    def _generate_one(self) -> GeneratedExample:
        entry = self.rng.choice(self._parsed_entries)
        omega_name = entry["name"]
        noetic = entry["noetic"]
        # Domain selection: if the registry pinned a domain to this Ω_*,
        # the named emergent is anchored at that domain — we keep it. If
        # the registry left domain open (e.g. Ω_presence), we randomly
        # either omit the domain (noetic-level) or pick a domain to
        # diversify the expression pool.
        if entry["domain"] is not None:
            domain: str | None = entry["domain"]
        else:
            # 50% no-domain (noetic-level emergent), 50% pick a domain.
            if self.rng.random() < 0.5:
                domain = None
            else:
                domain = self.rng.choice(self.DOMAINS)

        # Register order permutation — derivation order is one valid
        # rendering; cross-register `×` is commutative at this notational
        # level so any permutation also compiles and carries the same
        # semantics. Variation expands the pool from O(entries) to
        # O(entries × |registers|! × drive-axis × domain-axis).
        registers = list(entry["registers"])
        self.rng.shuffle(registers)

        # Drive subscripts on the operands: independent per-register-instantiation.
        # Sampling regime — every example carries at least one drive
        # subscript so the unique-combination space is always at least
        # k! × 7. Without drives the no-domain Ω_presence pool degenerates
        # to 2 unique forms and Ω_refusal (domain-locked) to 6 forms,
        # which guarantees duplicates at any reasonable bucket size.
        #   - 40% uniform drive across all operands (single-drive emphasis)
        #   - 60% independent drive per operand (maximum diversity)
        if self.rng.random() < 0.4:
            uniform_drive: int | None = self.rng.choice(self.DRIVES)
            drive_strs = [f"_{{F{uniform_drive}}}" for _ in registers]
        else:
            uniform_drive = None
            drive_strs = [
                f"_{{F{self.rng.choice(self.DRIVES)}}}" for _ in registers
            ]

        dom_part = f"^{domain}" if domain else ""
        # Render Unicode `Ω_` from the registry's ASCII `Omega_` spelling.
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
        filled = filled.replace("{context}", self.rng.choice(profs) if profs else "a real-world context")

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
