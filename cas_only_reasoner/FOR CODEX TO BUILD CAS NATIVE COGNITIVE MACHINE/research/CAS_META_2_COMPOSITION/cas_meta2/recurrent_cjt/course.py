"""CAS_RDCJT_001 step three: the CFC course bound to the variable depth schedule.

The recurrence is the mechanism; the course is what has to be equal on both sides for
the comparison to mean anything. This module fixes the course, and it fixes it by
reading the schedule that already exists rather than by restating a shape:

* per round, 28 within-cube decisions, 12 across-face, 8 return-to-cube and 8
  maintenance — 56 decisions and **8 optimizer updates**, the last derived from the
  constructor's declared batch structure ([8,8,8,4] / [8,4] / [8] / [8]) rather than
  copied from a table;
* sixteen rounds, each assigned one depth, every depth four times, so exposure to each
  depth is equal including maintenance;
* ``schedule_binding`` reads ``face_schedule.cfc_round_events`` and checks its own
  counts against the declared allowance, so a course that drifts away from the
  schedule fails instead of reporting the wrong shape;
* the matched one-pass condition is ``depths=(1,) * 16`` with the same events, the
  same starting weights, the same batch structure and the same update count. The
  depth schedule is the ONE difference.

One declared gap, reported as a gap: the constructor plan declares the maintenance
allowance — 8 decisions, one batch, every round — but does not say WHICH decisions.
``maintenance_round`` fills that with the same cohort's previous visit and labels it a
declared choice, not a recovered fact. It is not presented as recovered.

The evidence that set this candidate's target is worth restating here, because it is
what the course is for: in the delivered readout every rewired ``direct_inventory``
question was answered as a one-item superset in all four conditions (0/6 in each, 24
of 24 failures, byte-identical across conditions), while the two route questions on
the same rewritten graphs scored 12/12. The answer did not follow the supplied
relationships. Whether more passes fix that is the thing to measure — on a FRESH
family panel, because those rewired rows have now been examined and cannot be the
final test.
"""
from __future__ import annotations

from collections import OrderedDict

from . import recurrence as rc

SCHEMA = "cas.recurrent-cjt-course/0.1"

#: The maintenance allowance is declared; its source is not. Recorded, not hidden.
MAINTENANCE_NOTE = {
    "declared": {"decisions_per_round": 8, "batches": [8], "updates_per_round": 1},
    "source": ("the constructor plan declares the allowance but not WHICH decisions. "
               "The default here replays the same cohort's previous visit's "
               "return-to-cube decisions (8 events, one batch of 8)"),
    "status": "DECLARED_CHOICE_FILLING_A_DECLARED_GAP",
    "consequence": ("a different maintenance source changes what the maintenance "
                    "phase rehearses. Both conditions use the same source, so the "
                    "comparison is unaffected; the absolute numbers are conditional "
                    "on this choice and are reported as such")}


def require(condition, code):
    if not condition:
        raise ValueError(code)


# --------------------------------------------------------------------------
# the declared shape of one round
# --------------------------------------------------------------------------

def round_plan(round_index, *, depth=None):
    """One round: its depth, its four phases, and the batches each phase flushes at."""
    depth = rc.depth_for_round(round_index) if depth is None else int(depth)
    require(depth in rc.DEPTHS, "COURSE_DEPTH_NOT_DECLARED:" + str(depth))
    phases = []
    for phase, decisions, _declared_updates in rc.ROUND_PHASES:
        batches = rc.phase_batches(phase)
        phases.append({"phase": phase, "decisions": decisions,
                       "batches": list(batches), "updates": len(batches)})
    return {"round": round_index, "depth": depth, "phases": phases,
            "decisions": sum(entry["decisions"] for entry in phases),
            "batches": sum(len(entry["batches"]) for entry in phases),
            "updates": sum(entry["updates"] for entry in phases)}


def course_plan(*, depths=None):
    """The whole declared course. ``depths`` is the ONE thing the conditions differ in."""
    depths = tuple(depths or rc.ROUND_DEPTH_SCHEDULE)
    rounds = [round_plan(index, depth=depths[index])
              for index in range(len(depths))]
    coverage = {}
    for entry in rounds:
        coverage[entry["depth"]] = coverage.get(entry["depth"], 0) + 1
    return {"schema": SCHEMA, "depths": list(depths), "rounds": rounds,
            "round_count": len(rounds),
            "decisions": sum(entry["decisions"] for entry in rounds),
            "batches": sum(entry["batches"] for entry in rounds),
            "updates": sum(entry["updates"] for entry in rounds),
            "depth_coverage": coverage,
            "maintenance": dict(MAINTENANCE_NOTE),
            "matching": ("the one-pass condition is depths=(1,)*16: same events, same "
                         "starting weights, same batches, same updates")}


def schedule_binding(built=None):
    """Do the constructor's per-round allowance and the schedule's own round agree?

    Read, not assumed. If the schedule's ``cfc_round_events`` ever stops producing
    28 / 12 / 8, the course would be teaching a different shape from the one it
    reports, and this check is what refuses that.
    """
    from ..graph_teaching import face_schedule as schedule
    events = schedule.cfc_round_events(0, built=built)
    counted = {}
    for event in events:
        counted[event["movement"]] = counted.get(event["movement"], 0) + 1
    declared = {phase: decisions for phase, decisions, _u in rc.ROUND_PHASES}
    agreement = OrderedDict()
    for phase in ("WITHIN_CUBE", "ACROSS_FACE", "RETURN_TO_CUBE"):
        scheduled = counted.get(phase, 0)
        agreement[phase] = {"scheduled": scheduled, "declared": declared[phase],
                            "agrees": scheduled == declared[phase]}
    return {"schema": SCHEMA, "scheduled_events": len(events),
            "by_movement": counted, "agreement": agreement,
            "maintenance_stream": ("the schedule has no maintenance event generator: "
                                   "the maintenance allowance is declared in the "
                                   "constructor plan only"),
            "all_agree": all(entry["agrees"] for entry in agreement.values())}


def maintenance_round(round_index, *, cohorts=None):
    """Which round's events the maintenance phase replays.

    See ``MAINTENANCE_NOTE``: the allowance is declared, the source is not. This is
    the declared choice, and the literal reading of "old skill" — the same cohort's
    previous visit. It is a choice, and it is reported as a choice.
    """
    from ..graph_teaching.face_schedule import CFC_COHORTS
    cohorts = CFC_COHORTS if cohorts is None else cohorts
    require(int(round_index) >= 0, "COURSE_ROUND_NEGATIVE")
    source = int(round_index) - int(cohorts)
    return 0 if source < 0 else source


# --------------------------------------------------------------------------
# running the course
# --------------------------------------------------------------------------

def default_tasks_for_round(round_index, *, built=None):
    """The scheduled events of one round, compiled into learner-shaped tasks.

    The three target phases come from ``cfc_round_events``. The maintenance phase
    comes from ``maintenance_round``, and which round that is gets recorded by the
    caller as a declared choice.
    """
    from ..graph_teaching import face_experiment as experiment
    from ..graph_teaching import face_schedule as schedule
    source = maintenance_round(round_index)
    by_phase = {}
    for event in schedule.cfc_round_events(round_index, built=built):
        by_phase.setdefault(event["movement"], []).append(event)
    by_phase["OLD_SKILL_MAINTENANCE"] = [
        event for event in schedule.cfc_round_events(source, built=built)
        if event["movement"] == "RETURN_TO_CUBE"]
    return {phase: [experiment.episode_task(experiment.compile_event(
        event, built=built))
        for event in by_phase.get(phase, [])]
        for phase, _decisions, _updates in rc.ROUND_PHASES}


def run_course(*, learner, batch_step, tasks_for_round=None, depths=None,
               accounting=None, observer=None):
    """Sixteen rounds at the scheduled depths, one optimizer update per declared batch.

    ``batch_step`` is injected (``learner.recurrent_batch_step`` in the deployed
    path), so this function holds no torch. The phases flush at their boundaries, so
    within-cube updates can affect the across-face work that follows.
    """
    supplied_tasks = tasks_for_round or default_tasks_for_round
    plan = course_plan(depths=depths)
    require(plan["round_count"] == len(rc.ROUND_DEPTH_SCHEDULE),
            "COURSE_ROUND_COUNT:" + str(plan["round_count"]))
    rows = []
    for entry in plan["rounds"]:
        round_index = entry["round"]
        learner.set_depth(entry["depth"])
        supplied = supplied_tasks(round_index)
        for phase in entry["phases"]:
            pool = list(supplied.get(phase["phase"]) or [])
            require(len(pool) == phase["decisions"],
                    "COURSE_PHASE_LENGTH:%s:%d!=%d"
                    % (phase["phase"], len(pool), phase["decisions"]))
            offset = 0
            for batch_size in phase["batches"]:
                batch = pool[offset:offset + batch_size]
                offset += batch_size
                require(len(batch) == batch_size, "COURSE_BATCH_SHORT")
                outcome = batch_step(learner, batch)
                require(outcome["optimizer_steps"] == 1,
                        "COURSE_BATCH_MORE_THAN_ONE_UPDATE:" + phase["phase"])
                row = {"round": round_index, "depth": entry["depth"],
                       "phase": phase["phase"], "batch_size": len(batch),
                       "optimizer_steps": int(outcome["optimizer_steps"]),
                       "mean_loss": outcome["mean_loss"]}
                rows.append(row)
                if observer is not None:
                    observer(row)
    return {"plan": plan, "rows": rows,
            "report": course_report(rows, plan=plan, accounting=accounting)}


def course_report(rows, *, plan, accounting=None):
    """What the course actually did, against what it declared.

    Both conditions must land on the same decisions, batches and updates; the depth
    schedule is the only field allowed to differ, and it is reported per round so a
    silent flattening cannot pass as a matched run.
    """
    by_round = OrderedDict()
    for row in rows:
        entry = by_round.setdefault(row["round"], {
            "depth": row["depth"], "decisions": 0, "batches": 0, "updates": 0,
            "by_phase": OrderedDict()})
        entry["decisions"] += row["batch_size"]
        entry["batches"] += 1
        entry["updates"] += row["optimizer_steps"]
        phase = entry["by_phase"].setdefault(row["phase"], {"decisions": 0,
                                                            "batches": 0})
        phase["decisions"] += row["batch_size"]
        phase["batches"] += 1
    declared = {entry["round"]: entry for entry in plan["rounds"]}
    mismatches = []
    # Missing rounds are checked FIRST and separately. Iterating only what was
    # delivered would let a whole absent round pass as a match, which is the exact
    # failure mode a completeness check exists to catch.
    missing = sorted(index for index in declared if index not in by_round)
    for index in missing:
        wanted = declared[index]
        mismatches.append({"round": index, "field": "round_delivered",
                           "delivered": "absent", "declared": wanted["decisions"]})
    for index, entry in by_round.items():
        if index not in declared:
            mismatches.append({"round": index, "field": "round_not_declared",
                               "delivered": entry["decisions"], "declared": 0})
            continue
        wanted = declared[index]
        for field in ("depth", "decisions", "batches", "updates"):
            if entry[field] != wanted[field]:
                mismatches.append({"round": index, "field": field,
                                   "delivered": entry[field],
                                   "declared": wanted[field]})
        for phase in wanted["phases"]:
            got = entry["by_phase"].get(phase["phase"]) or {"decisions": 0,
                                                            "batches": 0}
            if got["decisions"] != phase["decisions"] or got["batches"] != len(
                    phase["batches"]):
                mismatches.append({"round": index, "field": "phase:" + phase["phase"],
                                   "delivered": dict(got),
                                   "declared": {"decisions": phase["decisions"],
                                                "batches": len(phase["batches"])}})
    return {"schema": SCHEMA,
            "delivered": {"decisions": sum(entry["decisions"]
                                           for entry in by_round.values()),
                          "batches": sum(entry["batches"]
                                         for entry in by_round.values()),
                          "updates": sum(entry["updates"]
                                         for entry in by_round.values()),
                          "rounds": len(by_round),
                          "rounds_present": sorted(by_round)},
            "declared": {"decisions": plan["decisions"],
                         "batches": plan["batches"],
                         "updates": plan["updates"],
                         "rounds": plan["round_count"],
                         "rounds_present": sorted(declared)},
            "missing_rounds": missing,
            "by_round": by_round,
            "mismatches": mismatches,
            "matches_declaration": not mismatches,
            "depths_delivered": [entry["depth"] for entry in by_round.values()],
            "depth_coverage": plan["depth_coverage"],
            "accounting": (accounting.report()
                           if accounting is not None else None),
            "maintenance": dict(MAINTENANCE_NOTE),
            "boundary": {
                "equal_updates_across_conditions": (
                    "8 per round and 128 in total at every depth: eight passes are "
                    "eight sample passes and one update"),
                "unequal_compute_across_conditions": (
                    "the recurrent condition performs 3.75 times the sample-level "
                    "transformation passes; equal teaching exposure is not equal "
                    "training compute and this report never calls it equal"),
                "automatic_retries": 0}}


# --------------------------------------------------------------------------
# what exists, and what does not
# --------------------------------------------------------------------------

def readiness_report():
    """Implemented / partial / declared-choice / absent, each with its artefact.

    Per the CNCM completion rule: a passing narrow test is not proof that the
    candidate exists, so nothing here is offered as one.
    """
    return {
        "candidate": "CAS_RDCJT_001",
        "status": "RECURRENT_CJT_READY_NEURAL_UNTESTED",
        "implemented": {
            "shared_core_recurrence": "cas_meta2/recurrent_cjt/recurrence.py",
            "numerical_wrapper_that_does_not_detach":
                "cas_meta2/recurrent_cjt/learner.py: tensor_rms, cast hook",
            "learner_integration": ("cas_meta2/recurrent_cjt/learner.py: "
                                    "RecurrentGraphLearner over the SAME module, "
                                    "three scoring entrances overridden"),
            "one_update_per_batch_at_every_depth":
                "cas_meta2/recurrent_cjt/learner.py: recurrent_batch_step",
            "evaluation_depths": ("R1, R2, R4, R8, RESET_8 in "
                                  "learner.depth_sweep"),
            "variable_depth_course": "cas_meta2/recurrent_cjt/course.py: run_course",
            "course_bound_to_the_existing_schedule":
                "cas_meta2/recurrent_cjt/course.py: schedule_binding",
            "depth_one_is_the_existing_computation":
                "tests/test_recurrent_cjt_learner.py: bitwise equality at depth one",
        },
        "declared_choices_filling_declared_gaps": {
            "maintenance_event_source": MAINTENANCE_NOTE["status"],
        },
        "absent": {
            "fresh_family_panel_for_the_recurrent_test": (
                "the delivered rewired direct_inventory rows are examined material "
                "and cannot be the final test; a fresh panel with the same subtype "
                "structure does not exist yet"),
            "packaged_worker_and_entrypoint_for_the_recurrent_candidate": (
                "no versioned entrypoint, no resource profile, no package"),
            "repository_frozen_digests_for_this_candidate": (
                "the encoder and checkpoint digests are frozen for the readout "
                "candidate, not for this one"),
            "neural_execution": ("no GPU run has been performed or authorised; "
                                 "nothing in this status is a measurement of learning"),
            "costed_execution_request": ("no request, no authority, no reservation"),
        },
        "budget": {"reserved": "$375.00", "cap": "$400.00", "free": "$25.00",
                   "note": "nothing in this step spent or reserved anything"},
        "boundary": ("EVERY number in this candidate so far is derived arithmetic or "
                     "plumbing verification on a hand-built stand-in. None of it is a "
                     "measurement of learning, and none of it is evidence that more "
                     "passes help"),
    }
