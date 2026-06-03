#!/usr/bin/env python3
"""Build a definition-locked TKS/CAS probe fixture.

This fixture is deliberately different from the Condition-3 topical fixture:
its prompts are generated from the owner-provided TKS 40 Element and 28
Foundation definitions rather than from topical business scenarios. It is an
input artifact, not a verdict.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_definition_locked_tks_fixture.v2"
DEFINITIONS_SCHEMA_VERSION = "tks_owner_provided_axis_definitions.v1"
MANIFEST_SCHEMA_VERSION = "definition_locked_tks40_f28_manifest.v2"
CREATED_AT = "2026-06-03T00:00:00+00:00"
DEFAULT_OUTPUT_DIR = Path("docs/working/definition_locked_tks_mtc_20260603")
SOURCE_DEFINITIONS_PATH = Path("docs/reference/tks_owner_locked_definitions_20260603.json")
VARIANTS_PER_CLASS = 12


NOETIC_BY_NUMBER = {
    1: {"operator": "^1", "name": "Mind"},
    2: {"operator": "^2", "name": "Positive"},
    3: {"operator": "^3", "name": "Negative"},
    4: {"operator": "^4", "name": "Vibration"},
    5: {"operator": "^5", "name": "Female"},
    6: {"operator": "^6", "name": "Male"},
    7: {"operator": "^7", "name": "Rhythm"},
    8: {"operator": "^8", "name": "Above/Cause"},
    9: {"operator": "^9", "name": "Below/Effect"},
    10: {"operator": "^0", "name": "Idea"},
}


DOMAIN_BY_LETTER = {
    "A": "Spiritual",
    "B": "Mental",
    "C": "Emotional",
    "D": "Physical",
}


FOUNDATION_DRIVES = {
    "1": "desire to be and be with God",
    "2": "wisdom, insight, and knowledge",
    "3": "life, vitality, and health",
    "4": "companionship, love, and friendship",
    "5": "worldly power, influence, and control",
    "6": "material food and things",
    "7": "lust, sex, and reproduction",
}


FOUNDATION_REGISTERS = {
    "a": "Spiritual",
    "b": "Mental",
    "c": "Emotional",
    "d": "Physical",
}


PROMPT_FRAMES_40E = [
    "TKS Element definition card: {title}. Source definition: {definition}",
    "Audit trace: identify the TKS 40 Element whose definition says: {definition}",
    "Architecture sample: the element is defined as '{definition}'",
    "Probe row: use the locked TKS 40 Element source text only. {title}: {definition}",
    "Classifier input: TKS 40 Element title '{title}' with source meaning: {definition}",
    "Heldout definition prompt: recover the element from this definition: {definition}",
    "Definition contrast: ignore topical content and use only the TKS element structure: {definition}",
    "TKS source row: the relevant element is described this way: {definition}",
    "State-reading prompt: this source passage defines {title}: {definition}",
    "No-label probe: source definition text: {definition}",
    "Canonical fixture row: element definition: {definition}",
    "Definition-locked example: a system is in the TKS element state described by '{definition}'",
]


PROMPT_FRAMES_F28 = [
    "TKS Foundation definition card: {title}. Source definition: {definition}",
    "Audit trace: identify the TKS 28 Foundation whose definition says: {definition}",
    "Architecture sample: the foundation is defined as '{definition}'",
    "Probe row: use the locked TKS 28 Foundation source text only. {title}: {definition}",
    "Classifier input: TKS 28 Foundation title '{title}' with source meaning: {definition}",
    "Heldout definition prompt: recover the foundation from this definition: {definition}",
    "Definition contrast: ignore topical content and use only the TKS foundation structure: {definition}",
    "TKS source row: the relevant foundation is described this way: {definition}",
    "Foundation-reading prompt: this source passage defines {title}: {definition}",
    "No-label probe: source definition text: {definition}",
    "Canonical fixture row: foundation definition: {definition}",
    "Definition-locked example: a system is in the TKS foundation state described by '{definition}'",
]


def _app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--source-definitions",
        type=Path,
        default=SOURCE_DEFINITIONS_PATH,
        help="Locked owner-provided TKS definitions JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = _app_root() / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    source = load_definition_source(args.source_definitions)
    definitions = build_definitions(source)
    rows = build_rows(source)
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
    print(
        f"rows={len(rows)} 40e={sum(1 for row in rows if row['axis'] == '40e')} "
        f"f28={sum(1 for row in rows if row['axis'] == 'f28')}"
    )
    print(f"sha256 fixture_json={sha256_file(paths['fixture_json'])}")
    print(f"sha256 manifest={sha256_file(paths['manifest'])}")
    return 0


def load_definition_source(path: Path = SOURCE_DEFINITIONS_PATH) -> dict[str, Any]:
    source_path = path if path.is_absolute() else _repo_root() / path
    source = json.loads(source_path.read_text(encoding="utf-8"))
    validate_definition_source(source, source_path)
    return source


def validate_definition_source(source: dict[str, Any], source_path: Path) -> None:
    if source.get("schema_version") != DEFINITIONS_SCHEMA_VERSION:
        raise ValueError(f"{source_path} has unexpected schema_version: {source.get('schema_version')}")
    elements = source.get("tks_40_elements")
    foundations = source.get("tks_28_foundations")
    if not isinstance(elements, list) or not isinstance(foundations, list):
        raise ValueError(f"{source_path} must contain tks_40_elements and tks_28_foundations lists")
    element_codes = [item.get("code") for item in elements]
    foundation_codes = [item.get("code") for item in foundations]
    expected_elements = [f"{letter}{number}" for letter in "ABCD" for number in range(1, 11)]
    expected_foundations = [f"{number}{letter}" for letter in "abcd" for number in range(1, 8)]
    if element_codes != expected_elements:
        raise ValueError(f"{source_path} TKS 40 Element codes are not canonical A1-D10 order")
    if foundation_codes != expected_foundations:
        raise ValueError(f"{source_path} TKS 28 Foundation codes are not canonical 1a-7d order")
    for collection_name, collection in (("tks_40_elements", elements), ("tks_28_foundations", foundations)):
        for item in collection:
            if not item.get("title") or not item.get("definition"):
                raise ValueError(f"{source_path} {collection_name} item {item.get('code')} lacks title/definition")


def build_definitions(source: dict[str, Any]) -> dict[str, Any]:
    return dict(source)


def build_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for element in source["tks_40_elements"]:
        letter, number = split_element_code(element["code"])
        noetic = NOETIC_BY_NUMBER[number]
        domain_name = DOMAIN_BY_LETTER[letter]
        for variant, frame in enumerate(PROMPT_FRAMES_40E):
            split = "train" if variant < 8 else "test"
            row_id = f"definition_locked_40e_{element['code'].lower()}_v{variant:02d}"
            rows.append(
                {
                    "id": row_id,
                    "scenario_id": row_id,
                    "axis": "40e",
                    "split": split,
                    "prompt_variant": variant,
                    "prompt_source": "definition_locked_owner_provided_tks_40_elements",
                    "prompt": frame.format(title=element["title"], definition=element["definition"]),
                    "expected_cas_axes": {
                        "operator": noetic["operator"],
                        "noetic": noetic["name"],
                        "domain": letter,
                        "domain_name": domain_name,
                        "element": element["code"],
                        "element_title": element["title"],
                    },
                    "definition_trace": {
                        "source": "owner_provided_tks_40_elements_2026_06_03",
                        "element": element,
                        "mapped_noetic": noetic,
                        "mapped_domain": {"code": letter, "name": domain_name},
                    },
                }
            )

    for foundation in source["tks_28_foundations"]:
        number, letter = split_foundation_code(foundation["code"])
        for variant, frame in enumerate(PROMPT_FRAMES_F28):
            split = "train" if variant < 8 else "test"
            row_id = f"definition_locked_f28_{foundation['code'].lower()}_v{variant:02d}"
            rows.append(
                {
                    "id": row_id,
                    "scenario_id": row_id,
                    "axis": "f28",
                    "split": split,
                    "prompt_variant": variant,
                    "prompt_source": "definition_locked_owner_provided_tks_28_foundations",
                    "prompt": frame.format(title=foundation["title"], definition=foundation["definition"]),
                    "expected_cas_axes": {
                        "drive": number,
                        "drive_name": FOUNDATION_DRIVES[number],
                        "register": letter,
                        "register_name": FOUNDATION_REGISTERS[letter],
                        "foundation": foundation["code"],
                        "foundation_title": foundation["title"],
                    },
                    "definition_trace": {
                        "source": "owner_provided_tks_28_foundations_2026_06_03",
                        "foundation": foundation,
                        "mapped_drive": {"code": number, "name": FOUNDATION_DRIVES[number]},
                        "mapped_register": {"code": letter, "name": FOUNDATION_REGISTERS[letter]},
                    },
                }
            )
    return rows


def split_element_code(code: str) -> tuple[str, int]:
    letter = code[0]
    number = int(code[1:])
    if letter not in DOMAIN_BY_LETTER:
        raise ValueError(f"unknown TKS 40 Element domain code: {code}")
    if number not in NOETIC_BY_NUMBER:
        raise ValueError(f"unknown TKS 40 Element noetic number: {code}")
    return letter, number


def split_foundation_code(code: str) -> tuple[str, str]:
    number = code[0]
    letter = code[1]
    if number not in FOUNDATION_DRIVES:
        raise ValueError(f"unknown TKS 28 Foundation drive code: {code}")
    if letter not in FOUNDATION_REGISTERS:
        raise ValueError(f"unknown TKS 28 Foundation register code: {code}")
    return number, letter


def build_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_axis = Counter(row["axis"] for row in rows)
    element_counts = Counter(row["expected_cas_axes"].get("element") for row in rows if row["axis"] == "40e")
    foundation_counts = Counter(row["expected_cas_axes"].get("foundation") for row in rows if row["axis"] == "f28")
    split_counts = Counter((row["axis"], row["split"]) for row in rows)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at": CREATED_AT,
        "source_fixture": "definition_locked_tks40_f28_fixture_20260603.json",
        "honesty_boundary": (
            "This manifest locks owner-provided TKS source labels for a definition-derived fixture. "
            "It is not a model run, not a comparator verdict, and not evidence that CAS Harness has passed uniqueness."
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
                "id": "definition_locked_tks_40e",
                "axis": "40e",
                "role": "tks",
                "class_count": 40,
                "labels": {row["id"]: row["expected_cas_axes"]["element"] for row in rows if row["axis"] == "40e"},
                "description": "Definition-locked TKS 40 Elements: A1-D10 owner-provided source definitions.",
            },
            {
                "id": "definition_locked_tks_f28",
                "axis": "f28",
                "role": "tks",
                "class_count": 28,
                "labels": {row["id"]: row["expected_cas_axes"]["foundation"] for row in rows if row["axis"] == "f28"},
                "description": "Definition-locked TKS 28 Foundations: 1a-7d owner-provided source definitions.",
            },
        ],
    }


def build_readme(rows: list[dict[str, Any]]) -> str:
    return f"""# Definition-Locked TKS/CAS MTC Fixture - 2026-06-03

Status: built as an input fixture, not a verdict.

This directory contains the definition-locked fixture for the next
matched-taxonomy / uniqueness pass. It is sourced from the owner-provided TKS
40 Element and TKS 28 Foundation definitions supplied on 2026-06-03.

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

This is an input fixture. It is not a model capture, not a comparator result,
and not a CAS Harness `ACCEPT`.

The 40E rows are generated from explicit TKS Element definitions `A1` through
`D10`.

The F28 rows are generated from explicit TKS Foundation definitions `1a`
through `7d`.

The source text intentionally contains the TKS titles in many definitions. This
fixture therefore tests definition grounding and axis recovery from source
definitions; by itself it is not a blind semantic generalization proof.
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
