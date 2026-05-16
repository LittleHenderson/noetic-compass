"""Build the Stage 6 role-bound noetic counterfactual pilot fixture.

This is the first concrete artifact from
STAGE6_ROUNDTABLE_V3_PLAN_20260516.md. It is intentionally small:
10 contrast bundles x 5 noetic pairs x 2 focused roles = 100 rows.

The point is not training scale. The point is to prove the v3 data
shape, split isolation, and validator before generating the full
3,000-row fixture.

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage6_role_bound_pilot.py
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_DATE = "20260516"
_OUT_JSONL = _HERE / f"stage6_role_bound_pilot_{_DATE}.jsonl"
_OUT_MANIFEST = _HERE / f"stage6_role_bound_pilot_manifest_{_DATE}.json"

_NOETIC_NAMES = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}

_PAIR_META = {
    "0_1": {
        "labels": (0, 1),
        "roles": {
            0: "object_content",
            1: "active_processing",
        },
    },
    "2_3": {
        "labels": (2, 3),
        "roles": {
            2: "toward_vector",
            3: "away_vector",
        },
    },
    "4_7": {
        "labels": (4, 7),
        "roles": {
            4: "impression_strength",
            7: "repeated_cadence",
        },
    },
    "5_6": {
        "labels": (5, 6),
        "roles": {
            5: "carrier_shaped_by_received_contents",
            6: "construct_made_of_inner_parts",
        },
    },
    "8_9": {
        "labels": (8, 9),
        "roles": {
            8: "source_cue",
            9: "resulting_content",
        },
    },
}

_BUNDLES = [
    {
        "id": "bundle001_debugging_patch",
        "split": "train",
        "lexical_pack_id": "debugging_alert_patch_trace",
        "object": "dashboard bug",
        "processor": "analyst",
        "toward": "clear reproduction",
        "away": "noisy log trail",
        "impression": "red error banner",
        "cadence": "hourly check loop",
        "carrier": "reviewer",
        "prior": "past outage reports",
        "construct": "patch plan",
        "parts": "rollback, test, deploy, and monitor steps",
        "cue": "alert ping",
        "result": "incident checklist",
    },
    {
        "id": "bundle002_classroom_method",
        "split": "train",
        "lexical_pack_id": "classroom_question_method_board",
        "object": "geometry question",
        "processor": "student",
        "toward": "diagram method",
        "away": "guessing shortcut",
        "impression": "teacher's example",
        "cadence": "daily review cycle",
        "carrier": "learner",
        "prior": "earlier lessons",
        "construct": "solution plan",
        "parts": "given facts, sketch, rule, and check",
        "cue": "board diagram",
        "result": "angle procedure",
    },
    {
        "id": "bundle003_policy_appeal",
        "split": "train",
        "lexical_pack_id": "policy_worker_appeal_audit",
        "object": "workplace policy",
        "processor": "case officer",
        "toward": "appeal path",
        "away": "unchecked penalty",
        "impression": "public complaint",
        "cadence": "quarterly audit cycle",
        "carrier": "committee",
        "prior": "previous worker cases",
        "construct": "fairness review",
        "parts": "notice, appeal, bias check, and remedy",
        "cue": "risk flag",
        "result": "worker-protection checklist",
    },
    {
        "id": "bundle004_music_practice",
        "split": "train",
        "lexical_pack_id": "music_chord_scale_session",
        "object": "opening chord",
        "processor": "player",
        "toward": "clean tone",
        "away": "rushed fingering",
        "impression": "first chord",
        "cadence": "metronome drill",
        "carrier": "performer",
        "prior": "years of scales",
        "construct": "practice plan",
        "parts": "warmup, tempo, phrase, and review",
        "cue": "count-in click",
        "result": "finger pattern",
    },
    {
        "id": "bundle005_route_planning",
        "split": "train",
        "lexical_pack_id": "route_shade_detour_map",
        "object": "river route",
        "processor": "planner",
        "toward": "shaded path",
        "away": "blocked detour",
        "impression": "bridge closure sign",
        "cadence": "morning traffic cycle",
        "carrier": "driver",
        "prior": "commute history",
        "construct": "route plan",
        "parts": "start, turn, checkpoint, and arrival",
        "cue": "map alert",
        "result": "alternate route",
    },
    {
        "id": "bundle006_recipe_sauce",
        "split": "train",
        "lexical_pack_id": "recipe_sauce_heat_timing",
        "object": "sauce recipe",
        "processor": "cook",
        "toward": "balanced flavor",
        "away": "burnt edge",
        "impression": "sharp aroma",
        "cadence": "stirring interval",
        "carrier": "chef",
        "prior": "kitchen trials",
        "construct": "meal plan",
        "parts": "ingredients, heat, timing, and plate",
        "cue": "smell of garlic",
        "result": "simmering procedure",
    },
    {
        "id": "bundle007_legal_argument",
        "split": "val",
        "lexical_pack_id": "legal_claim_precedent_exception",
        "object": "legal claim",
        "processor": "judge",
        "toward": "clear precedent",
        "away": "unsupported exception",
        "impression": "key testimony",
        "cadence": "hearing schedule",
        "carrier": "court",
        "prior": "prior decisions",
        "construct": "argument",
        "parts": "claim, evidence, rule, and conclusion",
        "cue": "cited case",
        "result": "precedent analysis",
    },
    {
        "id": "bundle008_model_card",
        "split": "val",
        "lexical_pack_id": "model_card_risk_eval_limit",
        "object": "model card",
        "processor": "auditor",
        "toward": "clear limitation",
        "away": "hidden failure mode",
        "impression": "warning table",
        "cadence": "release review loop",
        "carrier": "evaluation team",
        "prior": "test history",
        "construct": "deployment note",
        "parts": "data, limits, checks, and rollout",
        "cue": "risk marker",
        "result": "safety review",
    },
    {
        "id": "bundle009_dog_training",
        "split": "test",
        "lexical_pack_id": "dog_command_reward_schedule",
        "object": "sit command",
        "processor": "dog",
        "toward": "treat reward",
        "away": "sharp correction",
        "impression": "trainer's voice",
        "cadence": "practice session",
        "carrier": "animal",
        "prior": "earlier handling",
        "construct": "training routine",
        "parts": "cue, posture, reward, and repeat",
        "cue": "spoken command",
        "result": "sitting response",
    },
    {
        "id": "bundle010_product_design",
        "split": "test",
        "lexical_pack_id": "product_layout_button_feedback",
        "object": "checkout button",
        "processor": "designer",
        "toward": "clear action",
        "away": "confusing layout",
        "impression": "user complaint",
        "cadence": "weekly usability pass",
        "carrier": "design team",
        "prior": "customer feedback",
        "construct": "interface plan",
        "parts": "layout, wording, state, and response",
        "cue": "support ticket",
        "result": "layout revision",
    },
]


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _make_base_sentence(pair_key: str, bundle: dict[str, str], swap: bool) -> tuple[str, dict[int, str]]:
    labels = _PAIR_META[pair_key]["labels"]
    if pair_key == "0_1":
        role_a = f"A names the {bundle['object']} as the item under review"
        role_b = f"B actively holds and compares that item during the task"
    elif pair_key == "2_3":
        role_a = f"A pulls the agent toward {bundle['toward']}"
        role_b = f"B pushes the agent away from {bundle['away']}"
    elif pair_key == "4_7":
        role_a = f"A lands with strong force through the {bundle['impression']}"
        role_b = f"B returns through the {bundle['cadence']}"
    elif pair_key == "5_6":
        role_a = f"A is shaped by {bundle['prior']} already received"
        role_b = f"B is built from {bundle['parts']}"
    elif pair_key == "8_9":
        role_a = f"A calls up B for the system"
        role_b = f"A is the {bundle['cue']} and B is the {bundle['result']}"
    else:
        raise ValueError(f"unknown pair_key {pair_key!r}")

    if pair_key == "8_9":
        if not swap:
            base = f"{role_b}. {role_a}."
            label_to_focus = {8: "A", 9: "B"}
        else:
            base = (
                f"B is the {bundle['cue']} and A is the {bundle['result']}. "
                "B calls up A for the system."
            )
            label_to_focus = {8: "B", 9: "A"}
        return base, label_to_focus

    if not swap:
        base = f"{role_a}; {role_b}."
        label_to_focus = {labels[0]: "A", labels[1]: "B"}
    else:
        base = f"{role_b.replace('B ', 'A ', 1)}; {role_a.replace('A ', 'B ', 1)}."
        label_to_focus = {labels[0]: "B", labels[1]: "A"}
    return base, label_to_focus


def _mapping_note(label: int, focus: str, pair_key: str) -> str:
    role = _PAIR_META[pair_key]["roles"][label]
    return f"Focus {focus} is the {role} role for {label}:{_NOETIC_NAMES[label]}."


def _build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle_index, bundle in enumerate(_BUNDLES, start=1):
        for pair_index, pair_key in enumerate(("0_1", "2_3", "4_7", "5_6", "8_9"), start=1):
            # Alternate the A/B assignment by bundle and pair so focus marker
            # alone cannot predict a noetic label.
            swap = (bundle_index + pair_index) % 2 == 0
            base, label_to_focus = _make_base_sentence(pair_key, bundle, swap=swap)
            labels = _PAIR_META[pair_key]["labels"]
            pair_id = f"{bundle['id']}_{pair_key}"
            for label in labels:
                focus = label_to_focus[label]
                english = f"{base} Focus: {focus}."
                row = {
                    "sample_id": f"stage6_pilot_{bundle['id']}_{pair_key}_n{label}",
                    "dataset_version": "stage6_role_bound_noetic_pilot_v0",
                    "dataset_scope": "pilot_schema_and_validator",
                    "split": bundle["split"],
                    "contrast_bundle_id": bundle["id"],
                    "lexical_pack_id": bundle["lexical_pack_id"],
                    "template_id": f"{bundle['id']}_{pair_key}_template_v01",
                    "counterfactual_pair_id": pair_id,
                    "paraphrase_family": f"{bundle['split']}_role_focus_minimal",
                    "surface_style": "role_bound_system_plain",
                    "english": english,
                    "base_sentence": base,
                    "noetic_label": label,
                    "noetic_name": _NOETIC_NAMES[label],
                    "canonical_noetic": label,
                    "canonical_label": _NOETIC_NAMES[label],
                    "cas_expression": f"^{label}",
                    "focus_span": focus,
                    "contrast_partner_label": labels[1] if label == labels[0] else labels[0],
                    "hard_contrast_labels": list(labels),
                    "semantic_role": _PAIR_META[pair_key]["roles"][label],
                    "mapping_note": _mapping_note(label, focus, pair_key),
                    "anti_leak_flags": {
                        "contains_cas_notation": False,
                        "contains_label_name": False,
                        "approved_alias_used": False,
                        "counterbalanced_keyword_pack": True,
                    },
                    "source_strategy": "hand_authored_role_bound_counterfactual",
                    "review_status": "author_reviewed_not_blind",
                    "confidence": "pilot_high",
                }
                rows.append(row)
    return rows


def main() -> int:
    rows = _build_rows()
    _OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _OUT_JSONL.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    counts = Counter(int(row["noetic_label"]) for row in rows)
    split_counts = Counter(str(row["split"]) for row in rows)
    manifest = {
        "schema_version": "stage6_role_bound_pilot_manifest.v1",
        "dataset_version": "stage6_role_bound_noetic_pilot_v0",
        "status": "pilot_not_training_not_locked_eval",
        "output_file": _OUT_JSONL.name,
        "output_sha256": _sha256_of_file(_OUT_JSONL),
        "n_records": len(rows),
        "n_bundles": len(_BUNDLES),
        "n_counterfactual_pairs": len({row["counterfactual_pair_id"] for row in rows}),
        "class_distribution": {str(k): counts[k] for k in sorted(counts)},
        "split_distribution": {k: split_counts[k] for k in sorted(split_counts)},
        "design": {
            "rows_per_bundle": 10,
            "pairs_per_bundle": 5,
            "labels_per_pair": 2,
            "focus_markers_counterbalanced": True,
            "model_input_field": "english",
            "model_input_excludes_mapping_note": True,
        },
    }
    _OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
