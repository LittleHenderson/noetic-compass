"""Pure preparation of one-child-call alternatives under unchanged native rules.

No model, tensor, native execution, task labels, learning, or provider calls.
The proposed B-versus-R input contrast remains a CUDA construction gate.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import time

from . import codec, grammar_v3
from .curriculum import check_native_topology, graph_signature
from .ir import SCHEMA as PROGRAM_SCHEMA, validate_program
from .native import EXPECTED, admit_action

SCHEMA = "cas-meta2-one-child-scaffold-preparation/8"
PARENT_NAMES = ("v0", "v1", "v2", "v3", "v4")
CHILD_NAMES = ("p0", "p1")
ROOT = Path(__file__).resolve().parents[1]
PREPARATION_ROOT = ROOT / "records/child_call_v8_preparation_002"
SOURCE_PINS = {
    "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py": "5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187",
    "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py": "c1604059580a553e131233ecdbb5b1de8439edbba03865f7985a71b0dfdfb736",
    "CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py": "0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735",
    "CAS_META_2_COMPOSITION/cas_meta2/native.py": "16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512",
}
BOUNDARY = "Pure structural enumeration only. Native acceptance, numerical contrast, task correctness, and learned skill are UNEXECUTED."


def require(value, code):
    if not value:
        raise ValueError(code)


def _names(parent_names, child_names):
    require(type(parent_names) in (tuple, list) and len(parent_names) == 5
            and len(set(parent_names)) == 5 and all(n in codec.VARIABLE_NAMES[1:] for n in parent_names),
            "SCAFFOLD_FIVE_DISTINCT_SUPPORTED_PARENT_NAMES_REQUIRED")
    require(type(child_names) in (tuple, list) and len(child_names) == 2
            and len(set(child_names)) == 2 and all(n in codec.PROCEDURE_NAMES[1:] for n in child_names),
            "SCAFFOLD_TWO_DISTINCT_SUPPORTED_CHILD_NAMES_REQUIRED")
    return tuple(parent_names), tuple(child_names)


def _run(cjt, source, output):
    return {"kind": "RUN", "cjt_id": cjt, "input": source, "output": output}


def _procedure(steps, returned):
    return {"input": "arg", "allowed_cjts": ["A", "B", "C", "R"],
            "steps": deepcopy(steps), "return": returned}


def child_catalog(child_names=CHILD_NAMES):
    _, child_names = _names(PARENT_NAMES, child_names)
    # Different executed CJT sequences and result producers; not renamed clones.
    return {child_names[0]: _procedure([_run("C", "arg", "v0")], "v0"),
            child_names[1]: _procedure([_run("C", "arg", "v0"), _run("R", "v0", "v1")], "v1")}


def _prelude(names):
    return [_run("A", "arg", names[0]), _run("B", names[0], names[1]),
            _run("C", names[1], names[2]), _run("R", names[2], names[3])]


def development_scaffold(*, observations=None, parent_names=PARENT_NAMES, child_names=CHILD_NAMES):
    """Public catalog/skeleton, not a task with a hidden chosen program."""
    names, children = _names(parent_names, child_names)
    if observations is None:
        observations = [{"slot": slot, "tag": tag,
                         "values": [round(n/10 + slot/10000, 4) for n in range(1, 9)]}
                        for slot, tag in enumerate(("copper", "amber", "cobalt"))]
    catalog = child_catalog(children)
    scope = ["arg", *names[:4]]
    returns = ["arg", *names]
    prelude = _prelude(names)
    text = ("DEVELOPMENT CONSTRUCTION CHECK; no requested solution or answer is supplied. "
            "Given one selected observation as arg, the supplied parent performs "
            + json.dumps(prelude, sort_keys=True) + ". Then exactly one CALL stores its result in "
            + names[4] + ". Public child catalog: " + json.dumps(catalog, sort_keys=True)
            + ". Choose a child from " + json.dumps(list(children))
            + ", its input from the full scope " + json.dumps(scope)
            + ", and the parent's return from the full scope " + json.dumps(returns)
            + ". Topology and accepted-Effect checks apply equally to every choice.")
    public = {"problem": text, "observations": deepcopy(observations)}
    codec.validate_public(public)
    # Reuse admission's exact public-byte checks with a fixed legal structural
    # control. This executes no CJT and does not choose a task's correct answer.
    admit_action(public, compile_choice({"binding": 0, "child": children[0],
        "input": names[1], "return": names[4]}, parent_names=names, child_names=children))
    return {"schema": SCHEMA, "public": public, "catalog": catalog,
            "parent_prelude": prelude, "call_output": names[4],
            "choice_spaces": {"binding": [0, 1, 2], "child": list(children),
                              "input": scope, "return": returns},
            "input_producers": {"arg": None, **dict(zip(names[:4], ("A", "B", "C", "R"), strict=True))},
            "has_gold_target": False, "boundary": BOUNDARY}


def compile_choice(choice, *, parent_names=PARENT_NAMES, child_names=CHILD_NAMES):
    """Compile predicted choices only; include exactly the selected child.

    This stage checks membership, codec and IR. Native-topology/ref-return
    rejections are intentionally retained for the enumeration's next stage.
    """
    names, children = _names(parent_names, child_names)
    require(type(choice) is dict and set(choice) == {"binding", "child", "input", "return"},
            "SCAFFOLD_CHOICE_FIELDS_INVALID")
    require(type(choice["binding"]) is int and choice["binding"] in (0, 1, 2), "SCAFFOLD_BINDING_INVALID")
    require(choice["child"] in children and choice["input"] in ("arg", *names[:4])
            and choice["return"] in ("arg", *names), "SCAFFOLD_CHOICE_OUTSIDE_PUBLIC_SCOPE")
    call = {"kind": "CALL", "procedure": choice["child"], "input": choice["input"], "output": names[4]}
    program = {"schema": PROGRAM_SCHEMA, "entry": "main", "procedures": {
        "main": _procedure([*_prelude(names), call], choice["return"]),
        choice["child"]: child_catalog(children)[choice["child"]]}}
    action = {"binding": choice["binding"], "program": program}
    validate_program(program)
    codec.validate_action(action)
    return action


def _source_identity():
    for relative, expected in SOURCE_PINS.items():
        path = ROOT.parent / relative
        require(path.is_file() and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                           for p in (path, *path.parents))
                and sha256(path.read_bytes()).hexdigest() == expected,
                "SCAFFOLD_ACCEPTED_SOURCE_CHANGED:" + relative)
    return dict(SOURCE_PINS)


def enumerate_candidates(*, observations=None, parent_names=PARENT_NAMES, child_names=CHILD_NAMES):
    """Enumerate all 180 choices; no semantic answer filters or native calls."""
    names, children = _names(parent_names, child_names)
    sources = _source_identity()
    scaffold = development_scaffold(observations=observations, parent_names=names, child_names=children)
    space = scaffold["choice_spaces"]
    rows = []
    for values in product(*(space[k] for k in ("binding", "child", "input", "return"))):
        choice = dict(zip(("binding", "child", "input", "return"), values, strict=True))
        action = compile_choice(choice, parent_names=names, child_names=children)
        ir = validate_program(action["program"])
        ids = codec.action_to_ids(action, max_length=256)
        require(codec.ids_to_action(ids, max_length=256) == action, "SCAFFOLD_CODEC_ROUNDTRIP_FAILED")
        grammar = grammar_v3.GrammarState(max_length=256)
        for token in ids:
            grammar = grammar.advance_id(token)
        require(grammar.complete and grammar.to_action() == action, "SCAFFOLD_GRAMMAR_PATH_FAILED")
        row = {"choice": choice, "action": action, "action_sha256": codec.canonical_sha256(action),
               "token_count": len(ids), "ir": ir, "codec_and_complete_grammar": True,
               "input_producer": scaffold["input_producers"][choice["input"]],
               "native_execution": "UNEXECUTED", "actual_input_tensor_sha256": None,
               "actual_output_tensor_sha256": None, "actual_semantic_content": None,
               "actual_compute_plan_units": None, "native_verifier_result": None}
        try:
            topology = check_native_topology(action["program"])
        except ValueError as error:
            row.update(status="TOPOLOGY_REJECTED", reason=str(error), topology=None, graph_signature=None)
        else:
            row.update(topology=topology, graph_signature=graph_signature(action["program"]))
            try:
                admitted = admit_action(scaffold["public"], action)
            except ValueError as error:
                row.update(status="RETURN_OR_PUBLIC_ADMISSION_REJECTED", reason=str(error))
            else:
                require(admitted == topology, "SCAFFOLD_NATIVE_ADMISSION_PLAN_DIFFERS")
                row.update(status="PURE_ADMISSION_PASSED", reason=None)
        rows.append(row)
    indexed = {(r["choice"]["binding"], r["choice"]["child"], r["choice"]["input"], r["choice"]["return"]): r for r in rows}
    pairs = []
    for binding, child in product(space["binding"], space["child"]):
        left, right = [indexed[(binding, child, source, names[4])] for source in (names[1], names[3])]
        require(left["status"] == right["status"] == "PURE_ADMISSION_PASSED", "SCAFFOLD_PAIR_NOT_ADMITTED")
        require(left["graph_signature"] != right["graph_signature"]
                and left["topology"]["runs"][4]["input_node"] == 1
                and right["topology"]["runs"][4]["input_node"] == 3,
                "SCAFFOLD_PAIR_MUST_CHANGE_DATAFLOW_NOT_SPELLING")
        a, b = deepcopy(left["action"]), deepcopy(right["action"])
        a["program"]["procedures"]["main"]["steps"][4]["input"] = b["program"]["procedures"]["main"]["steps"][4]["input"]
        require(a == b, "SCAFFOLD_UNCONTROLLED_PAIR_DIFFERENCE")
        pairs.append({"binding": binding, "child": child, "parent_return": names[4],
                      "left_action_sha256": left["action_sha256"], "right_action_sha256": right["action_sha256"],
                      "left_input": {"variable": names[1], "producer": "B", "run_node": 1},
                      "right_input": {"variable": names[3], "producer": "R", "run_node": 3},
                      "first_child_run": {"cjt_id": "C", "run_node": 4},
                      "only_call_input_changed": True, "different_renaming_independent_graphs": True,
                      "expected_preparation_symbols_if_ACCEPT": {"B": EXPECTED["B"], "R": EXPECTED["R"]},
                      "actual_semantic_or_numeric_discrimination": "UNEXECUTED"})
    counts = dict(Counter(r["status"] for r in rows))
    require(len(rows) == 180 and len(pairs) == 6, "SCAFFOLD_ENUMERATION_COVERAGE_CHANGED")
    require(counts == {"PURE_ADMISSION_PASSED": 90, "TOPOLOGY_REJECTED": 72,
                       "RETURN_OR_PUBLIC_ADMISSION_REJECTED": 18}, "SCAFFOLD_ADMISSION_COUNTS_CHANGED")
    require(_source_identity() == sources, "SCAFFOLD_SOURCE_CHANGED_DURING_ENUMERATION")
    return {"schema": SCHEMA, "status": "PURE_ENUMERATION_PREPARED_NATIVE_GATE_OPEN", "scaffold": scaffold,
            "source_sha256": sources, "candidate_count": len(rows), "counts": counts,
            "per_child_full_input_scope": space["input"],
            "topology_eligible_inputs_each_child": ["arg", names[1], names[3]],
            "topology_rejected_inputs_each_child": [names[0], names[2]],
            "published_effect_return_choices": list(names), "rejected_observation_return": "arg",
            "candidate_rows": rows, "controlled_input_pairs": pairs,
            "distinct_public_child_sequences": {children[0]: ["C"], children[1]: ["C", "R"]},
            "static_action_token_range": [min(r["token_count"] for r in rows), max(r["token_count"] for r in rows)],
            "static_native_run_counts": sorted({r["ir"]["expanded_run_count"] for r in rows}),
            "scored_task_correctness": None, "training_allowed_by_this_preparation": False,
            "native_construction_gate": "UNEXECUTED: both B/R source Effects and both selected-child paths must actually ACCEPT and show a meaningful checked contrast on development inputs before training.",
            "verifier_boundary": "Existing verify_task compares graph signature, selected observation, RUN input-node dependencies, selected return, and all actual output bytes. Structural differences are not substituted for actual output checks.",
            "no_new_semantics": True, "no_guard_change": True, "no_neural_execution": True,
            "no_provider_calls": True, "boundary": BOUNDARY}


def _new_output(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not path.exists()
            and path.resolve().is_relative_to(PREPARATION_ROOT.resolve())
            and path.resolve() != PREPARATION_ROOT.resolve()
            and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                        for p in (path, *path.parents)), "SCAFFOLD_NEW_IN_SCOPE_OUTPUT_REQUIRED")
    return path


def _encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def run_preparation(output):
    """Explicit CLI boundary: write one new full enumeration and its receipt."""
    output = _new_output(output)
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    source_before = _source_identity()
    self_before = sha256(Path(__file__).read_bytes()).hexdigest()
    result = enumerate_candidates()
    source_after = _source_identity()
    self_after = sha256(Path(__file__).read_bytes()).hexdigest()
    require(source_before == source_after and self_before == self_after,
            "SCAFFOLD_PREPARATION_SOURCE_CHANGED")
    _new_output(output)
    output.mkdir(parents=True, exist_ok=False)
    raw = _encoded(result)
    with (output / "enumeration.json").open("xb") as stream:
        stream.write(raw)
    saved = (output / "enumeration.json").read_bytes()
    require(saved == raw, "SCAFFOLD_ENUMERATION_OUTPUT_CHANGED")
    source_after = _source_identity()
    self_after = sha256(Path(__file__).read_bytes()).hexdigest()
    require(source_before == source_after and self_before == self_after,
            "SCAFFOLD_PREPARATION_SOURCE_CHANGED")
    receipt = {"schema": SCHEMA, "status": result["status"], "started_utc": started_utc,
               "finished_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic()-started, "output_directory": str(output),
               "source_sha256_before": source_before, "source_sha256_after": source_after,
               "self_sha256_before": self_before, "self_sha256_after": self_after,
               "candidate_count": result["candidate_count"], "counts": result["counts"],
               "controlled_input_pairs": len(result["controlled_input_pairs"]),
               "static_action_token_range": result["static_action_token_range"],
               "static_native_run_counts": result["static_native_run_counts"],
               "files": {"enumeration.json": {"bytes": len(saved), "sha256": sha256(saved).hexdigest()}},
               "training_allowed_by_this_preparation": False, "native_execution": "UNEXECUTED",
               "neural_execution": False, "provider_calls": False, "boundary": BOUNDARY}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(_encoded(receipt))
    return receipt


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    receipt = run_preparation(args.output)
    print(json.dumps({"status": receipt["status"], "candidate_count": receipt["candidate_count"],
                      "counts": receipt["counts"], "controlled_input_pairs": receipt["controlled_input_pairs"],
                      "receipt": str(Path(receipt["output_directory"]) / "receipt.json"),
                      "native_execution": "UNEXECUTED"}, sort_keys=True))


if __name__ == "__main__":
    main()
