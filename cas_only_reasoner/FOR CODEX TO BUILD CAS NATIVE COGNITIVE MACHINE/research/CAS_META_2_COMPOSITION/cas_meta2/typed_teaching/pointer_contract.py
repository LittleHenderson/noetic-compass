"""Pure admission for the pointer study: does a machine that points at the question's own input learn
answers about worlds it never read?

Owner-approved 2026-09-19: option 1, "pointer answers plus the checkpoint check", after both corrections
were accepted. The course, the hold-out, the teaching order and the random start are the practice study's,
reused BY IMPORT and never re-derived, so the two studies are comparable question for question. What changes
is the machine's relation to its input: one focus world is read as a small directed graph, the question is
expressed by pointing at that graph's nodes, and the answer is a pointer into the input instead of a label
drawn from a fixed bank. No teacher, final panel, numerical runtime or provider is imported here.

THIS TREE IS THE CRITICAL-MASS 2x VERSION (`EXPERIMENT_VERSION`): the registered training duration is 20
passes, twice R18's measured 10, and the science around it is R18's unchanged -- see the version block below
`SOURCE_SEED`. Passes 10 and 20 are both evaluated and neither is selected over the other.

DELIBERATE OPEN ITEMS, each written as a mechanism waiting for a measured decision, never guessed:

* ``REMOVALS`` -- the per-question lists already solved by a registered flag rule (review FP2) or by a
  registered rank/order rule (review DG3). It is an explicit, typed, currently EMPTY placeholder. While it
  is empty, ``relational_population`` refuses to be read as a finished population
  (``RELATIONAL_POPULATION_UNRECONCILED``).
* ``MAIN_COUNTERS`` -- the pointer machine's own counter key set (INTERFACE_SPEC_POINTER section 1). The
  planned-work FORMULA is registered in ``DESIGN["planned_work"]``; the key set is not guessed.
* Two decisions moved AFTER the interface spec was written at HEAD ``7276f4f2``, and this module carries
  them as recorded status rather than as settled choices: HEAD ``6cb0b348`` reopens the node rank decision
  (a rank-only single-flag rule eats 4 of the 9 eligible held ``reach`` questions), and
  ``DESIGN_DRAFT_v0.2.md`` section 6.4 measures that the input's own ``contains`` adjacency already answers
  every eligible held ``parts`` and ``edge_account`` question with no learned weights. Both narrow the
  RELATIONAL tier, so they are lens A / owner decisions, not this file's.

THE SINGLE PASS IS STRATIFIED. Owner decision 2026-09-19: option 2 of the LB11 question, "Stratify AND
train longer (Recommended)". The owner's words for that option are recorded verbatim in
``DESIGN["owner_approval"]``. ``STRATIFIED`` below is that decision as a module constant and
``pointer_schedule`` defaults to it.

WHY, WITH THE MEASUREMENT (records/typed_pointer_001/pre_design/REVIEW_SYNTHESIS.md section 4.7, measured
by ``lb11_economics.py``; the raw reading is its ``lb11_economics_out.txt``). The practice schedule's MIXED
course spends each of its 147 updates on a handful of kinds and leaves the rest out, so most per-kind heads
receive no gradient at all in most updates. As-is, a kind is ABSENT from this many of the 147 updates of a
pass: role_set 115, analogy 112, context 107, definition 105, edge_account 95, correspondence 67, parts 63,
reach 40. That is the starvation behind the learnability lens's "rarest head sees a gradient in 320 of
1470". Stratifying -- one record of every one of the eight kinds in every update -- removes the absence
entirely:

    branch                          updates/pass   presentations/pass   every kind every update?
    A as-is (practice MIXED)              147               818          no
    B stratified (this decision)          147             1176          yes   (+43.8 %)
    C widened (the lens's literal)        470             3760          yes   (+359.7 %)

B costs +358 presentations per pass, 818 -> 1176, for 43.8 % more presentations AT THE SAME UPDATE COUNT.
It is affordable; the lens's literal reading is not. C multiplies presentations by 4.6x and its 10 passes
would need 4716 updates, above the raised ceiling of 3544, so C is refused as stated. The extra
presentations cost instance time only; the update count, and therefore the learned parameter trajectory's
length, is unchanged at 147 per pass.

THE PRACTICE SCHEDULE ITSELF IS UNTOUCHED. The stratified pass is this study's own, built here from the same
MIXED base batch slots; ``practice_contract.practice_schedule`` is still imported unchanged and
``stratified=False`` reproduces it byte for byte (test ``..._non_stratified_fidelity...``), so the two
studies stay comparable question for question.

THE GATE IS KEYED ON THE RELATIONAL TIER (review FP1): copying one input flag alone passes the practice
gate (definition 5 + context 5 held questions, b=10, c=0, p=0.0009765625), so a gain on the DIRECT_READ
kinds alone must never produce the primary label. The all-kinds result is a reported flag, never the label.

Why MATERIAL carries the eighteen practice checkpoints: the checkpoint check restores the three practice
checkpoints per seed and compares the registered ``^6`` sub-block, and the launch-time ``git_package_bytes``
scope admits ``records/`` paths only when the new contract lists them in MATERIAL (pipeline review RK5).
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import importlib.util
from pathlib import Path
import re

from . import course_plan, matched_contract as matched, practice_contract as practice, source

# `canonical` and `require` are the shared pair, so every failure raises `ValueError("TYPED_MATCHED:" + code)`.
canonical, require = matched.canonical, matched.require

CANDIDATE = "CNCM_TYPED_POINTER_LEARNING_001"
CONFIG_SCHEMA = "cncm.typed-pointer-worker-config/0.1"
STUDY_TOKEN = "tpntr"
JOB_PATTERN = r"cas-meta2-tpntr-\d{14}-([a-f0-9]{8})-m-(20260917|20260918|20260919)"
# Bucket = job + "-807562639912"; 63 characters is the maximum this pattern allows (RK4).
BUCKET_PATTERN = r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]"
BUCKET_SUFFIX = "-807562639912"

CONDITION = practice.CONDITION
MODEL_SEEDS = practice.MODEL_SEEDS
SOURCE_SEED, ENCODER_SEED = practice.SOURCE_SEED, practice.ENCODER_SEED
# ----------------------------------------------------------------------------------------------------------------
# VERSION. This tree is the CRITICAL-MASS 2x version of the pointer study: the registered full run trains
# TWICE as long as R18's, and nothing else about the science moves. `EXPERIMENT_VERSION` is the identity every
# record of this version carries (DESIGN, the worker config, the package manifest, the admission study record),
# so a 20-pass artifact can never be read as a 10-pass one. `VERSION_PASS_MULTIPLIER` says the ONLY axis of the
# change in one number: 2x the registered passes, 4x/8x deliberately NOT implemented.
#
# WHAT IS IDENTICAL TO R18, by import and by unchanged constant: the model and learner, the course, the
# held-back worlds and records, the stratified batch order, the optimizer and its settings, the 59-packet
# development panel, the private scorer, and the 564-record registry. See `_INHERITED` below, which is the
# pointer study's own list of fields copied unchanged from the matched study, and `DESIGN`, which adds only
# this version's own numbers on top of it.
EXPERIMENT_VERSION = "cncm.typed-pointer-critical-mass-2x/1"
VERSION_PASS_MULTIPLIER = 2
RUN_MODEL_SEED = 20260918
# ----------------------------------------------------------------------------------------------------------------
# TRAINING LENGTH IS A DELIBERATE, MEASURED CHOICE -- DO NOT INHERIT 10 PASSES BY DEFAULT.
#
# The practice study stopped at 10 passes with the loss still falling, monotonically, and having used only
# 5,465.811116 s of a 12,300 s worker deadline (44.4%). Ten passes was a protocol choice, not convergence.
# See records/typed_pointer_001/pre_design/LEARNING_LEVERS.md, which is the authority for this comment.
#
# The practice ceiling below was 2048, which caps this study at 13 passes
# (13 x 147 + 16 = 1927 <= 2048; 14 passes = 2074 and is REFUSED). Training length is the cheapest available
# improvement to the neurons, so that ceiling is RAISED here -- a new candidate is entitled to its own registered
# limit -- to permit up to MAX_PASSES_PERMITTED passes and no more.
#
# PASSES IS NOW SET, FROM A MEASUREMENT -- the decision this comment always demanded. The measurement is the
# DELIVERED R17 job (seed 20260917, 10 passes, `records/typed_pointer_001/receipt_analogy_on_20260917`,
# result `elapsed_seconds` 10,516.263135700006, worker clock 9,895.504149891001 s of a 12,300 s deadline, so
# 80.5 % of the deadline was used and the loss was still falling):
#
#     measured per update          7,197.795890278999 s / 1,470 updates = 4.896459789305442 s
#     measured per evaluation      1,088.1962510759972 s / 21            = 51.81886909885701 s
#     measured phase A             890.397366079 s over 3 checkpoints
#     measured worker-side glue    719.1146424570053 s
#     20 passes projected          719.1146424570053 + 2,940 x 4.896459789305442
#                                  + (18 regular + 5 ablation) x 51.81886909885701
#                                  + 890.397366079 = 17,196.937778367716 s worker clock
#     projected INSTANCE seconds   17,196.937778367716 + 598.1888835440004 (the measured non-worker overhead
#                                  this machine already carries) = 17,795.126661911716 s
#     projected cost               17,795.126661911716 / 3,600 x 2.5200000000 + 1.48 = $13.94
#
# The core-call budget is re-checked against the same measurement, as this comment requires: 20 passes x 1,176
# presentations x 8 rounds = 188,160 core calls against the registered 600,000 MAX_CORE_CALLS (31.4 %), so the
# update budget (2,940 + 16 = 2,956 of 3,544) binds first and neither is close. Both are recorded in DESIGN.
# ----------------------------------------------------------------------------------------------------------------
PASSES = 20                        # = VERSION_PASS_MULTIPLIER x practice.PASSES, set from the measurement above
# PASS 10 AND PASS 20 ARE BOTH EVALUATED. 10 keeps the R18 comparison point (state at the duration R18 ran);
# 20 is this version's own final state. No best-checkpoint selection: both are written, both are scored, and
# the gate reads pass 20 (the registered final pass) exactly as it read pass 10 before.
PASS_CHECKPOINTS = (0, 1, 2, 4, 6, 8, 10, 20)
FULL_COURSE_CHECKPOINTS = (0, 1, 10, 20)
INTERFERENCE_UPDATES, INTERFERENCE_BATCH = practice.INTERFERENCE_UPDATES, practice.INTERFERENCE_BATCH
REPLAY_UPDATES = practice.REPLAY_UPDATES
MAX_PASSES_PERMITTED = 24
LEARNER_MAX_UPDATES_CEILING = MAX_PASSES_PERMITTED * 147 + INTERFERENCE_UPDATES   # 3544, permits 24 passes
MAX_CORE_CALLS = practice.MAX_CORE_CALLS
# ----------------------------------------------------------------------------------------------------------------
# THE RESOURCE ENVELOPE, RE-DERIVED FROM A USD 20.00 ALL-SERVICES CAP AND NOTHING ELSE.
#
# The observed on-demand rate is $2.5200000000/h for g7.2xlarge in us-west-2 and the ancillary allowance this
# launcher reserves is $1.48 (both carried unchanged from R18/R17). The binding rule is the ledger's own:
# `budget.validate_plan` requires `reserved_usd >= rate x runtime_seconds_max / 3600 + ancillary`, so the
# reservation and the instance limit are one arithmetic decision:
#
#     instance_seconds_max  25,200 s = 7 h exactly
#     declared cost bound   2.5200000000 x 7 + 1.48                        = $19.12
#     reservation           19.20  (>= the bound; the ledger's rule above)  = $19.20
#     other services        0.10 allowance                                 = $0.10
#     ALL SERVICES          19.20 + 0.10                                    = $19.30  <= $20.00
#
# The limit is 1.42 x the projected instance seconds above, close to R18's safety ratio (14,400 / 10,234.598687940716
# = 1.41); it is NOT tightened to the projection because a killed run is paid for and returns nothing.
# The deadline chain below keeps R18's own spreads (300 / 900 / 600 / 300 s) and its 2,100 s of total
# non-worker envelope slack, so the ordering checks in `aws/typed_pointer_launch.py` still hold:
#     23,100 < 23,400 < 24,300 < 24,900 < 25,200  and  7,200 < 24,900 < 25,200
# ----------------------------------------------------------------------------------------------------------------
WORKER_DEADLINE_SECONDS = 23100
MAX_WALL_SECONDS = 23400
RESERVATION_USD = "19.20"
INSTANCE_SECONDS_MAX = 25200

# ----------------------------------------------------------------------------------------------------------------
# STRATIFIED. The owner's decision of 2026-09-19, recorded verbatim in `DESIGN["owner_approval"]`: the option
# labelled "Stratify AND train longer (Recommended)". It is a module constant because `pointer_schedule` defaults to
# it; `stratified=False` is the only way back to the practice study's own unstratified order.
#
# THE MEASUREMENT IT ANSWERS (REVIEW_SYNTHESIS.md section 4.7, measured by pre_design/lb11_economics.py, raw reading
# in pre_design/lb11_economics_out.txt). The as-is MIXED pass of 147 updates leaves each kind ABSENT from this many
# updates: role_set 115, analogy 112, context 107, definition 105, edge_account 95, correspondence 67, parts 63,
# reach 40 -- so a role_set head receives a gradient in 32 of 147 updates and an analogy head in 35. In the
# stratified pass every kind is present in every update: 0 absences for all eight, still 147 updates, at
# presentations_per_pass 1176 against 818, i.e. +358 presentations and +43.8 %. The lens's literal reading of the
# same instruction (+359.7 %, 3760 presentations per pass) would need 4716 updates over ten passes, above this
# contract's ceiling of 3544, and is refused as stated. Both branches are implemented so the comparison stays
# re-runnable and the fidelity property below stays testable.
# ----------------------------------------------------------------------------------------------------------------
STRATIFIED = True

# THE TWO DIGESTS OF THE STRATIFIED SCHEDULE. They are two different KINDS of constant, and that difference is
# what adversarial review R2 item M4 found wrong here (fixed 2026-09-19):
#
#   * STRATIFIED_PASS_DIGEST -- the SINGLE stratified pass, the digest of the slot list `_stratified_pass`
#     returns with its generated ids. It is PASS-COUNT INDEPENDENT by construction, so `pointer_schedule`
#     recomputes it on every call and refuses to return a schedule whose composition has silently moved
#     (`POINTER_STRATIFY_DIGEST`). A frozen literal is the right thing for this one.
#   * STRATIFIED_BATCHES_DIGEST -- the WHOLE default schedule. This one is a FUNCTION OF `PASSES`: the pass
#     number is inside every occurrence id and every presentation id, so a different pass count is a different
#     schedule with a different digest. It is therefore DERIVED at import time from whatever `PASSES` is, in
#     the block below `CNCM`, and is never written down as a literal.
#   * STRATIFIED_BATCHES_DIGEST_AT_10_PASSES -- the ten-pass literal, KEPT FOR THE RECORD: the identity
#     measured 2026-09-19 on this frozen course, and the evidence that a different pass count really does give
#     a different digest. It is checked against the derivation at import (at EVERY pass count, not only at ten)
#     and again by `tests/test_typed_pointer_study.py` and `records/typed_pointer_001/holdout_audit.py`.
#
# WHY THE WHOLE-SCHEDULE DIGEST MAY NOT BE FROZEN. Protocol section 6
# (`docs/CNCM_TYPED_POINTER_STUDY_v0.1.md:686-699`) requires `PASSES` to be set from the AWS smoke job's
# MEASURED per-update cost, and `PASSES` above inherits the practice study's ten as a STARTING POINT only.
# Freezing `1c67edd7...` as `STRATIFIED_BATCHES_DIGEST` made this contract contradict itself: the moment
# `PASSES` was set as the protocol demands, the test that pinned it went red and `holdout_audit.py` exited 1
# with `SOURCE_SCHEDULE_IS_NOT_THE_BASE_SCHEDULE` -- a MISLEADING failure that looks like a real schedule
# problem and would stall a launch the owner has already pre-approved.
#
# The practice digest for comparison stays
# `daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857` at ten passes (`stratified=False`).
TEN_PASSES = 10                     # the practice study's own count: what the recorded literal below measured
STRATIFIED_BATCHES_DIGEST_AT_10_PASSES = "1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304"
STRATIFIED_PASS_DIGEST = "80ae7121ff75f687e9c6c88593e2ed7d3f6024173d3577243ed05049c8859056"

# Reused UNCHANGED by import: the hold-out must stay byte-identical to the practice study (test P1).
digest = source.digest
split = practice.split
held_worlds = practice.held_worlds
held_back_questions = practice.held_back_questions
practice_schedule = practice.practice_schedule    # kept for reference/tests; use pointer_schedule below
KINDS = practice.KINDS                           # the eight kinds, same tuple, same order, taken BY IMPORT


def _kind_pools(frozen):
    """`{kind: sorted trained record ids of that kind}` -- the pools the stratified round-robin draws from.

    Empty pool is impossible on the frozen course (a test drives the refusal instead), but it is refused rather
    than silently producing a short batch, because a short batch is exactly the defect this schedule fixes.
    """
    trained = set(split(frozen)[1])
    pools = {kind: sorted(row["record_id"] for row in frozen["registry"]
                          if row["query"]["kind"] == kind and row["record_id"] in trained)
             for kind in KINDS}
    missing = [kind for kind in KINDS if not pools[kind]]
    require(not missing, "POINTER_STRATIFY_POOL:" + ",".join(missing))
    return pools


def _non_stratified_pass(frozen, base, keep_set):
    """The practice study's own single pass, clone for clone: `practice_contract.py:135-144` verbatim.

    Byte-identical to the practice construction on purpose (test P1 / the fidelity test): same slot skip rule,
    same five carried keys, same per-record filtering of every id list.
    """
    one_pass = []
    for batch in base:
        keep = [at for at, key in enumerate(batch["record_ids"]) if key in keep_set]
        if not keep:
            continue
        one_pass.append({"round": batch["round"], "phase": batch["phase"], "depth": batch["depth"],
                         "source_cursor": batch["cursor"],
                         "record_ids": [batch["record_ids"][at] for at in keep],
                         "occurrence_ids": [batch["occurrence_ids"][at] for at in keep],
                         "presentation_ids": [batch["presentation_ids"][at] for at in keep]})
    return one_pass


def _stratified_pass(frozen, base, keep_set):
    """One pass in which every batch carries ALL EIGHT KINDS: eight records, one per kind.

    Owner decision 2026-09-19. Built from the SAME MIXED base batch slots the practice study uses, so the depth
    distribution, the phase structure and the round numbering are the base's and unchanged; only the membership
    and the ids are this study's.

      * slot selection is the same rule as the practice pass -- every base slot holding at least one TRAINED
        record -- so the update count stays 147 per pass;
      * inside a slot, exactly one record per kind is taken from that kind's TRAINED pool (sorted), chosen by a
        deterministic round-robin cursor over that pool that persists across slots within the pass, which is
        `lb11_economics.py`'s branch B and the measurement REVIEW_SYNTHESIS section 4.7 reports as
        presentations_per_pass 1176;
      * `round`, `phase`, `depth` and `source_cursor` come from the base batch (the requirement is explicit);
      * `occurrence_ids` and `presentation_ids` are generated from (slot index, kind index) alone, so they are
        reproducible without the base ids and are UNIQUE INSIDE A BATCH -- which is what this contract's own
        `OCCURRENCE_UNIQUE` check requires, and is all the pass loop's re-digest needs. They are formed in the
        practice schedule's own style: an occurrence id is the `typed-occurrence-` prefix and a 64-hex digest, and a
        presentation id is the pass prefix, an 8-hex slot token and the ordinal of the kind inside the batch. The
        pass loop below still re-digests every occurrence id per pass, so the per-pass mechanism is untouched.
    """
    slots = [batch for batch in base if any(key in keep_set for key in batch["record_ids"])]
    pools = _kind_pools(frozen)
    cursor = {kind: 0 for kind in KINDS}
    one_pass = []
    for index, batch in enumerate(slots):
        token = source.digest({"domain": "typed-pointer-stratified-v1", "slot": index})[:8]
        records, occurrences, presentations = [], [], []
        for at, kind in enumerate(KINDS):
            pool = pools[kind]
            records.append(pool[cursor[kind] % len(pool)])
            cursor[kind] += 1
            occurrences.append("typed-occurrence-" + source.digest({"domain": "typed-pointer-stratified-v1",
                                                                    "slot": index, "kind": kind}))
            presentations.append("pointer-stratified-%s-%02d" % (token, at))
        one_pass.append({"round": batch["round"], "phase": batch["phase"], "depth": batch["depth"],
                         "source_cursor": batch["cursor"], "record_ids": records,
                         "occurrence_ids": occurrences, "presentation_ids": presentations})
    require(len(one_pass) == len(slots), "POINTER_STRATIFY_SLOTS")
    return one_pass


def pointer_schedule(frozen, passes=None, stratified=None):
    """`passes` repetitions of the MIXED course, keeping only trained records. Returns (batches, stats).

    A faithful clone of `practice_contract.practice_schedule` (`practice_contract.py:130-172`) with TWO differences:
    the pass count is a parameter, and the update bound is THIS contract's ceiling rather than the practice one; and
    the single pass is STRATIFIED unless told otherwise.

    STRATIFIED (the default, owner decision 2026-09-19, module constant `STRATIFIED`). Every one of the eight kinds
    appears in every update at the SAME 147 updates per pass, which removes the per-kind starvation the as-is MIXED
    order has (role_set absent from 115 of 147 updates, analogy 112, context 107, definition 105, edge_account 95,
    correspondence 67, parts 63, reach 40 -- REVIEW_SYNTHESIS.md section 4.7). It costs +43.8 % presentations,
    818 -> 1176 per pass, and leaves the update count alone. The lens's literal fix (+359.7 %, 4716 updates over ten
    passes) is above this contract's 3544 ceiling and is refused as stated. See `_stratified_pass`.

    NOT STRATIFIED (`stratified=False`) MUST STAY BYTE-IDENTICAL TO TODAY, tested: the practice path, unchanged.
    With `passes == practice.PASSES` it reproduces the practice study's own `batches_digest` exactly,
    `daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857`, and its `updates_per_pass` 147 and
    `presentations_per_pass` 818. So the per-pass construction, the occurrence-id digest domain and the
    presentation-id prefix on that branch are deliberately kept identical to the practice study's; only the number of
    repetitions is a parameter. A different pass count therefore produces a different `batches_digest`, which is
    expected and must be recorded in the protocol.

    Why the pass count exists at all: the practice function hard-codes `PASSES = 10` and then enforces
    `main_updates + INTERFERENCE_UPDATES <= practice.LEARNER_MAX_UPDATES_CEILING`, which is 2048. That caps the study
    at 13 passes and refuses 14. Training length is the cheapest available improvement to the neurons -- the practice
    run stopped at pass 10 with the loss still falling and 44.4 % of its deadline unused -- so the pointer study must
    be able to run longer. See `pre_design/LEARNING_LEVERS.md`.

    `CLOSED:` the value of `PASSES` itself is 20, set from the DELIVERED R17 job's MEASURED per-update cost -- see
    the measurement block beside `PASSES` above -- and the stratified whole-schedule digest below is derived from
    it rather than frozen as a literal.
    """
    count = PASSES if passes is None else passes
    layered = STRATIFIED if stratified is None else stratified
    require(type(layered) is bool, "POINTER_STRATIFIED_FLAG:" + type(layered).__name__)
    require(type(count) is int and 1 <= count <= MAX_PASSES_PERMITTED,
            "POINTER_PASSES_BOUND:" + str(count))
    base, base_stats = matched.schedule(frozen, CONDITION)
    held, trained, excluded = split(frozen)
    keep_set = set(trained)
    one_pass = (_stratified_pass(frozen, base, keep_set) if layered
                else _non_stratified_pass(frozen, base, keep_set))
    if layered:
        # Fail closed on composition drift: the stratified pass is a frozen artifact, so it may not silently
        # change under a re-derivation. This is pass-count independent, so it costs one digest per call.
        require(source.digest(one_pass) == STRATIFIED_PASS_DIGEST, "POINTER_STRATIFY_DIGEST")
        kinds_of = {row["record_id"]: row["query"]["kind"] for row in frozen["registry"]}
        require(all(len(b["record_ids"]) == len(KINDS)
                    and {kinds_of[key] for key in b["record_ids"]} == set(KINDS) for b in one_pass),
                "POINTER_STRATIFY_COVERAGE")
    batches = []
    for number in range(1, count + 1):
        for batch in one_pass:
            occurrences = ["typed-occurrence-" + source.digest({"domain": "typed-practice-v1", "pass": number,
                                                               "occurrence": occurrence})
                           for occurrence in batch["occurrence_ids"]]
            batches.append({**deepcopy(batch), "cursor": len(batches), "pass": number,
                            "occurrence_ids": occurrences,
                            "presentation_ids": ["practice-p%02d-%s" % (number, p)
                                                 for p in batch["presentation_ids"]]})
    require(all(key in keep_set for b in batches for key in b["record_ids"]), "HOLDOUT_TRAINED")
    require(all(len(b["occurrence_ids"]) == len(set(b["occurrence_ids"])) for b in batches), "OCCURRENCE_UNIQUE")
    counts = matched._slot_counts(frozen)
    held_ids = set(held)
    stats = {"condition": CONDITION, "source_seed": SOURCE_SEED, "passes": count, "holdout_unit": "FOCUS_WORLD",
             "held_worlds": held_worlds(frozen), "updates_per_pass": len(one_pass), "main_updates": len(batches),
             "presentations_per_pass": sum(len(b["record_ids"]) for b in one_pass),
             "presentations": sum(len(b["record_ids"]) for b in batches),
             "planned_slot_core_passes": sum(counts[k] * b["depth"] for b in batches for k in b["record_ids"]),
             "presentation_slots": sum(counts[k] for b in batches for k in b["record_ids"]),
             "held_back_records": len(held), "trained_records": len(trained), "excluded_records": len(excluded),
             "held_back_questions": len(held_back_questions(frozen)),
             "held_back_kinds": dict(sorted(Counter(r["query"]["kind"] for r in frozen["registry"]
                                                    if r["record_id"] in held_ids).items())),
             "held_back_record_ids_digest": source.digest(held), "excluded_record_ids_digest": source.digest(excluded),
             "source_schedule_digest": base_stats["batches_digest"], "batches_digest": source.digest(batches),
             "actual_compute_measured": False}
    require(0 < stats["main_updates"] + INTERFERENCE_UPDATES <= LEARNER_MAX_UPDATES_CEILING,
            "POINTER_UPDATE_BOUND:%d>%d" % (stats["main_updates"] + INTERFERENCE_UPDATES,
                                            LEARNER_MAX_UPDATES_CEILING))
    return deepcopy(batches), stats
interference_batches = practice.interference_batches
retention_packets = practice.retention_packets
development_packets = practice.development_packets
load_material = practice.load_material
public_packets = practice.public_packets
material_inputs = practice.material_inputs

# The three tiers, fixed before the run. Primary label: RELATIONAL. TEXT is reported, never labelled on.
DIRECT_READ = ("definition", "context")
RELATIONAL = ("parts", "edge_account", "reach", "correspondence", "analogy")
TEXT = ("role_set",)
TIERS = {"DIRECT_READ": DIRECT_READ, "RELATIONAL": RELATIONAL, "TEXT": TEXT}
require(sorted([*DIRECT_READ, *RELATIONAL, *TEXT]) == sorted(practice.KINDS)
        and len({*DIRECT_READ, *RELATIONAL, *TEXT}) == len(practice.KINDS), "TIERS_COVERAGE")

# Smallest b with 2**-b <= 0.01 at c = 0: 2**-7 = 0.0078125 <= 0.01 (test P12/design re-derives it).
MIN_PASSING_B = 7

# ---------------------------------------------------------------------------------------------------
# The 18 checkpoint pins, inlined from records/typed_pointer_001/pre_design/contract_pins/checkpoint_pins.json
# (generated by make_pins.py beside it; test P3 compares every value against that JSON).
#
# Inlined rather than read at import time ON PURPOSE: the pins JSON is not a MATERIAL entry, so a
# packaged worker would not be shipped it, and an import-time read would fail the whole job before any
# work was done. Keys are CNCM-root-relative and carry EXACTLY `bytes` and `sha256` (worker_contract.py:26-29).
# ---------------------------------------------------------------------------------------------------
CHECKPOINT_PINS = {
    "records/typed_practice_001/receipt_20260917/checkpoints/final.pt":
        {"bytes": 1717107, "sha256": "24686285c3618b2f352dc3f245bd82de1a2bb07e989c1082c6f57c3d891a333c"},
    "records/typed_practice_001/receipt_20260917/checkpoints/final_checkpoint.json":
        {"bytes": 22953, "sha256": "95e86d62a3ac70f21d523c232bb830330ca78992c0546a6c62c7316eaf55ea36"},
    "records/typed_practice_001/receipt_20260917/checkpoints/initial.pt":
        {"bytes": 1583505, "sha256": "0c1af5abb80cec2f67373fbf51c49d6e02f2edb4dc957de7bc8b9b494df98e7f"},
    "records/typed_practice_001/receipt_20260917/checkpoints/initial_checkpoint.json":
        {"bytes": 22913, "sha256": "b9d7712a23096baba2e2df9433a3f8d19778c0d0a0b17658ea297e66d08b7a30"},
    "records/typed_practice_001/receipt_20260917/checkpoints/pass_01.pt":
        {"bytes": 1717107, "sha256": "c562469a930818cef8a8d1eea3d9d986bb40c87023640424a45fa7cee19a97d4"},
    "records/typed_practice_001/receipt_20260917/checkpoints/pass_01_checkpoint.json":
        {"bytes": 22941, "sha256": "8f201e058c0a86d4b7820d679dc89769ee23f0db3b72e1175cb59249e753bfab"},
    "records/typed_practice_001/receipt_20260918/checkpoints/final.pt":
        {"bytes": 1717171, "sha256": "01cabdac9f1c01efe445859ae743aa50a7600e884fdc12a11803b49a8e0424e4"},
    "records/typed_practice_001/receipt_20260918/checkpoints/final_checkpoint.json":
        {"bytes": 22953, "sha256": "b4342a8ce3b2775ef617f51ab98fcc4f7f921f922378f1a023edebf13db26067"},
    "records/typed_practice_001/receipt_20260918/checkpoints/initial.pt":
        {"bytes": 1583569, "sha256": "21e8758c7ec5b37da2bf741b714a2a958303f0ba20962697e410cf800382c6b3"},
    "records/typed_practice_001/receipt_20260918/checkpoints/initial_checkpoint.json":
        {"bytes": 22914, "sha256": "93abe51582d0b93ebe2579546801259f458823c57c7aaf0c8fc6a4e150e77e90"},
    "records/typed_practice_001/receipt_20260918/checkpoints/pass_01.pt":
        {"bytes": 1717107, "sha256": "460250c30a7e96b8eb0f426a16ffb2b070b493d969e427a3c7feb22e9e82a091"},
    "records/typed_practice_001/receipt_20260918/checkpoints/pass_01_checkpoint.json":
        {"bytes": 22946, "sha256": "09e90c83dcfc17335f82868393aedb14eb3df9aa3b5a60fb708c09bfef08ec52"},
    "records/typed_practice_001/receipt_20260919/checkpoints/final.pt":
        {"bytes": 1717107, "sha256": "9cca11430a0488bb8e211f8adf291999f179ae8d20a95631145d4f40763422b9"},
    "records/typed_practice_001/receipt_20260919/checkpoints/final_checkpoint.json":
        {"bytes": 22953, "sha256": "c1ac9c3b783d2a7c02295270fb51e20177f5b30a2725c8334f1d4e1b94fae17b"},
    "records/typed_practice_001/receipt_20260919/checkpoints/initial.pt":
        {"bytes": 1583569, "sha256": "90cb22f297f4e8fe9e3585e9fa74ab6565f47fafa81d8941341a2b091d4de656"},
    "records/typed_practice_001/receipt_20260919/checkpoints/initial_checkpoint.json":
        {"bytes": 22914, "sha256": "7e3d9386ee9b36d1b51f9573d3cf56a1eb52b242a2b7f2b012ecfb9e1967d182"},
    "records/typed_practice_001/receipt_20260919/checkpoints/pass_01.pt":
        {"bytes": 1717107, "sha256": "31334ab72bbaad57d15a8557bb4ca7e36e2ad8181732281f4520f3e412fd2f87"},
    "records/typed_practice_001/receipt_20260919/checkpoints/pass_01_checkpoint.json":
        {"bytes": 22941, "sha256": "b58e8a3feda8957f9b649c7e68d30b36f9e95ac0c055a6beb2aee5dd616e7f30"},
}
CHECKPOINT_PINS_COUNT = 18
CHECKPOINT_PINS_BYTES = 15259777
require(len(CHECKPOINT_PINS) == CHECKPOINT_PINS_COUNT, "CHECKPOINT_PINS_COUNT")
require(all(set(pin) == {"bytes", "sha256"} for pin in CHECKPOINT_PINS.values()), "CHECKPOINT_PIN_KEYS")
require(sum(pin["bytes"] for pin in CHECKPOINT_PINS.values()) == CHECKPOINT_PINS_BYTES, "CHECKPOINT_PINS_BYTES")
require(not set(CHECKPOINT_PINS) & set(practice.MATERIAL), "CHECKPOINT_PINS_OVERLAP")

# practice.MATERIAL plus the 18 checkpoint rows. Nothing else is added and no row gains a key.
MATERIAL = {**deepcopy(practice.MATERIAL), **deepcopy(CHECKPOINT_PINS)}
require(set(CHECKPOINT_PINS) <= set(MATERIAL) and len(MATERIAL) == 21, "CHECKPOINT_PINS_MATERIAL")
require(all(set(row) == {"bytes", "sha256"} for row in MATERIAL.values()), "MATERIAL_ROW_KEYS")


def _checkpoint_rows(root):
    """The 18 shipped checkpoints read off disk and re-checked against their pins, as inventory rows."""
    rows = []
    for name in sorted(CHECKPOINT_PINS):
        path = Path(root) / name
        require(path.is_file() and not path.is_symlink(), "MATERIAL_PATH:" + name)
        raw = path.read_bytes()
        require(len(raw) <= matched.MAX_MEMBER_BYTES, "INPUT_MEMBER_BOUND:" + name)
        row = {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
        require({key: row[key] for key in ("bytes", "sha256")} == CHECKPOINT_PINS[name], "MATERIAL_BYTES:" + name)
        rows.append(row)
    return rows


def input_inventory(root):
    """practice.input_inventory(root) plus the 18 checkpoint rows, sorted by path, bound re-checked.

    Without the checkpoint rows the launch-time package scope rejects the files the checkpoint check needs
    (`PRACTICE_SOURCE_MEMBER_SCOPE`, pipeline review RK5).
    """
    root = Path(root).resolve(strict=True)
    rows = [*practice.input_inventory(root), *_checkpoint_rows(root)]
    rows.sort(key=lambda row: row["path"])
    require(len({row["path"] for row in rows}) == len(rows), "INPUT_ROW_IDENTITY")
    require(len(rows) <= 2000 and sum(row["bytes"] for row in rows) <= 96 * 1024 ** 2, "INPUT_TOTAL_BOUND")
    return rows


# ---------------------------------------------------------------------------------------------------
# The pointer machine's planned work. DG10: the practice study's DESIGN carries OLD-MACHINE work counts
# (`planned_slot_core_passes` 124510, `presentation_slots` 32280) that this machine does not have, so its
# own formula is registered here instead: one packet forward per presentation, and K shared
# message-passing rounds per packet regardless of the batch's depth (DG1).
# `relations` is the formula in machine-readable form: result = schedule_stat x multiplier. The result
# names are provisional; the OPEN decision `MAIN_COUNTERS` fixes the key set that the learner must match.
# ---------------------------------------------------------------------------------------------------
PLANNED_WORK_ROUNDS = 8
PLANNED_WORK = {
    "unit": "PACKET_FORWARD",
    "rounds": PLANNED_WORK_ROUNDS,
    "relations": (
        ("packet_forward_calls", "presentations", 1),
        ("core_forward_calls", "presentations", PLANNED_WORK_ROUNDS),
        ("core_forward_attempts", "presentations", PLANNED_WORK_ROUNDS),
        ("sample_core_passes", "presentations", PLANNED_WORK_ROUNDS),
        ("prediction_calls", "presentations", 1),
        ("private_loss_plan_calls", "presentations", 1),
        ("staged_batches", "main_updates", 1),
        ("backward_attempts", "main_updates", 1),
        ("backward_calls", "main_updates", 1),
        ("optimizer_step_attempts", "main_updates", 1),
        ("optimizer_updates", "main_updates", 1),
    ),
}

# CLOSED 2026-09-19. The pointer machine's own counter key set, and the ONE shared source of truth.
#
# `typed_practice_worker.py:361` compares the canonical bytes of the summed per-update deltas, and
# `counter_delta` (`typed_course_worker.py:55-59`, "COUNTER_FIELDS") requires the two snapshots' key sets to
# match EXACTLY, so one extra or missing key fails MAIN_TRAINING_COUNTERS after the spend. The set below is
# copied from `pointer_learner.COUNTER_KEYS`, which is where the learner builds its `counters` dict; a test
# asserts the two are equal, because the contract cannot import the learner without a cycle.
#
# The units are the POINTER machine's own: packet forwards, rounds times packets, and updates -- NOT the old
# machine's per-slot core passes (review DG10). A packet forward is one presentation; each forward runs
# PLANNED_WORK_ROUNDS rounds of message passing, so the core ledger is rounds x packets. On the frozen
# stratified schedule that is 1176 presentations per pass x 8 = 9408 core calls per pass, i.e. 94080 over ten
# passes against the registered 600000 MAX_CORE_CALLS -- the reconciliation the smoke job must confirm.
#
# Note `slot_forwards`, the old machine's per-slot counter, is deliberately NOT here: the pointer machine has
# no per-slot forward.
# The ORDER is the learner's, deliberately: a test asserts this tuple EQUALS `pointer_learner.COUNTER_KEYS`,
# and equal tuples are a stronger claim than equal sets. Nothing depends on the order at runtime --
# `expected_main_delta` returns a dict and `counter_delta` compares key SETS -- but a claim of one shared source
# of truth should be literally true rather than true-up-to-permutation.
MAIN_COUNTERS = ("core_forward_attempts", "core_forward_calls", "sample_core_passes",
                 "packet_forward_calls", "prediction_calls", "staged_batches", "backward_attempts",
                 "backward_calls", "optimizer_step_attempts", "optimizer_updates",
                 "private_loss_plan_calls")


def expected_main_delta(stats):
    """The planned work of the main-training phase, from the registered formula and the closed counter set."""
    require(MAIN_COUNTERS is not None, "MAIN_COUNTERS_OPEN")
    require(type(MAIN_COUNTERS) is tuple and len(set(MAIN_COUNTERS)) == len(MAIN_COUNTERS), "MAIN_COUNTERS")
    by_name = {name: stats[key] * multiplier for name, key, multiplier in PLANNED_WORK["relations"]}
    require(set(MAIN_COUNTERS) == set(by_name), "MAIN_COUNTERS")
    return {name: by_name[name] for name in MAIN_COUNTERS}


# ---------------------------------------------------------------------------------------------------
# The gate population. OPEN: the frozen per-question list after the registered removals.
# REMOVALS is an explicit, typed, CURRENTLY EMPTY placeholder so a later agent fills in the measured
# lists without touching the logic below. Rule names are fixed: `flag_rule` (FP2) and `rank_rule` (DG3).
# ---------------------------------------------------------------------------------------------------
REMOVAL_RULES = ("flag_rule", "order_rule", "present_rule", "inexpressible")
# FROZEN 2026-09-19. Eleven removals across FOUR classes, and the classes are different kinds of thing:
#
#  * flag_rule, order_rule, present_rule -- SHORTCUT rules. A registered no-learning policy answers these, so a
#    gain there would not be evidence of learning. Ids printed by `lk6_gate_population_out.txt` lines 62, 65, 68
#    and copied here through `pre_design/freeze_removals.py` rather than retyped.
#  * inexpressible -- ARCHITECTURAL. The five `correspondence` questions are removed because the drafted head
#    CANNOT EXPRESS a bijection (LB12/LB13/LB15: 0 of 20 held correct; in 81 of 88 records no additive per-node
#    score over these inputs can prefer a correct answer). This is a limit of the head, not a shortcut, and
#    conflating the two would misdescribe why these questions left the gate. Correspondence is still run, scored
#    and published; it leaves the LABEL, not the study.
#
# With these applied the RELATIONAL gate population is 18 -- analogy 5, edge_account 5, parts 2, reach 6 -- with
# a digest of 4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d, re-derived and asserted in
# tests. Minimum passing b is 7, so the required share is 7/18 = 0.3889.
REMOVALS = {
    "flag_rule": {"parts": [
        "typed-query-4a0342c26f982758689611569bebd798f324a52a3b8ee25cb5f016b394e17509",
        "typed-query-6d9f6280ddb8dc463bfb557617353b7857fba6cfda057403516a79d8a5ec1249",
        "typed-query-a14f184d8f6cc4f3b80a87998515fe3c707c2dfb4f92a2358f1233fc43fba1d9"]},
    "order_rule": {"reach": [
        "typed-query-5850f9113bccb701f9bc1cd326758889b77cd0cb3f0a443181b9e1105c3f9e94",
        "typed-query-85a38565803471f8fe7867631871a54f1f5ba7d4be1ae01d8516d9b5af68e2c7"]},
    "present_rule": {"reach": [
        "typed-query-dde56958ee3398739016ce6152278d821a1691cb5875c191e9a42077da4b16f7"]},
    "inexpressible": {"correspondence": [
        "typed-query-06e475e2b15faf1f1171e023219499f3255033f2dd71e05c86388b733c3f6077",
        "typed-query-6122a0c6cf78338961e9fd54efca446b1b31a74eddcc0e9f9480a1acc62b37c4",
        "typed-query-9b29b95ce429d36bf88bd5d301f0e146d178dd21b20bada78641e29dae9793e8",
        "typed-query-a6316d425dd26e46b9898a510e4e90dead89e882c57b444d44014a59c4de29e0",
        "typed-query-b291ebd18e0a4ea355ee1e08b1f82ba6e934c4e68cd4252691acbd86dc437a86"]},
}
# The verified eligible composition (measured 2026-09-19). 45 eligible = 10 DIRECT_READ + 29 RELATIONAL
# + 6 role_set; the 29 are correspondence 5, edge_account 5, reach 9, analogy 5, parts 5.
VERIFIED_ELIGIBLE_TOTAL = 45
VERIFIED_ELIGIBLE_RELATIONAL = 29
VERIFIED_RELATIONAL_BY_KIND = {"parts": 5, "edge_account": 5, "reach": 9, "correspondence": 5, "analogy": 5}
VERIFIED_RELATIONAL_BY_WORLD = {
    "world-98c6352de9137e679b7d2a460ab99be2791d9c719b0808b2fe3bbb09375534a9": 6,
    "world-28f61f2d7941a373f50285be7e57b1a9b8ec85bc0aff9e2d18c683e9f86b4547": 5,
    "world-6e1fcbdadc4a1aff1b5deddf2d84b9db1ca75b2ba9bbf98e2b202145a33d14be": 6,
    "world-22704554ac881d9846c94b37c5aabc5790edf38f7810692028f0b5e8ce8e4952": 5,
    "world-4090ec49174f1d031b16507663d875616c489382d0be1fdf7f4616aeb3dde9fc": 7,
}
# The frozen population the removals must produce. Asserted by tests, not merely described.
# `by_kind` is built over ALL five RELATIONAL kinds, so `correspondence` is present with a count of zero:
# all five of its questions left the gate as the architectural-inexpressibility class. The headline
# population is 18 = analogy 5 + edge_account 5 + parts 2 + reach 6 + correspondence 0.
VERIFIED_POPULATION = 18
VERIFIED_POPULATION_BY_KIND = {"parts": 2, "edge_account": 5, "reach": 6, "correspondence": 0, "analogy": 5}
VERIFIED_POPULATION_DIGEST = "4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d"
# Historical: the removals as INTERFACE_SPEC_POINTER.md:46 first recorded them, kept because the record of what
# was believed earlier is load-bearing. Superseded by the frozen REMOVALS above.
VERIFIED_KNOWN_REMOVALS = {"flag_rule": {"parts": 3}, "rank_rule": {"reach": 2}}
# The rank-last pointing rule's 5 questions are NOT removed: the rank feature is EXCLUDED
# (`DESIGN["node_rank_feature"]` is False), so a rule that needs it is not a registered baseline. Recorded
# because the run printed those ids and a later agent must not mistake them for removals.
UNRECONCILED_REMOVAL_READINGS = {"parts_adjacency": 5, "edge_account_adjacency": 5, "reach_rank_only": 4,
                                 "rank_last_pointing_not_removed": 5}
# ---------------------------------------------------------------------------------------------------
# THE TWO ZERO-LEARNING FLOORS INSIDE THE FROZEN POPULATION. Adversarial review R1 item 6 found this contract
# claiming the rank-solvable questions "are removed instead". They are NOT: all five are inside the frozen 18.
# These two recorded sets are what lets that be COMPUTED from the population rather than asserted again.
#
#   * RANK_LAST_SOLVED_QUESTION_IDS -- what an "always point at the alphabetically last node ref" rule answers,
#     reading NO adjacency and learning NOTHING. The rule is the leaks lens's `rank_last_policy`
#     (`pre_design/measurements/leaks_review/lk6_gate_population.py:173-193`): the last ref of the focus
#     world's sorted refs, in every node slot, `VIA` for `reach`. It solves 5 of the 45 eligible held questions
#     -- `parts` 1/5 and `reach` 4/9 (review LK7) -- and ALL FIVE are inside the frozen population, in 2 kinds
#     and 2 held worlds. No rank rule is in `REMOVALS`, so nothing removed them: the 2 `reach` questions
#     `REMOVALS["order_rule"]` takes are the DG3 ORDER-dependence removals, a DIFFERENT set.
#   * ORACLE_ONE_HOP_SOLVED_QUESTION_IDS -- what the checker's own adjacency rule answers when applied to the
#     input (`lk6_gate_population.py:266-290`): `parts` = children of the whole argument, `edge_account` = the
#     focus world's full adjacency, `reach` = DIRECT iff the part is a child. It solves 11 of the eligible 45,
#     of which 7 are inside the frozen population. That is the ceiling the label must be read BESIDE and never
#     subtracted: applying that rule to the input IS the skill under test (protocol section 4.4, confirmed by
#     the owner), so `MIN_PASSING_B` stays 7 and `REMOVALS` gains nothing.
#
# Both sets were re-derived BY IMPORT from those rules and scored by the private checker on this frozen course,
# and both re-derivations are re-run by `tests/test_typed_pointer_study.py` and by
# `records/typed_pointer_001/holdout_audit.py`, so neither is a claim nobody checked. The COUNTS INSIDE THE
# POPULATION are never written down here: `zero_learning_floor` intersects these sets with the population
# `relational_population` has just derived, so a changed population or a changed removal list moves the number.
# ---------------------------------------------------------------------------------------------------
RANK_LAST_SOLVED_QUESTION_IDS = (
    "typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f",
    "typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005",
    "typed-query-786bbcba487ecf70442672d83b1d36b6ab7ed062e996abf3c04569f67d203ceb",
    "typed-query-aa62bbee865ac5ca1a350bb48564cea189bedbba60867d0f94250d10ed95f217",
    "typed-query-f341afc7254139140ecbc5edaba9fd164bac26896c217e61e9c9c5b5ac8b5d82")
ORACLE_ONE_HOP_SOLVED_QUESTION_IDS = (
    "typed-query-0dcbaf897c1b84ec4febc2e82ee4f58002d9397ab835fea95f0a9ffb847b0226",
    "typed-query-29e8f3c3bf9dd513de24e16b4cf7436352f07bc1c3d80d7151ebdfa2030043b8",
    "typed-query-35a5228878433ecea2de7adce40d9a596c42bbb9704ad6678d376769e44370de",
    "typed-query-4a0342c26f982758689611569bebd798f324a52a3b8ee25cb5f016b394e17509",
    "typed-query-6caa13d8bd54f96e3b8981d4cd9cfbef5986ea0d621e2f4833b336507b88d353",
    "typed-query-6d9f6280ddb8dc463bfb557617353b7857fba6cfda057403516a79d8a5ec1249",
    "typed-query-786bbcba487ecf70442672d83b1d36b6ab7ed062e996abf3c04569f67d203ceb",
    "typed-query-a14f184d8f6cc4f3b80a87998515fe3c707c2dfb4f92a2358f1233fc43fba1d9",
    "typed-query-c7ee82d21b69bf37a34cadf033ed59ddb829ceec26d3459ecca3b239c29f16ab",
    "typed-query-d51fda7f878d7656bdebb87867573769bc53bc3299bb3e2af514eb9a4274b445",
    "typed-query-dde56958ee3398739016ce6152278d821a1691cb5875c191e9a42077da4b16f7")
require(len(set(RANK_LAST_SOLVED_QUESTION_IDS)) == len(RANK_LAST_SOLVED_QUESTION_IDS)
        and len(set(ORACLE_ONE_HOP_SOLVED_QUESTION_IDS)) == len(ORACLE_ONE_HOP_SOLVED_QUESTION_IDS)
        and bool(set(RANK_LAST_SOLVED_QUESTION_IDS) & set(ORACLE_ONE_HOP_SOLVED_QUESTION_IDS)),
        "ZERO_LEARNING_FLOOR_IDS")
require(all(value.startswith("typed-query-") and len(value) == len("typed-query-") + 64
            for value in RANK_LAST_SOLVED_QUESTION_IDS + ORACLE_ONE_HOP_SOLVED_QUESTION_IDS),
        "ZERO_LEARNING_FLOOR_ID_FORM")


def zero_learning_floor(question_ids):
    """The measured zero-learning floors INSIDE a population, COMPUTED from that population's question ids.

    R1 item 6: a rule that learns nothing already answers this many questions of the gate's own population, so
    the label has to be read beside the number. NOTHING IS REMOVED HERE and no threshold moves: the returned
    counts are an intersection of two recorded measurements with the population the caller derived.
    """
    ids = set(question_ids)
    rank = sorted(set(RANK_LAST_SOLVED_QUESTION_IDS) & ids)
    oracle = sorted(set(ORACLE_ONE_HOP_SOLVED_QUESTION_IDS) & ids)
    union = sorted(set(rank) | set(oracle))
    return {"rank_last_questions": rank, "rank_last_total": len(rank),
            "oracle_one_hop_questions": oracle, "oracle_one_hop_total": len(oracle),
            "union_questions": union, "union_total": len(union),
            "rank_last_eligible_total": len(RANK_LAST_SOLVED_QUESTION_IDS),
            "oracle_one_hop_eligible_total": len(ORACLE_ONE_HOP_SOLVED_QUESTION_IDS),
            "population_total": len(ids)}
# CNCM root. TWO uses, and neither of them assumes a working directory:
#   * `_practice_gates` locates the practice study's own gate reader lazily -- `records/` is analysis
#     territory, outside the packaged source scope, so that one is loaded on first use and never at import;
#   * `_import_time_stratified_digests` reads the FROZEN COURSE to derive the whole-schedule digest for the
#     current `PASSES`. That course is a pinned MATERIAL row, and every MATERIAL row IS shipped to the worker
#     at this same relative path (`worker_contract.py:135-150`), with the sources loaded from their real paths
#     (`cncm/typed_source_attestation.py:94`), so `parents[4]` is the run root in the packaged worker too. That
#     is why THIS read is safe at import while the pins JSON is not: the pins JSON is NOT a MATERIAL row, so a
#     packaged worker is not shipped it, and an import-time read of it would fail the job before any work was
#     done (see the CHECKPOINT_PINS note below).
CNCM = Path(__file__).resolve().parents[4]
_GATES_MODULE = None


def stratified_batches_digest(frozen, passes=None, stratified=None):
    """The WHOLE-schedule digest for `passes` (default `PASSES`), computed exactly as `pointer_schedule` does.

    ONE function, so the contract, its test and `records/typed_pointer_001/holdout_audit.py` cannot drift
    apart: all three ask `pointer_schedule` for the schedule and read the digest it computed over it. Every
    bound `pointer_schedule` enforces (the `POINTER_PASSES_BOUND` range, the composition digest, the coverage
    check, the update ceiling) therefore applies here too, with no second copy of the rules.
    """
    _, stats = pointer_schedule(frozen, passes, stratified)
    return stats["batches_digest"]


def _import_time_stratified_digests():
    """`{pass count: whole-schedule digest}` for the current `PASSES`, plus the recorded ten.

    DERIVED, NOT FROZEN (review R2, M4). The schedule is built from the frozen course at this module's own
    root by the same call `pointer_schedule` makes for a launch, so `STRATIFIED_BATCHES_DIGEST` follows
    `PASSES` by construction and never has to be re-measured by hand when `PASSES` is set from the smoke job.

    Ten is ALWAYS computed as well, whatever `PASSES` is, for two reasons: the recorded ten-pass identity stays
    checkable at EVERY pass count rather than only at ten, and a later change to the stratified composition
    fails closed HERE at import instead of being discovered after a spend.
    """
    frozen = load_material(CNCM)[0]
    return {count: stratified_batches_digest(frozen, count) for count in sorted({PASSES, TEN_PASSES})}


_STRATIFIED_BATCHES_DIGESTS = _import_time_stratified_digests()
STRATIFIED_BATCHES_DIGEST = _STRATIFIED_BATCHES_DIGESTS[PASSES]
# The ten-pass record must still reproduce, at ANY `PASSES` ...
require(_STRATIFIED_BATCHES_DIGESTS[TEN_PASSES] == STRATIFIED_BATCHES_DIGEST_AT_10_PASSES,
        "POINTER_STRATIFIED_DIGEST_AT_10_PASSES")
# ... and at any pass count other than ten the digest must have MOVED. That is the invariant the defect broke:
# the whole-schedule digest is a FUNCTION of the pass count, not a constant measured once and frozen.
require(PASSES == TEN_PASSES or STRATIFIED_BATCHES_DIGEST != STRATIFIED_BATCHES_DIGEST_AT_10_PASSES,
        "POINTER_STRATIFIED_DIGEST_PASS_COUNT")


def _practice_gates():
    """The practice study's own eligible/shortcut derivation, loaded lazily and only when asked for.

    `records/` is analysis territory: it is outside the packaged source scope (`worker_contract.py:138-143`
    globs only `cncm/` and `cas_meta2/`), so this module is loaded on first use and never at import time.
    The AWS worker imports this contract and must not depend on a `records/` script being shipped.
    """
    global _GATES_MODULE
    if _GATES_MODULE is None:
        path = CNCM / "records" / "typed_practice_001" / "evaluate_gates.py"
        require(path.is_file(), "PRACTICE_GATES_MISSING")
        spec = importlib.util.spec_from_file_location("cncm_practice_gates", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        require(callable(getattr(module, "eligible_questions", None)), "PRACTICE_GATES_API")
        _GATES_MODULE = module
    return _GATES_MODULE


def _removals():
    """Validate the placeholder's shape and return it. Empty is valid; malformed is not."""
    require(type(REMOVALS) is dict and set(REMOVALS) == set(REMOVAL_RULES), "RELATIONAL_REMOVALS_SHAPE")
    for rule in REMOVAL_RULES:
        require(type(REMOVALS[rule]) is dict, "RELATIONAL_REMOVALS_SHAPE:" + rule)
        for kind, questions in REMOVALS[rule].items():
            require(kind in RELATIONAL and type(questions) is list
                    and all(type(question) is str for question in questions), "RELATIONAL_REMOVALS_SHAPE:" + rule)
    return REMOVALS


def relational_population(frozen):
    """The pointer study's gate population: eligible held RELATIONAL questions minus the registered removals.

    MECHANISM, NOT A FROZEN LITERAL.
      (a) take every eligible held-back question of the RELATIONAL kinds: the practice study's own hold-out
          (`held_back_questions`) minus the practice study's own registered input-blind shortcut questions,
          reused through `records/typed_practice_001/evaluate_gates.py:eligible_questions` rather than
          re-derived;
      (b) subtract every question solved by a registered FLAG rule (`REMOVALS["flag_rule"]`, review FP2) or
          a registered ORDER rule (`REMOVALS["order_rule"]`, review DG3);
      (c) return the surviving question ids, their per-kind counts, their per-world counts, a digest, and the
          measured ZERO-LEARNING FLOOR inside those ids (`zero_learning_floor`, review R1 item 6) -- the
          number a rule that learns nothing already answers, reported and never subtracted.

    THE VERIFIED INPUTS a later agent must reconcile against (measured 2026-09-19, recorded here rather
    than re-derived): 45 eligible held questions = 10 DIRECT_READ (definition 5 + context 5) + 29
    RELATIONAL + 6 role_set. The 29 RELATIONAL are correspondence 5, edge_account 5, reach 9, analogy 5,
    parts 5, and their held worlds are world-98c6352d 6, world-28f61f2d 5, world-6e1fcbda 6,
    world-22704554 5, world-4090ec49 7. Known removals: the FP2 flag rule solves 3 of the 5 eligible held
    `parts`; node-order dependence covers 2 of the 9 eligible held `reach`.

    While `REMOVALS` is empty the returned population is NOT the frozen one, and the function raises
    `RELATIONAL_POPULATION_UNRECONCILED` unless the eligible RELATIONAL total and its per-kind and
    per-world composition are exactly the verified values above, so the placeholder cannot be mistaken
    for a finished population.

    NOT THE LAST WORD ON THESE NUMBERS, and the guard is deliberately the only thing reconciling them.
    `DESIGN_DRAFT_v0.2.md:649-656` (section 6.4, "PENDING on the gate") measures that the input's own
    `contains` adjacency already answers 5 of 5 eligible held `parts` and 5 of 5 `edge_account` with no
    learned weights at all. THE OVERLAP IS NO LONGER UNMEASURED (review R1 item 6): the rank-only single-flag
    rule (R10) solves 4 of the 9 eligible held `reach` plus 1 of the 5 `parts`, and all 5 of those questions
    are still in the frozen population -- measured, and computed by `zero_learning_floor` on every call.
    That leaves the two zero-learning classes R1 reported: 7 of the 18 from the one-hop adjacency rules and 11
    of the 18 from their union with the rank rule, which is the number the gate reader prints beside the label.
    It is a ceiling the label is read beside; it is NOT a removal and it moves no threshold, because applying
    that rule to the input IS the skill under test (protocol section 4.4) and `MIN_PASSING_B` stays 7.
   """
    rules = _removals()
    empty = not any(rules[rule] for rule in REMOVAL_RULES)
    held = held_back_questions(frozen)
    trained = set(split(frozen)[1])
    eligible, shortcut_hit, shortcut = _practice_gates().eligible_questions(frozen, trained, held)
    kind_of = {row["query"]["query_id"]: row["query"]["kind"] for row in frozen["registry"]}
    world_of = {row["query"]["query_id"]: row["source_world_id"] for row in frozen["registry"]}
    record_world = {row["record_id"]: row["source_world_id"] for row in frozen["registry"]}
    # A question is one unit of the gate and belongs to exactly one held world (as the practice reader
    # already assumes when it reads the kind off `records[0]`).
    require(all(len({record_world[record] for record in records}) == 1 and world_of[question] ==
                record_world[records[0]] for question, records in held.items()), "RELATIONAL_POPULATION_WORLD")
    require(set(eligible) <= set(held) and all(question in kind_of and question in world_of for question in eligible),
            "RELATIONAL_POPULATION_INPUT")

    eligible_relational = sorted(question for question in eligible if kind_of[question] in RELATIONAL)
    eligible_by_kind = {kind: sum(1 for q in eligible_relational if kind_of[q] == kind) for kind in RELATIONAL}
    eligible_by_world = dict(sorted(Counter(world_of[q] for q in eligible_relational).items()))
    counts = {tier: sum(1 for q in eligible if kind_of[q] in kinds) for tier, kinds in TIERS.items()}
    require(sum(eligible_by_world.values()) == len(eligible_relational) == sum(eligible_by_kind.values()),
            "RELATIONAL_POPULATION_COUNTS")
    require(not empty or (len(eligible_relational) == VERIFIED_ELIGIBLE_RELATIONAL
                          and eligible_by_kind == VERIFIED_RELATIONAL_BY_KIND
                          and eligible_by_world == VERIFIED_RELATIONAL_BY_WORLD
                          and sum(counts.values()) == VERIFIED_ELIGIBLE_TOTAL),
            "RELATIONAL_POPULATION_UNRECONCILED")

    removed = []
    for rule in REMOVAL_RULES:
        for kind in sorted(rules[rule]):
            listed = rules[rule][kind]
            require(set(listed) <= {q for q in eligible_relational if kind_of[q] == kind},
                    "RELATIONAL_REMOVALS_UNKNOWN:" + rule + ":" + kind)
            removed.extend(listed)
    require(len(removed) == len(set(removed)), "RELATIONAL_REMOVALS_OVERLAP")
    surviving = sorted(set(eligible_relational) - set(removed))

    return {
        "tier": "RELATIONAL",
        "tiers": list(RELATIONAL),
        "eligible_by_tier": dict(sorted(counts.items())),
        "eligible_questions": eligible_relational,
        "eligible_total": len(eligible_relational),
        "eligible_by_kind": eligible_by_kind,
        "eligible_by_world": eligible_by_world,
        "eligible_digest": digest(eligible_relational),
        "removed_questions": sorted(removed),
        "removed_by_rule": {rule: {kind: sorted(rules[rule][kind]) for kind in sorted(rules[rule])}
                            for rule in REMOVAL_RULES},
        "question_ids": surviving,
        "total": len(surviving),
        "by_kind": {kind: sum(1 for q in surviving if kind_of[q] == kind) for kind in RELATIONAL},
        "by_world": dict(sorted(Counter(world_of[q] for q in surviving).items())),
        "digest": digest(surviving),
        "removals_measured": not empty,
        "population_complete": not empty,
        # R1 item 6: what a zero-learning rule already answers INSIDE this population, COMPUTED from the
        # surviving ids above. Reported, never subtracted: the population and `MIN_PASSING_B` are untouched.
        "zero_learning_floor": zero_learning_floor(surviving),
        "verified_inputs": {"eligible_total": VERIFIED_ELIGIBLE_TOTAL,
                            "eligible_relational": VERIFIED_ELIGIBLE_RELATIONAL,
                            "by_kind": deepcopy(VERIFIED_RELATIONAL_BY_KIND),
                            "by_world": deepcopy(VERIFIED_RELATIONAL_BY_WORLD),
                            "known_removals": deepcopy(VERIFIED_KNOWN_REMOVALS),
                            "unreconciled_removal_readings": deepcopy(UNRECONCILED_REMOVAL_READINGS)},
        "shortcut_question_ids": list(shortcut_hit),
        "shortcut_answers": dict(shortcut),
    }


# The 17 inherited machine fields that are genuinely machine-independent. `package` is deliberately NOT
# inherited: the pointer package ships the 18 practice checkpoints through MATERIAL, so the practice
# study's package description would be false here (DG10). `registered_learner_unchanged` and
# `initialization` are not inherited either -- both are false for a new machine and a new learner.
_INHERITED = ("d_model", "max_input_tokens", "prediction_depth", "depths", "optimizer_class", "optimizer_foreach",
              "optimizer_fused", "optimizer_config", "training_loss", "reporting_loss", "main_targets", "replay",
              "replay_counts", "source_attestation", "projection_scope", "region", "instance_type")

BOUNDARY = ("Typed pointer reading of ONE focus world as a small directed graph, on one teaching order. The "
            "held-back questions are about five course worlds the machine never read (same world sizes and "
            "question kinds as training); the development panel is out-of-distribution ten-node parts/reach. "
            "The primary label is keyed on the RELATIONAL tier, so gains on the DIRECT_READ kinds alone "
            "cannot produce it. No protected final-study, general CAS architecture, or full-machine claim.")

DESIGN = {**{key: deepcopy(matched.DESIGN[key]) for key in _INHERITED},
    "candidate": CANDIDATE,
    "purpose": "DOES_THE_POINTER_MACHINE_LEARN_RELATIONAL_ANSWERS_ON_WORLDS_IT_NEVER_READ",
    # CORRECTED 2026-09-19 (pre-flight, $0). This record carried only FOUR of the five owner decisions and had
    # flattened the em dash in the third to `--`. Neither was cosmetic. Protocol section 0.2 says "The selected
    # labels are recorded verbatim and are copied into every job's `owner.json`", and `prepare_study.py` copies
    # THIS string into all three owner records -- so a paraphrase or a missing decision here is propagated
    # straight into the signed per-job governance records.
    #
    # Root cause of the flattened dash, and why the fix looks like this: this module is PURE ASCII (verified, 0
    # characters above U+007F), so the em dash had been transliterated to `--`. `\u2014` below is an ASCII source
    # escape that evaluates to the real em dash, so the VALUE is byte-for-byte the protocol's while the file stays
    # pure ASCII. Do not "tidy" it back to `--`.
    #
    # All five labels are now byte-for-byte the protocol's. THE CITATION IS THE PROTOCOL'S SECTION 0.2, ITEMS
    # 1-5 -- not a line number, because a line number here has already gone stale once: an 18-line correction
    # block inserted into section 0.2 item 2 pushed decisions 3, 4 and 5 down the file (protocol commit
    # `69dc269d`). Section 0.2 is the authority; the numbers below are only a convenience for finding the labels.
    #
    # DATED HINT ONLY, byte-scanned 2026-09-19 against the protocol at HEAD `d57ea9a6`
    # (`docs/CNCM_TYPED_POINTER_STUDY_v0.1.md`, 96429 bytes, sha256
    # 8ac6673325dcd1db6bb34cce567fa2c4c17fa6a56b6ddc01bb1fb70eb73a7079):
    #   item 1 -> :52, item 2 -> :57, item 3 -> :86, item 4 -> :89-92 (the label wraps), item 5 -> :94.
    # This hint used to read :52/:57/:61/:64/:69, and the amendment left three of those five wrong. Expect the
    # same drift after any further protocol edit: re-read section 0.2, and never trust these numbers alone.
    "owner_approval": ("2026-09-19 owner decisions, verbatim, five of five: \"Accept both, carry on.\" (both "
        "corrections -- the in-job checkpoint check costs about $0.38-0.63 per job, not \"no extra cost\", and "
        "pointer answers alone cannot work because the INPUT must change too, one world read as a graph instead "
        "of a blend of all 64), \"Approve the smoke job (Recommended)\" (a short AWS smoke job for S10, well under "
        "$1, before any paid launch), \"Yes \u2014 require the relational kinds.\" (the primary label is keyed on "
        "the RELATIONAL tier; the all-kinds result is a reported flag, never the label), \"Run it as the transfer "
        "test, label honestly (Recommended)\" (the study runs as the transfer test it was built to be, and the "
        "label is printed honestly, so a tier or a kind whose answer is already in the input is reported as such "
        "and never carries a learning claim), and on the LB11 schedule question \"Stratify AND train longer "
        "(Recommended)\" (the single pass is stratified -- every one of the eight kinds in every update at the "
        "same 147 updates per pass -- and the pass count is the study's own parameter above the practice study's "
        "10, so `STRATIFIED` is True and `MAX_PASSES_PERMITTED` is 24)."),
    "machine": "POINTER",
    "input_unit": "ONE_FOCUS_WORLD_READ_AS_A_DIRECTED_GRAPH",
    "answer_form": "POINTER_INTO_THE_QUESTION_INPUT",
    # DECIDED 2026-09-19: the node rank FEATURE is EXCLUDED. CORRECTED 2026-09-19 (adversarial review R1,
    # item 6): this comment and `node_rank_decision_status` used to say the rank-solvable QUESTIONS were
    # "removed instead". They were NOT, and the claim was false: all five of them are inside the frozen
    # population. What is measurably true is below, and the count is computed, never asserted here.
    #
    # Both review lenses agree, from opposite directions. The leaks lens (LK7) measured the
    # alphabetically-last-node rule solving 5 of 45 eligible questions by itself (parts 1/5, reach 4/9) and
    # stated the preference plainly: take the removal option so the vacuity law survives. The learnability
    # lens (LB1) reached the same fork from the hidden-ref-order side (5/26 held reach records). The REMOVAL
    # option was NOT taken -- `REMOVAL_RULES` has four classes and none of them is rank, and the 2 `reach`
    # questions `REMOVALS["order_rule"]` takes are the DG3 ORDER-dependence removals, a different set.
    #
    # WHAT IS MEASURABLY TRUE (measured by import on this frozen course, re-derived by the test suite and by
    # `records/typed_pointer_001/holdout_audit.py`, and computed by `zero_learning_floor` on every call): the
    # rank-last rule solves 5 of the eligible 45 and ALL 5 are in the population, parts 1 and reach 4, in 2
    # kinds and 2 held worlds; the one-hop adjacency rules solve 7 of the population in 2 kinds and 5 worlds;
    # and their union covers 11 of the 18. A reader must therefore NOT read this population as rank-free.
    #
    # Had the removal option been taken, the population would have fallen from 18 to 13 and the required share
    # would have risen from 7/18 = 0.3889 to 7/13 = 0.5385, and that would have withdrawn the draft's own
    # vacuity paragraph, because the rank IS the node alias: 244 of 244 node refs have their sorted position
    # equal to their own stored index. Those are the reasons the FEATURE is off -- not a claim of removal.
    "node_rank_feature": False,
    "node_rank_decision_status": "EXCLUDED_2026_09_19_RANK_FEATURE_OFF_RANK_SOLVABLE_QUESTIONS_NOT_REMOVED",
    "head_set": "OPEN_LENS_B_EXPRESSIVITY_TABLE",
    "core_rounds": PLANNED_WORK_ROUNDS,
    "planned_work": deepcopy(PLANNED_WORK),
    "tiers": {tier: list(kinds) for tier, kinds in TIERS.items()},
    "primary_label_tier": "RELATIONAL",
    "primary_label_rule": "RELATIONAL_TIER_GAIN_REQUIRED_TWO_KINDS_TWO_WORLDS_ALL_THREE_SEEDS",
    "flag_copy_alone_cannot_pass": True,
    "gate_population": "ELIGIBLE_HELD_RELATIONAL_QUESTIONS_MINUS_REGISTERED_FLAG_AND_RANK_RULE_REMOVALS",
    # CLOSED 2026-09-19. This flag was left `True` from the design phase and contradicted the rest of this
    # file: `REMOVALS`, above, is filled with the frozen 11 removals across four classes -- cited BY NAME and
    # not by line number, so this reference cannot go stale -- and `relational_population` reports
    # `population_complete: True` against `VERIFIED_POPULATION` (18) and `VERIFIED_POPULATION_DIGEST`. Nothing
    # read it, so it manufactured a false statement about the study rather than causing a failure. It is now
    # `False`, which is what "the gate is frozen at 18" means.
    # `pre_design/GATE_FEASIBILITY.md` is the power calculation behind the value 18.
    "gate_population_open": False,
    "checkpoint_check": "THREE_PRACTICE_CHECKPOINTS_PER_SEED_RESTORED_IN_PHASE_A_BEFORE_THE_POINTER_MODEL_IS_SEEDED",
    "initialization": "REGISTERED_RANDOM_PER_MODEL_SEED_AFTER_PHASE_A_RESTORES",
    "condition": CONDITION, "source_seed": SOURCE_SEED, "encoder_seed": ENCODER_SEED,
    "model_seeds": list(MODEL_SEEDS), "passes": PASSES, "holdout_unit": "FOCUS_WORLD",
    # THE VERSION IDENTITY, carried into the package manifest (`experiment`/`typed_design`), the worker config
    # and the worker report, so no 20-pass artifact can be read as an R18 10-pass one.
    "experiment_version": EXPERIMENT_VERSION, "pass_multiplier_over_r18": VERSION_PASS_MULTIPLIER,
    "run_model_seed": RUN_MODEL_SEED,
    "training_duration_change_only": ("SAME_MODEL_DATA_BATCH_ORDER_OPTIMIZER_HOLDOUT_DEV_PANEL_SCORING_AND_SOURCE_LOGIC_"
                                      "AS_R18_ONLY_THE_TRAINING_DURATION_AND_THE_OUTPUT_ENVELOPE_MOVE"),
    "learning_rate_schedule": "CONSTANT_AS_HELM_1_0", "planned_main_updates": None,
    "evaluated_at_both_durations": True, "best_checkpoint_selection": False,
    # The single pass a reader must know about before trusting any per-kind statement: STRATIFIED, one record of
    # each of the eight kinds in EVERY update at the same 147 updates per pass, chosen by the owner's 2026-09-19
    # decision (see `owner_approval`). `schedule_stratified_absent_updates_as_is` is the as-is branch's own
    # measurement (REVIEW_SYNTHESIS.md section 4.7), kept beside it so the comparison travels with the field
    # rather than having to be re-derived; under stratification every one of those eight counts is 0.
    # `schedule_stratified_batches_digest` is the DERIVED whole-schedule digest for the registered `PASSES`
    # (review R2, M4), never a literal: a shipped design that carried another pass count's digest while the
    # job ran this one would be a false statement about the job. For 20 passes it is NOT the ten-pass value
    # `1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304`; the import-time check below and
    # `tests/test_typed_pointer_critical_mass_2x.py` both assert that difference.
    "schedule_stratified": STRATIFIED,
    "schedule_stratified_decision": "OWNER_DECISION_STRATIFY_AND_TRAIN_LONGER_RECOMMENDED",
    "schedule_stratified_updates_per_pass": 147, "schedule_stratified_presentations_per_pass": 1176,
    "schedule_stratified_kinds_per_batch": len(KINDS),
    "schedule_stratified_batches_digest": STRATIFIED_BATCHES_DIGEST,
    "schedule_stratified_pass_digest": STRATIFIED_PASS_DIGEST,
    "schedule_unstratified_updates_per_pass": 147, "schedule_unstratified_presentations_per_pass": 818,
    "schedule_unstratified_batches_digest": "daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857",
    "schedule_stratified_absent_updates_as_is": {"role_set": 115, "analogy": 112, "context": 107,
                                                 "definition": 105, "edge_account": 95, "correspondence": 67,
                                                 "parts": 63, "reach": 40},
    "holdout_rule": practice.DESIGN["holdout_rule"], "held_worlds": list(practice.HELD_WORLDS),
    "pass_checkpoints": list(PASS_CHECKPOINTS), "full_course_checkpoints": list(FULL_COURSE_CHECKPOINTS),
    "interference_updates": INTERFERENCE_UPDATES, "interference_batch": INTERFERENCE_BATCH,
    "interference_trained_records_only": True, "replay_updates": REPLAY_UPDATES,
    "learner_max_updates_ceiling": LEARNER_MAX_UPDATES_CEILING, "max_core_calls": MAX_CORE_CALLS,
    "worker_deadline_seconds": WORKER_DEADLINE_SECONDS, "max_wall_seconds": MAX_WALL_SECONDS,
    "instance_seconds_max": INSTANCE_SECONDS_MAX, "reservation_usd": RESERVATION_USD,
    "jobs": 1, "automatic_retries": 0, "launch_enabled": False, "partial_course_is_success": False,
    "registered_learner_unchanged": False,
    "package": ("PINNED_COURSE_TOKENIZER_SOURCES_THE_TWO_WHEELS_AND_THE_EIGHTEEN_PRACTICE_CHECKPOINTS_"
                "NO_PRIVATE_TARGET_BUNDLE"),
    "boundary": BOUNDARY,
    "learning_on_held_back_established": False}


def parse_job(job):
    require(type(job) is str, "JOB")
    match = re.fullmatch(JOB_PATTERN, job)
    require(match is not None, "JOB")
    return CONDITION, int(match.group(2))


def make_config(root, *, source_sha, job, bucket, model_seed):
    require(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}", source_sha), "SOURCE_SHA")
    require(type(model_seed) is int and model_seed in MODEL_SEEDS, "MODEL_SEED")
    require(parse_job(job) == (CONDITION, model_seed) and re.fullmatch(JOB_PATTERN, job).group(1) == source_sha[:8],
            "JOB_PARAMETERS")
    require(type(bucket) is str and re.fullmatch(BUCKET_PATTERN, bucket), "BUCKET")
    frozen, _, development = load_material(root)
    _, stats = pointer_schedule(frozen)
    held, _, excluded = split(frozen)
    retention = list(retention_packets(frozen))
    interference = interference_batches(frozen)
    rows = input_inventory(root)
    design = {**deepcopy(DESIGN), "model_seed": model_seed, "schedule": stats,
        "held_back_record_ids": held, "excluded_record_ids": excluded,
        "development_digest": development["development_digest"],
        "development_packets": len(development["packets"]), "retention_packets": len(retention),
        "retention_record_ids_digest": digest([key for key, _ in retention]),
        "interference_batches_digest": digest(interference)}
    return {"schema": CONFIG_SCHEMA, "source_sha": source_sha, "job": job, "bucket": bucket,
        "design": design, "inputs": rows, "inputs_sha256": sha256(canonical(rows)).hexdigest()}


def validate_config(config, root):
    require(type(config) is dict and set(config) == {"schema", "source_sha", "job", "bucket", "design", "inputs",
                                                     "inputs_sha256"}, "CONFIG_FIELDS")
    _, seed = parse_job(config["job"])
    expected = make_config(root, source_sha=config["source_sha"], job=config["job"], bucket=config["bucket"],
                           model_seed=seed)
    require(canonical(config) == canonical(expected), "CONFIG_IDENTITY")
    return deepcopy(expected)
