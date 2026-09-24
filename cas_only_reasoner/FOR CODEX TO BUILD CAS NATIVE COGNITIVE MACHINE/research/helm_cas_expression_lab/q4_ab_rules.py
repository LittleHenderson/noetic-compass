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
T2_DELTA = 0.01                             # 2,700 x the largest move the saved model showed (3.6378e-06)
T2_MIN_SHARE = Fraction(1, 10)
T2_ALPHA = Fraction(1, 100)
T3_MIN_DISTINCT = 32                        # of the 256 SP1 rows; the saved model gave 1 distinct output of 96
PAIR_ALPHA = Fraction(1, 100)
ARM_MIN_SEEDS = 2                           # "at least 2 of its 3 seeds"

# ---- digests measured on the laptop from VISIBLE Q3 v0.7 files (pure Python, 2026-09-24) ------------------------
Q3_MANIFEST_SHA256 = "1cf98a2b48ade4acf12c51c0cc74d3dd2504f7eb0e7d24662fe8b6f7d29f8bf9"
RUN_001_PLAN_SHA256 = "9dacc83627422d704c9db58f5ddbac82936e7d52211ec061247419fbad78095c"
RUN_001_WEIGHTS_SHA256 = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
DIAGNOSTIC_SELECTION_DIGEST = "0b98bfc94a5aed8af2d4fef72378fec7dfa9d46808b09ff30f750972387a3059"
INSPECTED_DEV_DIGEST = "d91d914b93a9f131110cce59efb09028f8b71387107a5fe53ffc51ed6ee10105"
INSPECTED_TRAIN_DIGEST = "1131a9c34c06de6c106c902a039379b9d6b10d795bc268da490763f296a145c8"
SP1_DIGEST = "dab48792e0a7382c3e224e7c027d677405983b8a67cd522e59ef7add25cfc122"
EDIT_PANEL_DIGEST = "05d62b99f52db1a3b2a6511ffe0bb091b9415cc772474bb58d43a72b757c94d2"
A_POOL_DIGEST = "9064635d86c95ae4886e24ce63810b9d216e22106a10d2645a9efdfe91e21a08"
A_POOL_ROWS = 1792
EDIT_COUNT = 773                           # measurable edits on EDIT64 (11 more leaf fields have no compilable edit)

STOP_CODES = (
    "GPU_REQUIRED", "RUNTIME_VERSION_MISMATCH", "CUBLAS_WORKSPACE_CONFIG_DIFFERS", "GPU_BUSY_OR_UNKNOWN",
    "CUSTODY_REFUSED", "RUN_001_RECORDS_INCONSISTENT", "Q3_DATA_NOT_PINNED", "COMPILER_ENGINE_NOT_PYTHON",
    "PANEL_DIGEST_MISMATCH", "B_PACKAGE_NOT_PINNED", "B_PIN_NOT_THE_FROZEN_PACKAGE", "B_PACKAGE_BUILD_FAILED",
    "B_PACKAGE_MISMATCH", "STAGE0_NOT_REPRODUCED", "REINIT_NOT_REPRODUCED", "SMOKE_NONDETERMINISTIC",
    "SMOKE_PAIR_INIT_MISMATCH", "SMOKE_FAILED", "PROJECTED_OVER_TIME", "NUMERICAL_FAILURE", "RUN_WALL_LIMIT",
    "JOB_WALL_LIMIT",
)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def frozen_record() -> dict:
    """Every frozen value, as JSON. The runner copies it into its results; the reader compares it with its own."""
    return {
        "schema": SCHEMA, "experiment": EXPERIMENT, "label": LABEL, "arms": list(ARMS), "arm_meaning": ARM_MEANING,
        "seeds": list(SEEDS), "run_order": [list(x) for x in RUN_ORDER], "updates": UPDATES,
        "checkpoints": list(CHECKPOINTS), "loss_window": LOSS_WINDOW, "width": WIDTH, "learning_rate": LEARNING_RATE,
        "clip_norm": CLIP_NORM, "optimizer": OPTIMIZER, "loss": LOSS, "init": INIT, "order": ORDER,
        "numerical_policy": NUMERICAL_POLICY, "expected_torch": EXPECTED_TORCH, "expected_python": EXPECTED_PYTHON,
        "eval_decode_max_tokens": EVAL_DECODE_MAX_TOKENS, "sp1_seed": SP1_SEED, "sp1_size": SP1_SIZE,
        "edit_stride": EDIT_STRIDE, "teach_fit_rows": TEACH_FIT_ROWS, "panels": PANELS,
        "comparison_panels": list(COMPARISON_PANELS), "b_package": B_PACKAGE,
        "smoke": {"updates": SMOKE_UPDATES, "checkpoints": list(SMOKE_CHECKPOINTS),
                  "panel_stride": SMOKE_STRIDE, "edit_row_stride": SMOKE_EDIT_STRIDE},
        "time": {"projection_safety": str(PROJECTION_SAFETY), "reload_allowance_seconds": RELOAD_ALLOWANCE_SECONDS,
                 "run_wall_seconds": RUN_WALL_SECONDS, "job_wall_seconds": JOB_WALL_SECONDS},
        "rules": {"T1": {"field": T1_FIELD, "alpha": str(T1_ALPHA), "panel": "SP1",
                         "null_rate": "max(most-frequent noetic rate in the arm's teaching pool, "
                                      "most-frequent noetic rate among the SP1 targets)",
                         "test": "exact one-sided binomial P(X >= k | n, p0) <= alpha, on grammar-masked "
                                 "teacher-forced choices at every noetic position of SP1"},
                  "T2": {"delta": T2_DELTA, "min_share": str(T2_MIN_SHARE), "alpha": str(T2_ALPHA),
                         "panel": "EDIT64",
                         "test": "u = edits with p_new(edited) - p_new(original) >= delta, d = edits with <= -delta; "
                                 "pass iff u >= min_share x edits and exact one-sided sign test P(X >= u | u+d, 1/2) "
                                 "<= alpha"},
                  "T3": {"min_distinct": T3_MIN_DISTINCT, "panel": "SP1",
                         "test": "distinct free-decoded token sequences on SP1 >= min_distinct"},
                  "INPUT_USE_DETECTED": "T1 and T2 and T3",
                  "ARCHITECTURE_CHANGE_JUSTIFIED": "no arm shows INPUT_USE_DETECTED at the FINAL checkpoint in at "
                                                   "least %d of its 3 seeds" % ARM_MIN_SEEDS,
                  "B_BEATS_A": "per seed pair, exact canonical tree, paired rows: b = B exact and A not, c = A exact "
                               "and B not; b > c and P(X >= b | b+c, 1/2) <= %s" % PAIR_ALPHA,
                  "LESSONS_HELP": "B_BEATS_A in all 3 seed pairs, per panel"},
        "digests": {"q3_manifest": Q3_MANIFEST_SHA256, "run_001_plan": RUN_001_PLAN_SHA256,
                    "run_001_weights": RUN_001_WEIGHTS_SHA256, "diagnostic_selection": DIAGNOSTIC_SELECTION_DIGEST,
                    "inspected_dev": INSPECTED_DEV_DIGEST, "inspected_train": INSPECTED_TRAIN_DIGEST,
                    "sp1": SP1_DIGEST, "edit_panel": EDIT_PANEL_DIGEST, "a_pool": A_POOL_DIGEST,
                    "a_pool_rows": A_POOL_ROWS, "edit_count": EDIT_COUNT},
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
