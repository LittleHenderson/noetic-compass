"""Bounded, paired curriculum revision over unchanged META2 IR and CJTs.

Construction validates structure, wording and coverage, not neural outcomes.
All future test predictions must be sealed before a learner opens private
targets. No model, new opcode, topology edge or general compiler is added.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import random
import re

from .codec import PROCEDURE_NAMES, action_to_tokens, validate_action, validate_public
from .curriculum import (TAGS, _render as _legacy_render, check_native_topology,
                         check_public, generate_dataset as _legacy_dataset,
                         graph_signature, parse_problem, permitted_view)
from .ir import SCHEMA as PROGRAM_SCHEMA, validate_program


SCHEMA = "cas-meta2-curriculum/2"
MANIFEST_SCHEMA = "cas-meta2-dataset-manifest/2"
DEFAULT_SEED = 20260917
DEFAULT_COUNTS = {"train": 768, "validation": 48, "test": 72}
GROUPS = ("same_depth", "wording_shift", "deeper_calls")
MAX_EXPANDED_RUNS = 15
MAX_ACTION_TOKENS = 256
LEGACY_DATASET_SEED = 20260906
HEX = re.compile(r"[0-9a-f]{64}\Z")
WORDING_COMBINATIONS = tuple(tuple(values) for values in product(range(3), repeat=4))


class CurriculumV2Error(ValueError):
    pass


def require(value, code):
    if not value:
        raise CurriculumV2Error(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _counts(counts):
    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    require(set(counts) == set(DEFAULT_COUNTS)
            and all(type(counts[key]) is int and 1 <= counts[key] <= DEFAULT_COUNTS[key] for key in counts),
            "INVALID_V2_SPLIT_COUNTS")
    require(counts["train"] >= 48 and counts["train"] % 8 == 0
            and counts["validation"] >= 6 and counts["validation"] % 3 == 0
            and counts["test"] >= 6 and counts["test"] % 3 == 0, "INVALID_V2_COUNT_PROPORTIONS")
    return counts


@lru_cache(maxsize=1)
def legacy_graph_signatures():
    """Only old structure hashes; no saved or future private file is opened."""
    old = _legacy_dataset(seed=LEGACY_DATASET_SEED)
    return frozenset(graph_signature(task["target"]["program"])
                     for tasks in old["splits"].values() for task in tasks)


def _exclusions(extra):
    require(extra is None or type(extra) in (set, frozenset), "EXCLUSIONS_MUST_BE_SET")
    extra = set() if extra is None else set(extra)
    require(all(type(value) is str and HEX.fullmatch(value) for value in extra), "INVALID_EXCLUDED_GRAPH_SIGNATURE")
    legacy = legacy_graph_signatures()
    combined = set(legacy) | extra
    return combined, {"legacy_constructor_seed": LEGACY_DATASET_SEED, "legacy_graph_count": len(legacy),
                      "additional_graph_count": len(extra), "additional_sha256": digest(sorted(extra)),
                      "count": len(combined), "sha256": digest(sorted(combined))}


def wording_combinations(remainder):
    require(type(remainder) is int and remainder in (0, 1, 2), "INVALID_WORDING_PARTITION")
    return tuple(values for values in WORDING_COMBINATIONS if sum(values) % 3 == remainder)


def render_problem(program, tag, combination):
    """Recombine existing surface forms; this renderer is not the rule parser."""
    require(type(combination) in (list, tuple) and len(combination) == 4
            and all(type(value) is int and value in (0, 1, 2) for value in combination), "INVALID_WORDING_COMBINATION")
    rendered = [_legacy_render(program, tag, family).splitlines() for family in range(3)]
    roles = [0]
    for procedure in program["procedures"].values():
        roles.extend([1] + [2] * len(procedure["steps"]) + [3])
    require(all(len(lines) == len(roles) for lines in rendered), "RENDERED_ROLE_COUNT_MISMATCH")
    return "\n".join(rendered[combination[role]][index] for index, role in enumerate(roles))


def _procedure():
    return {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [], "return": "arg"}


def _append(proc, kind, source, **fields):
    output = "v" + str(len(proc["steps"]))
    proc["steps"].append({"kind": kind, **fields, "input": source, "output": output})
    return output


def _self_work(procedure, rng):
    b_values = [_append(procedure, "RUN", "arg", cjt_id="B") for _ in range(rng.randint(1, 2))]
    c_values = [_append(procedure, "RUN", rng.choice(b_values), cjt_id="C") for _ in range(rng.randint(1, 2))]
    procedure["return"] = rng.choice(b_values + c_values)
    return b_values + c_values


def _names(rng, number, index):
    pool = list(PROCEDURE_NAMES[1:])
    anchor = pool[index % len(pool)]
    return [anchor] + rng.sample([name for name in pool if name != anchor], number - 1)


def _root(rng, count=None):
    main = _procedure()
    values = [_append(main, "RUN", "arg", cjt_id="A") for _ in range(rng.randint(1, 3) if count is None else count)]
    return {"schema": PROGRAM_SCHEMA, "entry": "main", "procedures": {"main": main}}, values


def _construct(rng, depth, index):
    # One ordinary flat task covers the highest locally emitted variable name
    # v8 positively; no future test-label inspection is used to select it.
    anchor = depth == 1 and index == 0
    program, a_values = _root(rng, 3 if anchor else None)
    procedures, main = program["procedures"], program["procedures"]["main"]
    if depth == 1:
        b_values = [_append(main, "RUN", rng.choice(a_values), cjt_id="B") for _ in range(3 if anchor else rng.randint(1, 3))]
        c_values = [_append(main, "RUN", rng.choice(b_values), cjt_id="C") for _ in range(3 if anchor else rng.randint(1, 3))]
        main["return"] = rng.choice(b_values + c_values)
    elif depth == 2:
        children = _names(rng, rng.randint(1, 3), index)
        for name in children:
            procedures[name] = _procedure()
            _self_work(procedures[name], rng)
        order = children + ([children[0]] if index % 4 == 0 else [])
        outputs = [_append(main, "CALL", rng.choice(a_values), procedure=name) for name in order]
        main["return"] = rng.choice(outputs)
    elif depth == 3:
        top, *leaves = _names(rng, rng.randint(2, 3), index)
        procedures[top] = _procedure()
        own_outputs = _self_work(procedures[top], rng)
        for name in leaves:
            procedures[name] = _procedure()
            _self_work(procedures[name], rng)
        order = leaves + ([leaves[0]] if index % 4 == 0 else [])
        calls = [_append(procedures[top], "CALL", "arg", procedure=name) for name in order]
        procedures[top]["return"] = rng.choice(own_outputs + calls)
        main["return"] = _append(main, "CALL", rng.choice(a_values), procedure=top)
    else:
        raise CurriculumV2Error("UNSUPPORTED_TRAINING_DEPTH")
    _target_stats({"program": program, "binding": 0})
    return program


def _paired_programs(rng, index):
    """Move a nonempty second child under the first: depth 3 becomes 4.

    All three child frames run B/C work on the same earlier A argument. The
    ordered RUN operations, their actual input dependencies, and final selected
    RUN remain identical. Only the call/return nesting changes.
    """
    shallow, a_values = _root(rng)
    top, first, second = _names(rng, 3, index)
    for name in (top, first, second):
        shallow["procedures"][name] = _procedure()
        _self_work(shallow["procedures"][name], rng)
    deep = deepcopy(shallow)
    for program in (shallow, deep):
        program["procedures"]["main"]["return"] = _append(
            program["procedures"]["main"], "CALL", a_values[index % len(a_values)], procedure=top)
    _append(shallow["procedures"][top], "CALL", "arg", procedure=first)
    shallow["procedures"][top]["return"] = _append(shallow["procedures"][top], "CALL", "arg", procedure=second)
    deep["procedures"][top]["return"] = _append(deep["procedures"][top], "CALL", "arg", procedure=first)
    deep["procedures"][first]["return"] = _append(deep["procedures"][first], "CALL", "arg", procedure=second)
    _target_stats({"program": shallow, "binding": 0})
    _target_stats({"program": deep, "binding": 0})
    require(_native_work(shallow) == _native_work(deep), "PAIRED_NATIVE_WORK_MISMATCH")
    return shallow, deep


def _native_work(program):
    plan = check_native_topology(program)
    return {"runs": [{key: row[key] for key in ("cjt_id", "input_node")} for row in plan["runs"]],
            "return_node": plan["return_node"]}


def _target_stats(action):
    validate_action(action)
    stats = validate_program(action["program"])
    plan = check_native_topology(action["program"])
    require(stats["expanded_run_count"] <= MAX_EXPANDED_RUNS, "V2_NATIVE_RUN_CEILING")
    require(all(any(step["kind"] == "RUN" for step in procedure["steps"])
                for procedure in action["program"]["procedures"].values()), "EMPTY_WRAPPER_PROCEDURE_FORBIDDEN")
    require(all(procedure["allowed_cjts"] == ["A", "B", "C"]
                for procedure in action["program"]["procedures"].values()), "V2_TARGET_SCOPE_MUST_STAY_ABC")
    require(all(row["cjt_id"] in ("A", "B", "C") for row in plan["runs"]), "NEW_NATIVE_NODE_FORBIDDEN")
    require(all(event["output_node"] >= 0 for event in plan["events"] if event["kind"] == "RETURN"), "RAW_INPUT_RETURN_FORBIDDEN")
    stats["action_tokens"] = len(action_to_tokens(action, max_length=MAX_ACTION_TOKENS))
    return stats


def _validate_pair(shallow, deep):
    require(set(shallow["procedures"]) == set(deep["procedures"]), "V2_PAIRED_PROCEDURE_SET_MISMATCH")
    first_stats = _target_stats({"program": shallow, "binding": 0})
    second_stats = _target_stats({"program": deep, "binding": 0})
    require(all(first_stats[key] == second_stats[key] for key in (
        "procedure_count", "instruction_count", "expanded_instruction_count", "expanded_run_count", "action_tokens")),
        "V2_PAIRED_WORK_SIZE_MISMATCH")
    for name in shallow["procedures"]:
        require([step for step in shallow["procedures"][name]["steps"] if step["kind"] == "RUN"]
                == [step for step in deep["procedures"][name]["steps"] if step["kind"] == "RUN"],
                "V2_PAIRED_PROCEDURE_WORK_CHANGED")
    require(_native_work(shallow) == _native_work(deep), "V2_PAIRED_NATIVE_WORK_MISMATCH")


def _observations(rng, seen):
    tags, observations = rng.sample(TAGS, 3), []
    for slot, tag in enumerate(tags):
        for _ in range(1000):
            values = [round(base / 10 + rng.uniform(-0.0004, 0.0004), 7) for base in range(1, 9)]
            if tuple(values) not in seen:
                seen.add(tuple(values))
                observations.append({"slot": slot, "tag": tag, "values": values})
                break
        else:
            raise CurriculumV2Error("UNIQUE_OBSERVATION_GENERATION_EXHAUSTED")
    return observations


def _task(program, observations, binding, combination, task_id, group, triplet=None):
    tag = next(row["tag"] for row in observations if row["slot"] == binding)
    public = {"problem": render_problem(program, tag, combination), "observations": deepcopy(observations)}
    action = {"program": deepcopy(program), "binding": binding}
    require(parse_problem(public) == action, "RECOMBINED_WORDING_MEANING_MISMATCH")
    return {"task_id": task_id, "public": public, "target": action,
            "provenance": {"graph_signature": graph_signature(program), "depth": validate_program(program)["max_call_depth"],
                           "evaluation_group": group, "triplet_id": triplet, "wording_combination": list(combination)}}


def generate_dataset(seed=DEFAULT_SEED, counts=None, excluded_graph_signatures=None):
    counts = _counts(counts)
    require(type(seed) is int and 0 <= seed < 2**63, "INVALID_V2_SEED")
    excluded, _ = _exclusions(excluded_graph_signatures)
    rng, graphs, observations_seen, splits = random.Random(seed), set(excluded), set(), {}
    train_depths = [1] * (counts["train"] // 4) + [2] * (counts["train"] * 3 // 8) + [3] * (counts["train"] * 3 // 8)
    validation_depths = [depth for depth in (1, 2, 3) for _ in range(counts["validation"] // 3)]
    for split, depths, remainder, group in (("train", train_depths, 0, "training"),
                                            ("validation", validation_depths, 2, "validation")):
        tasks = []
        combinations = wording_combinations(remainder)
        for index, depth in enumerate(depths):
            for _ in range(10000):
                try:
                    program = _construct(rng, depth, index)
                except CurriculumV2Error as error:
                    if str(error) == "V2_NATIVE_RUN_CEILING":
                        continue
                    raise
                signature = graph_signature(program)
                if signature not in graphs:
                    graphs.add(signature)
                    break
            else:
                raise CurriculumV2Error("V2_GRAPH_GENERATION_EXHAUSTED")
            observations = _observations(rng, observations_seen)
            tasks.append(_task(program, observations, index % 3, combinations[index % len(combinations)],
                               f"meta2-v2-{split}-{index:05d}", group))
        rng.shuffle(tasks)
        splits[split] = tasks
    testing = []
    known, shifted = wording_combinations(0), wording_combinations(1)
    for index in range(counts["test"] // 3):
        for _ in range(10000):
            shallow, deep = _paired_programs(rng, index)
            signatures = {graph_signature(shallow), graph_signature(deep)}
            if len(signatures) == 2 and not signatures & graphs:
                graphs.update(signatures)
                break
        else:
            raise CurriculumV2Error("V2_PAIRED_GRAPH_GENERATION_EXHAUSTED")
        observations = _observations(rng, observations_seen)
        triplet = f"triplet-{index:04d}"
        for group, program, combination in (("same_depth", shallow, known[index % len(known)]),
                                           ("wording_shift", shallow, shifted[index % len(shifted)]),
                                           ("deeper_calls", deep, known[index % len(known)])):
            testing.append(_task(program, observations, index % 3, combination,
                                 f"meta2-v2-test-{triplet}-{group}", group, triplet))
    rng.shuffle(testing)
    splits["test"] = testing
    result = {"schema": SCHEMA, "seed": seed, "splits": splits}
    result["manifest"] = validate_dataset(result, excluded_graph_signatures=excluded_graph_signatures)
    return result


def _coverage(tasks):
    declarations, targets, instructions = Counter(), Counter(), Counter()
    sentences = {name: Counter() for name in ("start", "declaration", "RUN", "CALL", "RETURN")}
    child_calls, child_programs, earlier_inputs, earlier_returns, repeated_calls = 0, 0, 0, 0, 0
    for task in tasks:
        program, child = task["target"]["program"], False
        combination = task["provenance"]["wording_combination"]
        sentences["start"][str(combination[0])] += 1
        all_callees = Counter()
        for name, procedure in program["procedures"].items():
            declarations[name] += 1
            sentences["declaration"][str(combination[1])] += 1
            sentences["RETURN"][str(combination[3])] += 1
            values = ["arg"]
            instructions["RETURN"] += 1
            for step in procedure["steps"]:
                instructions[step["kind"]] += 1
                sentences[step["kind"]][str(combination[2])] += 1
                earlier_inputs += step["input"] != values[-1]
                values.append(step["output"])
                if step["kind"] == "CALL":
                    targets[step["procedure"]] += 1
                    all_callees[step["procedure"]] += 1
                    if name != "main":
                        child_calls += 1
                        child = True
            earlier_returns += procedure["return"] != values[-1]
        repeated_calls += sum(max(0, count - 1) for count in all_callees.values())
        child_programs += child
    return {"procedure_declarations": dict(sorted(declarations.items())), "procedure_call_targets": dict(sorted(targets.items())),
            "instructions": dict(sorted(instructions.items())), "calls_from_child_procedures": child_calls,
            "programs_with_child_calls": child_programs, "earlier_value_inputs": earlier_inputs,
            "earlier_value_returns": earlier_returns, "repeated_callee_uses": repeated_calls,
            "sentence_primitives": {name: dict(sorted(counts.items())) for name, counts in sentences.items()}}


def validate_dataset(dataset, excluded_graph_signatures=None):
    require(type(dataset) is dict and dataset.get("schema") == SCHEMA
            and set(dataset.get("splits", {})) == set(DEFAULT_COUNTS)
            and type(dataset.get("seed")) is int and 0 <= dataset["seed"] < 2**63, "INVALID_V2_DATASET")
    splits = dataset["splits"]
    require(all(type(tasks) is list for tasks in splits.values()), "INVALID_V2_PARTITION")
    counts = _counts({split: len(tasks) for split, tasks in splits.items()})
    excluded, exclusion_receipt = _exclusions(excluded_graph_signatures)
    ids, graph_owners, input_owners, report, triplets = set(), {}, {}, {}, {}
    token_counts = {}
    for split in ("train", "validation", "test"):
        depth_counts, groups, bindings = Counter(), Counter(), [0, 0, 0]
        token_counts[split] = Counter()
        max_runs, max_tokens, max_chars = 0, 0, 0
        for task in splits[split]:
            require(type(task) is dict and set(task) == {"task_id", "public", "target", "provenance"}, "INVALID_V2_TASK_FIELDS")
            require(type(task["task_id"]) is str and task["task_id"] not in ids, "DUPLICATE_V2_TASK_ID")
            ids.add(task["task_id"])
            public, action, provenance = task["public"], task["target"], task["provenance"]
            check_public(public)
            validate_public(public)
            stats = _target_stats(action)
            token_counts[split].update(action_to_tokens(action, max_length=MAX_ACTION_TOKENS))
            signature = graph_signature(action["program"])
            require(signature not in excluded, "OLD_GRAPH_REUSED")
            require(type(provenance) is dict and set(provenance) == {
                "graph_signature", "depth", "evaluation_group", "triplet_id", "wording_combination"}, "INVALID_V2_PROVENANCE")
            group, triplet, combination = provenance["evaluation_group"], provenance["triplet_id"], provenance["wording_combination"]
            require(provenance["graph_signature"] == signature and type(provenance["depth"]) is int
                    and provenance["depth"] == stats["max_call_depth"], "V2_GRAPH_OR_DEPTH_PROVENANCE_MISMATCH")
            if split == "test":
                require(group in GROUPS and type(triplet) is str and re.fullmatch(r"triplet-\d{4}", triplet), "INVALID_V2_TEST_GROUP")
                require(stats["max_call_depth"] == (4 if group == "deeper_calls" else 3), "V2_TEST_DEPTH_MISMATCH")
                remainder = 1 if group == "wording_shift" else 0
                require(group not in triplets.setdefault(triplet, {}), "DUPLICATE_TRIPLET_GROUP")
                triplets[triplet][group] = task
            else:
                require(group == ("training" if split == "train" else "validation") and triplet is None,
                        "INVALID_V2_DEVELOPMENT_GROUP")
                remainder = 0 if split == "train" else 2
            require(type(combination) is list and tuple(combination) in wording_combinations(remainder), "V2_WORDING_PARTITION_MISMATCH")
            tag = next(row["tag"] for row in public["observations"] if row["slot"] == action["binding"])
            require(public["problem"] == render_problem(action["program"], tag, combination)
                    and parse_problem(public) == action, "V2_ACTUAL_WORDING_OR_MEANING_MISMATCH")
            owner = (split, triplet, group)
            if signature in graph_owners:
                previous = graph_owners[signature]
                require(split == previous[0] == "test" and triplet == previous[1]
                        and {group, previous[2]} == {"same_depth", "wording_shift"}, "V2_GRAPH_OVERLAP_NOT_PERMITTED")
            else:
                graph_owners[signature] = owner
            for observation in public["observations"]:
                values = tuple(observation["values"])
                if values in input_owners:
                    previous = input_owners[values]
                    require(split == previous[0] == "test" and triplet == previous[1]
                            and observation == previous[2], "V2_INPUT_OVERLAP_NOT_PERMITTED")
                else:
                    input_owners[values] = (split, triplet, observation)
            depth_counts[stats["max_call_depth"]] += 1
            groups[group] += 1
            bindings[action["binding"]] += 1
            max_runs, max_tokens = max(max_runs, stats["expanded_run_count"]), max(max_tokens, stats["action_tokens"])
            max_chars = max(max_chars, len(public["problem"]))
        report[split] = {"count": len(splits[split]), "sha256": digest(splits[split]),
            "depth_counts": {str(key): value for key, value in sorted(depth_counts.items())},
            "evaluation_groups": dict(sorted(groups.items())),
            "max_expanded_runs": max_runs, "max_action_tokens": max_tokens, "max_public_characters": max_chars}
        if split == "train":
            report[split]["binding_counts"] = bindings
    require(report["train"]["depth_counts"] == {"1": counts["train"] // 4, "2": counts["train"] * 3 // 8, "3": counts["train"] * 3 // 8}
            and report["validation"]["depth_counts"] == {str(depth): counts["validation"] // 3 for depth in (1, 2, 3)},
            "V2_DEVELOPMENT_DEPTH_PROPORTIONS_MISMATCH")
    require(len(triplets) == counts["test"] // 3 and report["test"]["evaluation_groups"] == {
        group: counts["test"] // 3 for group in GROUPS}, "V2_TRIPLET_COUNTS_MISMATCH")
    for triplet in triplets.values():
        require(set(triplet) == set(GROUPS), "V2_TRIPLET_INCOMPLETE")
        same, wording, deep = (triplet[group] for group in GROUPS)
        require(same["target"] == wording["target"] and same["public"]["observations"] == wording["public"]["observations"] == deep["public"]["observations"]
                and same["target"]["binding"] == deep["target"]["binding"], "V2_PAIRED_INPUT_OR_TARGET_MISMATCH")
        require(same["provenance"]["wording_combination"] == deep["provenance"]["wording_combination"]
                and same["public"]["problem"] != wording["public"]["problem"], "V2_PAIRED_WORDING_MISMATCH")
        _validate_pair(same["target"]["program"], deep["target"]["program"])
    coverage = _coverage(splits["train"])
    missing_target_tokens = {split: sorted(set(token_counts[split]) - set(token_counts["train"]))
                             for split in ("validation", "test")}
    require(not any(missing_target_tokens.values()), "V2_UNSEEN_POSITIVE_TARGET_TOKEN")
    missing_sentence_primitives = [name + ":" + str(family) for name, values in coverage["sentence_primitives"].items()
                                   for family in range(3) if values.get(str(family), 0) <= 0]
    require(not missing_sentence_primitives, "V2_SENTENCE_PRIMITIVE_TRAINING_GAP")
    require(all(coverage["procedure_declarations"].get(name, 0) > 0 and coverage["procedure_call_targets"].get(name, 0) > 0
                for name in PROCEDURE_NAMES[1:]), "V2_PROCEDURE_IDENTITY_TRAINING_GAP")
    require(coverage["programs_with_child_calls"] == counts["train"] * 3 // 8
            and all(coverage["instructions"].get(name, 0) > 0 for name in ("RUN", "CALL", "RETURN"))
            and all(coverage[key] > 0 for key in ("earlier_value_inputs", "earlier_value_returns", "repeated_callee_uses")),
            "V2_CONTROL_PRIMITIVE_TRAINING_GAP")
    return {"schema": MANIFEST_SCHEMA, "seed": dataset["seed"], "counts": counts, "splits": report,
        "evaluation_group_counts": {group: counts["test"] // 3 for group in GROUPS}, "triplets": len(triplets),
        "training_coverage": coverage, "exclusions": exclusion_receipt,
        "positive_target_token_coverage": {"training_counts": dict(sorted(token_counts["train"].items())),
            "validation_tokens_covered": True, "test_tokens_covered": True,
            "missing_validation_tokens": missing_target_tokens["validation"], "missing_test_tokens": missing_target_tokens["test"]},
        "missing_training_sentence_primitives": missing_sentence_primitives,
        "graph_sets_disjoint_across_splits": True, "input_instances_disjoint_across_splits": True,
        "duplicate_exceptions": {"test_graph_reuse": "Only same_depth/wording_shift within one triplet.",
                                 "test_input_reuse": "Only the three members of one matched triplet."},
        "wording_partitions": {"train_and_same_depth": 0, "test_wording_shift": 1, "validation": 2,
                               "rule": "Sum of four existing sentence-family IDs modulo 3."},
        "every_procedure_has_native_run": True, "deeper_pairs_preserve_native_work": True,
        "max_expanded_runs": MAX_EXPANDED_RUNS, "max_action_tokens": MAX_ACTION_TOKENS,
        "native_outcomes_checked": False, "training_or_neural_execution_performed": False,
        "boundary": "Pure curriculum construction only. Same unchanged A→B→C native topology, IR and codec. "
                    "Depth includes entry. Native task/output correctness still requires AWS evaluation after all predictions seal."}


def validate_manifest(manifest, expected_counts=None):
    """Check public metadata only; does not read a private partition or prove it."""
    expected = _counts(DEFAULT_COUNTS if expected_counts is None else expected_counts)
    require(type(manifest) is dict and manifest.get("schema") == MANIFEST_SCHEMA
            and manifest.get("counts") == expected and type(manifest.get("seed")) is int, "INVALID_V2_PUBLIC_MANIFEST")
    require(set(manifest.get("sha256", {})) == {"train.json", "validation.json", "test_public.json", "test_private.json"}
            and all(type(value) is str and HEX.fullmatch(value) for value in manifest["sha256"].values()), "INVALID_V2_PARTITION_HASHES")
    require(manifest.get("evaluation_group_counts") == {group: expected["test"] // 3 for group in GROUPS}
            and manifest.get("triplets") == expected["test"] // 3
            and manifest.get("graph_sets_disjoint_across_splits") is True
            and manifest.get("input_instances_disjoint_across_splits") is True
            and manifest.get("every_procedure_has_native_run") is True
            and manifest.get("deeper_pairs_preserve_native_work") is True, "V2_MANIFEST_COVERAGE_MISMATCH")
    require(all(manifest.get("splits", {}).get(split, {}).get("count") == count for split, count in expected.items()), "V2_MANIFEST_SPLIT_COUNT_MISMATCH")
    require(all("binding_counts" not in manifest["splits"][split] for split in ("validation", "test")),
            "V2_PUBLIC_HELD_OUT_BINDING_COUNTS_FORBIDDEN")
    coverage = manifest.get("training_coverage", {})
    tokens = manifest.get("positive_target_token_coverage", {})
    require(type(tokens) is dict and set(tokens) == {"training_counts", "validation_tokens_covered",
            "test_tokens_covered", "missing_validation_tokens", "missing_test_tokens"},
            "V2_PUBLIC_TARGET_COVERAGE_FIELDS_INVALID")
    require(tokens.get("validation_tokens_covered") is True and tokens.get("test_tokens_covered") is True
            and tokens.get("missing_validation_tokens") == tokens.get("missing_test_tokens") == []
            and manifest.get("missing_training_sentence_primitives") == []
            and all(coverage.get("procedure_declarations", {}).get(name, 0) > 0
                    and coverage.get("procedure_call_targets", {}).get(name, 0) > 0 for name in PROCEDURE_NAMES[1:])
            and coverage.get("programs_with_child_calls") == expected["train"] * 3 // 8,
            "V2_MANIFEST_POSITIVE_TRAINING_COVERAGE_MISSING")
    require(all(coverage.get("sentence_primitives", {}).get(role, {}).get(str(family), 0) > 0
                for role in ("start", "declaration", "RUN", "CALL", "RETURN") for family in range(3)),
            "V2_MANIFEST_SENTENCE_COVERAGE_MISSING")
    require(manifest.get("native_outcomes_checked") is False
            and manifest.get("training_or_neural_execution_performed") is False, "V2_CONSTRUCTION_MUST_NOT_CLAIM_NEURAL_RESULTS")
    return {"schema": MANIFEST_SCHEMA, "counts": dict(expected), "sha256": dict(manifest["sha256"]),
            "private_partition_opened": False, "boundary": "Manifest shape/count/hash checks only; full constructor validation is separately bound."}


def write_dataset(output, seed=DEFAULT_SEED, counts=None, excluded_graph_signatures=None):
    dataset = generate_dataset(seed, counts, excluded_graph_signatures)
    path = Path(output)
    require(not path.exists(), "V2_DATASET_OUTPUT_MUST_BE_NEW")
    path.mkdir(parents=True, exist_ok=False)
    files = {"train.json": dataset["splits"]["train"], "validation.json": dataset["splits"]["validation"],
             "test_public.json": [permitted_view(task) for task in dataset["splits"]["test"]],
             "test_private.json": dataset["splits"]["test"]}
    hashes = {}
    for name, value in files.items():
        payload = canonical(value) + b"\n"
        with (path / name).open("xb") as stream:
            stream.write(payload)
        hashes[name] = sha256(payload).hexdigest()
    manifest = {**dataset["manifest"], "sha256": hashes}
    validate_manifest(manifest, dataset["manifest"]["counts"])
    with (path / "dataset_manifest.json").open("xb") as stream:
        stream.write(canonical(manifest) + b"\n")
    return manifest
