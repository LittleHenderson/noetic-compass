"""Read saved training outputs only; no project imports or checker/model rerun."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ART = BASE / "receipt_002/collected/results/artifacts"
INPUTS = []
def read(path):
    raw = path.read_bytes()
    INPUTS.append({"path": path.relative_to(BASE).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    return json.loads(raw)

manifest = read(ART / "manifest.json")
manifest_by_name = {r["name"]: r for r in manifest["artifacts"]}
review_receipt = read(BASE / "completed_review_002/receipt.json")
review = read(BASE / "completed_review_002/stdout.json")
assert sha256((ART / "manifest.json").read_bytes()).hexdigest() == review_receipt["worker_manifest_sha256"]
review_pin = next(r for r in review_receipt["artifacts"] if r["path"].endswith("stdout.json"))
assert INPUTS[-1]["sha256"] == review_pin["sha256"]
predictions, scoring = {}, {}
for phase in ("initial", "final"):
    p = read(ART / (phase + "_predictions.json"))
    s = read(ART / (phase + "_scoring.json"))
    predictions[phase] = {r["record_id"]: r for r in p["predictions"]}
    scoring[phase] = {r["record_id"]: r for r in s["rows"]}
    assert list(predictions[phase]) == list(scoring[phase]) and len(scoring[phase]) == 564
    for pin in INPUTS[-2:]:
        declared = manifest_by_name[Path(pin["path"]).name]
        assert (pin["sha256"], pin["bytes"]) == (declared["sha256"], declared["bytes"])
    for key, row in scoring[phase].items():
        assert row["prediction_id"] == predictions[phase][key]["prediction_id"]
        assert row["kind"] == predictions[phase][key]["answer"]["kind"]
        assert type(row["correct"]) is bool

def histogram(values):
    return dict(sorted(Counter(values).items(), key=lambda p: str(p[0])))
def top(values):
    return [{"value": value, "count": count} for value, count in Counter(values).most_common(5)]
def world(ref):
    return ref.split("/", 1)[0]
def rows(phase, kind):
    return [r for r in predictions[phase].values() if r["answer"]["kind"] == kind]

observed = {}
for kind in ("context", "definition", "edge_account", "analogy"):
    observed[kind] = {"recorded_exact_answer_metrics": review["by_kind"][kind], "phases": {}}
    for phase in ("initial", "final"):
        selected = rows(phase, kind)
        values = [r["answer"]["value"] for r in selected]
        assert len(selected) == 70
        symbols = [v for r in selected for v in r["decisions"]["selected"].values()]
        detail = {"records": 70, "recorded_correct": sum(scoring[phase][r["record_id"]]["correct"] for r in selected)}
        if kind == "context":
            nonempty = [v for v in values if v["participants"]]
            detail.update(participant_count_histogram=histogram(len(v["participants"]) for v in values),
                emitted_participants_total=sum(len(v["participants"]) for v in values),
                setting_points_outside_emitted_participant_world=sum(any(world(ref) != world(v["setting_ref"]) for ref in v["participants"]) for v in nonempty),
                nonempty_participant_records=len(nonempty),
                top_setting_world_aliases=top(s for s in symbols if s.startswith("W")))
        elif kind == "definition":
            detail.update(kind_ref_same_world_as_emitted_whole=sum(world(v["kind_ref"]) == world(v["whole"]) for v in values),
                function_ref_same_world_as_emitted_whole=sum(world(v["function_ref"]) == world(v["whole"]) for v in values),
                both_declaration_refs_same_world_as_emitted_whole=sum(world(v["kind_ref"]) == world(v["function_ref"]) == world(v["whole"]) for v in values),
                kind_and_function_refs_different_worlds=sum(world(v["kind_ref"]) != world(v["function_ref"]) for v in values),
                top_declaration_world_aliases=top(s for s in symbols if s.startswith("W")),
                emitted_whole_node_suffixes=histogram(v["whole"].rsplit("/", 1)[1] for v in values))
        elif kind == "edge_account":
            all_edges = [e for v in values for e in v["edges"]]
            detail.update(edge_count_histogram=histogram(len(v["edges"]) for v in values),
                emitted_edges_total=len(all_edges),
                records_with_self_edges=sum(any(e["source"] == e["target"] for e in v["edges"]) for v in values),
                self_edges_total=sum(e["source"] == e["target"] for e in all_edges),
                top_local_pairs=top(e["source"].rsplit("/",1)[1]+"->"+e["target"].rsplit("/",1)[1] for e in all_edges),
                binary_decisions=histogram(symbols))
        else:
            detail.update(distinct_selected_worlds=len({v["world_id"] for v in values if v["world_id"] is not None}),
                distinct_answer_values=len({v["world_id"] for v in values}),
                no_match_answers=sum(v["world_id"] is None for v in values), top_world_aliases=top(symbols))
        observed[kind]["phases"][phase] = detail

analogy_ids = [r["record_id"] for r in rows("initial", "analogy")]
lost = [key for key in analogy_ids if scoring["initial"][key]["correct"] and not scoring["final"][key]["correct"]]
gained = [key for key in analogy_ids if not scoring["initial"][key]["correct"] and scoring["final"][key]["correct"]]
unchanged_correct = [key for key in analogy_ids if scoring["initial"][key]["correct"] and scoring["final"][key]["correct"]]
changed = [key for key in analogy_ids if predictions["initial"][key]["answer"]["value"] != predictions["final"][key]["answer"]["value"]]
assert (len(lost),len(gained),len(unchanged_correct)) == (12,10,0)
observed["analogy"]["turnover"] = {"lost_record_ids": lost, "gained_record_ids": gained,
    "unchanged_correct_record_ids": unchanged_correct, "changed_answer_count": len(changed),
    "lost_final_aliases": top(next(iter(predictions["final"][key]["decisions"]["selected"].values())) for key in lost),
    "gained_final_aliases": top(next(iter(predictions["final"][key]["decisions"]["selected"].values())) for key in gained)}
examples = {}
for kind in observed:
    keys = (lost[:3] if kind == "analogy" else [r["record_id"] for r in rows("final", kind)][:3])
    examples[kind] = [{"record_id": key,
        "initial_value": predictions["initial"][key]["answer"]["value"],
        "final_value": predictions["final"][key]["answer"]["value"],
        "initial_recorded_correct": scoring["initial"][key]["correct"],
        "final_recorded_correct": scoring["final"][key]["correct"]} for key in keys]

result = {"schema": "cncm.typed-course-output-pattern-diagnosis/0.1", "status": "READ_ONLY_RECORDED_OUTPUT_PATTERNS",
    "job": review_receipt["job"], "source_sha": review_receipt["source_sha"], "inputs": INPUTS,
    "observed": observed, "examples": examples,
    "hypotheses_not_established": [
        "Cross-world declaration mismatches suggest weak linking of the requested world to global declaration choices; this does not establish whether encoding, core capacity, readout, optimization, or curriculum caused it.",
        "Analogy gains and losses may reflect interference or changed output preference across training; only two saved evaluation points were examined, so no particular update or mechanism is identified."],
    "limits": ["All70 cases per selected kind are already-exposed training material, not held-out transfer.",
        "Correctness is taken from saved scoring receipts; no semantic checker was rerun.",
        "Reference-world comparisons are consistency counts between emitted fields, not newly computed partial correctness scores.",
        "Self-edge and answer-size counts describe emitted syntax only; no graph repair or new scoring was performed.",
        "No tensors, checkpoints, providers, neural execution, or new experiment were used.",
        "No causal claim or matched learning advantage follows from these output patterns."],
    "input_bytes_unchanged": all(sha256((BASE/p["path"]).read_bytes()).hexdigest() == p["sha256"] for p in INPUTS)}
assert result["input_bytes_unchanged"]
with (OUT/"diagnosis.json").open("x",encoding="utf-8") as f:
    json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
print(json.dumps({"observed": observed,"inputs_unchanged":True},indent=2,sort_keys=True))
