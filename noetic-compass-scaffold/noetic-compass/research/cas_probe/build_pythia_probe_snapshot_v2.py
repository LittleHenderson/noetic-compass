"""Build the v2 Pythia noetic-probe label snapshot.

V2 starts from the frozen v1 snapshot and appends deterministic,
hand-authored rows that repair the Stage 5.3 finding:

    ^6 Male was alias-bound ("breaking down / unpacking") and did not
    recognize the corrected concept "an idea made of nested ideas while
    itself being part of a larger set of ideas."

The augment rows are research-only probe supervision. They are not CAS
Native training data and do not touch production code.

Run from repo root:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/build_pythia_probe_snapshot_v2.py
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_BASE_DATE = "20260515"
_V2_DATE = "20260516"
_BASE_LABELS = _HERE / f"pythia_probe_labels_{_BASE_DATE}.jsonl"
_OUT_LABELS = _HERE / f"pythia_probe_labels_v2_{_V2_DATE}.jsonl"
_OUT_MANIFEST = _HERE / f"pythia_probe_manifest_v2_{_V2_DATE}.json"

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


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _augment_rows(label: int, group: str, texts: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": f"v2_{group}_{i:03d}",
            "source_seed_id": f"v2_hand_authored_{group}_{i:03d}",
            "english": text,
            "noetic_label": label,
            "noetic_name": _NOETIC_NAMES[label],
            "source_cas_expression": f"^{label}",
            "grammar_category": "v2_hand_authored_noetic_repair",
            "v2_group": group,
            "v2_note": "hand-authored probe-supervision row; research-only; not production CAS Native training data",
        }
        for i, text in enumerate(texts, start=1)
    ]


def _build_augments() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    rows += _augment_rows(
        6,
        "male_nested_composition",
        [
            "A single idea contains smaller ideas arranged inside it as a nested structure.",
            "The concept is built from inner concepts that each carry part of its meaning.",
            "The plan is one idea, but it includes goals, steps, tools, timing, and constraints.",
            "The claim is composed from premise, evidence, warrant, exception, and conclusion.",
            "The command idea contains cue, posture, memory, reward expectation, and repetition.",
            "The recipe is one idea made from ingredients, order, heat, timing, and serving.",
            "The policy idea contains rights, duties, enforcement, appeal, and review.",
            "The design is a whole idea whose parts are layout, function, color, motion, and state.",
            "The story-world idea contains setting, character, motive, conflict, and outcome.",
            "The workflow is one idea made from input, transform, check, output, and feedback.",
            "The model-card idea contains data, training, limits, tests, and deployment context.",
            "The proof idea is built from assumptions, lemmas, inference steps, and conclusion.",
        ],
    )
    rows += _augment_rows(
        6,
        "male_no_alias_plain",
        [
            "The larger thought depends on the smaller thoughts that sit within it.",
            "Several meanings join inside one meaning without becoming separate topics.",
            "The idea is not atomic; it has internal constituents.",
            "One thought stands apart while being made from other thoughts inside it.",
            "The whole meaning is structured by the meanings it includes.",
            "A combined idea is present because several inner ideas work together.",
            "The concept has parts inside parts, all belonging to the same concept.",
            "The inner meanings are constituents of the larger meaning.",
            "The main idea has an internal architecture of smaller ideas.",
            "The thought contains a set of related sub-thoughts within itself.",
            "The central meaning is assembled from meanings that remain inside it.",
            "The idea has nested content rather than being a single simple unit.",
        ],
    )
    rows += _augment_rows(
        6,
        "male_alias_blend",
        [
            "Breaking down the idea reveals the nested ideas that compose it.",
            "Unpacking the plan shows the inner parts that make the plan one idea.",
            "Looking underneath the claim reveals premise, evidence, rule, and conclusion.",
            "Pulling apart the concept exposes the smaller ideas inside the larger one.",
            "Breaking down the policy shows the rights, duties, exceptions, and review process within it.",
            "Unpacking the recipe reveals ingredients, timing, order, and heat as inner ideas.",
            "Looking underneath the model-card shows data, training, limits, and tests inside the same idea.",
            "Breaking down the workflow exposes input, transformation, validation, and output.",
            "Unpacking the story shows setting, motive, conflict, and outcome within the story idea.",
            "Pulling apart the argument reveals how its smaller ideas compose the whole.",
            "Breaking down the command reveals cue, response, memory, and reward expectation.",
            "Looking underneath the design reveals the functions and states that compose it.",
        ],
    )

    rows += _augment_rows(
        5,
        "female_accumulated_mind",
        [
            "A mind is shaped by the experiences it has taken in over time.",
            "The person's past becomes part of what the person is now.",
            "The system's prior training forms the makeup from which it responds.",
            "Memory, habit, and history compose the way this mind receives new ideas.",
            "What the mind has lived through becomes part of the mind itself.",
            "The model's learned corpus is part of what its processing system is made of.",
            "The worker's experience changes what seems obvious during a new task.",
            "The musician's years of practice shape how a new melody is heard.",
            "The reader's background becomes part of how the passage is understood.",
            "The agent's accumulated state shapes how new input is interpreted.",
            "A mind carries its prior contents into the next act of awareness.",
            "The student's earlier lessons become part of the present understanding.",
            "The judge's history with similar cases shapes the present evaluation.",
            "The system's stored patterns form the substrate for its next response.",
            "The person's identity is composed by remembered experiences and values.",
            "The mind has been impregnated by what it repeatedly received.",
            "The observer's past makes the same image mean something different.",
            "The user profile becomes part of the system's interpretive makeup.",
        ],
    )

    rows += _augment_rows(
        0,
        "idea_bare_object",
        [
            "A single topic is the object currently under discussion.",
            "This is the subject matter itself, before any reaction to it.",
            "The bridge is the thing being considered.",
            "The policy is the item the analysis is about.",
            "The route is the thing held as the content of thought.",
            "The painting is the object before the viewer.",
            "The bug report is the topic the developer is considering.",
            "The question is the thing currently in mind.",
            "The missing key is the object of the search.",
            "The proposed rule is the content under review.",
        ],
    )
    rows += _augment_rows(
        2,
        "positive_attraction",
        [
            "The option attracts attention and pulls the mind toward it.",
            "The proposal feels appealing and keeps drawing interest.",
            "The candidate is favored by the selection process.",
            "The opportunity speaks to the person and invites pursuit.",
            "The idea feels worth moving toward.",
            "The bright route pulls the traveler forward.",
            "The solution stands out as desirable among the choices.",
            "The mind has affinity for this possibility.",
            "The reward draws the agent toward the action.",
            "The evidence appears promising and attracts further attention.",
        ],
    )
    rows += _augment_rows(
        4,
        "vibration_impression",
        [
            "The idea makes a strong impression on the mind.",
            "The sentence resonates and stays present after it is heard.",
            "The signal has high salience in the processing state.",
            "The image strikes the viewer and keeps echoing afterward.",
            "The memory has a strong felt presence.",
            "The phrase lands with force and remains noticeable.",
            "The sound makes a lasting impression on awareness.",
            "The result feels vivid because it resonates strongly.",
            "The warning carries enough weight to stay active in mind.",
            "The melody lingers because its impression is strong.",
        ],
    )
    rows += _augment_rows(
        8,
        "above_trigger",
        [
            "One cue triggers another idea to appear.",
            "The smell of bread brings a kitchen memory to mind.",
            "The warning flag causes the system to retrieve a safety procedure.",
            "The old song makes the driver think of a summer trip.",
            "The question points the debater toward a stored answer.",
            "The jacket on the chair triggers the memory of a pocket.",
            "The failing assertion brings an off-by-one possibility to mind.",
            "The painted doorway reminds the viewer of a childhood house.",
            "The alarm starts the thought of evacuation.",
            "The phrase makes the reader think of a different passage.",
        ],
    )

    return rows


def build() -> dict[str, Any]:
    base = _load_jsonl(_BASE_LABELS)
    augments = _build_augments()
    rows = base + augments

    with _OUT_LABELS.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    base_dist = Counter(int(row["noetic_label"]) for row in base)
    augment_dist = Counter(int(row["noetic_label"]) for row in augments)
    final_dist = Counter(int(row["noetic_label"]) for row in rows)
    manifest = {
        "schema_version": "pythia_probe_snapshot.v2",
        "snapshot_id": f"pythia_probe_labels_v2_{_V2_DATE}",
        "snapshot_file": _OUT_LABELS.name,
        "snapshot_sha256": _sha256_of_file(_OUT_LABELS),
        "base_snapshot_file": _BASE_LABELS.name,
        "base_snapshot_sha256": _sha256_of_file(_BASE_LABELS),
        "base_record_count": len(base),
        "augment_record_count": len(augments),
        "record_count": len(rows),
        "base_class_distribution": {str(k): v for k, v in sorted(base_dist.items())},
        "augment_class_distribution": {str(k): v for k, v in sorted(augment_dist.items())},
        "final_class_distribution": {str(k): v for k, v in sorted(final_dist.items())},
        "purpose": (
            "Repair Stage 5.3's alias-bound ^6 Male readout by adding "
            "corrected nested-composition examples, no-alias composition "
            "examples, and hard ^5 Female vs ^6 Male contrasts."
        ),
        "holdout_warning": (
            "Do not evaluate v2 by claiming success on rows copied into this "
            "snapshot. Use Stage 5.2/5.3 fixtures and future held-out fixtures "
            "for transfer checks."
        ),
    }
    with _OUT_MANIFEST.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return manifest


def main() -> int:
    manifest = build()
    print(f"snapshot written: {_OUT_LABELS}")
    print(f"manifest written: {_OUT_MANIFEST}")
    print(f"records: {manifest['record_count']} ({manifest['base_record_count']} base + {manifest['augment_record_count']} augments)")
    print("final_class_distribution:")
    for label, count in manifest["final_class_distribution"].items():
        print(f"  ^{label}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
