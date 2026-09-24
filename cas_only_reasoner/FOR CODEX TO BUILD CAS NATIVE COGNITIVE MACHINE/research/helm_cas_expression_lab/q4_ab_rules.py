"""Q4-SDG-1 A-versus-B comparison 0.2: the FROZEN rules. Standard library only; no torch, no data, no model.

Everything a program needs to run the comparison and to read its results is fixed here, before any launch:
arms, seeds, practice budget, checkpoints, hyperparameters, panel definitions, digests of the panels (measured on
the laptop from VISIBLE files only), the input-use thresholds and the exact statistical tests. The runner
(q4_ab_train.py) writes this record into every result file; the reader (read_q4_ab_results.py) refuses results whose
record differs from its own. Human-readable companion: Q4_SDG_AB_SPEC_v0_2.md.

Label: CLAUDE_BUILT_CLAUDE_CHECKED (temporary takeover while Codex is away). Experiment id Q4-SDG-1.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from math import comb

SCHEMA = "helm-cas-expression-lab.q4-sdg-ab/0.2"
SPEC_REVISION = ("v0.2 revision 3 (coordinator decisions of 2026-09-24 after the verification of 294471a5; "
                 "PROPOSED_FOR_REVIEW)")
EXPERIMENT = "Q4-SDG-1"
LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"

# ---- arms, seeds, practice budget -----------------------------------------------------------------------------
ARMS = ("A", "B")
ARM_MEANING = {"A": "existing family-G teaching: visible Q3 v0.7 G train rows (minus the reserved panel rows)",
               "B": "the pinned CAS SDG lesson package, families A-C train split (minus any panel content); no D"}
SEEDS = (20260931, 20260932, 20260933)          # new; pair i uses SEEDS[i] for BOTH arms (same starting tensors)
Q3_SEEDS = tuple(range(20260921, 20260926))      # never used here (20260921 only for the Stage-0 re-init check)
RUN_ORDER = tuple((arm, seed) for seed in SEEDS for arm in ARMS)   # A1 B1 A2 B2 A3 B3: a timeout keeps whole pairs
UPDATES = 32768                                  # single-example updates per run = presentations per run
CHECKPOINTS = (0, 128, 512, 2048, 8192, 16384, 32768)   # measured after this many updates; the last is FINAL
FINAL = CHECKPOINTS[-1]
LOSS_WINDOW = 64                                 # per-update losses are summarised in windows of 64 updates

# ---- identical to records/q4_authorized_20260922/run_001/plan.json (a test re-reads that plan) --------------------
WIDTH = 64
LEARNING_RATE = 0.001
CLIP_NORM = 1.0
OPTIMIZER = "torch.optim.AdamW(model.parameters(), lr=0.001); every other argument at the torch default"
LOSS = "torch.nn.functional.cross_entropy(logits, gold): full vocabulary, mean over target positions, EOS included"
INIT = ("torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); deterministic flags; "
        "build_model(NeuralConfig(64), device='cuda:0'); AdamW; then the seeded order (q4_smoke_job._worker order)")
ORDER = ("epoch e: perm = list(range(n)); rng.shuffle(perm) with ONE random.Random(seed) for the whole run; "
         "epoch 0 equals q4_smoke_job's random.Random(seed).shuffle(order)")
NUMERICAL_POLICY = "CUDA_FLOAT32_DETERMINISTIC_OR_FAIL_NO_FALLBACK"
EXPECTED_TORCH = "2.11.0+cu128"
EXPECTED_PYTHON = "3.14"

# ---- evaluation ------------------------------------------------------------------------------------------------
EVAL_DECODE_MAX_TOKENS = 64       # every panel target has <= 56 tokens; a longer decode is wrong under any limit
SP1_SEED = 20260965               # new: selection of the reserved FAMILIAR_STRUCTURE_NEW_CONTENT pool
SP1_SIZE = 256                    # proportional to each G-train shape's non-inspected rows (largest remainder)
EDIT_STRIDE = 4                   # SP1 rows 0, 4, 8, ... = the 64-row one-field-edit panel (EDIT64)
TEACH_FIT_ROWS = 64               # the first 64 rows of each run's own first epoch (per arm; not compared)
PANELS = {
    "SP1": "FAMILIAR_STRUCTURE_NEW_CONTENT: 256 visible Q3 G train rows reserved before any arm, drawn from the "
           "rows the diagnostic never showed, allocated to the 16 G-train shapes in proportion to their rows "
           "(largest remainder), never taught to either arm (shared; decisive)",
    "SP2": "NEW_STRUCTURE: all 256 visible Q3 G dev rows (9 held-out depth-3 shapes; shared). SP2U = the 208 rows "
           "never inspected (decisive); SP2ALL = all 256 (reported and labelled)",
    "B_DEV": "the B package's own dev split: B-INTERNAL, reported for both arms, never decisive",
    "TEACH_FIT": "the first 64 rows of the run's own first epoch: per-run teaching fit, never compared",
}
COMPARISON_PANELS = ("SP1", "SP2U", "SP2ALL")
PRIMARY_PANELS = ("SP1", "SP2U")            # the one overall lessons answer combines these two (SP2ALL is reported)
MISSING_PANEL = ("LONGER_OR_DEEPER_THAN_TAUGHT: directive section 8's fourth panel is NOT built. The only such "
                 "visible rows are the protected Q3 G eval (depths 4-5), which no loop may touch")

# ---- B package identity (the pin itself is written after the AWS data build, into Q4_SDG_DATA_PINS.json) ---------
B_PACKAGE = {"schema": "helm-cas-expression-lab.q4-sdg-lessons/0.1", "size": 4096, "seed": 20260941,
             "feedback_seed": 20260951, "engine": "python", "data_dir": "data/q4_sdg_v0_1"}

# ---- smoke stage and time limits -------------------------------------------------------------------------------
SMOKE_UPDATES = 64
SMOKE_CHECKPOINTS = (0, 32, 64)
SMOKE_STRIDE = 16                           # smoke panels = every 16th row of each panel (spread over shapes)
SMOKE_EDIT_STRIDE = 8                       # smoke edit rows = every 8th row of EDIT64
PROJECTION_SAFETY = Fraction(5, 4)          # projected time x 1.25 must fit what is left of the job's wall limit
RELOAD_ALLOWANCE_SECONDS = 90               # per run, for the fresh-process reload check
RUN_WALL_SECONDS = 3000                     # per run (training + all its checkpoints)
JOB_WALL_SECONDS = 11400                    # whole q4_ab_train.py run (190 min), inside the 225-min machine timer

# ---- the decision rules (M1). Justification from the diagnosis numbers is in the spec, section 7 ----------------
T1_FIELD = "noetic"
T1_ALPHA = Fraction(1, 100)
SP1_NOETIC_NULL = Fraction(90, 799)         # most frequent noetic value among the SP1 targets (N1), measured
A_POOL_NOETIC_NULL = Fraction(605, 5671)    # most frequent noetic value in arm A's teaching pool (N2), measured
T2_DELTA = 0.01                             # 2,700 x the largest move the saved model showed (3.6378e-06)
T2_MIN_SHARE = Fraction(1, 10)
T2_ALPHA = Fraction(1, 100)
T3_MIN_DISTINCT = 32                        # of the 256 SP1 rows; the saved model gave 1 distinct output of 96
# NONE means TOTAL collapse only (coordinator decision 1 of 2026-09-24): T1, T2V and T2P all fail AND the run gives
# exactly this many distinct free outputs over the 256 SP1 rows. Two or more distinct free outputs is never NONE.
NONE_DISTINCT_FREE_OUTPUTS = 1
PAIR_ALPHA = Fraction(1, 100)
ARM_MIN_SEEDS = 2                           # "at least 2 of its 3 seeds" are FULL (valid runs)
ARM_MIN_VALID_RUNS = 2                      # an arm has too few valid runs below this
ARM_MIN_VALID_NONE_RUNS = 2                 # "NONE in at least 2 of its arm's 3 seeds" (valid runs; decision 3)
# One-field edits come in two kinds. A PRESENCE edit adds or removes an optional drive or register, so the input
# text gets longer or shorter; reading it needs only the input's length or layout. A VALUE edit changes a value in
# place (same input length). Only value edits test field-value reading (review of 3771f989, MINOR 1).
EDIT_KIND_RULE = "presence iff field in (drive, register) and 'None' in (from, to); value otherwise"
VALUE_EDIT_COUNTS = {"noetic": 196, "domain": 185, "drive": 88, "register": 69}     # 538, measured
PRESENCE_EDIT_COUNTS = {"drive": 108, "register": 127}                             # 235, measured
VALUE_EDIT_COUNT = sum(VALUE_EDIT_COUNTS.values())
PRESENCE_EDIT_COUNT = sum(PRESENCE_EDIT_COUNTS.values())
EDIT_VALUE_COLUMNS = ("p_new_original", "p_new_edited", "p_old_original", "p_old_edited", "masked_choice_original",
                      "masked_choice_edited", "summary_cosine", "row", "position")
# Input-use levels of one run at one checkpoint (review of 3771f989, MAJOR; coordinator decisions 1 and 2 of
# 2026-09-24). Checked in this order. STRUCTURE_OR_OUTPUT_VARIATION replaces revision 2's STRUCTURE_ONLY: its
# definition ("2 or more distinct free outputs, or T2P passes, while T1 and T2V fail") contains STRUCTURE_ONLY.
LEVELS = ("FULL", "TEACHER_FORCED_ONLY", "PARTIAL_FIELDS", "STRUCTURE_OR_OUTPUT_VARIATION", "NONE")
FIELD_LEVELS = ("FULL", "TEACHER_FORCED_ONLY", "PARTIAL_FIELDS")     # exactly the levels where T1 or T2V passes
ARCHITECTURE_REASONS = ("INPUT_USE_RULE_FIRES_AT_INITIALISATION", "TEACHER_FORCED_ONLY", "PARTIAL_FIELDS",
                        "STRUCTURE_OR_OUTPUT_VARIATION", "SEED_DEPENDENT", "NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID",
                        "TOO_FEW_VALID_RUNS")
INFORMATION_LABELS = ("FIELDS_NOT_READ_IN_ANY_RUN",)               # decision 4: information only, justifies nothing
LESSON_OUTCOMES = ("HELP", "HURT", "EFFECT_NOT_SHOWN", "COMPARISON_INCOMPLETE", "NOT_EVALUATED")
OVERALL_LESSON_OUTCOMES = ("HELP", "HURT", "MIXED", "EFFECT_NOT_SHOWN", "COMPARISON_INCOMPLETE", "NOT_EVALUATED")

# ---- digests measured on the laptop from VISIBLE Q3 v0.7 files (pure Python, 2026-09-24) ------------------------
Q3_MANIFEST_SHA256 = "1cf98a2b48ade4acf12c51c0cc74d3dd2504f7eb0e7d24662fe8b6f7d29f8bf9"
RUN_001_PLAN_SHA256 = "9dacc83627422d704c9db58f5ddbac82936e7d52211ec061247419fbad78095c"
RUN_001_WEIGHTS_SHA256 = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
DIAGNOSTIC_SELECTION_DIGEST = "0b98bfc94a5aed8af2d4fef72378fec7dfa9d46808b09ff30f750972387a3059"
INSPECTED_DEV_DIGEST = "d91d914b93a9f131110cce59efb09028f8b71387107a5fe53ffc51ed6ee10105"
INSPECTED_TRAIN_DIGEST = "1131a9c34c06de6c106c902a039379b9d6b10d795bc268da490763f296a145c8"
SP1_DIGEST = "dab48792e0a7382c3e224e7c027d677405983b8a67cd522e59ef7add25cfc122"
SP2_DIGEST = "00e55a809e02ac1fec043443cdb2e6413bbfd5ac3abaa2539534c7e8b793884a"          # [id, content_sha256]
PANEL_TARGETS_DIGEST = "ba04a4de476cf678be42c71ceb03d90e1d6aba98fda8cb5d7785004f91b7f28a"  # SP1+SP2 targets
EDIT_PANEL_DIGEST = "05d62b99f52db1a3b2a6511ffe0bb091b9415cc772474bb58d43a72b757c94d2"
EDIT_KINDS_DIGEST = "c276d894a03804987d1435f160203922de824b59e96c38e07de9bcb23ca6f322"     # [row, position, kind]
A_POOL_DIGEST = "9064635d86c95ae4886e24ce63810b9d216e22106a10d2645a9efdfe91e21a08"
A_POOL_ROWS = 1792
EDIT_COUNT = 773                           # measurable edits on EDIT64 (11 more leaf fields have no compilable edit)
MEASURED_DIGEST_KEYS = ("diagnostic_selection", "inspected_dev", "inspected_train", "sp1", "sp2", "panel_targets",
                        "edit_panel", "edit_kinds", "a_pool", "a_pool_rows", "edit_count", "value_edit_count",
                        "presence_edit_count", "sp1_noetic_null", "a_pool_noetic_null")

STOP_CODES = (
    "GPU_REQUIRED", "RUNTIME_VERSION_MISMATCH", "CUBLAS_WORKSPACE_CONFIG_DIFFERS", "GPU_BUSY_OR_UNKNOWN",
    "CUSTODY_REFUSED", "RUN_001_RECORDS_INCONSISTENT", "Q3_DATA_NOT_PINNED", "COMPILER_ENGINE_NOT_PYTHON",
    "PANEL_DIGEST_MISMATCH", "B_PACKAGE_NOT_PINNED", "B_PIN_NOT_THE_FROZEN_PACKAGE", "B_PACKAGE_BUILD_FAILED",
    "B_PACKAGE_MISMATCH", "STAGE0_NOT_REPRODUCED", "REINIT_NOT_REPRODUCED", "SMOKE_NONDETERMINISTIC",
    "SMOKE_PAIR_INIT_MISMATCH", "SMOKE_RELOAD_FAILED", "SMOKE_FAILED", "PROJECTED_OVER_TIME", "NUMERICAL_FAILURE",
    "RUN_WALL_LIMIT", "JOB_WALL_LIMIT",
)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def frozen_record() -> dict:
    """Every frozen value, as JSON. The runner copies it into its results; the reader compares it with its own."""
    t2_test = ("u = edits with p_new(edited) - p_new(original) >= delta, d = edits with <= -delta; pass iff "
               "u >= min_share x (edits of this kind) and exact one-sided sign test P(X >= u | u+d, 1/2) <= alpha")
    return {
        "schema": SCHEMA, "spec_revision": SPEC_REVISION, "experiment": EXPERIMENT, "label": LABEL,
        "arms": list(ARMS), "arm_meaning": ARM_MEANING,
        "seeds": list(SEEDS), "run_order": [list(x) for x in RUN_ORDER], "updates": UPDATES,
        "checkpoints": list(CHECKPOINTS), "loss_window": LOSS_WINDOW, "width": WIDTH, "learning_rate": LEARNING_RATE,
        "clip_norm": CLIP_NORM, "optimizer": OPTIMIZER, "loss": LOSS, "init": INIT, "order": ORDER,
        "numerical_policy": NUMERICAL_POLICY, "expected_torch": EXPECTED_TORCH, "expected_python": EXPECTED_PYTHON,
        "eval_decode_max_tokens": EVAL_DECODE_MAX_TOKENS, "sp1_seed": SP1_SEED, "sp1_size": SP1_SIZE,
        "edit_stride": EDIT_STRIDE, "teach_fit_rows": TEACH_FIT_ROWS, "panels": PANELS,
        "comparison_panels": list(COMPARISON_PANELS), "primary_panels": list(PRIMARY_PANELS),
        "missing_panel": MISSING_PANEL, "b_package": B_PACKAGE,
        "smoke": {"updates": SMOKE_UPDATES, "checkpoints": list(SMOKE_CHECKPOINTS),
                  "panel_stride": SMOKE_STRIDE, "edit_row_stride": SMOKE_EDIT_STRIDE,
                  "reload": "fresh-process reload of smoke run A_first; SMOKE_RELOAD_FAILED unless RELOAD_REPRODUCED"},
        "time": {"projection_safety": str(PROJECTION_SAFETY), "reload_allowance_seconds": RELOAD_ALLOWANCE_SECONDS,
                 "run_wall_seconds": RUN_WALL_SECONDS, "job_wall_seconds": JOB_WALL_SECONDS},
        "edits": {"kind_rule": EDIT_KIND_RULE, "value_counts": VALUE_EDIT_COUNTS,
                  "presence_counts": PRESENCE_EDIT_COUNTS, "value_edit_count": VALUE_EDIT_COUNT,
                  "presence_edit_count": PRESENCE_EDIT_COUNT, "value_columns": list(EDIT_VALUE_COLUMNS)},
        "rules": {"T1": {"field": T1_FIELD, "alpha": str(T1_ALPHA), "panel": "SP1",
                         "null_rate": "max(most-frequent noetic rate in the arm's teaching pool, "
                                      "most-frequent noetic rate among the SP1 targets)",
                         "sp1_noetic_null": str(SP1_NOETIC_NULL), "a_pool_noetic_null": str(A_POOL_NOETIC_NULL),
                         "test": "exact one-sided binomial P(X >= k | n, p0) <= alpha, on grammar-masked "
                                 "teacher-forced choices at every noetic position of SP1"},
                  "T2V": {"delta": T2_DELTA, "min_share": str(T2_MIN_SHARE), "alpha": str(T2_ALPHA),
                          "panel": "EDIT64 VALUE edits only (%d)" % VALUE_EDIT_COUNT, "test": t2_test,
                          "meaning": "field-value reading with the correct previous tokens"},
                  "T2P": {"delta": T2_DELTA, "min_share": str(T2_MIN_SHARE), "alpha": str(T2_ALPHA),
                          "panel": "EDIT64 PRESENCE edits only (%d)" % PRESENCE_EDIT_COUNT, "test": t2_test,
                          "meaning": "reading of drive/register presence (input length or layout) only"},
                  "T2_ALL_EDITS": "reported, never decisive",
                  "T3": {"min_distinct": T3_MIN_DISTINCT, "panel": "SP1",
                         "test": "distinct free-decoded token sequences on SP1 >= min_distinct",
                         "meaning": "free generation has not collapsed. NOT evidence of field-value reading: a "
                                    "structure-only reader reaches 180 distinct outputs on SP1. Separates FULL from "
                                    "TEACHER_FORCED_ONLY"},
                  "NONE": {"distinct_free_outputs": NONE_DISTINCT_FREE_OUTPUTS, "panel": "SP1",
                           "meaning": "TOTAL collapse only: T1, T2V and T2P all fail and the run gives exactly %d "
                                      "distinct free output over the 256 SP1 rows; 2 or more is never NONE "
                                      "(coordinator decision 1 of 2026-09-24)" % NONE_DISTINCT_FREE_OUTPUTS},
                  "LEVELS": "checked in order, with D = distinct free outputs on SP1: FULL = T1 and T2V and T3; "
                            "TEACHER_FORCED_ONLY = (T1 or T2V) and not T3; PARTIAL_FIELDS = T3 and exactly one of "
                            "T1, T2V; STRUCTURE_OR_OUTPUT_VARIATION = not T1 and not T2V and (T2P or D >= 2); "
                            "NONE = not T1 and not T2V and not T2P and D = 1",
                  "CALIBRATION_GUARD": "fires iff some run passes T1, T2V or T2P at checkpoint 0. Distinct free "
                                       "outputs (and so T3) are NOT in the guard: an untrained model's free outputs "
                                       "may vary. The checkpoint-0 distinct-output count of every run is reported",
                  "ARM": "SHOWS_INPUT_USE iff FULL in at least %d valid runs; SHOWS_NO_INPUT_USE iff NONE in at "
                         "least %d valid runs and every run of the arm that has a FINAL reading (valid or not) is "
                         "NONE; INPUT_USE_UNDETERMINED otherwise" % (ARM_MIN_SEEDS, ARM_MIN_VALID_NONE_RUNS),
                  "ARCHITECTURE_CHANGE_JUSTIFIED": "calibration guard silent, every run that has a FINAL reading "
                                                   "(valid or not) is NONE, and each arm has at least %d valid NONE "
                                                   "runs (coordinator decision 3 of 2026-09-24)"
                                                   % ARM_MIN_VALID_NONE_RUNS,
                  "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE": "calibration guard silent and some arm "
                                                                         "SHOWS_INPUT_USE; teaching fit is not tested",
                  "ARCHITECTURE_DECISION_INCOMPLETE": "otherwise, with every reason that applies from %s"
                                                      % ", ".join(ARCHITECTURE_REASONS),
                  "FIELDS_NOT_READ_IN_ANY_RUN": "information only; justifies nothing by itself: emitted iff at least "
                                                "one run has a FINAL reading and no run passes T1 or T2V at the FINAL "
                                                "checkpoint (valid or not); names the target for a later, separately "
                                                "approved design discussion (coordinator decision 4 of 2026-09-24)",
                  "B_BEATS_A": "per seed pair, exact canonical tree, paired rows: b = B exact and A not, c = A exact "
                               "and B not; b > c and P(X >= b | b+c, 1/2) <= %s" % PAIR_ALPHA,
                  "LESSONS_HELP": "B_BEATS_A in all 3 seed pairs, per panel",
                  "LESSONS_OVERALL": "over the primary panels SP1 and SP2U, in order: NOT_EVALUATED if either is; "
                                     "COMPARISON_INCOMPLETE if either is; MIXED if one is HELP and the other HURT; "
                                     "HURT if either is HURT; HELP if both are HELP; EFFECT_NOT_SHOWN otherwise"},
        "digests": {"q3_manifest": Q3_MANIFEST_SHA256, "run_001_plan": RUN_001_PLAN_SHA256,
                    "run_001_weights": RUN_001_WEIGHTS_SHA256, "diagnostic_selection": DIAGNOSTIC_SELECTION_DIGEST,
                    "inspected_dev": INSPECTED_DEV_DIGEST, "inspected_train": INSPECTED_TRAIN_DIGEST,
                    "sp1": SP1_DIGEST, "sp2": SP2_DIGEST, "panel_targets": PANEL_TARGETS_DIGEST,
                    "edit_panel": EDIT_PANEL_DIGEST, "edit_kinds": EDIT_KINDS_DIGEST, "a_pool": A_POOL_DIGEST,
                    "a_pool_rows": A_POOL_ROWS, "edit_count": EDIT_COUNT, "value_edit_count": VALUE_EDIT_COUNT,
                    "presence_edit_count": PRESENCE_EDIT_COUNT, "sp1_noetic_null": str(SP1_NOETIC_NULL),
                    "a_pool_noetic_null": str(A_POOL_NOETIC_NULL)},
        "stop_codes": list(STOP_CODES),
    }


def frozen_sha256() -> str:
    return sha(canonical(frozen_record()))


# ---- exact tests (integers and fractions only; no floating point) ----------------------------------------------
def binomial_upper_tail(k: int, n: int, p) -> Fraction:
    """P(X >= k) for X ~ Binomial(n, p), exactly. p is a Fraction (or int) in [0, 1]."""
    p = Fraction(p)
    if type(k) is not int or type(n) is not int or n < 0 or not 0 <= p <= 1:
        raise ValueError("INVALID_BINOMIAL_ARGUMENTS")
    if k <= 0:
        return Fraction(1)
    if k > n:
        return Fraction(0)
    a, b = p.numerator, p.denominator
    c = b - a
    if a == 0:
        return Fraction(0)
    if c == 0:
        return Fraction(1)
    term = comb(n, k) * a ** k * c ** (n - k)          # C(n,i) a^i c^(n-i), then each next term by an exact ratio
    total = term
    for i in range(k, n):
        term = term * (n - i) * a // ((i + 1) * c)
        total += term
    return Fraction(total, b ** n)


def sign_test_upper(wins: int, losses: int) -> Fraction:
    """Exact one-sided sign test: P(X >= wins | wins + losses, 1/2). Ties are dropped before calling."""
    return binomial_upper_tail(wins, wins + losses, Fraction(1, 2))


def most_frequent_rate(counts: dict) -> Fraction:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("EMPTY_CLASS_COUNTS")
    return Fraction(max(counts.values()), total)


# ---- digests over panel content (the same functions on the laptop, on the machine and in the reader) ------------
def panel_targets_digest(rows) -> str:
    """rows: (id, target_tokens, slot_kinds) of SP1 then SP2, in panel order."""
    return sha(canonical([[i, list(tokens), list(kinds)] for i, tokens, kinds in rows]))


def edit_kind(field, old, new) -> str:
    """'presence' when a drive or register is added or removed (the input text changes length); else 'value'."""
    return "presence" if field in ("drive", "register") and "None" in (str(old), str(new)) else "value"


def edit_kinds_digest(items) -> str:
    """items: (row id, target position, kind) of every MEASURABLE edit, in edit order."""
    return sha(canonical([[row, position, kind] for row, position, kind in items]))


# ---- the decision functions (the reader calls these; the spec and the record above say the same in words) -------
def input_use_level(t1: bool, t2v: bool, t2p: bool, distinct: int) -> str:
    """One run at one checkpoint. distinct = distinct free outputs over the SP1 rows; T3 = distinct >= T3_MIN_DISTINCT.
    See LEVELS; every combination of T1, T2V, T2P and the distinct count has exactly one level."""
    if type(distinct) is not int or distinct < NONE_DISTINCT_FREE_OUTPUTS:
        raise ValueError("INVALID_DISTINCT_FREE_OUTPUTS")
    t3 = distinct >= T3_MIN_DISTINCT
    if t1 and t2v and t3:
        return "FULL"
    if t1 or t2v:
        return "PARTIAL_FIELDS" if t3 else "TEACHER_FORCED_ONLY"
    if t2p or distinct > NONE_DISTINCT_FREE_OUTPUTS:
        return "STRUCTURE_OR_OUTPUT_VARIATION"
    return "NONE"


def calibration_guard_fires(checkpoint_0_tests) -> bool:
    """checkpoint_0_tests: (T1, T2V, T2P) of every run that has a checkpoint-0 reading. Distinct outputs are not used."""
    return any(t1 or t2v or t2p for t1, t2v, t2p in checkpoint_0_tests)


def arm_label(arm: str, finals) -> str:
    """finals: (FINAL level, run is valid) of every run of this arm that HAS a FINAL reading, valid or not.
    Runs with no FINAL reading (missing, or an unreadable final checkpoint) are left out."""
    finals = [(level, bool(valid)) for level, valid in finals]
    valid_levels = [level for level, valid in finals if valid]
    if valid_levels.count("FULL") >= ARM_MIN_SEEDS:
        return "ARM_%s_SHOWS_INPUT_USE" % arm
    if (valid_levels.count("NONE") >= ARM_MIN_VALID_NONE_RUNS
            and all(level == "NONE" for level, _ in finals)):
        return "ARM_%s_SHOWS_NO_INPUT_USE" % arm
    return "ARM_%s_INPUT_USE_UNDETERMINED" % arm


def architecture_decision(finals_by_arm: dict, guard_fires: bool):
    """(label, reasons). finals_by_arm: arm -> (FINAL level, valid) of every run of that arm with a FINAL reading."""
    if guard_fires:
        return "ARCHITECTURE_DECISION_INCOMPLETE", ["INPUT_USE_RULE_FIRES_AT_INITIALISATION"]
    finals = {arm: [(level, bool(valid)) for level, valid in finals_by_arm.get(arm, ())] for arm in ARMS}
    labels = {arm: arm_label(arm, finals[arm]) for arm in ARMS}
    if any(label.endswith("_SHOWS_INPUT_USE") for label in labels.values()):
        return "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE", []
    if all(label.endswith("_SHOWS_NO_INPUT_USE") for label in labels.values()):
        return "ARCHITECTURE_CHANGE_JUSTIFIED", []
    present = [level for arm in ARMS for level, _ in finals[arm]]
    reasons = [level for level in ("TEACHER_FORCED_ONLY", "PARTIAL_FIELDS", "STRUCTURE_OR_OUTPUT_VARIATION")
               if level in present]
    if "FULL" in present:
        reasons.append("SEED_DEPENDENT")
    if any(level != "NONE" and not valid for arm in ARMS for level, valid in finals[arm]):
        reasons.append("NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID")
    if any(sum(1 for _, valid in finals[arm] if valid) < ARM_MIN_VALID_RUNS for arm in ARMS):
        reasons.append("TOO_FEW_VALID_RUNS")
    if not reasons:                                   # cannot happen (a test enumerates the cases); fail loudly
        raise ValueError("ARCHITECTURE_INCOMPLETE_WITHOUT_A_REASON")
    return "ARCHITECTURE_DECISION_INCOMPLETE", reasons


def fields_not_read_in_any_run(final_levels) -> bool:
    """Information only (decision 4). final_levels: the FINAL level of every run that has a FINAL reading, valid or
    not. True iff there is at least one such run and none passes T1 or T2V (none is in FIELD_LEVELS)."""
    final_levels = list(final_levels)
    return bool(final_levels) and not any(level in FIELD_LEVELS for level in final_levels)


def overall_lessons(per_panel: dict) -> str:
    """per_panel: panel -> one of LESSON_OUTCOMES. The one overall answer over PRIMARY_PANELS."""
    outcomes = [per_panel[p] for p in PRIMARY_PANELS]
    if "NOT_EVALUATED" in outcomes:
        return "NOT_EVALUATED"
    if "COMPARISON_INCOMPLETE" in outcomes:
        return "COMPARISON_INCOMPLETE"
    if "HELP" in outcomes and "HURT" in outcomes:
        return "MIXED"
    if "HURT" in outcomes:
        return "HURT"
    if all(x == "HELP" for x in outcomes):
        return "HELP"
    return "EFFECT_NOT_SHOWN"
