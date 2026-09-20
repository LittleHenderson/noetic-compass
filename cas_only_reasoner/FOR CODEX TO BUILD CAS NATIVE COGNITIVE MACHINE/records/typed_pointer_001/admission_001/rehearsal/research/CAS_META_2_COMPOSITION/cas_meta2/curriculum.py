"""Construction-first, topology-safe program-composition practice.

Problems use a deliberately controlled procedural language, not unrestricted
English. Public wording describes requested operations and nested methods; it
never supplies the executable IR, an answer tensor, or a checkpoint prediction.
All independent checks here are structural, not native neural outcome checks.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import re

from .ir import SCHEMA as PROGRAM_SCHEMA, canonical_program, validate_program


SCHEMA = "cas-meta2-curriculum/0.1"
DEFAULT_COUNTS = {"train": 256, "validation": 48, "test": 72}
TAGS = ("copper", "amber", "cobalt", "silver", "coral", "indigo", "jade", "violet")
TOPOLOGY = frozenset((("A", "B"), ("B", "C"), ("C", "R"), ("R", "C")))
_IDENT = r"[A-Za-z_][A-Za-z0-9_]{0,31}"


class CurriculumError(ValueError):
    pass


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("ascii")).hexdigest()


def check_public(public):
    if type(public) is not dict or set(public) != {"problem", "observations"}:
        raise CurriculumError("INVALID_PUBLIC_FIELDS")
    if type(public["problem"]) is not str or not 1 <= len(public["problem"]) <= 32768:
        raise CurriculumError("INVALID_PROBLEM")
    observations = public["observations"]
    if type(observations) is not list or len(observations) != 3:
        raise CurriculumError("INVALID_OBSERVATIONS")
    slots, tags = set(), set()
    for observation in observations:
        if type(observation) is not dict or set(observation) != {"slot", "tag", "values"}:
            raise CurriculumError("INVALID_OBSERVATION_FIELDS")
        slot, tag, values = observation["slot"], observation["tag"], observation["values"]
        if type(slot) is not int or slot not in range(3) or slot in slots:
            raise CurriculumError("INVALID_SLOT")
        if type(tag) is not str or tag not in TAGS or tag in tags:
            raise CurriculumError("INVALID_TAG")
        if (type(values) is not list or len(values) != 8 or
                any(type(v) not in (int, float) or not math.isfinite(v) or not -1 <= v <= 1 for v in values)):
            raise CurriculumError("INVALID_VECTOR")
        slots.add(slot)
        tags.add(tag)
    return public


def permitted_view(task):
    """Copy only problem and visible observations; no gold or provenance."""
    return deepcopy(check_public(task["public"]))


def _interpret(program):
    """Independent symbolic interpreter; does not call IR expansion.

    Values denote the creating RUN index, not fictitious numeric Effects. CALL
    inputs and returns transport those exact indices. This provides a structural
    oracle and topology check; the AWS runtime must still verify actual outputs.
    """
    validate_program(program)
    events, runs = [], []
    frames = 0

    def visit(name, argument, parent, depth):
        nonlocal frames
        frame = frames
        frames += 1
        proc = program["procedures"][name]
        values = {proc["input"]: argument}
        events.append({"kind": "ENTER", "frame": frame, "parent": parent, "input_node": argument})
        for step in proc["steps"]:
            source = values[step["input"]]
            if step["kind"] == "CALL":
                result = visit(step["procedure"], source, frame, depth + 1)
            else:
                producer = None if source == -1 else runs[source]["cjt_id"]
                if producer is not None and (producer, step["cjt_id"]) not in TOPOLOGY:
                    raise CurriculumError("NATIVE_TOPOLOGY_MISMATCH")
                result = len(runs)
                row = {"kind": "RUN", "frame": frame, "node": result,
                       "cjt_id": step["cjt_id"], "input_node": source}
                runs.append(row)
                events.append(row)
            values[step["output"]] = result
        result = values[proc["return"]]
        events.append({"kind": "RETURN", "frame": frame, "output_node": result})
        return result

    result = visit(program["entry"], -1, None, 1)
    return {"events": events, "runs": runs, "return_node": result}


def check_native_topology(program):
    """Separate from the general IR; retain the accepted fixture's edge set."""
    return _interpret(program)


def graph_signature(program):
    """Ignore spelling of procedures/values and observation binding.

    Node order, dependencies, nesting, and selected return remain represented.
    Renaming an otherwise identical program cannot make a held-out graph new.
    """
    return _digest(_interpret(program))


def _new_procedure():
    return {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [], "return": "arg"}


def _append(proc, kind, source, **fields):
    output = f"v{len(proc['steps'])}"
    proc["steps"].append({"kind": kind, "input": source, "output": output, **fields})
    return output


def _construct(rng, depth):
    """Construct formal dependencies first. Rendering knows no RNG or targets."""
    program = {"schema": PROGRAM_SCHEMA, "entry": "main", "procedures": {"main": _new_procedure()}}
    procedures = program["procedures"]
    main = procedures["main"]
    a_values = [_append(main, "RUN", "arg", cjt_id="A") for _ in range(rng.randint(1, 3))]
    outcomes = []
    for _ in range(rng.randint(1, 3)):
        source = rng.choice(a_values)
        if depth == 1:
            current = main
            argument = source
        else:
            name = f"p{len(procedures) - 1}"
            current = procedures[name] = _new_procedure()
            argument = "arg"
            outcome = _append(main, "CALL", source, procedure=name)
        b_values = [_append(current, "RUN", argument, cjt_id="B") for _ in range(rng.randint(1, 2))]
        c_values = []
        for _ in range(rng.randint(1, 2)):
            b_source = rng.choice(b_values)
            if depth < 3:
                c_values.append(_append(current, "RUN", b_source, cjt_id="C"))
            else:
                leaf_name = f"p{len(procedures) - 1}"
                leaf = procedures[leaf_name] = _new_procedure()
                leaf["return"] = _append(leaf, "RUN", "arg", cjt_id="C")
                c_values.append(_append(current, "CALL", b_source, procedure=leaf_name))
        selected = rng.choice(c_values)
        if depth == 1:
            outcomes.append(selected)
        else:
            current["return"] = selected
            outcomes.append(outcome)
    main["return"] = rng.choice(outcomes)
    validate_program(program)
    check_native_topology(program)
    return program


def _render(program, tag, family):
    # Three independently parsed, split-disjoint sentence constructions. These
    # are controlled requests, not claims of general language comprehension.
    first = (f"Use observation {tag}.", f"Select observation {tag}.", f"Begin with observation {tag}.")
    lines = [first[family]]
    for name, proc in program["procedures"].items():
        lines.append((f"Method {name} takes arg.", f"Procedure {name} receives arg.",
                      f"For {name}, incoming value is arg.")[family])
        for step in proc["steps"]:
            out, source = step["output"], step["input"]
            if step["kind"] == "RUN":
                cjt = step["cjt_id"]
                choices = (f"In {name}, obtain {out} by applying junction {cjt} to {source}.",
                           f"Produce {out} in {name} with junction {cjt} using {source}.",
                           f"Compute {out} inside {name}: junction {cjt} acting on {source}.")
            else:
                child = step["procedure"]
                choices = (f"In {name}, obtain {out} by invoking method {child} on {source}.",
                           f"Produce {out} in {name} with procedure {child} using {source}.",
                           f"Compute {out} inside {name}: call {child} acting on {source}.")
            lines.append(choices[family])
        result = proc["return"]
        lines.append((f"Method {name} returns {result}.", f"Return {result} from procedure {name}.",
                      f"The result of {name} is {result}.")[family])
    return "\n".join(lines)


def parse_problem(public):
    """Separate parser implementation reconstructs meaning from public words.

    This is also the rule/reference selector. It has no access to task target,
    generation seed, graph provenance, expected native labels, or answer tensor.
    """
    check_public(public)
    lines = public["problem"].splitlines()
    if not lines:
        raise CurriculumError("UNPARSEABLE_PROBLEM")
    start = re.fullmatch(r"(?:Use|Select|Begin with) observation ([a-z]+)\.", lines[0])
    if start is None:
        raise CurriculumError("UNPARSEABLE_OBSERVATION_REQUEST")
    selected = [row["slot"] for row in public["observations"] if row["tag"] == start[1]]
    if len(selected) != 1:
        raise CurriculumError("UNKNOWN_REQUESTED_OBSERVATION")
    definitions = {}
    declared, returned = set(), set()
    name = _IDENT
    declarations = [rf"Method ({name}) takes arg\.", rf"Procedure ({name}) receives arg\.",
                    rf"For ({name}), incoming value is arg\."]
    runs = [rf"In ({name}), obtain ({name}) by applying junction ([ABC]) to ({name})\.",
            rf"Produce ({name}) in ({name}) with junction ([ABC]) using ({name})\.",
            rf"Compute ({name}) inside ({name}): junction ([ABC]) acting on ({name})\."]
    calls = [rf"In ({name}), obtain ({name}) by invoking method ({name}) on ({name})\.",
             rf"Produce ({name}) in ({name}) with procedure ({name}) using ({name})\.",
             rf"Compute ({name}) inside ({name}): call ({name}) acting on ({name})\."]
    returns = [rf"Method ({name}) returns ({name})\.", rf"Return ({name}) from procedure ({name})\.",
               rf"The result of ({name}) is ({name})\."]
    for line in lines[1:]:
        matched = False
        for pattern in declarations:
            match = re.fullmatch(pattern, line)
            if match:
                owner = match[1]
                if owner in declared:
                    raise CurriculumError("DUPLICATE_METHOD_DECLARATION")
                declared.add(owner)
                definitions[owner] = {"input": "arg", "allowed_cjts": ["A", "B", "C"],
                                      "steps": [], "return": "arg"}
                matched = True
                break
        if matched:
            continue
        for kind, patterns in (("RUN", runs), ("CALL", calls)):
            for index, pattern in enumerate(patterns):
                match = re.fullmatch(pattern, line)
                if match:
                    one, two, operation, source = match.groups()
                    owner, output = (one, two) if index == 0 else (two, one)
                    if owner not in declared or owner in returned:
                        raise CurriculumError("STEP_OUTSIDE_OPEN_METHOD")
                    key = "cjt_id" if kind == "RUN" else "procedure"
                    definitions[owner]["steps"].append({"kind": kind, key: operation,
                                                         "input": source, "output": output})
                    matched = True
                    break
            if matched:
                break
        if matched:
            continue
        for index, pattern in enumerate(returns):
            match = re.fullmatch(pattern, line)
            if match:
                owner, output = (match[2], match[1]) if index == 1 else (match[1], match[2])
                if owner not in declared or owner in returned:
                    raise CurriculumError("INVALID_RETURN_DECLARATION")
                definitions[owner]["return"] = output
                returned.add(owner)
                matched = True
                break
        if not matched:
            raise CurriculumError("UNPARSEABLE_SENTENCE")
    if declared != returned:
        raise CurriculumError("MISSING_RETURN_DECLARATION")
    program = {"schema": PROGRAM_SCHEMA, "entry": "main", "procedures": definitions}
    validate_program(program)
    check_native_topology(program)
    return {"program": program, "binding": selected[0]}


def generate_dataset(seed=20260906, counts=None):
    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    if set(counts) != {"train", "validation", "test"} or any(type(n) is not int or not 2 <= n <= 10000 for n in counts.values()):
        raise CurriculumError("INVALID_SPLIT_COUNTS")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise CurriculumError("INVALID_SEED")
    rng = random.Random(seed)
    all_graphs, all_inputs, splits = set(), set(), {}
    for family, split in enumerate(("train", "validation", "test")):
        tasks = []
        for index in range(counts[split]):
            depth = (3 if index % 2 else 2) if split == "test" else (1 + index % 2)
            for attempt in range(10000):
                program = _construct(rng, depth)
                signature = graph_signature(program)
                if signature not in all_graphs:
                    all_graphs.add(signature)
                    break
            else:
                raise CurriculumError("UNIQUE_GRAPH_GENERATION_EXHAUSTED")
            tags = rng.sample(TAGS, 3)
            observations = []
            for slot, tag in enumerate(tags):
                while True:
                    # Preserve the native fixture's already checked input
                    # neighborhood. Novel program graphs, not unqualified
                    # changes in decoder range, are this experiment's variable.
                    vector = [round(base / 10 + rng.uniform(-0.0004, 0.0004), 7)
                              for base in range(1, 9)]
                    key = tuple(vector)
                    if key not in all_inputs:
                        all_inputs.add(key)
                        break
                observations.append({"slot": slot, "tag": tag, "values": vector})
            binding = index % 3
            public = {"problem": _render(program, tags[binding], family), "observations": observations}
            task = {"task_id": f"meta2-{split}-{index:05d}", "public": public,
                    "target": {"program": program, "binding": binding},
                    "provenance": {"graph_signature": signature, "wording_template": f"family-{family}",
                                   "depth": depth}}
            # Formal structure and wording are checked before dataset release.
            if parse_problem(public) != task["target"]:
                raise CurriculumError("RENDERED_MEANING_MISMATCH")
            tasks.append(task)
        rng.shuffle(tasks)
        splits[split] = tasks
    result = {"schema": SCHEMA, "seed": seed, "splits": splits}
    result["manifest"] = validate_dataset(result)
    return result


def validate_dataset(dataset):
    if dataset.get("schema") != SCHEMA or set(dataset.get("splits", {})) != {"train", "validation", "test"}:
        raise CurriculumError("INVALID_DATASET")
    graphs, inputs, ids, families, report = set(), set(), set(), {}, {}
    for split in ("train", "validation", "test"):
        tasks = dataset["splits"][split]
        if type(tasks) is not list or not tasks:
            raise CurriculumError("EMPTY_SPLIT")
        depths, bindings = [], [0, 0, 0]
        families[split] = set()
        for task in tasks:
            if set(task) != {"task_id", "public", "target", "provenance"}:
                raise CurriculumError("INVALID_TASK_FIELDS")
            if task["task_id"] in ids:
                raise CurriculumError("DUPLICATE_TASK_ID")
            ids.add(task["task_id"])
            public, target, provenance = permitted_view(task), task["target"], task["provenance"]
            if set(target) != {"program", "binding"} or type(target["binding"]) is not int or target["binding"] not in range(3):
                raise CurriculumError("INVALID_TARGET")
            if parse_problem(public) != target:
                raise CurriculumError("PUBLIC_TARGET_MISMATCH")
            signature = graph_signature(target["program"])
            if signature in graphs:
                raise CurriculumError("GRAPH_SPLIT_OVERLAP")
            graphs.add(signature)
            stats = validate_program(target["program"])
            if provenance != {"graph_signature": signature, "wording_template": f"family-{('train','validation','test').index(split)}",
                              "depth": stats["max_call_depth"]}:
                raise CurriculumError("INVALID_PROVENANCE")
            # Do not trust a recorded template identifier over actual wording.
            selected_tag = next(o["tag"] for o in public["observations"] if o["slot"] == target["binding"])
            if public["problem"] != _render(target["program"], selected_tag, ("train", "validation", "test").index(split)):
                raise CurriculumError("WORDING_TEMPLATE_MISMATCH")
            families[split].add(provenance["wording_template"])
            depths.append(stats["max_call_depth"])
            bindings[target["binding"]] += 1
            for row in public["observations"]:
                key = tuple(row["values"])
                if key in inputs:
                    raise CurriculumError("INPUT_INSTANCE_OVERLAP")
                inputs.add(key)
        report[split] = {"count": len(tasks), "sha256": _digest(tasks), "graph_count": len(tasks),
                         "min_depth": min(depths), "max_depth": max(depths), "binding_counts": bindings}
    if any(families[a] & families[b] for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise CurriculumError("WORDING_SPLIT_OVERLAP")
    if report["test"]["max_depth"] <= report["train"]["max_depth"]:
        raise CurriculumError("MISSING_DEEPER_HOLDOUT")
    return {"schema": "cas-meta2-dataset-manifest/0.1", "splits": report,
            "graph_signatures_disjoint": True, "wording_templates_disjoint": True,
            "input_instances_disjoint": True, "native_outcomes_checked": False,
            "boundary": "Controlled procedure-language transduction and named unary dependencies; AWS outcome verification still required."}


def write_dataset(output, seed=20260906, counts=None):
    """Write a NEW dataset directory; test gold is kept in a separate file."""
    dataset = generate_dataset(seed, counts)
    path = Path(output)
    path.mkdir(parents=True, exist_ok=False)
    files = {"train.json": dataset["splits"]["train"], "validation.json": dataset["splits"]["validation"],
             "test_public.json": [permitted_view(t) for t in dataset["splits"]["test"]],
             "test_private.json": dataset["splits"]["test"]}
    hashes = {}
    for name, value in files.items():
        payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode("ascii") + b"\n"
        (path / name).write_bytes(payload)
        hashes[name] = hashlib.sha256(payload).hexdigest()
    manifest = {**dataset["manifest"], "seed": seed, "sha256": hashes}
    (path / "dataset_manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="ascii")
    return manifest
