"""Pure, public-task-conditioned one-child curriculum; no native execution.

This is controlled procedural/source selection, not an invented arithmetic
meaning for a CJT. Authored L1/L2 labels are existing fixture expectations,
not proof that a new task executes. The parent always returns the child result;
return-choice learning is deliberately outside this first pilot.
"""
from collections import Counter
from copy import deepcopy
import random
import re
import struct

from . import codec
from .child_scaffold_v8 import compile_choice
from .curriculum import TAGS, check_public, graph_signature
from .ir import validate_program
from .native import EXPECTED, admit_action

SCHEMA = "cas-meta2-one-child-task/8"
DATASET_SCHEMA = "cas-meta2-one-child-curriculum/8"
COMBINATIONS = ("B_C", "B_CR", "R_C", "R_CR")
FAMILIAR = COMBINATIONS[:3]
HELD_OUT = "R_CR"
COUNTS = {"train": 192, "validation": 72, "test": 48}
GROUP_COUNTS = {"train": 64, "validation": 24, "test": 24}
REQUESTS = {
    "train": "Request observation {tag}; take the {ordinal} committed prelude result; request the child's authored label {label}.",
    "validation": "Use observation {tag}. The child input must be the {ordinal} committed prelude result. Its requested authored result label is {label}.",
    "test": "Choose observation {tag}. Feed the child the {ordinal} committed prelude result and ask for authored result label {label}.",
    "qualification": "Development request: observation {tag}; source is the {ordinal} committed prelude result; desired authored child label is {label}.",
}
BOUNDARY = ("Public-task-conditioned controlled procedure and source-provenance selection. "
            "No new numeric transformation semantics, repair claim, learned return choice, "
            "native task correctness, or training permission follows from this pure package.")


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _payload(values):
    return struct.pack("<8f", *values)


def _digest(value):
    return codec.canonical_sha256(value)


def _catalog_line(name, kind):
    if kind == "C":
        body = "C(arg)->v0; RETURN v0"
    else:
        body = "C(arg)->v0; R(v0)->v1; RETURN v1"
    return f"Child {name}: {body}; authored result {EXPECTED[kind[-1]]}."


def _render(context, combination, family):
    names, children = context["parent_names"], context["child_names"]
    source, kind = combination.split("_")
    tag = next(row["tag"] for row in context["observations"] if row["slot"] == context["binding"])
    catalog = [_catalog_line(children[0], "C"), _catalog_line(children[1], "CR")]
    if context["reverse_catalog"]:
        catalog.reverse()
    return "\n".join([
        "ONE-CHILD TASK / 8", "Parent main input arg.",
        f"Prelude: A(arg)->{names[0]}; B({names[0]})->{names[1]}; C({names[1]})->{names[2]}; R({names[2]})->{names[3]}.",
        f"CALL output: {names[4]}.",
        "Available CALL inputs: " + ", ".join(["arg", *names[:4]]) + ".",
        "Available parent returns: " + ", ".join(["arg", *names]) + ".",
        *catalog,
        "Authored labels are fixture expectations if accepted, not new numerical meanings. All ordinary topology and Effect checks still apply.",
        REQUESTS[family].format(tag=tag, ordinal="second" if source == "B" else "fourth", label=EXPECTED[kind[-1]]),
        "Parent return: the child CALL output. Execute exactly one child CALL after the supplied prelude.",
    ])


def _request(line):
    matches = []
    for family, template in REQUESTS.items():
        pattern = re.escape(template)
        for name, expression in (("tag", "[a-z]+"), ("ordinal", "second|fourth"), ("label", "L1|L2")):
            pattern = pattern.replace(re.escape("{" + name + "}"), f"(?P<{name}>{expression})")
        found = re.fullmatch(pattern, line)
        if found:
            matches.append((family, found.groupdict()))
    _require(len(matches) == 1, "CHILD_REQUEST_AMBIGUOUS_OR_UNSUPPORTED")
    return matches[0]


def _read_public(public):
    """Read public constraints only; never accept a task/target/seed/row ID."""
    codec.validate_public(public)
    check_public(public)
    _require(len({_payload(row["values"]) for row in public["observations"]}) == 3,
             "CHILD_OBSERVATIONS_FLOAT32_ALIASED")
    lines = public["problem"].splitlines()
    _require(len(lines) == 11 and lines[0] == "ONE-CHILD TASK / 8"
             and lines[1] == "Parent main input arg.", "CHILD_PUBLIC_FORMAT_INVALID")
    prelude = re.fullmatch(r"Prelude: A\(arg\)->(v\d+); B\(\1\)->(v\d+); C\(\2\)->(v\d+); R\(\3\)->(v\d+)\.", lines[2])
    output = re.fullmatch(r"CALL output: (v\d+)\.", lines[3])
    _require(prelude is not None and output is not None, "CHILD_PRELUDE_INVALID")
    names = (*prelude.groups(), output[1])
    _require(len(set(names)) == 5 and all(n in codec.VARIABLE_NAMES[1:] for n in names),
             "CHILD_PARENT_NAMES_INVALID")
    _require(lines[4] == "Available CALL inputs: " + ", ".join(["arg", *names[:4]]) + "."
             and lines[5] == "Available parent returns: " + ", ".join(["arg", *names]) + ".",
             "CHILD_FULL_PUBLIC_SCOPE_REQUIRED")
    kinds = {}
    for line in lines[6:8]:
        # Decode the actual declaration independently of _catalog_line. A
        # renderer error must not redefine what the public parser accepts.
        found = re.fullmatch(
            r"Child (?P<name>p\d+): C\(arg\)->(?P<first>v\d+); "
            r"(?:R\((?P=first)\)->(?P<second>v\d+); )?"
            r"RETURN (?P<returned>v\d+); authored result (?P<label>L[123])\.", line)
        _require(found is not None, "CHILD_CATALOG_INVALID")
        entry = found.groupdict()
        kind = "CR" if entry["second"] is not None else "C"
        last = entry["second"] or entry["first"]
        _require(entry["name"] in codec.PROCEDURE_NAMES[1:] and entry["first"] == "v0"
                 and (entry["second"] is None or entry["second"] == "v1")
                 and entry["returned"] == last and entry["label"] == EXPECTED[kind[-1]]
                 and kind not in kinds, "CHILD_CATALOG_INVALID")
        kinds[kind] = entry["name"]
    _require(set(kinds) == {"C", "CR"} and len(set(kinds.values())) == 2,
             "CHILD_BOTH_DISTINCT_CATALOG_ENTRIES_REQUIRED")
    _require(lines[8] == "Authored labels are fixture expectations if accepted, not new numerical meanings. All ordinary topology and Effect checks still apply."
             and lines[10] == "Parent return: the child CALL output. Execute exactly one child CALL after the supplied prelude.",
             "CHILD_SCOPE_OR_RETURN_CONTRACT_CHANGED")
    family, request = _request(lines[9])
    selected = [row["slot"] for row in public["observations"] if row["tag"] == request["tag"]]
    _require(len(selected) == 1, "CHILD_REQUEST_OBSERVATION_NOT_FOUND")
    # This branch resolves an authored label against BOTH public definitions,
    # not a hidden graph, task ID, generator seed, or records fixture.
    chosen_kind = next(kind for kind in kinds if EXPECTED[kind[-1]] == request["label"])
    return {"parent_names": names, "child_names": (kinds["C"], kinds["CR"]),
            "binding": selected[0], "source": "B" if request["ordinal"] == "second" else "R",
            "kind": chosen_kind, "family": family,
            "reverse_catalog": lines[6].startswith(f"Child {kinds['CR']}: ")}


def compile_candidate(public, choice):
    """Compile a predicted tuple; the public request does not prune alternatives.

    Full supported binding/input/return scope remains available to the frozen
    compiler. This function does not secretly replace a wrong choice with gold.
    """
    info = _read_public(public)
    return compile_choice(choice, parent_names=info["parent_names"], child_names=info["child_names"])


def candidate_choices(public):
    """Four B/R x C/CR controls, holding requested binding and return fixed.

    This is a development qualification panel, NOT a model's legality mask.
    The complete public input/return scope is larger than these four controls.
    """
    info = _read_public(public)
    names, children = info["parent_names"], info["child_names"]
    return [{"binding": info["binding"], "child": child, "input": source, "return": names[4]}
            for source in (names[1], names[3]) for child in children]


def parse_problem(public):
    """Independent public-only rule selector for the exact controlled language."""
    info = _read_public(public)
    names, children = info["parent_names"], info["child_names"]
    choice = {"binding": info["binding"], "child": children[info["kind"] == "CR"],
              "input": names[1 if info["source"] == "B" else 3], "return": names[4]}
    return compile_choice(choice, parent_names=names, child_names=children)


def _make_task(context, combination, split, group_id, index, evaluation_target):
    # Formal target FIRST. Neither parser nor a stored outcome supplies this.
    source, kind = combination.split("_")
    names, children = context["parent_names"], context["child_names"]
    target = compile_choice({"binding": context["binding"], "child": children[0 if kind == "C" else 1],
                             "input": names[1 if source == "B" else 3], "return": names[4]},
                            parent_names=names, child_names=children)
    public = {"problem": _render(context, combination, split), "observations": deepcopy(context["observations"])}
    task = {"schema": SCHEMA, "task_id": f"child-v8-{split}-{index:05d}", "public": public, "target": target,
            "provenance": {"split": split, "group_id": group_id, "combination": combination,
                "evaluation_target": evaluation_target, "wording_template": split,
                "graph_signature": graph_signature(target["program"]), "depth": 2,
                "target_source": "formal_public_constraints", "native_outcomes_checked": False}}
    validate_task(task)
    return task


def validate_task(task):
    _require(type(task) is dict and set(task) == {"schema", "task_id", "public", "target", "provenance"}
             and task["schema"] == SCHEMA, "CHILD_TASK_FIELDS_INVALID")
    _require(type(task["task_id"]) is str and re.fullmatch(r"child-v8-(train|validation|test|qualification)-\d{5}", task["task_id"]),
             "CHILD_TASK_ID_INVALID")
    target, provenance = task["target"], task["provenance"]
    _require(parse_problem(task["public"]) == target, "CHILD_PUBLIC_TARGET_MISMATCH")
    stats = validate_program(target["program"])
    plan = admit_action(task["public"], target)
    info = _read_public(task["public"])
    combination = info["source"] + "_" + info["kind"]
    _require(task["task_id"].startswith(f"child-v8-{info['family']}-"), "CHILD_TASK_ID_SPLIT_MISMATCH")
    _require(type(provenance) is dict and set(provenance) == {
        "split", "group_id", "combination", "evaluation_target", "wording_template", "graph_signature",
        "depth", "target_source", "native_outcomes_checked"}, "CHILD_PROVENANCE_FIELDS_INVALID")
    _require(provenance["split"] == provenance["wording_template"] == info["family"]
             and provenance["combination"] == combination
             and provenance["graph_signature"] == graph_signature(target["program"])
             and provenance["depth"] == stats["max_call_depth"] == 2
             and provenance["target_source"] == "formal_public_constraints"
             and provenance["native_outcomes_checked"] is False,
             "CHILD_PROVENANCE_MISMATCH")
    _require(type(provenance["group_id"]) is str and re.fullmatch(
        re.escape(info["family"]) + r"-group-\d{3}", provenance["group_id"]), "CHILD_GROUP_ID_INVALID")
    expected_target = ("development_native_qualification" if info["family"] == "qualification" else
                       "unseen_composition" if combination == HELD_OUT else "fresh_instances_familiar_graphs")
    _require(provenance["evaluation_target"] == expected_target, "CHILD_EVALUATION_TARGET_MISMATCH")
    _require(stats["expanded_run_count"] == len(plan["runs"]) == (5 if info["kind"] == "C" else 6),
             "CHILD_RUN_COUNT_CHANGED")
    _require(codec.ids_to_action(codec.action_to_ids(target, max_length=256), max_length=256) == target,
             "CHILD_ACTION_CODEC_MISMATCH")
    return task


def _context(rng, used_payloads, binding):
    names = tuple(rng.sample(codec.VARIABLE_NAMES[1:], 5))
    children = tuple(rng.sample(codec.PROCEDURE_NAMES[1:], 2))
    tags = rng.sample(TAGS, 3)
    observations = []
    for slot, tag in enumerate(tags):
        for _ in range(1000):
            values = [round(base / 10 + rng.uniform(-0.0004, 0.0004), 7) for base in range(1, 9)]
            key = _payload(values)
            if key not in used_payloads:
                used_payloads.add(key)
                break
        else:
            raise ValueError("CHILD_FRESH_INPUT_GENERATION_EXHAUSTED")
        observations.append({"slot": slot, "tag": tag, "values": values})
    rng.shuffle(observations)
    return {"parent_names": names, "child_names": children, "observations": observations,
            "binding": binding, "reverse_catalog": bool(rng.randrange(2))}


def qualification_tasks():
    """Four deterministic fresh development requests, binding 0 only.

    Shared observations support controlled comparisons; these are NOT train,
    validation, or final tasks. No native result is inferred from generation.
    """
    context = _context(random.Random(810240001), set(), 0)
    return [_make_task(context, combination, "qualification", "qualification-group-000", index,
                       "development_native_qualification") for index, combination in enumerate(COMBINATIONS)]


def generate_dataset(seed=2026090608):
    """Return an in-memory, checked package. No file writes or training launch."""
    _require(type(seed) is int and 0 <= seed < 2**63, "CHILD_SEED_INVALID")
    rng = random.Random(seed)
    # Never reuse the qualification payloads as training/final instances.
    used = {_payload(row["values"]) for task in qualification_tasks() for row in task["public"]["observations"]}
    splits = {}
    for split in ("train", "validation", "test"):
        tasks = []
        bindings = [index % 3 for index in range(GROUP_COUNTS[split])]
        rng.shuffle(bindings)
        for group_index, binding in enumerate(bindings):
            context = _context(rng, used, binding)
            combinations = FAMILIAR if split != "test" else (FAMILIAR[group_index % 3], HELD_OUT)
            for combination in combinations:
                tasks.append(_make_task(context, combination, split, f"{split}-group-{group_index:03d}", len(tasks),
                    "unseen_composition" if combination == HELD_OUT else "fresh_instances_familiar_graphs"))
        rng.shuffle(tasks)
        splits[split] = tasks
    result = {"schema": DATASET_SCHEMA, "seed": seed, "splits": splits}
    result["manifest"] = validate_dataset(result)
    return result


def validate_dataset(dataset):
    _require(type(dataset) is dict and set(dataset) in ({"schema", "seed", "splits"}, {"schema", "seed", "splits", "manifest"})
             and dataset["schema"] == DATASET_SCHEMA and type(dataset["seed"]) is int
             and 0 <= dataset["seed"] < 2**63 and type(dataset["splits"]) is dict
             and set(dataset["splits"]) == set(COUNTS), "CHILD_DATASET_INVALID")
    qualification_payloads = {_payload(row["values"]) for task in qualification_tasks() for row in task["public"]["observations"]}
    ids, public_hashes, owners, graph_by_combination, reports = set(), set(), {}, {}, {}
    for split, count in COUNTS.items():
        tasks = dataset["splits"][split]
        _require(type(tasks) is list and len(tasks) == count, "CHILD_SPLIT_COUNTS_CHANGED")
        groups, combos, bindings, depths, modes = {}, Counter(), Counter(), Counter(), Counter()
        for task in tasks:
            validate_task(task)
            provenance, public, target = task["provenance"], task["public"], task["target"]
            _require(provenance["split"] == split, "CHILD_SPLIT_LABEL_MISMATCH")
            _require(task["task_id"] not in ids and _digest(public) not in public_hashes, "CHILD_DUPLICATE_TASK_OR_PUBLIC")
            ids.add(task["task_id"])
            public_hashes.add(_digest(public))
            info = _read_public(public)
            context_key = _digest({"observations": public["observations"], "parent_names": info["parent_names"],
                "child_names": info["child_names"], "binding": info["binding"], "reverse_catalog": info["reverse_catalog"]})
            group = groups.setdefault(provenance["group_id"], {"context": context_key, "combinations": []})
            _require(group["context"] == context_key, "CHILD_GROUP_CONTEXT_CHANGED")
            combination = provenance["combination"]
            group["combinations"].append(combination)
            signature = graph_signature(target["program"])
            _require(graph_by_combination.setdefault(combination, signature) == signature, "CHILD_COMBINATION_GRAPH_CHANGED")
            combos[combination] += 1
            bindings[str(target["binding"])] += 1
            depths[str(provenance["depth"])] += 1
            modes[provenance["evaluation_target"]] += 1
            for row in public["observations"]:
                _require(all(abs(value - base/10) <= 0.00040001 for base, value in enumerate(row["values"], 1)),
                         "CHILD_INPUT_OUTSIDE_NARROW_PREPARATION_NEIGHBORHOOD")
                key, owner = _payload(row["values"]), (split, provenance["group_id"])
                _require(key not in qualification_payloads, "CHILD_QUALIFICATION_INPUT_REUSED")
                _require(owners.setdefault(key, owner) == owner, "CHILD_INPUT_CROSS_GROUP_OR_SPLIT_REUSE")
        _require(len(groups) == GROUP_COUNTS[split], "CHILD_GROUP_COUNT_CHANGED")
        expected = {cell: (64 if split == "train" else 24) for cell in FAMILIAR} if split != "test" else {
            **{cell: 8 for cell in FAMILIAR}, HELD_OUT: 24}
        _require(dict(combos) == expected, "CHILD_COMBINATION_DISTRIBUTION_CHANGED")
        for group in groups.values():
            cells = group["combinations"]
            _require(sorted(cells) == sorted(FAMILIAR) if split != "test" else
                     len(cells) == 2 and HELD_OUT in cells and len(set(cells) & set(FAMILIAR)) == 1,
                     "CHILD_CONTRAST_GROUP_INVALID")
        reports[split] = {"count": count, "independent_context_groups": len(groups),
            "combination_counts": dict(sorted(combos.items())), "binding_counts": dict(sorted(bindings.items())),
            "depth_counts": dict(depths), "evaluation_target_counts": dict(sorted(modes.items())),
            "public_sha256": _digest([task["public"] for task in tasks]), "private_tasks_sha256": _digest(tasks),
            "wording_template": split}
    _require(len(set(graph_by_combination.values())) == 4, "CHILD_STRUCTURAL_COMBINATIONS_ALIASED")
    result = {"schema": DATASET_SCHEMA, "seed": dataset["seed"], "splits": reports, "graph_signatures": graph_by_combination,
        "held_out_combination": HELD_OUT, "held_out_unseen_to": ["training", "validation"],
        "held_out_not_unseen_to": ["builder", "runtime_development_qualification"],
        "familiar_graph_overlap_intentional": True, "all_depths": [2], "calls_per_task": 1,
        "cross_split_float32_observation_overlap": False, "qualification_payloads_excluded": True,
        "contrast_variants_kept_in_group": True, "independent_observation_context_count": sum(GROUP_COUNTS.values()),
        "unique_float32_observation_payload_count": len(owners),
        "wording_templates_disjoint": True, "validation_unseen_combinations": False,
        "learned_choices": ["observation_binding", "child_selection", "child_input_source"],
        "parent_return": "fixed_child_call_output_not_a_varied_learning_target",
        "numeric_range": "each coordinate base/10 +/- 0.0004; native qualification is not implied for every new instance",
        "native_outcomes_checked": False, "training_allowed_by_this_package": False,
        "boundary": BOUNDARY}
    if "manifest" in dataset:
        _require(dataset["manifest"] == result, "CHILD_STORED_MANIFEST_MISMATCH")
    return result


def export_parts(dataset):
    """Return separately named public/private payloads without writing them."""
    manifest = validate_dataset(dataset)
    return {"train.json": deepcopy(dataset["splits"]["train"]),
            "validation.json": deepcopy(dataset["splits"]["validation"]),
            "test_public.json": [deepcopy(task["public"]) for task in dataset["splits"]["test"]],
            "test_private.json": deepcopy(dataset["splits"]["test"]), "manifest.json": deepcopy(manifest)}
