"""Guarded pure reproduction of the full matched-study preparation stage."""
from dataclasses import asdict
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
DENIED = {"torch", "numpy", "tensorflow", "jax", "jaxlib", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "cas_cjt", "casformer", "transformers"}
attempts, blocked_reads = [], []


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            attempts.append(fullname)
            raise AssertionError("MATCH_PREPARATION_FORBIDDEN_IMPORT:" + fullname)


def write(name, value):
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with (OUT / name).open("xb") as stream:
        stream.write(raw)
    assert (OUT / name).read_bytes() == raw
    return {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def read_guard(path, *args, **kwargs):
    if not isinstance(path, int):
        value = Path(path)
        if value.name in {"data_manifest.json", "TASK_BINDINGS.json"} or value.suffix in {".pt", ".whl", ".zip"}:
            blocked_reads.append(str(path))
            raise AssertionError("MATCH_PREPARATION_FINAL_OR_NUMERIC_ARTIFACT:" + str(path))
    return original_open(path, *args, **kwargs)


assert not DENIED.intersection(sys.modules)
sys.meta_path.insert(0, Deny())
original_open = io.open
io.open = read_guard
sys.path[:0] = [str(ROOT), str(RESEARCH)]
os.chdir(ROOT)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
tests = ["tests/test_rpa_learning_match.py", "tests/test_rpa_course_adapter.py",
         "research/CAS_META_2_COMPOSITION/tests/test_complementary_development_data.py",
         "research/CAS_META_2_COMPOSITION/tests/test_scoped_ordered_encoder.py"]
paths = sorted(set((ROOT / "cncm").glob("*.py")) | set((RESEARCH / "cas_meta2").rglob("*.py"))
               | {ROOT / name for name in tests} | {Path(__file__).resolve(),
                 RESEARCH / "tools/check_structural_supply_20260916.py",
                 RESEARCH / "records/complementary_teaching_001/preparation_20260916/historical_exclusions.json",
                 RESEARCH / "records/learning_panel_001/supply.json"})
before = [pin(path) for path in paths]
artifacts = [write("inputs_before.json", before)]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
import pytest
code = int(pytest.main(["-q", "-p", "no:cacheprovider", *tests,
                       "--basetemp=" + str(OUT / "tmp"), "--junitxml=" + str(OUT / "tests.xml")]))
counts = {key: sum(int(row.get(key, "0")) for row in ET.parse(OUT / "tests.xml").getroot().iter("testsuite"))
          for key in ("tests", "failures", "errors", "skipped")}
summary = {}
if code == 0:
    from cncm import rpa_learning_match as match, rpa_course_adapter as admission
    from cas_meta2.complementary_teaching import development_data
    from cas_meta2.graph_teaching import ordered_encoder, scoped_ordered_encoder as scoped
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from tools.check_structural_supply_20260916 import shape_key
    comparisons = [match.compile_training_comparison(seed) for seed in (101, 202, 303)]
    artifacts += [write("matched_schedules.json", comparisons)]
    summary["source_schedule_seeds"] = [row["source_seed"] for row in comparisons]
    summary["comparisons"] = [{"seed": row["source_seed"],
        "counts": row["schedules"][match.ALT]["counts"],
        "contrasts": row["comparisons_to_component_whole"]} for row in comparisons]
    exclusions = json.loads((RESEARCH / "records/complementary_teaching_001/preparation_20260916/historical_exclusions.json").read_bytes())
    development = development_data.build_development(exclusions, topology_key=shape_key)
    artifacts += [write("development_only.json", development)]
    summary["development"] = development["counts"]
    profile = admission.source_profile()
    prepared = admission.prepare_course(seed=101, condition=match.ALT,
        expected_source_profile_digest=profile["profile_digest"])
    tokenizer = admission.fit_training_tokenizer(prepared)
    # Deliberate supplied fixture identities, NOT observed projection/checkpoint bytes.
    encoder_profile = scoped.profile_identity(tokenizer, d_model=64, seed=20260916,
                                              projection_sha256="b" * 64)
    context = {"model_id": "pure-course-binding-fixture", "checkpoint_sha256": "a" * 64}
    bound = admission.bind_course(prepared, tokenizer=tokenizer, ordered_profile=encoder_profile,
                                  model_context=context)
    admission.check_course_targets(bound, prepared=prepared, tokenizer=tokenizer,
                                   ordered_profile=encoder_profile, model_context=context)
    for packet in bound["registry"]:
        admission.validate_prediction_packet(packet, tokenizer=tokenizer,
            ordered_profile=encoder_profile, model_context=context)
    artifacts += [write("course_prepared.json", prepared), write("course_bound_fixture.json", bound),
                  write("training_only_tokenizer.json", tokenizer.to_dict())]
    summary["course_binding"] = {"presentations": len(prepared["presentations"]),
        "batches": len(prepared["batches"]), "unique_packets": len(bound["registry"]),
        "binding": bound["binding"], "readiness": bound["readiness"],
        "fixture_identity_notice": "Projection/checkpoint hashes are explicit placeholders; no numerical objects exist."}
    nodes = "node A kind=idea\nnode B kind=idea\nnode C kind=idea\n"
    graph_a, graph_b = nodes + "rel A --contains--> B\n", nodes + "rel A --contains--> C\n"
    def public(first, second):
        return {"problem": "Support context:\n" + first + "Current task context:\n" + second
                + "LIST_PARTS(A): what does the current task directly contain?\nChoose one supplied option.\n",
                "observations": [{"slot": i, "tag": text, "values": [0.0] * 8}
                                 for i, text in enumerate(["['B']", "['C']", "[]"])]}
    left, right = public(graph_a, graph_b), public(graph_b, graph_a)
    synthetic = LosslessPublicTokenizer.fit_train([left, right], max_length=1024)
    old_a, old_b = ordered_encoder.compile_frames(left, synthetic), ordered_encoder.compile_frames(right, synthetic)
    new_a, new_b = scoped.compile_frames(left, synthetic), scoped.compile_frames(right, synthetic)
    assert left != right and old_a == old_b and new_a != new_b
    probe = {"left": left, "right": right, "synthetic_tokenizer": synthetic.to_dict(),
        "legacy_frames_left": [asdict(row) for row in old_a], "legacy_frames_right": [asdict(row) for row in old_b],
        "scoped_frames_left": [asdict(row) for row in new_a], "scoped_frames_right": [asdict(row) for row in new_b],
        "legacy_collision": True, "scoped_frames_distinct": True, "numeric_calls": 0,
        "boundary": "Synthetic framing fixture; distinct maps do not prove distinct outputs for every finite projection."}
    artifacts += [write("scope_binding_probe.json", probe)]
    summary["scope_binding"] = {"legacy_frames_equal": True, "scoped_frames_equal": False,
                                "legacy_frame_count": len(old_a), "scoped_frame_count": len(new_a)}
after = [pin(path) for path in paths]
artifacts += [write("inputs_after.json", after), pin(OUT / "tests.xml")]
loaded = sorted(DENIED.intersection(sys.modules))
accepted = code == 0 and before == after and not attempts and not blocked_reads and not loaded
receipt = {"schema_version": "cncm.matched-learning-preparation-check/0.1",
    "status": "PURE_PREPARATION_CHECKS_PASS" if accepted else "FAILED",
    "parent_commit": head, "test_modules": tests, "tests": counts,
    "current_input_pins": len(after), "input_pins_unchanged": before == after,
    "forbidden_import_attempts": attempts, "forbidden_modules_loaded": loaded, "blocked_reads": blocked_reads,
    "artifacts": artifacts, "summary": summary, "neural_calls": 0, "optimizer_updates": 0,
    "provider_calls": 0, "final_study_frozen": False,
    "boundary": "Pure full-course preparation, scoped encoder maps and development-only construction. "
                "No numerical encoder, learner, fresh paired checkpoint, GPU acceptance or learning gain."}
write("receipt.json", receipt)
print(json.dumps({"status": receipt["status"], "tests": counts, "receipt": str(OUT / "receipt.json")}))
raise SystemExit(0 if accepted else 1)
