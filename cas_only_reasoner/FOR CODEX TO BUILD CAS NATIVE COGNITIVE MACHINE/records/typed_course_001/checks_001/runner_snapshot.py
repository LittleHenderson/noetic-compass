"""Guarded full-course reconstruction and private checker evidence."""
from collections import Counter
from hashlib import sha256
import importlib.abc
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research/CAS_META_2_COMPOSITION"
OUT = Path(sys.argv[1]).resolve()
OUT.relative_to(Path(__file__).resolve().parent)
OUT.mkdir(parents=True, exist_ok=False)
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
DENIED = {"torch", "numpy", "tensorflow", "jax", "jaxlib", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "cas_cjt", "casformer", "transformers"}
OLD_MODULES = {"cas_meta2.graph_teaching.face_corpus", "cas_meta2.graph_teaching.face_tasks",
               "cas_meta2.graph_teaching.face_schedule", "cas_meta2.graph_teaching.face_experiment",
               "cas_meta2.graph_teaching.final_panel", "cas_meta2.complementary_teaching.course"}
attempts, blocked_reads, blocked_execution = [], [], []


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED or fullname in OLD_MODULES:
            attempts.append(fullname)
            raise AssertionError("TYPED_COURSE_FORBIDDEN_IMPORT:" + fullname)


def audit(event, args):
    if (event.startswith("socket.") and event != "socket.gethostname") or event.startswith(
            ("subprocess.", "os.system", "os.posix_spawn")):
        blocked_execution.append(event)
        raise AssertionError("TYPED_COURSE_FORBIDDEN_EXECUTION:" + event)


def write(name, value):
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with (OUT / name).open("xb") as stream:
        stream.write(raw)
    return {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


original_open = io.open
def read_guard(path, *args, **kwargs):
    if not isinstance(path, int):
        value = Path(path)
        if value.name in {"data_manifest.json", "TASK_BINDINGS.json"} or value.suffix in {".pt", ".whl", ".zip"}:
            blocked_reads.append(str(path))
            raise AssertionError("TYPED_COURSE_FINAL_OR_NUMERIC_ARTIFACT:" + str(path))
    return original_open(path, *args, **kwargs)


assert not DENIED.intersection(sys.modules) and not OLD_MODULES.intersection(sys.modules)
sys.meta_path.insert(0, Deny())
io.open = read_guard
sys.addaudithook(audit)
sys.path[:0] = [str(ROOT), str(RESEARCH)]
os.chdir(RESEARCH)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
tests = ["tests/test_typed_teaching_" + stem + ".py"
         for stem in ("source", "answers", "focal", "checker", "course_plan", "course")]
from cas_meta2.typed_teaching import course, course_plan
paths = sorted(set((RESEARCH / "cas_meta2/typed_teaching").glob("*.py"))
    | {RESEARCH / name for name in tests}
    | {RESEARCH / row["path"] for row in course.profile()["files"]}
    | {ROOT / row["path"] for row in course.profile()["plan_source_profile"]["files"]}
    | {ROOT / "records/matched_learning_preparation_001/checks_001/course_prepared.json",
       ROOT / "records/matched_learning_preparation_001/checks_001/matched_schedules.json",
       Path(__file__).resolve()})
before = [pin(path) for path in paths]
artifacts = [write("inputs_before.json", before)]
import pytest
runner_error = None
try:
    code = int(pytest.main(["-q", "-p", "no:cacheprovider", *tests,
                           "--basetemp=" + str(OUT / "tmp"), "--junitxml=" + str(OUT / "tests.xml")]))
except Exception as exc:
    code, runner_error = 1, {"type": type(exc).__name__, "message": str(exc)}
    artifacts.append(write("runner_error.json", runner_error))
try:
    counts = {key: sum(int(row.get(key, "0")) for row in ET.parse(OUT / "tests.xml").getroot().iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
except (ET.ParseError, FileNotFoundError):
    counts = {key: None for key in ("tests", "failures", "errors", "skipped")}
summary = {}
if code == 0:
    try:
        prepared = course.prepare_course(101, course_plan.ALT)
        artifacts.append(write("prepared_course.json", prepared))
        compiled = course.compile_course(101, course_plan.ALT)
        seal = course.seal_course(compiled, OUT / "public_course.json")
        artifacts += [pin(OUT / "public_course.json"), write("public_seal.json", seal)]
        # The exact public course exists and has passed fsync/readback before targets.
        private = course.derive_targets_from_seal(OUT / "public_course.json", expected_sha256=seal["sha256"])
        artifacts.append(write("private_targets.json", private))
        comparisons = []
        for seed in course_plan.SEEDS:
            arms = {condition: course.compile_course(seed, condition) for condition in course_plan.CONDITIONS}
            alt, mixed, graph = [arms[c] for c in course_plan.CONDITIONS]
            same_registry = alt["registry"] == mixed["registry"] == graph["registry"]
            same_items = Counter(p["record_id"] for p in alt["presentations"]) == Counter(
                p["record_id"] for p in mixed["presentations"])
            schedule = lambda c: [(b["depth"], b["record_ids"]) for b in c["batches"]]
            assert same_registry and same_items and schedule(alt) != schedule(mixed)
            assert schedule(alt) == schedule(graph)
            comparisons.append({"source_seed": seed, "counts": alt["counts"],
                "course_digests": {key: value["course_digest"] for key, value in arms.items()},
                "same_public_registry_including_support_answers": same_registry,
                "same_presentation_multiset": same_items, "alt_mixed_order_differs": True,
                "ordinary_graph_equals_alt": True, "actual_compute_measured": False})
        artifacts.append(write("matched_comparisons.json", comparisons))
        targets, records = private["targets"], {r["record_id"]: r for r in compiled["registry"]}
        roles = Counter()
        alternatives = Counter()
        for p in compiled["presentations"]:
            target = targets[p["record_id"]]
            alternatives[len(target["admissible_answers"])] += 1
            if target["kind"] == "role_set":
                roles[target["admissible_answers"][0]["value"]["status"]] += 1
        sample = {}
        for r in compiled["registry"]:
            if r["query"]["kind"] not in sample:
                sample[r["query"]["kind"]] = course.model_packet(compiled, r["record_id"])
        artifacts.append(write("public_packet_examples.json", sample))
        summary = {"counts": compiled["counts"], "private_target_registry": len(targets),
            "role_presentations_by_status": dict(roles),
            "presentations_by_admissible_answer_count": dict(alternatives),
            "source_seeds_compiled": list(course_plan.SEEDS), "conditions_compiled": list(course_plan.CONDITIONS),
            "public_course_sha256": seal["sha256"], "public_course_bytes": seal["bytes"],
            "full_course_rebuilt": True, "semantic_checker_implemented": True,
            "neural_decoder_implemented": False, "final_targets_constructed": False,
            "study_admitted": False, "source_profile": compiled["source_profile"]}
    except Exception as exc:
        code, runner_error = 1, {"type": type(exc).__name__, "message": str(exc)}
        artifacts.append(write("evidence_build_error.json", runner_error))
after = [pin(path) for path in paths]
artifacts.append(write("inputs_after.json", after))
if (OUT / "tests.xml").exists():
    artifacts.append(pin(OUT / "tests.xml"))
loaded = sorted(DENIED.intersection(sys.modules) | OLD_MODULES.intersection(sys.modules))
accepted = code == 0 and before == after and not attempts and not blocked_reads and not blocked_execution and not loaded
receipt = {"schema": "cncm.typed-full-course-pure-check/0.1",
    "status": "PURE_FULL_COURSE_AND_CHECKER_PASS" if accepted else "FAILED",
    "parent_commit": HEAD, "tests": counts, "test_modules": tests, "runner_error": runner_error,
    "input_pins": len(before), "input_pins_unchanged": before == after,
    "forbidden_import_attempts": attempts, "forbidden_modules_loaded": loaded,
    "blocked_artifact_reads": blocked_reads, "blocked_execution_attempts": blocked_execution,
    "artifacts": artifacts, "summary": summary, "neural_calls": 0, "optimizer_updates": 0, "provider_calls": 0,
    "boundary": "Pure full training-course reconstruction and private semantic targets after durable public seal. No neural decoder, numeric input/compute acceptance, model trial, protected final construction, matched learning result or full-machine completion."}
write("receipt.json", receipt)
print(json.dumps({"status": receipt["status"], "tests": counts, "summary": summary,
                  "receipt": str(OUT / "receipt.json")}))
raise SystemExit(0 if accepted else 1)
