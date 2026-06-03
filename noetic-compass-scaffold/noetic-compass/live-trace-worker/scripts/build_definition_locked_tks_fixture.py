#!/usr/bin/env python3
"""Build a definition-locked CAS/TKS probe fixture.

This fixture is deliberately different from the Condition-3 topical fixture:
its prompts are generated from the locked CAS/TKS definition sources rather
than from topical business scenarios. It is an input artifact, not a verdict.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_definition_locked_tks_fixture.v1"
DEFAULT_OUTPUT_DIR = Path("docs/working/definition_locked_tks_mtc_20260603")
VARIANTS_PER_CLASS = 12


NOETICS = [
    {
        "operator": "^0",
        "co": "CO-0",
        "name": "Idea",
        "definition": "All things in and outside the Mind.",
    },
    {
        "operator": "^1",
        "co": "CO-1",
        "name": "Mind",
        "definition": "Various degrees of awareness that processes, stores, outputs, and intakes Ideas.",
    },
    {
        "operator": "^2",
        "co": "CO-2",
        "name": "Positive",
        "definition": "An Idea the Mind has an affinity for and is attracted toward.",
    },
    {
        "operator": "^3",
        "co": "CO-3",
        "name": "Negative",
        "definition": "An Idea the Mind is adverse to and repelled by.",
    },
    {
        "operator": "^4",
        "co": "CO-4",
        "name": "Vibration",
        "definition": "The degree to which an Idea resonates with the Mind, its impression.",
    },
    {
        "operator": "^5",
        "co": "CO-5",
        "name": "Female",
        "definition": "A Mind impregnated with an Idea, the Ideas a Mind is composed of.",
    },
    {
        "operator": "^6",
        "co": "CO-6",
        "name": "Male",
        "definition": "An Idea impregnated with another Idea, the Ideas an Idea is composed of.",
    },
    {
        "operator": "^7",
        "co": "CO-7",
        "name": "Rhythm",
        "definition": "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.",
    },
    {
        "operator": "^8",
        "co": "CO-8",
        "name": "Above/Cause",
        "definition": "An Idea that triggers a different Idea than itself to come to Mind.",
    },
    {
        "operator": "^9",
        "co": "CO-9",
        "name": "Below/Effect",
        "definition": "The Idea brought to Mind by an Above/Cause trigger.",
    },
]


DOMAINS = [
    {
        "domain": "P",
        "name": "Principled",
        "definition": "The highest level of the cognitive architecture: axioms, non-negotiables, core identity, universal truths, intent, integrity, the why, and the always.",
    },
    {
        "domain": "C",
        "name": "Cognitive",
        "definition": "The map-room level: facts, logic, data, categories, strategy, systemic planning, accuracy, efficiency, the how, and the what.",
    },
    {
        "domain": "E",
        "name": "Evaluative",
        "definition": "The value-and-weight level: subjective value, emotional resonance, aesthetic weight, meaning, consequence, tradeoff friction, and what it costs.",
    },
    {
        "domain": "O",
        "name": "Operational",
        "definition": "The concrete execution level: physical action, immediate sensory feedback, material substrate, result, impact, the now, and the doing.",
    },
]


DRIVES = [
    {
        "drive": "F1",
        "name": "Unity",
        "definition": "the drive toward wholeness, coherence, reconciliation, and integration across particulars",
    },
    {
        "drive": "F2",
        "name": "Wisdom",
        "definition": "the drive toward understanding, evidence, learning, comprehension, and insight",
    },
    {
        "drive": "F3",
        "name": "Vitality",
        "definition": "the drive toward life, energy, thriving, safety, health, and aliveness",
    },
    {
        "drive": "F4",
        "name": "Connection",
        "definition": "the drive toward relationship, empathy, mutual attunement, and social coherence",
    },
    {
        "drive": "F5",
        "name": "Agency",
        "definition": "the drive toward choice, action, responsibility, control, and execution authority",
    },
    {
        "drive": "F6",
        "name": "Structure",
        "definition": "the drive toward order, rules, boundaries, safeguards, constraints, and system design",
    },
    {
        "drive": "F7",
        "name": "Purpose",
        "definition": "the drive toward meaning, long-term goals, calling, direction, and larger consequences",
    },
]


REGISTERS = [
    {
        "register": "T",
        "name": "Transcendent",
        "definition": "high-abstraction, purpose-orienting, integrative-across-particulars",
    },
    {
        "register": "A",
        "name": "Analytical",
        "definition": "explicit, sequential, logical, reason-based",
    },
    {
        "register": "f",
        "name": "Affective",
        "definition": "value-laden, feeling-toned",
    },
    {
        "register": "E",
        "name": "Embodied",
        "definition": "sensorimotor, concrete, direct engagement with material or physical substrate",
    },
]


PROMPT_FRAMES_40E = [
    "Definition card: a cognitive state has this noetic dynamic: {noetic_definition} Its operating level is this domain dynamic: {domain_definition}",
    "Audit trace: classify the state where the structural operation is '{noetic_definition}' and the level of processing is '{domain_definition}'",
    "Architecture sample: the mind-idea relation is defined as '{noetic_definition}' while the information lives at the level defined as '{domain_definition}'",
    "Probe row: use the locked definitions only. Noetic dynamic: {noetic_definition} Domain dynamic: {domain_definition}",
    "Classifier input: the state combines the following operator meaning with the following processing level. Operator meaning: {noetic_definition} Processing level: {domain_definition}",
    "Heldout definition prompt: identify the cognitive state from these source definitions: {noetic_definition} Also: {domain_definition}",
    "Definition contrast: ignore topical content and use only this structure. Relation: {noetic_definition} Level: {domain_definition}",
    "CAS source row: the relevant idea relation is '{noetic_definition}' and the relevant processing domain is '{domain_definition}'",
    "State-reading prompt: the operation describes '{noetic_definition}' and the domain describes '{domain_definition}'",
    "No-label probe: structural dynamic equals '{noetic_definition}'. Processing layer equals '{domain_definition}'",
    "Canonical fixture row: operator definition: {noetic_definition} domain definition: {domain_definition}",
    "Definition-locked example: a system is in the state described by '{noetic_definition}' inside the level described by '{domain_definition}'",
]


PROMPT_FRAMES_F28 = [
    "Foundation card: a system shows {drive_definition}. The operational register is {register_definition}.",
    "Audit trace: classify the drive-register state where the motivational dynamic is {drive_definition} and the register is {register_definition}.",
    "Architecture sample: the drive is {drive_definition}; the character of operation is {register_definition}.",
    "Probe row: use the locked drive and register definitions only. Drive dynamic: {drive_definition}. Register dynamic: {register_definition}.",
    "Classifier input: motivational architecture: {drive_definition}. Operational character: {register_definition}.",
    "Heldout definition prompt: identify the foundation from this drive definition and register definition: {drive_definition}; {register_definition}.",
    "Definition contrast: ignore topical content and use only this structure. Drive: {drive_definition}. Register: {register_definition}.",
    "CAS source row: the relevant drive is {drive_definition}; the register is {register_definition}.",
    "Foundation-reading prompt: the drive points toward {drive_definition}. The register is {register_definition}.",
    "No-label probe: motivational pressure equals {drive_definition}. Register expression equals {register_definition}.",
    "Canonical fixture row: drive definition: {drive_definition}. register definition: {register_definition}.",
    "Definition-locked example: a system is organized by {drive_definition} expressed as {register_definition}.",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = _app_root() / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    definitions = build_definitions()
    rows = build_rows()
    manifest = build_manifest(rows)
    readme = build_readme(rows)

    paths = {
        "definitions": output_dir / "canonical_tks_cas_axis_definitions_20260603.json",
        "fixture_json": output_dir / "definition_locked_tks40_f28_fixture_20260603.json",
        "fixture_jsonl": output_dir / "definition_locked_tks40_f28_fixture_20260603.jsonl",
        "manifest": output_dir / "definition_locked_tks40_f28_manifest_20260603.json",
        "readme": output_dir / "README.md",
    }
    write_json(paths["definitions"], definitions)
    write_json(paths["fixture_json"], {"schema_version": SCHEMA_VERSION, "scenarios": rows})
    paths["fixture_jsonl"].write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    write_json(paths["manifest"], manifest)
    paths["readme"].write_text(readme, encoding="utf-8")

    print(f"wrote {output_dir}")
    print(f"rows={len(rows)} 40e={sum(1 for row in rows if row['axis'] == '40e')} f28={sum(1 for row in rows if row['axis'] == 'f28')}")
    print(f"sha256 fixture_json={sha256_file(paths['fixture_json'])}")
    print(f"sha256 manifest={sha256_file(paths['manifest'])}")
    return 0


def build_definitions() -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_canonical_axis_definitions.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "honesty_boundary": (
            "The 10 Noetic definitions are verbatim canonical from CAS_FOUNDATIONAL_CLARIFICATIONS. "
            "Domains/registers/drives are the current CAS v7.5/v7.7 translation layer. "
            "The original TKS 28 Foundations source text is not fully populated in the repository."
        ),
        "sources": [
            {
                "path": "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
                "role": "authoritative 10 Noetic definitions and register axis",
            },
            {
                "path": "noetic-compass-scaffold/noetic-compass/CLAUDE.md",
                "role": "current implementation-facing CAS ontology summary",
            },
            {
                "path": "docs/reference/tks_28_foundations_translation_key.md",
                "role": "CAS v7.5 TKS 28 Foundations translation key",
            },
            {
                "path": "book/manuscript/Chapter_03_The_Four_Processing_Domains.md",
                "role": "domain-definition prose source",
            },
        ],
        "noetics": NOETICS,
        "domains": DOMAINS,
        "drives": DRIVES,
        "registers": REGISTERS,
        "element_count": len(NOETICS) * len(DOMAINS),
        "foundation_count": len(DRIVES) * len(REGISTERS),
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for noetic in NOETICS:
        for domain in DOMAINS:
            element = f"{noetic['operator']}|{domain['domain']}"
            for variant, frame in enumerate(PROMPT_FRAMES_40E):
                split = "train" if variant < 8 else "test"
                row_id = f"definition_locked_40e_{element.replace('^', 'n').replace('|', '_')}_v{variant:02d}"
                rows.append(
                    {
                        "id": row_id,
                        "scenario_id": row_id,
                        "axis": "40e",
                        "split": split,
                        "prompt_variant": variant,
                        "prompt_source": "definition_locked_canonical_axis_definitions",
                        "prompt": frame.format(
                            noetic_definition=noetic["definition"],
                            domain_definition=domain["definition"],
                        ),
                        "expected_cas_axes": {
                            "operator": noetic["operator"],
                            "noetic": noetic["name"],
                            "domain": domain["domain"],
                            "element": element,
                        },
                        "definition_trace": {
                            "noetic": noetic,
                            "domain": domain,
                        },
                    }
                )

    for drive in DRIVES:
        for register in REGISTERS:
            foundation = f"{drive['drive']}|{register['register']}"
            for variant, frame in enumerate(PROMPT_FRAMES_F28):
                split = "train" if variant < 8 else "test"
                row_id = f"definition_locked_f28_{foundation.replace('|', '_')}_v{variant:02d}"
                rows.append(
                    {
                        "id": row_id,
                        "scenario_id": row_id,
                        "axis": "f28",
                        "split": split,
                        "prompt_variant": variant,
                        "prompt_source": "definition_locked_cas_v7_5_tks28_translation_key",
                        "prompt": frame.format(
                            drive_definition=drive["definition"],
                            register_definition=register["definition"],
                        ),
                        "expected_cas_axes": {
                            "drive": drive["drive"],
                            "register": register["register"],
                            "foundation": foundation,
                        },
                        "definition_trace": {
                            "drive": drive,
                            "register": register,
                        },
                    }
                )
    return rows


def build_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_axis = Counter(row["axis"] for row in rows)
    element_counts = Counter(row["expected_cas_axes"].get("element") for row in rows if row["axis"] == "40e")
    foundation_counts = Counter(row["expected_cas_axes"].get("foundation") for row in rows if row["axis"] == "f28")
    split_counts = Counter((row["axis"], row["split"]) for row in rows)
    return {
        "schema_version": "definition_locked_tks40_f28_manifest.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_fixture": "definition_locked_tks40_f28_fixture_20260603.json",
        "honesty_boundary": (
            "This manifest locks the intended CAS labels for a definition-derived fixture. "
            "It is not a comparator verdict and not a claim that TKS 28 original source descriptions are fully populated."
        ),
        "row_count": len(rows),
        "axis_counts": dict(sorted(by_axis.items())),
        "split_counts": {f"{axis}:{split}": count for (axis, split), count in sorted(split_counts.items())},
        "forty_element_counts": dict(sorted(element_counts.items())),
        "foundation_28_counts": dict(sorted(foundation_counts.items())),
        "expected_counts": {
            "forty_elements": 40,
            "foundation_28": 28,
            "variants_per_class": VARIANTS_PER_CLASS,
            "train_variants_per_class": 8,
            "test_variants_per_class": 4,
        },
        "taxonomies": [
            {
                "id": "definition_locked_cas_40e",
                "axis": "40e",
                "role": "cas",
                "class_count": 40,
                "labels": {row["id"]: row["expected_cas_axes"]["element"] for row in rows if row["axis"] == "40e"},
                "description": "Definition-locked CAS 40E labels: 10 Noetics x 4 Domains.",
            },
            {
                "id": "definition_locked_tks_f28",
                "axis": "f28",
                "role": "cas",
                "class_count": 28,
                "labels": {row["id"]: row["expected_cas_axes"]["foundation"] for row in rows if row["axis"] == "f28"},
                "description": "Definition-locked CAS v7.5 Drive x Register labels, position-matched to TKS 28 Foundations.",
            },
        ],
    }


def build_readme(rows: list[dict[str, Any]]) -> str:
    fixture_hash_note = "Run the generator to refresh hashes printed to stdout."
    return f"""# Definition-Locked TKS/CAS MTC Fixture - 2026-06-03

Status: built as an input fixture, not a verdict.

This directory contains the first definition-locked fixture for the next
matched-taxonomy / uniqueness pass. It is intentionally sourced from the locked
CAS/TKS definition documents instead of the Condition-3 topical scenario text.

## Contents

- `canonical_tks_cas_axis_definitions_20260603.json` - source definitions and
  source paths.
- `definition_locked_tks40_f28_fixture_20260603.json` - one JSON document with
  all rows.
- `definition_locked_tks40_f28_fixture_20260603.jsonl` - JSONL view of the same
  rows.
- `definition_locked_tks40_f28_manifest_20260603.json` - label counts and row
  label manifest.

## Counts

```text
rows: {len(rows)}
40E rows: {sum(1 for row in rows if row['axis'] == '40e')}
F28 rows: {sum(1 for row in rows if row['axis'] == 'f28')}
variants per class: {VARIANTS_PER_CLASS}
train/test per class: 8/4
```

## Honesty Boundary

The 10 Noetic definitions are verbatim canonical from
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`.

The 40E state labels are generated as `Noetic x Domain`.

The F28 labels are generated as `Drive x Register`, following the current CAS
v7.5 translation key in `docs/reference/tks_28_foundations_translation_key.md`.
That reference explicitly says the original TKS 28 Foundations source
population remains pending. Therefore this fixture locks the current CAS
Drive/Register translation layer; it does not claim the full original TKS 28
Foundation prose has been recovered.

{fixture_hash_note}
"""


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
