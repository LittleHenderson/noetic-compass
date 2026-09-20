"""Hash-bound, zero-update GPU diagnosis of six retained curriculum learners.

Imports are non-neural. Real checkpoint loading and inference occur only inside
run on the authorized Linux CUDA worker. Historical results remain untouched.
"""
from __future__ import annotations

import ast
import gzip
import hashlib
import json
import time
from pathlib import Path
from zipfile import ZipFile

from .graph import canonical, digest, require

SCHEMA = "cas-graph6-contrast-readout/1"
RESULT_SCHEMA = "cas-graph6-contrast-result/1"
CONFIG_SCHEMA = "cas-graph6-contrast-config/1"
SOURCE_JOB = "cas-meta2-graph6curr-20260910133000-aecb5d07"
SOURCE_DIR = ("records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/"
              "receipt_" + SOURCE_JOB)
SOURCE_RESULT = SOURCE_DIR + "/curriculum_result.json"
SOURCE_RESULT_SHA256 = "848db69bdb0eaefa4f702a4dd4361f779fbc9fbc13c7ca5609de071a8cbcd4d0"
SOURCE_RESULT_BYTES = 4210428
TRANSPORT_RESULT = "records/graph6_contrast_001/retained_curriculum_result.json.gz"
PILOT = "research/CAS_META_2_COMPOSITION"
MAX_WALL_SECONDS = 1200
SEEDS = (20260913, 20260914, 20260915)
CONDITIONS = ("control", "varied")
PROBE_SEED = 20260927


def sha256_file(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_source(root):
    path = Path(root) / SOURCE_RESULT
    if path.exists():
        raw = path.read_bytes()
    else:
        with gzip.open(Path(root) / TRANSPORT_RESULT, "rb") as stream:
            raw = stream.read(SOURCE_RESULT_BYTES + 1)
    require(len(raw) == SOURCE_RESULT_BYTES and digest(raw) == SOURCE_RESULT_SHA256,
            "CONTRAST_SOURCE_RESULT_HASH")
    result = json.loads(raw)
    require(result["job"] == SOURCE_JOB, "CONTRAST_SOURCE_JOB")
    keys = [(row["condition"], row["learner_seed"]) for row in result["learners"]]
    require(sorted(keys) == sorted((c, s) for c in CONDITIONS for s in SEEDS),
            "CONTRAST_SIX_DISTINCT_LEARNERS")
    return result


def input_inventory(root):
    root = Path(root)
    source = read_source(root)
    rows = []
    for learner in source["learners"]:
        checkpoint = [a for a in learner["artifacts"] if a["step"] == 256]
        require(len(checkpoint) == 1, "CONTRAST_FINAL_CHECKPOINT_REQUIRED")
        item = checkpoint[0]
        relative = SOURCE_DIR + "/checkpoints/" + Path(item["path"]).name
        path = root / relative
        require(path.stat().st_size == item["bytes"] and sha256_file(path) == item["sha256"],
                "CONTRAST_CHECKPOINT_HASH:" + relative)
        rows.append({"condition": learner["condition"], "seed": learner["learner_seed"],
                     "checkpoint": relative, "sha256": item["sha256"], "bytes": item["bytes"],
                     "expected_parameter_digest": learner["final_checkpoint_identity"],
                     "practice_correct": learner["practice"]["after_256"]["correct"]})
    return rows


def historical_implementation_check(root):
    """The only current framework addition is the unused scores method."""
    root = Path(root)
    with ZipFile(root / SOURCE_DIR / "source.zip") as archive:
        rows = {}
        names = ("adapter.py", "lessons.py", "curriculum.py", "real_framework.py")
        for name in names:
            relative = "cas_meta2/graph_teaching/" + name
            archived = archive.read(PILOT + "/" + relative)
            current = (root / relative).read_bytes()
            if name == "real_framework.py":
                left, right = ast.parse(archived), ast.parse(current)
                for tree in (left, right):
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef) and node.name == "GraphLearner":
                            node.body = [child for child in node.body if not (
                                isinstance(child, ast.FunctionDef) and child.name == "scores")]
                equal = ast.dump(left) == ast.dump(right)
            else:
                equal = archived == current
            require(equal, "CONTRAST_HISTORICAL_IMPLEMENTATION_CHANGED:" + name)
            rows[relative] = {"historical_sha256": digest(archived),
                              "current_sha256": digest(current), "compatible": equal}
        relative = "cas_meta2/features_v2.py"
        archived = archive.read(PILOT + "/" + relative)
        current = (root / relative).read_bytes()
        require(archived == current, "CONTRAST_TOKENIZER_SOURCE_CHANGED")
        rows[relative] = {"historical_sha256": digest(archived),
                          "current_sha256": digest(current), "compatible": True}
    return rows


def validate_config(config, root):
    require(config.get("schema") == CONFIG_SCHEMA, "CONTRAST_CONFIG_SCHEMA")
    require(config.get("training") is False and type(config.get("optimizer_updates")) is int
            and config.get("optimizer_updates") == 0,
            "CONTRAST_NO_TRAINING")
    require(config.get("probe_seed") == PROBE_SEED, "CONTRAST_PROBE_SEED")
    require(config.get("max_wall_seconds") == MAX_WALL_SECONDS, "CONTRAST_WALL_BOUND")
    require(config.get("inputs") == input_inventory(root), "CONTRAST_INPUT_BINDINGS")
    require(config.get("source_result_sha256") == SOURCE_RESULT_SHA256, "CONTRAST_RESULT_BINDING")
    return config


def write_json(path, document):
    raw = json.dumps(document, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    Path(path).write_bytes(raw)
    return {"name": Path(path).name, "bytes": len(raw), "sha256": digest(raw)}


def deliver(results, artifacts, report, *, failed=False):
    results, artifacts = Path(results), Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    entries = [write_json(artifacts / "contrast_readout.json", report)]
    summary = {"schema": SCHEMA, "job": report["job"], "optimizer_updates": 0,
               "learners": [{"condition": x["condition"], "seed": x["seed"],
                             "practice_reproduced": x["practice_reproduced"],
                             "weights_unchanged": x["probe"]["weights_unchanged"],
                             "summary": x["probe"]["summary"],
                             "length_permutations": len(x["probe"]["list_length_probe"])}
                            for x in report.get("learners", [])]}
    entries.append(write_json(artifacts / "measurements.json", summary))
    write_json(artifacts / "manifest.json", {"artifacts": entries})
    envelope = {"schema": RESULT_SCHEMA, "job": report["job"],
                "status": "CONTRAST_READOUT_FAILED" if failed else "CONTRAST_READOUT_DELIVERED",
                "optimizer_updates": 0, "artifacts": entries,
                "summary": summary, "failure": report.get("failure"),
                "boundary": "Retrospective zero-update diagnosis; no training, new transfer claim, or causal attribution."}
    receipt = write_json(results / "result.json", envelope)
    (results / "result.json.sha256").write_bytes((receipt["sha256"] + "\n").encode())
    return envelope


def run(config, *, root, results, artifacts, torch=None, device=None):
    from . import adapter, curriculum, curriculum_experiment, trainer, contrast_probe
    from .real_framework import build_encoder, build_graph_training_framework, GraphLearner
    if torch is None:
        from cas_meta2.teaching_cycle.gpu_adapter import _cuda
        torch, device = _cuda()
    require(str(device).startswith("cuda"), "CONTRAST_CUDA_REQUIRED")
    pilot = Path(root) / PILOT
    validate_config(config, pilot)
    started = time.monotonic()
    report = {"schema": SCHEMA, "job": config["job"], "learners": [],
              "inputs": config["inputs"], "source_result_sha256": SOURCE_RESULT_SHA256,
              "execution_design": config.get("execution_design"),
              "optimizer_updates": 0, "neural_device": str(device)}
    try:
        report["historical_implementation"] = historical_implementation_check(pilot)
        source = read_source(pilot)
        records = trainer.training_records(20260909)
        tasks = [adapter.public_records(row, "cas") for row in records]
        encoder = build_encoder(torch, [t["public"] for t in tasks], d_model=64,
                                seed=20260909, device=device)
        encoded_state = curriculum_experiment.encoder_state(torch, encoder)
        for item, old in zip(config["inputs"], source["learners"]):
            require(time.monotonic() - started < MAX_WALL_SECONDS, "CONTRAST_DEADLINE")
            payload = torch.load(str(pilot / item["checkpoint"]), map_location=device,
                                 weights_only=True)
            require(payload["schema"] == curriculum_experiment.CHECKPOINT_SCHEMA,
                    "CONTRAST_CHECKPOINT_SCHEMA")
            require(payload["condition"] == item["condition"] and payload["learner_seed"] == item["seed"]
                    and payload["step"] == 256 and payload["arm"] == "cas", "CONTRAST_CHECKPOINT_IDENTITY")
            retained_encoder = payload["encoder"]
            require(retained_encoder["vocabulary"] == encoded_state["vocabulary"], "CONTRAST_VOCABULARY_RESTORE")
            require(torch.equal(retained_encoder["projection"], encoded_state["projection"]),
                    "CONTRAST_ENCODER_PROJECTION_RESTORE")
            for key in ("d_model", "max_length", "structural_problem_binding", "projection_frozen"):
                require(retained_encoder[key] == encoded_state[key], "CONTRAST_ENCODER_METADATA:" + key)
            own_records = curriculum.control_records() if item["condition"] == "control" else curriculum.varied_records()
            require(payload["record_ids"] == [r["record_id"] for r in own_records], "CONTRAST_TRAINING_RECORDS")
            framework = build_graph_training_framework(torch, device, seed=item["seed"], encoder=encoder)
            framework.module.load_state_dict(payload["model"], strict=True)
            framework.module.eval()
            learner = GraphLearner(torch, framework,
                [adapter.public_records(r, "cas") for r in own_records], device, 0.003)
            for parameter in framework.module.parameters():
                parameter.requires_grad_(False)
            before = learner.checkpoint_identity()
            require(before == item["expected_parameter_digest"], "CONTRAST_PARAMETER_RESTORE")
            with torch.no_grad():
                observed = []
                for record in records:
                    public = adapter.public_records(record, "cas")
                    prediction = learner.predict({k: public[k] for k in ("public", "encoded_options", "record_id", "op")})
                    observed.append({"record_id": record["record_id"], "op": record["op"],
                                     "predicted": prediction, "correct": prediction == record["correct"]})
                expected = {r["record_id"]: r["correct"] for r in old["practice"]["after_256"]["predictions"]}
                actual = {r["record_id"]: r["correct"] for r in observed}
                require(actual == expected, "CONTRAST_PRACTICE_REPRODUCTION")
                probe = contrast_probe.run_probe(torch=torch, learner=learner, records=records,
                            practice_predictions=actual, seed=PROBE_SEED, arm="cas", device=device)
            require(learner.checkpoint_identity() == before, "CONTRAST_PARAMETER_MUTATION")
            report["learners"].append({"condition": item["condition"], "seed": item["seed"],
                "practice_reproduced": True, "practice": observed, "probe": probe,
                "checkpoint_sha256": item["sha256"], "parameter_digest": before})
            Path(artifacts).mkdir(parents=True, exist_ok=True)
            write_json(Path(artifacts) / "progress.json", report)
        require(len(report["learners"]) == 6, "CONTRAST_LEARNER_COVERAGE")
        report["elapsed_seconds"] = time.monotonic() - started
        return deliver(results, artifacts, report)
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)[:2000]}
        report["elapsed_seconds"] = time.monotonic() - started
        deliver(results, artifacts, report, failed=True)
        raise
