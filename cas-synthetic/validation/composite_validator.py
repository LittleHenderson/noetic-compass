"""Composite (semantic coherence) validator.

Checks beyond schema shape:
  1. Registers in `register_labels` appear in `cas_expression` (when both present).
  2. `omega_name` in `omega_labels` is admitted in omega_registry.yaml.
  3. Prereq state_ids in `production_target` are in [0, 40) (covered by schema too,
     checked here for completeness).
  4. When `is_valid=false`, expect `distance_to_valid > 0` or a declared violation_type.
  5. Rust engine Rule 4 result (when applicable) matches the example's
     declared is_valid / violation_type metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schema_validator import CANONICAL_REGISTERS


_OMEGA_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "cas-native"
    / "config"
    / "omega_registry.yaml"
)


@dataclass
class CompositeValidationReport:
    ok: bool
    issues: list[str] = field(default_factory=list)
    rule_four_checked: bool = False
    rule_four_valid: bool | None = None
    rule_four_distance: float | None = None


class CompositeValidator:
    def __init__(self, omega_registry_path: Path | None = None) -> None:
        path = omega_registry_path or _OMEGA_REGISTRY_PATH
        try:
            with open(path, encoding="utf-8") as f:
                registry = yaml.safe_load(f)
        except FileNotFoundError:
            registry = {"admitted": []}
        self.admitted_omega_names = {
            entry["name"] for entry in registry.get("admitted", [])
        }

    def validate(
        self,
        example: dict[str, Any],
        rust_rule_four: dict[str, Any] | None = None,
    ) -> CompositeValidationReport:
        issues: list[str] = []

        cas_expr = example.get("cas_expression", "")
        register_labels = example.get("register_labels", []) or []
        omega_labels = example.get("omega_labels", []) or []
        production_target = example.get("production_target")
        meta = example.get("_meta", {})

        # 1. Register labels appear in cas_expression
        if register_labels and cas_expr:
            for lbl in register_labels:
                reg = lbl.get("register")
                if reg not in CANONICAL_REGISTERS:
                    continue  # schema already flags
                if f"|{reg}" not in cas_expr and f"|<" not in cas_expr:
                    issues.append(
                        f"register_labels includes {reg!r} but '|{reg}' not in cas_expression"
                    )

        # 2. Omega names admitted
        for lbl in omega_labels:
            name = lbl.get("omega_name")
            if name and name not in self.admitted_omega_names:
                issues.append(
                    f"omega_labels: {name!r} not admitted in omega_registry.yaml "
                    f"(admitted: {sorted(self.admitted_omega_names)})"
                )

        # 3. Prereq state ids — already schema-enforced; redundant coherence check.
        if production_target:
            prereqs = production_target.get("prereqs", [])
            if prereqs:
                for i, pair in enumerate(prereqs):
                    try:
                        sid, _ = pair
                    except Exception:
                        continue
                    if isinstance(sid, int) and not (0 <= sid < 40):
                        issues.append(
                            f"production_target.prereqs[{i}].state_id {sid} outside [0, 40)"
                        )

        # 4. Violation metadata coherence
        is_valid_meta = meta.get("is_valid", True)
        dist = meta.get("distance_to_valid", 0.0)
        vtype = meta.get("violation_type")
        if not is_valid_meta:
            if dist <= 0 and not vtype:
                issues.append(
                    "example marked is_valid=false but no distance_to_valid and no violation_type"
                )

        # 5. Rust Rule 4 coherence
        rf_valid = None
        rf_dist = None
        if rust_rule_four and rust_rule_four.get("applicable"):
            rf_valid = rust_rule_four["is_valid"]
            rf_dist = rust_rule_four["distance"]
            # If Rust says valid but example declared invalid, or vice versa
            if rf_valid != is_valid_meta:
                issues.append(
                    f"Rust Rule 4 valid={rf_valid} disagrees with example metadata is_valid={is_valid_meta}"
                )

        return CompositeValidationReport(
            ok=not issues,
            issues=issues,
            rule_four_checked=bool(rust_rule_four and rust_rule_four.get("applicable")),
            rule_four_valid=rf_valid,
            rule_four_distance=rf_dist,
        )
