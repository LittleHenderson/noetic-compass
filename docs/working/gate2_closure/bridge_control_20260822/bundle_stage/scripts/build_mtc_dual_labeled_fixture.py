#!/usr/bin/env python3
"""Build dual-labeled Stage MTC pilot fixtures.

============================== DO NOT USE ==============================
QUARANTINED 2026-05-31. This generator's OPERATOR_CUES (below) are
meaning-stripped, domain-flattened Noetic skeletons that ALSO drift from
canonical CAS:
  - ^3 cue "recognizes what would make the situation worse" is analytical
    (Scheme-B drift); canonical ^3 Negative is VISCERAL aversion.
  - ^8 cue "looks for the deeper cause" is the Scheme-B "Causal Reasoning"
    drift; canonical ^8 Above/Cause is associative TRIGGERING.
These fixtures produced the MTC FALSIFY null (40E hidden 5.5% vs 2.5% chance;
F28 at chance; scrambled labels recover as well as real). That null is a
fixture-design artifact of meaning-stripping, NOT evidence against CAS.
SUPERSEDED BY the Condition-2 real-TKS fixture:
  docs/working/mtc_matched_taxonomy_20260530/build_mtc_condition2_meaning_instantiated.py
Do not regenerate or capture from this builder. Kept only as the documented
record of what NOT to do. See docs/working/mtc_matched_taxonomy_20260530/.
=======================================================================

The generated rows are ordinary scenario prompts with two independent label
systems attached before activation capture:

* CAS labels for the target axis (40E or F28)
* coherent non-CAS comparator labels under ``control_semantic``

This does not run a model and does not create a verdict. It creates the fixture
that makes the matched-taxonomy control eligible to run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_mtc_dual_labeled_fixture.v1"

OPERATORS = tuple(f"^{index}" for index in range(10))
DOMAINS = ("P", "C", "E", "O")
DRIVES = tuple(f"F{index}" for index in range(1, 8))
REGISTERS = ("T", "A", "f", "E")

# DO NOT USE — meaning-stripped + anti-drift-violating (^3 analytical, ^8 causal).
# Produced the MTC FALSIFY null. Superseded by the Condition-2 real-TKS fixture.
OPERATOR_CUES = {
    "^0": "the person first notices what kind of thing is in front of them",
    "^1": "the person weighs what the situation is asking for",
    "^2": "the person recognizes what would improve the situation",
    "^3": "the person recognizes what would make the situation worse",
    "^4": "the person senses the tone or signal coming from the situation",
    "^5": "the person notices who is receiving support or care",
    "^6": "the person notices who is sending direction or force",
    "^7": "the person follows a repeating pattern across steps",
    "^8": "the person looks for the deeper cause behind the surface event",
    "^9": "the person focuses on the visible outcome instead of the deeper cause",
}

DOMAIN_CUES = {
    "P": "as a matter of practical reality",
    "C": "as a matter of thought and interpretation",
    "E": "as a matter of feeling and response",
    "O": "as a matter of outward action and consequence",
}

DRIVE_CUES = {
    "F1": "who needs to be included, protected, or kept connected",
    "F2": "what facts, uncertainty, and context are still missing",
    "F3": "where harm, health, safety, or resilience may be at stake",
    "F4": "where trust, empathy, and relationship pressure may matter",
    "F5": "where choice, consent, responsibility, or control may matter",
    "F6": "where rules, boundaries, safeguards, or constraints apply",
    "F7": "what larger goal, meaning, or long-term consequence matters",
}

REGISTER_CUES = {
    "T": "in the stated facts and reasoning",
    "A": "in the person's direct experience",
    "f": "in the emotional pressure around the choice",
    "E": "in the larger value or purpose behind the situation",
}

TOPIC_SETTINGS = {
    "healthcare": ("clinic intake desk", "nurse", "patient update"),
    "education": ("school advising office", "teacher", "student progress note"),
    "commerce_finance": ("small business counter", "bookkeeper", "refund request"),
    "law_governance": ("city permit office", "clerk", "policy exception"),
    "software_data": ("software support queue", "engineer", "bug report"),
    "logistics_operations": ("shipping desk", "dispatcher", "delivery change"),
    "customer_support": ("service help line", "support agent", "customer complaint"),
    "public_safety": ("community safety desk", "coordinator", "incident report"),
    "medical_care": ("clinic intake desk", "nurse", "patient update"),
    "learning_assessment": ("school advising office", "teacher", "student progress note"),
    "market_transaction": ("small business counter", "bookkeeper", "refund request"),
    "law_policy": ("city permit office", "clerk", "policy exception"),
    "technical_system": ("software support queue", "engineer", "bug report"),
    "operations_planning": ("shipping desk", "dispatcher", "delivery change"),
    "human_services": ("benefits office", "case worker", "family support request"),
}

FRAME_CUES = {
    "classification": "sorts the case into the correct working category",
    "causal_explanation": "explains what produced the current problem",
    "procedure": "lays out the next steps in order",
    "tradeoff_decision": "chooses between two imperfect options",
    "risk_mitigation": "reduces the chance of a bad outcome",
    "describe_state": "describes what is happening right now",
    "explain_cause": "explains why the situation reached this point",
    "choose_action": "selects the next action",
    "evaluate_risk": "judges what could go wrong",
}


def _rotated_marker_map(values: list[str], markers: list[str], *, row_index: int, salt: int) -> dict[str, str]:
    if len(values) != len(markers):
        raise ValueError("values and markers must have equal length")
    offset = (row_index * 7 + salt) % len(values)
    return {marker: values[(index + offset) % len(values)] for index, marker in enumerate(markers)}


def _targeted_marker_map(
    values: list[str],
    markers: list[str],
    *,
    target_value: str,
    target_marker_index: int,
) -> dict[str, str]:
    if len(values) != len(markers):
        raise ValueError("values and markers must have equal length")
    if target_value not in values:
        raise ValueError(f"target value {target_value!r} not present")
    offset = (values.index(target_value) - target_marker_index) % len(values)
    return {marker: values[(index + offset) % len(values)] for index, marker in enumerate(markers)}


def _marker_for_value(marker_map: dict[str, str], value: str) -> str:
    for marker, mapped_value in marker_map.items():
        if mapped_value == value:
            return marker
    raise ValueError(f"value {value!r} not present in marker map")


def _render_marker_map(marker_map: dict[str, str], cue_lookup: dict[str, str]) -> str:
    return "; ".join(f"{marker}: {cue_lookup[value]}" for marker, value in marker_map.items())


def _topic_cue(topic: str) -> str:
    setting, actor, artifact = TOPIC_SETTINGS[topic]
    return f"{setting} with a {actor} reviewing a {artifact}"


@dataclass(frozen=True)
class AxisSpec:
    axis: str
    source_axis: str
    cas_labels: list[str]
    control_id: str
    control_labels: list[str]
    rows_per_class: int
    train_per_class: int


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _control(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    controls = manifest.get("controls", {})
    if key not in controls:
        raise SystemExit(f"manifest missing control {key}")
    return controls[key]


def _axis_spec(
    *,
    axis: str,
    manifest: dict[str, Any],
    rows_per_class: int,
    train_per_class: int,
) -> AxisSpec:
    if axis == "40e":
        cas_labels = [f"{operator}|{domain}" for operator in OPERATORS for domain in DOMAINS]
        control = _control(manifest, "nc40_topic_frame")
        return AxisSpec(
            axis="40e",
            source_axis="stage9_40e",
            cas_labels=cas_labels,
            control_id=control["control_id"],
            control_labels=[str(label) for label in control["labels"]],
            rows_per_class=rows_per_class,
            train_per_class=train_per_class,
        )
    if axis == "f28":
        cas_labels = [f"{drive}|{register}" for drive in DRIVES for register in REGISTERS]
        control = _control(manifest, "nc28_topic_function_nested")
        return AxisSpec(
            axis="f28",
            source_axis="stage7_f28",
            cas_labels=cas_labels,
            control_id=control["control_id"],
            control_labels=[str(label) for label in control["labels"]],
            rows_per_class=rows_per_class,
            train_per_class=train_per_class,
        )
    raise SystemExit(f"unsupported axis: {axis}")


def _parse_control_label(label: str) -> tuple[str, str]:
    parts = label.split("_")
    if label.startswith("NC40_"):
        # NC40_{topic}_{frame}; both topic and frame can contain underscores.
        frame_options = (
            "classification",
            "causal_explanation",
            "procedure",
            "tradeoff_decision",
            "risk_mitigation",
        )
        body = label.removeprefix("NC40_")
        for frame in frame_options:
            suffix = f"_{frame}"
            if body.endswith(suffix):
                return body[: -len(suffix)], frame
    if label.startswith("NC28_"):
        function_options = ("describe_state", "explain_cause", "choose_action", "evaluate_risk")
        body = label.removeprefix("NC28_")
        for function in function_options:
            suffix = f"_{function}"
            if body.endswith(suffix):
                return body[: -len(suffix)], function
    raise ValueError(f"cannot parse control label: {label}")


def _split_for_rep(rep: int, spec: AxisSpec) -> str:
    return "train" if rep < spec.train_per_class else "test"


def _prompt_40e(operator: str, domain: str, control_label: str, rep: int, row_index: int) -> str:
    topic, frame = _parse_control_label(control_label)
    operator_map = _targeted_marker_map(
        list(OPERATORS),
        [f"N{i}" for i in range(10)],
        target_value=operator,
        target_marker_index=rep % 10,
    )
    domain_map = _targeted_marker_map(
        list(DOMAINS),
        [f"D{i}" for i in range(4)],
        target_value=domain,
        target_marker_index=rep % 4,
    )
    topic_values = list(TOPIC_SETTINGS.keys())[:8]
    topic_map = _targeted_marker_map(
        topic_values,
        [f"T{i}" for i in range(8)],
        target_value=topic,
        target_marker_index=rep % 8,
    )
    frame_values = [
        "classification",
        "causal_explanation",
        "procedure",
        "tradeoff_decision",
        "risk_mitigation",
    ]
    frame_map = _targeted_marker_map(
        frame_values,
        [f"R{i}" for i in range(5)],
        target_value=frame,
        target_marker_index=rep % 5,
    )
    return (
        "A reviewer receives a case card with several possible readings. "
        f"Reasoning notes: {_render_marker_map(operator_map, OPERATOR_CUES)}. "
        f"Lenses: {_render_marker_map(domain_map, DOMAIN_CUES)}. "
        f"Settings: {_render_marker_map(topic_map, {value: _topic_cue(value) for value in topic_values})}. "
        f"Tasks: {_render_marker_map(frame_map, FRAME_CUES)}. "
        f"For this row, use reasoning note {_marker_for_value(operator_map, operator)}, "
        f"lens {_marker_for_value(domain_map, domain)}, "
        f"setting {_marker_for_value(topic_map, topic)}, "
        f"and task {_marker_for_value(frame_map, frame)}. "
        f"Write the short review note for pass {rep + 1}."
    )


def _prompt_f28(drive: str, register: str, control_label: str, rep: int, row_index: int) -> str:
    topic, function = _parse_control_label(control_label)
    drive_map = _targeted_marker_map(
        list(DRIVES),
        [f"F{i}" for i in range(7)],
        target_value=drive,
        target_marker_index=rep % 7,
    )
    register_map = _targeted_marker_map(
        list(REGISTERS),
        [f"G{i}" for i in range(4)],
        target_value=register,
        target_marker_index=rep % 4,
    )
    topic_values = [
        "medical_care",
        "learning_assessment",
        "market_transaction",
        "law_policy",
        "technical_system",
        "operations_planning",
        "human_services",
    ]
    topic_map = _targeted_marker_map(
        topic_values,
        [f"T{i}" for i in range(7)],
        target_value=topic,
        target_marker_index=rep % 7,
    )
    function_values = ("describe_state", "explain_cause", "choose_action", "evaluate_risk")
    function_map = _targeted_marker_map(
        list(function_values),
        [f"R{i}" for i in range(4)],
        target_value=function,
        target_marker_index=rep % 4,
    )
    return (
        "A reviewer receives a case card with several possible readings. "
        f"Concerns: {_render_marker_map(drive_map, DRIVE_CUES)}. "
        f"Lenses: {_render_marker_map(register_map, REGISTER_CUES)}. "
        f"Settings: {_render_marker_map(topic_map, {value: _topic_cue(value) for value in topic_values})}. "
        f"Tasks: {_render_marker_map(function_map, FRAME_CUES)}. "
        f"For this row, use concern {_marker_for_value(drive_map, drive)}, "
        f"lens {_marker_for_value(register_map, register)}, "
        f"setting {_marker_for_value(topic_map, topic)}, "
        f"and task {_marker_for_value(function_map, function)}. "
        f"Write the short review note for pass {rep + 1}."
    )


def _build_row(
    *,
    spec: AxisSpec,
    cas_label: str,
    control_label: str,
    rep: int,
    row_index: int,
) -> dict[str, Any]:
    split = _split_for_rep(rep, spec)
    parent, child = _parse_control_label(control_label)

    if spec.axis == "40e":
        operator, domain = cas_label.split("|", 1)
        prompt = _prompt_40e(operator, domain, control_label, rep, row_index)
        return {
            "id": f"mtc40_{split}_{row_index:05d}",
            "sample_id": f"mtc40_{split}_{row_index:05d}",
            "split": split,
            "prompt": prompt,
            "labels_operator": operator,
            "labels_domain": domain,
            "labels_40e": cas_label,
            "expected_cas_axes": {
                "operator": operator,
                "domain": domain,
                "element": cas_label,
            },
            "control_semantic": {
                "topic_40": parent,
                "frame_40": child,
            },
            "metadata": {
                "fixture_family": "mtc_dual_labeled_v1",
                "axis": "40e",
                "authoring_rule": "concrete ordinary scenario; dual labels assigned before capture",
            },
        }

    drive, register = cas_label.split("|", 1)
    prompt = _prompt_f28(drive, register, control_label, rep, row_index)
    return {
        "id": f"mtcf28_{split}_{row_index:05d}",
        "sample_id": f"mtcf28_{split}_{row_index:05d}",
        "split": split,
        "prompt": prompt,
        "drive": drive,
        "register": register,
        "labels_f28": cas_label,
        "expected_cas_axes": {
            "drive": drive,
            "register": register,
            "foundation": cas_label,
        },
        "control_semantic": {
            "topic_7": parent,
            "function_4": child,
        },
        "metadata": {
            "fixture_family": "mtc_dual_labeled_v1",
            "axis": "f28",
            "authoring_rule": "concrete ordinary scenario; dual labels assigned before capture",
        },
    }


def build_fixture(spec: AxisSpec) -> dict[str, Any]:
    if len(spec.cas_labels) != len(spec.control_labels):
        raise SystemExit(
            f"{spec.axis} requires equal CAS/control cardinality; "
            f"got {len(spec.cas_labels)} and {len(spec.control_labels)}"
        )
    if not (0 < spec.train_per_class < spec.rows_per_class):
        raise SystemExit("--train-per-class must be between 1 and rows-per-class - 1")

    rows: list[dict[str, Any]] = []
    for rep in range(spec.rows_per_class):
        for cas_index, cas_label in enumerate(spec.cas_labels):
            control_index = (cas_index + rep) % len(spec.control_labels)
            rows.append(
                _build_row(
                    spec=spec,
                    cas_label=cas_label,
                    control_label=spec.control_labels[control_index],
                    rep=rep,
                    row_index=len(rows),
                )
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "fixture_ready_for_materializer",
        "axis": spec.axis,
        "source_axis": spec.source_axis,
        "control_id": spec.control_id,
        "rows_per_cas_class": spec.rows_per_class,
        "train_per_cas_class": spec.train_per_class,
        "test_per_cas_class": spec.rows_per_class - spec.train_per_class,
        "row_count": len(rows),
        "important_limit": (
            "Fixture only. This is not an activation capture, probe result, "
            "matched-taxonomy verdict, or Evidence Packet."
        ),
        "records": rows,
    }
    payload["content_sha256"] = _sha256_json(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--axis", required=True, choices=("40e", "f28"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows-per-class", type=int, default=25)
    parser.add_argument("--train-per-class", type=int, default=20)
    args = parser.parse_args()

    manifest = _load_json(args.manifest)
    spec = _axis_spec(
        axis=args.axis,
        manifest=manifest,
        rows_per_class=args.rows_per_class,
        train_per_class=args.train_per_class,
    )
    payload = build_fixture(spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote MTC dual-labeled fixture: {args.output}")
    print(f"rows: {payload['row_count']}")
    print(f"sha256: {payload['content_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
