"""Source-bound algebraic audit and CUDA-only numeric encoder diagnostic.

No learner, optimizer, checkpoint or answer selection is constructed. The
checker supplies counterexample labels only to the audit, never to an encoder.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import time

CONFIG_SCHEMA = "cas-ordered-encoder-config/1"
RESULT_SCHEMA = "cas-ordered-encoder-result/1"
SCHEMA = "cas-ordered-encoder-probe/1"
CANDIDATE = "CAS_ORDERED_ENCODER_DIAGNOSTIC_001"
PROBE_SEED = 20260916
ENCODER_SEED = 20260909
MAX_WALL_SECONDS = 1200
FAMILIES = 16
D_MODEL = 64
PILOT = "research/CAS_META_2_COMPOSITION"
LEGACY_SHA256 = "82c177e8f70e6931d90a79b65defe9fe6848cce6ab690c67f890b12c4799cd3c"
EXECUTION_DESIGN = {
    "candidate": CANDIDATE, "training": False, "optimizer_updates": 0,
    "max_wall_seconds": MAX_WALL_SECONDS, "jobs": 1, "automatic_retries": 0,
    "reservation_usd": "7.00", "instance_type": "g7.2xlarge", "region": "us-west-2",
    "probe_seed": PROBE_SEED, "checkpoints": 0, "launch_enabled": False,
    "worker_bootstrap_seconds_max": 3600, "instance_seconds_max": 7200,
    "resource_plan_role": "Inherited hardware, cost, and teardown limits only; historical training metadata does not describe this diagnostic.",
}
SOURCE_FILES = (
    "cas_meta2/features_v2.py", "cas_meta2/codec.py",
    "cas_meta2/graph_teaching/adapter.py", "cas_meta2/graph_teaching/graph.py",
    "cas_meta2/graph_teaching/lessons.py", "cas_meta2/graph_teaching/reference.py",
    "cas_meta2/graph_teaching/real_framework.py", "cas_meta2/graph_teaching/trainer.py",
    "cas_meta2/graph_teaching/ordered_encoder.py",
    "cas_meta2/graph_teaching/ordered_encoder_probe.py",
    "cas_meta2/graph_teaching/curriculum_experiment.py",
    "cas_meta2/teaching_cycle/gpu_adapter.py",
)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    """Match the established launcher's newline-terminated canonical JSON."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8") + b"\n"


def digest(value):
    return sha256(value).hexdigest()


def input_inventory(root):
    root = Path(root)
    result = []
    for name in sorted(SOURCE_FILES):
        raw = (root / name).read_bytes()
        result.append({"path": name, "bytes": len(raw), "sha256": digest(raw)})
    legacy = next(row for row in result if row["path"].endswith("/real_framework.py"))
    require(legacy["sha256"] == LEGACY_SHA256, "LEGACY_ENCODER_AUDIT_SOURCE_CHANGED")
    return result


def witness_cases():
    """Valid explicit graphs, identical options, changed directional answers."""
    from .graph import Graph, Node, Relation
    from .lessons import _render_prompt
    from .reference import reach_kind
    rows = []
    for family in range(FAMILIES):
        # B and C are unseen lexical anagrams under the historical tokenizer.
        a, b, c = ("zzprobe%droot" % family, "zzprobe%dab" % family,
                   "zzprobe%dba" % family)
        nodes = tuple(Node(name, "idea", ()) for name in (a, b, c))
        graph = Graph(nodes, (Relation("contains", a, b, ("constituent", b)),)).validate()
        reversed_graph = Graph(nodes, (Relation("contains", b, a,
                                               ("constituent", a)),)).validate()
        reordered = Graph(tuple(reversed(nodes)), graph.relations).validate()
        options = [{"slot": i, "tag": tag, "values": [0.0] * 8}
                   for i, tag in enumerate(("direct", "absent", "via:" + c))]
        for arm in ("cas", "generic"):
            def variant(current, part, idea):
                public = {"problem": _render_prompt("REACHED_VIA", current,
                          {"part": part, "idea": idea}, arm), "observations": options}
                return {"public": public, "answer": reach_kind(current, part, idea)}
            rows.append({"family": family, "arm": arm,
                "base": variant(graph, b, a),
                "edge_reversal": variant(reversed_graph, b, a),
                "query_role_swap": variant(graph, a, b),
                "unseen_anagram_query": variant(graph, c, a),
                "structural_reorder": variant(reordered, b, a)})
    return rows


def training_publics():
    from .adapter import public_records
    from .trainer import training_records
    return [public_records(record, "cas")["public"]
            for record in training_records(ENCODER_SEED)]


def legacy_algebraic_signature(public, tokenizer):
    """Normal form of the reviewed product/mean encoder over real arithmetic.

    It is a sufficient collision witness, not a complete numerical emulator.
    Normalization preserves equality of identical products. Token order can
    affect GPU roundoff; this function does not assert bitwise tensor equality.
    """
    from cas_meta2.features_v2 import _word_token
    markers = {tokenizer.vocabulary.index(_word_token(word)) for word in ("node", "rel")}
    newline = tokenizer.vocabulary.index(_word_token("\n"))
    encoded = tokenizer.encode_public(public)
    segments, rest, current = [], [], None
    for token, kind in zip(encoded["ids"], encoded["kinds"]):
        if kind != 0:
            continue
        if token == newline:
            current = None
        elif token in markers:
            current = [token]
            segments.append(current)
        elif current is not None:
            current.append(token)
        else:
            rest.append(token)
    require(segments, "PROBE_STRUCTURAL_SEGMENTS_REQUIRED")
    return {"products": sorted([sorted(Counter(row).items()) for row in segments]),
            "rest_mean_counts": sorted(Counter(rest).items())}


def algebraic_audit(root):
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    inventory = input_inventory(root)
    tokenizer = LosslessPublicTokenizer.fit_train(training_publics(), max_length=1024)
    pairs = []
    for case in witness_cases():
        baseline = legacy_algebraic_signature(case["base"]["public"], tokenizer)
        for name in ("edge_reversal", "query_role_swap", "unseen_anagram_query",
                     "structural_reorder"):
            variant = case[name]
            same = baseline == legacy_algebraic_signature(variant["public"], tokenizer)
            changed = case["base"]["answer"] != variant["answer"]
            require(same, "LEGACY_WITNESS_DID_NOT_COLLIDE:" + name)
            require(changed == (name != "structural_reorder"), "WITNESS_TARGET_RELATION:" + name)
            require(case["base"]["public"]["observations"] == variant["public"]["observations"],
                    "WITNESS_OPTIONS_CHANGED")
            pairs.append({"family": case["family"], "arm": case["arm"], "contrast": name,
                          "algebraically_identical": same, "answer_changed": changed,
                          "base_answer": case["base"]["answer"], "variant_answer": variant["answer"],
                          "base_public_sha256": digest(canonical(case["base"]["public"])),
                          "variant_public_sha256": digest(canonical(variant["public"]))})
    return {"schema": SCHEMA, "status": "ALGEBRAIC_COLLISIONS_CONFIRMED",
            "source_inputs": inventory, "pairs": pairs,
            "changed_answer_collisions": sum(row["answer_changed"] for row in pairs),
            "reorder_controls": sum(not row["answer_changed"] for row in pairs),
            "neural_calls": 0, "boundary": "Source-bound real-arithmetic collision proof; GPU numeric and learning outcomes are separate."}


def validate_config(config, root):
    require(type(config) is dict and config.get("schema") == CONFIG_SCHEMA, "ORDERED_CONFIG_SCHEMA")
    require(set(config) == {"schema", "candidate", "job", "bucket", "region", "source_sha",
            "training", "optimizer_updates", "max_wall_seconds", "probe_seed", "inputs",
            "inputs_sha256", "execution_design"}, "ORDERED_CONFIG_FIELDS")
    require(config.get("candidate") == CANDIDATE, "ORDERED_CANDIDATE")
    require(type(config.get("job")) is str and re.fullmatch(
            r"cas-meta2-orderedencoder-\d{14}-[a-f0-9]{8}", config["job"]), "ORDERED_JOB")
    require(type(config.get("bucket")) is str and re.fullmatch(
            r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", config["bucket"]), "ORDERED_BUCKET")
    require(config.get("region") == "us-west-2", "ORDERED_REGION")
    require(canonical(config.get("execution_design")) == canonical(EXECUTION_DESIGN),
            "ORDERED_EXECUTION_DESIGN")
    require(config.get("training") is False and type(config.get("optimizer_updates")) is int
            and config["optimizer_updates"] == 0, "ORDERED_NO_TRAINING")
    require(type(config.get("probe_seed")) is int and config["probe_seed"] == PROBE_SEED,
            "ORDERED_PROBE_SEED")
    require(type(config.get("max_wall_seconds")) is int
            and config["max_wall_seconds"] == MAX_WALL_SECONDS, "ORDERED_WALL_BOUND")
    require(type(config.get("source_sha")) is str
            and re.fullmatch(r"[0-9a-f]{40}", config["source_sha"]), "ORDERED_SOURCE_SHA")
    require(canonical(config.get("inputs")) == canonical(input_inventory(root)), "ORDERED_INPUT_BINDINGS")
    require(config.get("inputs_sha256") == digest(canonical(config["inputs"])), "ORDERED_INPUTS_DIGEST")
    return config


def write_json(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    Path(path).write_bytes(raw)
    return {"name": Path(path).name, "bytes": len(raw), "sha256": digest(raw)}


def deliver(results, artifacts, report, failed=False):
    results, artifacts = Path(results), Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    entries = [write_json(artifacts / "encoder_probe.json", report)]
    summary = {key: report.get(key) for key in ("job", "source_sha", "checks", "elapsed_seconds",
               "projection_unchanged", "projection_sha256_before", "projection_sha256_after", "failure")}
    summary.update({"schema": SCHEMA, "optimizer_updates": 0, "learner_forward_calls": 0})
    entries.append(write_json(artifacts / "measurements.json", summary))
    write_json(artifacts / "manifest.json", {"artifacts": entries})
    envelope = {"schema": RESULT_SCHEMA, "job": report["job"], "artifacts": entries,
        "status": "ORDERED_ENCODER_DIAGNOSTIC_FAILED" if failed else "ORDERED_ENCODER_DIAGNOSTIC_DELIVERED",
        "optimizer_updates": 0, "summary": summary, "failure": report.get("failure"),
        "boundary": "Encoding mechanism diagnostic only; no trained accuracy, native routing, or learning benefit claim."}
    receipt = write_json(results / "result.json", envelope)
    (results / "result.json.sha256").write_text(receipt["sha256"] + "\n", encoding="ascii")
    return envelope


def run(config, *, root, results, artifacts):
    """Validate all inputs before acquiring the actual AWS CUDA device."""
    pilot = Path(root) / PILOT
    validate_config(config, pilot)
    from cas_meta2.teaching_cycle.gpu_adapter import _cuda
    from .real_framework import build_encoder
    from .ordered_encoder import build_ordered_encoder
    from .curriculum_experiment import encoder_state
    started = time.monotonic()
    report = {"schema": SCHEMA, "job": config["job"], "source_sha": config["source_sha"],
              "inputs": config["inputs"], "execution_design": config.get("execution_design"),
              "optimizer_updates": 0, "learner_forward_calls": 0, "rows": []}
    try:
        torch, device = _cuda()
        require(str(device).startswith("cuda"), "ORDERED_CUDA_REQUIRED")
        report.update({"neural_device": str(device), "torch_version": torch.__version__,
                       "gpu_name": torch.cuda.get_device_name(device)})
        report["algebraic_audit"] = algebraic_audit(pilot)
        legacy = build_encoder(torch, training_publics(), D_MODEL, ENCODER_SEED, device)
        before = encoder_state(torch, legacy)
        report["projection_sha256_before"] = digest(before["projection"].detach().cpu().contiguous().numpy().tobytes())
        ordered = build_ordered_encoder(torch, legacy, seed=PROBE_SEED, device=device)
        report["ordered_profile"] = ordered["ordered_profile"]
        with torch.no_grad():
            for case in witness_cases():
                require(time.monotonic() - started < MAX_WALL_SECONDS, "ORDERED_DEADLINE")
                vectors = {}
                for name in ("base", "edge_reversal", "query_role_swap", "unseen_anagram_query", "structural_reorder"):
                    public = case[name]["public"]
                    vectors[name] = {"legacy": legacy["encode_problem"](public),
                                     "ordered": ordered["encode_problem"](public)}
                    require(all(bool(torch.isfinite(v).all()) for v in vectors[name].values()), "ENCODER_NONFINITE")
                raw = {name: {key: value.detach().cpu().tolist() for key, value in item.items()}
                       for name, item in vectors.items()}
                for name in ("edge_reversal", "query_role_swap", "unseen_anagram_query", "structural_reorder"):
                    row = {"family": case["family"], "arm": case["arm"], "contrast": name,
                           "answer_changed": case["base"]["answer"] != case[name]["answer"]}
                    for key in ("legacy", "ordered"):
                        a, b = vectors["base"][key], vectors[name][key]
                        delta = float(torch.linalg.vector_norm(a-b).item())
                        scale = max(float(torch.linalg.vector_norm(a).item()), float(torch.linalg.vector_norm(b).item()), 1.0)
                        row[key + "_relative_l2"] = delta / scale
                        row[key + "_bitwise_equal"] = bool(torch.equal(a, b))
                    row["raw_vectors"] = {"base": raw["base"], "variant": raw[name]}
                    report["rows"].append(row)
        after = encoder_state(torch, legacy)
        report["projection_sha256_after"] = digest(after["projection"].detach().cpu().contiguous().numpy().tobytes())
        report["projection_unchanged"] = (torch.equal(before["projection"], after["projection"])
                                          and before["vocabulary"] == after["vocabulary"])
        changed = [r for r in report["rows"] if r["answer_changed"]]
        controls = [r for r in report["rows"] if not r["answer_changed"]]
        report["checks"] = {"assigned_pairs": len(report["rows"]), "changed_answer_pairs": len(changed),
            "reorder_controls": len(controls), "legacy_collision_tolerance": 1e-5,
            "ordered_separation_threshold": 1e-3,
            "legacy_near_collisions": sum(r["legacy_relative_l2"] <= 1e-5 for r in changed),
            "ordered_separated": sum(r["ordered_relative_l2"] > 1e-3 for r in changed),
            "ordered_reorder_exact": sum(r["ordered_bitwise_equal"] for r in controls)}
        checks = report["checks"]
        require(checks["assigned_pairs"] == FAMILIES*2*4 and len(changed) == FAMILIES*2*3,
                "PROBE_COVERAGE_INCOMPLETE")
        require(report["projection_unchanged"], "FROZEN_PROJECTION_MUTATED")
        require(checks["legacy_near_collisions"] == len(changed), "LEGACY_NUMERIC_COLLISION_NOT_REPRODUCED")
        require(checks["ordered_separated"] == len(changed), "ORDERED_COUNTEREXAMPLE_NOT_SEPARATED")
        require(checks["ordered_reorder_exact"] == len(controls), "ORDERED_LINE_ORDER_DEPENDENT")
        report["elapsed_seconds"] = time.monotonic() - started
        return deliver(results, artifacts, report)
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)[:2000]}
        report["elapsed_seconds"] = time.monotonic() - started
        deliver(results, artifacts, report, failed=True)
        raise
