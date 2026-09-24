"""AWS T4 checks for the larger-question path (v0.1, revision 1). Forward passes only. No training. GPU only.

PLAIN SUMMARY. Four checks, always run in the order d, c, b, a, so the most important check cannot be the one a
wall stop cuts. Each check emits PASS or FAIL from measured values; the program then emits one verdict.

  d  FULL_LEARNER_SUBCLASS. Two fresh learners built from the same seed, `PointerCourseLearner` and
     `LargerQuestionPointerLearner`, must start identical and give byte-identical predictions on the course
     packets. The subclass answers every fixture, refuses the refusal fixtures without moving a counter, and
     refuses to train. The original learner refuses the 6-node correspondence fixture F20
     (`TYPED_PERMUTATION_BOUND`), which is why the path exists. Two pairs are checked:
       ON  - the switch ON, as `PointerCourseLearner` builds it; all 564 course packets.
       OFF - the switch OFF; every 8th course packet (71 of 564), all fixtures, all refusals. `PointerCourseLearner`
             cannot be asked for the switch OFF, so for the two constructor calls ONLY, the module-level
             `pointer_learner._build_container` is replaced by a wrapper that passes
             `analogy_focus_comparison=False`, and is restored straight after (in `finally`). No file is edited.
             Both learners' `module.analogy_focus_comparison` is read back and must be False.
  c  SEVEN_NODE_REFUSAL. Every refusal fixture (a 7-node world; a node of degree 5) raises `LargerPathRefusal`
     with its named code, and `GraphForward` is never called.
  b  FIXTURES_THROUGH_LEARNER. Every public 5- and 6-node fixture goes read -> forward -> decode -> checker v2
     grade with no error, on five containers: the three trained Helm 2.0 final checkpoints (switch OFF), a fresh
     switch-OFF container and a fresh switch-ON container. Each row also records the raw `whole` and `part`
     query positions Helm reads (`pointer_learner.py:1102-1103`) and whether they pass the trained range (0-3).
  a  OLD_PACKET_PRESERVATION_AGAINST_T4_HISTORY. The six Helm 2.0 checkpoints (seeds 20260917-19, initial and
     final) are loaded into a switch-OFF container exactly as `preservation_digest.py` loads them. All 564 course
     packets go through `predict_packet`; every one must take the ORIGINAL route. The per-model overall logit
     digest must equal the `overall_digest` the T4 item-1 job recorded for the same checkpoint (see T4_REFERENCE).

ORDER OF WORK.
  1. `--list-inputs` prints REQUIRED_INPUTS as JSON and exits 0. It imports no torch and no project code.
  2. The outputs are create-only: the run refuses (exit 4) if `--out`, `--out.partial` or `--out.rows.jsonl` exists.
  3. Every REQUIRED_INPUTS file must exist with its exact bytes and sha256; the two source trees must be present;
     the two wheels must be importable. Torch is not imported yet. A failure is SETUP_REFUSED (exit 4).
  4. torch and CUDA (exit 2 without them). If check a is requested, the torch build and the GPU must match the
     T4 reference, or the digests would not be comparable (SETUP_REFUSED:T4_REFERENCE_ENVIRONMENT_DIFFERS).
  5. Context: the pinned course, the fixtures and the source pins (exit 4 on a mismatch).
  6. Preflight: about 20 timed forward passes project the total; above WALL_SECONDS it refuses (exit 5,
     PREFLIGHT_OVER_WALL_LIMIT) before the main work.
  7. Checks d, c, b, a. Every finished row (one model, one fixture, one refusal, one learner pair) is appended to
     `<out>.rows.jsonl` at once, flushed and fsynced, so a stop at the wall limit keeps everything that ran.
     The summary `<out>` is written once, at the end or at a stop, create-only.

WHAT IS WRITTEN. No correct/incorrect field is written. But right/wrong CAN be recomputed from what is written:
`answer_sha256` is the sha256 of the canonical answer, and the public fixture file holds every correct value;
`check_digest` is the checker's digest over a receipt body that contains `correct`. These are public plumbing
fixtures, so this is acceptable here. This recording scheme must NEVER be used for sealed items.

    CAS_META2_RUN_TEACHING_CYCLE=1 python -B t4_larger_question_checks.py --out RESULT.json [--checks d,c,b,a]
    python -B t4_larger_question_checks.py --list-inputs

The environment variable is the learner's own execution guard (`teaching_cycle/gpu_adapter.py:37-39`); check d
needs it and a Linux worker. It is never set by this script.

Exit codes: 0 = all four checks PASS; 1 = a check FAILED or was not run; 2 = GPU_REQUIRED (no torch or no CUDA);
3 = WALL_LIMIT_REACHED; 4 = SETUP_REFUSED (inputs, outputs, source drift, reference environment, identities);
5 = PREFLIGHT_OVER_WALL_LIMIT.
"""
import argparse
import collections
from copy import deepcopy
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import pathlib
import platform
import sys
import time
import traceback

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
HERE = pathlib.Path(__file__).resolve().parent
RESEARCH = HERE.parent
PACKAGE = HERE.parents[2]
REPO_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
SCHEMA = "claude.helm-larger-question-t4-checks/0.2"
CHECK_ORDER = ("d", "c", "b", "a")
CHECK_NAMES = {"d": "FULL_LEARNER_SUBCLASS", "c": "SEVEN_NODE_REFUSAL", "b": "FIXTURES_THROUGH_LEARNER",
               "a": "OLD_PACKET_PRESERVATION_AGAINST_T4_HISTORY"}
SEEDS = (20260917, 20260918, 20260919)
FRESH_SEED = 20260917
WALL_SECONDS = 3600
EXPECTED_COURSE_PACKETS = 564
D_OFF_COURSE_STRIDE = 8                 # the switch-OFF learner pair sees ids[::8]: 71 of the 564 course packets
TRAINED_MAX_QUERY_POSITION = 3          # course focus worlds have at most 4 nodes, so `whole`/`part` are 0..3
PREFLIGHT_COURSE_CALLS = 16             # timed `predict_packet` calls on course packets
PREFLIGHT_FIXTURE_IDS = ("F20", "H01", "F17", "F24")   # timed `predict_packet` + checker v2 grade
PREFLIGHT_LEARNER_CALLS = 3             # timed `PointerCourseLearner.predict` calls (only if check d can run)
PREFLIGHT_MARGIN = 1.15                 # the remaining work is multiplied by this before it is compared

# (bytes, sha256) of the Helm 2.0 checkpoints, read from the committed git blobs on 2026-09-23. They equal the
# `artifact_manifest.json` rows of each receipt (checked for seed 20260917) and the T4 reference rows below.
CHECKPOINTS = {
    (20260917, "initial"): (2235079, "59dd46877bd7bf97dbb4059975051cc6102b374d5c387d3a183884048b71b004"),
    (20260917, "final"): (3670007, "c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb"),
    (20260918, "initial"): (2235079, "d3c6292f2c0d09e29952bfe353d47fff058741d42c0a8e8dbe7a80eaad8fd645"),
    (20260918, "final"): (3670007, "a6e72caac1fccbd994433a46684846f5a3de48683dcc6b5def5946b85ef20658"),
    (20260919, "initial"): (2235079, "93b84558c0123673eabcc462f68afe8ecb1537b598e297ee16f7a7458787ee9f"),
    (20260919, "final"): (3670007, "c83e0123643a2433e1650bd4898dc28865204fd3d03fbedd22910632caf7dec8"),
}


def _checkpoint_path(seed, phase):
    return "records/typed_pointer_001/receipt_%d/checkpoints/%s.pt" % (seed, phase)


_WHEELS = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
# Every data file the run reads, relative to the CNCM root (`PACKAGE`; in git: REPO_PREFIX). Raw bytes; all
# committed blobs, none with a CR byte. The material and wheel rows equal `worker_contract.MATERIAL`,
# `matched_contract.DEVELOPMENT_PIN` and `worker_contract.WHEELS` (a torch-free test checks this).
REQUIRED_INPUTS = (
    {"path": "records/typed_course_001/checks_002/public_course.json", "bytes": 4165195,
     "sha256": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
     "why": "the frozen course: 564 packets and the 64-world bank (pointer_contract.load_material)"},
    {"path": "records/typed_interface_001/checks_002/training_tokenizer.json", "bytes": 447140,
     "sha256": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
     "why": "the frozen tokenizer (load_material; the encoder of check d)"},
    {"path": "records/typed_matched_001/development_001/compact_development.json", "bytes": 685549,
     "sha256": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4",
     "why": "read and checked by matched_contract.load_material, which pointer_contract.load_material is"},
    {"path": _WHEELS + "casformer_reference-0.1.0-py3-none-any.whl", "bytes": 36501,
     "sha256": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
     "why": "wheel; real_framework imports `casformer` (install with pip --no-deps before the run)"},
    {"path": _WHEELS + "cas_neural_cjt-0.2.0-py3-none-any.whl", "bytes": 221994,
     "sha256": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9",
     "why": "wheel; real_framework imports `cas_cjt` (install with pip --no-deps before the run)"},
    *({"path": _checkpoint_path(seed, phase), "bytes": CHECKPOINTS[(seed, phase)][0],
       "sha256": CHECKPOINTS[(seed, phase)][1], "why": "Helm 2.0 checkpoint (checks a and b)"}
      for seed in SEEDS for phase in ("initial", "final")),
    {"path": "research/CAS_META_2_COMPOSITION/eval_paths/fixtures/larger_question_fixtures_v0_1.json",
     "bytes": 190466, "sha256": "7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3",
     "why": "the 41 public fixtures (checks b, c, d)"},
)
# Shipped whole (`*.py`), exactly as the training launcher ships them (`worker_contract.py:138-139`). The protected
# files inside are pinned by `larger_question_scope.PROTECTED_SOURCE_LF_SHA256`; check a also pins the five files
# of T4_REFERENCE_SOURCE_LF_SHA256.
REQUIRED_SOURCE_TREES = ("cncm", "research/CAS_META_2_COMPOSITION/cas_meta2")
# The code under test. Not pinned here (a file cannot pin itself); their LF sha256 is written into the record.
EVAL_PATHS_FILES = ("__init__.py", "larger_question_scope.py", "larger_question_learner.py",
                    "larger_question_fixtures.py", "t4_larger_question_checks.py")
# Importable top-level modules the two wheels provide, and the installed distribution versions.
WHEEL_MODULES = {"casformer": ("casformer_reference", "0.1.0"), "cas_cjt": ("cas_neural_cjt", "0.2.0")}

# ---- check a's reference: the T4 item-1 job (HELM-ANALOGY-REPAIR-1, attempt 2) --------------------------------
# Read with `git show 41071a3f:<folder>/<file>` from origin/research/helm-integration-20260923 on 2026-09-23.
# COMPARED FIELD: `results[i].overall_digest` of the row whose `checkpoint` is `_checkpoint_path(seed, phase)` and
# whose `checkpoint_sha256` equals CHECKPOINTS. It is the SAME QUANTITY as this script's `overall_digest`:
#   * per record: sha256 of compact sorted-key JSON `{slot_id: ["%08x" float32 bit patterns]}` of the head
#     logits (`preservation_digest.py:98-100`; `larger_question_learner.logit_bits_digest`);
#   * overall: sha256 of the newline-joined "record_id digest" lines over the sorted 564 record ids (`:101`);
#   * same logits: `GraphForward(...).head_logits(plan, indicators)` with the plan from the frozen
#     `slots.compile_slots`, the reading from `pointer_inputs.read_packet` and the same role indicators; on the
#     ORIGINAL route `predict_packet` calls exactly these;
#   * same container: `_build_container(torch, _framework(torch, device, seed), device,
#     analogy_focus_comparison=False)`, strict `load_state_dict` of `torch.load(...)["model_state"]`, eval mode;
#   * same source (T4_REFERENCE_SOURCE_LF_SHA256), same course digest, same determinism settings;
#   * same torch build and GPU class (checked before the run; bits may differ on other hardware or builds).
# The OFF rows (repaired source, switch OFF) equal the control rows (unchanged Helm 2.0 source 20208c92) on all
# six checkpoints, so the reference is also Helm 2.0's own T4 history.
T4_REFERENCE = {
    "commit": "41071a3f1dd86ffbb00dbf07233c32dcea5e8a1b",
    "branch": "origin/research/helm-integration-20260923",
    "folder": "records/helm_eval_design_20260923/analogy_repair_t4_job/results",
    "files_sha256": {
        "preservation_OFF_T4_seed20260917.json": "27f856d9f7d1d48bf220321d33e589910822850e4efedb6b5f5cb9f159d58890",
        "preservation_OFF_T4_seed20260918.json": "f36e44ead4d6759b11b0766fd3bf04d6ef58d6c75bf72c03d55ef9caa3482efa",
        "preservation_OFF_T4_seed20260919.json": "abc1ece79e195280bbaf4c597a72eb87b97f196974aa250b22153e75f72801cd",
        "preservation_control_20208c92_T4_seed20260917.json":
            "8ffa0ac95c21a16cdbd1c71ec8f68bb18b82dfbaa8ec340efef578231e841749",
        "preservation_control_20208c92_T4_seed20260918.json":
            "fff9e352b13c8120a8bf264e06169aab264cc86d175d5d53cd17f04dd96c18c2",
        "preservation_control_20208c92_T4_seed20260919.json":
            "24b006a5e711878ea5fb036a0a8c820d9e8ac510226840bb076ef5c89884890d",
    },
    "compared_field": "results[].overall_digest",
    "tool": "records/helm_eval_design_20260923/analogy_wiring_probe/preservation_digest.py",
    "tool_sha256_lf": "21bf01e5411d3d959bd8106f8f6a7ca6ca158d97f4000c0b060d57e99176292e",
    "container_kwargs_off": {"analogy_focus_comparison": False},
    "course_digest": "272c26e1391c65607d40ff7ae67522402f6a2af553478d32ea6daa0e8e706dbb",
    "torch": "2.11.0+cu128",
    "gpu_name_contains": "T4",
    "instance": "g4dn.2xlarge (Tesla T4)",
}
T4_REFERENCE_OVERALL_DIGEST = {
    (20260917, "initial"): "1aaa01da42a8f754470696a6b35b08ac876cead7f36e29e939ae0e720972ba0a",
    (20260917, "final"): "949b371973745a0686537f9c9031451c9d3558a35e0b23c94b79ef5a23155806",
    (20260918, "initial"): "47e4cfb267aec4f959388aa4c8a4d37d2d52b8c60d7b8d3afb33b8aca3ebd365",
    (20260918, "final"): "5cede80f347b84b05a402e698417153076f3edd053daa32e008ce38f37a050a7",
    (20260919, "initial"): "fc2412f665a98884399209c0d0d9b7fa28c56ed0a98786ab2eb196f0467be858",
    (20260919, "final"): "62c188861902422664fcf59535d6b8011b34d7db5bcdb377ab95ce21fc00375a",
}
_TYPED = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
T4_REFERENCE_SOURCE_LF_SHA256 = {       # the reference run's `source_sha256_lf` (OFF files)
    "cncm/typed_matched_worker.py": "51afa5e5ca908356c53381c30767b65ae9057c388aa2cc0b231fbb5be4dd6522",
    _TYPED + "pointer_contract.py": "70be7ae7b7b3dbefd6a5d168b04ab7394718d7456a264614236d31b0c9c09b3d",
    _TYPED + "pointer_inputs.py": "ba920d9e65e20b96dd0614a7131a80b9b87dd9918cb07d94ec5ebb4b628d0ecd",
    _TYPED + "pointer_learner.py": "2ebb1b086953002272d18e75d397bb233b75f62442d073487ebade2e93487781",
    _TYPED + "slots.py": "3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487",
}
BOUNDARY = ("Plumbing checks only: forward passes under torch.no_grad(); no optimizer step and no checkpoint "
            "written. Nothing here measures Helm's accuracy. The fixtures are public and not an evaluation set. "
            "No correct/incorrect field is written, but right/wrong is recomputable from answer_sha256 and "
            "check_digest with the public fixture file; acceptable for public fixtures, never for sealed items.")


class SetupRefused(Exception):
    pass


class WallLimit(Exception):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _lf_sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _error(error):
    return {"type": type(error).__name__, "message": str(error)[:400]}


def _overall_digest(ids, per_record):
    """`preservation_digest.py:101`: sha256 of the newline-joined "record_id digest" lines, ids sorted."""
    return hashlib.sha256("\n".join("%s %s" % (rid, per_record[rid]) for rid in ids).encode()).hexdigest()


def learner_guard_ok():
    """The learner's own execution guard (`gpu_adapter.execution_guard`), read without calling it."""
    return platform.system() == "Linux" and os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") == "1"


# ------------------------------------------------------------------------------------------------ inputs
def list_inputs():
    """Everything a bundle must carry. Constants only: no file is read, no torch and no project code imported."""
    return {"schema": SCHEMA, "root": REPO_PREFIX, "required_inputs": deepcopy(list(REQUIRED_INPUTS)),
            "required_source_trees": [{"path": tree, "pattern": "*.py"} for tree in REQUIRED_SOURCE_TREES],
            "eval_paths_files": ["research/CAS_META_2_COMPOSITION/eval_paths/" + name for name in EVAL_PATHS_FILES],
            "installed_wheel_modules": {name: {"distribution": dist, "version": version}
                                        for name, (dist, version) in WHEEL_MODULES.items()},
            "runtime": {"torch": "a CUDA build; check a needs " + T4_REFERENCE["torch"] + " on a T4",
                        "environment": "CAS_META2_RUN_TEACHING_CYCLE=1 and Linux for check d"}}


def _installed_version(distribution):
    for name in (distribution, distribution.replace("_", "-")):
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def verify_inputs(requested, root=PACKAGE):
    """Existence, bytes and sha256 of every input, BEFORE torch is imported. Raises `SetupRefused` by name."""
    root = pathlib.Path(root)
    files = []
    for spec in REQUIRED_INPUTS:
        path = root / spec["path"]
        if not path.is_file():
            raise SetupRefused("INPUT_MISSING:" + spec["path"])
        raw = path.read_bytes()
        if len(raw) != spec["bytes"] or hashlib.sha256(raw).hexdigest() != spec["sha256"]:
            raise SetupRefused("INPUT_MISMATCH:" + spec["path"])
        files.append({"path": spec["path"], "bytes": len(raw), "sha256": spec["sha256"]})
    trees = {}
    for tree in REQUIRED_SOURCE_TREES:
        paths = sorted((root / tree).rglob("*.py"))
        if not paths:
            raise SetupRefused("SOURCE_TREE_MISSING:" + tree)
        lines = ["%s %s" % (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                 for path in paths]
        trees[tree] = {"py_files": len(paths), "digest": hashlib.sha256("\n".join(lines).encode()).hexdigest()}
    eval_files = {}
    for name in EVAL_PATHS_FILES:
        path = root / "research/CAS_META_2_COMPOSITION/eval_paths" / name
        if not path.is_file():
            raise SetupRefused("INPUT_MISSING:eval_paths/" + name)
        eval_files[name] = _lf_sha256(path)
    wheels = {}
    for module, (distribution, version) in WHEEL_MODULES.items():
        if importlib.util.find_spec(module) is None:
            raise SetupRefused("WHEEL_NOT_IMPORTABLE:" + module)
        installed = _installed_version(distribution)
        if installed != version:
            raise SetupRefused("WHEEL_VERSION:%s:%s" % (distribution, installed))
        wheels[module] = {"distribution": distribution, "version": installed}
    reference_source = {}
    if "a" in requested:
        for name, expected in T4_REFERENCE_SOURCE_LF_SHA256.items():
            observed = _lf_sha256(root / name) if (root / name).is_file() else None
            if observed != expected:
                raise SetupRefused("T4_REFERENCE_SOURCE_DIFFERS:" + name)
            reference_source[name] = observed
    return {"files": files, "source_trees": trees, "eval_paths_lf_sha256": eval_files,
            "wheels_installed": wheels, "t4_reference_source_lf_sha256": reference_source}


# ------------------------------------------------------------------------------------------------ outputs
class RowWriter:
    """Append-only, create-only JSON Lines file. Every row is flushed and fsynced the moment it is written."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.handle = open(self.path, "x", encoding="utf-8", newline="\n")
        self.count = collections.Counter()

    def emit(self, check, row):
        self.handle.write(_canonical({"check": check, **row}) + "\n")
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.count[check] += 1

    def close(self):
        if not self.handle.closed:
            self.handle.close()


def _publish(path, payload):
    """Write the summary once, create-only: `.partial` (exclusive create) then a hard link that refuses to replace."""
    path = pathlib.Path(path)
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    partial = pathlib.Path(str(path) + ".partial")
    with open(partial, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(partial, path)
    except FileExistsError:
        raise
    except OSError:  # a filesystem without hard links: still create-only, not atomic
        with open(path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    os.unlink(partial)


# ------------------------------------------------------------------------------------------------ context
class Context:
    """Everything the checks share. Built only after the input and CUDA checks have passed."""

    def __init__(self, torch, device, started, rows, requested):
        self.torch, self.device, self.started, self.rows = torch, device, started, rows
        sys.dont_write_bytecode = True
        for path in (PACKAGE, RESEARCH):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from cas_meta2.typed_teaching import (answers, pointer_contract, pointer_inputs, pointer_learner, slots,
                                              source, worker_contract)
        from cncm.typed_matched_worker import _framework
        from eval_paths import larger_question_scope
        try:
            # Checked BEFORE the learner half is imported (that import re-checks the same pins).
            self.source_pins = larger_question_scope.verify_source_pins()
        except larger_question_scope.LargerPathRefusal as error:
            raise SetupRefused(str(error)) from error
        from eval_paths import larger_question_fixtures, larger_question_learner
        self.answers, self.contract, self.pointer_inputs = answers, pointer_contract, pointer_inputs
        self.PL, self.slots, self.source, self.worker_contract = pointer_learner, slots, source, worker_contract
        self.framework = _framework
        self.FX, self.LL, self.scope = larger_question_fixtures, larger_question_learner, larger_question_scope
        frozen, tokenizer = pointer_contract.load_material(PACKAGE)[:2]
        self.course_digest, self.tokenizer = frozen["course_digest"], tokenizer
        if "a" in requested and self.course_digest != T4_REFERENCE["course_digest"]:
            raise SetupRefused("T4_REFERENCE_COURSE_DIGEST")
        self.packets = dict(pointer_contract.public_packets(frozen))
        self.ids = sorted(self.packets)
        if len(self.ids) != EXPECTED_COURSE_PACKETS:
            raise SetupRefused("COURSE_PACKET_COUNT:%d" % len(self.ids))
        self.tagger = pointer_learner.role_tagger(str(PACKAGE))
        try:
            self.document, self.fixtures = larger_question_fixtures.load()
        except ValueError as error:
            raise SetupRefused("FIXTURE_IDENTITY:" + str(error)) from error
        rows = {row["fixture_id"]: row for row in self.document["fixtures"]}
        self.fixture_rows = rows
        self.larger_ids = sorted(key for key, row in rows.items() if "expected_refusal" not in row)
        self.refused_ids = sorted(key for key, row in rows.items() if "expected_refusal" in row)
        if not set(PREFLIGHT_FIXTURE_IDS) <= set(self.larger_ids) or "F20" not in self.larger_ids:
            raise SetupRefused("FIXTURE_IDS")
        self._encoder = None
        del frozen

    def wall(self):
        if time.monotonic() - self.started > WALL_SECONDS:
            raise WallLimit()

    def emit(self, check, row):
        self.rows.emit(check, row)

    def container(self, seed, phase, *, switch):
        """A pointer container. `phase` None = fresh; otherwise a pinned Helm 2.0 checkpoint, loaded strictly."""
        torch = self.torch
        model = self.PL._build_container(torch, self.framework(torch, self.device, seed), self.device,
                                         analogy_focus_comparison=switch)
        checkpoint = None
        if phase is not None:
            path = PACKAGE / _checkpoint_path(seed, phase)
            raw = path.read_bytes()
            size, digest = CHECKPOINTS[(seed, phase)]
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                raise SetupRefused("CHECKPOINT_PIN:%d:%s" % (seed, phase))
            state = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)["model_state"]
            model.load_state_dict(state, strict=True)
            checkpoint = {"seed": seed, "phase": phase, "path": _checkpoint_path(seed, phase), "sha256": digest}
        model.eval()
        if model.analogy_focus_comparison is not switch:
            raise SetupRefused("SWITCH_STATE")
        return model, checkpoint

    def encoder(self):
        """The frozen typed encoder the learners need, built once (as `cncm/typed_pointer_worker.py:869-884`)."""
        if self._encoder is None:
            from cas_meta2.typed_teaching import encoder as encoder_module
            self._encoder = encoder_module.build_frozen_typed_encoder(
                self.torch, self.tokenizer, seed=self.contract.DESIGN["encoder_seed"], d_model=64,
                device=self.device)
        return self._encoder

    def learner_kwargs(self, run_id):
        design = self.contract.DESIGN
        return {"optimizer_config": deepcopy(design["optimizer_config"]),
                "run_context": {"run_id": run_id,
                                "course_sha256": self.contract.MATERIAL[self.worker_contract.COURSE_PATH]["sha256"],
                                "condition": design["condition"], "source_seed": design["source_seed"]},
                "limits": {"max_updates": 1, "max_core_calls": 1000000, "max_wall_seconds": 7200},
                "device": self.device, "tagger": self.tagger, "python_seed": FRESH_SEED, "root": str(PACKAGE)}

    def original_steps(self, model, packet):
        """The ORIGINAL scoring steps of `PointerCourseLearner._graph` with the frozen `slots`, no route."""
        torch, PL, slots = self.torch, self.PL, self.slots
        with torch.no_grad():
            plan = slots.compile_slots(packet)
            reading = self.pointer_inputs.read_packet(packet)
            reading["_device"] = self.device
            forward = PL.GraphForward(torch, model, reading, self.device)
            indicators = (self.tagger.indicators(packet) if reading["query"]["kind_name"] == "role_set"
                          else [0] * PL.CLAUSE_COUNT)
            rows = forward.head_logits(plan, indicators)
            scores = PL._logit_rows(torch, plan, PL._scalar_scores(torch, rows))
            decisions = slots.score_decisions(packet, scores)
            answer = slots.assemble_answer(packet, decisions)
        return {"plan": plan, "rows": rows, "scores": scores, "decisions": decisions, "answer": answer}


# ------------------------------------------------------------------------------------------------ preflight
def planned_work(ids, larger_ids, refused_ids, requested, *, learner_ok):
    """Forward-pass calls and builds each requested check plans. Pure; the preflight multiplies it by timings."""
    work = collections.Counter()
    if "a" in requested:
        work["pp_course_calls"] += len(SEEDS) * 2 * len(ids)
        work["container_builds"] += len(SEEDS) * 2
    if "b" in requested:
        work["pp_fixture_calls"] += (len(SEEDS) + 2) * len(larger_ids)
        work["container_builds"] += len(SEEDS) + 2
    if "c" in requested:
        work["pp_fixture_calls"] += len(refused_ids)          # informational ORIGINAL steps; refusals cost 0
        work["container_builds"] += 3
    if "d" in requested and learner_ok:
        work["learner_course_calls"] += 2 * len(ids) + 2 * len(ids[::D_OFF_COURSE_STRIDE])
        work["learner_fixture_calls"] += 2 * len(larger_ids)
        work["learner_builds"] += 4
    return dict(work)


def project_total(elapsed, timings, work):
    """Projected wall seconds for the whole run: elapsed so far plus PREFLIGHT_MARGIN x the remaining work."""
    learner_fixture = max(timings["pp_fixture"], timings["learner_course"] - timings["pp_course"]
                          + timings["pp_fixture"])
    remaining = (work.get("pp_course_calls", 0) * timings["pp_course"]
                 + work.get("pp_fixture_calls", 0) * timings["pp_fixture"]
                 + work.get("learner_course_calls", 0) * timings["learner_course"]
                 + work.get("learner_fixture_calls", 0) * learner_fixture
                 + work.get("container_builds", 0) * timings["container_build"]
                 + work.get("learner_builds", 0) * timings["learner_build"])
    return {"elapsed_seconds": elapsed, "remaining_seconds_unmargined": remaining, "margin": PREFLIGHT_MARGIN,
            "projected_total_seconds": elapsed + PREFLIGHT_MARGIN * remaining, "wall_seconds": WALL_SECONDS}


def preflight(ctx, requested):
    """About 20 timed forward passes. Returns the preflight row; the caller refuses if the projection is over."""
    torch, LL, scope, PL = ctx.torch, ctx.LL, ctx.scope, ctx.PL
    clock = time.monotonic
    start = clock()
    model, _ = ctx.container(FRESH_SEED, None, switch=False)
    container_build = clock() - start
    step = max(1, len(ctx.ids) // PREFLIGHT_COURSE_CALLS)
    sample = ctx.ids[::step][:PREFLIGHT_COURSE_CALLS]
    for rid in ctx.ids[-2:]:  # warm-up, not timed: the first calls pay CUDA and cuBLAS start-up
        LL.predict_packet(torch, model, ctx.packets[rid], ctx.device, tagger=ctx.tagger)
    course, fixture = [], []
    for rid in sample:  # the per-packet work of check a
        ctx.wall()
        start = clock()
        result = LL.predict_packet(torch, model, ctx.packets[rid], ctx.device, tagger=ctx.tagger)
        LL.logit_bits_digest(torch, result["rows"])
        course.append(clock() - start)
    for key in PREFLIGHT_FIXTURE_IDS:  # the per-fixture work of check b
        ctx.wall()
        packet = ctx.fixtures[key]
        start = clock()
        result = LL.predict_packet(torch, model, packet, ctx.device, tagger=ctx.tagger)
        scope.compile_plan(packet)
        ctx.answers.validate_answer(packet["source"], packet["record"]["query"], result["answer"])
        scope.grade(packet, result["answer"])
        LL.logit_bits_digest(torch, result["rows"])
        fixture.append(clock() - start)
    del model
    torch.cuda.empty_cache()
    learner_ok = "d" in requested and learner_guard_ok()
    learner, learner_build = [], 0.0
    if learner_ok:
        encoder = ctx.encoder()  # built once and reused by check d; its build time is already in `elapsed`
        start = clock()
        probe = PL.PointerCourseLearner(torch, ctx.framework(torch, ctx.device, FRESH_SEED), encoder,
                                        **ctx.learner_kwargs("larger-question-path-preflight"))
        learner_build = clock() - start
        probe.predict(ctx.packets[ctx.ids[-1]], PL.PREDICTION_DEPTH)  # warm-up, not timed
        for rid in sample[:PREFLIGHT_LEARNER_CALLS]:
            ctx.wall()
            start = clock()
            probe.predict(ctx.packets[rid], PL.PREDICTION_DEPTH)
            learner.append(clock() - start)
        del probe
        torch.cuda.empty_cache()
    pp_course = sum(course) / len(course)
    timings = {"pp_course": pp_course, "pp_fixture": sum(fixture) / len(fixture),
               "learner_course": sum(learner) / len(learner) if learner else pp_course,
               "container_build": container_build, "learner_build": learner_build}
    work = planned_work(ctx.ids, ctx.larger_ids, ctx.refused_ids, requested, learner_ok=learner_ok)
    projection = project_total(clock() - ctx.started, timings, work)
    return {"row": "preflight", "timed_calls": {"predict_packet_course": len(course),
                                                "predict_packet_fixture_and_grade": len(fixture),
                                                "learner_predict": len(learner)},
            "seconds": {"course": course, "fixture": fixture, "learner": learner}, "timings": timings,
            "planned_work": work, **projection,
            "fits": projection["projected_total_seconds"] <= WALL_SECONDS}


# ------------------------------------------------------------------------------------------------ check d
def _build_pair(ctx, switch):
    """`PointerCourseLearner` and `LargerQuestionPointerLearner` from the same seed, with the switch as asked."""
    PL, LL, torch = ctx.PL, ctx.LL, ctx.torch
    kwargs, encoder = ctx.learner_kwargs("larger-question-path-check"), ctx.encoder()
    original_build = PL._build_container
    if not switch:
        def build_switch_off(torch_module, framework, device, **options):
            if "analogy_focus_comparison" in options:
                raise ValueError("D_OFF_CALLER_ALREADY_SETS_THE_SWITCH")
            return original_build(torch_module, framework, device, analogy_focus_comparison=False, **options)
        PL._build_container = build_switch_off
    try:
        original = PL.PointerCourseLearner(torch, ctx.framework(torch, ctx.device, FRESH_SEED), encoder, **kwargs)
        larger = LL.LargerQuestionPointerLearner(torch, ctx.framework(torch, ctx.device, FRESH_SEED), encoder,
                                                 **kwargs)
    finally:
        PL._build_container = original_build
    if not (original.module.analogy_focus_comparison is switch and larger.module.analogy_focus_comparison is switch):
        raise ValueError("D_SWITCH_STATE")
    return original, larger


def _learner_pair(ctx, label, switch, course_ids):
    torch, PL, scope = ctx.torch, ctx.PL, ctx.scope
    original, larger = _build_pair(ctx, switch)
    same_start = (PL.state_identity(torch, dict(original.module.state_dict()))
                  == PL.state_identity(torch, dict(larger.module.state_dict()))
                  and original.run_identity_digest == larger.run_identity_digest)
    mismatches = []
    for rid in course_ids:
        ctx.wall()
        a = original.predict(ctx.packets[rid], PL.PREDICTION_DEPTH)
        b = larger.predict(ctx.packets[rid], PL.PREDICTION_DEPTH)
        if _canonical(a) != _canonical(b):
            mismatches.append(rid)
    counters_equal = original.counters == larger.counters
    pair = {"label": label, "switch": switch, "same_start": same_start, "course_packets": len(course_ids),
            "prediction_mismatches": len(mismatches), "mismatched_record_ids": mismatches[:20],
            "counters_equal_after_course": counters_equal}
    ctx.emit("d", {"row": "course_pair", **pair})
    fixture_errors = 0
    for key in ctx.larger_ids:
        ctx.wall()
        packet = ctx.fixtures[key]
        try:
            prediction = larger.predict(packet, PL.PREDICTION_DEPTH)
            grade = scope.grade(packet, prediction["answer"])
            if type(grade["correct"]) is not bool:
                raise ValueError("GRADE_NOT_BOOLEAN")
            row = {"fixture_id": key, "prediction_id": prediction["prediction_id"], "graded": True,
                   "check_digest": grade["check"]["check_digest"]}
        except Exception as error:  # noqa: BLE001 - every error is recorded and fails the check
            fixture_errors += 1
            row = {"fixture_id": key, "error": _error(error)}
        ctx.emit("d", {"row": "fixture", "label": label, **row})
    try:
        original.predict(ctx.fixtures["F20"], PL.PREDICTION_DEPTH)
        original_refuses = {"refused": False}
    except Exception as error:  # noqa: BLE001
        original_refuses = {"refused": "TYPED_PERMUTATION_BOUND" in str(error), "error": _error(error)}
    ctx.emit("d", {"row": "original_refuses_F20", "label": label, **original_refuses})
    refusal_ok = True
    for key in ctx.refused_ids:
        before = dict(larger.counters)
        try:
            larger.predict(ctx.fixtures[key], PL.PREDICTION_DEPTH)
            row = {"fixture_id": key, "refused": False}
        except scope.LargerPathRefusal as error:
            row = {"fixture_id": key, "refused": True, "code": error.code}
        except Exception as error:  # noqa: BLE001
            row = {"fixture_id": key, "refused": False, "error": _error(error)}
        row["counters_unchanged"] = larger.counters == before
        refusal_ok = (refusal_ok and row["refused"] and row.get("code") == ctx.fixture_rows[key]["expected_refusal"]
                      and row["counters_unchanged"])
        ctx.emit("d", {"row": "refusal", "label": label, **row})
    training = []
    for name, call in (("stage_batch", lambda: larger.stage_batch([], PL.PREDICTION_DEPTH, cursor=0,
                                                                  occurrence_ids=[])),
                       ("train_sealed_batch", lambda: larger.train_sealed_batch("x", expected_sha256="0" * 64,
                                                                                target_receipts=[]))):
        try:
            call()
            training.append({"method": name, "refused": False})
        except scope.LargerPathRefusal as error:
            training.append({"method": name, "refused": error.code == "INFERENCE_ONLY"})
    ctx.emit("d", {"row": "training_refused", "label": label, "calls": training})
    passed = (same_start and not mismatches and counters_equal and fixture_errors == 0
              and original_refuses["refused"] is True and refusal_ok and all(row["refused"] for row in training))
    del original, larger
    torch.cuda.empty_cache()
    return {**pair, "fixtures": len(ctx.larger_ids), "fixture_errors": fixture_errors,
            "original_learner_refuses_6_node_correspondence": original_refuses, "refusals_ok": refusal_ok,
            "training_refused": training, "verdict": "PASS" if passed else "FAIL"}


def check_d(ctx):
    if not learner_guard_ok():
        return {"name": CHECK_NAMES["d"], "verdict": "FAIL",
                "reason": "ENV_GUARD_NOT_SET: needs Linux and CAS_META2_RUN_TEACHING_CYCLE=1 (learner guard)"}
    pairs = [_learner_pair(ctx, "ON_FRESH_%d" % FRESH_SEED, True, ctx.ids),
             _learner_pair(ctx, "OFF_FRESH_%d_EVERY_%dTH_COURSE_PACKET" % (FRESH_SEED, D_OFF_COURSE_STRIDE), False,
                           ctx.ids[::D_OFF_COURSE_STRIDE])]
    return {"name": CHECK_NAMES["d"], "verdict": "PASS" if all(p["verdict"] == "PASS" for p in pairs) else "FAIL",
            "pairs": pairs,
            "switch_off_scope": ("every %dth sorted course packet (%d of %d), all fixtures and refusals; the OFF "
                                 "learners are built through a scoped, restored substitute of "
                                 "pointer_learner._build_container" % (D_OFF_COURSE_STRIDE,
                                                                        len(ctx.ids[::D_OFF_COURSE_STRIDE]),
                                                                        len(ctx.ids)))}


# ------------------------------------------------------------------------------------------------ check c
def check_c(ctx):
    torch, LL, scope = ctx.torch, ctx.LL, ctx.scope
    failed, count = False, 0
    original_forward, calls = LL.GraphForward, [0]

    def counting(*args, **kwargs):
        calls[0] += 1
        return original_forward(*args, **kwargs)

    for label, switch in (("OFF_FRESH_%d" % FRESH_SEED, False), ("ON_FRESH_%d" % FRESH_SEED, True)):
        model, _ = ctx.container(FRESH_SEED, None, switch=switch)
        for key in ctx.refused_ids:
            ctx.wall()
            expected = ctx.fixture_rows[key]["expected_refusal"]
            before = calls[0]
            LL.GraphForward = counting
            try:
                LL.predict_packet(torch, model, ctx.fixtures[key], ctx.device, tagger=ctx.tagger)
                outcome = {"refused": False}
            except scope.LargerPathRefusal as error:
                outcome = {"refused": True, "code": error.code, "message": str(error)}
            except Exception as error:  # noqa: BLE001
                outcome = {"refused": False, "error": _error(error)}
            finally:
                LL.GraphForward = original_forward
            outcome.update({"fixture_id": key, "container": label, "expected_code": expected,
                            "graph_forward_calls": calls[0] - before})
            ok = outcome["refused"] and outcome.get("code") == expected and outcome["graph_forward_calls"] == 0
            failed = failed or not ok
            count += 1
            ctx.emit("c", {"row": "refusal", "ok": ok, **outcome})
        del model
        torch.cuda.empty_cache()
    # Informational: the ORIGINAL steps answer the 7-node and degree-5 questions without any refusal.
    model, _ = ctx.container(FRESH_SEED, None, switch=False)
    for key in ctx.refused_ids:
        ctx.wall()
        try:
            ctx.original_steps(model, ctx.fixtures[key])
            row = {"fixture_id": key, "original_steps_answered": True}
        except Exception as error:  # noqa: BLE001
            row = {"fixture_id": key, "original_steps_answered": False, "error": _error(error)}
        ctx.emit("c", {"row": "original_steps_without_the_route_INFORMATIONAL", **row})
    del model
    torch.cuda.empty_cache()
    return {"name": CHECK_NAMES["c"], "verdict": "FAIL" if failed or count != 2 * len(ctx.refused_ids) else "PASS",
            "refusal_rows": count}


# ------------------------------------------------------------------------------------------------ check b
def check_b(ctx):
    torch, LL, scope = ctx.torch, ctx.LL, ctx.scope
    positions = {}
    for key in ctx.larger_ids:  # the raw scalar positions Helm reads (`pointer_learner.py:1102-1103`)
        query = ctx.pointer_inputs.read_packet(ctx.fixtures[key])["query"]
        values = [value for value in (query["whole"], query["part"]) if value is not None]
        positions[key] = {"query_whole": query["whole"], "query_part": query["part"],
                          "past_trained_query_range": bool(values) and max(values) > TRAINED_MAX_QUERY_POSITION}
    specs = [("OFF_HELM20_FINAL_%d" % seed, seed, "final", False) for seed in SEEDS]
    specs += [("OFF_FRESH_%d" % FRESH_SEED, FRESH_SEED, None, False),
              ("ON_FRESH_%d" % FRESH_SEED, FRESH_SEED, None, True)]
    containers, failed = [], False
    for label, seed, phase, switch in specs:
        model, checkpoint = ctx.container(seed, phase, switch=switch)
        count, errors = 0, 0
        for key in ctx.larger_ids:
            ctx.wall()
            packet = ctx.fixtures[key]
            try:
                result = LL.predict_packet(torch, model, packet, ctx.device, tagger=ctx.tagger)
                if result["route"] != scope.LARGER:
                    raise ValueError("ROUTE:" + result["route"])
                if _canonical(result["plan"]) != _canonical(scope.compile_plan(packet)[1]):
                    raise ValueError("PLAN_DIFFERS_FROM_SCOPE_PLAN")
                ctx.answers.validate_answer(packet["source"], packet["record"]["query"], result["answer"])
                grade = scope.grade(packet, result["answer"])
                if type(grade["correct"]) is not bool:
                    raise ValueError("GRADE_NOT_BOOLEAN")
                # No correct/incorrect field is written. Right/wrong IS recomputable from `answer_sha256` and
                # `check_digest` with the public fixture file: acceptable for public fixtures, never for sealed items.
                row = {"fixture_id": key, "kind": ctx.fixture_rows[key]["kind"], "route": result["route"],
                       "plan_profile_schema": result["plan"]["profile"]["schema"],
                       "slots": len(result["plan"]["slots"]),
                       "candidates": len(result["plan"]["correspondence_candidates"]),
                       "logit_bits": LL.logit_bits_digest(torch, result["rows"]),
                       "answer_sha256": hashlib.sha256(_canonical(result["answer"]).encode()).hexdigest(),
                       "graded_by": grade["checker_module"], "graded": True,
                       "check_digest": grade["check"]["check_digest"],
                       "admissible_answer_count": grade["admissible_answer_count"], **positions[key]}
            except Exception as error:  # noqa: BLE001 - every error is recorded and fails the check
                errors += 1
                row = {"fixture_id": key, "error": _error(error), **positions[key]}
            count += 1
            ctx.emit("b", {"row": "fixture", "container": label, "switch": switch, "checkpoint": checkpoint, **row})
        failed = failed or errors > 0 or count != len(ctx.larger_ids)
        containers.append({"label": label, "checkpoint": checkpoint, "switch": switch, "fixtures": count,
                           "errors": errors})
        del model
        torch.cuda.empty_cache()
    past = sorted(key for key, row in positions.items() if row["past_trained_query_range"])
    return {"name": CHECK_NAMES["b"], "verdict": "FAIL" if failed else "PASS", "containers": containers,
            "fixtures_with_query_positions_past_trained_range": past,
            "note": ("plumbing only: no correct/incorrect field is written, but right/wrong is recomputable from "
                     "answer_sha256 and check_digest with the public fixture file; never use this for sealed items")}


# ------------------------------------------------------------------------------------------------ check a
def check_a(ctx):
    torch, LL, scope = ctx.torch, ctx.LL, ctx.scope
    models, failed = [], False
    for seed in SEEDS:
        for phase in ("initial", "final"):
            model, checkpoint = ctx.container(seed, phase, switch=False)
            per_record, off_route = {}, []
            for rid in ctx.ids:
                ctx.wall()
                result = LL.predict_packet(torch, model, ctx.packets[rid], ctx.device, tagger=ctx.tagger)
                if result["route"] != scope.ORIGINAL:
                    off_route.append(rid)
                per_record[rid] = LL.logit_bits_digest(torch, result["rows"])
            overall = _overall_digest(ctx.ids, per_record)
            reference = T4_REFERENCE_OVERALL_DIGEST[(seed, phase)]
            summary = {**checkpoint, "switch": False, "records": len(per_record),
                       "non_original_route_count": len(off_route), "non_original_route_ids": off_route[:20],
                       "overall_digest": overall, "t4_reference_overall_digest": reference,
                       "equal_to_t4_reference": overall == reference}
            failed = (failed or overall != reference or bool(off_route)
                      or len(per_record) != EXPECTED_COURSE_PACKETS)
            # The per-record digests go to the rows file only, so a mismatch can be located against the reference.
            ctx.emit("a", {"row": "model", **summary, "per_record": per_record})
            models.append(summary)
            del model
            torch.cuda.empty_cache()
    return {"name": CHECK_NAMES["a"], "verdict": "FAIL" if failed or len(models) != 6 else "PASS",
            "models": models, "compared_field": T4_REFERENCE["compared_field"],
            "reference": {key: T4_REFERENCE[key] for key in ("commit", "branch", "folder", "tool_sha256_lf")}}


CHECKS = {"d": check_d, "c": check_c, "b": check_b, "a": check_a}


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    parser.add_argument("--checks", default=",".join(CHECK_ORDER))
    parser.add_argument("--list-inputs", action="store_true")
    args = parser.parse_args(argv)
    if args.list_inputs:
        print(json.dumps(list_inputs(), indent=1, sort_keys=True))
        return 0
    chosen = [name.strip() for name in args.checks.split(",") if name.strip()]
    if not args.out or not chosen or any(name not in CHECKS for name in chosen) or len(set(chosen)) != len(chosen):
        print("BAD_ARGUMENTS: --out is required; --checks is a subset of d,c,b,a")
        return 1
    requested = [name for name in CHECK_ORDER if name in chosen]  # always d, c, b, a, whatever order was typed
    out = pathlib.Path(args.out)
    rows_path = pathlib.Path(str(out) + ".rows.jsonl")
    if any(path.exists() for path in (out, pathlib.Path(str(out) + ".partial"), rows_path)):
        print("SETUP_REFUSED OUTPUT_EXISTS: outputs are create-only")
        return 4
    started = time.monotonic()
    rows = RowWriter(rows_path)
    payload = {"schema": SCHEMA, "complete": False, "requested": requested, "boundary": BOUNDARY,
               "wall_seconds_limit": WALL_SECONDS, "rows_file": rows_path.name, "checks": {},
               "python": sys.version.split()[0], "platform": platform.platform()}
    rows.emit("run", {"row": "header", "schema": SCHEMA, "requested": requested,
                      "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})

    def finish(verdict, code, **extra):
        payload.update(extra)
        payload.update({"verdict": verdict, "wall_seconds": time.monotonic() - started,
                        "rows_by_check": dict(rows.count)})
        rows.emit("run", {"row": "verdict", "verdict": verdict, "exit_code": code})
        rows.close()
        payload["rows_file_sha256"] = hashlib.sha256(rows_path.read_bytes()).hexdigest()
        _publish(out, payload)
        print(verdict, extra.get("reason", ""))
        return code

    try:
        payload["inputs"] = verify_inputs(requested)  # BEFORE torch: missing or changed files cost no GPU time
    except SetupRefused as error:
        return finish("SETUP_REFUSED", 4, reason=str(error))
    try:
        import torch
    except ImportError:
        return finish("GPU_REQUIRED", 2, reason="GPU_REQUIRED: torch is not importable")
    if not torch.cuda.is_available():
        return finish("GPU_REQUIRED", 2, reason="GPU_REQUIRED: CUDA is not available; no CPU fallback")
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
    device = torch.device("cuda", 0)
    payload.update({"torch": torch.__version__, "device_name": torch.cuda.get_device_name(device)})
    if "a" in requested and (payload["torch"] != T4_REFERENCE["torch"]
                             or T4_REFERENCE["gpu_name_contains"] not in payload["device_name"]):
        return finish("SETUP_REFUSED", 4, reason="T4_REFERENCE_ENVIRONMENT_DIFFERS: check a needs torch %s on a %s"
                      % (T4_REFERENCE["torch"], T4_REFERENCE["gpu_name_contains"]))
    try:
        ctx = Context(torch, device, started, rows, requested)
    except Exception as error:  # noqa: BLE001 - any setup failure is a refusal, written before exiting
        return finish("SETUP_REFUSED", 4, reason="%s: %s" % (type(error).__name__, str(error)[:400]),
                      traceback=traceback.format_exc()[-4000:])
    payload.update({"course_digest": ctx.course_digest, "source_lf_sha256": ctx.source_pins,
                    "fixture_set_digest": ctx.document["fixture_set_digest"],
                    "larger_fixtures": len(ctx.larger_ids), "refusal_fixtures": len(ctx.refused_ids)})
    try:
        report = preflight(ctx, requested)
    except WallLimit:
        return finish("WALL_LIMIT_REACHED", 3, reason="during the preflight")
    except Exception as error:  # noqa: BLE001 - a preflight that cannot time the work refuses the run
        return finish("SETUP_REFUSED", 4,
                      reason="PREFLIGHT_CRASHED: %s: %s" % (type(error).__name__, str(error)[:400]),
                      traceback=traceback.format_exc()[-4000:])
    rows.emit("run", report)
    payload["preflight"] = {key: value for key, value in report.items() if key != "seconds"}
    if not report["fits"]:
        return finish("PREFLIGHT_OVER_WALL_LIMIT", 5, reason="projected %.0f s > %d s"
                      % (report["projected_total_seconds"], WALL_SECONDS))
    for name in requested:
        try:
            payload["checks"][name] = CHECKS[name](ctx)
        except WallLimit:
            payload["checks"][name] = {"name": CHECK_NAMES[name], "verdict": "NOT_COMPLETE",
                                       "reason": "WALL_LIMIT_REACHED", "rows_written": rows.count[name]}
            for later in requested[requested.index(name) + 1:]:
                payload["checks"][later] = {"name": CHECK_NAMES[later], "verdict": "NOT_RUN"}
            return finish("WALL_LIMIT_REACHED", 3, reason="cut during check " + name)
        except SetupRefused as error:
            return finish("SETUP_REFUSED", 4, reason=str(error))
        except Exception as error:  # noqa: BLE001 - a crashed check is a failed check
            payload["checks"][name] = {"name": CHECK_NAMES[name], "verdict": "FAIL", "crash": _error(error),
                                       "traceback": traceback.format_exc()[-4000:]}
        rows.emit(name, {"row": "check_verdict", "verdict": payload["checks"][name]["verdict"]})
        print(name, CHECK_NAMES[name], payload["checks"][name]["verdict"], flush=True)
    verdicts = [payload["checks"][name]["verdict"] for name in requested]
    if sorted(requested) == sorted(CHECKS) and all(value == "PASS" for value in verdicts):
        verdict = "INTEGRATION_CHECKS_PASS"
    elif any(value != "PASS" for value in verdicts):
        verdict = "INTEGRATION_CHECKS_FAIL"
    else:
        verdict = "INTEGRATION_CHECKS_INCOMPLETE"
    payload["complete"] = True
    return finish(verdict, 0 if verdict == "INTEGRATION_CHECKS_PASS" else 1)


if __name__ == "__main__":
    sys.exit(main())
