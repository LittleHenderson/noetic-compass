"""Guarded public-only input/slot construction and complete course sizing."""
from collections import Counter
from hashlib import sha256
import importlib.abc
import io
import json
import math
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
OLD = {"cas_meta2.typed_teaching.checker", "cas_meta2.graph_teaching.face_corpus",
       "cas_meta2.graph_teaching.face_tasks", "cas_meta2.graph_teaching.face_schedule",
       "cas_meta2.graph_teaching.final_panel", "cas_meta2.complementary_teaching.course"}
attempts, blocked_reads, blocked_execution = [], [], []
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED or fullname in OLD:
            attempts.append(fullname)
            raise AssertionError("TYPED_INTERFACE_FORBIDDEN_IMPORT:" + fullname)
def audit(event, args):
    if (event.startswith("socket.") and event != "socket.gethostname") or event.startswith(
            ("subprocess.", "os.system", "os.posix_spawn")):
        blocked_execution.append(event)
        raise AssertionError("TYPED_INTERFACE_FORBIDDEN_EXECUTION:" + event)
original_open = io.open
def read_guard(path, *args, **kwargs):
    if not isinstance(path, int):
        value = Path(path)
        if value.name in {"private_targets.json", "data_manifest.json", "TASK_BINDINGS.json"} or value.suffix in {".pt", ".whl", ".zip"}:
            blocked_reads.append(str(path))
            raise AssertionError("TYPED_INTERFACE_PRIVATE_OR_NUMERIC_ARTIFACT:" + str(path))
    return original_open(path, *args, **kwargs)
def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)+"\n").encode()
def write(name, value):
    with (OUT / name).open("xb") as stream:
        stream.write(raw(value))
    return pin(OUT / name)
def write_lines(name, rows):
    with (OUT / name).open("xb") as stream:
        for row in rows:
            stream.write(raw(row))
    return pin(OUT / name)
def pin(path):
    value = path.read_bytes()
    return {"path":path.relative_to(ROOT).as_posix(), "bytes":len(value), "sha256":sha256(value).hexdigest()}

assert not DENIED.intersection(sys.modules) and not OLD.intersection(sys.modules)
sys.meta_path.insert(0, Deny())
io.open = read_guard
sys.addaudithook(audit)
sys.path[:0] = [str(ROOT), str(RESEARCH)]
os.chdir(RESEARCH)
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
from cas_meta2.typed_teaching import course, course_plan, source, input_frames, slots, tokenization
retained = ROOT / "records/typed_course_001/checks_002/public_course.json"
assert pin(retained)["sha256"] == "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987"
baseline = json.loads(retained.read_bytes())
assert baseline["source_profile"] == course.profile()
prior_receipt = ROOT / "records/typed_course_001/checks_002/receipt.json"
assert pin(prior_receipt)["sha256"] == "7e83de9926e09f0c27bcda1c5ada3e67668fe363fd5a318090cb01473d0d523d"
tests = ["tests/test_typed_teaching_" + name + ".py"
         for name in ("source", "answers", "slots", "input_frames", "tokenization")]
paths = sorted(set((RESEARCH / "cas_meta2/typed_teaching").glob("*.py"))
    | {RESEARCH / name for name in tests}
    | {RESEARCH / row["path"] for row in course.profile()["files"]}
    | {ROOT / row["path"] for row in course.profile()["plan_source_profile"]["files"]}
    | {retained, prior_receipt, Path(__file__).resolve()})
before = [pin(path) for path in paths]
artifacts = [write("inputs_before.json", before)]
import pytest
error = None
try:
    code = int(pytest.main(["-q", "--tb=short", "-p", "no:cacheprovider", *tests,
        "--basetemp="+str(OUT/"tmp"), "--junitxml="+str(OUT/"tests.xml")]))
except Exception as exc:
    code, error = 1, {"type":type(exc).__name__, "message":str(exc)}
counts = {key:sum(int(r.get(key,"0")) for r in ET.parse(OUT/"tests.xml").getroot().iter("testsuite"))
          for key in ("tests","failures","errors","skipped")} if (OUT/"tests.xml").exists() else {}
summary = {}
if code == 0:
    try:
        packets, frames, plans, syntax_examples = {}, {}, {}, []
        for row in baseline["registry"]:
            key = row["record_id"]
            packet = course.model_packet(baseline, key)
            frame, plan = input_frames.compile_packet(packet), slots.compile_slots(packet)
            assert input_frames.restore_packet(frame) == packet
            assert plan["packet_digest"] == source.digest(packet)
            frame_aliases = {"worlds":[{"alias":w["alias"], "world_id":w["world_id"],
                "nodes":[{"alias":alias,"ref":w["world_id"]+suffix} for alias,suffix in w["nodes"]]}
                for w in frame["aliases"]]}
            assert plan["aliases"] == frame_aliases
            packets[key], frames[key], plans[key] = packet, frame, plan
            scores = {slot["slot_id"]:{symbol:0.0 for symbol in slot["symbols"]} for slot in plan["slots"]}
            decision = slots.score_decisions(packet, scores)
            answer = slots.assemble_answer(packet, decision)
            syntax_examples.append({"record_id":key, "plan_digest":plan["plan_digest"], "answer":answer,
                                    "source":"SYNTHETIC_ZERO_LOGITS_NOT_MODEL_PREDICTION", "semantic_scoring_performed":False})
        ordered = sorted(frames)
        artifacts += [write_lines("public_frames.jsonl", ({"record_id":k, "frame":frames[k]} for k in ordered)),
                      write_lines("public_slots.jsonl", ({"record_id":k, "plan":plans[k]} for k in ordered)),
                      write_lines("zero_logit_syntax.jsonl", syntax_examples)]
        # Every fitted text is a projection of the one hash-pinned training registry.
        estimate = max(tokenization.training_token_count(frames[k]) for k in ordered)
        cap = max(1024, 1 << (estimate-1).bit_length())
        assert cap <= tokenization.HARD_MAX_TOKENS
        tokenizer = tokenization.fit_train([frames[k] for k in ordered], max_tokens=cap)
        artifacts.append(write("training_tokenizer.json", tokenizer.to_dict()))
        assert tokenization.FrameTokenizer.from_dict(tokenizer.to_dict()).digest == tokenizer.digest
        measurements = []
        for key in ordered:
            sequence = tokenizer.encode_frame(frames[key])
            assert tokenizer.validate_sequence(frames[key], sequence)
            measurements.append({"record_id":key,"kind":packets[key]["record"]["query"]["kind"],
                "packet_bytes":len(source.canonical(packets[key]).encode()),
                "frame_text_bytes":len(frames[key]["text"].encode("utf-8")),
                "frame_digest":source.digest(frames[key]), "tokens_including_markers":len(sequence["ids"]),
                "sequence_digest":sequence["sequence_digest"],"token_ids_digest":source.digest(sequence["ids"]),
                "slots":len(plans[key]["slots"]),
                "correspondence_candidates":len(plans[key]["correspondence_candidates"]),
                "forced_candidates":plans[key]["forced_candidate_count"]})
        artifacts.append(write("measurements.json", measurements))
        measured = {r["record_id"]:r for r in measurements}
        # Rebind the held registry to newly constructed target-free source schedules.
        # Complete intent/lineage identity, not guessed task kind, determines joins.
        def signature(occ):
            return source.digest({k:v for k,v in occ.items() if k != "occurrence_id"})
        base_join = {p["occurrence_id"]:p["record_id"] for p in baseline["presentations"]}
        lookup = {signature(o):base_join[o["occurrence_id"]] for o in baseline["plan"]["occurrences"]}
        assert len(lookup) == 1152
        schedules, memberships = [], {}
        for seed in course_plan.SEEDS:
            for condition in course_plan.CONDITIONS:
                plan = course_plan.compile_plan(seed, condition)
                assert Counter(signature(o) for o in plan["occurrences"]) == Counter(lookup.keys())
                joins = {o["occurrence_id"]:lookup[signature(o)] for o in plan["occurrences"]}
                batches = [{**b,"record_ids":[joins[o] for o in b["occurrence_ids"]]} for b in plan["batches"]]
                records = [k for b in batches for k in b["record_ids"]]
                assert len(records) == 1152 and len(batches) == 160
                assert Counter(records) == Counter(base_join.values())
                values = [measured[k] for k in records]
                row = {"source_seed":seed,"condition":condition,"source_plan_digest":plan["plan_digest"],
                       "binding":"EXACT_FROZEN_INTENT_LINEAGE_TO_ACCEPTED_TRAINING_REGISTRY",
                       "presentations":1152,"groups":160,"unique_packets":len(set(records)),
                       "presentation_slots":sum(r["slots"] for r in values),
                       "planned_slot_core_passes":sum(measured[k]["slots"]*b["depth"] for b in batches for k in b["record_ids"]),
                       "tokens_per_presentation_sum":sum(r["tokens_including_markers"] for r in values),
                       "presentation_multiset_digest":source.digest(sorted(Counter(records).items())),
                       "batches":batches,"model_calls":0,"actual_compute_measured":False}
                schedules.append(row)
                memberships[(seed, condition)] = [(b["depth"],b["record_ids"]) for b in batches]
            assert memberships[(seed,course_plan.ALT)] != memberships[(seed,course_plan.MIXED)]
            assert memberships[(seed,course_plan.ALT)] == memberships[(seed,course_plan.DAG)]
        artifacts.append(write("schedule_bindings.json", schedules))
        def stats(rows):
            sizes = sorted(row["tokens_including_markers"] for row in rows)
            return {"packets":len(rows), "min":sizes[0],"p50":sizes[math.ceil(.5*len(sizes))-1],
                    "p95":sizes[math.ceil(.95*len(sizes))-1],"max":sizes[-1],
                    "quantile_rule":"nearest_rank_over_unique_public_packets"}
        by_kind = {kind:stats([r for r in measurements if r["kind"]==kind])
                   for kind in sorted({r["kind"] for r in measurements})}
        summary = {"unique_training_packets":len(ordered),"bank_worlds":len(baseline["bank"]["worlds"]),
                   "kinds":by_kind,"token_counts":stats(measurements),"token_cap":cap,
                   "vocabulary_size":len(tokenizer.vocabulary),"tokenizer_digest":tokenizer.digest,
                   "largest_input_record_ids":[r["record_id"] for r in measurements if r["tokens_including_markers"]==estimate],
                   "max_frame_text_bytes":max(r["frame_text_bytes"] for r in measurements),
                   "max_original_packet_bytes":max(r["packet_bytes"] for r in measurements),
                   "max_slots":max(r["slots"] for r in measurements),
                   "frame_profile":input_frames.profile(),"slot_profile":slots.profile(),
                   "tokenizer_source_profile":tokenization.profile(),
                   "schedule_counts":[{k:v for k,v in row.items() if k!="batches"} for row in schedules],
                   "private_main_targets_read":False,"new_targets_derived":False,
                   "numeric_encoder_implemented":False,"learned_decoder_executed":False,
                   "study_admitted":False,"learning_improvement_established":False}
    except Exception as exc:
        code,error = 1,{"type":type(exc).__name__,"message":str(exc)}
        artifacts.append(write("construction_error.json",error))
after = [pin(path) for path in paths]
artifacts.append(write("inputs_after.json", after))
if (OUT/"tests.xml").exists():
    artifacts.append(pin(OUT/"tests.xml"))
loaded = sorted(DENIED.intersection(sys.modules)|OLD.intersection(sys.modules))
passed = code == 0 and before == after and not attempts and not blocked_reads and not blocked_execution and not loaded
receipt = {"schema":"cncm.typed-interface-pure-check/0.1","status":"PURE_INPUT_SLOTS_TOKENIZATION_PASS" if passed else "FAILED",
           "parent_commit":HEAD,"tests":counts,"runner_error":error,"input_pins":len(before),
           "input_pins_unchanged":before==after,"forbidden_import_attempts":attempts,
           "forbidden_modules_loaded":loaded,"blocked_artifact_reads":blocked_reads,
           "blocked_execution_attempts":blocked_execution,"artifacts":artifacts,"summary":summary,
           "neural_calls":0,"optimizer_updates":0,"provider_calls":0,
           "boundary":"Public-only frames, syntax decoding and measured pure token counts; planned slot work is not measured CUDA compute or learning."}
write("receipt.json",receipt)
print(json.dumps({"status":receipt["status"],"tests":counts,"error":error,"receipt":str(OUT/"receipt.json"),
                  "summary":{k:v for k,v in summary.items() if k not in {"frame_profile","slot_profile","tokenizer_source_profile","largest_input_record_ids"}}}))
raise SystemExit(0 if passed else 1)
