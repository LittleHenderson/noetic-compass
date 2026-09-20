"""AWS-only assisted development-prefix diagnostic; no training or launcher.

Imports are pure. Runtime admission needs independently pinned launch/budget
evidence and live IMDSv2 identity before any neural import. The parent launcher
must still verify the canonical ledger and enforce instance lifetime/cleanup.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cas-meta2-assisted-prefix-diagnostic/8"
PLAN_SCHEMA = "cas-meta2-prefix-diagnostic-plan/8"
KEYS = ("cas_initial", "cas_selected", "generic_initial", "generic_selected")
BOUNDARY = "Assisted development next-decision diagnostic, not autonomous task success, learning, or native execution."


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def regular(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                       for p in (path, *path.parents)), "V8_REGULAR_FILE_REQUIRED")
    return path


def file_hash(path):
    with regular(path).open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def read_pinned(path, expected):
    from .bundle import decode
    require(type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected), "V8_SHA256_REQUIRED")
    path = regular(path)
    require(path.stat().st_size <= 32 * 1024**2 and file_hash(path) == expected, "V8_PINNED_JSON_CHANGED")
    return decode(path.read_bytes())


def require_request(job):
    require(sys.platform == "linux" and os.environ.get("CAS_META2_RUN_PREFIX_DIAGNOSTIC") == "1",
            "V8_AWS_LINUX_EXPLICIT_ENABLE_REQUIRED")
    require(type(job) is str and re.fullmatch(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}", job)
            and os.environ.get("CAS_META2_AWS_JOB_ID") == job, "V8_EXACT_JOB_REQUIRED")
    require(not {"torch", "casformer", "cas_cjt", "tensorflow", "jax"}.intersection(
        n.split(".")[0] for n in sys.modules), "V8_NEURAL_IMPORT_BEFORE_ADMISSION")


def plan_bounds(plan, job, manifest_sha256):
    require(plan.get("schema") == PLAN_SCHEMA and plan.get("job") == job
            and plan.get("bundle_manifest_sha256") == manifest_sha256
            and plan.get("launch_enabled") is True, "V8_REGISTERED_ENABLED_PLAN_REQUIRED")
    require(type(plan.get("max_seconds")) is int and 1 <= plan["max_seconds"] <= 1800
            and all(type(plan.get(k)) is int and plan[k] == v
                    for k, v in (("batch_size", 16), ("tasks_per_checkpoint", 120), ("seed", 7)))
            and plan.get("checkpoints") == list(KEYS),
            "V8_DIAGNOSTIC_BOUNDS_CHANGED")
    require(re.fullmatch("[0-9a-f]{40}", plan.get("source_sha", ""))
            and re.fullmatch("i-[0-9a-f]{17}", plan.get("instance_id", "")), "V8_SOURCE_INSTANCE_REQUIRED")
    return plan


def source_closure(plan):
    desc = plan["source_manifest"]
    manifest = read_pinned(desc["path"], desc["sha256"])
    require(manifest.get("schema") == "cas-meta2-prefix-source-package/8"
            and manifest["source_sha"] == plan["source_sha"]
            and manifest["frozen_source_files"] == 603 and manifest["protected_baseline_files"] == 316,
            "V8_SOURCE_MANIFEST_MISMATCH")
    package = regular(desc["path"]).parent
    files = manifest["files_sha256"]
    require(type(files) is dict and len(files) == 615 and manifest.get("addition_count") == 11,
            "V8_SOURCE_CLOSURE_INCOMPLETE")
    for name, expected in files.items():
        require(type(name) is str and "\\" not in name and ":" not in name
                and all(p not in ("", ".", "..") for p in name.split("/")), "V8_SOURCE_PATH_INVALID")
        require(file_hash(package / name) == expected, "V8_SOURCE_BYTES_CHANGED:" + name)
    for path in (Path(__file__), ROOT / "cas_meta2/policy_v3.py", ROOT / "aws/budget.py"):
        require(path.resolve().is_relative_to(package.resolve())
                and files.get(path.resolve().relative_to(package.resolve()).as_posix()) == file_hash(path),
                "V8_IMPORTED_SOURCE_OUTSIDE_REGISTERED_PACKAGE")
    archive = plan["source_archive"]
    require(file_hash(archive["path"]) == archive["sha256"], "V8_SOURCE_ARCHIVE_CHANGED")
    with ZipFile(regular(archive["path"])) as zipped:
        names = zipped.namelist()
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) == 616
                and set(names) == set(files) | {"prefix_source_manifest.json"}, "V8_ARCHIVE_MEMBERS_CHANGED")
        require(zipped.read("prefix_source_manifest.json") == regular(desc["path"]).read_bytes(),
                "V8_ARCHIVE_MANIFEST_MISMATCH")
        require(all(sha256(zipped.read(name)).hexdigest() == expected for name, expected in files.items()),
                "V8_ARCHIVE_SOURCE_MAP_MISMATCH")
    # Installed accepted CASformer must match the published source before import.
    spec = importlib.util.find_spec("casformer")
    require(spec is not None and spec.origin is not None, "V8_CASFORMER_INSTALL_REQUIRED")
    installed = regular(spec.origin).parent
    expected = {k.split("/casformer/", 1)[1]: v for k, v in files.items()
                if "/CASFORMER_v0_1/casformer/" in k and k.endswith(".py")}
    actual = {p.relative_to(installed).as_posix(): file_hash(p) for p in installed.rglob("*.py")}
    require(actual == expected and expected, "V8_INSTALLED_CASFORMER_BYTES_CHANGED")
    return manifest


def reservation_binding(plan):
    # This is linkage to parent-pinned evidence, not a live ledger/history audit.
    from aws import budget
    receipt = read_pinned(**{"path": plan["reservation_receipt"]["path"],
                             "expected": plan["reservation_receipt"]["sha256"]})
    ledger = read_pinned(plan["ledger_snapshot"]["path"], plan["ledger_snapshot"]["sha256"])
    require(ledger.get("schema") == budget.SCHEMA and ledger.get("owner_task_cap_usd") == "400.00"
            and ledger.get("no_automatic_refund") is True
            and receipt["ledger_sha256"] == plan["ledger_snapshot"]["sha256"], "V8_LEDGER_PIN_MISMATCH")
    total = budget.reservations_total(ledger["reservations"])
    require(total <= budget.CAP and budget.amount(ledger["total_reserved_usd"]) == total
            and budget.amount(ledger["remaining_unreserved_usd"]) == budget.CAP-total,
            "V8_LEDGER_TOTALS_INVALID")
    matches = [r for r in ledger["reservations"] if r["job"] == plan["job"]]
    require(len(matches) == 1 and matches[0] == receipt["reservation"], "V8_REAL_RESERVED_JOB_REQUIRED")
    entry = matches[0]
    require(entry["source_sha"] == plan["source_sha"]
            and entry["archive_sha256"] == plan["source_archive"]["sha256"]
            and entry["plan"] == plan["resource_plan"]
            and entry["plan_sha256"] == budget.digest(budget.encoded(entry["plan"]))
            and receipt["revision"] == ledger["revision"]
            and receipt["total_reserved_usd"] == ledger["total_reserved_usd"]
            and receipt["remaining_unreserved_usd"] == ledger["remaining_unreserved_usd"],
            "V8_RESERVATION_SOURCE_PLAN_MISMATCH")
    reserved = budget.amount(entry["reserved_usd"], positive=True)
    require(reserved <= budget.amount("4.00") and entry["reserved_usd"] == plan["max_cost_usd"],
            "V8_FOUR_DOLLAR_RESERVATION_BOUND")
    budget.validate_plan(entry["plan"], entry["reserved_usd"])
    resource = entry["plan"]
    require(resource["instance_type"] == "g7.2xlarge" and resource["runtime_seconds_max"] <= 3600
            and resource["runtime_seconds_max"] >= plan["max_seconds"]
            and resource["automatic_retries"] == 0, "V8_RESOURCE_BOUND_CHANGED")
    return entry


def ec2_identity(plan):
    # No environment credentials or cloud SDK. Token is neither stored nor logged.
    from urllib.request import Request, build_opener, ProxyHandler
    opener = build_opener(ProxyHandler({}))
    base = "http://169.254.169.254/latest/"
    def request(path, *, token=None):
        headers = ({"X-aws-ec2-metadata-token-ttl-seconds": "60"} if token is None
                   else {"X-aws-ec2-metadata-token": token})
        with opener.open(Request(base+path, headers=headers, method="PUT" if token is None else "GET"),
                         timeout=3) as response:
            raw = response.read(65537)
        require(len(raw) <= 65536, "V8_IMDS_RESPONSE_BOUND")
        return raw
    token = request("api/token").decode("ascii")
    from .bundle import decode
    identity = decode(request("dynamic/instance-identity/document", token=token))
    require(identity.get("accountId") == "807562639912" and identity.get("region") == "us-west-2"
            and identity.get("instanceId") == plan["instance_id"]
            and identity.get("instanceType") == "g7.2xlarge", "V8_LIVE_EC2_IDENTITY_MISMATCH")
    return identity


def score_choice(scores, target, allowed):
    require(type(scores) is list and scores and all(type(v) in (float, int) and math.isfinite(v) for v in scores),
            "V8_FINITE_SCORES_REQUIRED")
    require(type(target) is int and 0 <= target < len(scores) and type(allowed) in (tuple, list)
            and allowed and len(allowed) == len(set(allowed))
            and all(type(v) is int and 0 <= v < len(scores) for v in allowed) and target in allowed,
            "V8_LEGAL_SCORE_TARGET_REQUIRED")
    def one(indices):
        top = max(sorted(indices), key=lambda i: scores[i])
        peak = max(scores[i] for i in indices)
        normalizer = peak + math.log(math.fsum(math.exp(scores[i]-peak) for i in indices))
        return {"top1_token_id": top, "correct": top == target, "nll": normalizer-scores[target]}
    return {"raw_full_vocabulary": one(range(len(scores))), "grammar_masked": one(allowed),
            "target_token_id": target, "allowed_count": len(allowed), "single_option": len(allowed) == 1}


def checkpoint_metadata(payload, record, registration, tokenizer, vocabulary):
    expected = {"schema": "cas-meta2-contrast-training/7", "family": record["family"],
        "epoch": record["epoch"], "optimizer_steps": record["optimizer_steps"],
        "training_config": registration["config"], "policy_config": registration["policy_config"],
        "source_sha256": registration["source_sha256"],
        "manifest_sha256": registration["data"]["manifest_sha256"], "tokenizer": tokenizer,
        "action_vocabulary": vocabulary, "validation": record["validation"], "accepted": False}
    require(type(payload) is dict and set(payload) == set(expected) | {"state_dict", "optimizer_state_dict"}
            and all(payload[k] == v and type(payload[k]) is type(v) for k, v in expected.items()),
            "V8_CHECKPOINT_METADATA_MISMATCH")
    require(isinstance(payload["state_dict"], dict) and type(payload["optimizer_state_dict"]) is dict
            and set(payload["optimizer_state_dict"]) == {"state", "param_groups"},
            "V8_CHECKPOINT_STATE_FIELDS_INVALID")


def capture_generation(model, tokenizer, publics, *, device, deadline):
    """Call unchanged prediction with publics only; tap returns original scores."""
    from .. import policy_v3 as policy, codec, grammar_v3
    emitted = [[codec.BOS_ID] for _ in publics]
    states = [grammar_v3.GrammarState.from_ids(row, max_length=256) for row in emitted]
    stopped = [False] * len(publics)
    captures = [dict() for _ in publics]
    original = model.decode
    def tap(memory, batch, ids):
        require(time.monotonic() < deadline, "V8_DIAGNOSTIC_DEADLINE")
        result = original(memory, batch, ids)
        prefixes = ids.detach().cpu().tolist()
        scores = result[:, -1].detach().cpu().tolist()
        require(len(prefixes) == len(publics), "V8_GENERATION_BATCH_CHANGED")
        for i, prefix in enumerate(prefixes):
            require(prefix[:len(emitted[i])] == emitted[i], "V8_ACTUAL_GENERATED_PREFIX_MISMATCH")
            if stopped[i] or states[i].complete:
                continue
            allowed = list(states[i].allowed_ids())
            if not allowed:
                stopped[i] = True
                continue
            values = scores[i]
            require(len(values) == len(codec.ACTION_VOCABULARY) and all(math.isfinite(v) for v in values),
                    "V8_GENERATED_SCORES_NONFINITE")
            chosen = max(sorted(allowed), key=lambda n: values[n])
            index = len(emitted[i])
            captures[i][index] = {"prefix_ids": list(emitted[i]), "scores": values,
                                  "allowed_ids": allowed, "chosen_token_id": chosen}
            emitted[i].append(chosen)
            try:
                states[i] = states[i].advance_id(chosen)
            except (codec.PolicyContractError, grammar_v3.GrammarError):
                stopped[i] = True
        return result
    model.decode = tap
    try:
        actions = policy.predict_public(model, tokenizer, publics, device=device, batch_size=16)
    finally:
        model.decode = original
    for action, ids in zip(actions, emitted, strict=True):
        returned = action["token_ids"] if action.get("status") == "REJECTED" else codec.action_to_ids(action)
        require(ids == returned, "V8_RETURNED_ACTION_DIFFERS_FROM_CAPTURED_EMISSION")
    return actions, emitted, captures


def teacher_scores(model, tokenizer, tasks, *, device):
    from .. import policy_v3 as policy, codec
    from .sites import extract_sites
    batch = policy.encode_batch([t["public"] for t in tasks], tokenizer, device=device)
    targets = policy.encode_targets([t["target"] for t in tasks], device=device, max_length=256)
    telemetry = model.decode_with_telemetry(model.encode(batch), batch, targets["decoder_input_ids"])
    rows = []
    for i, task in enumerate(tasks):
        ids = codec.action_to_ids(task["target"], max_length=256)
        require(ids[0] == codec.BOS_ID and ids[-1] == codec.EOS_ID
                and targets["decoder_input_ids"][i, :len(ids)-1].tolist() == ids[:-1]
                and targets["target_ids"][i, :len(ids)-1].tolist() == ids[1:]
                and int(targets["valid"][i].sum().item()) == len(ids)-1, "V8_TEACHER_SHIFT_EOS_MISMATCH")
        sites = extract_sites(ids, max_length=256)
        require(sites["complete"], "V8_REFERENCE_NOT_ADMISSIBLE")
        scored = {}
        for site in sites["sites"]:
            j = site["token_index"]
            require(j > 0 and site["observed"] and site["prefix_ids"] == ids[:j], "V8_TEACHER_SITE_ALIGNMENT")
            scores = telemetry["token_logits"][i, j-1].detach().cpu().tolist()
            scored[j] = score_choice(scores, ids[j], site["allowed_ids"])
        rows.append(scored)
    return rows


def summarize(rows):
    from .sites import ROLES
    groups = defaultdict(list)
    for task in rows:
        for role in ROLES:
            groups[(task["checkpoint"], task["cohort"], task["depth"], role)]
        for site in task["decision_rows"]:
            groups[(task["checkpoint"], task["cohort"], task["depth"], site["reference_site"]["role"])].append(site)
    result = []
    for (checkpoint, cohort, depth, role), sites in sorted(groups.items()):
        row = {"checkpoint": checkpoint, "cohort": cohort, "depth": depth, "role": role,
               "reference_sites": len(sites), "correspondence": dict(Counter(s["correspondence"] for s in sites))}
        for condition in ("correct_prefix", "self_generated_prefix"):
            scored = [s for s in sites if s[condition] is not None]
            row[condition] = {"scored_sites": len(scored), "unscored_sites": len(sites)-len(scored),
                "single_option_sites": sum(s[condition]["single_option"] for s in scored),
                "generated_prefix_relation": {
                    "identical": sum(s.get("preceding_tokens_differ") is False for s in scored),
                    "different": sum(s.get("preceding_tokens_differ") is True for s in scored),
                    "unpaired": sum(s.get("preceding_tokens_differ") is None for s in scored)},
                **{kind: {"correct": sum(s[condition][kind]["correct"] for s in scored),
                           "attempted": len(scored),
                           "mean_nll": None if not scored else math.fsum(s[condition][kind]["nll"] for s in scored)/len(scored)}
                   for kind in ("raw_full_vocabulary", "grammar_masked")}}
            for bucket, singleton in (("single_option", True), ("multiple_options", False)):
                subset = [s for s in scored if s[condition]["single_option"] is singleton]
                row[condition][bucket] = {kind: {
                    "correct": sum(s[condition][kind]["correct"] for s in subset), "attempted": len(subset),
                    "mean_nll": None if not subset else math.fsum(s[condition][kind]["nll"] for s in subset)/len(subset)}
                    for kind in ("raw_full_vocabulary", "grammar_masked")}
        result.append(row)
    return result


def run(bundle, output, *, job, expected_manifest_sha256, plan_path, expected_plan_sha256):
    require_request(job)
    started = time.monotonic()
    plan = plan_bounds(read_pinned(plan_path, expected_plan_sha256), job, expected_manifest_sha256)
    deadline = started + plan["max_seconds"]
    source = source_closure(plan)
    reservation = reservation_binding(plan)
    from .bundle import validate_bundle
    loaded = validate_bundle(bundle, expected_manifest_sha256=expected_manifest_sha256)
    identity = ec2_identity(plan)
    require_request(job)
    require(time.monotonic() < deadline, "V8_DIAGNOSTIC_DEADLINE")
    output = Path(output).absolute()
    require(not output.exists() and output.resolve().is_relative_to((ROOT/"runs").resolve())
            and output.resolve() != (ROOT/"runs").resolve()
            and not any(p.is_symlink() for p in (output, *output.parents)), "V8_NEW_RUN_OUTPUT_REQUIRED")
    for key, value in {"CUBLAS_WORKSPACE_CONFIG": ":4096:8", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                       "OPENBLAS_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"}.items():
        os.environ[key] = value
    import torch
    from .. import policy_v3 as policy, codec
    from ..features_v2 import LosslessPublicTokenizer
    from ..ir import validate_program
    from .sites import compare_sites
    device = policy.require_cuda("cuda")
    name = torch.cuda.get_device_name(device)
    require("RTX PRO 4500" in name.upper() and "T4" not in name.upper(), "V8_REGISTERED_GPU_REQUIRED")
    require(str(torch.__version__) == "2.11.0+cu128" and torch.version.cuda == "12.8", "V8_REGISTERED_TORCH_CUDA_REQUIRED")
    torch.set_num_threads(1)
    random.seed(7); torch.manual_seed(7); torch.cuda.manual_seed_all(7)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False; torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    tokenizer = LosslessPublicTokenizer.from_dict(loaded["tokenizer"])
    registration = loaded["registration"]
    config = policy.PolicyConfig(**registration["policy_config"])
    require(config.max_action_length == 256 and config.max_length == 1024, "V8_POLICY_LENGTH_CHANGED")
    output.mkdir(parents=True, exist_ok=False)
    rows = []; result = {"schema": SCHEMA, "completed": False, "boundary": BOUNDARY,
        "job": job, "environment": {"ec2": identity, "gpu": name, "torch": str(torch.__version__),
        "cuda": torch.version.cuda, "python": sys.version}, "plan_sha256": expected_plan_sha256,
        "bundle_manifest_sha256": expected_manifest_sha256, "source_manifest_sha256": plan["source_manifest"]["sha256"],
        "source_sha": source["source_sha"], "source_archive_sha256": plan["source_archive"]["sha256"],
        "reservation": reservation, "neural_training": False, "native_execution": False, "learning_accepted": False,
        "scheduled_cohort_denominators_per_checkpoint": {name: item["decision_counts"]
            for name, item in loaded["manifest"]["cohorts"].items()},
        "scheduled_reference_opportunities": 9088,
        "scheduled_reference_opportunities_each": {"total": 2272, "single_option": 360, "multiple_options": 1912}}
    try:
        for checkpoint in KEYS:
            require(time.monotonic() < deadline, "V8_DIAGNOSTIC_DEADLINE")
            item = loaded["checkpoints"][checkpoint]; record = item["record"]
            require(file_hash(item["path"]) == record["sha256"]
                    and regular(item["path"]).stat().st_size == record["bytes"], "V8_CHECKPOINT_BYTES_CHANGED")
            payload = torch.load(item["path"], map_location=device, weights_only=True)
            checkpoint_metadata(payload, record, registration, loaded["tokenizer"], list(codec.ACTION_VOCABULARY))
            def check_tensors(value):
                if isinstance(value, torch.Tensor):
                    require(value.device.type == "cuda" and bool(torch.isfinite(value).all()), "V8_CHECKPOINT_TENSOR_INVALID")
                elif isinstance(value, dict):
                    for v in value.values(): check_tensors(v)
                elif isinstance(value, (list, tuple)):
                    for v in value: check_tensors(v)
            check_tensors(payload)
            if record["family"] == "cas":
                model = policy.CASProgramGenerator(len(tokenizer.vocabulary), config, device=device)
            else:
                model = policy.GenericProgramGenerator(len(tokenizer.vocabulary), config,
                    registration["parameter_matching"]["generic_ff_width"], device=device)
            model.load_state_dict(payload["state_dict"], strict=True)
            model.eval(); model.requires_grad_(False)
            before = {k: v.detach().clone() for k, v in model.state_dict().items()}
            with torch.no_grad():
                for cohort in ("train_probe", "validation"):
                    tasks = loaded["cohorts"][cohort]
                    require(len(tasks) == (24 if cohort == "train_probe" else 96), "V8_COHORT_COUNT_CHANGED")
                    saved = loaded["saved_development"][checkpoint]["probe_actions" if cohort == "train_probe" else "validation_actions"]
                    for offset in range(0, len(tasks), 16):
                        require(time.monotonic() < deadline, "V8_DIAGNOSTIC_DEADLINE")
                        group = tasks[offset:offset+16]
                        # Gold is not passed to prediction or its tap. Score assistance only afterward.
                        actions, streams, captures = capture_generation(model, tokenizer,
                            [t["public"] for t in group], device=device, deadline=deadline)
                        assisted = teacher_scores(model, tokenizer, group, device=device)
                        for i, task in enumerate(group):
                            comparison = compare_sites(codec.action_to_ids(task["target"]), streams[i])
                            for site in comparison["rows"]:
                                ref = site["reference_site"]; gen = site["generated_site"]
                                site["correct_prefix"] = assisted[i][ref["token_index"]]
                                site["self_generated_prefix"] = None
                                if site["correspondence"] == "MATCHED" and site["expected_choice"] == "LEGAL" and gen["observed"]:
                                    tap = captures[i][gen["token_index"]]
                                    require(tap["prefix_ids"] == gen["prefix_ids"]
                                            and set(tap["allowed_ids"]) == set(gen["allowed_ids"])
                                            and tap["chosen_token_id"] == gen["chosen_token_id"], "V8_SITE_CAPTURE_MISMATCH")
                                    site["self_generated_prefix"] = score_choice(tap["scores"], site["expected_token_id"], gen["allowed_ids"])
                            row = {"checkpoint": checkpoint, "checkpoint_sha256": record["sha256"],
                                "cohort": cohort, "cohort_index": offset+i, "task_id": task["task_id"],
                                "depth": validate_program(task["target"]["program"])["max_call_depth"],
                                "public_sha256": codec.canonical_sha256(task["public"]),
                                "action": actions[i], "emitted_token_ids": streams[i],
                                "matches_saved_development_action": actions[i] == saved[offset+i],
                                "generation_termination": comparison["generated"]["termination"],
                                "decision_rows": comparison["rows"], "extra_generated_sites": comparison["extra_generated_sites"],
                                "site_counts": comparison["totals"], "boundary": BOUNDARY}
                            rows.append(row)
                            with (output/f"{checkpoint}_{cohort}_{offset+i:03d}.json").open("xb") as stream:
                                stream.write(canonical(row))
                        require(time.monotonic() < deadline, "V8_DIAGNOSTIC_DEADLINE")
            require(all(torch.equal(before[k], v) for k, v in model.state_dict().items()), "V8_MODEL_STATE_CHANGED")
            require(file_hash(item["path"]) == record["sha256"], "V8_CHECKPOINT_CHANGED_AFTER_DIAGNOSTIC")
            del before, payload, model
        require(len(rows) == 480, "V8_DIAGNOSTIC_TASK_DENOMINATOR_CHANGED")
        for checkpoint in KEYS:
            opportunities = [s for r in rows if r["checkpoint"] == checkpoint for s in r["decision_rows"]]
            require(len(opportunities) == 2272
                    and sum(s["correct_prefix"]["single_option"] for s in opportunities) == 360,
                    "V8_REFERENCE_OPPORTUNITY_DENOMINATOR_CHANGED")
        require(source_closure(plan) == source and reservation_binding(plan) == reservation,
                "V8_SOURCE_OR_RESERVATION_CHANGED")
        require(validate_bundle(bundle, expected_manifest_sha256=expected_manifest_sha256)["manifest"] == loaded["manifest"],
                "V8_BUNDLE_CHANGED_AFTER_DIAGNOSTIC")
        require(time.monotonic() < deadline, "V8_DIAGNOSTIC_DEADLINE")
        result["completed"] = True
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        result.update(task_rows_completed=len(rows), scheduled_task_rows=480, summaries=summarize(rows),
            saved_development_action_matches=sum(r["matches_saved_development_action"] for r in rows),
            wall_seconds=time.monotonic()-started, finished_utc=datetime.now(timezone.utc).isoformat(),
            files_sha256={p.name: file_hash(p) for p in sorted(output.glob("*.json"))})
        with (output/"diagnostic_receipt.json").open("xb") as stream:
            stream.write(canonical(result))
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "output", "job", "manifest-sha256", "plan", "plan-sha256"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args()
    result = run(args.bundle, args.output, job=args.job, expected_manifest_sha256=args.manifest_sha256,
                 plan_path=args.plan, expected_plan_sha256=args.plan_sha256)
    print(json.dumps({"completed": result["completed"], "task_rows_completed": result["task_rows_completed"],
                      "boundary": BOUNDARY}))


if __name__ == "__main__":
    main()
