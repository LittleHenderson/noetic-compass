"""Construction-first synthetic tasks; no neural execution or model imports.

This is a small CAS-SDG-style adapter, not the full historical SDG service.
Gold is constructed from formal stage/source choices, then wording is rendered.
A separately written parser and manual anchors check those choices. Held-out
templates and formal input instances are disjoint, but custody is internal.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import re

VERSION = "cas-meta1-sdg/1"
TAGS = ("amber", "teal", "violet", "coral", "indigo", "lime")
STAGES = ("first", "second", "final")
BASE_VALUES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
EXPECTED = (
    {"workflow": ["A"], "final_symbol": "L1", "repair_required": False},
    {"workflow": ["A", "B"], "final_symbol": "L3", "repair_required": False},
    {"workflow": ["A", "B", "C", "R", "C"], "final_symbol": "L2", "repair_required": True},
)
TEMPLATES = {
    "train": (
        "For sample {tag}, stop after the {stage} stage.",
        "Use the {tag} input and deliver the {stage} stage result.",
        "Take sample {tag}. I need its {stage} stage result.",
        "Process the {tag} sample to the {stage} stage.",
        "The requested sample is {tag}; the requested stage is {stage}.",
        "Return the {stage} stage result for sample {tag}.",
    ),
    "validation": (
        "Please take the input tagged {tag} as far as the {stage} stage.",
        "For {tag}, the {stage} stage result is the one requested.",
    ),
    "test": (
        "Using sample {tag}, provide only its {stage} stage result.",
        "I require the {stage} stage result from the input marked {tag}.",
        "Choose the sample tagged {tag} and finish at the {stage} stage.",
    ),
}
DEFAULT_COUNTS = {"train": 864, "validation": 72, "test": 72}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def check_public(public):
    if type(public) is not dict or set(public) != {"problem", "observations"}:
        raise ValueError("PUBLIC_FIELDS_MISMATCH")
    if type(public["problem"]) is not str or not 1 <= len(public["problem"]) <= 512:
        raise ValueError("INVALID_PROBLEM")
    observations = public["observations"]
    if type(observations) is not list or len(observations) != 3:
        raise ValueError("THREE_OBSERVATIONS_REQUIRED")
    tags = set()
    for slot, observation in enumerate(observations):
        if type(observation) is not dict or set(observation) != {"slot", "tag", "values"}:
            raise ValueError("OBSERVATION_FIELDS_MISMATCH")
        if type(observation["slot"]) is not int or observation["slot"] != slot:
            raise ValueError("SLOT_ORDER_MISMATCH")
        if observation["tag"] not in TAGS or observation["tag"] in tags:
            raise ValueError("INVALID_OR_DUPLICATE_TAG")
        tags.add(observation["tag"])
        values = observation["values"]
        if type(values) is not list or len(values) != 8:
            raise ValueError("EIGHT_VALUES_REQUIRED")
        if any(type(value) not in (int, float) or not math.isfinite(value)
               or abs(value - base) > 0.001 for value, base in zip(values, BASE_VALUES)):
            raise ValueError("INPUT_OUTSIDE_REGISTERED_FIXTURE_NEIGHBORHOOD")
    return True


def permitted_view(task):
    # No task ID, split label, formal target, answer, or provenance is returned.
    check_public(task["public"])
    return deepcopy(task["public"])


def rule_select(public):
    """Deliberately simple reference parser, given the same public information."""
    check_public(public)
    words = set(re.findall(r"[a-z]+", public["problem"].lower()))
    requested = [(0, "first"), (1, "second"), (2, "final")]
    procedures = [index for index, name in requested if name in words]
    bindings = [obs["slot"] for obs in public["observations"] if obs["tag"] in words]
    if len(procedures) != 1 or len(bindings) != 1:
        raise ValueError("AMBIGUOUS_OR_UNSUPPORTED_TASK")
    return {"procedure": procedures[0], "binding": bindings[0]}


def _formal_instance(rng, procedure, binding):
    tags = rng.sample(list(TAGS), 3)
    observations = []
    for slot, tag in enumerate(tags):
        values = [round(base + rng.uniform(-0.0004, 0.0004), 7) for base in BASE_VALUES]
        observations.append({"slot": slot, "tag": tag, "values": values})
    return {"stage": STAGES[procedure], "requested_tag": tags[binding],
            "observations": observations}


def generate_dataset(seed=20260905, counts=None):
    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    if set(counts) != set(DEFAULT_COUNTS):
        raise ValueError("SPLITS_REQUIRED")
    rng = random.Random(seed)
    dataset = {}
    for split, count in counts.items():
        if type(count) is not int or count < 9 or count % 9:
            raise ValueError("COUNT_MUST_BE_POSITIVE_MULTIPLE_OF_NINE")
        rows = []
        # Joint procedure/binding balance, not merely label marginal balance.
        for repeat in range(count // 9):
            for procedure in range(3):
                for binding in range(3):
                    formal = _formal_instance(rng, procedure, binding)
                    template_index = repeat % len(TEMPLATES[split])
                    template = TEMPLATES[split][template_index]
                    public = {
                        "problem": template.format(tag=formal["requested_tag"], stage=formal["stage"]),
                        "observations": deepcopy(formal["observations"]),
                    }
                    target = {"procedure": procedure, "binding": binding,
                              "expected": deepcopy(EXPECTED[procedure])}
                    rows.append({
                        "id": digest({"version": VERSION, "formal": formal, "wording": public["problem"]}),
                        "public": public, "target": target,
                        "provenance": {
                            "generator": VERSION, "seed": seed, "split": split,
                            "template_id": f"{split}:{template_index}",
                            "formal_instance_digest": digest(formal),
                            "construction": "formal stage/source and tensor first; surface wording second",
                            "custody": "INTERNAL_DEVELOPMENT_HOLDOUT_NOT_EXTERNAL_AUDIT",
                        },
                    })
        rng.shuffle(rows)
        dataset[split] = rows
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset):
    if set(dataset) != {"train", "validation", "test"}:
        raise ValueError("SPLITS_REQUIRED")
    ids, formal_ids, public_hashes, split_templates = set(), set(), set(), {}
    counts = {}
    for split, rows in dataset.items():
        joint = {(p, b): 0 for p in range(3) for b in range(3)}
        templates = set()
        for task in rows:
            if set(task) != {"id", "public", "target", "provenance"}:
                raise ValueError("TASK_FIELDS_MISMATCH")
            public = permitted_view(task)
            target = task["target"]
            if set(target) != {"procedure", "binding", "expected"}:
                raise ValueError("TARGET_FIELDS_MISMATCH")
            p, b = target["procedure"], target["binding"]
            if type(p) is not int or type(b) is not int or (p, b) not in joint:
                raise ValueError("TARGET_RANGE")
            # A separately coded public parser checks rendered text and binding.
            if rule_select(public) != {"procedure": p, "binding": b}:
                raise ValueError("SURFACE_ROUNDTRIP_MISMATCH")
            if target["expected"] != EXPECTED[p]:
                raise ValueError("DECLARED_OUTCOME_MISMATCH")
            provenance = task["provenance"]
            if provenance["split"] != split or not provenance["template_id"].startswith(split + ":"):
                raise ValueError("SPLIT_PROVENANCE_MISMATCH")
            formal_id = provenance["formal_instance_digest"]
            reconstructed = {"stage": STAGES[p], "requested_tag": public["observations"][b]["tag"],
                             "observations": public["observations"]}
            if formal_id != digest(reconstructed):
                raise ValueError("FORMAL_INSTANCE_DIGEST_MISMATCH")
            if task["id"] != digest({"version": VERSION, "formal": reconstructed,
                                     "wording": public["problem"]}):
                raise ValueError("TASK_ID_MISMATCH")
            public_hash = digest(public)
            if task["id"] in ids or formal_id in formal_ids or public_hash in public_hashes:
                raise ValueError("DUPLICATE_OR_SPLIT_LEAKAGE")
            ids.add(task["id"]); formal_ids.add(formal_id); public_hashes.add(public_hash)
            templates.add(provenance["template_id"])
            joint[(p, b)] += 1
        if not rows or len(set(joint.values())) != 1 or min(joint.values()) == 0:
            raise ValueError("UNBALANCED_JOINT_TARGETS")
        split_templates[split] = sorted(templates)
        counts[split] = len(rows)
    # Template identifiers AND literal wording templates have separate ownership.
    all_templates = [template for group in TEMPLATES.values() for template in group]
    if len(set(all_templates)) != len(all_templates):
        raise ValueError("TEMPLATE_OVERLAP")
    return {"status": "STRUCTURAL_AND_SURFACE_TARGET_CHECKS_PASSED", "counts": counts,
            "unique_formal_instances": len(formal_ids), "templates": split_templates,
            "neural_outcomes_checked": False,
            "boundary": "Independent direct-native outcome checking happens on AWS, not in this text generator."}


def write_dataset(output, seed=20260905, counts=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    dataset = generate_dataset(seed, counts)
    objects = {"train.json": dataset["train"], "validation.json": dataset["validation"],
               "test_public.json": [permitted_view(task) for task in dataset["test"]],
               "test_private.json": dataset["test"]}
    hashes = {}
    for name, value in objects.items():
        raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        (output / name).write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schema": VERSION, "seed": seed, "sha256": hashes,
        "checks": validate_dataset(dataset),
        "generator_file_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "label_custody": "Training/validation private targets are supervised inputs. Test targets may only be opened after all selector predictions are sealed.",
        "permitted_fields": ["problem", "observations"],
        "excluded_selector_fields": ["id", "target", "provenance"],
        "native_outcome_authority": "Independent direct frozen-runtime reference on AWS",
        "capability_scope": "Three named stage goals and three source bindings; not unrestricted language or new program synthesis.",
    }
    (output / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260905)
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.output, args.seed), indent=2))


if __name__ == "__main__":
    main()
