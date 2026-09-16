"""Guarded pure checks for public source and answer syntax; no course/learner."""
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
               "cas_meta2.graph_teaching.final_panel", "cas_meta2.complementary_teaching.course"}
attempts, blocked_reads, blocked_execution = [], [], []


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED or fullname in OLD_MODULES:
            attempts.append(fullname)
            raise AssertionError("TYPED_CHECK_FORBIDDEN_IMPORT:" + fullname)


def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "os.system", "os.posix_spawn")):
        blocked_execution.append(event)
        raise AssertionError("TYPED_CHECK_FORBIDDEN_EXECUTION:" + event)


def write(name, value):
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with (OUT / name).open("xb") as stream:
        stream.write(raw)
    return {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": sha256(raw).hexdigest()}


original_open = io.open
def read_guard(path, *args, **kwargs):
    if not isinstance(path, int):
        value = Path(path)
        if value.name in {"data_manifest.json", "TASK_BINDINGS.json"} or value.suffix in {".pt", ".whl", ".zip"}:
            blocked_reads.append(str(path))
            raise AssertionError("TYPED_CHECK_FINAL_OR_NUMERIC_ARTIFACT:" + str(path))
    return original_open(path, *args, **kwargs)


assert not DENIED.intersection(sys.modules)
assert not OLD_MODULES.intersection(sys.modules)
sys.meta_path.insert(0, Deny())
io.open = read_guard
sys.addaudithook(audit)
sys.path[:0] = [str(ROOT), str(RESEARCH)]
os.chdir(RESEARCH)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
tests = ["tests/test_typed_teaching_source.py", "tests/test_typed_teaching_answers.py"]
paths = sorted(set((RESEARCH / "cas_meta2/typed_teaching").glob("*.py"))
    | {RESEARCH / name for name in tests}
    | {RESEARCH / "cas_meta2/graph_teaching/face_corpus.py",
       RESEARCH / "cas_meta2/graph_teaching/face_tasks.py",
       RESEARCH / "cas_meta2/graph_teaching/face_roles.py",
       RESEARCH / "cas_meta2/graph_teaching/reference.py",
       RESEARCH / "cas_meta2/complementary_teaching/course.py", Path(__file__).resolve()})
before = [pin(path) for path in paths]
artifacts = [write("inputs_before.json", before)]
import pytest
code = int(pytest.main(["-q", "-p", "no:cacheprovider", *tests,
                       "--basetemp=" + str(OUT / "tmp"), "--junitxml=" + str(OUT / "tests.xml")]))
counts = {key: sum(int(row.get(key, "0")) for row in ET.parse(OUT / "tests.xml").getroot().iter("testsuite"))
          for key in ("tests", "failures", "errors", "skipped")}
summary = {}
if code == 0:
    from cas_meta2.typed_teaching import source, answers
    profile = source.source_profile()
    families = source.training_families(expected_source_profile_digest=profile["profile_digest"])
    bank = source.freeze_bank(families)
    envelope = source.compile_source(families[0], bank=bank)
    public = source.public_source(envelope)
    focus = next(w for w in public["worlds"] if w["world_id"] == public["focus_world_id"])
    nodes = [n["ref"] for n in focus["nodes"]]
    examples = []
    for kind in answers.RULES:
        args, rule = {}, None
        if kind == "role_set":
            args = {"focal_excerpt": "Inspect this excerpt only: Bicycle contains Wheel."}
        if kind == "parts":
            args = {"whole": focus["declared_whole"]}
        if kind == "reach":
            args = {"whole": nodes[0], "part": nodes[1]}
            rule = answers.RULES[kind][0]
        if kind == "correspondence":
            args = {"target_world_id": public["bank"]["world_ids"][0]}
        query = answers.compile_query(public, kind=kind, rule=rule, arguments=args)
        examples.append({"query": query, "answer_space": answers.answer_space(public, query)})
    assert len(families) == len(bank["worlds"]) == 64
    assert all(f["split"] == "training" for f in families)
    assert all(w["branch_order"]["process_order"] is None for w in bank["worlds"])
    artifacts += [write("training_bank.json", bank), write("first_source_envelope.json", envelope),
                  write("query_syntax_examples.json", {"notice": "Public grammar examples only, no semantic target or full-course reconstruction.",
                                                       "examples": examples})]
    summary = {"training_families": len(families), "training_domains": dict(Counter(f["domain"] for f in families)),
        "nodes_per_world": dict(Counter(len(w["nodes"]) for w in bank["worlds"])),
        "bank_worlds": len(bank["worlds"]), "bank_digest": bank["bank"]["bank_digest"],
        "source_profile": profile, "first_public_bytes": len(source.canonical(public).encode()),
        "answer_kinds_checked": list(answers.RULES), "roles_offered": list(answers.ROLE_IDS),
        "declared_temporal_process_worlds": 0,
        "full_course_rebuilt": False, "semantic_teacher_checker_implemented": False,
        "neural_decoder_implemented": False, "study_admitted": False}
after = [pin(path) for path in paths]
artifacts += [write("inputs_after.json", after), pin(OUT / "tests.xml")]
loaded = sorted(DENIED.intersection(sys.modules) | OLD_MODULES.intersection(sys.modules))
accepted = (code == 0 and before == after and not attempts and not blocked_reads
            and not blocked_execution and not loaded)
receipt = {"schema": "cncm.typed-teaching-pure-check/0.1",
    "status": "PURE_SOURCE_AND_SYNTAX_PASS" if accepted else "FAILED",
    "parent_commit": HEAD, "tests": counts, "test_modules": tests,
    "input_pins": len(before), "input_pins_unchanged": before == after,
    "forbidden_import_attempts": attempts, "forbidden_modules_loaded": loaded,
    "blocked_artifact_reads": blocked_reads, "blocked_execution_attempts": blocked_execution,
    "artifacts": artifacts, "summary": summary,
    "neural_calls": 0, "optimizer_updates": 0, "provider_calls": 0,
    "boundary": "Pure training-only source and answer grammar. No final targets constructed, no full-course typed reconstruction, semantic checker, numerical decoder, matched run or learning gain."}
write("receipt.json", receipt)
print(json.dumps({"status": receipt["status"], "tests": counts, "receipt": str(OUT / "receipt.json")}))
raise SystemExit(0 if accepted else 1)

