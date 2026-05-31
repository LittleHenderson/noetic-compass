#!/usr/bin/env python3
"""Build concrete MTC v2 pilot fixtures for 40E and F28.

============================== DO NOT USE ==============================
QUARANTINED 2026-05-31. Like the marker-balanced generator, this v2 concrete
generator strips the real TKS Element/Foundation meaning out of the prompts in
the name of leakage control, and produced a fixture null (no above-chance CAS
recovery). The over-correction removes exactly the recognizable TKS semantic
territory that drove the 95.625% lineage, so the model has no reason to
internally represent the CAS distinction. That is a fixture-design artifact,
NOT evidence against CAS.
SUPERSEDED BY the Condition-2 real-TKS fixture:
  docs/working/mtc_matched_taxonomy_20260530/build_mtc_condition2_meaning_instantiated.py
which keeps the real TKS meaning while killing the copy-the-gloss shortcut
(text leakage 50% -> 6.9%). Do not regenerate or capture from this builder.
=======================================================================

This generator is intentionally separate from the marker-balanced generator.
It emits natural scenario prose with CAS labels attached out-of-band, so the
prompt text does not expose class badges, cue-card maps, or source vocabulary
anchor nouns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_mtc_v2_concrete_fixture.v1"
DEFAULT_SEED = 2026053202
DEFAULT_ROWS_PER_CLASS = 6
DEFAULT_TRAIN_PER_CLASS = 4

OPERATORS = tuple(f"^{index}" for index in range(10))
DOMAINS = ("P", "C", "E", "O")
DRIVES = tuple(f"F{index}" for index in range(1, 8))
REGISTERS = ("T", "A", "f", "E")

BANNED_PROMPT_ANCHOR_TERMS = (
    "identity",
    "need",
    "good",
    "bad",
    "signal",
    "receiver",
    "transmitter",
    "pattern",
    "source",
    "manifest",
    "operator",
    "domain",
    "drive",
    "register",
    "foundation",
    "noetic",
    "idea",
    "mind",
    "positive",
    "negative",
    "vibration",
    "female",
    "male",
    "rhythm",
    "above",
    "below",
    "cause",
    "effect",
    "unity",
    "wisdom",
    "vitality",
    "connection",
    "agency",
    "structure",
    "purpose",
    "analytical",
    "affective",
    "transcendent",
    "embodied",
)

VISIBLE_BADGE_FRAGMENTS = (
    "reasoning notes:",
    "lenses:",
    "concerns:",
    "settings:",
    "tasks:",
    "for this row",
    "case card",
)

TOPIC_SETTINGS_40 = {
    "healthcare": ("clinic intake desk", "nurse", "patient message about a delayed refill"),
    "education": ("school advising office", "teacher", "student progress note after a missed exam"),
    "commerce_finance": ("neighborhood shop counter", "bookkeeper", "refund request for a damaged order"),
    "law_governance": ("city permit office", "clerk", "resident request for a late filing"),
    "software_data": ("software support queue", "engineer", "bug report from a payroll team"),
    "logistics_operations": ("shipping desk", "dispatcher", "delivery change after a truck delay"),
    "customer_support": ("service help line", "support agent", "complaint about a closed account"),
    "public_safety": ("community safety desk", "coordinator", "incident report after a blocked exit"),
}

TOPIC_SETTINGS_F28 = {
    "medical_care": ("clinic intake desk", "nurse", "patient message about a new symptom"),
    "learning_assessment": ("school advising office", "teacher", "student progress note after tutoring"),
    "market_transaction": ("neighborhood shop counter", "bookkeeper", "invoice dispute with a vendor"),
    "law_policy": ("city permit office", "clerk", "resident request about a local rule"),
    "technical_system": ("software support queue", "engineer", "bug report from a payroll team"),
    "operations_planning": ("shipping desk", "dispatcher", "delivery change after a route closure"),
    "human_services": ("benefits office", "case worker", "family request after a missed appointment"),
}

FRAME_REQUESTS = {
    "classification": (
        "sort the request into the most useful working category",
        "state what kind of issue the reviewer should handle first",
    ),
    "causal_explanation": (
        "explain how the delay likely happened",
        "connect the reported facts to the likely reason for the trouble",
    ),
    "procedure": (
        "lay out the next three steps in order",
        "turn the messy request into a clean workflow",
    ),
    "tradeoff_decision": (
        "choose between two imperfect next steps",
        "recommend the option that best fits the constraints",
    ),
    "risk_mitigation": (
        "reduce the chance that the situation worsens",
        "name the safeguard the reviewer should use before replying",
    ),
    "describe_state": (
        "describe what is happening right now",
        "summarize the current status without adding speculation",
    ),
    "explain_cause": (
        "explain why the situation reached this point",
        "connect the facts to the likely reason for the trouble",
    ),
    "choose_action": (
        "select the next practical action",
        "recommend the next step for the staff member",
    ),
    "evaluate_risk": (
        "judge what could go wrong if the team waits",
        "name the concern that should be checked before anyone proceeds",
    ),
}

TOPIC_DETAILS_40 = {
    "healthcare": (
        "the refill was approved yesterday, but the pickup time still shows next week",
        "the appointment reminder lists the wrong room while the chart lists the right clinician",
        "the lab form arrived late, and the patient is waiting near the front desk",
    ),
    "education": (
        "the makeup exam has an open slot, but the family calendar has a conflict",
        "the tutoring note lists progress, while the gradebook still shows the older score",
        "the class roster was updated after the parent call, and the teacher has not replied",
    ),
    "commerce_finance": (
        "the package photo shows a torn corner, but the receipt lists a final-sale item",
        "the refund log shows two partial credits, while the customer expected one full credit",
        "the vendor invoice has a late fee, and the purchase order was approved on time",
    ),
    "law_governance": (
        "the form arrived after the portal closed, but the filing fee was paid on time",
        "the resident brought a stamped copy, while the desk record still marks the file pending",
        "the permit packet is missing one page, and the hearing starts after lunch",
    ),
    "software_data": (
        "the payroll export skipped two names, but the nightly job marked the run complete",
        "the bug ticket has a screenshot, while the server log shows a different timestamp",
        "the dashboard count changed after a deploy, and the support queue is filling",
    ),
    "logistics_operations": (
        "the truck reached the depot late, but the customer time slot opens at noon",
        "the loading bay has one broken scanner, while the route sheet has already printed",
        "the driver swapped trailers after a delay, and the warehouse crew is waiting",
    ),
    "customer_support": (
        "the account closed after a failed address check, but the customer is waiting on a payout",
        "the chat transcript shows a promised callback, while the ticket has no owner",
        "the refund email bounced twice, and the customer has called again",
    ),
    "public_safety": (
        "the exit was blocked during setup, but the room opens for an evening meeting",
        "the inspection photo shows a loose handrail, while the event crew is setting chairs",
        "the incident note lists a crowding problem, and the coordinator has ten minutes",
    ),
}

TOPIC_DETAILS_F28 = {
    "medical_care": (
        "the patient mentions a new symptom, but the triage slot is almost over",
        "the prescription label differs from the visit summary, while the nurse is preparing a call",
        "the clinic message lists a fever reading, and the family is waiting for instructions",
    ),
    "learning_assessment": (
        "the quiz score improved, but the assignment portal still marks the work late",
        "the tutoring sheet lists two mastered skills, while the parent email asks about the old grade",
        "the teacher has a new writing sample, and the student is waiting after class",
    ),
    "market_transaction": (
        "the invoice total changed, but the shipment receipt still shows the original amount",
        "the vendor sent a replacement order, while the payment record still has the disputed charge",
        "the customer returned one item, and the sales receipt lists two discounts",
    ),
    "law_policy": (
        "the local rule changed last month, but the posted checklist still has old wording",
        "the resident has a dated notice, while the clerk sees a newer filing deadline",
        "the permit question came in before closing, and the counter line is short",
    ),
    "technical_system": (
        "the server job finished, but the dashboard still shows yesterday's count",
        "the bug report includes a fresh screenshot, while the log window has rolled forward",
        "the data import skipped one column, and the release manager is waiting",
    ),
    "operations_planning": (
        "the route closure starts at noon, but the delivery board still lists the old path",
        "the warehouse scanner is down, while the packing crew has already staged the boxes",
        "the dispatch sheet changed after a driver call, and the dock team is waiting",
    ),
    "human_services": (
        "the family missed an appointment, but the case worker has a same-day opening",
        "the benefits letter lists a deadline, while the household report has a new address",
        "the service desk has a voicemail transcript, and the client is waiting in the lobby",
    ),
}

PROMPT_OPENERS = (
    "At the {place}, a {actor} is reviewing a {artifact}.",
    "Inside the {place}, a {actor} is checking a {artifact}.",
    "During a shift at the {place}, a {actor} opens a {artifact}.",
)

DETAIL_OPENERS = (
    "The note says {detail}.",
    "The file shows {detail}.",
    "The latest entry says {detail}.",
)

HANDOFF_CONSTRAINTS = (
    "The reviewer has one minute before the next handoff.",
    "The reviewer has to reply before the afternoon queue review.",
    "The reviewer is preparing a brief note before another staff member takes over.",
)

TASK_CLOSERS = (
    "Write a short staff note that can {task_request}.",
    "Draft a brief staff note that can {task_request}.",
    "Write the handoff note so it can {task_request}.",
)

DISTRACTOR_PACKS = (
    {
        "pack_id": "orchard_lighthouse_ledger",
        "terms": ("orchard", "lighthouse", "ledger", "festival"),
    },
    {
        "pack_id": "canyon_library_ribbon",
        "terms": ("canyon", "library", "ribbon", "cabinet"),
    },
    {
        "pack_id": "harbor_museum_candle",
        "terms": ("harbor", "museum", "candle", "blanket"),
    },
    {
        "pack_id": "meadow_theater_compass",
        "terms": ("meadow", "theater", "compass", "window"),
    },
)


@dataclass(frozen=True)
class AxisSpec:
    axis: str
    source_axis: str
    cas_labels: list[str]
    control_id: str
    control_labels: list[str]
    rows_per_class: int
    train_per_class: int
    seed: int


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
    rows_per_class: int = DEFAULT_ROWS_PER_CLASS,
    train_per_class: int = DEFAULT_TRAIN_PER_CLASS,
    seed: int = DEFAULT_SEED,
) -> AxisSpec:
    if axis == "40e":
        control = _control(manifest, "nc40_topic_frame")
        return AxisSpec(
            axis="40e",
            source_axis="stage9_40e",
            cas_labels=[f"{operator}|{domain}" for operator in OPERATORS for domain in DOMAINS],
            control_id=str(control["control_id"]),
            control_labels=[str(label) for label in control["labels"]],
            rows_per_class=rows_per_class,
            train_per_class=train_per_class,
            seed=seed,
        )
    if axis == "f28":
        control = _control(manifest, "nc28_topic_function_nested")
        return AxisSpec(
            axis="f28",
            source_axis="stage7_f28",
            cas_labels=[f"{drive}|{register}" for drive in DRIVES for register in REGISTERS],
            control_id=str(control["control_id"]),
            control_labels=[str(label) for label in control["labels"]],
            rows_per_class=rows_per_class,
            train_per_class=train_per_class,
            seed=seed,
        )
    raise SystemExit(f"unsupported axis: {axis}")


def _parse_control_label(label: str) -> tuple[str, str]:
    if label.startswith("NC40_"):
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


def _pick(options: tuple[str, ...], *, seed: int, row_index: int, salt: str) -> str:
    digest = hashlib.sha256(f"{seed}:{row_index}:{salt}".encode("utf-8")).digest()
    return options[int.from_bytes(digest[:4], "big") % len(options)]


def _surface_pair(axis: str, *, seed: int, row_index: int) -> tuple[str, str]:
    """Pick visible prompt topic/task independently of the matched-control label.

    The matched-control label remains in metadata for the runner, but the prompt
    cannot expose that label as a reusable text key. This keeps the local text
    gate from confusing "control label is visible" with a real semantic readout.
    """
    rng = random.Random(f"{seed}:{axis}:surface:{row_index}")
    if axis == "40e":
        return (
            rng.choice(tuple(TOPIC_SETTINGS_40)),
            rng.choice(
                (
                    "classification",
                    "causal_explanation",
                    "procedure",
                    "tradeoff_decision",
                    "risk_mitigation",
                )
            ),
        )
    if axis == "f28":
        return (
            rng.choice(tuple(TOPIC_SETTINGS_F28)),
            rng.choice(("describe_state", "explain_cause", "choose_action", "evaluate_risk")),
        )
    raise ValueError(f"unsupported axis: {axis}")


def _prompt_40e(
    *,
    topic: str,
    frame: str,
    row_index: int,
    seed: int,
) -> str:
    place, actor, artifact = TOPIC_SETTINGS_40[topic]
    opener = _pick(PROMPT_OPENERS, seed=seed, row_index=row_index, salt="opener")
    detail_opener = _pick(DETAIL_OPENERS, seed=seed, row_index=row_index, salt="detail_opener")
    detail = _pick(TOPIC_DETAILS_40[topic], seed=seed, row_index=row_index, salt="topic_detail")
    constraint = _pick(HANDOFF_CONSTRAINTS, seed=seed, row_index=row_index, salt="constraint")
    frame_request = _pick(FRAME_REQUESTS[frame], seed=seed, row_index=row_index, salt="frame")
    closer = _pick(TASK_CLOSERS, seed=seed, row_index=row_index, salt="closer")
    return (
        f"{opener.format(place=place, actor=actor, artifact=artifact)} "
        f"{detail_opener.format(detail=detail)} "
        f"{constraint} "
        f"{closer.format(task_request=frame_request)}"
    )


def _prompt_f28(
    *,
    topic: str,
    function: str,
    row_index: int,
    seed: int,
) -> str:
    place, actor, artifact = TOPIC_SETTINGS_F28[topic]
    opener = _pick(PROMPT_OPENERS, seed=seed, row_index=row_index, salt="opener")
    detail_opener = _pick(DETAIL_OPENERS, seed=seed, row_index=row_index, salt="detail_opener")
    detail = _pick(TOPIC_DETAILS_F28[topic], seed=seed, row_index=row_index, salt="topic_detail")
    constraint = _pick(HANDOFF_CONSTRAINTS, seed=seed, row_index=row_index, salt="constraint")
    function_request = _pick(FRAME_REQUESTS[function], seed=seed, row_index=row_index, salt="function")
    closer = _pick(TASK_CLOSERS, seed=seed, row_index=row_index, salt="closer")
    return (
        f"{opener.format(place=place, actor=actor, artifact=artifact)} "
        f"{detail_opener.format(detail=detail)} "
        f"{constraint} "
        f"{closer.format(task_request=function_request)}"
    )


def _lexical_metadata(row_index: int, *, seed: int, topic: str, task: str) -> dict[str, Any]:
    pack = DISTRACTOR_PACKS[(row_index + seed) % len(DISTRACTOR_PACKS)]
    return {
        "lexical_pack_id": pack["pack_id"],
        "lexical_distractors": list(pack["terms"]),
        "lexical_distractor_rule": "stored as metadata only; prompt prose stays natural",
        "domain_slug": topic,
        "task_slug": task,
        "paraphrase_family": f"concrete_v2_{row_index % 5}",
        "surface_style": "ordinary_staff_note",
        "question_type": "short_response",
    }


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
    surface_parent, surface_child = _surface_pair(spec.axis, seed=spec.seed, row_index=row_index)
    lexical = _lexical_metadata(
        row_index,
        seed=spec.seed,
        topic=surface_parent,
        task=surface_child,
    )

    if spec.axis == "40e":
        operator, domain = cas_label.split("|", 1)
        prompt = _prompt_40e(
            topic=surface_parent,
            frame=surface_child,
            row_index=row_index,
            seed=spec.seed,
        )
        return {
            "id": f"mtc40v2_{split}_{row_index:05d}",
            "sample_id": f"mtc40v2_{split}_{row_index:05d}",
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
            "surface_semantic": {
                "topic_40": surface_parent,
                "frame_40": surface_child,
            },
            "lexical_pack_id": lexical["lexical_pack_id"],
            "domain_slug": lexical["domain_slug"],
            "task_slug": lexical["task_slug"],
            "paraphrase_family": lexical["paraphrase_family"],
            "surface_style": lexical["surface_style"],
            "question_type": lexical["question_type"],
            "metadata": {
                "fixture_family": "mtc_v2_concrete",
                "axis": "40e",
                "seed": spec.seed,
                "matched_control_prompt_policy": (
                    "control label is row metadata; visible prompt topic/task is independently rotated"
                ),
                **lexical,
            },
        }

    drive, register = cas_label.split("|", 1)
    prompt = _prompt_f28(
        topic=surface_parent,
        function=surface_child,
        row_index=row_index,
        seed=spec.seed,
    )
    return {
        "id": f"mtcf28v2_{split}_{row_index:05d}",
        "sample_id": f"mtcf28v2_{split}_{row_index:05d}",
        "split": split,
        "prompt": prompt,
        "drive": drive,
        "register": register,
        "labels_drive": drive,
        "labels_register": register,
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
        "surface_semantic": {
            "topic_7": surface_parent,
            "function_4": surface_child,
        },
        "lexical_pack_id": lexical["lexical_pack_id"],
        "domain_slug": lexical["domain_slug"],
        "task_slug": lexical["task_slug"],
        "paraphrase_family": lexical["paraphrase_family"],
        "surface_style": lexical["surface_style"],
        "question_type": lexical["question_type"],
        "metadata": {
            "fixture_family": "mtc_v2_concrete",
            "axis": "f28",
            "seed": spec.seed,
            "matched_control_prompt_policy": (
                "control label is row metadata; visible prompt topic/task is independently rotated"
            ),
            **lexical,
        },
    }


def _validate_prompt_hygiene(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        prompt = str(row.get("prompt", ""))
        lower = prompt.lower()
        for term in BANNED_PROMPT_ANCHOR_TERMS:
            if re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", lower):
                raise RuntimeError(f"prompt contains banned anchor term {term!r}: {row.get('id')}")
        for fragment in VISIBLE_BADGE_FRAGMENTS:
            if fragment in lower:
                raise RuntimeError(f"prompt contains visible fixture fragment {fragment!r}: {row.get('id')}")
        if "^" in prompt:
            raise RuntimeError(f"prompt contains visible operator badge: {row.get('id')}")


def build_fixture(spec: AxisSpec) -> dict[str, Any]:
    if len(spec.cas_labels) != len(spec.control_labels):
        raise SystemExit(
            f"{spec.axis} requires equal CAS/control cardinality; "
            f"got {len(spec.cas_labels)} and {len(spec.control_labels)}"
        )
    if not (0 < spec.train_per_class < spec.rows_per_class):
        raise SystemExit("--train-per-class must be between 1 and rows-per-class - 1")

    row_jobs: list[tuple[int, str, str]] = []
    assignment_rng = random.Random(f"{spec.seed}:{spec.axis}:control_assignment")
    for rep in range(spec.rows_per_class):
        control_labels = list(spec.control_labels)
        assignment_rng.shuffle(control_labels)
        for cas_label, control_label in zip(spec.cas_labels, control_labels, strict=True):
            row_jobs.append((rep, cas_label, control_label))
    random.Random(spec.seed).shuffle(row_jobs)

    rows = [
        _build_row(
            spec=spec,
            cas_label=cas_label,
            control_label=control_label,
            rep=rep,
            row_index=row_index,
        )
        for row_index, (rep, cas_label, control_label) in enumerate(row_jobs)
    ]
    _validate_prompt_hygiene(rows)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_date": "2026-05-30",
        "status": "fixture_ready_for_capture",
        "axis": spec.axis,
        "source_axis": spec.source_axis,
        "control_id": spec.control_id,
        "seed": spec.seed,
        "rows_per_cas_class": spec.rows_per_class,
        "train_per_cas_class": spec.train_per_class,
        "test_per_cas_class": spec.rows_per_class - spec.train_per_class,
        "row_count": len(rows),
        "prompt_authoring_rule": (
            "ordinary concrete scenario prose; CAS labels, matched-control labels, "
            "and lexical distractors are metadata only"
        ),
        "records": rows,
    }
    payload["content_sha256"] = _sha256_json(payload)
    return payload


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote MTC v2 concrete fixture: {path}")
    print(f"rows: {payload['row_count']}")
    print(f"sha256: {payload['content_sha256']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--axis", required=True, choices=("40e", "f28"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows-per-class", type=int, default=DEFAULT_ROWS_PER_CLASS)
    parser.add_argument("--train-per-class", type=int, default=DEFAULT_TRAIN_PER_CLASS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    manifest = _load_json(args.manifest)
    spec = _axis_spec(
        axis=args.axis,
        manifest=manifest,
        rows_per_class=args.rows_per_class,
        train_per_class=args.train_per_class,
        seed=args.seed,
    )
    _write_payload(args.output, build_fixture(spec))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
