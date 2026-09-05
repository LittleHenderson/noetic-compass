"""Check stored results of one failed protocol without overriding its gate.

This is a diagnostic record, not a replacement release validator. It accepts
only the exact already-inspected packet and preserves its failed cleanup gate.
No checkpoint loading, CUDA calls, original-record edits, or provider calls.
"""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import traceback
from datetime import datetime, timezone
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "410bce98307a5644db51928459b73391c7066b72"
PACKET_HASH = "0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93"
INSPECTION_HASH = "4fb60dc51248b2c75dbd2bf2c0f278e95fc29c7612b792e6b7e82a79936fd2a9"
JOB = "cas-meta2-20260905214620-cfdbb893"
ISSUE = "gpu_preflight_v2:V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED"


class NoNeuralOrProviderImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "tensorflow", "jax", "casformer", "cas_cjt", "cupy", "boto3"}:
            raise RuntimeError("DIAGNOSTIC_IMPORT_FORBIDDEN:" + fullname)
        return None


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def restore_public_definition_order(task):
    """Restore only presentation order, after independently checking meaning."""
    from cas_meta2.curriculum import parse_problem
    from cas_meta2.executor import canonical
    before = canonical(task)
    parsed = parse_problem(task["public"])
    require(parsed == task["target"] and canonical(parsed) == canonical(task["target"]),
            "PUBLIC_MEANING_DOES_NOT_MATCH_STORED_TARGET")
    original = task["target"]["program"]["procedures"]
    names = list(parsed["program"]["procedures"])
    restored = deepcopy(task)
    restored["target"]["program"]["procedures"] = {
        name: restored["target"]["program"]["procedures"][name] for name in names}
    after = canonical(restored)
    require(before == after and restored == task, "ORDER_RESTORATION_CHANGED_CANONICAL_DATA")
    return restored, {"changed_order": list(original) != names,
        "stored_definition_order": list(original), "public_definition_order": names,
        "canonical_sha256_before": sha256(before).hexdigest(),
        "canonical_sha256_after": sha256(after).hexdigest()}


def restore_dataset_order(tasks):
    from cas_meta2.executor import canonical
    require(type(tasks) is list, "DATASET_TASK_LIST_REQUIRED")
    before = canonical(tasks)
    restored, rows = [], []
    for index, task in enumerate(tasks):
        value, row = restore_public_definition_order(task)
        restored.append(value)
        rows.append({"index": index, "task_id": task["task_id"], **row})
    after = canonical(restored)
    require(before == after, "DATASET_ORDER_ADAPTER_CHANGED_CANONICAL_BYTES")
    return restored, {"task_count": len(tasks), "affected_rows": sum(row["changed_order"] for row in rows),
        "canonical_sha256_before": sha256(before).hexdigest(), "canonical_sha256_after": sha256(after).hexdigest(),
        "all_meanings_independently_equal": True, "only_procedure_dictionary_iteration_order_restored": True,
        "rows": rows}



def no_links(path):
    for current in (path, *path.parents):
        require(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(),
                "DIAGNOSTIC_SOURCE_LINK_REFUSED")


class PinnedProjectLoader(importlib.abc.Loader):
    """Execute only newly rechecked source bytes, never a cached bytecode file."""
    def __init__(self, guard, fullname, source_path):
        self.guard, self.fullname, self.source_path = guard, fullname, source_path

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        if self.source_path is None:
            no_links(self.guard.root / "tools")
            require(list(module.__path__) == [str(self.guard.root / "tools")],
                    "TOOLS_NAMESPACE_PATH_MISMATCH")
        else:
            raw = self.guard.checked_bytes(self.fullname)
            exec(compile(raw, str(self.source_path), "exec"), module.__dict__)
            require(self.guard.checked_bytes(self.fullname) == raw,
                    "PROJECT_SOURCE_CHANGED_DURING_IMPORT")
        self.guard.executed[self.fullname] = module


class CheckedProjectImports(importlib.abc.MetaPathFinder):
    """The two project packages cannot fall back to sys.path or earlier code."""
    def __init__(self, root, source_hashes):
        self.root = Path(root).resolve()
        self.source_hashes = dict(source_hashes)
        self.modules, self.executed = {}, {}
        for relative in source_hashes:
            if not relative.endswith(".py"):
                continue
            path = self.root / relative
            name = relative[:-3].replace("/", ".")
            if name.endswith(".__init__"):
                name = name.removesuffix(".__init__")
            require(name.startswith("tools.") or name == "cas_meta2" or name.startswith("cas_meta2."),
                    "PROJECT_SOURCE_ALLOWLIST_INVALID")
            self.modules[name] = path
        require("cas_meta2" in self.modules and (self.root / "tools").is_dir(),
                "PROJECT_PACKAGES_REQUIRED")

    def checked_bytes(self, fullname):
        path = self.modules[fullname]
        no_links(path)
        require(path.is_file() and path.resolve().is_relative_to(self.root),
                "PROJECT_IMPORT_PATH_INVALID")
        raw = path.read_bytes()
        relative = path.relative_to(self.root).as_posix()
        require(sha256(raw).hexdigest() == self.source_hashes[relative],
                "PROJECT_IMPORT_BYTES_DIFFER_FROM_GIT:" + fullname)
        return raw

    def reject_preloaded(self, modules=None):
        modules = sys.modules if modules is None else modules
        # A fresh diagnostic needs no preloaded project modules. Reject even a
        # plausible __file__: it does not prove which bytes previously ran.
        require(not any(name == "tools" or name.startswith("tools.")
                        or name == "cas_meta2" or name.startswith("cas_meta2.")
                        for name in modules), "PRELOADED_PROJECT_MODULE_REFUSED")

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "tools":
            no_links(self.root / "tools")
            spec = importlib.machinery.ModuleSpec(fullname, PinnedProjectLoader(self, fullname, None),
                                                 is_package=True)
            spec.submodule_search_locations = [str(self.root / "tools")]
            return spec
        if fullname in self.modules:
            source_path = self.modules[fullname]
            self.checked_bytes(fullname)
            locations = [str(source_path.parent)] if fullname == "cas_meta2" else None
            return importlib.util.spec_from_file_location(fullname, source_path,
                loader=PinnedProjectLoader(self, fullname, source_path), submodule_search_locations=locations)
        if fullname.startswith("tools.") or fullname.startswith("cas_meta2."):
            raise ValueError("UNPINNED_PROJECT_IMPORT_REFUSED:" + fullname)
        return None

    def loaded_records(self, modules=None):
        modules = sys.modules if modules is None else modules
        loaded = {name: module for name, module in modules.items()
                  if name == "tools" or name.startswith("tools.")
                  or name == "cas_meta2" or name.startswith("cas_meta2.")}
        require(set(loaded) == set(self.executed), "PROJECT_MODULE_COVERAGE_CHANGED")
        result = {}
        for name, module in sorted(loaded.items()):
            require(module is self.executed[name], "PROJECT_MODULE_OBJECT_REPLACED")
            if name == "tools":
                require(getattr(module, "__file__", None) is None
                        and list(module.__path__) == [str(self.root / "tools")],
                        "TOOLS_NAMESPACE_PATH_MISMATCH")
                result[name] = {"kind": "explicit_checked_namespace",
                                "paths": [str(self.root / "tools")], "sha256": None}
            else:
                expected = self.modules[name]
                require(Path(getattr(module, "__file__", "")).resolve() == expected.resolve()
                        and module.__spec__.origin == str(expected),
                        "LOADED_PROJECT_MODULE_PATH_MISMATCH")
                raw = self.checked_bytes(name)
                result[name] = {"kind": "git_checked_source_bytes", "path": str(expected),
                                "sha256": sha256(raw).hexdigest()}
        return result


def main():
    output = Path(__file__).resolve().parent / "result"
    no_links(output)
    require(not output.exists(), "NEW_RESULT_DIRECTORY_REQUIRED")
    sys.meta_path.insert(0, NoNeuralOrProviderImports())
    # Verify executable dependencies before importing them. The recorded source
    # SHA, not a mutable manifest or this script's own hashes, is the authority.
    git_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                    capture_output=True, text=True, check=True).stdout.strip())
    names = ["tools/audit_stored_packet_v2.py", "tools/inspect_cloud_packet_v2.py",
             "tools/inspect_cloud_packet.py", "tools/experiment_profiles.py", "EXPERIMENT_V2.json"]
    names += ["cas_meta2/" + name + ".py" for name in (
        "__init__", "campaign_v2", "curriculum_v2", "curriculum", "codec", "executor",
        "features_v2", "selection_v2", "ir", "native", "stored")]
    source_hashes = {}
    for name in names:
        path = ROOT / name
        no_links(path)
        require(path.is_file(), "REGULAR_SOURCE_REQUIRED")
        relative = path.relative_to(git_root).as_posix()
        frozen = subprocess.run(["git", "show", SOURCE + ":" + relative], cwd=ROOT,
                                capture_output=True, check=True).stdout
        require(path.read_bytes() == frozen, "DIAGNOSTIC_SOURCE_CHANGED:" + name)
        source_hashes[name] = sha256(frozen).hexdigest()
    project_imports = CheckedProjectImports(ROOT, source_hashes)
    project_imports.reject_preloaded()
    sys.meta_path.insert(0, project_imports)
    from tools import audit_stored_packet_v2 as stored
    from tools import inspect_cloud_packet as archive_checks

    inspection_path = ROOT / "records/aws_learning_v2_001_inspection/inspection_receipt.json"
    packet_path = ROOT / "records/aws_learning_v2_001/cloud_artifacts.zip"
    extraction_root = ROOT / "records/aws_learning_v2_001_extracted"
    index_path = inspection_path.with_name("full_member_index.json")
    for path in (inspection_path, packet_path, index_path):
        stored._regular(path)
    require(digest(inspection_path) == INSPECTION_HASH, "EXACT_FAILED_INSPECTION_REQUIRED")
    require(digest(packet_path) == PACKET_HASH, "EXACT_SOURCE_PACKET_REQUIRED")
    inspection = stored.json_bytes(inspection_path.read_bytes())
    require(inspection["status"] == "CAS_META_2_V2_PACKET_EVIDENCE_MISMATCH"
            and inspection["issues"] == [ISSUE]
            and inspection["completed_run_evidence_verified"] is False,
            "ORIGINAL_FAILED_PROTOCOL_GATE_MUST_REMAIN_FAILED")
    require(inspection["source_sha"] == SOURCE and inspection["job"] == JOB
            and inspection["packet_sha256"] == PACKET_HASH
            and inspection["archive_safety_and_all_included_bytes_checked"] is True
            and inspection["original_full_index_verified"] is True,
            "ORIGINAL_BYTE_AND_SOURCE_CHECKS_REQUIRED")
    require(Path(inspection["extraction"]["path"]).resolve() == extraction_root.resolve()
            and inspection["extraction"]["all_member_bytes_verified_after_write"] is True,
            "EXACT_SAFE_EXTRACTION_REQUIRED")
    require(digest(index_path) == inspection["full_member_index_sha256"], "FULL_INDEX_CHANGED")
    index = stored.json_bytes(index_path.read_bytes())
    require(index["schema"] == "cas-meta2-full-packet-index/1"
            and index["packet_sha256"] == PACKET_HASH, "FULL_INDEX_PACKET_MISMATCH")
    entries = index["entries"]
    require(len(entries) == inspection["member_files"] == inspection["extraction"]["files_verified"],
            "INDEX_COVERAGE_MISMATCH")
    with zipfile.ZipFile(packet_path) as archive:
        infos, expanded = archive_checks._safe_infos(archive)
        require(set(infos) == {row["path"] for row in entries}, "ZIP_INDEX_COVERAGE_MISMATCH")
        require(len(entries) == len({row["path"].casefold() for row in entries}), "INDEX_ALIASES")
        for row in entries:
            require(set(row) == {"path", "bytes", "sha256"}, "INDEX_FIELDS")
            name = archive_checks.safe_name(row["path"])
            raw = archive.read(infos[name])
            require(len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"],
                    "ZIP_INDEX_BYTES_MISMATCH:" + name)
        require(expanded == sum(row["bytes"] for row in entries), "ZIP_EXPANDED_COUNT")

    class DiagnosticRecords:
        # Reuse only immutable member-reading methods. Do not call, replace, or
        # modify the accepted Extracted constructor or its required-success gate.
        path = stored.Extracted.path
        raw = stored.Extracted.raw
        same_hash = stored.Extracted.same_hash
        verify_all = stored.Extracted.verify_all

        def json(self, name):
            value = stored.Extracted.json(self, name)
            targets = {stored.BASE + "dataset/" + filename
                       for filename in ("train.json", "validation.json", "test_private.json")}
            if name not in targets:
                return value
            restored, report = restore_dataset_order(value)
            report["original_member_sha256"] = self.inventory[name]["sha256"]
            if name in self.order_reports:
                require(self.order_reports[name] == report, "ORDER_ADAPTER_REPEAT_CHANGED")
            else:
                self.order_reports[name] = report
            return restored

    records = DiagnosticRecords()
    records.root = extraction_root
    records.order_reports = {}
    records.inventory = {row["path"]: row for row in entries}
    records.inspection_path = inspection_path
    records.inspection_hash = INSPECTION_HASH
    records.index_path = index_path
    records.index_hash = digest(index_path)
    records.verify_all()
    receipt = {
        "schema": "cas-meta2-failed-protocol-stored-diagnostic/2",
        "checked_path_import_resolution": True,
        "preloaded_project_modules_rejected": True,
        "presentation_order_adapter": {"schema": "cas-meta2-readonly-presentation-order-adapter/1",
            "datasets": records.order_reports, "on_disk_bytes_changed": False,
            "boundary": "Only target.program.procedures dictionary iteration order is restored in detached JSON values, from independently parsed public declarations after exact action and canonical-byte equality. Frozen dataset and native semantic checkers are unchanged; the original GPU-preflight and full-protocol gates remain failed."},
        "status": "CAS_META_2_V2_STORED_DIAGNOSTIC_RUNNING",
        "full_protocol_accepted": False, "original_full_inspection_status": inspection["status"],
        "unresolved_full_protocol_issues": [ISSUE], "packet_sha256": PACKET_HASH,
        "failed_inspection_sha256": INSPECTION_HASH, "source_sha": SOURCE, "job": JOB,
        "frozen_dependency_hashes": source_hashes, "diagnostic_script_sha256": digest(Path(__file__)),
        "member_files": len(entries), "neural_execution_performed": False,
        "checkpoint_loading_performed": False, "provider_calls_performed": False,
        "completed_stages": [], "errors": [], "progress": {},
        "boundary": "Stored-result diagnostic only. The original GPU cleanup and full protocol gates remain failed. No independent neural execution, allocation-owner diagnosis, model promotion, learning advantage or complete-CNCM claim.",
    }
    try:
        validator, receipt["published_schema"] = stored.protected_schema()
        receipt["trace_schema_validation"] = stored.validate_all_traces(records, validator,
            progress=receipt["progress"].setdefault("traces", {}))
        receipt["completed_stages"].append("all_stored_traces")
        receipt["smoke"] = stored.audit_smoke(records, progress=receipt["progress"].setdefault("smoke", {}))
        receipt["completed_stages"].append("smoke_stored_semantics")
        receipt["full"] = stored.audit_full(records, progress=receipt["progress"].setdefault("full", {}))
        receipt["completed_stages"].append("all_sealed_choices_and_native_results")
        receipt["evaluation_groups"] = stored.audit_evaluation_groups(records, receipt["full"])
        receipt["completed_stages"].append("paired_group_results")
    except Exception as error:
        receipt["errors"].append({"type": type(error).__name__, "reason": str(error),
                                   "traceback": traceback.format_exc()})
    finally:
        records.verify_all()
        require(digest(packet_path) == PACKET_HASH, "ORIGINAL_PACKET_CHANGED")
        require(all(digest(ROOT / name) == value for name, value in source_hashes.items()), "DEPENDENCY_CHANGED")
        require(digest(Path(__file__)) == receipt["diagnostic_script_sha256"], "DIAGNOSTIC_CHANGED")
        receipt["loaded_project_modules"] = project_imports.loaded_records()
        receipt["all_original_evidence_unchanged"] = True
    receipt["diagnostic_completed"] = not receipt["errors"]
    receipt["status"] = ("CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED"
                         if not receipt["errors"] else "CAS_META_2_V2_STORED_DIAGNOSTIC_FAILED")
    receipt["utc"] = datetime.now(timezone.utc).isoformat()
    receipt["command"] = sys.argv
    receipt["python"] = sys.version
    no_links(output)
    output.mkdir(exist_ok=False)
    adapter_bytes = json.dumps(receipt["presentation_order_adapter"], sort_keys=True, indent=2).encode("utf-8") + b"\n"
    (output / "presentation_order_adapter.json").write_bytes(adapter_bytes)
    receipt["presentation_order_adapter_file_sha256"] = sha256(adapter_bytes).hexdigest()
    (output / "diagnostic_receipt.json").write_bytes(
        json.dumps(receipt, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    print(json.dumps({key: receipt[key] for key in ("status", "diagnostic_completed", "full_protocol_accepted", "errors")}))
    return 0 if receipt["diagnostic_completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

