"""BOARD *CHANGE* TEST -- runner for PREREG_BOARD_CHANGE_V1.md.

STANDALONE AND NEW. This file does not import, read or modify next_board_test.py,
PREREG_NEXT_BOARD_V1.md, compliance_check.py or PREREG_BOARD_CHANGE_V1.md. Every
constant here is a NEW NAME in a NEW FILE (prereg s17). It reuses only the shared
transport infrastructure in docs/working/gate2_closure/independent_bank/ (providers,
pilot_label, l1_agreement) and the six-code board rubric, which s6.1 requires VERBATIM.

WHAT IT TESTS (prereg s2)
    CLAIM 1 -- DETECTION (retrospective). When the kind of response changes between
        assistant turn N and turn N+1, does the board lens (applied to each turn IN
        ISOLATION, producing the indicator b_N != b_{N+1}) see it, better than a surface
        model reading the same two texts?
    CLAIM 2 -- EARLY WARNING (prospective). Is there a signal in turn N ALONE that a
        change is coming at N+1, before N+1 exists? Reported ONLY on the MODEL-INITIATED
        subset. Gated at 2x the margin, 5x the permutation strictness, p99 not p95, and
        with two downgrade gates promoted to hard kills.

THE THREE READER PANELS (prereg s6) -- the non-circularity is the whole point
    T-BOARD  sees ONE assistant turn, with the board rubric. Never a neighbour, never a
             user turn, never a turn index, never a conversation id.
    T-CHANGE sees the PAIR of assistant turns and is NEVER given the board rubric, any
             board name, or any board vocabulary. This is the GROUND TRUTH.
    T-USER   sees ONLY the two user messages, never a model reply. Decides whether the
             second asks for a different KIND of response than the first. This is what
             splits USER-INDUCED (trivial) from MODEL-INITIATED (the interesting case).
    No panel can derive another panel's answer key: the item views do not overlap and
    the vocabularies do not overlap.

PRIMARY METRIC (prereg s7)
    F1 on the CHANGE class, co-required with MCC > 0, with precision, recall, the base
    rate beside every figure and the full 2x2 confusion matrix. ACCURACY IS FORBIDDEN AS
    A HEADLINE and is written only as a diagnostic, always next to the base rate.

USAGE
    python board_change_test.py --smoke                      # mechanical only. RUN FIRST.
    python board_change_test.py --pilot --stage generate
    python board_change_test.py --pilot --stage label --task change
    python board_change_test.py --pilot --stage label --task user
    python board_change_test.py --pilot --stage label --task board
    python board_change_test.py --pilot --stage gate0
    python board_change_test.py --pilot --stage pilot-size   # r-hat + the resize rule
    python board_change_test.py --pilot --stage analyze

    Both API stages CHECKPOINT to JSONL as each unit lands and SKIP completed units on
    restart, so a crash never costs the spend.

PILOT SPEND GATE (prereg s8.3 / s15)
    16 Stratum N conversations, ~409 calls, $6-$18. A pilot CANNOT PASS Gate 0 -- 144
    possible pairs against a 240-pair floor -- and is a RED-LIGHT-ONLY check. A pilot
    VACUOUS is not a stop signal and must not be read as one.
"""
import os
import re
import sys
import json
import math
import time
import random
import hashlib
import argparse
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.abspath(os.path.join(HERE, "..", "gate2_closure", "independent_bank"))
if BANK_DIR not in sys.path:
    sys.path.insert(0, BANK_DIR)

import providers                                          # noqa: E402,F401
from pilot_label import call_with_retry, MODELS           # noqa: E402
from l1_agreement import fleiss_kappa                     # noqa: E402
from gen_real_outputs import PROMPTS as BANK_PROMPTS      # noqa: E402
from openai import OpenAI                                 # noqa: E402

import numpy as np                                        # noqa: E402
from sklearn.feature_extraction.text import (             # noqa: E402
    TfidfVectorizer, CountVectorizer)
from sklearn.linear_model import LogisticRegression       # noqa: E402
from sklearn.preprocessing import OneHotEncoder           # noqa: E402
from sklearn.model_selection import GroupKFold            # noqa: E402

try:   # Windows console is cp1252 and provider errors carry non-latin text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PREREG_PATH = os.path.join(HERE, "PREREG_BOARD_CHANGE_V1.md")
BLIND_SEED_PATH = os.path.join(HERE, "board_change_seeds_blind.json")

# =====================================================================
# FROZEN CONSTANTS -- all NEW names in a NEW file (prereg s17)
# =====================================================================
BC_ORDER = ["gemini", "deepseek", "qwen", "glm"]
# Matched to pilot_label._SEM. The pools are sized to this SUM so a worker blocked on
# the GLM Semaphore(1) never starves gemini / deepseek / qwen. Raising --workers does
# NOT raise GLM throughput; it produces 429 storms (prereg s13, recorded dead end).
BC_PROVIDER_CONCURRENCY = {"gemini": 4, "deepseek": 2, "qwen": 2, "glm": 1}

BC_MAXTOK_LABEL = 16000          # DEFECT 2 fix (prereg s5.5)
BC_MAXTOK_LABEL_GLM = 20000      # "reader max_tokens is raised for glm-4.6 specifically"
BC_MAXTOK_GEN = 800              # prereg s5.5, AS WRITTEN. See the warning below.
BC_GEN_TEMPERATURE = 0.7

# ---------------------------------------------------------------------------
# MEASURED DEFECT IN THE PREREGISTERED GENERATION BUDGET -- 2026-08-19, PRE-SPEND
#
# At the preregistered generation budget of max_tokens=800, THREE OF THE FOUR FROZEN
# GENERATORS CANNOT PRODUCE A USABLE TURN. Measured, not inferred:
#
#   gemini-2.5-flash  800 -> finish='length', answer 121-131 chars, completion_tokens=30.
#                            Its thinking tokens are billed against max_tokens but are
#                            NOT returned, so the visible answer is truncated to well
#                            under the prereg's own MIN_TURN_CHARS=200 floor.
#                     4000 -> finish='stop', answer 3392 chars.
#   glm-4.6           800 -> finish='length', answer 0 chars, reasoning 3252 chars,
#                            completion_tokens=800. The reasoning trace consumes the
#                            ENTIRE budget before any answer is emitted.
#                     2000 -> finish='stop', answer 3675 chars.
#   deepseek-v4-pro   800 -> passes at turn 0 (answer 1748c / reasoning 1721c) and fails
#                            as the conversation context grows.
#   qwen3.8-max       800 -> passes.
#
# End-to-end at 800, an 8-conversation smoke produced 2 SURVIVING CONVERSATIONS, BOTH
# qwen. gemini, deepseek and glm produced zero.
#
# s5.5's DEFECT 1 ("a 25x generator length gap ... gemini produced ~140-character turns")
# MISDIAGNOSES THIS. That gap was never a generator style property; it is the thinking /
# reasoning trace eating max_tokens, which is the SAME failure s5.5 correctly diagnoses
# as DEFECT 2 and fixes for the READER path by raising max_tokens to 16000. The remedy
# s5.5 prescribes for the generation path -- MIN_TURN_CHARS + regeneration + truncation
# -- CANNOT WORK, because a budget ceiling is deterministic: every regeneration attempt
# hits the identical wall.
#
# Raising this constant is a PREREGISTRATION AMENDMENT and must be recorded in s18 with a
# timestamp and a reason. It is an OWNER DECISION, not the runner's. The frozen value is
# therefore left in place and --gen-max-tokens exists so the amendment, if made, is
# explicit, one flag wide, and recorded in the report as a deviation.
# ---------------------------------------------------------------------------
BC_GEN_BUDGET_DEFECT = (
    "At the preregistered max_tokens=800, gemini-2.5-flash returns 121-131 visible chars "
    "(finish='length'; thinking tokens billed but not returned), glm-4.6 returns 0 chars "
    "(reasoning trace consumes the whole budget), and deepseek-v4-pro fails as context "
    "grows. An 8-conversation smoke yielded 2 surviving conversations, both qwen. s5.5's "
    "DEFECT 1 misdiagnoses this as a generator length gap; regeneration cannot fix a "
    "deterministic budget ceiling. Raising the budget is a s18 amendment and an owner "
    "decision.")

BC_TURNS_PER_CONV = 10           # prereg s5.2
BC_MIN_TURN_CHARS = 200          # DEFECT 1 fix (prereg s5.5)
BC_MAX_REGEN = 2
BC_MIN_TURNS = 6
BC_READER_TRUNC_CHARS = 1000     # prereg s6.1
BC_GEN_LENGTH_RATIO_FLAG = 3.0   # prereg s5.5

BC_N_NEUTRAL_FULL = 60           # prereg s5.2
BC_N_SHIFT_FULL = 20
BC_N_PILOT = 16

BC_REPAIR_ROUNDS = 2             # prereg s6.4
BC_REPAIR_BATCH = 3

BC_SEED_PROMPT_ORDER = 4102
BC_SEED_FOLLOWUP_N_BASE = 811000
BC_SEED_FOLLOWUP_S_BASE = 822000
BC_SEED_BATCH_BASE = {"board": 61000, "change": 62000, "user": 63000}
BC_SEED_ALIAS_BASE = 96000
BC_SEED_TRIVIAL_RANDOM = 31337   # the "random at the base rate" degenerate strategy

BC_BOOT_N = 2000                 # prereg s8.4
BC_BOOT_SEED = 7
BC_BOOT_LOWER_Q = 5
BC_PERM_TRIALS = 1000            # prereg s9 CONTROL 3
BC_PERM_SEED = 0
BC_C_GRID = (0.25, 1.0, 4.0, 16.0)   # prereg s9

# ---- GATE 0 (prereg s10.1) -------------------------------------------------
BC_G0_KAPPA_MIN_BOARD = 0.35
BC_G0_KAPPA_MIN_CHANGE = 0.35
BC_G0_KAPPA_MIN_USER = 0.30
BC_G0_COMPLETE_N_MIN = 60
BC_G0_RAW_KAPPA_COMPONENT = 0.35
BC_G0_RAW_ABSOLUTE_FLOOR = 0.50
BC_G0_COMPLETE_CASE_COVERAGE_MIN = 0.60
BC_G0_BOARD_CONSENSUS_COVERAGE_MIN = 0.70
BC_G0_PAIR_CONSENSUS_COVERAGE_MIN = 0.75
BC_G0_USER_CONSENSUS_COVERAGE_MIN = 0.75
BC_G0_B0_SHARE_MAX = 0.40
BC_G0_COLLISIONS_MAX = 0
BC_G0_MIN_ANALYSABLE_PAIRS = 240
BC_USER_PANEL_POSITIVE_CONTROL_MIN = 0.50

# ---- CLAIM GATES (prereg s10.2 / s10.3) ------------------------------------
BC_C1_MARGIN = 0.05
BC_C2_MARGIN = 0.10
BC_C1_PERM_ALPHA = 0.05
BC_C2_PERM_ALPHA = 0.01
BC_G2_MIN_CHANGES = 40
BC_G2_MIN_PAIRS = 150
BC_KILL_KAPPA_CHANGE = 0.20                  # prereg s13 instrument kill
BC_GROUND_TRUTH_SURFACE_FLAG = 0.667         # prereg s9 CONTROL 1 diagnostic

# ---- PILOT RESIZE RULE (prereg s8.3) ---------------------------------------
BC_PILOT_PAIRS_PER_CONV = 2.98   # 9 * c^2(0.49) * c_p(0.75) * P(SAME-KIND|N)(0.90)
BC_PILOT_STOP_RATE = 0.10
BC_RESIZE_MIN = 60
BC_RESIZE_MAX = 120

# =====================================================================
# USER-TURN BANKS (prereg s5.3) -- i.i.d. WITH REPLACEMENT, mandatory.
# A permutation draw would make f_t and f_{t+1} dependent and manufacture a
# turn-to-turn dependence with zero board content. Inherited fatal fix.
# =====================================================================
BC_CONTINUERS = [                # Stratum N -- request no particular kind of response
    ("C1", "Go on."),
    ("C2", "Say more about that."),
    ("C3", "Keep going."),
    ("C4", "Mm-hm."),
    ("C5", "And?"),
]
BC_SHIFTERS = [                  # Stratum S -- the retired design's bank, unchanged
    ("U1", "Say more about that."),
    ("U2", "What's the strongest case against what you just said?"),
    ("U3", "I don't think that's right. Convince me, or change your mind."),
    ("U4", "Okay — what should I actually do first?"),
    ("U5", "How would you know if you were wrong here?"),
]
BC_SHIFT_POSITIVE_CONTROL_ID = "U4"   # prereg s3.2

# =====================================================================
# READER RUBRICS
# =====================================================================
# T-BOARD -- VERBATIM from the retired design (prereg s6.1 requires this): the same six
# codes, the same reader-facing behaviour descriptions, the same five disambiguators.
# Readers never see the words CAS, TKS, Noetic, board, CCB, or any board name.
BC_BOARDS = ["B1", "B2", "B3", "B4", "B5", "B0"]
BC_RUBRIC_BOARD = """You will read short excerpts of assistant answers, one at a time.
For EACH excerpt, choose the ONE label below that best describes what the answer is
mainly doing. These are descriptions of behaviour, nothing more.

B1 - Decides whether to answer or to decline.
   Resolves to one of two clear paths: a real answer OR an explicit refusal - not a
   hedged blend. Once it declines, it stays declined. States a firm standing principle
   that the request cannot renegotiate. Surfaces BOTH what pulls it toward the request
   and what pushes it away from THAT SAME ONE request, then nets them into one verdict.
   May re-read an ambiguous request and name the alternative meanings before judging.
   Leaves a reason trail: what it caught, which consideration decided it, why.

B2 - About how OFTEN something repeats, not what it is.
   Names or clearly implies a rate ("every two hours", "like clockwork"). Describes a
   CYCLE that runs a fixed ordered sequence and returns to its own start, not a one-off.
   Talks about how rigid the pattern is - how hard it is to knock off its own rate (a
   loose preference vs a self-restoring compulsion). Talks about pulling an internal
   rhythm into step with an outside one, and about changing it by slow incremental drag
   rather than a jump. Or about how LONG each episode runs at the same frequency.

B3 - Holds TWO distinct things side by side and compares them.
   Explicitly discards what the two share ("both agree on X, which tells you nothing")
   and spends its words on how they diverge. Names the KIND of difference, not its size -
   never a bare score, never just "A differs from B". Insists both sides are judged
   against the SAME single yardstick, and flags it as a defect if they were weighed on
   different standards. Guards against inflating a trivial divergence into a false
   dichotomy.

B4 - Finds past cases by RESEMBLANCE OF SHAPE, not by keyword.
   "This is like the time when...", "I've seen this kind of pressure before, three times" -
   matching cases whose surface wording shares nothing. Talks about what is held deeply
   and near-permanently versus what fades fast, with rehearsal framed as a deliberate
   policy. Reports what is ABSENT - names gaps in its own experience, and separates
   never-encountered from encountered-then-faded. Summarises an episode as a SEQUENCE OF
   MOVES rather than quoting the sentence. Says vivid, high-stakes events were written
   hard and routine ones barely moved the needle.

B5 - About CAPACITY, not content.
   Whether there is enough left to do the work at all: fatigue, depletion, budget,
   headroom. Treats ordering as a hard gate: refuses to act until the governing principle
   is loaded first, and sequences explicitly before engaging. Budgets and throttles -
   allocates a limited resource across competing demands, caps how much any one demand
   may pull, deliberately keeps reserve. Names a ladder of tiers - warn, then rest, then
   stop - ending in explicit SILENCE, not a degraded answer. Names confident output from
   an exhausted system as the worst failure.

B0 - None of the five above is clearly doing the dominant work in this excerpt.

HOW TO CHOOSE - read these before you label anything:

1. COUNT THE INPUTS. B1 also weighs a pull-toward against a push-away - but on ONE
   request. B3 needs TWO SEPARATE THINGS being compared. The words "difference",
   "differential", "on the one hand / on the other" do NOT by themselves make it B3.
   Count how many distinct things are on the table.
2. A SAFETY TOPIC DOES NOT MAKE IT B1. An excerpt can compare a request against a
   known-safe baseline; that is two inputs and cancellation of what they share, so it is
   B3, however safety-flavoured it reads.
3. B2 vs B5. Both use energy and rhythm words. B2 is about how OFTEN and how LOCKED a
   repeating behaviour is (rate, cycle, rigidity, episode length). B5 is about whether
   there is ENOUGH, what ORDER things must happen in, and when to STOP.
4. REPETITION ALONE IS NOT B2. B2 needs rate plus cycle plus rigidity together. A passing
   mention that something happens repeatedly is not enough.
5. PICK THE DOMINANT ONE. Real answers mix. Choose the single label doing the most work.
   If none dominates, choose B0. B0 is a legitimate answer, not a failure - choosing it
   honestly is better than forcing a fit."""

# T-CHANGE -- the GROUND TRUTH panel. Sees the PAIR. Contains NO board rubric, NO board
# name, NO board vocabulary. Neither panel can derive the other's answer (prereg s6.2).
BC_RUBRIC_CHANGE = """You will read pairs of short excerpts. Each pair is two consecutive
reply turns from the same conversation, in the order they were said. They are labelled
FIRST and SECOND.

For EACH pair, decide ONE thing:

    Did the KIND of response change between FIRST and SECOND?

CHANGE - SECOND is a different KIND of response from FIRST. The reply turned from one
   sort of move to another sort of move.
SAME - SECOND is the same KIND of response as FIRST. It goes on doing the same sort of
   thing, even where the content has moved on.

HOW TO CHOOSE - read these before you label anything:

1. JUDGE THE KIND OF RESPONSE, NOT THE SUBJECT MATTER. New details, new examples, or a
   new sub-topic inside the same sort of reply are SAME.
2. JUDGE WHAT THE REPLY IS DOING, not how long it is or how it is laid out. A change of
   formatting on its own is not a change of kind.
3. You do not see what the person said between the two turns. Do not guess it.
4. Every pair gets exactly one answer, and it must be CHANGE or SAME. There is no
   'unsure' option and no third answer."""

# T-USER -- sees ONLY the two user messages. Never a model reply (prereg s3.1 / s6.3).
BC_RUBRIC_USER = """You will read pairs of short messages. Each pair is two things the
same person said to an assistant, in the order they said them. They are labelled FIRST
and SECOND.

For EACH pair, decide ONE thing:

    Does the SECOND message ask for a different KIND of response than the FIRST?

DIFFERENT-KIND - the second message calls for a different sort of reply than the first
   did. It steers the reply toward something else.
SAME-KIND - the second message calls for the same sort of reply as the first, or it does
   not steer the reply at all. It just asks for more, or signals the person is listening.

HOW TO CHOOSE - read these before you label anything:

1. A message that only asks for more, or only signals that the person is still there,
   does NOT call for a different kind of reply. That is SAME-KIND.
2. A message that redirects what is being asked for DOES call for a different kind of
   reply. That is DIFFERENT-KIND.
3. You do not see any of the replies. Do not guess them.
4. Every pair gets exactly one answer, and it must be DIFFERENT-KIND or SAME-KIND. There
   is no 'unsure' option and no third answer."""

BC_TASKS = {
    "board": {
        "rubric": BC_RUBRIC_BOARD,
        "codes": BC_BOARDS,
        "re": r"\b(B[0-5])\b",
        "menu": "B0|B1|B2|B3|B4|B5",
        "batch": 6,
        "unit": "EXCERPT",
        "noun": "excerpt",
    },
    "change": {
        "rubric": BC_RUBRIC_CHANGE,
        "codes": ["CHANGE", "SAME"],
        "re": r"\b(CHANGE|SAME)\b",
        "menu": "CHANGE|SAME",
        "batch": 4,
        "unit": "PAIR",
        "noun": "pair",
    },
    "user": {
        "rubric": BC_RUBRIC_USER,
        "codes": ["DIFFERENT-KIND", "SAME-KIND"],
        "re": r"\b(DIFFERENT-KIND|SAME-KIND)\b",
        "menu": "DIFFERENT-KIND|SAME-KIND",
        "batch": 12,
        "unit": "PAIR",
        "noun": "pair",
    },
}

_WRITE_LOCK = threading.Lock()


# =====================================================================
# shared helpers
# =====================================================================
def _sha256(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"unavailable: {str(e)[:80]}"


def _client(provider, model):
    bu, key, _ = providers.resolve(provider, model)   # never returns/prints key values
    return OpenAI(api_key=key, base_url=bu)


def _split_text(resp):
    """Return (answer_text, reasoning_text) SEPARATELY.

    deepseek-v4-pro and glm-4.6 routinely return an EMPTY message.content with the
    trace in reasoning_content. Concatenating the two would let a chain-of-thought
    aside ("looks the same, so SAME") be harvested as a considered label, so they are
    kept apart: ONLY the answer may yield labels. The trace is captured for diagnosis.
    """
    msg = resp.choices[0].message
    ans = getattr(msg, "content", None) or ""
    rea = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
    if not ans or not rea:
        try:
            d = msg.model_dump()
            ans = ans or (d.get("content") or "")
            rea = rea or (d.get("reasoning_content") or d.get("reasoning") or "")
        except Exception:
            pass
    return ans or "", rea or ""


def _jsonl_append(path, obj):
    with _WRITE_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _jsonl_read(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _r4(x):
    return None if x is None else round(float(x), 4)


def _trunc(t):
    return (t or "")[:BC_READER_TRUNC_CHARS]


# =====================================================================
# CORPUS PLAN (prereg s5.2 / s5.3 / s5.4)
# =====================================================================
# s5.4 fixes 80 distinct seed prompts: 36 from the existing bank, 44 newly authored
# under blind-author discipline. The family table in s5.4 is explicitly delegated to
# the runner -- "the exact per-stratum allocation is frozen in the runner before
# generation and printed in the report" -- so it is frozen HERE and never touched again:
#
#   Stratum N (60) = 44 blind-authored (F1 9, F2 9, F3 9, F4 9, F5 8) + 16 bank
#   Stratum S (20) = 20 bank
#   36 bank prompts total, 44 new, 80 distinct, NO seed reused across conversations.
#
# The Stratum N order ROUND-ROBINS the six families so that ANY PREFIX is family
# balanced -- which is what makes the 16-conversation pilot representative of the
# corpus it is sizing, and what lets the pilot conversations be retained unchanged in
# the full corpus (s8.3).
BC_FAMILY_PLAN_N = {"F1": 9, "F2": 9, "F3": 9, "F4": 9, "F5": 8, "F6": 16}
BC_FAMILY_PLAN_S = {"F6": 20}
BC_FAMILY_SHAPES = {
    "F1": "factual -> personal",
    "F2": "request -> boundary",
    "F3": "open -> action",
    "F4": "explain -> edge of knowledge",
    "F5": "steady (the honest negatives -- seeds expected NOT to shift)",
    "F6": "mixed / existing bank prompts, unclassified",
}


def load_blind_families():
    """The 44 new seeds, authored WITHOUT sight of the board taxonomy or rubric.

    s5.4: "authored under the same blind-author discipline: the author never sees the
    board taxonomy, the board rubric, or any board name." The bank lives in its own
    file so the blindness is auditable separately from this runner.
    """
    if not os.path.exists(BLIND_SEED_PATH):
        raise SystemExit(
            f"missing blind-authored seed bank {BLIND_SEED_PATH}. s5.4 requires 44 new "
            f"seeds authored without sight of the board taxonomy or rubric.")
    d = json.load(open(BLIND_SEED_PATH, encoding="utf-8"))
    fams = d.get("families") or {}
    for fam, want in (("F1", 9), ("F2", 9), ("F3", 9), ("F4", 9), ("F5", 8)):
        got = fams.get(fam) or []
        if len(got) != want:
            raise SystemExit(f"blind seed bank: family {fam} has {len(got)} seeds, "
                             f"the frozen plan needs {want}")
    return fams, d


def build_corpus_plan():
    """Deterministic full-corpus plan. The pilot is its first BC_N_PILOT Stratum N rows.

    Provenance (stratum, pilot membership, family) is a property of THE PLAN and is
    written into every payload, so s10.4's "provenance is decided by the data, not by a
    CLI flag" is enforceable: analyse recomputes the plan and aborts on any disagreement.
    """
    fams, blind_meta = load_blind_families()
    bank = random.Random(BC_SEED_PROMPT_ORDER).sample(list(BANK_PROMPTS), 36)
    bank_n, bank_s = bank[:BC_FAMILY_PLAN_N["F6"]], bank[BC_FAMILY_PLAN_N["F6"]:]

    queues = [("F1", list(fams["F1"])), ("F2", list(fams["F2"])), ("F3", list(fams["F3"])),
              ("F4", list(fams["F4"])), ("F5", list(fams["F5"])), ("F6", list(bank_n))]
    ordered_n = []
    while any(q for _, q in queues):                    # round-robin -> balanced prefixes
        for fam, q in queues:
            if q:
                ordered_n.append((fam, q.pop(0)))
    if len(ordered_n) != BC_N_NEUTRAL_FULL:
        raise SystemExit(f"Stratum N plan built {len(ordered_n)} seeds, expected "
                         f"{BC_N_NEUTRAL_FULL}")

    plan, seen = [], set()
    for i, (fam, prompt) in enumerate(ordered_n):
        plan.append(_conv_spec(i, "N", fam, prompt))
    for j, prompt in enumerate(bank_s):
        plan.append(_conv_spec(BC_N_NEUTRAL_FULL + j, "S", "F6", prompt))
    for p in plan:
        if p["seed_prompt"] in seen:                    # s5.4: no seed reused, ever
            raise SystemExit(f"seed prompt reused across conversations: "
                             f"{p['seed_prompt'][:60]!r}")
        seen.add(p["seed_prompt"])
    return plan, blind_meta


def _conv_spec(cid, stratum, family, prompt):
    bank_ = BC_CONTINUERS if stratum == "N" else BC_SHIFTERS
    base = BC_SEED_FOLLOWUP_N_BASE if stratum == "N" else BC_SEED_FOLLOWUP_S_BASE
    rng = random.Random(base + cid)
    fups = [rng.choice(bank_) for _ in range(BC_TURNS_PER_CONV - 1)]   # i.i.d. WITH replacement
    prov = BC_ORDER[cid % len(BC_ORDER)]
    return {"conv_id": cid, "stratum": stratum, "family": family, "seed_prompt": prompt,
            "gen_provider": prov, "gen_model": MODELS[prov],
            "is_pilot": bool(stratum == "N" and cid < BC_N_PILOT),
            "followups": fups}


def select_plan(A, full_plan):
    if A.smoke:
        rows = [p for p in full_plan if p["stratum"] == "N"][:A.n_convos]
        return [dict(p, is_smoke=True) for p in rows]
    if A.pilot:
        return [p for p in full_plan if p["stratum"] == "N" and p["is_pilot"]]
    return full_plan


# =====================================================================
# STAGE 1 -- GENERATE  (prereg s5.1 / s5.5)
# =====================================================================
def gen_conversation(spec, n_turns, min_turns, gen_max_tokens=BC_MAXTOK_GEN):
    """One conversation, turns generated SEQUENTIALLY with growing context.

    Real model outputs only -- no templates, no synthetic text, no rendered strings
    (s5.1 binding). DEFECT 1 fix: a turn under BC_MIN_TURN_CHARS is REGENERATED up to
    BC_MAX_REGEN times; if it is still short the conversation is TRUNCATED at the last
    good turn and kept if it reached min_turns. Conversations are never discarded --
    discarding shrinks the binding n and skews the generator mix.
    """
    prov, model = spec["gen_provider"], spec["gen_model"]
    client = _client(prov, model)
    msgs = [{"role": "user", "content": spec["seed_prompt"]}]
    turns, truncated_at, regens = [], None, 0
    for t in range(n_turns):
        if t == 0:
            fid, user_text = "SEED", spec["seed_prompt"]
        else:
            fid, user_text = spec["followups"][t - 1]
            msgs.append({"role": "user", "content": user_text})
        out, why = "", None
        for attempt in range(BC_MAX_REGEN + 1):
            try:
                r = call_with_retry(client, prov, model=model, max_tokens=gen_max_tokens,
                                    temperature=BC_GEN_TEMPERATURE, messages=msgs)
                cand = _split_text(r)[0].strip()
                if r.choices[0].finish_reason != "stop" and len(cand) < BC_MIN_TURN_CHARS:
                    # BUDGET CEILING, not generator style. Regeneration cannot clear it.
                    why = (f"finish={r.choices[0].finish_reason} with {len(cand)}c "
                           f"answer at max_tokens={gen_max_tokens} -- BUDGET CEILING")
                    cand = ""
            except Exception as e:
                why = f"call failed ({str(e)[:90]})"
                cand = ""
            if len(cand) >= BC_MIN_TURN_CHARS:
                out = cand
                break
            if cand:
                why = f"short ({len(cand)} chars < {BC_MIN_TURN_CHARS})"
            if attempt < BC_MAX_REGEN:
                regens += 1
        if not out:
            truncated_at = f"turn {t}: {why}"
            break
        msgs.append({"role": "assistant", "content": out})
        turns.append({"turn_idx": t, "followup_id": fid, "user": user_text,
                      "assistant": out})
    if len(turns) < min_turns:
        raise RuntimeError(f"conv {spec['conv_id']}: only {len(turns)} usable turns "
                           f"({truncated_at})")
    rec = {k: spec[k] for k in ("conv_id", "stratum", "family", "seed_prompt",
                                "gen_provider", "gen_model", "is_pilot")}
    rec.update({"followups": spec["followups"], "truncated_at": truncated_at,
                "n_regens": regens, "turns": turns})
    return rec


def stage_generate(A, plan):
    existing = {r["conv_id"] for r in _jsonl_read(A.conv_file)}
    todo = [s for s in plan if s["conv_id"] not in existing]
    print(f"[generate] {len(plan)} conversations x {A.n_turns} turns; {len(todo)} to "
          f"make, {len(existing)} already checkpointed", flush=True)
    if todo:
        pool = A.workers or sum(BC_PROVIDER_CONCURRENCY.values())
        with ThreadPoolExecutor(max_workers=pool) as ex:
            futs = {ex.submit(gen_conversation, s, A.n_turns, A.min_turns,
                              A.gen_max_tokens): s for s in todo}
            for n, fut in enumerate(as_completed(futs), 1):
                s = futs[fut]
                try:
                    rec = fut.result()
                except Exception as e:
                    print(f"    [conv {s['conv_id']} / {s['gen_provider']}] DROPPED: "
                          f"{str(e)[:120]}", flush=True)
                    continue
                _jsonl_append(A.conv_file, rec)
                print(f"    {n}/{len(todo)} conv {rec['conv_id']} "
                      f"({rec['gen_provider']}) {len(rec['turns'])} turns"
                      + (f"  TRUNCATED: {rec['truncated_at']}"
                         if rec["truncated_at"] else ""), flush=True)
    rows = load_conversations(A, plan)
    print_generation_summary(rows)
    return rows


def generator_length_stats(rows):
    per = defaultdict(list)
    for c in rows:
        for t in c["turns"]:
            per[c["gen_provider"]].append(len(t["assistant"]))
    med = {p: float(np.median(v)) for p, v in per.items() if v}
    ratio = (max(med.values()) / min(med.values())) if len(med) >= 2 and min(med.values()) else None
    return {"median_chars_per_generator": {k: round(v, 1) for k, v in sorted(med.items())},
            "turns_per_generator": {k: len(v) for k, v in sorted(per.items())},
            "max_min_median_ratio": _r4(ratio),
            "GENERATOR_LENGTH_IMBALANCE_FLAG": bool(
                ratio is not None and ratio > BC_GEN_LENGTH_RATIO_FLAG),
            "flag_threshold": BC_GEN_LENGTH_RATIO_FLAG}


def print_generation_summary(rows):
    gl = generator_length_stats(rows)
    n_turns = sum(len(c["turns"]) for c in rows)
    trunc = [c["conv_id"] for c in rows if c["truncated_at"]]
    print(f"\n  corpus: {len(rows)} conversations, {n_turns} assistant turns")
    print(f"  per-generator median chars : {gl['median_chars_per_generator']}")
    print(f"  per-generator turn counts  : {gl['turns_per_generator']}")
    print(f"  max/min median ratio       : {gl['max_min_median_ratio']} "
          f"(flag > {BC_GEN_LENGTH_RATIO_FLAG}) -> "
          f"GENERATOR_LENGTH_IMBALANCE_FLAG={gl['GENERATOR_LENGTH_IMBALANCE_FLAG']}")
    print(f"  truncated conversations    : {len(trunc)} {trunc[:12]}")
    print(f"  total regenerations        : {sum(c.get('n_regens', 0) for c in rows)}")
    seen = set()
    for c in sorted(rows, key=lambda r: r["conv_id"]):
        if c["gen_provider"] in seen:
            continue
        seen.add(c["gen_provider"])
        t = c["turns"][0]["assistant"]
        print(f"\n  SAMPLE [conv {c['conv_id']} / {c['gen_provider']} / turn 0, "
              f"{len(t)}c]: {t[:220].replace(chr(10), ' ')}")


def load_conversations(A, plan):
    """Load the corpus and ENFORCE provenance from the data, not from a CLI flag (s10.4)."""
    by_plan = {p["conv_id"]: p for p in plan}
    rows, seen = [], set()
    for r in _jsonl_read(A.conv_file):
        cid = r.get("conv_id")
        if cid not in by_plan or cid in seen:
            continue
        p = by_plan[cid]
        for field in ("stratum", "family", "seed_prompt", "gen_provider", "is_pilot"):
            if r.get(field) != p[field]:
                raise SystemExit(
                    f"PROVENANCE ABORT (s10.4): conversation {cid} payload has "
                    f"{field}={r.get(field)!r} but the frozen plan says {p[field]!r}. "
                    f"Provenance is decided by the data; a disagreement aborts the run.")
        seen.add(cid)
        rows.append(r)
    return sorted(rows, key=lambda r: r["conv_id"])


# =====================================================================
# ITEM VIEWS -- three tasks, three DISJOINT views (prereg s6)
# =====================================================================
def build_items(rows, task):
    """One item list per task. The three views do not overlap:
       board  -> ONE assistant turn.
       change -> the PAIR of assistant turns (no user text at all).
       user   -> the PAIR of USER messages (no assistant text at all).
    """
    items = []
    for c in rows:
        turns = c["turns"]
        base = {"conv_id": c["conv_id"], "gen_provider": c["gen_provider"],
                "stratum": c["stratum"], "is_pilot": c["is_pilot"]}
        if task == "board":
            for t in turns:
                items.append(dict(base, uid=f"c{c['conv_id']}t{t['turn_idx']}",
                                  turn_idx=t["turn_idx"],
                                  view=[_trunc(t["assistant"])]))
        else:
            for k in range(len(turns) - 1):
                a, b = turns[k], turns[k + 1]
                if task == "change":
                    view = [_trunc(a["assistant"]), _trunc(b["assistant"])]
                else:
                    view = [a["user"], b["user"]]
                items.append(dict(base, uid=f"c{c['conv_id']}{'p' if task=='change' else 'u'}{k}",
                                  turn_idx=a["turn_idx"], view=view))
    return items


# =====================================================================
# STAGE 2 -- LABEL  (prereg s6.4)
# =====================================================================
def readers_for(task, item):
    """Generator != labeller, MANDATORY, enforced at job-build time (point 1 of 3).

    Both turns of a pair come from the same conversation and therefore the same
    generator, so exclusion is well defined for every task view.

    For T-USER the items are OUR OWN bank strings, not model output, so no model can
    have written them. A deterministic excluded_reader = BC_ORDER[conv_id % 4] keeps the
    panel exactly 3 wide, which Fleiss kappa requires. THIS IS A STRUCTURE-PRESERVING
    HOLDOUT, NOT A SEPARATION CONTROL, and the report says so in those words.
    """
    excluded = (BC_ORDER[item["conv_id"] % len(BC_ORDER)] if task == "user"
                else item["gen_provider"])
    return [p for p in BC_ORDER if p != excluded]


def make_batches_bc(items, batch_size, seed):
    """Shuffle with a per-reader seed, then DETERMINISTICALLY repair same-conversation
    batch-mates. A reader that sees two items from one conversation in one prompt can
    smooth its own labels and manufacture exactly the dependence under test, so residual
    collisions ABORT the run at label time and are a hard Gate 0 check.

    Each accepted swap strictly reduces the total collision count, so this terminates.
    """
    xs = list(items)
    random.Random(seed).shuffle(xs)
    batches = [xs[k:k + batch_size] for k in range(0, len(xs), batch_size)]
    swaps = 0
    progressed = True
    while progressed:
        progressed = False
        for bi in range(len(batches)):
            while True:
                b = batches[bi]
                dup_pos, seen = None, set()
                for pos, it in enumerate(b):
                    if it["conv_id"] in seen:
                        dup_pos = pos
                        break
                    seen.add(it["conv_id"])
                if dup_pos is None:
                    break
                it = b[dup_pos]
                others = {x["conv_id"] for k, x in enumerate(b) if k != dup_pos}
                found = False
                for bj in range(len(batches)):                 # deterministic scan
                    if bj == bi:
                        continue
                    if it["conv_id"] in {x["conv_id"] for x in batches[bj]}:
                        continue
                    for opos, o in enumerate(batches[bj]):
                        if o["conv_id"] in others:
                            continue
                        batches[bi][dup_pos], batches[bj][opos] = o, it
                        swaps += 1
                        found = progressed = True
                        break
                    if found:
                        break
                if not found:
                    break
    residual = sum(len(b) - len({x["conv_id"] for x in b}) for b in batches)
    return batches, swaps, residual


def parse_labels(answer_text, alias_to_uid, code_re):
    """STRICT parse (prereg s6.4). A call is accepted only if ALL of:
         1. finish_reason == 'stop'                      (checked by the caller);
         2. a JSON array parses out of the ANSWER, never out of a reasoning trace;
         3. every id is an alias ACTUALLY SHOWN IN THIS BATCH -- batch-alias
            intersection, so a fabricated id can never overwrite a genuine label from
            another batch;
         4. EXACTLY the batch's ids appear, once each.
       Anything else yields ZERO labels and routes the batch to repair.
    """
    m = re.search(r"\[.*\]", answer_text, re.S)
    if not m:
        return {}, "no_json_array"
    raw = m.group(0)
    try:
        rows = json.loads(raw)
    except Exception:
        rows = []
        for block in re.findall(r"\{[^{}]*\}", raw, re.S):
            idm = re.search(r'"id"\s*:\s*(\d+)', block)
            if not idm:
                continue
            lm = re.search(code_re, block[idm.end():], re.I)
            if lm:
                rows.append({"id": int(idm.group(1)), "label": lm.group(1)})
    if not isinstance(rows, list) or not rows:
        return {}, "unparseable_array"
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            aid = int(row.get("id"))
        except Exception:
            continue
        lm = re.search(code_re, str(row.get("label", "")), re.I)
        if not lm or aid not in alias_to_uid:            # fabricated id -> DROPPED
            continue
        out.setdefault(alias_to_uid[aid], lm.group(1).upper())
    if len(out) != len(alias_to_uid):
        return {}, f"incomplete_{len(out)}_of_{len(alias_to_uid)}"
    return out, "ok"


def render_item(task, alias, item):
    cfg = BC_TASKS[task]
    if task == "board":
        return f"--- {cfg['unit']} {alias} ---\n{item['view'][0]}"
    return (f"--- {cfg['unit']} {alias} ---\nFIRST:\n{item['view'][0]}\n\n"
            f"SECOND:\n{item['view'][1]}")


def read_batch(task, reader, model, batch, alias_seed, allow_reasoning_only):
    """ONE labelling call. Per-batch, per-reader ALIAS ids: a reader never sees an
    internal uid, a turn index, or a conversation id. The internal uid encodes position,
    so printing it would contradict the blindness guarantee outright. The alias<->uid map
    lives only on the analysis side."""
    cfg = BC_TASKS[task]
    aliases = random.Random(alias_seed).sample(range(1000, 10000), len(batch))
    alias_to_uid = {a: it["uid"] for a, it in zip(aliases, batch)}
    blocks = [render_item(task, a, it) for a, it in zip(aliases, batch)]
    prompt = (cfg["rubric"] + f"\n\n{cfg['noun'].capitalize()}s to label:\n"
              + "\n\n".join(blocks)
              + "\n\nReturn ONLY a JSON array as your FINAL ANSWER: "
              f'[{{"id": <number>, "label": "<{cfg["menu"]}>"}}]. '
              f"Every {cfg['noun']} id above must appear exactly once. Use only the "
              "labels above. Put the array in your ANSWER, not only in your reasoning. "
              "Write the array FIRST, before any explanation.")
    maxtok = BC_MAXTOK_LABEL_GLM if reader == "glm" else BC_MAXTOK_LABEL
    client = _client(reader, model)
    r = call_with_retry(client, reader, model=model, max_tokens=maxtok,
                        temperature=0.0, messages=[{"role": "user", "content": prompt}])
    ans, rea = _split_text(r)
    finish = r.choices[0].finish_reason
    base = {"task": task, "reader": reader, "labels": {}, "n_ans": len(ans),
            "n_rea": len(rea), "uids": [it["uid"] for it in batch], "finish": finish}
    if finish != "stop":
        base["status"] = f"finish_{finish}"
        return base
    if not ans.strip():
        if not allow_reasoning_only:
            base["status"] = "reasoning_only_refused"
            return base
        ans = rea
    mapping, status = parse_labels(ans, alias_to_uid, cfg["re"])
    base["labels"] = mapping
    base["status"] = status
    return base


def _batch_key(task, reader, uids):
    return f"{task}|{reader}|" + hashlib.sha256(
        ",".join(sorted(uids)).encode()).hexdigest()[:16]


def _run_label_jobs(jobs, pool, ckpt, allow_reasoning_only, done_keys, label):
    todo = [j for j in jobs if j["key"] not in done_keys]
    print(f"  {label}: {len(todo)} calls to make "
          f"({len(jobs) - len(todo)} already checkpointed)", flush=True)
    stats, per_reader, t0 = Counter(), defaultdict(Counter), time.time()
    if not todo:
        return stats, per_reader
    with ThreadPoolExecutor(max_workers=pool) as ex:
        futs = {ex.submit(read_batch, j["task"], j["reader"], MODELS[j["reader"]],
                          j["batch"], j["alias_seed"], allow_reasoning_only): j
                for j in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            j = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                print(f"    [{j['reader']}] call ERROR {str(e)[:110]}", flush=True)
                stats["call_error"] += 1
                per_reader[j["reader"]]["call_error"] += 1
                continue
            res["key"] = j["key"]
            _jsonl_append(ckpt, res)                    # checkpoint as it lands
            done_keys.add(j["key"])
            stats[res["status"]] += 1
            per_reader[j["reader"]][res["status"]] += 1
            if n % 10 == 0 or res["status"] != "ok":
                print(f"    {n}/{len(todo)} ({time.time()-t0:.0f}s) {j['reader']}: "
                      f"{res['status']} ({len(res['labels'])} labels)", flush=True)
    return stats, per_reader


def collect_marks(ckpt, task, by_uid):
    """Rebuild reader -> {uid: code}. Enforces generator != labeller a SECOND time,
    structurally, at COLLECTION: a checkpoint row from an earlier run with a different
    rotation can never contribute a self-read. First write wins, so a later batch never
    overwrites a genuine label."""
    marks = defaultdict(dict)
    for row in _jsonl_read(ckpt):
        if row.get("task") != task or row.get("status") != "ok":
            continue
        reader = row.get("reader")
        for uid, code in (row.get("labels") or {}).items():
            it = by_uid.get(uid)
            if it is None:
                continue
            if reader not in readers_for(task, it):
                continue
            marks[reader].setdefault(uid, code)
    return marks


def stage_label(A, task, rows):
    items = build_items(rows, task)
    by_uid = {it["uid"]: it for it in items}
    cfg = BC_TASKS[task]
    bs = A.batch_override.get(task, cfg["batch"])
    print(f"\n[label:{task}] {len(items)} items; 3 blind readers each "
          f"(batch={bs})", flush=True)

    jobs, meta = [], []
    for ri, reader in enumerate(BC_ORDER):
        mine = [it for it in items if reader in readers_for(task, it)]
        batches, swaps, residual = make_batches_bc(
            mine, bs, BC_SEED_BATCH_BASE[task] + ri)
        meta.append({"task": task, "reader": reader, "n_items": len(mine),
                     "n_batches": len(batches), "conv_spread_swaps": swaps,
                     "residual_same_conversation_collisions": residual})
        if residual > BC_G0_COLLISIONS_MAX:
            raise SystemExit(
                f"ABORT at label time (s6.4): reader {reader}, task {task} has "
                f"{residual} residual same-conversation batch collisions with "
                f"batch_size={bs}. Lower the batch size or add conversations. No API "
                f"call was made.")
        for bi, b in enumerate(batches):
            jobs.append({"task": task, "reader": reader, "batch": b,
                         "alias_seed": BC_SEED_ALIAS_BASE + ri * 100000 + bi,
                         "key": _batch_key(task, reader, [x["uid"] for x in b])})

    record_hashes(A)                       # s10.4: hash record written at first call
    done = {r["key"] for r in _jsonl_read(A.label_ckpt) if r.get("key")}
    pool = A.workers or sum(BC_PROVIDER_CONCURRENCY.values())
    print(f"  {len(jobs)} labelling calls; conv-spread swaps "
          f"{[(m['reader'], m['conv_spread_swaps']) for m in meta]}", flush=True)
    stats, per_reader = _run_label_jobs(jobs, pool, A.label_ckpt,
                                        A.allow_reasoning_only, done, "main pass")

    for rnd in range(A.repair_rounds):     # s6.4 REPAIR PASS
        marks = collect_marks(A.label_ckpt, task, by_uid)
        missing = []
        for ri, reader in enumerate(BC_ORDER):
            want = {it["uid"] for it in items if reader in readers_for(task, it)}
            gap = sorted(want - set(marks.get(reader, {})))
            if gap:
                missing.append((ri, reader, gap))
        if not missing:
            print(f"  repair round {rnd+1}: nothing missing.", flush=True)
            break
        print("  repair round %d: %s" % (
            rnd + 1, ", ".join(f"{r}:{len(g)}" for _, r, g in missing)), flush=True)
        rjobs = []
        for ri, reader, gap in missing:
            batches, _, resid = make_batches_bc(
                [by_uid[u] for u in gap], A.repair_batch_size,
                BC_SEED_BATCH_BASE[task] + ri + 977 * (rnd + 1))
            for bi, b in enumerate(batches):
                rjobs.append({"task": task, "reader": reader, "batch": b,
                              "alias_seed": (BC_SEED_ALIAS_BASE + 7000000 * (rnd + 1)
                                             + ri * 100000 + bi),
                              "key": _batch_key(task, reader, [x["uid"] for x in b])})
        s2, p2 = _run_label_jobs(rjobs, pool, A.label_ckpt, A.allow_reasoning_only,
                                 done, f"repair round {rnd+1}")
        stats += s2
        for r, c in p2.items():
            per_reader[r] += c

    marks = collect_marks(A.label_ckpt, task, by_uid)
    got = Counter(len([p for p in BC_ORDER if it["uid"] in marks.get(p, {})])
                  for it in items)
    print(f"  call statuses: {dict(stats)}")
    print(f"  readers-per-item: {dict(sorted(got.items()))} (3 = complete case)")
    return {"marks": {k: dict(v) for k, v in marks.items()}, "batch_meta": meta,
            "call_statuses": dict(stats),
            "per_reader_call_statuses": {r: dict(c) for r, c in per_reader.items()}}


def record_hashes(A):
    """s10.4: the sha256 of the preregistration and of this runner, recorded when the
    FIRST labelling call ran, is compared at analyse time. A mismatch means one of them
    was edited after data collection began, and THE RUN IS NOT PREREGISTERED."""
    if os.path.exists(A.hash_file):
        return
    with open(A.hash_file, "w", encoding="utf-8") as f:
        json.dump({"recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "prereg_sha256": _sha256(PREREG_PATH),
                   "runner_sha256": _sha256(os.path.abspath(__file__)),
                   "blind_seed_bank_sha256": _sha256(BLIND_SEED_PATH)}, f, indent=2)


def check_hashes(A):
    now = {"prereg_sha256": _sha256(PREREG_PATH),
           "runner_sha256": _sha256(os.path.abspath(__file__)),
           "blind_seed_bank_sha256": _sha256(BLIND_SEED_PATH)}
    if not os.path.exists(A.hash_file):
        return {"recorded": None, "now": now, "match": None,
                "note": "no hash record exists (no labelling call has run under this tag)"}
    rec = json.load(open(A.hash_file, encoding="utf-8"))
    match = all(rec.get(k) == now[k] for k in now)
    return {"recorded": rec, "now": now, "match": bool(match),
            "note": ("" if match else
                     "MISMATCH -- the preregistration or the runner was edited after "
                     "data collection began. THE RUN IS NOT PREREGISTERED.")}


# =====================================================================
# CONSENSUS + AGREEMENT
# =====================================================================
def consensus_of(codes):
    """>= 2 AGREEING among >= 2 PRESENT. A tie or a three-way split is NO consensus."""
    if len(codes) < 2:
        return None, len(codes)
    c = Counter(codes)
    top, n = c.most_common(1)[0]
    if n < 2 or sum(1 for _, v in c.items() if v == n) > 1:
        return None, n
    return top, n


def agreement_block(task, items, marks):
    per_item, rows3 = [], []
    for it in items:
        readers = [p for p in BC_ORDER if it["uid"] in marks.get(p, {})]
        codes = [marks[p][it["uid"]] for p in readers]
        cons, votes = consensus_of(codes)
        per_item.append({"uid": it["uid"], "conv_id": it["conv_id"],
                         "turn_idx": it["turn_idx"], "stratum": it["stratum"],
                         "gen_provider": it["gen_provider"],
                         "reader_codes": {p: marks[p][it["uid"]] for p in readers},
                         "n_readers": len(readers), "consensus": cons,
                         "consensus_votes": votes,
                         "unanimous": bool(len(codes) == 3 and len(set(codes)) == 1),
                         "n_distinct_codes": len(set(codes))})
        if len(codes) == 3:
            rows3.append(codes)
    n = len(items)
    kappa = round(fleiss_kappa(rows3), 4) if len(rows3) >= 2 else None
    tot = agree = 0
    for codes in rows3:
        for i in range(3):
            for j in range(i + 1, 3):
                tot += 1
                agree += int(codes[i] == codes[j])
    raw = round(agree / tot, 4) if tot else None
    marg = Counter(c for codes in rows3 for c in codes)
    tot_m = sum(marg.values())
    p_e = sum((v / tot_m) ** 2 for v in marg.values()) if tot_m else None
    derived = (p_e + BC_G0_RAW_KAPPA_COMPONENT * (1 - p_e)) if p_e is not None else None
    binding = (max(BC_G0_RAW_ABSOLUTE_FLOOR, derived) if derived is not None else None)
    n_cons = sum(1 for r in per_item if r["consensus"])
    return {
        "task": task, "n_items": n,
        "n_complete_cases": len(rows3),
        "complete_case_coverage": _r4(len(rows3) / n) if n else None,
        "n_with_consensus": n_cons,
        "consensus_coverage": _r4(n_cons / n) if n else None,
        "fleiss_kappa_complete_cases": kappa,
        "raw_pairwise_agreement_complete_cases": raw,
        "P_e_from_observed_marginals": _r4(p_e),
        "raw_floor_derived_Pe_plus_035": _r4(derived),
        "raw_floor_absolute": BC_G0_RAW_ABSOLUTE_FLOOR,
        "raw_floor_binding": _r4(binding),
        "which_floor_bound": (None if binding is None else
                              ("derived" if derived is not None and derived >= BC_G0_RAW_ABSOLUTE_FLOOR
                               else "absolute_0.50")),
        "label_marginals_complete_cases": dict(sorted(marg.items())),
        "consensus_label_distribution": dict(sorted(Counter(
            r["consensus"] for r in per_item if r["consensus"]).items())),
        "per_item": per_item,
    }


# =====================================================================
# ANALYSIS SET
# =====================================================================
def build_analysis_set(rows, panels):
    """A transition is ANALYSABLE for Claim 1 iff it has board consensus at BOTH ends
    and T-CHANGE consensus on the pair. Claim 2 additionally needs T-USER consensus, and
    is computed on the MODEL-INITIATED subset (T-USER = SAME-KIND) only."""
    b = {r["uid"]: r for r in panels["board"]["per_item"]}
    ch = {r["uid"]: r for r in panels["change"]["per_item"]}
    us = {r["uid"]: r for r in panels["user"]["per_item"]}
    out = []
    for c in rows:
        turns = c["turns"]
        for k in range(len(turns) - 1):
            cid = c["conv_id"]
            bn, bn1 = b.get(f"c{cid}t{turns[k]['turn_idx']}"), b.get(f"c{cid}t{turns[k+1]['turn_idx']}")
            cp, up = ch.get(f"c{cid}p{k}"), us.get(f"c{cid}u{k}")
            rec = {
                "conv_id": cid, "pair_idx": k, "turn_idx": turns[k]["turn_idx"],
                "stratum": c["stratum"], "family": c["family"],
                "is_pilot": c["is_pilot"], "gen_provider": c["gen_provider"],
                "text_N": turns[k]["assistant"], "text_N1": turns[k + 1]["assistant"],
                "followup_id_N": turns[k]["followup_id"],
                "followup_id_N1": turns[k + 1]["followup_id"],
                "b_N": bn["consensus"] if bn else None,
                "b_N1": bn1["consensus"] if bn1 else None,
                "unanimous_N": bn["unanimous"] if bn else None,
                "n_distinct_codes_N": bn["n_distinct_codes"] if bn else None,
                "gt_change": cp["consensus"] if cp else None,
                "user_verdict": up["consensus"] if up else None,
            }
            rec["board_indicator"] = (None if (rec["b_N"] is None or rec["b_N1"] is None)
                                      else int(rec["b_N"] != rec["b_N1"]))
            rec["analysable_c1"] = bool(rec["board_indicator"] is not None
                                        and rec["gt_change"] is not None)
            rec["user_class"] = ({"DIFFERENT-KIND": "USER-INDUCED",
                                  "SAME-KIND": "MODEL-INITIATED"}
                                 .get(rec["user_verdict"], "UNCLASSIFIED"))
            rec["analysable_c2"] = bool(rec["analysable_c1"]
                                        and rec["user_class"] == "MODEL-INITIATED")
            out.append(rec)
    return out


# =====================================================================
# METRICS  (prereg s7)
# =====================================================================
def prf(y_true, y_pred):
    tp = sum(1 for a, p in zip(y_true, y_pred) if a == 1 and p == 1)
    fp = sum(1 for a, p in zip(y_true, y_pred) if a == 0 and p == 1)
    fn = sum(1 for a, p in zip(y_true, y_pred) if a == 1 and p == 0)
    tn = sum(1 for a, p in zip(y_true, y_pred) if a == 0 and p == 0)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    den = math.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / den) if den > 0 else 0.0
    n = len(y_true)
    return {"n": n, "base_rate_CHANGE": _r4(sum(y_true) / n) if n else None,
            "change_f1": _r4(f1), "precision_CHANGE": _r4(prec),
            "recall_CHANGE": _r4(rec), "mcc": _r4(mcc),
            "confusion_2x2": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
            "accuracy_DIAGNOSTIC_NOT_THE_RESULT": _r4((tp + tn) / n) if n else None}


def f1_of(y_true, y_pred):
    tp = sum(1 for a, p in zip(y_true, y_pred) if a == 1 and p == 1)
    fp = sum(1 for a, p in zip(y_true, y_pred) if a == 0 and p == 1)
    fn = sum(1 for a, p in zip(y_true, y_pred) if a == 1 and p == 0)
    d = 2 * tp + fp + fn
    return (2.0 * tp / d) if d else 0.0


def mcc_of(y_true, y_pred):
    tp = sum(1 for a, p in zip(y_true, y_pred) if a == 1 and p == 1)
    fp = sum(1 for a, p in zip(y_true, y_pred) if a == 0 and p == 1)
    fn = sum(1 for a, p in zip(y_true, y_pred) if a == 1 and p == 0)
    tn = sum(1 for a, p in zip(y_true, y_pred) if a == 0 and p == 0)
    den = math.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return ((tp * tn - fp * fn) / den) if den > 0 else 0.0


# =====================================================================
# LOCO MACHINERY  (prereg s9)
# =====================================================================
def loco_predict(feats, y, groups, fit_predict):
    """Leave-one-CONVERSATION-out. Vectorisers are refit INSIDE every training fold; C is
    tuned on grouped inner splits of the TRAINING FOLD ONLY. All controls are computed
    over the same test indices, including the ones with no fitted parameters.
    Returns pooled predictions aligned with the input order, or None if uncomputable."""
    n = len(y)
    if n == 0 or len(set(groups)) < 2:
        return None
    preds = [None] * n
    for g in sorted(set(groups)):
        te = [i for i in range(n) if groups[i] == g]
        tr = [i for i in range(n) if groups[i] != g]
        if not te or not tr:
            return None
        ytr = [y[i] for i in tr]
        if len(set(ytr)) < 2:                    # degenerate fold -> majority class
            maj = 1 if sum(ytr) * 2 > len(ytr) else 0
            for i in te:
                preds[i] = maj
            continue
        try:
            p = fit_predict([feats[i] for i in tr], ytr, [feats[i] for i in te],
                            [groups[i] for i in tr])
        except Exception:
            return None
        for i, v in zip(te, p):
            preds[i] = int(v)
    return None if any(v is None for v in preds) else preds


def _tune_C(Xtr, ytr, gtr):
    ng = len(set(gtr))
    if ng < 2:
        return 1.0
    k = min(4, ng)
    best, bestc = -1.0, 1.0
    for C in BC_C_GRID:
        scores = []
        try:
            for itr, ite in GroupKFold(n_splits=k).split(Xtr, ytr, groups=gtr):
                yy = [ytr[i] for i in itr]
                if len(set(yy)) < 2:
                    continue
                m = LogisticRegression(max_iter=500, random_state=42, C=C)
                m.fit(Xtr[itr], yy)
                scores.append(f1_of([ytr[i] for i in ite], list(m.predict(Xtr[ite]))))
        except Exception:
            continue
        if scores and float(np.mean(scores)) > best:
            best, bestc = float(np.mean(scores)), C
    return bestc


def _fit_lr(Xtr, ytr, Xte, gtr):
    C = _tune_C(Xtr, ytr, gtr)
    m = LogisticRegression(max_iter=500, random_state=42, C=C)
    m.fit(Xtr, ytr)
    return list(m.predict(Xte))


def make_text_arm(kind, joiner):
    """S1 char / S2 word unigram, refit inside each training fold."""
    def fp(tr, ytr, te, gtr):
        vec = (TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=5000)
               if kind == "char" else
               CountVectorizer(max_features=3000, stop_words="english", binary=True))
        Xtr = vec.fit_transform([joiner(t) for t in tr])
        Xte = vec.transform([joiner(t) for t in te])
        return _fit_lr(Xtr, ytr, Xte, gtr)
    return fp


def make_length_arm(fields):
    def fp(tr, ytr, te, gtr):
        def mat(rows):
            out = []
            for r in rows:
                ls = [len(r[f]) for f in fields]
                out.append(ls + ([abs(ls[1] - ls[0])] if len(ls) == 2 else []))
            return np.asarray(out, dtype=float)
        return _fit_lr(mat(tr), ytr, mat(te), gtr)
    return fp


def make_pair_cosine_arm():
    """S4 -- 'just measure how different the two texts are'. Cosine distance between the
    two turns' OWN vectors, char and word, thresholded by a logistic fit. This is the arm
    most likely to kill the study, and it is included for exactly that reason (s9)."""
    def fp(tr, ytr, te, gtr):
        cv = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=5000)
        wv = CountVectorizer(max_features=3000, stop_words="english", binary=True)
        corpus = [r["text_N"] for r in tr] + [r["text_N1"] for r in tr]
        cv.fit(corpus)
        wv.fit(corpus)

        def mat(rows):
            out = []
            for vec in (cv, wv):
                A = vec.transform([r["text_N"] for r in rows]).astype(float)
                B = vec.transform([r["text_N1"] for r in rows]).astype(float)
                a = np.asarray(A.multiply(B).sum(axis=1)).ravel()
                na = np.sqrt(np.asarray(A.multiply(A).sum(axis=1)).ravel())
                nb = np.sqrt(np.asarray(B.multiply(B).sum(axis=1)).ravel())
                den = np.where(na * nb > 0, na * nb, 1.0)
                out.append(1.0 - (a / den))
            return np.vstack(out).T
        return _fit_lr(mat(tr), ytr, mat(te), gtr)
    return fp


def make_cat_arm(fields):
    def fp(tr, ytr, te, gtr):
        enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        Xtr = enc.fit_transform([[str(r.get(f)) for f in fields] for r in tr])
        Xte = enc.transform([[str(r.get(f)) for f in fields] for r in te])
        return _fit_lr(Xtr, ytr, Xte, gtr)
    return fp


# =====================================================================
# BASELINES / NULLS / BOOTSTRAP
# =====================================================================
def trivial_bar(y, groups):
    """CONTROL 2 (s7.3). Three degenerate strategies, computed on the TRAINING FOLDS, the
    highest of them is the bar. always-CHANGE -> 2p/(1+p); always-SAME -> 0; random at
    the base rate -> ~p. Every one of them scores MCC = 0, which is why MCC is a
    CO-REQUIREMENT: F1 alone can be gamed by predicting the rare class always."""
    n = len(y)
    if n == 0 or len(set(groups)) < 2:
        return None
    rng = random.Random(BC_SEED_TRIVIAL_RANDOM)
    always_c, always_s, rand = [0] * n, [0] * n, [0] * n
    p_trains = []
    for g in sorted(set(groups)):
        tr = [i for i in range(n) if groups[i] != g]
        te = [i for i in range(n) if groups[i] == g]
        p_tr = (sum(y[i] for i in tr) / len(tr)) if tr else 0.0
        p_trains.append(p_tr)
        for i in te:
            always_c[i] = 1
            always_s[i] = 0
            rand[i] = 1 if rng.random() < p_tr else 0
    cands = {"always_CHANGE": f1_of(y, always_c), "always_SAME": f1_of(y, always_s),
             "random_at_train_base_rate": f1_of(y, rand)}
    best = max(cands, key=lambda k: cands[k])
    p_bar = float(np.mean(p_trains))
    return {"strategies_change_f1": {k: _r4(v) for k, v in cands.items()},
            "mean_train_base_rate": _r4(p_bar),
            "formula_2p_over_1_plus_p": _r4(2 * p_bar / (1 + p_bar)),
            "binding_strategy": best, "trivial_f1_bar": _r4(cands[best]),
            "_bar": cands[best], "_preds": {"always_CHANGE": always_c,
                                            "always_SAME": always_s,
                                            "random_at_train_base_rate": rand}}


def perm_null(y, preds, groups, trials=BC_PERM_TRIALS, seed=BC_PERM_SEED):
    """CONTROL 3. WITHIN-CONVERSATION block permutation, NEVER a global shuffle. Each
    conversation is one seed prompt on one topic written by one model, so its turns are
    label-homogeneous for reasons that have nothing to do with transitions; a global null
    would be beaten by that homogeneity alone. Block permutation preserves each
    conversation's composition and isolates exactly the temporal link."""
    if preds is None or not y:
        return None
    real = f1_of(y, preds)
    idx = defaultdict(list)
    for i, g in enumerate(groups):
        idx[g].append(i)
    rng = random.Random(seed)
    nulls = []
    for _ in range(trials):
        yp = list(y)
        for g, ii in idx.items():
            vals = [y[i] for i in ii]
            rng.shuffle(vals)
            for i, v in zip(ii, vals):
                yp[i] = v
        nulls.append(f1_of(yp, preds))
    arr = np.asarray(nulls, dtype=float)
    return {"real_change_f1": _r4(real), "null_mean": _r4(arr.mean()),
            "null_p95": _r4(np.percentile(arr, 95)),
            "null_p99": _r4(np.percentile(arr, 99)),
            "empirical_p": _r4((int((arr >= real).sum()) + 1) / (trials + 1)),
            "trials": trials,
            "_real": real, "_p95": float(np.percentile(arr, 95)),
            "_p99": float(np.percentile(arr, 99)),
            "_p": (int((arr >= real).sum()) + 1) / (trials + 1)}


def cluster_boot_margin(y, pred_a, pred_b, groups, metric=f1_of):
    """s8.4 paired cluster bootstrap over CONVERSATIONS. The point margin must clear its
    threshold AND the 5th percentile must exceed 0. Observations cluster (up to 9 pairs
    per conversation), so the CLUSTERS, not the pairs, set the resolution."""
    if pred_a is None or pred_b is None or not y:
        return None
    idx = defaultdict(list)
    for i, g in enumerate(groups):
        idx[g].append(i)
    gs = sorted(idx)
    if len(gs) < 2:
        return None
    point = metric(y, pred_a) - metric(y, pred_b)
    rng = random.Random(BC_BOOT_SEED)
    draws = []
    for _ in range(BC_BOOT_N):
        sel = [rng.choice(gs) for _ in gs]
        ii = [i for g in sel for i in idx[g]]
        yy = [y[i] for i in ii]
        if len(set(yy)) < 1:
            continue
        draws.append(metric(yy, [pred_a[i] for i in ii])
                     - metric(yy, [pred_b[i] for i in ii]))
    if not draws:
        return None
    arr = np.asarray(draws, dtype=float)
    return {"point_margin": _r4(point),
            "boot_p5": _r4(np.percentile(arr, BC_BOOT_LOWER_Q)),
            "boot_p95": _r4(np.percentile(arr, 100 - BC_BOOT_LOWER_Q)),
            "_point": point, "_p5": float(np.percentile(arr, BC_BOOT_LOWER_Q))}


def cluster_boot_value(y, pred, groups, metric):
    if pred is None or not y:
        return None
    idx = defaultdict(list)
    for i, g in enumerate(groups):
        idx[g].append(i)
    gs = sorted(idx)
    if len(gs) < 2:
        return None
    rng = random.Random(BC_BOOT_SEED)
    draws = []
    for _ in range(BC_BOOT_N):
        sel = [rng.choice(gs) for _ in gs]
        ii = [i for g in sel for i in idx[g]]
        draws.append(metric([y[i] for i in ii], [pred[i] for i in ii]))
    arr = np.asarray(draws, dtype=float)
    return {"point": _r4(metric(y, pred)), "boot_p5": _r4(np.percentile(arr, BC_BOOT_LOWER_Q)),
            "_point": metric(y, pred), "_p5": float(np.percentile(arr, BC_BOOT_LOWER_Q))}


def gate(name, margin_block, threshold, note=""):
    """FAIL-CLOSED (s9, binding). If a control CANNOT BE COMPUTED its gate is null --
    NEVER true -- and the verdict is VACUOUS. In the retired design a surface array
    initialised to 0.0 let the primary kill evaluate (acc - 0.0) >= 0.05 and SILENTLY
    PASS with no control computed at all. That must never happen again."""
    if margin_block is None:
        return {"gate": name, "pass": None, "reason": "UNCOMPUTABLE -> null, never true",
                "threshold": threshold, "note": note}
    ok = bool(margin_block["_point"] >= threshold and margin_block["_p5"] > 0)
    return {"gate": name, "pass": ok, "threshold": threshold,
            "point_margin": margin_block["point_margin"],
            "boot_p5": margin_block["boot_p5"], "note": note}


# =====================================================================
# CLAIM EVALUATION
# =====================================================================
def eval_claim1(pairs):
    an = [r for r in pairs if r["analysable_c1"]]
    if not an:
        return {"n_analysable_pairs": 0, "computable": False,
                "note": "no analysable pairs -> every gate is null, verdict VACUOUS"}
    y = [1 if r["gt_change"] == "CHANGE" else 0 for r in an]
    g = [r["conv_id"] for r in an]
    board = [r["board_indicator"] for r in an]

    surf = {
        "S1_char": loco_predict(an, y, g, make_text_arm(
            "char", lambda r: r["text_N"] + "\n\n" + r["text_N1"])),
        "S2_word_unigram": loco_predict(an, y, g, make_text_arm(
            "word", lambda r: r["text_N"] + "\n\n" + r["text_N1"])),
        "S3_length": loco_predict(an, y, g, make_length_arm(["text_N", "text_N1"])),
        "S4_pair_cosine": loco_predict(an, y, g, make_pair_cosine_arm()),
    }
    surf_f1 = {k: (None if v is None else _r4(f1_of(y, v))) for k, v in surf.items()}
    live = {k: v for k, v in surf.items() if v is not None}
    best_surf_name = (max(live, key=lambda k: f1_of(y, live[k])) if live else None)
    best_surf = live.get(best_surf_name)

    ctl = {
        "C5_user_move": loco_predict(an, y, g, make_cat_arm(
            ["followup_id_N", "followup_id_N1"])),
        "C6_turn_position": loco_predict(an, y, g, make_cat_arm(["turn_idx"])),
        "C9_generator_identity": loco_predict(an, y, g, make_cat_arm(["gen_provider"])),
    }
    triv = trivial_bar(y, g)
    metrics = prf(y, board)
    perm = perm_null(y, board, g)
    mccb = cluster_boot_value(y, board, g, mcc_of)

    gates = {
        "G1_1_SURFACE_PRIMARY_KILL": gate(
            "G1-1 SURFACE", cluster_boot_margin(y, board, best_surf, g), BC_C1_MARGIN,
            f"strongest surface arm = {best_surf_name}"),
        "G1_2_TRIVIAL_BASELINE": gate(
            "G1-2 TRIVIAL", (cluster_boot_margin(
                y, board, triv["_preds"][triv["binding_strategy"]], g)
                if triv else None), BC_C1_MARGIN,
            f"binding strategy = {triv['binding_strategy'] if triv else None}"),
        "G1_3_MCC": ({"gate": "G1-3 MCC", "pass": None,
                      "reason": "UNCOMPUTABLE -> null, never true"} if mccb is None else
                     {"gate": "G1-3 MCC",
                      "pass": bool(mccb["_point"] > 0 and mccb["_p5"] > 0),
                      "mcc": mccb["point"], "boot_p5": mccb["boot_p5"]}),
        "G1_4_PERMUTATION_NULL": ({"gate": "G1-4 PERM", "pass": None,
                                   "reason": "UNCOMPUTABLE -> null, never true"}
                                  if perm is None else
                                  {"gate": "G1-4 PERM",
                                   "pass": bool(perm["_p"] < BC_C1_PERM_ALPHA
                                                and perm["_real"] > perm["_p95"]),
                                   "empirical_p": perm["empirical_p"],
                                   "alpha": BC_C1_PERM_ALPHA,
                                   "null_p95": perm["null_p95"]}),
        "G1_6_USER_MOVE_HARD_KILL": gate(
            "G1-6 USER MOVE", cluster_boot_margin(y, board, ctl["C5_user_move"], g),
            BC_C1_MARGIN, "HARD KILL: a signal produced by the scripted stimulus is a "
                          "design artefact"),
        "G1_7_TURN_POSITION_DOWNGRADE": gate(
            "G1-7 TURN POS", cluster_boot_margin(y, board, ctl["C6_turn_position"], g),
            BC_C1_MARGIN, "downgrade gate"),
        "G1_8_GENERATOR_IDENTITY_DOWNGRADE": gate(
            "G1-8 GENERATOR", cluster_boot_margin(
                y, board, ctl["C9_generator_identity"], g),
            BC_C1_MARGIN, "downgrade gate"),
    }

    # diagnostic companion (s9): can a surface model recover the GROUND TRUTH at all?
    gt_surf = max([f1_of(y, v) for v in live.values()], default=None)
    return {
        "n_analysable_pairs": len(an),
        "computable": True,
        "PRIMARY_change_f1": metrics["change_f1"],
        "metrics": metrics,
        "board_indicator_note": (
            "the Claim 1 predictor is the DETERMINISTIC indicator b_N != b_{N+1}; it "
            "fits no parameters, so LOCO is a formality for it and it is evaluated over "
            "the same test indices as every fitted control"),
        "surface_battery_change_f1": surf_f1,
        "surface_change_f1_max": _r4(max([v for v in surf_f1.values() if v is not None],
                                         default=None)
                                     if any(v is not None for v in surf_f1.values()) else None),
        "strongest_surface_arm": best_surf_name,
        "controls_change_f1": {k: (None if v is None else _r4(f1_of(y, v)))
                               for k, v in ctl.items()},
        "trivial_baseline": (None if triv is None else
                             {k: v for k, v in triv.items() if not k.startswith("_")}),
        "permutation_null": (None if perm is None else
                             {k: v for k, v in perm.items() if not k.startswith("_")}),
        "mcc_bootstrap": (None if mccb is None else
                          {k: v for k, v in mccb.items() if not k.startswith("_")}),
        "ground_truth_surface_f1_diagnostic": _r4(gt_surf),
        "GROUND_TRUTH_IS_SURFACE_FLAG": bool(
            gt_surf is not None and gt_surf > BC_GROUND_TRUTH_SURFACE_FLAG),
        "ground_truth_surface_flag_threshold": BC_GROUND_TRUTH_SURFACE_FLAG,
        "gates": gates,
    }


def eval_claim2(pairs, subset, label):
    an = [r for r in pairs if r["analysable_c1"] and r["user_class"] == subset]
    base = {"subset": subset, "label": label, "n_analysable_pairs": len(an),
            "n_changes": sum(1 for r in an if r["gt_change"] == "CHANGE")}
    if len(an) < 4 or len({r["conv_id"] for r in an}) < 2:
        base.update({"computable": False,
                     "note": "too few analysable pairs -> every gate is null, VACUOUS"})
        return base
    y = [1 if r["gt_change"] == "CHANGE" else 0 for r in an]
    g = [r["conv_id"] for r in an]

    p1 = loco_predict(an, y, g, make_cat_arm(["b_N"]))                    # PRIMARY
    p2 = loco_predict(an, y, g, make_cat_arm(                             # secondary
        ["b_N", "unanimous_N", "n_distinct_codes_N"]))
    surf = {
        "char_turnN": loco_predict(an, y, g, make_text_arm(
            "char", lambda r: r["text_N"][:BC_READER_TRUNC_CHARS])),
        "word_turnN": loco_predict(an, y, g, make_text_arm(
            "word", lambda r: r["text_N"][:BC_READER_TRUNC_CHARS])),
        "length_turnN": loco_predict(an, y, g, make_length_arm(["text_N"])),
    }
    live = {k: v for k, v in surf.items() if v is not None}
    best_name = max(live, key=lambda k: f1_of(y, live[k])) if live else None
    best = live.get(best_name)
    ctl = {
        "C5_user_move": loco_predict(an, y, g, make_cat_arm(
            ["followup_id_N", "followup_id_N1"])),
        "C6_turn_position": loco_predict(an, y, g, make_cat_arm(["turn_idx"])),
        "C9_generator_identity": loco_predict(an, y, g, make_cat_arm(["gen_provider"])),
    }
    triv = trivial_bar(y, g)
    metrics = prf(y, p1) if p1 is not None else None
    perm = perm_null(y, p1, g)
    mccb = cluster_boot_value(y, p1, g, mcc_of) if p1 is not None else None

    sample_floor = bool(base["n_changes"] >= BC_G2_MIN_CHANGES
                        and base["n_analysable_pairs"] >= BC_G2_MIN_PAIRS)
    gates = {
        "G2_0_SAMPLE_FLOOR": {"gate": "G2-0 SAMPLE FLOOR", "pass": sample_floor,
                              "n_changes": base["n_changes"],
                              "min_changes": BC_G2_MIN_CHANGES,
                              "n_pairs": base["n_analysable_pairs"],
                              "min_pairs": BC_G2_MIN_PAIRS},
        "G2_1_SURFACE_PRIMARY_KILL": gate(
            "G2-1 SURFACE", cluster_boot_margin(y, p1, best, g), BC_C2_MARGIN,
            f"strongest surface arm = {best_name}; 2x the Claim 1 margin"),
        "G2_2_TRIVIAL_BASELINE": gate(
            "G2-2 TRIVIAL", (cluster_boot_margin(
                y, p1, triv["_preds"][triv["binding_strategy"]], g) if triv else None),
            BC_C2_MARGIN, "2x the Claim 1 margin"),
        "G2_3_MCC": ({"gate": "G2-3 MCC", "pass": None,
                      "reason": "UNCOMPUTABLE -> null, never true"} if mccb is None else
                     {"gate": "G2-3 MCC",
                      "pass": bool(mccb["_point"] > 0 and mccb["_p5"] > 0),
                      "mcc": mccb["point"], "boot_p5": mccb["boot_p5"]}),
        "G2_4_PERMUTATION_NULL": ({"gate": "G2-4 PERM", "pass": None,
                                   "reason": "UNCOMPUTABLE -> null, never true"}
                                  if perm is None else
                                  {"gate": "G2-4 PERM",
                                   "pass": bool(perm["_p"] < BC_C2_PERM_ALPHA
                                                and perm["_real"] > perm["_p99"]),
                                   "empirical_p": perm["empirical_p"],
                                   "alpha": BC_C2_PERM_ALPHA,
                                   "null_p99": perm["null_p99"],
                                   "note": "5x stricter than Claim 1, p99 not p95"}),
        "G2_5_USER_MOVE_HARD_KILL": gate(
            "G2-5 USER MOVE", cluster_boot_margin(y, p1, ctl["C5_user_move"], g),
            BC_C2_MARGIN, "HARD KILL"),
        "G2_6_TURN_POSITION_HARD_KILL": gate(
            "G2-6 TURN POS", cluster_boot_margin(y, p1, ctl["C6_turn_position"], g),
            BC_C2_MARGIN, "PROMOTED from downgrade to hard kill for Claim 2"),
        "G2_7_GENERATOR_IDENTITY_HARD_KILL": gate(
            "G2-7 GENERATOR", cluster_boot_margin(y, p1, ctl["C9_generator_identity"], g),
            BC_C2_MARGIN, "PROMOTED from downgrade to hard kill for Claim 2"),
    }
    return dict(base, computable=True,
                PRIMARY_change_f1=(metrics["change_f1"] if metrics else None),
                metrics=metrics,
                P2_secondary_reported_not_gating=(prf(y, p2) if p2 is not None else None),
                surface_battery_change_f1={k: (None if v is None else _r4(f1_of(y, v)))
                                           for k, v in surf.items()},
                strongest_surface_arm=best_name,
                controls_change_f1={k: (None if v is None else _r4(f1_of(y, v)))
                                    for k, v in ctl.items()},
                trivial_baseline=(None if triv is None else
                                  {k: v for k, v in triv.items() if not k.startswith("_")}),
                permutation_null=(None if perm is None else
                                  {k: v for k, v in perm.items() if not k.startswith("_")}),
                mcc_bootstrap=(None if mccb is None else
                               {k: v for k, v in mccb.items() if not k.startswith("_")}),
                gates=gates)


# =====================================================================
# GATE 0  (prereg s10.1)
# =====================================================================
def gate0_block(panels, pairs, batch_meta_all, plan_rows, n_possible_pairs):
    checks = []

    def add(name, value, floor, ok, note=""):
        checks.append({"check": name, "value": value, "floor": floor,
                       "pass": ok, "note": note})

    kmins = {"board": BC_G0_KAPPA_MIN_BOARD, "change": BC_G0_KAPPA_MIN_CHANGE,
             "user": BC_G0_KAPPA_MIN_USER}
    for t in ("board", "change", "user"):
        p = panels[t]
        k = p["fleiss_kappa_complete_cases"]
        add(f"fleiss_kappa_{t}", k, kmins[t],
            None if k is None else bool(k >= kmins[t]),
            "6 classes" if t == "board" else "binary -- KAPPA_NOT_COMPARABLE_ACROSS_TASKS")
        add(f"complete_cases_{t}", p["n_complete_cases"], BC_G0_COMPLETE_N_MIN,
            bool(p["n_complete_cases"] >= BC_G0_COMPLETE_N_MIN))
        raw, fl = p["raw_pairwise_agreement_complete_cases"], p["raw_floor_binding"]
        add(f"raw_agreement_{t}", raw, fl,
            None if (raw is None or fl is None) else bool(raw >= fl),
            f"floor DERIVED from observed marginals: P_e={p['P_e_from_observed_marginals']}, "
            f"bound by {p['which_floor_bound']}")
        add(f"complete_case_coverage_{t}", p["complete_case_coverage"],
            BC_G0_COMPLETE_CASE_COVERAGE_MIN,
            None if p["complete_case_coverage"] is None else
            bool(p["complete_case_coverage"] >= BC_G0_COMPLETE_CASE_COVERAGE_MIN))

    add("board_consensus_coverage", panels["board"]["consensus_coverage"],
        BC_G0_BOARD_CONSENSUS_COVERAGE_MIN,
        None if panels["board"]["consensus_coverage"] is None else
        bool(panels["board"]["consensus_coverage"] >= BC_G0_BOARD_CONSENSUS_COVERAGE_MIN))
    add("pair_consensus_coverage", panels["change"]["consensus_coverage"],
        BC_G0_PAIR_CONSENSUS_COVERAGE_MIN,
        None if panels["change"]["consensus_coverage"] is None else
        bool(panels["change"]["consensus_coverage"] >= BC_G0_PAIR_CONSENSUS_COVERAGE_MIN))
    add("user_consensus_coverage", panels["user"]["consensus_coverage"],
        BC_G0_USER_CONSENSUS_COVERAGE_MIN,
        None if panels["user"]["consensus_coverage"] is None else
        bool(panels["user"]["consensus_coverage"] >= BC_G0_USER_CONSENSUS_COVERAGE_MIN))

    dist = panels["board"]["consensus_label_distribution"]
    tot = sum(dist.values())
    b0 = (dist.get("B0", 0) / tot) if tot else None
    add("B0_share_of_consensus_board_labels", _r4(b0), BC_G0_B0_SHARE_MAX,
        None if b0 is None else bool(b0 <= BC_G0_B0_SHARE_MAX), "<= is the pass direction")

    resid = sum(m["residual_same_conversation_collisions"] for m in batch_meta_all)
    add("residual_same_conversation_batch_collisions", resid, BC_G0_COLLISIONS_MAX,
        bool(resid <= BC_G0_COLLISIONS_MAX), "== 0 is the pass direction")

    n_an = sum(1 for r in pairs if r["analysable_c1"])
    add("analysable_pairs", n_an, BC_G0_MIN_ANALYSABLE_PAIRS,
        bool(n_an >= BC_G0_MIN_ANALYSABLE_PAIRS),
        f"of {n_possible_pairs} possible pairs")

    # T-USER POSITIVE CONTROL on Stratum S (s3.2) -- the instrument check on the panel
    s_rows = [r for r in pairs if r["stratum"] == "S"
              and r["followup_id_N1"] == BC_SHIFT_POSITIVE_CONTROL_ID
              and r["followup_id_N"] != BC_SHIFT_POSITIVE_CONTROL_ID
              and r["user_verdict"] is not None]
    pc = (sum(1 for r in s_rows if r["user_verdict"] == "DIFFERENT-KIND") / len(s_rows)
          if s_rows else None)
    add("user_panel_positive_control_stratum_S", _r4(pc),
        BC_USER_PANEL_POSITIVE_CONTROL_MIN,
        None if pc is None else bool(pc >= BC_USER_PANEL_POSITIVE_CONTROL_MIN),
        f"n={len(s_rows)} U4-follows-non-U4 transitions in Stratum S. UNCOMPUTABLE -> "
        f"null -> the (a)/(b) split is UNMEASURED and Claim 2 is VACUOUS")

    n_fail = sum(1 for c in checks if c["pass"] is False)
    n_null = sum(1 for c in checks if c["pass"] is None)
    return {
        "checks": checks,
        "n_checks": len(checks), "n_failed": n_fail, "n_uncomputable_null": n_null,
        "GATE_0_PASS": bool(n_fail == 0 and n_null == 0),
        "KAPPA_NOT_COMPARABLE_ACROSS_TASKS": True,
        "kappa_note": (
            "T-BOARD is a 6-class task; T-CHANGE and T-USER are binary, where chance "
            "agreement is far higher and kappa is a harder, differently-scaled "
            "statistic. A kappa of 0.35 on a binary task is NOT the same achievement as "
            "0.35 on a 6-class task. No write-up may present them as one number."),
        "gates_are_null_when_uncomputable": True,
    }


# =====================================================================
# SEPARATION CONTROL (CONTROL 4) -- COMPUTED, never asserted
# =====================================================================
def separation_violations(A, rows):
    """s6.4 point 3: the violation set is COMPUTED at analyse time, not asserted.
    Hardcoding this check to true was a named defect in the retired design."""
    viol = []
    for task in ("board", "change", "user"):
        by_uid = {it["uid"]: it for it in build_items(rows, task)}
        for row in _jsonl_read(A.label_ckpt):
            if row.get("task") != task or row.get("status") != "ok":
                continue
            for uid in (row.get("labels") or {}):
                it = by_uid.get(uid)
                if it is None:
                    continue
                if task != "user" and row.get("reader") == it["gen_provider"]:
                    viol.append({"task": task, "uid": uid, "reader": row["reader"],
                                 "gen_provider": it["gen_provider"]})
    return viol


# =====================================================================
# STAGE -- ANALYSE
# =====================================================================
def run_panels(A, rows):
    panels, batch_meta_all, call_status = {}, [], {}
    for task in ("board", "change", "user"):
        items = build_items(rows, task)
        by_uid = {it["uid"]: it for it in items}
        marks = collect_marks(A.label_ckpt, task, by_uid)
        panels[task] = agreement_block(task, items, marks)
        panels[task]["reader_panel_note"] = (
            "STRUCTURE-PRESERVING HOLDOUT, NOT A SEPARATION CONTROL: T-USER items are "
            "our own bank strings, not model output, so no model can have written them. "
            "excluded_reader = BC_ORDER[conv_id % 4] keeps the panel exactly 3 wide, "
            "which Fleiss kappa requires." if task == "user" else
            "generator != labeller enforced at job-build time, at collection time, and "
            "recomputed as CONTROL 4 at analyse time.")
        per_reader = defaultdict(Counter)
        for r in _jsonl_read(A.label_ckpt):
            if r.get("task") == task:
                per_reader[r.get("reader")][r.get("status")] += 1
        call_status[task] = {k: dict(v) for k, v in per_reader.items()}
    for m in _jsonl_read(A.batch_meta_file):
        batch_meta_all.append(m)
    return panels, batch_meta_all, call_status


def pilot_size_block(pairs):
    """PROTECTION 1 + PROTECTION 2 (s8.3). r-hat is the observed MODEL-INITIATED change
    rate on the pilot's analysable pairs; the resize rule was written BEFORE any spend,
    so applying it later is not a deviation."""
    mi = [r for r in pairs if r["analysable_c2"]]
    n_chg = sum(1 for r in mi if r["gt_change"] == "CHANGE")
    r_hat = (n_chg / len(mi)) if mi else None
    an = [r for r in pairs if r["analysable_c1"]]
    overall = (sum(1 for r in an if r["gt_change"] == "CHANGE") / len(an)) if an else None
    out = {
        "n_analysable_pairs_claim1": len(an),
        "overall_change_base_rate_analysable": _r4(overall),
        "n_model_initiated_analysable_pairs": len(mi),
        "n_model_initiated_changes": n_chg,
        "r_hat_model_initiated_change_rate": _r4(r_hat),
        "planning_value_from_prereg": 0.25,
        "design_floor": 0.15,
        "hard_stop_rate": BC_PILOT_STOP_RATE,
        "pairs_per_conversation_constant": BC_PILOT_PAIRS_PER_CONV,
    }
    if r_hat is None or r_hat <= 0:
        out.update({"K_neutral": None, "K_raw": None,
                    "DECISION": "STOP -- CLAIM 2 VACUOUS",
                    "decision_reason": "r-hat is zero or uncomputable"})
        return out
    k_raw = math.ceil(BC_G2_MIN_CHANGES / (BC_PILOT_PAIRS_PER_CONV * r_hat))
    k = max(BC_RESIZE_MIN, min(BC_RESIZE_MAX, k_raw))
    out["K_raw_ceil_40_over_2p98_rhat"] = k_raw
    out["K_neutral_clamped_60_120"] = k
    if r_hat < BC_PILOT_STOP_RATE:
        out["DECISION"] = "STOP -- CLAIM 2 VACUOUS"
        out["decision_reason"] = (
            f"r-hat {r_hat:.4f} < the preregistered hard stop {BC_PILOT_STOP_RATE}. "
            f"Declare Claim 2 VACUOUS and DO NOT spend the remainder (s8.3, s14.4).")
    elif k_raw > BC_RESIZE_MAX:
        out["DECISION"] = "PROCEED AT THE 120 CAP -- 40-CHANGE FLOOR NOT GUARANTEED"
        out["decision_reason"] = (
            f"r-hat {r_hat:.4f} is at or above the {BC_PILOT_STOP_RATE} hard stop, so "
            f"the preregistered STOP does not fire, but the unclamped K_raw={k_raw} "
            f"exceeds the {BC_RESIZE_MAX} cap, so 40 model-initiated changes are not "
            f"guaranteed even at the ceiling. Reported, not silently clamped.")
    else:
        out["DECISION"] = f"PROCEED -- K_neutral = {k}"
        out["decision_reason"] = (
            f"r-hat {r_hat:.4f} -> ceil(40 / (2.98 * r-hat)) = {k_raw} -> clamped to "
            f"[{BC_RESIZE_MIN}, {BC_RESIZE_MAX}] = {k}")
    return out


def verdicts(g0, c1, c2_mi, pairs):
    def kill_state(gates, kills, downs):
        vals = [gates[k].get("pass") for k in kills if k in gates]
        dvals = [gates[k].get("pass") for k in downs if k in gates]
        if any(v is None for v in vals + dvals):
            return "VACUOUS", "a gate was UNCOMPUTABLE -> null, never true (s9 fail-closed)"
        if any(v is False for v in vals):
            return "REJECTED", "a kill gate failed"
        if any(v is False for v in dvals):
            return "PARTIAL", "the kill gates passed and a downgrade gate failed"
        return "HOLDS", "all gates for this claim passed"

    out = {}
    if not g0["GATE_0_PASS"]:
        out["CLAIM_1"] = {"verdict": "VACUOUS", "reason":
                          "Gate 0 failed or was uncomputable -> the claim was NEVER "
                          "TESTED, rather than tested and rejected. The prediction "
                          "statistics are still computed and written, so the run is not "
                          "wasted, but THEY ARE NOT EVIDENCE and may not be cited."}
        out["CLAIM_2"] = dict(out["CLAIM_1"])
    else:
        if not c1.get("computable"):
            out["CLAIM_1"] = {"verdict": "VACUOUS", "reason": "no analysable pairs"}
        else:
            v, why = kill_state(c1["gates"],
                                ["G1_1_SURFACE_PRIMARY_KILL", "G1_2_TRIVIAL_BASELINE",
                                 "G1_3_MCC", "G1_4_PERMUTATION_NULL",
                                 "G1_6_USER_MOVE_HARD_KILL"],
                                ["G1_7_TURN_POSITION_DOWNGRADE",
                                 "G1_8_GENERATOR_IDENTITY_DOWNGRADE"])
            out["CLAIM_1"] = {"verdict": v, "reason": why}
        if not c2_mi.get("computable") or not c2_mi["gates"]["G2_0_SAMPLE_FLOOR"]["pass"]:
            out["CLAIM_2"] = {"verdict": "VACUOUS", "reason":
                              "the Claim 2 sample floor was not reached (>= 40 "
                              "model-initiated changes AND >= 150 model-initiated "
                              "analysable pairs). NOT A REPAIR OPPORTUNITY -- re-running "
                              "with a corpus tuned until enough model-initiated changes "
                              "appear is selecting on the outcome and is forbidden."}
        else:
            v, why = kill_state(c2_mi["gates"],
                                ["G2_1_SURFACE_PRIMARY_KILL", "G2_2_TRIVIAL_BASELINE",
                                 "G2_3_MCC", "G2_4_PERMUTATION_NULL",
                                 "G2_5_USER_MOVE_HARD_KILL",
                                 "G2_6_TURN_POSITION_HARD_KILL",
                                 "G2_7_GENERATOR_IDENTITY_HARD_KILL"], [])
            out["CLAIM_2"] = {"verdict": v, "reason": why}
    out["A_CLAIM_1_PASS_DOES_NOT_LICENSE_CLAIM_2"] = True
    return out


def stage_analyze(A, rows, plan):
    panels, batch_meta_all, call_status = run_panels(A, rows)
    pairs = build_analysis_set(rows, panels)
    n_possible = sum(max(0, len(c["turns"]) - 1) for c in rows)
    g0 = gate0_block(panels, pairs, batch_meta_all, rows, n_possible)

    viol = separation_violations(A, rows)
    g0["checks"].append({"check": "CONTROL_4_generator_not_labeller_violations",
                         "value": len(viol), "floor": 0, "pass": bool(not viol),
                         "note": "COMPUTED, not asserted; violating ids listed in "
                                 "control_4_violations"})
    if viol:
        g0["GATE_0_PASS"] = False
        g0["n_failed"] += 1

    c1 = eval_claim1(pairs)
    c2_mi = eval_claim2(pairs, "MODEL-INITIATED", "Claim 2 -- the licensed subset")
    c2_ui = eval_claim2(pairs, "USER-INDUCED",
                        "NOT LICENSED -- USER-INDUCED CHANGE IS INSTRUCTION-FOLLOWING")
    ps = pilot_size_block(pairs)
    verd = verdicts(g0, c1, c2_mi, pairs)

    an = [r for r in pairs if r["analysable_c1"]]
    split = Counter(r["user_class"] for r in pairs if r["analysable_c1"])
    changes_by_class = Counter(r["user_class"] for r in an if r["gt_change"] == "CHANGE")
    persistence = {
        "realised_no_change_rate": _r4(
            sum(1 for r in an if r["gt_change"] == "SAME") / len(an)) if an else None,
        "per_conversation_change_rate": {
            str(c): _r4(sum(1 for r in an if r["conv_id"] == c and r["gt_change"] == "CHANGE")
                        / max(1, sum(1 for r in an if r["conv_id"] == c)))
            for c in sorted({r["conv_id"] for r in an})},
        "note": "CONTROL 7 -- descriptive. This is the quantity that killed the retired "
                "design and it is reported so the pivot stays auditable.",
    }

    non_pilot = [r for r in pairs if not r["is_pilot"]]
    sens = (eval_claim1(non_pilot) if any(r["analysable_c1"] for r in non_pilot)
            else {"computable": False,
                  "note": "no non-pilot conversations in this run -> the s8.3 "
                          "sensitivity recomputation is UNCOMPUTABLE"})

    report = {
        "WHAT_THIS_IS": (
            "Runner output for PREREG_BOARD_CHANGE_V1.md. Output space only. No weights "
            "claim, no activation claim, no localisation claim. The ground truth is a "
            "blind reader panel's judgement on the pair -- an observed rating, never a "
            "voltmeter reading from a model."),
        "ACCURACY_IS_FORBIDDEN_AS_A_HEADLINE": True,
        "PRIMARY_METRIC": "F1 on the CHANGE class, co-required with MCC > 0",
        "run": {
            "mode": ("smoke" if A.smoke else ("pilot" if A.pilot else "full")),
            "n_conversations": len(rows),
            "n_assistant_turns": sum(len(c["turns"]) for c in rows),
            "n_possible_pairs": n_possible,
            "turns_per_conversation_target": A.n_turns,
            "strata": dict(Counter(c["stratum"] for c in rows)),
            "families": dict(Counter(c["family"] for c in rows)),
            "generator_rotation": BC_ORDER,
            "reader_panel": MODELS,
            "frozen_family_plan_N": BC_FAMILY_PLAN_N,
            "frozen_family_plan_S": BC_FAMILY_PLAN_S,
            "family_shapes": BC_FAMILY_SHAPES,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "conv_file": A.conv_file, "label_ckpt": A.label_ckpt,
        },
        "GENERATION_BUDGET_DEVIATION": {
            "preregistered_max_tokens": BC_MAXTOK_GEN,
            "max_tokens_used": A.gen_max_tokens,
            "is_preregistration_deviation": bool(A.gen_max_tokens != BC_MAXTOK_GEN),
            "measured_defect": BC_GEN_BUDGET_DEFECT,
            "note": ("If is_preregistration_deviation is true this MUST be recorded in "
                     "PREREG_BOARD_CHANGE_V1.md s18 with a timestamp and a reason. If it "
                     "is false the corpus was generated at the preregistered budget, at "
                     "which 3 of the 4 frozen generators fail -- check the per-generator "
                     "turn counts before reading any number below."),
        },
        "immutability_sha256": check_hashes(A),
        "generation": generator_length_stats(rows),
        "generation_truncations": [{"conv_id": c["conv_id"], "n_turns": len(c["turns"]),
                                    "why": c["truncated_at"]}
                                   for c in rows if c["truncated_at"]],
        "reader_panels": {t: {k: v for k, v in panels[t].items() if k != "per_item"}
                          for t in panels},
        "per_reader_call_statuses": call_status,
        "labelling_batch_meta": batch_meta_all,
        "control_4_violations": viol,
        "GATE_0": g0,
        "user_induced_vs_model_initiated": {
            "split_of_analysable_pairs": dict(split),
            "changes_by_class": dict(changes_by_class),
            "unclassified_note": "UNCLASSIFIED transitions are excluded from both "
                                 "subsets, counted, and reported (s3.1).",
        },
        "CLAIM_1_DETECTION": c1,
        "CLAIM_2_EARLY_WARNING_MODEL_INITIATED": c2_mi,
        "CLAIM_2_ON_USER_INDUCED_SUBSET": dict(
            c2_ui, LICENCE="NOT LICENSED -- USER-INDUCED CHANGE IS INSTRUCTION-FOLLOWING"),
        "CONTROL_7_PERSISTENCE_DIAGNOSTIC": persistence,
        "PILOT_SIZE_GATE": ps,
        "NON_PILOT_SENSITIVITY_CLAIM_1": {
            "n_analysable_pairs": sens.get("n_analysable_pairs", 0),
            "PRIMARY_change_f1": sens.get("PRIMARY_change_f1"),
            "note": sens.get("note", "s8.3 preregistered sensitivity"),
        },
        "KILL_STATEMENT_CHECK": {
            "rule": "KILLED if surface_change_f1 >= board_change_f1 on Claim 1",
            "board_change_f1": c1.get("PRIMARY_change_f1"),
            "surface_change_f1": c1.get("surface_change_f1_max"),
            "killed": (None if (c1.get("PRIMARY_change_f1") is None
                                or c1.get("surface_change_f1_max") is None)
                       else bool(c1["surface_change_f1_max"] >= c1["PRIMARY_change_f1"])),
        },
        "INSTRUMENT_KILL_CHECK": {
            "rule": f"KILLED if T-CHANGE Fleiss kappa < {BC_KILL_KAPPA_CHANGE}",
            "kappa": panels["change"]["fleiss_kappa_complete_cases"],
            "killed": (None if panels["change"]["fleiss_kappa_complete_cases"] is None
                       else bool(panels["change"]["fleiss_kappa_complete_cases"]
                                 < BC_KILL_KAPPA_CHANGE)),
            "vacuous_band": f"[{BC_KILL_KAPPA_CHANGE}, {BC_G0_KAPPA_MIN_CHANGE}) -> VACUOUS",
        },
        "VERDICTS": verd,
        "CLAIM_CEILING": [
            "Output space only. No weights, activation or localisation claim.",
            "CAS-specificity stays GREY. The matched-taxonomy control is NOT in v1 and "
            "no result here may be described as CAS-specific, in any wording.",
            "A Claim 1 pass does NOT license Claim 2; Claim 2 on user-induced changes "
            "licenses nothing.",
            "The ground truth is a reader judgement, not physics.",
            "The base rate is ENRICHED by seed selection and is NOT an estimate of how "
            "often models change board in the wild.",
            "The board panel and the change panel share the same four models. "
            "Separation is by task and by call, not by model identity.",
            "The board-to-board sequencing question is ours, not the framework's.",
            "One corpus, one panel, four related commercial models. Not replication.",
            "No individual confusion-matrix cell is a result (s7.4 multiplicity).",
            "Nothing here revives Claim A.",
        ],
        "analysis_pairs": pairs,
        "reader_panel_per_item": {t: panels[t]["per_item"] for t in panels},
    }
    with open(A.report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print_report(report, A)
    return report


# =====================================================================
# PRINTING
# =====================================================================
def _fmt(v):
    return "n/a" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))


def print_report(rep, A):
    W = 84
    R = rep["run"]
    print("\n" + "=" * W)
    print(f"BOARD CHANGE TEST -- {R['mode'].upper()}   "
          f"{R['n_conversations']} convos / {R['n_assistant_turns']} turns / "
          f"{R['n_possible_pairs']} possible pairs")
    print("=" * W)

    print("\nGENERATION")
    g = rep["generation"]
    print(f"  per-generator median chars : {g['median_chars_per_generator']}")
    print(f"  max/min median ratio       : {g['max_min_median_ratio']}  "
          f"GENERATOR_LENGTH_IMBALANCE_FLAG={g['GENERATOR_LENGTH_IMBALANCE_FLAG']}")
    print(f"  truncated conversations    : {len(rep['generation_truncations'])}")

    print("\nREADER PANELS (Gate 0 inputs)")
    print(f"  {'task':<8}{'kappa':>8}{'raw':>8}{'floor':>8}{'cc_cov':>9}"
          f"{'cons_cov':>10}{'n_cc':>7}")
    for t in ("board", "change", "user"):
        p = rep["reader_panels"][t]
        print(f"  {t:<8}{_fmt(p['fleiss_kappa_complete_cases']):>8}"
              f"{_fmt(p['raw_pairwise_agreement_complete_cases']):>8}"
              f"{_fmt(p['raw_floor_binding']):>8}"
              f"{_fmt(p['complete_case_coverage']):>9}"
              f"{_fmt(p['consensus_coverage']):>10}{p['n_complete_cases']:>7}")
    print("  KAPPA_NOT_COMPARABLE_ACROSS_TASKS = True (6-class vs binary)")
    print(f"  board consensus label mix  : "
          f"{rep['reader_panels']['board']['consensus_label_distribution']}")
    print(f"  change consensus mix       : "
          f"{rep['reader_panels']['change']['consensus_label_distribution']}")
    print(f"  user consensus mix         : "
          f"{rep['reader_panels']['user']['consensus_label_distribution']}")

    print("\nGATE 0")
    for c in rep["GATE_0"]["checks"]:
        mark = {True: "PASS", False: "FAIL", None: "NULL"}[c["pass"]]
        print(f"  [{mark}] {c['check']:<46} {_fmt(c['value']):>9}  floor "
              f"{_fmt(c['floor'])}")
    print(f"  GATE_0_PASS = {rep['GATE_0']['GATE_0_PASS']}  "
          f"({rep['GATE_0']['n_failed']} failed, "
          f"{rep['GATE_0']['n_uncomputable_null']} uncomputable->null)")

    sp = rep["user_induced_vs_model_initiated"]
    print("\nUSER-INDUCED vs MODEL-INITIATED (blind T-USER panel, s3.1)")
    print(f"  analysable pairs by class : {sp['split_of_analysable_pairs']}")
    print(f"  CHANGES by class          : {sp['changes_by_class']}")

    for key, title in (("CLAIM_1_DETECTION", "CLAIM 1 -- DETECTION (retrospective)"),
                       ("CLAIM_2_EARLY_WARNING_MODEL_INITIATED",
                        "CLAIM 2 -- EARLY WARNING (model-initiated subset ONLY)"),
                       ("CLAIM_2_ON_USER_INDUCED_SUBSET",
                        "CLAIM 2 on the USER-INDUCED subset")):
        c = rep[key]
        print("\n" + "-" * W)
        print(title)
        if key == "CLAIM_2_ON_USER_INDUCED_SUBSET":
            print(f"  {c['LICENCE']}")
        if not c.get("computable"):
            print(f"  NOT COMPUTABLE: {c.get('note')}  "
                  f"(n_pairs={c.get('n_analysable_pairs')}, "
                  f"n_changes={c.get('n_changes')})")
            continue
        m = c.get("metrics")
        if m:
            print(f"  n pairs {m['n']}   BASE RATE (CHANGE) {_fmt(m['base_rate_CHANGE'])}")
            print(f"  change-class F1 {_fmt(m['change_f1'])}   "
                  f"precision {_fmt(m['precision_CHANGE'])}   "
                  f"recall {_fmt(m['recall_CHANGE'])}   MCC {_fmt(m['mcc'])}")
            cm = m["confusion_2x2"]
            print(f"  confusion 2x2   TP {cm['TP']}  FP {cm['FP']}  "
                  f"TN {cm['TN']}  FN {cm['FN']}")
            print(f"  accuracy {_fmt(m['accuracy_DIAGNOSTIC_NOT_THE_RESULT'])} "
                  f"[DIAGNOSTIC -- NOT THE RESULT; base rate "
                  f"{_fmt(m['base_rate_CHANGE'])}]")
        print(f"  surface battery : {c['surface_battery_change_f1']}   "
              f"strongest = {c['strongest_surface_arm']}")
        print(f"  controls        : {c['controls_change_f1']}")
        tb = c.get("trivial_baseline")
        if tb:
            print(f"  trivial bar     : {tb['trivial_f1_bar']} "
                  f"({tb['binding_strategy']}; 2p/(1+p)={tb['formula_2p_over_1_plus_p']})")
        pn = c.get("permutation_null")
        if pn:
            print(f"  perm null       : mean {pn['null_mean']}  p95 {pn['null_p95']}  "
                  f"p99 {pn['null_p99']}  empirical p {pn['empirical_p']}")
        for gk, gv in c["gates"].items():
            mark = {True: "PASS", False: "FAIL", None: "NULL"}[gv.get("pass")]
            extra = ""
            if "point_margin" in gv:
                extra = f"margin {_fmt(gv['point_margin'])} p5 {_fmt(gv['boot_p5'])}"
            elif "empirical_p" in gv:
                extra = f"p {gv['empirical_p']}"
            elif "mcc" in gv:
                extra = f"mcc {gv['mcc']} p5 {gv['boot_p5']}"
            elif "n_changes" in gv:
                extra = f"{gv['n_changes']} changes / {gv['n_pairs']} pairs"
            print(f"    [{mark}] {gk:<40} {extra}")

    print("\n" + "-" * W)
    print("KILL STATEMENT")
    k = rep["KILL_STATEMENT_CHECK"]
    print(f"  board_change_f1 {_fmt(k['board_change_f1'])} vs "
          f"surface_change_f1 {_fmt(k['surface_change_f1'])} -> KILLED={k['killed']}")
    ik = rep["INSTRUMENT_KILL_CHECK"]
    print(f"  T-CHANGE kappa {_fmt(ik['kappa'])} vs kill floor "
          f"{BC_KILL_KAPPA_CHANGE} -> KILLED={ik['killed']}")

    ps = rep["PILOT_SIZE_GATE"]
    print("\n" + "-" * W)
    print("PILOT SPEND GATE (s8.3)")
    print(f"  analysable pairs (Claim 1)         : {ps['n_analysable_pairs_claim1']}")
    print(f"  overall change base rate           : "
          f"{_fmt(ps['overall_change_base_rate_analysable'])}")
    print(f"  model-initiated analysable pairs   : "
          f"{ps['n_model_initiated_analysable_pairs']}")
    print(f"  model-initiated CHANGES            : {ps['n_model_initiated_changes']}")
    print(f"  r-hat                              : "
          f"{_fmt(ps['r_hat_model_initiated_change_rate'])}  "
          f"(planning 0.25, design floor 0.15, HARD STOP < "
          f"{BC_PILOT_STOP_RATE})")
    print(f"  K_raw = ceil(40/(2.98*r-hat))      : {ps.get('K_raw_ceil_40_over_2p98_rhat')}")
    print(f"  K_neutral clamped to [60,120]      : {ps.get('K_neutral_clamped_60_120')}")
    print(f"  DECISION                           : {ps['DECISION']}")
    print(f"    {ps['decision_reason']}")

    print("\n" + "=" * W)
    print("VERDICTS")
    for k2 in ("CLAIM_1", "CLAIM_2"):
        v = rep["VERDICTS"][k2]
        print(f"  {k2}: {v['verdict']}  -- {v['reason']}")
    print("  CLAIM 2 on the user-induced subset: NOT LICENSED -- USER-INDUCED CHANGE IS "
          "INSTRUCTION-FOLLOWING")
    ih = rep["immutability_sha256"]
    print(f"  prereg/runner sha256 match: {ih['match']} {ih.get('note','')}")
    print("=" * W)
    print(f"wrote {A.report_file}")


# =====================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pilot", action="store_true",
                    help="16 Stratum N conversations (~409 calls, $6-$18). "
                         "RED-LIGHT-ONLY: a pilot CANNOT PASS Gate 0.")
    ap.add_argument("--smoke", action="store_true",
                    help="mechanical check only. RUN THIS FIRST.")
    ap.add_argument("--stage", default="all",
                    choices=["all", "generate", "label", "gate0", "pilot-size", "analyze"])
    ap.add_argument("--task", default="all", choices=["all", "board", "change", "user"])
    ap.add_argument("--n-convos", type=int, default=8, help="smoke only")
    ap.add_argument("--n-turns", type=int, default=None)
    ap.add_argument("--min-turns", type=int, default=None)
    ap.add_argument("--repair-rounds", type=int, default=BC_REPAIR_ROUNDS)
    ap.add_argument("--repair-batch-size", type=int, default=BC_REPAIR_BATCH)
    ap.add_argument("--workers", type=int, default=0,
                    help="0 = sum of per-provider concurrency (9). Raising this does "
                         "NOT raise GLM throughput.")
    ap.add_argument("--allow-reasoning-only", action="store_true",
                    help="PREREGISTRATION DEVIATION (s6.4). Must be logged in s18.")
    ap.add_argument("--gen-max-tokens", type=int, default=BC_MAXTOK_GEN,
                    help="generation budget. Default is the PREREGISTERED 800, at which "
                         "3 of the 4 frozen generators return an empty or truncated "
                         "answer (see BC_GEN_BUDGET_DEFECT). Raising it is a s18 "
                         "PREREGISTRATION AMENDMENT and an OWNER DECISION; the report "
                         "records it as a deviation.")
    ap.add_argument("--out-dir", default=HERE)
    A = ap.parse_args()

    if A.smoke and A.pilot:
        raise SystemExit("--smoke and --pilot are mutually exclusive")
    if not A.smoke and not A.pilot and A.stage != "analyze":
        raise SystemExit("this runner is gated on the pilot spend gate: pass --smoke "
                         "or --pilot. The full run is only licensed after --stage "
                         "pilot-size prints a PROCEED decision.")
    tag = "_smoke" if A.smoke else ("_pilot" if A.pilot else "")
    A.n_turns = A.n_turns or (3 if A.smoke else BC_TURNS_PER_CONV)
    A.min_turns = A.min_turns or (2 if A.smoke else BC_MIN_TURNS)
    A.batch_override = ({"board": 6, "change": 4, "user": 6} if A.smoke else {})
    A.conv_file = os.path.join(A.out_dir, f"conversations_change{tag}.jsonl")
    A.label_ckpt = os.path.join(A.out_dir, f"label_calls_change{tag}.jsonl")
    A.batch_meta_file = os.path.join(A.out_dir, f"batch_meta_change{tag}.jsonl")
    A.report_file = os.path.join(A.out_dir, f"board_change_report{tag}.json")
    A.hash_file = os.path.join(A.out_dir, f"board_change_hashes{tag}.json")

    full_plan, blind_meta = build_corpus_plan()
    plan = select_plan(A, full_plan)
    print(f"board CHANGE test [{'smoke' if A.smoke else 'pilot' if A.pilot else 'full'}]: "
          f"{len(plan)} conversations x {A.n_turns} turns; strata "
          f"{dict(Counter(p['stratum'] for p in plan))}; families "
          f"{dict(Counter(p['family'] for p in plan))}; generator rotation {BC_ORDER}",
          flush=True)
    print(f"  blind seed bank: {blind_meta.get('author_note', '')}", flush=True)
    if A.stage in ("all", "generate"):
        if A.gen_max_tokens == BC_MAXTOK_GEN:
            print(f"\n  *** WARNING -- GENERATION BUDGET: max_tokens={A.gen_max_tokens} is "
                  f"the PREREGISTERED value, and 3 of the 4 frozen generators FAIL at it.\n"
                  f"      {BC_GEN_BUDGET_DEFECT}\n", flush=True)
        else:
            print(f"\n  *** PREREGISTRATION DEVIATION: --gen-max-tokens="
                  f"{A.gen_max_tokens} (preregistered {BC_MAXTOK_GEN}). Record this in "
                  f"s18 with a timestamp and a reason.\n", flush=True)

    if A.stage in ("all", "generate"):
        stage_generate(A, plan)
    if A.stage == "generate":
        return

    rows = load_conversations(A, plan)
    if not rows:
        raise SystemExit(f"no conversations in {A.conv_file}; run --stage generate first.")

    if A.stage in ("all", "label"):
        tasks = ["change", "user", "board"] if A.task == "all" else [A.task]
        for t in tasks:
            res = stage_label(A, t, rows)
            for m in res["batch_meta"]:
                _jsonl_append(A.batch_meta_file, m)
    if A.stage == "label":
        return

    if A.stage == "gate0":
        panels, bm, _ = run_panels(A, rows)
        pairs = build_analysis_set(rows, panels)
        n_possible = sum(max(0, len(c["turns"]) - 1) for c in rows)
        g0 = gate0_block(panels, pairs, bm, rows, n_possible)
        print("\nGATE 0 ONLY -- no prediction statistic is computed at this stage.")
        for c in g0["checks"]:
            mark = {True: "PASS", False: "FAIL", None: "NULL"}[c["pass"]]
            print(f"  [{mark}] {c['check']:<46} {_fmt(c['value']):>9}  floor "
                  f"{_fmt(c['floor'])}   {c['note']}")
        print(f"\n  GATE_0_PASS = {g0['GATE_0_PASS']}")
        with open(os.path.join(A.out_dir, f"board_change_gate0{tag}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(g0, f, indent=2, ensure_ascii=False, default=str)
        return

    if A.stage == "pilot-size":
        panels, _, _ = run_panels(A, rows)
        pairs = build_analysis_set(rows, panels)
        ps = pilot_size_block(pairs)
        print("\nPILOT SPEND GATE")
        for k, v in ps.items():
            print(f"  {k:<44} {v}")
        with open(os.path.join(A.out_dir, f"board_change_pilot_size{tag}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(ps, f, indent=2, ensure_ascii=False, default=str)
        return

    stage_analyze(A, rows, plan)


if __name__ == "__main__":
    main()
