"""One consolidated read-only audit of the checked-component pilot (Attempt 007).

Boundaries, first, because they are the point:

* this tool **executes nothing neural**. It imports no torch, opens no socket,
  creates no reservation and loads no model. It reads the pinned scene, the
  frozen public records, and the artifacts Attempt 007 already delivered;
* it does **not** replace or repair Attempt 007's evidence. Missing historical
  telemetry is reported as missing, never backfilled;
* the measurements that need model execution against the retained checkpoints
  are **not** taken here. They are specified and packaged separately, and require
  their own approval before anything runs.

What it answers, in one pass:

1. the probe panel's answer distribution, from the reference checker rather than
   from reading, with constant-answer baselines for the same panel;
2. whether the private teacher target reaches learner-visible bytes (label
   alignment is a different thing, and is kept);
3. which answers the retained learners actually favoured, from the per-step
   telemetry Attempt 007 did deliver;
4. what is measured, what is missing, and what only execution can supply.

Usage: python tools/graph6_pilot_audit.py [output.json]
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.graph_teaching import (adapter, candidate_experiment as ce,  # noqa: E402
                                      candidate_run as cr, cube_node, reference,
                                      verified_teaching as vt,
                                      verified_training as vtr)

RECORD_DIR = (ROOT / "records/teaching_cycle_001/graph_first_candidate_001/"
              "training_mode_001/cube_verified_teaching_001")
ATTEMPT_007_RECEIPT = RECORD_DIR / "receipt_cas-meta2-graph6cand-20260910174500-e33a6497"
SMOKE_RUNS = ("SMOKE_RUN_001.json", "SMOKE_RUN_002.json")
ABSENCE = {"LIST_PARTS": lambda answer: list(answer) == [],
           "FIND_SHARED_PART": lambda answer: answer == "none",
           "REACHED_VIA": lambda answer: answer == "absent"}


def digest_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def answer_category(operation, answer):
    """The answer's meaning, not its spelling: absence, or what kind of part."""
    if operation == "LIST_PARTS":
        return "empty_list" if list(answer) == [] else "part_list"
    if operation == "FIND_SHARED_PART":
        return "none" if answer == "none" else "shared_part"
    if answer == "absent":
        return "absent"
    if answer == "direct":
        return "direct"
    return "via_other" if str(answer).startswith("via:") else str(answer)


def is_absence(operation, answer):
    return ABSENCE[operation](answer)


# --------------------------------------------------------------------------
# 1. the probe panel
# --------------------------------------------------------------------------

def probe_panel():
    inputs = ce.build_inputs()
    probe = inputs["probe"]
    preparation = cr.prepare_candidate_run()
    probe_plan = preparation["proposed_evaluation"]["probe"]
    panel = {"probe_questions": len(probe),
             "catalog_questions": probe_plan["catalog_questions"],
             "distinct_taught_questions": probe_plan["distinct_taught_questions"],
             "excluded_taught_questions": probe_plan["excluded_taught_questions"],
             "by_operation": OrderedDict(), "taught_versus_probe": {},
             "correct_slot_histogram": Counter(), "absence_answers": 0,
             "questions_without_an_absence_option": 0}
    for record in inputs["records"]:
        panel["taught_versus_probe"].setdefault("taught", Counter())[
            answer_category(record["op"], record["correct"])] += 1
    for record in probe:
        operation = record["op"]
        bucket = panel["by_operation"].setdefault(operation, Counter())
        bucket[answer_category(operation, record["correct"])] += 1
        panel["taught_versus_probe"].setdefault("probe", Counter())[
            answer_category(operation, record["correct"])] += 1
        if is_absence(operation, record["correct"]):
            panel["absence_answers"] += 1
        public = adapter.public_records(record, "cas")
        panel["correct_slot_histogram"][public["encoded_correct_index"]] += 1
        absence_offered = any(is_absence(operation, option)
                              for option in public["encoded_options"])
        if not absence_offered:
            panel["questions_without_an_absence_option"] += 1
    panel["absence_share"] = panel["absence_answers"] / len(probe)
    panel["by_operation"] = {op: dict(counts)
                             for op, counts in panel["by_operation"].items()}
    panel["taught_versus_probe"] = {
        name: dict(counts) for name, counts in panel["taught_versus_probe"].items()}
    panel["correct_slot_histogram"] = dict(panel["correct_slot_histogram"])
    # the checker's own rule, quoted so nobody has to re-derive it
    panel["shared_part_rule"] = (
        "reference.shared_parts: the direct constituents common to both ideas, "
        "plus either idea itself when it is a direct constituent of the other. "
        "The second clause is why Bicycle/Frame answers Frame and Rim/Wheel "
        "answers Rim; a reading of the first clause alone reports all fourteen "
        "pairs as 'none'.")
    return panel


def constant_rules():
    """What a rule that does not look at the graph would score on this panel."""
    probe = ce.build_inputs()["probe"]
    totals = {"questions": len(probe)}
    rules = OrderedDict()

    def score(pick):
        return sum(1 for record in probe
                   if canonical(record["correct"]) == canonical(pick(record)))

    def public(record):
        return adapter.public_records(record, "cas")

    def absence_then(fallback):
        def pick(record):
            options = public(record)["encoded_options"]
            for option in options:
                if is_absence(record["op"], option):
                    return option
            return fallback(options)
        return pick

    rules["always_absence_then_first_offered"] = score(absence_then(lambda o: o[0]))
    rules["always_absence_then_last_offered"] = score(absence_then(lambda o: o[-1]))
    rules["always_positive_then_first_offered"] = score(
        lambda record: next((option for option in public(record)["encoded_options"]
                             if not is_absence(record["op"], option)),
                            public(record)["encoded_options"][0]))
    for slot in range(3):
        rules["always_slot_%d" % slot] = score(
            lambda record, slot=slot: public(record)["encoded_options"][slot])
    rules["uniform_random_expectation"] = round(len(probe) / 3, 2)
    totals["rules"] = rules
    totals["absence_answer_mass"] = sum(
        1 for record in probe if is_absence(record["op"], record["correct"]))
    return totals


def canonical(value):
    from cas_meta2.graph_teaching.graph import canonical as _canonical
    return _canonical(value)


# --------------------------------------------------------------------------
# 2. label alignment versus private-target dependence
# --------------------------------------------------------------------------

def target_dependence():
    """Does the private teacher target reach learner-visible bytes?

    With the graph, the question and the candidate answers held fixed, a second
    target object is supplied that names a different offered choice. Everything
    the learner can see is then compared between the two records.
    """
    bundle = cube_node.load_bundle()
    report = vt.compile_bundle(bundle, choice_order="declared")
    index = vt.Index(bundle, vt.lesson_context(bundle, "view_context"), "view_context")
    targets = {target["exercise_id"]: target
               for target in report["private_teacher_targets"]}
    section = {"taught_records": [], "probe_records": [],
               "record_id_basis_contains": [],
               "delivered_compilation_measurement": {},
               "label_alignment_check": None}

    basis = vtr.record_from_exercise.__doc__ or ""
    source = (ROOT / "cas_meta2/graph_teaching/verified_training.py").read_text(
        encoding="utf-8")
    for field in ("expected_choice_id", "witness_kind", "expected_answer",
                  "correct", "record_id"):
        if '"%s"' % field in source:
            section["record_id_basis_contains"].append(field)
    section["label_alignment_check"] = (
        "candidate_experiment.connection_check reports "
        "all_slots_carry_the_teacher_answer, which asserts "
        "encoded_options[encoded_correct_index] == the teacher answer. That is "
        "label alignment: if it failed, the loss could reward the wrong option. "
        "It is not evidence of leakage, and it is kept.")
    section["delivered_compilation_measurement"] = {
        "note": ("measured on the code as delivered to Attempt 007, BEFORE the "
                 "public-projection fix was applied; the live rows below measure "
                 "the current code, which no longer carries the dependence"),
        "id_basis": "digest(canonical(core)), with expected_choice_id and "
                    "witness_kind inside core",
        "record_id_changed": "8 of 8",
        "learner_visible_option_order_changed": "4 of 8",
        "learner_visible_observations_changed": "4 of 8",
        "problem_text_changed": "0 of 8",
        "probe_records_via_record_from_question": "no change on any field",
        "fix": ("verified_training.public_projection strips the two target-derived "
                "fields from the id basis; new compilations only, so the delivered "
                "Attempt 007 records keep the ids they were measured with"),
    }

    for exercise in report["public_exercises"]:
        target = targets[exercise["exercise_id"]]
        choices = {choice["choice_id"]: choice["value"]
                   for choice in exercise["choices"]}
        others = [(choice_id, value) for choice_id, value in choices.items()
                  if canonical(value) != canonical(target["expected_answer"])]
        choice_id, value = sorted(others)[0]
        flipped = dict(target)
        flipped["expected_answer"] = value
        flipped["expected_choice_id"] = choice_id
        first = vtr.record_from_exercise(bundle, exercise, target, index,
                                         "view_context", "audit")
        second = vtr.record_from_exercise(bundle, exercise, flipped, index,
                                          "view_context", "audit")
        first_public = adapter.public_records(first, "cas")
        second_public = adapter.public_records(second, "cas")
        section["taught_records"].append({
            "exercise_id": exercise["exercise_id"],
            "operation": exercise["question"]["operation"],
            "target_changed_only": True,
            "prompt_text_identical":
                first_public["public"]["problem"] == second_public["public"]["problem"],
            "record_id_changed": first["record_id"] != second["record_id"],
            "learner_visible_option_order_changed":
                first_public["encoded_options"] != second_public["encoded_options"],
            "learner_visible_observations_changed":
                first_public["public"]["observations"]
                != second_public["public"]["observations"],
            "encoded_correct_index_changed":
                first_public["encoded_correct_index"]
                != second_public["encoded_correct_index"],
        })

    inputs = ce.build_inputs()
    for record in inputs["probe"][:6]:
        options = list(record["options"])
        question_key = record["cube_verified_teaching"]["question_key"]
        others = [option for option in options
                  if canonical(option) != canonical(record["correct"])]
        flipped = vtr.record_from_question(
            bundle, dict(record["question"]), options, others[0], "view_context",
            "audit", extra={"question_key": question_key})
        original = vtr.record_from_question(
            bundle, dict(record["question"]), options, record["correct"],
            "view_context", "audit", extra={"question_key": question_key})
        original_public = adapter.public_records(original, "cas")
        flipped_public = adapter.public_records(flipped, "cas")
        section["probe_records"].append({
            "operation": record["op"],
            "record_id_changed": original["record_id"] != flipped["record_id"],
            "prompt_text_identical":
                original_public["public"]["problem"] == flipped_public["public"]["problem"],
            "learner_visible_option_order_changed":
                original_public["encoded_options"]
                != flipped_public["encoded_options"],
        })
    return section


# --------------------------------------------------------------------------
# 3. what the retained learners actually chose
# --------------------------------------------------------------------------

def attempt007():
    """Per-step telemetry Attempt 007 delivered, and what it does not contain."""
    raw = (ATTEMPT_007_RECEIPT / "curriculum_result.json").read_bytes()
    envelope = json.loads(raw)
    measurements = envelope["measurements"]
    section = {
        "receipt": ATTEMPT_007_RECEIPT.name,
        "result_sha256": digest_of(ATTEMPT_007_RECEIPT / "curriculum_result.json"),
        "envelope_status": envelope["status"],
        "updates_per_condition": measurements["updates_per_condition"],
        "artifacts": envelope["artifacts"],
        "conditions": {},
        "available_from_this_delivery": [],
        "not_available_from_this_delivery": [],
    }
    for condition, payload in measurements["results"].items():
        steps = payload["predictions"]
        entry = {"steps": len(steps),
                 "correct_steps": sum(1 for s in steps if s["selected_is_correct"]),
                 "expected_category_counts": Counter(),
                 "selected_category_counts": Counter(),
                 "confusion": Counter(),
                 "phase_counts": Counter(),
                 "per_record": {},
                 "checkpoint_chain": {},
                 "first_half_correct": sum(
                     1 for s in steps[:len(steps) // 2] if s["selected_is_correct"]),
                 "second_half_correct": sum(
                     1 for s in steps[len(steps) // 2:] if s["selected_is_correct"])}
        for step in steps:
            expected = answer_category(step["operation"], step["expected_answer"])
            selected = answer_category(step["operation"], step["selected_answer"])
            entry["expected_category_counts"][expected] += 1
            entry["selected_category_counts"][selected] += 1
            entry["confusion"]["%s->%s" % (expected, selected)] += 1
            entry["phase_counts"][step["phase"]] += 1
            record = entry["per_record"].setdefault(
                step["record_id"], {"operation": step["operation"],
                                    "expected": step["expected_answer"],
                                    "correct": 0, "steps": 0,
                                    "selected": Counter()})
            record["steps"] += 1
            record["correct"] += 1 if step["selected_is_correct"] else 0
            record["selected"][str(step["selected_answer"])] += 1
        for record in entry["per_record"].values():
            record["selected"] = dict(record["selected"])
        chain = [step["update_identity"] for step in steps if step["update_identity"]]
        entry["checkpoint_chain"] = {
            "links": len(chain),
            "distinct_checkpoint_after": len({link["checkpoint_after"] for link in chain}),
            "consecutive_links_join": all(
                chain[index]["checkpoint_after"] == chain[index + 1]["checkpoint_before"]
                for index in range(len(chain) - 1)),
        }
        entry["expected_category_counts"] = dict(entry["expected_category_counts"])
        entry["selected_category_counts"] = dict(entry["selected_category_counts"])
        entry["confusion"] = dict(entry["confusion"])
        entry["phase_counts"] = dict(entry["phase_counts"])
        section["conditions"][condition] = entry

    # paired, per taught question, at each condition's last exposure to it.
    # Only the questions BOTH conditions practised can be paired at all: the
    # control never practises the five component-route questions, so it has no
    # telemetry for them.
    last = {}
    for condition, payload in measurements["results"].items():
        last[condition] = {}
        for step in payload["predictions"]:
            last[condition][step["record_id"]] = step["selected_is_correct"]
    checked_records = set(last["checked_component_teaching"])
    control_records = set(last["final_answer_only"])
    shared = sorted(checked_records & control_records)
    only_checked = [rid for rid in shared
                    if last["checked_component_teaching"][rid]
                    and not last["final_answer_only"][rid]]
    only_control = [rid for rid in shared
                    if last["final_answer_only"][rid]
                    and not last["checked_component_teaching"][rid]]
    both = [rid for rid in shared if last["final_answer_only"][rid]
            and last["checked_component_teaching"][rid]]
    neither = [rid for rid in shared if not last["final_answer_only"][rid]
               and not last["checked_component_teaching"][rid]]
    section["paired_taught_records_last_exposure"] = {
        "records_with_steps_in_both_conditions": len(shared),
        "records_only_checked_practised": len(checked_records - control_records),
        "records_only_control_practised": len(control_records - checked_records),
        "only_checked_correct": len(only_checked),
        "only_control_correct": len(only_control),
        "both_correct": len(both), "neither_correct": len(neither),
        "note": ("this pairing is over the taught records where per-step telemetry "
                 "exists in both conditions - three whole-answer questions; the "
                 "five component questions have no control-condition telemetry "
                 "because the control never practises them. The paired PROBE "
                 "comparison the directive asks for cannot be computed from this "
                 "delivery: its per-question rows were not retained.")}

    section["available_from_this_delivery"] = [
        "per-step expected and selected answers for all 128 training updates, "
        "with operation, phase, block and per-step parameter digests",
        "per-condition measured counts for the three taught whole-answer "
        "questions, the five taught component questions and the 44-question probe",
        "containment, checkpoint verification, matched initial weights, and the "
        "delivered checkpoint files with their hashes"]
    section["not_available_from_this_delivery"] = [
        "the per-question probe rows: the delivered report kept only the "
        "after-training per-operation breakdown, so which individual probe "
        "questions were lost or gained is not recoverable, and a paired "
        "McNemar comparison cannot be computed",
        "the per-step scores and losses: the worker injected no scorer and the "
        "learner exposed no scores method, so every score field reads "
        "'unavailable' (64 of 64 per condition)",
        "the before-training per-operation breakdown of the probe"]
    return section


# --------------------------------------------------------------------------
# 4. which observation belongs to which run
# --------------------------------------------------------------------------

def observations():
    section = {"attempt_007": {}, "smoke_runs": {}, "separations": []}
    receipt = json.loads((ATTEMPT_007_RECEIPT / "result.json").read_bytes())
    measurements = json.loads(
        (ATTEMPT_007_RECEIPT / "curriculum_result.json").read_bytes())["measurements"]
    checkpoints = sorted((ATTEMPT_007_RECEIPT / "checkpoints").glob("*.pt"))
    section["attempt_007"] = {
        "kind": "paid AWS run, the pilot's measurement",
        "status": receipt["status"],
        "elapsed_seconds": round(receipt["elapsed_seconds"], 1),
        "package": "candidate_package_006/",
        "updates": measurements["counters"]["actual_optimizer_updates"],
        "updates_per_condition": measurements["updates_per_condition"],
        "matched_initial_weights": measurements["matched_initial_weights"],
        "checkpoints": [{"name": path.name, "bytes": path.stat().st_size,
                         "sha256": digest_of(path)} for path in checkpoints],
        "device": "the AWS instance's A10G (g7.2xlarge)",
    }
    for name in SMOKE_RUNS:
        path = RECORD_DIR / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        # the saved stdout carries the tool's JSON and then its own boundary line
        document = json.loads(text[:text.rindex("}") + 1])
        section["smoke_runs"][name] = {
            "sha256": digest_of(path),
            "kind": "local smoke run, NOT a measurement",
            "device": document.get("gpu"),
            "torch": document.get("torch"),
            "updates_per_condition": document.get("updates_per_condition"),
            "total_updates": (document.get("counters") or {}).get(
                "actual_optimizer_updates"),
            "checkpoints_written": document.get("checkpoints"),
            "provenance_recorded_by_the_tool": sorted(document),
        }
    section["separations"] = [
        ("Attempt 007 trained 128 updates on the paid instance and delivered the "
         "checkpoints named above. The smoke runs trained 6 updates each, from "
         "fresh initial weights, on the local RTX 4070, and wrote their own "
         "throwaway checkpoint files: they are newly trained mini-runs, not "
         "rereads of the retained weights."),
        ("The smoke runs therefore cannot recover Attempt 007's missing "
         "per-question probe rows or its missing scores. They establish that the "
         "corrected instrumentation now records those fields."),
        ("A zero-update reread of the retained checkpoints is a third thing "
         "again, and it has not been done. That is what the packaged diagnostic "
         "specifies."),
    ]
    return section


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    report = OrderedDict()
    report["schema"] = "cas-graph-pilot-audit/1"
    report["boundary"] = ("read-only; no torch, no model, no provider, no "
                          "reservation, no training; Attempt 007 preserved as "
                          "delivered and never backfilled")
    report["probe_panel"] = probe_panel()
    report["constant_rules"] = constant_rules()
    report["target_dependence"] = target_dependence()
    report["attempt_007"] = attempt007()
    report["observations"] = observations()
    text = json.dumps(report, indent=2, sort_keys=False, default=str)
    if argv:
        Path(argv[0]).write_text(text + "\n", encoding="utf-8")
        print("written:", argv[0])
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
