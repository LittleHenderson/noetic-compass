"""One training packet, pure-only benchmark. No semantic targets or tensors."""
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys
import time

started = time.perf_counter()
root, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path[:0] = [str(root), str(root / "research/CAS_META_2_COMPOSITION")]
attempted = []
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "requests", "cas_cjt", "casformer"} or fullname.rsplit(".", 1)[-1] in {"checker", "loss_plan", "face_tasks", "face_corpus", "final_panel"}:
            attempted.append(fullname)
            raise RuntimeError("PROHIBITED_IMPORT:" + fullname)
sys.meta_path.insert(0, Deny())
from cas_meta2.typed_teaching import worker_contract, course, slots, binding

rows = []
def timed(name, fn):
    at = time.perf_counter()
    value = fn()
    rows.append({"operation": name, "seconds": time.perf_counter() - at})
    print(json.dumps(rows[-1]), flush=True)
    if time.perf_counter() - started > 55:
        raise RuntimeError("PURE_BENCHMARK_TIME_BOUND")
    return value

frozen, tokenizer, schedule = timed("load_material", lambda: worker_contract.load_material(root))
record = next(row for row in frozen["registry"] if row["query"]["kind"] == "correspondence")
packet = timed("model_packet", lambda: course.model_packet(frozen, record["record_id"]))
plan = timed("slots.compile_slots.first", lambda: slots.compile_slots(packet))
timed("slots.compile_slots.repeat", lambda: slots.compile_slots(packet))
timed("slots.validate_plan", lambda: slots.validate_plan(packet, plan))
bound = timed("binding.compile_packet", lambda: binding.compile_packet(packet, tokenizer, seed=20260916))
scores = {slot["slot_id"]: {symbol: 0.0 for symbol in slot["symbols"]} for slot in plan["slots"]}
decision = timed("slots.score_decisions.synthetic_zero_scores", lambda: slots.score_decisions(packet, scores))
timed("slots.assemble_answer.synthetic_decisions", lambda: slots.assemble_answer(packet, decision))
# Count repeated pure admission calls separately from the timing measurements.
counts = {}
def profile(frame, event, arg):
    if event == "call" and frame.f_code.co_name in {"validate_model_packet", "validate_public", "compile_slots", "public_digest", "_bounded", "profile"}:
        key = frame.f_globals.get("__name__", "") + "." + frame.f_code.co_name
        if key.startswith("cas_meta2"):
            counts[key] = counts.get(key, 0) + 1
sys.setprofile(profile)
slots.compile_slots(packet)
sys.setprofile(None)
sources = []
for name, module in sorted(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if name.startswith("cas_meta2") and filename and Path(filename).suffix == ".py":
        path = Path(filename).resolve()
        raw = path.read_bytes()
        sources.append({"module": name, "path": path.relative_to(root).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
result = {"schema": "typed-pure-one-packet-performance/0.1", "status": "PURE_ONLY_OBSERVED",
    "record_id": record["record_id"], "kind": record["query"]["kind"], "slots": len(plan["slots"]),
    "syntactic_correspondence_candidates": len(plan["correspondence_candidates"]),
    "bank_worlds": len(packet["source"]["bank"]["world_ids"]), "binding_rows": len(bound["rows"]),
    "binding_tokens": sum(row["count"] for row in bound["rows"]), "timings": rows,
    "separate_single_compile_profile_call_counts": counts, "sources": sources,
    "material": worker_contract.MATERIAL, "prohibited_import_attempts": attempted,
    "total_seconds": time.perf_counter() - started,
    "boundary": "One real training-only packet on local CPU; syntactic zero scores only. No semantic target or numerical model execution. Not a GPU runtime estimate."}
with output.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
print(json.dumps({"status": result["status"], "total_seconds": result["total_seconds"], "output": str(output)}))
