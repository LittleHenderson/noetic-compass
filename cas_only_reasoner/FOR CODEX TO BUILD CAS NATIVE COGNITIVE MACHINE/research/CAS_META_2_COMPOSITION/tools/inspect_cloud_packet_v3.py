"""Strict byte-only learning-v3 packet inspection; no checkpoint deserialization.

Archive, full-index, extraction and unchanged native-record byte checks reuse
the frozen v1 inspector. This separate v3 tool checks copy-policy GPU receipts,
format3 selection, cleanup, explicit presentation order and exclusions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PILOT = "research/CAS_META_2_COMPOSITION"
BASE = "cloud_job/campaign/"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
VERDICT_FIELDS = ("task_correct", "procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SHA1 = re.compile(r"[a-f0-9]{40}\Z")
MAX_COMPRESSED, MAX_EXPANDED, MAX_MEMBERS = 1024**3, 2 * 1024**3, 65536
legacy = profiles = None
_IMPORT_GUARD = None


class PacketInvalid(ValueError):
    pass


def require(value, reason):
    if not value:
        raise PacketInvalid(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(PacketInvalid("NONFINITE_JSON")))
    canonical(result)
    return result


def no_links(path):
    raw = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (raw, *raw.parents)),
            "AUDIT_SOURCE_OR_OUTPUT_LINK_REFUSED")
    return raw


def source_file(manifest, relative):
    require(type(manifest) is dict and manifest.get("pilot_dir") == PILOT, "V3_SOURCE_MANIFEST_REQUIRED")
    path = no_links(ROOT / relative)
    expected = manifest["files_sha256"].get(PILOT + "/" + relative)
    require(type(expected) is str and SHA256.fullmatch(expected) and path.is_file()
            and path.resolve().is_relative_to(ROOT) and file_hash(path) == expected,
            "V3_LOCAL_SOURCE_NOT_BOUND:" + relative)
    return expected


def _git_source_precheck(manifest, expected_source_sha):
    """Standard-library-only commit check before any project dependency runs."""
    import io
    import subprocess
    require(type(expected_source_sha) is str and SHA1.fullmatch(expected_source_sha)
            and type(manifest) is dict and manifest.get("source_sha") == expected_source_sha,
            "V3_EXTERNAL_SOURCE_SHA_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip()).resolve()
    resolved = subprocess.check_output(["git", "rev-parse", expected_source_sha + "^{commit}"], cwd=repo, text=True).strip()
    require(resolved == expected_source_sha, "V3_EXACT_GIT_SOURCE_COMMIT_REQUIRED")
    prefix = ROOT.relative_to(repo).as_posix() + "/"
    raw = subprocess.check_output(["git", "-c", "core.autocrlf=false", "archive", "--format=zip",
        expected_source_sha, "--", prefix + "cas_meta2", prefix + "tools"], cwd=repo)
    require(len(raw) <= 128 * 1024**2, "V3_PREIMPORT_ARCHIVE_SIZE")
    committed = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        total = 0
        for info in archive.infolist():
            if info.is_dir():
                continue
            require(info.filename.startswith(prefix), "V3_PREIMPORT_GIT_PATH")
            relative = info.filename.removeprefix(prefix)
            require(relative not in committed and (info.external_attr >> 16) & 0o170000 != 0o120000,
                    "V3_PREIMPORT_GIT_ALIAS_OR_LINK")
            total += info.file_size
            require(total <= 256 * 1024**2, "V3_PREIMPORT_EXPANSION_LIMIT")
            committed[relative] = sha(archive.read(info))
    count = 0
    for name, expected in manifest["files_sha256"].items():
        relative = name.removeprefix(PILOT + "/")
        if name.startswith((PILOT + "/cas_meta2/", PILOT + "/tools/")) and name.endswith(".py"):
            require(committed.get(relative) == expected and source_file(manifest, relative) == expected,
                    "V3_PREIMPORT_SOURCE_DIFFERS_FROM_GIT:" + relative)
            count += 1
    require(count > 0 and all(PILOT + "/" + name in manifest["files_sha256"] for name in (
        "tools/inspect_cloud_packet_v3.py", "tools/audit_stored_packet_v3.py",
        "tools/experiment_profiles_v3.py", "tools/inspect_cloud_packet.py", "cas_meta2/__init__.py")),
        "V3_PREIMPORT_HELPER_COVERAGE")
    return {"source_sha": expected_source_sha, "git_repo": str(repo), "python_files_verified_before_import": count}



def _configure(manifest, expected_source_sha):
    """Fresh checked project imports: no arbitrary sys.path/preloaded fallback."""
    global legacy, profiles, Packet, safe_name, _native, _verdict, LosslessPublicTokenizer
    global action_to_ids, depth_generated_metrics, selection_key, curriculum, _IMPORT_GUARD
    if _IMPORT_GUARD is not None:
        require(_IMPORT_GUARD.manifest == manifest and _IMPORT_GUARD.git_binding["source_sha"] == expected_source_sha, "V3_AUDITOR_RECONFIGURATION_REFUSED")
        _IMPORT_GUARD.verify()
        return
    git_binding = _git_source_precheck(manifest, expected_source_sha)
    import importlib.abc
    import importlib.machinery
    import importlib.util
    for name in sys.modules:
        require(name.split(".")[0] not in {"torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt", "boto3", "botocore"},
                "V3_NEURAL_OR_PROVIDER_MODULE_PRELOADED")
    permitted_tools = {"tools.inspect_cloud_packet_v3", "tools.audit_stored_packet_v3"}
    for name, module in list(sys.modules.items()):
        if name == "tools":
            require(getattr(module, "__file__", None) is None
                    and {str(Path(p).resolve()) for p in module.__path__} == {str(ROOT / "tools")}, "V3_FOREIGN_TOOLS_NAMESPACE")
        elif name in permitted_tools:
            source_file(manifest, name.replace(".", "/") + ".py")
            require(Path(getattr(module, "__file__", "")).resolve() == ROOT / (name.replace(".", "/") + ".py"),
                    "V3_FOREIGN_AUDITOR_MODULE")
        elif name == "cas_meta2" or name.startswith(("cas_meta2.", "tools.")):
            raise PacketInvalid("V3_PRELOADED_PROJECT_MODULE_REFUSED:" + name)

    class Loader(importlib.abc.Loader):
        def __init__(self, guard, name):
            self.guard, self.name = guard, name
        def create_module(self, spec):
            return None
        def exec_module(self, module):
            path = self.guard.paths[self.name]
            self.guard.loaded[self.name] = module
            exec(compile(self.guard.raw(self.name), str(path), "exec"), module.__dict__)

    class Guard(importlib.abc.MetaPathFinder):
        def __init__(self):
            self.manifest, self.paths, self.loaded = manifest, {}, {}
            self.git_binding = git_binding
            self.before = {name: module for name, module in sys.modules.items() if name == "tools" or name in permitted_tools}
            prefix = PILOT + "/"
            for name in manifest["files_sha256"]:
                if name.startswith((prefix + "cas_meta2/", prefix + "tools/")) and name.endswith(".py"):
                    relative = name.removeprefix(prefix)
                    module = relative[:-3].replace("/", ".").removesuffix(".__init__")
                    self.paths[module] = ROOT / relative
        def raw(self, name):
            path = self.paths[name]
            source_file(self.manifest, path.relative_to(ROOT).as_posix())
            return path.read_bytes()
        def find_spec(self, fullname, path=None, target=None):
            require(fullname.split(".")[0] not in {"torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt", "boto3", "botocore"},
                    "V3_NEURAL_OR_PROVIDER_IMPORT_REFUSED:" + fullname)
            if fullname == "tools":
                spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
                spec.submodule_search_locations = [str(ROOT / "tools")]
                return spec
            if fullname in self.paths:
                location = self.paths[fullname]
                self.raw(fullname)
                return importlib.util.spec_from_file_location(fullname, location, loader=Loader(self, fullname),
                    submodule_search_locations=[str(location.parent)] if location.name == "__init__.py" else None)
            require(not fullname.startswith(("tools.", "cas_meta2.")), "V3_UNBOUND_PROJECT_IMPORT:" + fullname)
            return None
        def verify(self):
            namespace = sys.modules.get("tools")
            if namespace is not None:
                require(getattr(namespace, "__file__", None) is None and {str(Path(p).resolve()) for p in namespace.__path__} == {str(ROOT / "tools")},
                        "V3_FOREIGN_TOOLS_NAMESPACE")
                if "tools" in self.before:
                    require(namespace is self.before["tools"], "V3_TOOLS_NAMESPACE_REPLACED")
                else:
                    self.before["tools"] = namespace
            rows = {}
            for name, module in self.before.items():
                require(sys.modules.get(name) is module, "V3_PROJECT_MODULE_REPLACED:" + name)
            for name, module in self.loaded.items():
                path = self.paths[name]
                require(sys.modules.get(name) is module and Path(module.__file__).resolve() == path.resolve()
                        and module.__spec__.origin == str(path), "V3_PROJECT_MODULE_REPLACED:" + name)
                rows[name] = {"path": str(path), "sha256": sha(self.raw(name))}
            observed = {n for n in sys.modules if n == "cas_meta2" or n.startswith(("cas_meta2.", "tools."))}
            require(observed <= set(self.loaded) | set(self.before), "V3_UNTRACKED_PROJECT_MODULE")
            return rows

    guard = Guard()
    sys.meta_path.insert(0, guard)
    try:
        from tools import inspect_cloud_packet as old
        from tools import experiment_profiles_v3 as registered
        repo, prefix = registered.git_context(ROOT)
        committed = registered.git_members(repo, prefix, expected_source_sha)
        require({name: sha(raw) for name, raw in committed.items()} == manifest["files_sha256"], "V3_COMPLETE_MANIFEST_DIFFERS_FROM_GIT")
        for name, raw in committed.items():
            path = no_links(ROOT.parent / name.removeprefix("research/"))
            require(path.is_file() and path.read_bytes() == raw, "V3_PACKAGED_LOCAL_SOURCE_DIFFERS_FROM_GIT:" + name)
        from cas_meta2.features_v2 import LosslessPublicTokenizer as tokenizer_type
        from cas_meta2.codec import action_to_ids as encode_action
        from cas_meta2.selection_v3 import depth_generated_metrics as metrics, selection_key as rank
        from cas_meta2 import curriculum_v3 as dataset_module
        legacy, profiles, Packet, safe_name = old, registered, old.Packet, old.safe_name
        _native, _verdict = old._native, old._verdict
        LosslessPublicTokenizer, action_to_ids = tokenizer_type, encode_action
        depth_generated_metrics, selection_key, curriculum = metrics, rank, dataset_module
        guard.verify()
        _IMPORT_GUARD = guard
    except BaseException:
        sys.meta_path.remove(guard)
        raise



STRESS = ("longest_input", "longest_target", "most_copy_occurrences")
SETTINGS = {"CUBLAS_WORKSPACE_CONFIG": ":4096:8", "deterministic_algorithms": True,
    "tf32_matmul": False, "tf32_cudnn": False, "cudnn_benchmark": False, "cudnn_deterministic": True}
CLEANUP_STEPS = ["synchronize_before", "collect_python_cycles",
    "clear_documented_cublas_and_cublaslt_workspaces", "empty_cuda_allocator_cache", "synchronize_after"]
COPY_NAMES = {"copy_query.weight", "copy_key.weight", "copy_gate.weight", "copy_gate.bias",
              "binding_query.weight", "binding_key.weight"}
POLICY_FILES = ("train_v3.py", "policy_v3.py", "features_v3.py", "grammar_v3.py", "selection_v3.py",
    "loss_v3.py", "policy.py", "features_v2.py", "codec.py", "ir.py", "curriculum_v3.py",
    "exclusions_v3.json", "development_exclusions_v3.json", "gpu_preflight_v3.py")


def _finite(value, *, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def _names(value):
    return type(value) is list and bool(value) and all(type(n) is str and n for n in value) and value == sorted(set(value))


def _runtime_cleanup(record, runtime, phases, *, expected_failure=False, settings_after=True):
    require(record.get("runtime_versions") == {"torch": "2.11.0+cu128", "cuda": "12.8"}
            and record.get("device") == "cuda:0" and record.get("gpu_name") == runtime["gpu"]
            and "T4" not in runtime["gpu"].upper(), "V3_CLEANUP_RUNTIME_MISMATCH")
    require(record.get("numerical_settings_before") == SETTINGS and (not settings_after or record.get("numerical_settings_after") == SETTINGS),
            "V3_NUMERICAL_SETTINGS_CHANGED")
    api = record["workspace_cleanup_api"]
    require(api.get("name") == "torch._C._cuda_clearCublasWorkspaces" and api.get("callable_verified") is True
            and api.get("documented_version") == "2.11", "V3_WORKSPACE_CLEANUP_API_UNCONFIRMED")
    require(set(record["cleanup"]) == set(phases) and bool(record.get("failures")) is expected_failure, "V3_CLEANUP_PHASE_COVERAGE")
    for phase in phases:
        item = record["cleanup"][phase]
        require(item.get("completed") is True and item.get("steps") == CLEANUP_STEPS, "V3_CLEANUP_STEPS_INCOMPLETE")
        for moment in ("before", "after"):
            require(set(item[moment]) == {"allocated_bytes", "reserved_bytes"}
                    and all(type(v) is int and v >= 0 for v in item[moment].values()), "V3_MEMORY_COUNTER_TYPE")
        require(item["after"] == {"allocated_bytes": 0, "reserved_bytes": 0}, "V3_ZERO_ALLOCATION_CLEANUP_REQUIRED")


def _geometry(training, config):
    from cas_meta2.features_v3 import encode_public_with_spans
    from cas_meta2.ir import validate_program
    tokenizer = LosslessPublicTokenizer.fit_train([t["public"] for t in training], max_length=1024)
    featured = [encode_public_with_spans(t["public"], tokenizer) for t in training]
    inputs = [len(row["encoded"]["ids"]) for row in featured]
    targets = [len(action_to_ids(t["target"], max_length=256)) for t in training]
    occurrences = [len(row["occurrences"]) for row in featured]
    depths = {str(d): sum(validate_program(t["target"]["program"])["max_call_depth"] == d for t in training) for d in (1, 2, 3)}
    require(len(training) == 3072 and depths == {"1": 1024, "2": 1024, "3": 1024}, "V3_PREFLIGHT_TRAIN_DEPTH_COUNTS")
    require(all(t["provenance"]["evaluation_group"] == "training" and t["provenance"]["triplet_id"] is None
                and re.fullmatch(r"meta2-v3-[a-f0-9]{16}-train-[0-9]{5}", t["task_id"]) for t in training),
            "V3_PREFLIGHT_REQUIRES_EXPLICIT_TRAINING")
    prefixes = {t["task_id"].split("-")[2] for t in training}
    require(len(prefixes) == 1 and len({t["task_id"] for t in training}) == 3072, "V3_PREFLIGHT_TRAIN_IDENTITY")
    batches = {}
    for label, values in zip(STRESS, (inputs, targets, occurrences)):
        indices = [i for _, i in sorted((-v, i) for i, v in enumerate(values))[:16]]
        batches[label] = {"selected_training_indices": indices, "selected_input_lengths": [inputs[i] for i in indices],
            "selected_target_lengths_including_bos_eos": [targets[i] for i in indices],
            "selected_copy_occurrence_counts": [occurrences[i] for i in indices],
            "actual_padded_input_tokens": max(inputs[i] for i in indices),
            "actual_padded_target_tokens_excluding_bos": max(targets[i] for i in indices) - 1,
            "actual_padded_copy_occurrences": max(1, max(occurrences[i] for i in indices)),
            "selected_public_sha256": sha(canonical([training[i]["public"] for i in indices])),
            "selected_target_sha256": sha(canonical([training[i]["target"] for i in indices]))}
    return tokenizer, {"training_examples": 3072, "batch_size": 16, "actual_ir_depth_counts": depths,
        "training_dataset_id_prefix": next(iter(prefixes)), "explicit_training_provenance_verified": True,
        "selection": "Three independent descending length/count sorts; original training row breaks ties. No synthetic or rewritten rows.",
        "tokenizer_digest": tokenizer.digest, "vocabulary_size": len(tokenizer.vocabulary),
        "training_tasks_sha256": sha(canonical(training)), "training_public_sha256": sha(canonical([t["public"] for t in training])),
        "maximum_training_input_tokens": max(inputs), "maximum_training_target_tokens_including_bos_eos": max(targets),
        "maximum_training_copy_occurrences": max(occurrences), "stress_batches": batches}


def _gate_layers(gates, geometry):
    require(type(gates) is list and len(gates) == 2, "V3_GATE_LAYER_COVERAGE")
    per_head = sum(geometry["selected_input_lengths"])
    for layer, row in enumerate(gates):
        require(type(row["layer"]) is int and row["layer"] == layer, "V3_GATE_LAYER_ORDER")
        active, valid = row["active_queries_per_head"], row["valid_queries_per_head"]
        require(type(active) is list and len(active) == 4
                and all(type(v) is int and 0 < v <= per_head for v in active)
                and type(valid) is list and all(type(v) is int for v in valid) and valid == [per_head] * 4,
                "V3_GATE_PER_HEAD_COUNTERS")
        fractions = [v / per_head for v in active]
        require(all(f >= .95 for f in fractions) and row["all_heads_meet_active_fraction"] is True,
                "V3_EVERY_HEAD_95_PERCENT_REQUIRED")
        require(type(row["active_fraction_per_head"]) is list and len(row["active_fraction_per_head"]) == 4
                and all(_finite(v) and math.isclose(v, e, abs_tol=1e-12) for v, e in zip(row["active_fraction_per_head"], fractions))
                and type(row["valid_queries"]) is int and row["valid_queries"] == per_head * 4
                and type(row["active_queries"]) is int and row["active_queries"] == sum(active)
                and _finite(row["active_fraction"]) and math.isclose(row["active_fraction"], sum(active) / (per_head * 4), abs_tol=1e-12),
                "V3_GATE_DERIVED_COUNTS_MISMATCH")


def _preflight_record(record, manifest, spec, job, runtime, geometry):
    require(record.get("schema") == "cas-meta2-copy-policy-gpu-preflight/3"
            and record.get("status") == "CAS_META_2_COPY_V3_GPU_PREFLIGHT_PASSED" and record.get("completed") is True
            and record.get("geometry_checks_completed") is True and record.get("memory_cleanup_confirmed") is True
            and record.get("training_tasks_unchanged") is True, "V3_ACTUAL_COPY_PREFLIGHT_REQUIRED")
    require(record.get("aws_job_id") == job and record.get("config") == spec["training"]
            and record.get("geometry") == geometry, "V3_PREFLIGHT_JOB_CONFIG_OR_GEOMETRY_MISMATCH")
    require(record.get("actual_copy_policy") is True and record.get("frozen_v2_geometry_called") is False
            and record.get("candidate_only") is True and type(record.get("optimizer_updates")) is int
            and record["optimizer_updates"] == 0 and all(record.get(k) is False for k in
            ("model_training_performed", "native_execution_performed", "held_out_labels_accessed")), "V3_PREFLIGHT_SCOPE_MISMATCH")
    expected = source_file(manifest, "cas_meta2/gpu_preflight_copy_v3.py")
    bound = record["geometry_source"]
    require(record["helper_sha256"] == bound["helper_sha256"] == expected
            and bound["factory"] == "cas_meta2.policy_v3.build_matched_policies"
            and bound["encoding"] == "cas_meta2.policy_v3.encode_batch"
            and bound["loss"] == "cas_meta2.loss_v3.weighted_training_loss", "V3_ACTUAL_FACTORY_SOURCE_MISMATCH")
    from cas_meta2.gpu_preflight_copy_v3 import PINNED_FILES
    from cas_meta2.loss_v3 import LOSS_CONTRACT, loss_weight_rows
    require(bound["files_sha256"] == PINNED_FILES and record["loss_contract"] == LOSS_CONTRACT, "V3_LOSS_SOURCE_CONTRACT_MISMATCH")
    for name, checksum in bound["files_sha256"].items():
        require(source_file(manifest, "cas_meta2/" + name) == checksum, "V3_PREFLIGHT_DEPENDENCY_NOT_ARCHIVED")
    matching, initial = record["parameter_matching"], record["initial_matching"]
    counts = {f: matching[f + "_trainable_parameters"] for f in ("cas", "generic")}
    require(all(type(v) is int and v > 0 for v in counts.values()) and initial["counts"] == counts
            and matching["frozen_candidate_parameter_names"] == [], "V3_PREFLIGHT_PARAMETER_COUNTS")
    difference = abs(counts["cas"] - counts["generic"]) / counts["cas"]
    require(difference <= .01 and _finite(matching["relative_difference"])
            and math.isclose(difference, matching["relative_difference"], abs_tol=1e-12), "V3_PREFLIGHT_PARAMETER_MATCH")
    common = initial["identical_common_initial_parameter_names"]
    require(_names(common) and COPY_NAMES <= set(common) and common == matching["common_initial_parameter_names"],
            "V3_COMMON_COPY_BINDING_INITIALIZATION")
    require(set(record["stress_batches"]) == set(STRESS), "V3_ALL_THREE_STRESS_BATCHES_REQUIRED")
    gradients = {}
    for label in STRESS:
        stress = record["stress_batches"][label]
        require(stress["geometry"] == geometry["stress_batches"][label] and set(stress["families"]) == {"cas", "generic"}
                and _finite(stress["positive_loss_weight_sum"], minimum=1), "V3_STRESS_GEOMETRY_OR_WEIGHT_MISMATCH")
        for family, observed in stress["families"].items():
            require(observed["all_parameters_cuda"] is True and observed["all_buffers_cuda"] is True
                    and type(observed["optimizer_updates"]) is int and observed["optimizer_updates"] == 0
                    and observed["all_trainable_parameter_tensors_have_finite_nonzero_gradient"] is True
                    and observed["missing_or_invalid_gradient_parameter_names"] == []
                    and observed["causal_future_token_check"] is True, "V3_STRESS_GRADIENT_DEVICE_OR_CAUSAL_FAILURE")
            names = observed["finite_nonzero_gradient_parameter_names"]
            require(_names(names) and set(common) <= set(names), "V3_GRADIENT_NAMES_INCOMPLETE")
            require(family not in gradients or gradients[family] == names, "V3_STRESS_GRADIENT_COVERAGE_CHANGED")
            gradients[family] = names
            require(_finite(observed["weighted_training_loss"])
                    and _finite(observed["copy_gate_min"]) and _finite(observed["copy_gate_max"])
                    and 0 <= observed["copy_gate_min"] <= observed["copy_gate_max"] <= 1, "V3_STRESS_LOSS_OR_COPY_METRIC_INVALID")
            if family == "cas":
                _gate_layers(observed["gate_layers"], stress["geometry"])
            else:
                require(observed["gate_layers"] == [], "V3_GENERIC_CAS_GATE_CLAIM")
    _runtime_cleanup(record, runtime, ("baseline", "final"))
    require(record["cuda_allocated_bytes_before"] == record["cuda_allocated_bytes_after_cleanup"] == 0
            and record["cuda_reserved_bytes_before"] == record["cuda_reserved_bytes_after_cleanup"] == 0,
            "V3_PREFLIGHT_ZERO_MEMORY_REQUIRED")
    values = [record[k] for k in ("peak_cuda_allocated_bytes", "peak_cuda_reserved_bytes", "gpu_total_memory_bytes")]
    require(all(type(v) is int for v in values) and 0 < values[0] <= values[1] <= values[2], "V3_PREFLIGHT_PEAK_MEMORY_INVALID")
    return {"gradient_parameter_names": gradients, "tokenizer_digest": geometry["tokenizer_digest"],
            "stress_batches": list(STRESS), "peak_cuda_allocated_bytes": values[0], "geometry": geometry}


def _preflight(packet, campaign, manifest, spec, job):
    record = packet.json(BASE + "gpu_preflight_copy_v3.json")
    require(record == campaign.get("gpu_preflight"), "V3_PREFLIGHT_RECEIPT_COPY_MISMATCH")
    train = packet.json(BASE + "dataset/train.json")
    _, geometry = _geometry(train, spec["training"])
    result = _preflight_record(record, manifest, spec, job, packet.json("cloud_job/runtime.json"), geometry)
    from cas_meta2.loss_v3 import loss_weight_rows
    for label in STRESS:
        indices = geometry["stress_batches"][label]["selected_training_indices"]
        rows = loss_weight_rows([train[i]["target"] for i in indices])
        total = sum(sum(row) for row in rows["weights"])
        require(record["stress_batches"][label]["positive_loss_weight_sum"] == total, "V3_PREFLIGHT_LOSS_WEIGHT_MASS_MISMATCH")
    return result


def _remote_member(path):
    marker = "/" + BASE
    require(type(path) is str and path.startswith("/") and path.count(marker) == 1, "V3_REMOTE_ARTIFACT_PATH_INVALID")
    return safe_name("cloud_job/campaign/" + path.split(marker, 1)[1])


def _process(packet, folder):
    record = packet.json(folder + "/process_receipt.json")
    require(record.get("schema") == "cas-meta2-campaign-subprocess/3" and record.get("completed") is True
            and type(record.get("returncode")) is int and record["returncode"] == 0
            and record.get("timed_out") is False and record.get("new_process_group") is True
            and record.get("automatic_retry") is False and type(record.get("pid")) is int and record["pid"] > 0
            and _finite(record.get("wall_seconds")), "V3_SUCCESSFUL_SEPARATE_PROCESS_REQUIRED")
    for stream in ("stdout", "stderr"):
        require(_remote_member(record[stream]) == folder + "/" + stream + ".txt", "V3_SUBPROCESS_STREAM_PATH")
        packet.same_hash(folder + "/" + stream + ".txt", record[stream + "_sha256"])
    return record


def _construction(packet, spec):
    record = packet.json(BASE + "dataset_construction_receipt.json")
    folder = BASE + "dataset_construction"
    process = _process(packet, folder)
    require(record.get("schema") == "cas-meta2-dataset-construction/3" and record.get("completed") is True
            and record.get("separate_process") is True and record.get("returncode") == 0
            and type(record.get("seed")) is int and record["seed"] == spec["curriculum"]["seed"]
            and type(record.get("combined_excluded_graphs")) is int and record["combined_excluded_graphs"] == 4488,
            "V3_DATASET_CONSTRUCTION_RECEIPT_INVALID")
    require(_remote_member(record["process_receipt"]) == folder + "/process_receipt.json", "V3_CONSTRUCTOR_PROCESS_PATH")
    packet.same_hash(folder + "/process_receipt.json", record["process_receipt_sha256"])
    packet.same_hash(BASE + "dataset/dataset_manifest.json", record["dataset_manifest_sha256"])
    command = record["command"]
    require(command == process["command"] and len(command) == 6 and command[1:3] == ["-B", "-c"]
            and command[3] == "import sys;from cas_meta2.curriculum_v3 import write_dataset,registered_development_exclusions;"
            "write_dataset(sys.argv[1],seed=int(sys.argv[2]),excluded_graph_signatures=registered_development_exclusions())"
            and _remote_member(command[4] + "/train.json") == BASE + "dataset/train.json"
            and command[5] == str(spec["curriculum"]["seed"]), "V3_CONSTRUCTION_COMMAND_MISMATCH")
    return {"separate_process_recorded": True, "excluded_graphs": 4488, "manifest_sha256": record["dataset_manifest_sha256"]}


def _property(case, name):
    rows = [child for child in case.findall("./properties/property") if child.get("name") == name]
    require(len(rows) == 1, "V3_GPU_PROPERTY_COVERAGE:" + name)
    return json_bytes(rows[0].get("value", "").encode("utf-8"))


def _campaign_gates(packet, campaign, manifest, spec, job):
    record = packet.json(BASE + "gpu_gates_v3.json")
    require(record == campaign.get("gpu_gates") and record.get("schema") == "cas-meta2-campaign-gpu-gates/3"
            and record.get("completed") is True and record.get("passed_cases") == record.get("expected_total_cases") == 5
            and record.get("actual_copy_modes") == 3 and record.get("trainer_integration_cases") == 2
            and set(record["groups"]) == {"actual_copy", "trainer"}, "V3_CAMPAIGN_FIVE_GPU_CASES_REQUIRED")
    require(_remote_member(record["training_file"]) == BASE + "dataset/train.json", "V3_GPU_TRAIN_FILE_PATH")
    packet.same_hash(BASE + "dataset/train.json", record["training_sha256"])
    expected = {"actual_copy": {"test_actual_copy_training_geometry_zero_cleanup_in_fresh_process[" + mode + "]"
                               for mode in ("cold", "warm", "repeated")},
                "trainer": {"test_real_paired_update_and_format3_checkpoint_reload",
                            "test_real_cuda_outer_cleanup_with_explicit_mock_inner_frame"}}
    cases_by_group, processes = {}, {}
    for group in expected:
        folder, row = BASE + "gpu_tests/" + group, record["groups"][group]
        process = _process(packet, folder)
        processes[group] = process
        require(process == row["process"] and row["expected_cases"] == len(expected[group]), "V3_GPU_PROCESS_COPY")
        packet.same_hash(folder + "/process_receipt.json", row["process_receipt_sha256"])
        xml = row["junit"]
        require(_remote_member(xml["path"]) == folder + "/junit.xml"
                and xml["tests"] == xml["passed"] == len(expected[group])
                and xml["failed"] == xml["errors"] == xml["skipped"] == 0, "V3_GPU_JUNIT_COPY_COUNTS")
        packet.same_hash(folder + "/junit.xml", xml["sha256"])
        cases = _xml_cases(packet.raw(folder + "/junit.xml"), expected[group])
        expected_rows = [{"classname": case.get("classname"), "name": case.get("name"),
                          "failed": False, "error": False, "skipped": False} for case in cases]
        require(xml["cases"] == expected_rows, "V3_GPU_JUNIT_CASE_COPY")
        test_file = spec["gpu_gates"]["actual_copy_test_file" if group == "actual_copy" else "trainer_test_file"]
        command = process["command"]
        require(row["test_file"] == test_file and len(command) == 12
                and command[1:9] == ["-B", "-m", "pytest", "-m", "gpu", "-q", "-p", "no:cacheprovider"]
                and command[9] == "--junitxml=" + xml["path"]
                and command[10].startswith("--basetemp=")
                and _remote_member(command[10].removeprefix("--basetemp=") + "/probe") == folder + "/basetemp/probe"
                and command[11] == test_file, "V3_CAMPAIGN_GPU_COMMAND_MISMATCH")
        require(all(case.get("classname", "").endswith(Path(test_file).stem) for case in cases), "V3_GPU_TEST_MODULE_MISMATCH")
        cases_by_group[group] = cases
    runtime = packet.json("cloud_job/runtime.json")
    training = packet.json(BASE + "dataset/train.json")
    _, geometry = _geometry(training, spec["training"])
    paths, pids = set(), set()
    for case in cases_by_group["actual_copy"]:
        mode = case.get("name").split("[")[1][:-1]
        envelope = _property(case, "actual_copy_v3_training_geometry")
        require(envelope["mode"] == mode and type(envelope["pid"]) is int and envelope["pid"] > 0
                and envelope["parent_pid"] == processes["actual_copy"]["pid"] and envelope["pid"] != envelope["parent_pid"]
                and envelope["pid"] not in pids and envelope["training_bytes_unchanged"] is True
                and envelope["training_sha256"] == record["training_sha256"]
                and envelope["optimizer_updates"] == 0 and envelope["private_evaluation_opened"] is False,
                "V3_COPY_MODE_PROCESS_OR_TRAINING_BINDING")
        pids.add(envelope["pid"])
        require(len(envelope["receipts"]) == (2 if mode == "repeated" else 1), "V3_COPY_MODE_ITERATION_COVERAGE")
        iteration_folders = []
        for index, path in enumerate(envelope["receipts"]):
            member = _remote_member(path)
            require(member.startswith(BASE + "gpu_tests/actual_copy/basetemp/")
                    and member.endswith(f"/iteration_{index}/gpu_preflight_copy_v3.json") and member not in paths,
                    "V3_COPY_ITERATION_PATH_OR_DUPLICATE")
            paths.add(member)
            iteration_folders.append(member.rsplit("/", 2)[0])
            saved = packet.json(member)
            _preflight_record(saved, manifest, spec, job, runtime, geometry)
            entry = saved["entry_memory"]["allocated_bytes"]
            require(type(entry) is int and (entry > 0 if mode == "warm" else entry == 0), "V3_COLD_WARM_ENTRY_NOT_EXERCISED")
        require(len(set(iteration_folders)) == 1, "V3_REPEATED_MODE_DIRECTORY_MISMATCH")
        stdout = packet.raw(iteration_folders[0] + "/child_stdout.txt")
        require(json_bytes(stdout.strip().splitlines()[-1]) == envelope, "V3_CHILD_RAW_OUTPUT_COPY")
        require(iteration_folders[0] + "/child_stderr.txt" in packet.inventory, "V3_CHILD_STDERR_MISSING")
    observed = {n for n in packet.inventory if n.startswith(BASE + "gpu_tests/actual_copy/") and n.endswith("/gpu_preflight_copy_v3.json")}
    require(observed == paths and len(paths) == 4, "V3_EXACT_FOUR_MODE_RECEIPTS_REQUIRED")
    _trainer_fixtures(packet, cases_by_group["trainer"], runtime)
    return {"cases": 5, "actual_copy_mode_receipts": 4, "trainer_integration_cases": 2,
            "boundary": "Retained AWS test records; no local checkpoint/model execution."}


def _trainer_fixtures(packet, cases, runtime):
    checkpoint_case = next(c for c in cases if c.get("name") == "test_real_paired_update_and_format3_checkpoint_reload")
    cleanup_case = next(c for c in cases if c.get("name") == "test_real_cuda_outer_cleanup_with_explicit_mock_inner_frame")
    checkpoint = _property(checkpoint_case, "authored_checkpoint_cuda")
    cleanup = _property(cleanup_case, "authored_real_cuda_cleanup")
    prefix = BASE + "gpu_tests/trainer/basetemp/"
    for name, value in (("authored_checkpoint_receipt.json", checkpoint), ("authored_cleanup_receipt.json", cleanup)):
        paths = [p for p in packet.inventory if p.startswith(prefix) and p.endswith("/" + name)]
        require(len(paths) == 1 and packet.json(paths[0]) == value, "V3_AUTHORED_RECEIPT_FILE_COPY:" + name)
    require(checkpoint.get("schema") == "cas-meta2-authored-checkpoint-test/3" and checkpoint.get("fixture_only") is True
            and checkpoint.get("curriculum_files_read") is False and checkpoint.get("heldout_labels_accessed") is False
            and checkpoint["paired_optimizer_steps"] == {"cas": 1, "generic": 1}
            and set(checkpoint["family_results"]) == {"cas", "generic"}, "V3_AUTHORED_CHECKPOINT_SCOPE")
    paths = set()
    for family, value in checkpoint["family_results"].items():
        require(type(value["optimizer_steps"]) is int and value["optimizer_steps"] == 1 and value["before_after_changed"] is True
                and value["rejected_identity_changes"] == ["sha256", "family", "policy_source_sha256", "epoch", "config", "tokenizer"]
                and _finite(value["weighted_loss_before_step"]) and set(value["reload"]) == {"initial", "selected"},
                "V3_AUTHORED_UPDATE_OR_REJECTION_COVERAGE")
        for state, observed in value["reload"].items():
            path = _remote_member(observed["path"])
            require(path.startswith(prefix) and path.endswith("/" + family + "_" + state + ".pt")
                    and path not in paths and observed["output_exactly_reproduced"] is True, "V3_AUTHORED_CHECKPOINT_RELOAD")
            packet.same_hash(path, observed["sha256"])
            paths.add(path)
    require({p for p in packet.inventory if p.startswith(prefix) and p.endswith(".pt")} == paths, "V3_AUTHORED_FOUR_CHECKPOINT_FILES")
    _runtime_cleanup(checkpoint["cleanup"], runtime, ("before_authored_checkpoint_frame", "after_authored_checkpoint_frame"),
                     settings_after=False)
    require(cleanup.get("schema") == "cas-meta2-authored-cleanup-test/3" and cleanup.get("explicit_mock_inner_frame") is True
            and cleanup.get("real_cuda_allocation_and_backward") is True and cleanup.get("actual_outer_trainer_cleanup") is True
            and cleanup.get("curriculum_files_read") is False and cleanup.get("heldout_labels_accessed") is False
            and set(cleanup["cases"]) == {"success", "failure"}, "V3_AUTHORED_CLEANUP_SCOPE")
    for name, row in cleanup["cases"].items():
        failure = name == "failure"
        require(row["schema"] == "cas-meta2-training-cleanup/3" and row["completed"] is (not failure)
                and row["status"] == "CAS_META_2_V3_TRAINING_CLEANUP_" + ("BLOCKED" if failure else "PASSED"),
                "V3_AUTHORED_CLEANUP_STATUS")
        if failure:
            require(len(row["failures"]) == 1 and row["failures"][0]["stage"] == "training"
                    and row["failures"][0]["message"] == "DELIBERATE_AUTHORED_CUDA_FRAME_FAILURE",
                    "V3_AUTHORED_FAILURE_NOT_EXPECTED")
        _runtime_cleanup(row, runtime, ("before_training", "after_training_frame_exit"), expected_failure=failure)
        files = [p for p in packet.inventory if p.startswith(prefix) and p.endswith("/" + name + "/training_cleanup_v3.json")]
        require(len(files) == 1 and packet.json(files[0]) == row, "V3_AUTHORED_CLEANUP_FILE_COPY")


def _training_cleanup(packet, campaign):
    record = packet.json(BASE + "training_cleanup_v3.json")
    require(record.get("schema") == "cas-meta2-training-cleanup/3"
            and record.get("status") == "CAS_META_2_V3_TRAINING_CLEANUP_PASSED"
            and record.get("completed") is True and record.get("failures") == [], "V3_TRAINING_CLEANUP_REQUIRED")
    require(record == campaign.get("training_cleanup"), "V3_TRAINING_CLEANUP_COPY_MISMATCH")
    _runtime_cleanup(record, packet.json("cloud_job/runtime.json"), ("before_training", "after_training_frame_exit"))
    return {"completed": True, "both_phases_zero": True, "boundary": "Saved CUDA cleanup record; not local GPU execution or provider cleanup."}


COPY_GPU_CASES = {
    "test_cuda_guard_precedes_candidate_construction", "test_identical_shared_initialization_and_finite_nonzero_task_gradients",
    "test_mean_pooling_covers_all_byte_fallback_rows", "test_repeated_spelling_copy_mass_is_aggregated_in_fixed_vocabulary",
    "test_no_symbols_uses_exact_fixed_head_and_keeps_binding_pointer_active", "test_causal_copy_scores_cannot_see_future_decoder_tokens",
    "test_occurrence_scope_refuses_observation_and_invalid_destination_ids",
    "test_same_grammar_blocks_disallowed_high_logits_and_never_repairs_bounded_dead_end",
    "test_mixed_symbol_and_no_symbol_rows_remain_finite_with_correct_mass", "test_rejected_row_evidence_excludes_inactive_batch_padding"}
LOSS_GPU_CASES = {"test_weighted_nll_matches_independent_sum_and_pad_gradients_are_zero",
    "test_weight_encoding_rejects_misaligned_target_or_decoder_inputs"} | {
    "test_invalid_weights_are_refused[" + name + "]" for name in ("negative", "nan", "zero_valid", "positive_pad", "learnable", "cpu")} | {
    "test_bad_log_probabilities_and_target_layout_are_refused[" + name + "]"
    for name in ("raw_logits", "nan", "wrong_vocabulary", "bad_valid", "bad_lengths")}


def _xml_cases(raw, expected):
    require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "XML_DECLARATION_REFUSED")
    root = ET.fromstring(raw)
    suites, cases = list(root.iter("testsuite")), list(root.iter("testcase"))
    require(suites and all(not list(suite.iter("testsuite"))[1:] for suite in suites), "NESTED_GPU_TEST_SUITES_REFUSED")
    totals = {key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}
    require(totals == {"tests": len(expected), "failures": 0, "errors": 0, "skipped": 0}
            and len(cases) == len(expected) and {case.get("name") for case in cases} == set(expected),
            "V3_GPU_TEST_COUNTS_OR_IDENTITIES_MISMATCH")
    require(all(not any(child.tag in ("failure", "error", "skipped") for child in case) for case in cases),
            "V3_HIDDEN_GPU_TEST_FAILURE")
    return cases


def _gpu_gate(packet, family):
    if family == "contract":
        return legacy._gpu_gate(packet, family)
    require(family == "policy", "V3_UNKNOWN_GPU_GATE")
    prefix = "cloud_job/gpu_policy"
    expected = legacy.GPU_CASES["policy"] | COPY_GPU_CASES | LOSS_GPU_CASES
    require(len(expected) == 27, "V3_GPU_CASE_REGISTRATION_ERROR")
    require(packet.json(prefix + "_receipt.json") == {"passed": 27, "tests": 27, "failures": 0, "errors": 0, "skipped": 0},
            "V3_EARLY_POLICY_27_REQUIRED")
    _xml_cases(packet.raw(prefix + "_tests.xml", 2 * 1024**2), expected)
    command = packet.json(prefix + "_command.json")
    require(type(command) is list and all(type(s) is str for s in command) and len(command) == 13
            and command[1:10] == ["-m", "pytest", "-m", "gpu", "tests/test_policy_gpu.py", "tests/test_policy_v3_gpu.py",
                                  "tests/test_loss_v3_gpu.py", "-q", "--junitxml"]
            and command[10].endswith("/gpu_policy_tests.xml") and command[11:] == ["-p", "no:cacheprovider"],
            "V3_EARLY_GPU_COMMAND_MISMATCH")
    require(prefix + "_tests.log" in packet.inventory, "V3_EARLY_GPU_RAW_LOG_MISSING")
    return {"passed": 27, "tests": sorted(expected)}


def _experiment_spec(manifest, path=None):
    require(type(manifest) is dict and "experiment" in manifest, "V3_EXPLICIT_MANIFEST_REQUIRED")
    path = no_links(path or ROOT / "EXPERIMENT_V3.json")
    raw = path.read_bytes()
    require(sha(raw) == source_file(manifest, "EXPERIMENT_V3.json"), "V3_SPEC_SOURCE_MISMATCH")
    experiment = profiles.validate_manifest(manifest, lambda name: raw)
    spec = profiles.validate_v3_spec(raw)
    from cas_meta2.campaign_v3 import validate_experiment
    validate_experiment(spec)
    require(spec["curriculum"]["seed"] == 20260919
            and spec["curriculum"]["counts"] == {"train": 3072, "validation": 96, "test": 72}
            and spec["training"]["seed"] == 7 and spec["training"]["epochs"] == 60
            and spec["training"]["validation_generation_interval"] == 5
            and spec["training"]["batch_size"] == 16 and spec["evaluation"]["arms"] == list(ARMS),
            "V3_REGISTERED_LEARNING_CONTRACT_REQUIRED")
    require(spec["evaluation"]["checkpoints"]["format"] == "cas-meta2-candidate-checkpoint/3"
            and spec["curriculum"]["exclusions"]["combined_count"] == 4488
            and spec["selection"]["train_probe_used_for_selection"] is False, "V3_CHECKPOINT_EXCLUSION_SELECTION_CONTRACT")
    return experiment, spec


def _source_binding(campaign, manifest, source_sha):
    experiment = profiles.validate_manifest(manifest)
    require(campaign.get("experiment") == experiment, "V3_CAMPAIGN_EXPERIMENT_MISMATCH")
    source = campaign.get("source")
    require(type(source) is dict, "V3_CAMPAIGN_SOURCE_MISSING")
    from cas_meta2.campaign_v3 import SOURCE_TESTS
    extras = ("EXPERIMENT_V3.json", "requirements-gpu.txt", "cas_meta2/exclusions_v3.json", "cas_meta2/development_exclusions_v3.json",
              *("tests/" + name for name in SOURCE_TESTS))
    for name in extras:
        require(source.get(name) == source_file(manifest, name), "V3_ASSET_SOURCE_BINDING_MISSING:" + name)
    # Only separately verified new assets are removed from this detached view.
    # All accepted native byte checks remain unchanged; original data is untouched.
    checked = legacy._source_binding({**campaign, "source": {k: v for k, v in source.items() if k not in extras}}, manifest, source_sha)
    for name, expected in source.items():
        require(source_file(manifest, name) == expected, "V3_CURRENT_SOURCE_DIFFERS_FROM_EXECUTED_SOURCE:" + name)
    return {**checked, "source_files_bound": checked["source_files_bound"] + len(extras), "experiment": experiment}


def _command(packet, experiment, smoke_only):
    argv = packet.json("cloud_job/command.json")
    require(type(argv) is list and all(type(item) is str for item in argv) and len(argv) in (7, 8),
            "V3_CAMPAIGN_COMMAND_INVALID")
    require(argv[1:3] == ["-m", experiment["entrypoint"]] and argv[3] == "--output"
            and argv[4].endswith("/research/CAS_META_2_COMPOSITION/runs/cloud_job/campaign")
            and argv[5] == "--max-wall-seconds" and re.fullmatch(r"[0-9]+", argv[6]) is not None
            and 60 <= int(argv[6]) <= 6600, "V3_ENTRYPOINT_OR_COMMAND_BINDING_MISMATCH")
    require(argv[7:] == (["--smoke-only"] if smoke_only else []), "V3_COMMAND_MODE_MISMATCH")
    return {"entrypoint": argv[2], "max_wall_seconds": int(argv[6]), "smoke_only": smoke_only}


def _dataset(packet, spec):
    manifest = packet.json(BASE + "dataset/dataset_manifest.json")
    extras = curriculum.registered_development_exclusions()
    base, _ = curriculum.exclusion_inventory()
    require(len(base) == 4312 and len(extras) == 177 and len(base & extras) == 1 and len(base | extras) == 4488,
            "V3_4488_EXCLUSIONS_REQUIRED")
    curriculum.validate_manifest(manifest, expected_counts=spec["curriculum"]["counts"],
        expected_seed=spec["curriculum"]["seed"], excluded_graph_signatures=extras)
    for name, checksum in manifest["sha256"].items():
        packet.same_hash(BASE + "dataset/" + name, checksum)
    _reconstruct_dataset(packet, manifest, extras)
    return manifest


def _reconstruct_dataset(packet, manifest, extras):
    """Cold JSON reconstruction shared by full acceptance and tiny API tests."""
    document = {"schema": "cas-meta2-curriculum/3", "seed": manifest["seed"], "dataset_id": manifest["dataset_id"], "splits": {
        "train": packet.json(BASE + "dataset/train.json"), "validation": packet.json(BASE + "dataset/validation.json"),
        "test": packet.json(BASE + "dataset/test_private.json")}}
    require(packet.json(BASE + "dataset/test_public.json") == [t["public"] for t in document["splits"]["test"]],
            "V3_PUBLIC_PRIVATE_MAPPING_MISMATCH")
    # validate_dataset reads explicit definition_order after JSON reload. No
    # insertion-order adapter or alteration of the saved target is permitted.
    before = sha(canonical(document))
    checked = curriculum.validate_dataset(document, excluded_graph_signatures=extras)
    require(sha(canonical(document)) == before, "V3_DATASET_CHANGED_BY_VALIDATOR")
    for key, value in checked.items():
        require(manifest.get(key) == value, "V3_RECONSTRUCTED_CURRICULUM_MISMATCH:" + key)
    return manifest


def _training_v3(packet, campaign, spec, manifest, seal):
    training = packet.json(BASE + "training_receipt.json")
    require(training == campaign.get("training"), "TRAINING_RECEIPT_COPY_MISMATCH")
    prereg = packet.json(BASE + "training_preregistration.json")
    require(prereg.get("schema") == "cas-meta2-learning-preregistration/3", "V3_PREREGISTRATION_SCHEMA_REQUIRED")
    config, registered = prereg["config"], spec["training"]
    require(type(config) is dict and set(config) == set(registered), "V3_TRAINING_CONFIG_FIELDS_MISMATCH")
    for name, expected in registered.items():
        if name == "max_training_seconds":
            require(type(config[name]) is int and 1 <= config[name] <= expected, "V3_TRAINING_TIME_ALLOCATION_INVALID")
        else:
            require(config[name] == expected, "V3_TRAINING_CONFIG_MISMATCH:" + name)
    require(prereg["train_examples"] == 3072 and prereg["validation_examples"] == 96 and prereg["test_examples"] == 72,
            "V3_PREREGISTERED_COUNTS_MISMATCH")
    require(prereg["arms"] == list(ARMS) and prereg["dataset_sha256"] == manifest["sha256"], "V3_PREREGISTERED_INPUT_MISMATCH")
    expected_source = {name: campaign["source"]["cas_meta2/" + name] for name in POLICY_FILES}
    require(prereg.get("policy_source_sha256") == expected_source, "V3_PREREG_POLICY_SOURCE_MISMATCH")
    require(prereg.get("fixed_validation_depth_counts") == {"1": 32, "2": 32, "3": 32}, "V3_FIXED_VALIDATION_DEPTHS")
    train = packet.json(BASE + "dataset/train.json")
    validation_tasks = packet.json(BASE + "dataset/validation.json")
    publics = packet.json(BASE + "dataset/test_public.json")
    require(len(train) == 3072 and len(validation_tasks) == 96 and len(publics) == 72, "V3_LEARNING_COUNTS_MISMATCH")
    tokenizer_record = packet.json(BASE + "tokenizer.json")
    tokenizer = LosslessPublicTokenizer.from_dict(tokenizer_record)
    rebuilt = LosslessPublicTokenizer.fit_train([task["public"] for task in train], max_length=config["policy"]["max_length"])
    require(tokenizer_record == rebuilt.to_dict() and tokenizer.digest == seal["tokenizer_digest"],
            "V3_TOKENIZER_NOT_EXACTLY_TRAIN_FITTED")
    round_trips = [task["public"] for task in train + validation_tasks] + publics
    for public in round_trips:
        require(tokenizer.check_round_trip(public) is True, "V3_PUBLIC_TEXT_ROUND_TRIP_FAILED")
    checkpoints = packet.json(BASE + "checkpoints.json")
    require(checkpoints == training["checkpoints"] and set(checkpoints) == {"cas", "generic"}, "V3_CHECKPOINT_RECEIPT_MISMATCH")
    complete = training["completed_epochs"]
    require(type(complete) is int and 1 <= complete <= training["requested_epochs"] == registered["epochs"],
            "V3_COMPLETED_EPOCHS_INVALID")
    require(training["learning_conditions_matched"] is True, "V3_MATCHED_LEARNING_REQUIRED")
    steps_per_epoch = math.ceil(3072 / config["batch_size"])
    require(training["optimizer_steps"] == {family: complete * steps_per_epoch for family in ("cas", "generic")},
            "V3_OPTIMIZER_STEPS_MISMATCH")
    history = packet.json(BASE + "training_history.json")
    require(type(history) is list and len(history) == complete
            and [row["epoch"] for row in history] == list(range(1, complete + 1)), "V3_HISTORY_COVERAGE_MISMATCH")
    eligible = {epoch for epoch in range(1, complete + 1)
                if epoch == 1 or epoch % registered["validation_generation_interval"] == 0 or epoch == registered["epochs"]}
    expected_files = {BASE + f"validation_predictions/{family}_epoch_{epoch:04d}.json"
                      for family in ("cas", "generic") for epoch in eligible}
    actual_files = {name for name in packet.inventory if name.startswith(BASE + "validation_predictions/")}
    optional_initial = {BASE + f"validation_predictions/{family}_epoch_0000.json" for family in ("cas", "generic")}
    require(actual_files == expected_files | optional_initial, "V3_VALIDATION_PREDICTION_COVERAGE_MISMATCH")
    train_probe = []
    from cas_meta2.ir import validate_program
    from cas_meta2.selection_v3 import target_loss_weights
    total_weights = sum(sum(target_loss_weights(t["target"])) for t in train)
    total_tokens = sum(len(action_to_ids(t["target"])) - 1 for t in train)
    for depth in (1, 2, 3):
        members = sorted((t for t in train if validate_program(t["target"]["program"])["max_call_depth"] == depth),
                         key=lambda task: task["task_id"])
        require(len(members) == 1024, "V3_TRAINING_DEPTH_DENOMINATOR")
        train_probe.extend(members[:8])
    probe_ids = [t["task_id"] for t in train_probe]
    require(prereg["training_probe"]["selection_use"] is False and prereg["training_probe"]["examples"] == 24
            and prereg["training_probe"]["task_ids"] == probe_ids, "V3_TRAINING_PROBE_SOURCE_MISMATCH")
    probe_files = {BASE + f"train_probe_predictions/{family}_epoch_{epoch:04d}.json"
                   for family in ("cas", "generic") for epoch in eligible | {0}}
    require({n for n in packet.inventory if n.startswith(BASE + "train_probe_predictions/")} == probe_files,
            "V3_TRAINING_PROBE_COVERAGE")
    for name in probe_files:
        saved = packet.json(name)
        require(saved["split"] == "train" and saved["used_for_checkpoint_selection"] is False and saved["task_ids"] == probe_ids
                and name.endswith(f'_epoch_{saved["epoch"]:04d}.json'), "V3_TRAINING_PROBE_ROLE_MISMATCH")
        require(saved["metrics"] == depth_generated_metrics(saved["actions"], train_probe), "V3_TRAINING_PROBE_METRICS_MISMATCH")
    checkpoint_digests, selected_epochs = {}, {}
    for family in ("cas", "generic"):
        require(set(checkpoints[family]) == {"initial", "selected", "last"}, "V3_SIX_CHECKPOINTS_REQUIRED")
        best_epoch, best_key = None, None
        for row in history:
            epoch = row["epoch"]
            require(row["optimizer_steps"] == {name: epoch * steps_per_epoch for name in ("cas", "generic")},
                    "V3_EPOCH_STEP_COUNT_MISMATCH")
            require(set(row["families"]) == {"cas", "generic"}, "V3_HISTORY_FAMILY_COVERAGE_MISMATCH")
            family_row = row["families"][family]
            require(_finite(family_row["training_weighted_token_nll"])
                    and type(family_row["training_tokens"]) is int and family_row["training_tokens"] == total_tokens
                    and family_row["training_weight_sum"] == total_weights, "V3_TRAINING_WEIGHT_OR_TOKEN_COUNTS")
            score = family_row["validation"]
            require(type(score["epoch"]) is int and score["epoch"] == epoch, "V3_VALIDATION_EPOCH_MISMATCH")
            require(type(score["token_cross_entropy"]) in (int, float)
                    and math.isfinite(score["token_cross_entropy"]) and score["token_cross_entropy"] >= 0,
                    "V3_VALIDATION_LOSS_INVALID")
            changed = False
            if epoch in eligible:
                saved = packet.json(BASE + f"validation_predictions/{family}_epoch_{epoch:04d}.json")
                require(saved["epoch"] == epoch and saved["split"] == "validation"
                        and saved["test_gold_access"] is False, "V3_VALIDATION_PREDICTION_ROLE_MISMATCH")
                recomputed = depth_generated_metrics(saved["actions"], validation_tasks)
                require(recomputed["overall"]["total"] == 96 and set(recomputed["by_depth"]) == {"1", "2", "3"}
                        and all(row["total"] == 32 for row in recomputed["by_depth"].values()), "V3_GENERATED_DEPTH_DENOMINATORS")
                require(saved["metrics"] == recomputed == score.get("generation"), "V3_GENERATED_VALIDATION_METRICS_MISMATCH")
                key = selection_key(score)
                changed = best_key is None or key > best_key
                if changed:
                    best_epoch, best_key = epoch, key
            else:
                require("generation" not in score, "V3_INELIGIBLE_GENERATION_RECORDED")
            require(type(family_row["selected"]) is bool and family_row["selected"] is changed,
                    "V3_EPOCH_SELECTION_HISTORY_MISMATCH")
        selected_epochs[family] = best_epoch
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            row = checkpoints[family][state]
            name = f"candidate_{family}_{suffix}.pt"
            require(set(row) == {"schema", "family", "policy_source_sha256", "path", "sha256", "bytes", "epoch", "optimizer_steps", "validation"}
                    and row.get("schema") == "cas-meta2-candidate-checkpoint/3" and row["family"] == family
                    and row["policy_source_sha256"] == expected_source, "V3_DECLARED_CHECKPOINT_SCHEMA_OR_SOURCE_REQUIRED")
            require(type(row["path"]) is str and row["path"].startswith("/") and row["path"].endswith("/" + BASE + name), "V3_CHECKPOINT_PATH_MISMATCH")
            packet.same_hash(BASE + name, row["sha256"])
            require(type(row["bytes"]) is int and row["bytes"] > 0
                    and row["bytes"] == packet.inventory[BASE + name]["bytes"], "V3_CHECKPOINT_SIZE_MISMATCH")
            expected_epoch = 0 if state == "initial" else best_epoch if state == "selected" else complete
            require(type(row["epoch"]) is int and row["epoch"] == expected_epoch
                    and type(row["optimizer_steps"]) is int and row["optimizer_steps"] == expected_epoch * steps_per_epoch,
                    "V3_SELECTED_CHECKPOINT_EPOCH_OR_STEPS_MISMATCH")
            if state != "initial":
                require(row["validation"] == history[expected_epoch - 1]["families"][family]["validation"],
                        "V3_CHECKPOINT_VALIDATION_COPY_MISMATCH")
            checkpoint_digests[name] = row["sha256"]
        initial_path = BASE + f"validation_predictions/{family}_epoch_0000.json"
        if initial_path in actual_files:
            saved = packet.json(initial_path)
            require(saved["epoch"] == 0 and saved["split"] == "validation" and saved["test_gold_access"] is False,
                    "V3_INITIAL_VALIDATION_ROLE_MISMATCH")
            derived = depth_generated_metrics(saved["actions"], validation_tasks)
            require(saved["metrics"] == derived == checkpoints[family]["initial"]["validation"]["generation"],
                    "V3_INITIAL_VALIDATION_METRICS_MISMATCH")
    expected_checkpoints = {BASE + name for name in checkpoint_digests}
    require({name for name in packet.inventory if name.startswith(BASE + "candidate_") and name.endswith(".pt")} == expected_checkpoints,
            "V3_EXACT_SIX_MAIN_CHECKPOINT_FILES_REQUIRED")
    matching = packet.json(BASE + "parameter_matching.json")
    require(matching == training["parameter_matching"], "PARAMETER_MATCHING_RECEIPT_MISMATCH")
    counts = (matching["cas_trainable_parameters"], matching["generic_trainable_parameters"])
    require(all(type(count) is int and count > 0 for count in counts), "PARAMETER_COUNTS_INVALID")
    mismatch = abs(counts[0] - counts[1]) / counts[0]
    require(mismatch <= registered["policy"]["max_parameter_mismatch_fraction"]
            and math.isclose(mismatch, matching["relative_difference"], abs_tol=1e-12), "ACTIVE_PARAMETER_MATCH_INVALID")
    gradients = packet.json(BASE + "gradient_connectivity.json")
    require(gradients == training["active_parameters"], "GRADIENT_RECEIPT_COPY_MISMATCH")
    for family, count in zip(("cas", "generic"), counts, strict=True):
        require(gradients[family]["all_parameter_tensors_connected"] is True
                and gradients[family]["connected_trainable_parameters"] == count
                and gradients[family]["trainable_parameters"] == count, "GRADIENT_CONNECTIVITY_INCOMPLETE")
    preflight = packet.json(BASE + "gpu_preflight_copy_v3.json")
    for family in ("cas", "generic"):
        require(_names(gradients[family]["parameter_tensor_names"])
                and all(gradients[family]["parameter_tensor_names"] == preflight["stress_batches"][label]["families"][family]["finite_nonzero_gradient_parameter_names"] for label in STRESS),
                "V3_TRAINING_PREFLIGHT_GRADIENT_NAME_COVERAGE")
    return {"training_probe_count": 24, "training_probe_used_for_selection": False, "checkpoint_sha256": checkpoint_digests, "completed_epochs": complete,
            "selected_epochs": selected_epochs, "eligible_epochs": sorted(eligible),
            "validation_examples_recounted_per_generation": 96, "public_text_round_trips": len(round_trips),
            "checkpoint_contents_loaded": False, "checkpoint_schema_boundary": "Declared JSON format and source-bound writer checked; binary checkpoint payloads were not parsed."}

def _full(packet, campaign, spec):
    _dataset(packet, spec)
    require(campaign.get("evaluation_completed") is True and campaign.get("all_test_cases_evaluated_per_arm") == 72
            and campaign.get("reference_cases") == 72 and campaign.get("arm_verdicts") == 360, "FULL_DENOMINATORS_INVALID")
    seal = packet.json(BASE + "predictions_seal.json")
    require(seal == campaign.get("prediction_seal"), "PREDICTION_SEAL_COPY_MISMATCH")
    require(seal.get("test_private_labels_loaded") is False and set(seal.get("arms", [])) == set(ARMS)
            and seal.get("test_examples") == 72 and seal.get("prediction_count") == 360, "PREDICTION_SEAL_COUNTS_INVALID")
    packet.same_hash(BASE + "predictions.jsonl", seal["sha256"])
    opening = packet.json(BASE + "test_gold_opening_receipt.json")
    require(opening["prediction_sha256_before_opening"] == seal["sha256"]
            and opening["test_private_sha256"] == seal["test_private_sha256"], "GOLD_OPENING_DIGEST_MISMATCH")
    require(datetime.fromisoformat(opening["opened_utc"]) > datetime.fromisoformat(seal["sealed_utc"]),
            "GOLD_OPENED_BEFORE_SEAL")
    manifest = packet.json(BASE + "dataset/dataset_manifest.json")
    for name, digest in manifest["sha256"].items():
        require(name in ("train.json", "validation.json", "test_public.json", "test_private.json"), "DATASET_FILENAME_INVALID")
        packet.same_hash(BASE + "dataset/" + name, digest)
    packet.same_hash(BASE + "dataset/test_public.json", seal["test_public_sha256"])
    packet.same_hash(BASE + "dataset/test_private.json", seal["test_private_sha256"])
    publics = packet.json(BASE + "dataset/test_public.json")
    private = packet.json(BASE + "dataset/test_private.json")
    predictions = [json_bytes(line) for line in packet.raw(BASE + "predictions.jsonl").splitlines()]
    require(len(publics) == len(private) == len(predictions) == 72, "TEST_CASE_MAPPING_COUNT_INVALID")
    for index, (public, task, prediction) in enumerate(zip(publics, private, predictions, strict=True)):
        require(task["public"] == public and prediction.get("case_index") == index
                and prediction.get("public_sha256") == sha(canonical(public))
                and set(prediction.get("actions", {})) == set(ARMS), "TEST_CASE_MAPPING_INVALID")
    training_details = _training_v3(packet, campaign, spec, manifest, seal)
    checkpoint_digests = training_details["checkpoint_sha256"]
    training = packet.json(BASE + "training_receipt.json")
    preflight = packet.json(BASE + "gpu_preflight_copy_v3.json")
    require(preflight["parameter_matching"] == training["parameter_matching"],
            "V3_PREFLIGHT_TRAINING_PARAMETER_MATCH_MISMATCH")
    evaluated = packet.json(BASE + "evaluation_results.json")
    cases = evaluated["cases"]
    require(len(cases) == 72 and sorted(row["case_index"] for row in cases) == list(range(72)), "EVALUATION_CASE_COVERAGE_INVALID")
    rows_by_arm = {arm: [] for arm in ARMS}
    for case in cases:
        index = case["case_index"]
        folder = BASE + f"evaluation/case_{index:04d}"
        require(case == packet.json(folder + "/case_receipt.json"), "EVALUATION_CASE_COPY_MISMATCH")
        reference = packet.json(folder + "/reference_result.json")
        require(reference["selected_action"] == private[index]["target"], "PRIVATE_REFERENCE_TARGET_MISMATCH")
        _native(packet, reference, folder + "/reference", reference=True)
        require(case["reference_verification"] == packet.json(folder + "/reference_verdict.json"), "REFERENCE_VERDICT_COPY_MISMATCH")
        _verdict(case["reference_verification"], correct=True)
        require(set(case["arms"]) == set(ARMS), "EVALUATION_ARM_COVERAGE_INVALID")
        for arm in ARMS:
            row = case["arms"][arm]
            arm_folder = folder + "/" + arm
            require(row == packet.json(arm_folder + "/case_receipt.json"), "ARM_RECEIPT_COPY_MISMATCH")
            require(row["case_index"] == index and row["arm"] == arm
                    and row["action"] == predictions[index]["actions"][arm], "PREDICTION_EXECUTION_ACTION_MISMATCH")
            verdict = row["verification"]
            require(verdict == packet.json(arm_folder + "/verification.json"), "ARM_VERDICT_COPY_MISMATCH")
            _verdict(verdict)
            require(verdict.get("repair_required") is False and verdict.get("repair_success") is None,
                    "UNSUPPORTED_REPAIR_CLAIM_IN_META2_RUN_CALL_PILOT")
            result = packet.json(arm_folder + "/execution_result.json")
            require(result["status"] == row["execution_status"], "EXECUTION_STATUS_MISMATCH")
            if row["model_rejection"] is True:
                require(result["status"] == "REJECTED" and not any(verdict[key] for key in VERDICT_FIELDS),
                        "REJECTED_PROGRAM_COUNTED_CORRECT")
            else:
                require(row["model_rejection"] is False and result["selected_action"] == row["action"], "EXECUTION_ACTION_MISMATCH")
                count = _native(packet, result, arm_folder + "/native", reference=False)
                require(verdict["native_runs"] == count and verdict["reserved_policy_units"] == result["reserved_policy_units"],
                        "NATIVE_COMPUTE_COUNTS_MISMATCH")
            rows_by_arm[arm].append(row)
    metrics = {}
    require(evaluated["results"] == campaign["results"] and set(evaluated["results"]) == set(ARMS), "METRIC_RECEIPT_COPY_MISMATCH")
    for arm, rows in rows_by_arm.items():
        counted = {key: sum(row["verification"][key] for row in rows) for key in VERDICT_FIELDS}
        saved = evaluated["results"][arm]
        require(saved["total"] == 72 and saved["all_cases_in_denominator"] is True, "ARM_DENOMINATOR_INVALID")
        require(all(type(saved[key]) is int for key in VERDICT_FIELDS), "METRIC_COUNTER_TYPE_INVALID")
        require(all(saved[key] == value for key, value in counted.items()), "RECORDED_METRIC_RECOUNT_MISMATCH")
        for key, expected in (
            ("model_rejections", sum(row["model_rejection"] for row in rows)),
            ("native_executed", sum(row["execution_status"] == "EXECUTED" for row in rows)),
            ("native_runs", sum(row["verification"].get("native_runs", 0) for row in rows)),
            ("reserved_policy_units", sum(row["verification"].get("reserved_policy_units", 0) for row in rows)),
        ):
            require(saved[key] == expected, "RECORDED_COMPUTE_RECOUNT_MISMATCH:" + key)
        require(math.isclose(saved["task_accuracy"], counted["task_correct"] / 72, abs_tol=1e-12), "TASK_ACCURACY_MISMATCH")
        require(saved["repair_required_total"] == 0 and saved["repair_success"] is None, "UNSUPPORTED_REPAIR_AGGREGATE")
        metrics[arm] = {"total": 72, **counted, "task_accuracy": counted["task_correct"] / 72,
                        "model_rejections": saved["model_rejections"], "native_runs": saved["native_runs"]}
    for family in ("cas", "generic"):
        gain = metrics[family + "_trained"]["task_accuracy"] - metrics[family + "_untrained"]["task_accuracy"]
        require(math.isclose(campaign[family + "_task_accuracy_gain"], gain, abs_tol=1e-12), "TASK_ACCURACY_GAIN_MISMATCH")
    group_counts = _groups(packet, campaign, private, cases, spec)
    payload = packet.json(BASE + "payload_sha256.json")
    actual_payload = {name.removeprefix(BASE): row["sha256"] for name, row in packet.inventory.items()
                      if name.startswith(BASE) and name != BASE + "payload_sha256.json"}
    require(payload == actual_payload, "CAMPAIGN_PAYLOAD_HASH_COVERAGE_MISMATCH")
    return {"cases": 72, "arm_verdicts": 360, "metrics": metrics,
            "checkpoint_sha256": checkpoint_digests, "checkpoint_contents_loaded": False,
            "completed_epochs": training["completed_epochs"], "learning_v3": training_details, "evaluation_groups": group_counts}


def _groups(packet, campaign, private, cases, spec):
    document = packet.json(BASE + "evaluation_groups.json")
    require(document.get("schema") == "cas-meta2-group-results/3"
            and document.get("groups") == campaign.get("evaluation_groups"), "V3_GROUP_RECEIPT_COPY_MISMATCH")
    expected = spec["curriculum"]["test_groups"]
    require(expected == {"same_depth": 24, "wording_shift": 24, "deeper_calls": 24}, "V3_REGISTERED_GROUPS_MISMATCH")
    indices = {group: [index for index, task in enumerate(private)
                      if task["provenance"]["evaluation_group"] == group] for group in expected}
    require({group: len(rows) for group, rows in indices.items()} == expected
            and sorted(index for rows in indices.values() for index in rows) == list(range(72))
            and document["group_case_indices"] == indices and set(document["groups"]) == set(expected),
            "V3_GROUP_CASE_MAPPING_MISMATCH")
    by_index = {case["case_index"]: case for case in cases}
    for group, members in indices.items():
        saved = document["groups"][group]
        require(set(saved) == set(ARMS), "V3_GROUP_ARM_COVERAGE_MISMATCH")
        for arm in ARMS:
            rows = [by_index[index]["arms"][arm] for index in members]
            counted = {key: sum(row["verification"][key] for row in rows) for key in VERDICT_FIELDS}
            counted.update(model_rejections=sum(row["model_rejection"] for row in rows),
                native_executed=sum(row["execution_status"] == "EXECUTED" for row in rows),
                native_runs=sum(row["verification"].get("native_runs", 0) for row in rows),
                reserved_policy_units=sum(row["verification"].get("reserved_policy_units", 0) for row in rows))
            require(saved[arm]["total"] == len(rows) and saved[arm]["all_cases_in_denominator"] is True
                    and all(type(saved[arm][key]) is int and saved[arm][key] == value for key, value in counted.items())
                    and math.isclose(saved[arm]["task_accuracy"], counted["task_correct"] / len(rows), abs_tol=1e-12)
                    and saved[arm]["repair_required_total"] == 0 and saved[arm]["repair_success"] is None,
                    "V3_GROUP_METRIC_RECOUNT_MISMATCH")
    return expected


def _audit_code_hashes():
    hashes = {str(Path(__file__).resolve()): file_hash(__file__)}
    if _IMPORT_GUARD is not None:
        hashes.update({row["path"]: row["sha256"] for row in _IMPORT_GUARD.verify().values()})
    return hashes


def _inspect_packet(path, *, expected_sha256, source_sha, job, output, source_manifest=None,
                   source_archive_sha256=None, extract=None, experiment_spec=None):
    if type(source_manifest) is dict:
        wrapper = source_manifest
        source_manifest = wrapper.get("launch_manifest", wrapper.get("manifest", wrapper))
        source_archive_sha256 = source_archive_sha256 or wrapper.get("archive_sha256")
    _configure(source_manifest, source_sha)
    experiment, spec = _experiment_spec(source_manifest, experiment_spec)
    audit_code = _audit_code_hashes()
    require(type(expected_sha256) is str and SHA256.fullmatch(expected_sha256), "EXPECTED_PACKET_SHA256_REQUIRED")
    require(type(source_sha) is str and SHA1.fullmatch(source_sha), "EXPECTED_SOURCE_SHA_REQUIRED")
    require(type(job) is str and re.fullmatch(r"[A-Za-z0-9._-]{1,160}", job), "EXPECTED_JOB_ID_REQUIRED")
    path = Path(path).resolve()
    require(path.is_file() and 0 < path.stat().st_size <= MAX_COMPRESSED, "COMPRESSED_SIZE_CEILING")
    require(file_hash(path) == expected_sha256, "PACKET_SHA256_MISMATCH")
    output = legacy._new_output(output)
    target = legacy._new_output(extract, extracted=True) if extract is not None else None
    if target is not None:
        require(not output.is_relative_to(target) and not target.is_relative_to(output), "INSPECTION_EXTRACTION_PATH_OVERLAP")
    with zipfile.ZipFile(path) as archive:
        infos, expanded = legacy._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            digest, count = hashlib.sha256(), 0
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    count += len(block)
                    require(count <= info.file_size, "MEMBER_SIZE_EXCEEDS_HEADER")
                    digest.update(block)
            require(count == info.file_size, "MEMBER_SIZE_MISMATCH")
            inventory.append({"path": name, "bytes": count, "sha256": digest.hexdigest()})
        packet = Packet(archive, infos, inventory)
        collection, index_verified = legacy._collection(packet, job, source_sha, source_archive_sha256)
        require(collection.get("experiment") == experiment, "V3_COLLECTION_EXPERIMENT_MISMATCH")
        issues, details = [], {}
        campaign = packet.json(BASE + "campaign_receipt.json") if BASE + "campaign_receipt.json" in packet.inventory else None
        remote_job = packet.json("cloud_job/job.json") if "cloud_job/job.json" in packet.inventory else None
        if remote_job is not None:
            require(all(remote_job.get(key) == collection.get(key) for key in ("job", "source_sha", "baseline_sha", "archive_sha256", "smoke_only", "experiment")),
                    "REMOTE_JOB_COLLECTION_IDENTITY_MISMATCH")
        run_status = "PARTIAL_EVIDENCE" if collection["partial_evidence"] else "FAILED_RUN"
        claimed_complete = collection["returncode"] == 0
        if claimed_complete:
            def check(label, operation):
                try:
                    details[label] = operation()
                except (PacketInvalid, KeyError, IndexError, AttributeError, TypeError, ValueError, OverflowError) as error:
                    issues.append(label + ":" + str(error))
            check("gpu_contract", lambda: legacy._gpu_gate(packet, "contract"))
            check("gpu_policy", lambda: _gpu_gate(packet, "policy"))
            check("environment", lambda: legacy._environment(packet))
            check("source_binding", lambda: _source_binding(campaign, source_manifest, source_sha))
            check("command_binding", lambda: _command(packet, experiment, collection["smoke_only"]))
            check("dataset_v3", lambda: _dataset(packet, spec))
            check("gpu_preflight_copy_v3", lambda: _preflight(packet, campaign, source_manifest, spec, job))
            check("campaign_gpu_gates", lambda: _campaign_gates(packet, campaign, source_manifest, spec, job))
            check("dataset_construction", lambda: _construction(packet, spec))
            check("campaign_identity", lambda: require(campaign["aws_job_id"] == job
                and campaign.get("schema") == "cas-meta2-campaign-receipt/3", "V3_CAMPAIGN_JOB_OR_SCHEMA_MISMATCH"))
            check("smoke", lambda: legacy._smoke(packet, campaign))
            expected_status = "CAS_META_2_V3_AWS_SMOKE_COMPLETED" if collection["smoke_only"] else "CAS_META_2_V3_AWS_CAMPAIGN_COMPLETED"
            if not isinstance(campaign, dict) or campaign.get("status") != expected_status or campaign.get("completed") is not True:
                issues.append("campaign:COMPLETION_STATUS_MISMATCH")
            elif collection["smoke_only"]:
                if campaign.get("evaluation_completed") is not False or campaign.get("training_performed") is not False:
                    issues.append("campaign:SMOKE_MAKES_LEARNING_CLAIM")
                if any(name.startswith(BASE + "candidate_") and name.endswith(".pt") for name in packet.inventory):
                    issues.append("campaign:SMOKE_HAS_CANDIDATE_CHECKPOINT")
            else:
                check("training_cleanup", lambda: _training_cleanup(packet, campaign))
                check("full_evaluation", lambda: _full(packet, campaign, spec))
            if remote_job is None or remote_job.get("returncode") != 0:
                issues.append("job:SUCCESS_JOB_RECEIPT_MISSING_OR_FAILED")
            if source_archive_sha256 is None:
                issues.append("source_binding:INDEPENDENT_SOURCE_ARCHIVE_SHA256_REQUIRED")
            run_status = "EVIDENCE_MISMATCH" if issues else ("SMOKE_EVIDENCE_VERIFIED" if collection["smoke_only"] else "FULL_EVIDENCE_VERIFIED")
        else:
            for name in ("cloud_job/remote_failure.json", BASE + "campaign_receipt.json"):
                if name in packet.inventory:
                    details[name] = packet.json(name)
        extraction = legacy._extract(packet, target) if target is not None else None
        require(file_hash(path) == expected_sha256, "PACKET_CHANGED_DURING_INSPECTION")
    require(all(_audit_code_hashes().get(k) == v for k, v in audit_code.items()), "V3_AUDIT_CODE_CHANGED_DURING_INSPECTION")
    for name in source_manifest["files_sha256"]:
        if name.startswith(PILOT + "/"):
            relative = name.removeprefix(PILOT + "/")
            if relative in ("EXPERIMENT_V3.json", "cas_meta2/exclusions_v3.json", "cas_meta2/development_exclusions_v3.json"):
                source_file(source_manifest, relative)
    inventory_document = {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": expected_sha256,
                          "entries": inventory}
    inventory_payload = json.dumps(inventory_document, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    output.mkdir(parents=True, exist_ok=False)
    (output / "full_member_index.json").write_bytes(inventory_payload)
    receipt = {
        "schema": "cas-meta2-packet-inspection/3", "status": "CAS_META_2_V3_PACKET_" + run_status,
        "experiment": experiment,
        "source_manifest": source_manifest, "source_manifest_sha256": sha(canonical(source_manifest)),
        "preimport_git_binding": _IMPORT_GUARD.git_binding,
        "audit_code_sha256": _audit_code_hashes(),
        "packet": str(path), "packet_sha256": expected_sha256, "source_sha": source_sha, "job": job,
        "compressed_bytes": path.stat().st_size, "expanded_bytes": expanded, "member_files": len(inventory),
        "archive_safety_and_all_included_bytes_checked": True, "original_full_index_verified": index_verified,
        "collection": {key: collection[key] for key in ("returncode", "smoke_only", "partial_evidence",
                      "original_file_count", "included_full_file_count", "omitted_full_file_count",
                      "original_file_index_sha256", "archive_sha256")},
        "completed_run_evidence_verified": claimed_complete and not issues,
        "full_member_index": str(output / "full_member_index.json"),
        "full_member_index_sha256": sha(inventory_payload), "issues": issues,
        "checks": details, "extraction": extraction, "utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_loading_performed": False, "neural_execution_performed": False,
        "stored_semantic_reverification_performed": False,
        "boundary": "V2 byte bindings, lossless public-text round trips and recorded validation/result recount only. Native stored-record semantic rechecking remains a separate gate. No CAS advantage, general reasoning, complete CNCM or hardware claim.",
    }
    (output / "inspection_receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt



def inspect_packet(path, *, expected_sha256, source_sha, job, output, source_manifest=None,
                   source_archive_sha256=None, extract=None, experiment_spec=None):
    """Preserve typed failure evidence even when validation stops early."""
    import traceback
    target = no_links(output)
    require(target.resolve().is_relative_to((ROOT / "records").resolve()) and not target.exists(),
            "V3_NEW_RECORDS_OUTPUT_REQUIRED")
    if extract is not None:
        extraction = no_links(extract)
        require(not target.resolve().is_relative_to(extraction.resolve()) and not extraction.resolve().is_relative_to(target.resolve()),
                "V3_OUTPUT_EXTRACTION_OVERLAP")
    started_hash = file_hash(path) if Path(path).is_file() else None
    code = {str(Path(__file__).resolve()): file_hash(__file__)}
    try:
        return _inspect_packet(path, expected_sha256=expected_sha256, source_sha=source_sha, job=job,
            output=target, source_manifest=source_manifest, source_archive_sha256=source_archive_sha256,
            extract=extract, experiment_spec=experiment_spec)
    except Exception as error:
        receipt = {"schema": "cas-meta2-packet-inspection/3", "status": "CAS_META_2_V3_PACKET_REJECTED",
            "completed_run_evidence_verified": False, "issues": [type(error).__name__ + ":" + str(error)],
            "traceback": traceback.format_exc(limit=20), "packet": str(Path(path).absolute()),
            "packet_sha256_observed_before": started_hash,
            "packet_sha256_observed_after": file_hash(path) if Path(path).is_file() else None,
            "packet_sha256": expected_sha256, "source_sha": source_sha, "job": job,
            "audit_code_sha256": code, "neural_execution_performed": False, "checkpoint_loading_performed": False,
            "stored_semantic_reverification_performed": False,
            "boundary": "Early typed rejection. Incomplete coverage is not a passed inspection."}
        target.mkdir(parents=True, exist_ok=True)
        destination = target / "inspection_receipt.json"
        require(not destination.exists(), "V3_FAILURE_RECEIPT_OVERWRITE_REFUSED")
        destination.write_bytes(canonical(receipt) + b"\n")
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-archive-sha256")
    parser.add_argument("--experiment-spec", type=Path)
    parser.add_argument("--extract", type=Path)
    args = parser.parse_args()
    try:
        wrapper = json_bytes(args.source_manifest.read_bytes())
        manifest = wrapper.get("launch_manifest", wrapper.get("manifest", wrapper))
        archive_sha = args.source_archive_sha256 or wrapper.get("archive_sha256")
        receipt = inspect_packet(args.packet, expected_sha256=args.sha256, source_sha=args.source_sha,
            job=args.job, output=args.output, source_manifest=manifest,
            source_archive_sha256=archive_sha, extract=args.extract, experiment_spec=args.experiment_spec)
    except (PacketInvalid, ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "CAS_META_2_V3_PACKET_REJECTED", "reason": str(error)}))
        return 2
    print(json.dumps({"status": receipt["status"], "issues": receipt["issues"],
                      "neural_execution_performed": False}, indent=2))
    return 0 if receipt["completed_run_evidence_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
