"""The two declared teaching organizations, and their exact arithmetic.

**Phase A/B grounding sweeps** (``CUBE_FACE_GROUNDING_001``): 16 guided sweeps in
which every training family receives one ``FACE_APPLY`` query per role with three
worked supports, then 8 mixed sweeps - 4 ``ROLE_FROM_CONTENT`` and 4
``FACE_APPLY`` without supports.

    64 families x 6 roles x 16 sweeps = 6,144 queries
    supports: 3 per guided query          = 18,432 support presentations
    64 x 6 x 4 x 2 (mixed)                = 3,072 queries
    total queries                          = 9,216
    at batch 8                             = 1,152 optimizer updates

**The CFC loop** (``CFC_LOOP_001``): one round visits four focal cubes through
seven within-cube stages (28 decisions), compares six roles across those cubes
with two decisions each (12), and returns to each cube with two decisions (8) -
48 decisions per round, 6 cohorts x 16 rounds = 4,608 decisions.

Honest accounting, because the plan requires it rather than a convenient number:

* the schedule counts *query episodes*, and it does **not** silently relabel eight
  sequential updates as one minibatch update. ``UPDATES_IF_ONE_PER_EPISODE``
  states the cost of the unbatched path (9,216) beside the batched one (1,152),
  and the runner records which path it actually took;
* supports are counted separately from queries and are never counted as updates;
* a sweep over six roles is not a completed seven-stage neural cycle, and no
  counter here calls it one.
"""
from __future__ import annotations

import hashlib
import random

from .graph import canonical, digest, require
from . import face_corpus as corpus
from . import face_roles as roles
from . import face_tasks as tasks

SCHEMA = "cas.cube-face-schedule/0.1"

BATCH_SIZE = 8
PHASE_A_SWEEPS = 16
PHASE_B_RECOGNITION_SWEEPS = 4
PHASE_B_APPLICATION_SWEEPS = 4
SUPPORTS_PER_GUIDED_QUERY = 3
RECOGNITION_GROUP_OFFSETS = (1, 2, 3, 4, 5)

CFC_CUBES_PER_COHORT = 4
CFC_COHORTS = 6
CFC_ROUNDS = 16
CFC_WITHIN_STAGES = 7
CFC_ACROSS_DECISIONS_PER_ROLE = 2
CFC_RETURN_DECISIONS_PER_CUBE = 2

MOVEMENTS = ("WITHIN_CUBE", "ACROSS_FACE", "RETURN_TO_CUBE")

#: The seven within-cube stages and the face each one teaches. Stage 7 is
#: reinforcement - a whole-idea question - and it is **not** a seventh face.
STAGE_FACES = (
    {"stage": 1, "stage_id": "name_and_function", "face": 1},
    {"stage": 2, "stage_id": "context", "face": 2},
    {"stage": 3, "stage_id": "analogy", "face": 3},
    {"stage": 4, "stage_id": "explicit_mapping", "face": 4},
    {"stage": 5, "stage_id": "decomposition", "face": 5},
    {"stage": 6, "stage_id": "recomposition", "face": 6},
    {"stage": 7, "stage_id": "reinforcement", "face": 5,
     "note": "reinforcement is a whole-idea question, not a seventh face"},
)


def _seed_for(name):
    """A deterministic RNG seed from either a declared integer seed or a name.

    Attempt 003 died here: the runner passes the experiment's integer seed, this
    helper assumed a name string, and the mixed-order conditions raised
    ``TypeError: can only concatenate str (not "int") to str`` - after the encoder
    and both pre-training checks had already run. Both kinds are now accepted, and
    the suite builds *every* declared condition through the production call so a
    path only some conditions take cannot go unexercised again.
    """
    if isinstance(name, int) and not isinstance(name, bool):
        return name
    return int(digest(("cas.cube-face-schedule:" + str(name)).encode("utf-8"))[:8], 16)


def _rotated(items, offset):
    offset = offset % len(items)
    return list(items[offset:]) + list(items[:offset])


def training_families(built=None):
    built = corpus.families() if built is None else built
    return corpus.by_split(corpus.TRAINING, built)


def event_key(event):
    """A stable identity for one scheduled episode, from public fields only."""
    return "|".join((event["movement"], event["profile"],
                     event["family_id"], str(event["face"]),
                     ",".join(event.get("support_ids") or ()),
                     str(event.get("offset", 0))))


def _support_ids(family, face, offset, built):
    supports = tasks.choose_supports(family, face, offset=offset, built=built)
    return [support["family_id"] for support in supports]


def grounding_events(built=None):
    """Every scheduled grounding episode, in the frozen order.

    Sweep order rotates families, roles and support offsets, so no surface
    convention stays tied to a role; the order is a pure function of the declared
    seed and is therefore reproducible from the manifest alone.
    """
    built = corpus.families() if built is None else built
    families = training_families(built)
    events = []
    for sweep in range(PHASE_A_SWEEPS):
        for position, family in enumerate(_rotated(families, sweep)):
            for face in _rotated(list(roles.FACE_NUMBERS), sweep + position):
                offset = (sweep + position + face) % len(families)
                events.append({
                    "movement": "ACROSS_FACE", "phase": "A", "sweep": sweep,
                    "profile": roles.FACE_APPLY, "face": face,
                    "family_id": family["family_id"], "support_ids":
                        _support_ids(family, face, offset, built),
                    "offset": offset, "assisted": True})
    for sweep in range(PHASE_B_RECOGNITION_SWEEPS):
        for position, family in enumerate(_rotated(families, sweep + 1)):
            for face in _rotated(list(roles.FACE_NUMBERS), sweep + position):
                group = roles.other_faces(
                    face, tasks.OPTIONS_PER_QUESTION - 1,
                    RECOGNITION_GROUP_OFFSETS[
                        (sweep + position + face) % len(RECOGNITION_GROUP_OFFSETS)])
                events.append({
                    "movement": "ACROSS_FACE", "phase": "B", "sweep": sweep,
                    "profile": roles.ROLE_FROM_CONTENT, "face": face,
                    "family_id": family["family_id"], "support_ids": [],
                    "group": list(group), "assisted": False})
    for sweep in range(PHASE_B_APPLICATION_SWEEPS):
        for position, family in enumerate(_rotated(families, sweep + 2)):
            for face in _rotated(list(roles.FACE_NUMBERS), sweep + position + 1):
                events.append({
                    "movement": "RETURN_TO_CUBE", "phase": "B", "sweep": sweep,
                    "profile": roles.FACE_APPLY, "face": face,
                    "family_id": family["family_id"], "support_ids": [],
                    "offset": (sweep + position) % len(families),
                    "assisted": False})
    require(len(events) == planned_counts()["supervised_query_presentations"],
            "FACE_SCHEDULE_QUERY_COUNT")
    return events


def cfc_round_events(round_index, built=None):
    """One complete CFC round: within, across, then return, for four cubes."""
    built = corpus.families() if built is None else built
    families = training_families(built)
    cohort_index = round_index % CFC_COHORTS
    cohort = _rotated(families, cohort_index * CFC_CUBES_PER_COHORT)[
        :CFC_CUBES_PER_COHORT]
    events = []
    for cube_position, family in enumerate(cohort):
        for stage in STAGE_FACES:
            events.append({
                "movement": "WITHIN_CUBE", "stage": stage["stage"],
                "stage_id": stage["stage_id"], "round": round_index,
                "profile": roles.FACE_APPLY, "face": stage["face"],
                "family_id": family["family_id"],
                "support_ids": _support_ids(
                    family, stage["face"],
                    (round_index + cube_position + stage["stage"]) % len(families),
                    built) if stage["stage"] < 7 else [],
                "offset": cube_position, "assisted": True})
    for face in roles.FACE_NUMBERS:
        group = roles.other_faces(face, tasks.OPTIONS_PER_QUESTION - 1,
                                  (round_index + face) % len(
                                      RECOGNITION_GROUP_OFFSETS) + 1)
        events.append({
            "movement": "ACROSS_FACE", "decision": "role_recognition",
            "round": round_index, "profile": roles.ROLE_FROM_CONTENT, "face": face,
            "family_id": cohort[face % len(cohort)]["family_id"],
            "support_ids": [], "group": list(group), "assisted": False})
        events.append({
            "movement": "ACROSS_FACE", "decision": "content_comparison",
            "round": round_index, "profile": roles.FACE_APPLY, "face": face,
            "family_id": cohort[(face + 1) % len(cohort)]["family_id"],
            "support_ids": [], "offset": face, "assisted": False})
    for family in cohort:
        events.append({
            "movement": "RETURN_TO_CUBE", "decision": "missing_face",
            "round": round_index, "profile": roles.FACE_APPLY, "face": 4,
            "family_id": family["family_id"], "support_ids": [],
            "offset": 0, "assisted": False})
        events.append({
            "movement": "RETURN_TO_CUBE", "decision": "whole_idea",
            "round": round_index, "profile": roles.FACE_APPLY, "face": 5,
            "family_id": family["family_id"], "support_ids": [],
            "offset": 1, "assisted": False})
    require(len(events) == planned_counts()["cfc_decisions_per_round"],
            "FACE_SCHEDULE_CFC_ROUND_COUNT")
    return events


def cfc_events(built=None):
    """Every CFC decision in the loop plan: cohorts x rounds x 48."""
    events = []
    for cohort_round in range(CFC_COHORTS * CFC_ROUNDS):
        events.extend(cfc_round_events(cohort_round, built))
    require(len(events) == planned_counts()["cfc_total_decisions"],
            "FACE_SCHEDULE_CFC_TOTAL")
    return events


def planned_counts():
    """The declared arithmetic, in one place, with both update accountings."""
    families = corpus.TRAINING_FAMILIES
    queries_a = families * len(roles.FACE_NUMBERS) * PHASE_A_SWEEPS
    supports_a = queries_a * SUPPORTS_PER_GUIDED_QUERY
    recognition_b = families * len(roles.FACE_NUMBERS) * PHASE_B_RECOGNITION_SWEEPS
    application_b = families * len(roles.FACE_NUMBERS) * PHASE_B_APPLICATION_SWEEPS
    queries_b = recognition_b + application_b
    queries = queries_a + queries_b
    cfc_per_round = (CFC_CUBES_PER_COHORT * CFC_WITHIN_STAGES
                     + len(roles.FACE_NUMBERS) * CFC_ACROSS_DECISIONS_PER_ROLE
                     + CFC_CUBES_PER_COHORT * CFC_RETURN_DECISIONS_PER_CUBE)
    return {
        "schema": SCHEMA,
        "batch_size": BATCH_SIZE,
        "training_families": families,
        "roles": len(roles.FACE_NUMBERS),
        "phase_a_sweeps": PHASE_A_SWEEPS,
        "phase_a_queries": queries_a,
        "phase_a_support_presentations": supports_a,
        "phase_b_recognition_sweeps": PHASE_B_RECOGNITION_SWEEPS,
        "phase_b_application_sweeps": PHASE_B_APPLICATION_SWEEPS,
        "phase_b_recognition_queries": recognition_b,
        "phase_b_application_queries": application_b,
        "phase_b_queries": queries_b,
        "supervised_query_presentations": queries,
        "worked_support_presentations": supports_a,
        "updates_at_declared_batch": queries // BATCH_SIZE,
        "UPDATES_IF_ONE_PER_EPISODE": queries,
        "batching_note": (
            "the plan's 1,152 updates presuppose minibatches of 8 independent "
            "query episodes. One optimizer step per episode is the unbatched path "
            "and costs 9,216 updates; eight sequential updates are not one "
            "minibatch update and are never relabelled as one."),
        "cfc_cubes_per_cohort": CFC_CUBES_PER_COHORT,
        "cfc_decisions_per_round": cfc_per_round,
        "cfc_cohorts": CFC_COHORTS,
        "cfc_rounds": CFC_ROUNDS,
        "cfc_total_decisions": cfc_per_round * CFC_COHORTS * CFC_ROUNDS,
        "seven_stage_cycles_note": (
            "a sweep over six roles is not a completed seven-stage neural cycle; "
            "no counter in this profile calls it one"),
        "support_rule": ("supports are worked examples from other training "
                         "families and are counted separately from queries"),
    }


def schedule_report(built=None):
    counts = planned_counts()
    events = grounding_events(built)
    by_phase = {}
    by_profile = {}
    by_role = {}
    supported = 0
    for event in events:
        by_phase[event["phase"]] = by_phase.get(event["phase"], 0) + 1
        by_profile[event["profile"]] = by_profile.get(event["profile"], 0) + 1
        by_role[str(event["face"])] = by_role.get(str(event["face"]), 0) + 1
        if event["support_ids"]:
            supported += 1
    return {
        "schema": SCHEMA,
        "counts": counts,
        "materialised_events": len(events),
        "events_by_phase": by_phase,
        "events_by_profile": by_profile,
        "events_by_role": by_role,
        "events_with_supports": supported,
        "cfc_round_movements": {
            "within_cube": CFC_CUBES_PER_COHORT * CFC_WITHIN_STAGES,
            "across_face": len(roles.FACE_NUMBERS) * CFC_ACROSS_DECISIONS_PER_ROLE,
            "return_to_cube": CFC_CUBES_PER_COHORT * CFC_RETURN_DECISIONS_PER_CUBE},
        "batch_arithmetic_holds": (
            counts["supervised_query_presentations"] % BATCH_SIZE == 0
            and counts["updates_at_declared_batch"] * BATCH_SIZE
            == counts["supervised_query_presentations"]),
    }


def mixed_order(events, seed="cfc-mixed-order-control"):
    """The same events in a fixed shuffled order.

    Every learning event, its supports, its targets and its counts are unchanged;
    only the organization differs, which is what the loop comparison asks about.
    The permutation is a pure function of the seed and the event identities, so it
    is reproducible and identical for both cue arms.
    """
    ordered = list(events)
    keys = [event_key(event) for event in ordered]
    random.Random(_seed_for(seed)).shuffle(ordered)
    require(sorted(event_key(event) for event in ordered) == sorted(keys),
            "FACE_SCHEDULE_MIXED_ORDER_CHANGED_EVENTS")
    return ordered


def cue_arm_events(events, arm):
    """The same events with the cue arm fixed; nothing else changes."""
    require(arm in ("stable", "neutral"), "FACE_SCHEDULE_ARM_UNKNOWN:" + str(arm))
    return [dict(event, arm=arm) for event in events]


def comparison_conditions():
    """The four arms the two plans ask about, and why each exists."""
    return (
        {"condition": "cfc_stable_cues", "organization": "CFC_LOOP",
         "cue": "stable",
         "question": "does the loop teach, with the numbered handle present?"},
        {"condition": "cfc_neutral_cue", "organization": "CFC_LOOP",
         "cue": "neutral",
         "question": "does the numbered handle add value inside the loop?"},
        {"condition": "mixed_order_stable_cues", "organization": "MIXED_ORDER",
         "cue": "stable",
         "question": "does the alternation beat the same events in mixed order?"},
        {"condition": "mixed_order_neutral_cue", "organization": "MIXED_ORDER",
         "cue": "neutral",
         "question": "the four-cell control; both plans' controls in one job"},
    )


def condition_events(condition, organization, arm, seed=None, built=None):
    """The event list for one condition: same events, one organization, one cue arm."""
    events = (grounding_events(built) if organization == "GROUNDING"
              else cfc_events(built))
    if organization == "MIXED_ORDER":
        events = mixed_order(events, seed or "cfc-mixed-order-control")
    return cue_arm_events(events, arm)


def schedule_digest(events):
    """A digest of one condition's exact event list, for the manifest."""
    return digest(canonical([event_key(event) for event in events]))
