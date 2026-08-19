"""Gate 4 -- the "NEXT BOARD" prediction test, v1 (Rev 0.4, post-adversarial-review).

Preregistration: PREREG_NEXT_BOARD_V1.md (same directory). READ IT FIRST.
This script implements that document and nothing else. Gates and thresholds are
frozen there; they are mirrored here as module constants and must not be edited
after the first labelling call. The analyze stage writes a sha256 of BOTH files
into the report so an edit after the fact is detectable.

HYPOTHESIS
    The CCB board type of assistant turn N predicts the board type of turn N+1
    above chance, above the marginal base rate, and above a surface model of
    turn N's raw text.

WHAT THIS IS NOT
    Output space only. No weights claim. The board-to-board sequencing claim is
    OURS, not the CAS-PCBA book's -- the book describes intra-board stage
    sequencing richly and inter-board sequencing not at all (PREREG section 3).
    CAS-specificity is addressed (not settled) by the v1 matched-taxonomy arm.

TWO CORPUS SOURCES (--generator, Rev 0.5 / PREREG v2, amended v2.1)
    --generator api   (default, unchanged)  four commercial models write the turns.
                      PRIMARY CLAIM = ecological sequential prediction.
    --generator sdg   forced-transition corpus from cas-synthetic's multi-turn
                      generator. That generator is TEMPLATE-RENDERED: it makes no
                      model call, no network call and no inference of any kind; its
                      whole live surface vocabulary is 22 authored strings.

                      *** THIS ARM IS WITHDRAWN AT v2.1 ON TWO NAMED KILLS. ***

                      (1) MAPPING CIRCULARITY. The turn-type -> board answer key was
                          authored by reading the rendered template strings THROUGH
                          THE SAME RUBRIC the reader panel is given. The statistic
                          therefore measures whether an LLM panel applying rubric R
                          to string S reproduces the label an author assigned to S by
                          applying R. It has NO INFORMATIVE RANGE. The v2 name
                          "INSTRUMENT CALIBRATION AGAINST KNOWN GROUND TRUTH" is
                          WITHDRAWN as unearned -- the truth was not known
                          independently, it was authored by the process under test.
                          The statistic is now RUBRIC ADHERENCE / READER RELIABILITY,
                          and CALIBRATED is not an available verdict anywhere.

                      (2) SURFACE-DETERMINED CORPUS. Measured on the realised
                          36-conversation corpus with LOCO folds grouped by
                          conversation: char TF-IDF = 1.0000, word unigram = 1.0000,
                          RAW CHARACTER COUNT = 1.0000. 38 distinct strings, zero
                          ambiguous, disjoint per-class length ranges. The
                          primary-kill gate (ra_acc - surface_acc >= 0.05) is
                          UNSATISFIABLE by any accuracy, so the verdict was fixed
                          before any labelling call. Preregistering a foregone kill
                          is not a study.

                      Both kills are taken for $0 by `--stage precheck`, and
                      `--stage label` REFUSES TO SPEND MONEY while either fires.
                      Reviving the arm requires a corpus whose SURFACE DOES NOT
                      DETERMINE THE LABEL and an answer key not derived from the
                      rubric -- not a relaxed bar.

STAGES
    --stage generate                 multi-turn conversations, generator rotated
    --stage precheck                 (sdg only) $0 surface-determinism + circularity
                                     kill; no reader panel, no network, no spend
    --stage label --taxonomy board   3 blind readers per turn; never its generator
    --stage label --taxonomy alt     matched 6-class discourse taxonomy, same panel
    --stage gate0                    agreement/coverage ONLY (read before prediction)
    --stage analyze                  prediction + all controls + all gates

    python next_board_test.py --stage generate --smoke
    python next_board_test.py --stage label --taxonomy board --smoke
    python next_board_test.py --stage gate0 --smoke
    python next_board_test.py --stage analyze --smoke

    python next_board_test.py --stage generate --generator sdg
    python next_board_test.py --stage precheck --generator sdg    # <- stops here

Both API stages CHECKPOINT to JSONL as each unit lands and SKIP completed units
on restart, so a crash never costs the stage.

INFRA REUSE (docs/working/gate2_closure/independent_bank/)
    providers.resolve             key handling; never prints key values
    pilot_label.call_with_retry   the ONLY transport: per-provider semaphores
                                  (gemini 4 / deepseek 2 / qwen 2 / glm 1), the
                                  GLM 7.0s proactive interval, 6 exponential retries
    pilot_label.MODELS            frozen 4-model blindness-probed panel
    l1_agreement.fleiss_kappa     shared Fleiss implementation
    acceptance_gate.gate_surface_separability   char TF-IDF(3,5) recipe (companion
                                  diagnostic only -- it is UNGROUPED, see notes)
    gen_real_outputs.PROMPTS      the existing 36-prompt seed bank (comparability)
"""
import os
import re
import sys
import json
import time
import random
import hashlib
import argparse
import itertools
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.linear_model import LogisticRegression

# Display only. Small LOCO folds on sparse char features routinely hit the lbfgs
# iteration cap; max_iter=500 is FROZEN because it is the acceptance_gate recipe, so
# the warning is expected noise and would otherwise bury the gate output. No logic change.
warnings.filterwarnings("ignore", category=ConvergenceWarning)

# --- sibling-directory infra ------------------------------------------------
# The independent_bank scripts import each other by BARE module name, so its
# directory must be on sys.path before we import any of them.
HERE = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.abspath(os.path.join(HERE, "..", "gate2_closure", "independent_bank"))
if BANK_DIR not in sys.path:
    sys.path.insert(0, BANK_DIR)

import providers                                          # noqa: E402
from pilot_label import call_with_retry, MODELS           # noqa: E402
from l1_agreement import fleiss_kappa                     # noqa: E402
from acceptance_gate import gate_surface_separability     # noqa: E402
from gen_real_outputs import PROMPTS                      # noqa: E402
from openai import OpenAI                                 # noqa: E402

try:  # Windows console is cp1252 and provider errors carry non-latin text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- cas-synthetic SDG (forced-transition arm) -------------------------------
# IMPORTED, NEVER COPIED. The package directory name contains a hyphen so it is
# not importable as a package; spec_from_file_location + an EXPLICIT sys.modules
# registration is required (on Python 3.14 @dataclass looks up cls.__module__ in
# sys.modules and raises AttributeError if the module was not registered before
# exec_module()). Loaded LAZILY so the api arm never pays for it and never fails
# when cas-synthetic is absent.
SDG_PATH = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "cas-synthetic", "generator", "multi_turn",
    "conversation_generator.py"))
_SDG_MOD = None


def load_sdg():
    global _SDG_MOD
    if _SDG_MOD is None:
        import importlib.util
        if not os.path.exists(SDG_PATH):
            raise SystemExit(f"--generator sdg requires {SDG_PATH}, which was not found.")
        spec = importlib.util.spec_from_file_location("cas_sdg_conversation_generator", SDG_PATH)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["cas_sdg_conversation_generator"] = mod   # MUST precede exec_module
        spec.loader.exec_module(mod)
        _SDG_MOD = mod
    return _SDG_MOD

# =====================================================================
# FROZEN CONSTANTS (mirror PREREG_NEXT_BOARD_V1.md -- do not edit post-hoc)
# =====================================================================
ORDER = ["gemini", "deepseek", "qwen", "glm"]
# Per-provider concurrency, matched to pilot_label._SEM. Generation and labelling
# pools are sized to this sum so a worker blocked on the GLM Semaphore(1) never
# starves the other three providers (review MINOR: workers=6 vs GLM sem=1).
PROVIDER_CONCURRENCY = {"gemini": 4, "deepseek": 2, "qwen": 2, "glm": 1}

SEED_PROMPT_SAMPLE = 20260819    # seed for choosing the seed prompts
SEED_FOLLOWUP_BASE = 770000      # + conv_id -> i.i.d. follow-up draws (WITH replacement)
SEED_BATCH_BASE = 4242           # + reader index -> labelling batch shuffle
SEED_ALIAS_BASE = 91000          # + reader/batch -> per-batch excerpt alias ids
SEED_PERM_NULL = 0               # permutation-null rng
SEED_BOOTSTRAP = 7               # paired cluster-bootstrap rng
SEED_SDG_BASE = 880000           # + conv_id -> SDG template-render rng (ADDED at v2;
                                 # a NEW constant, so no v1 value is edited post-hoc)
N_PERM_TRIALS = 1000
N_BOOT = 2000

MAXTOK_LABEL = 16000   # reasoning models spend the budget on trace before emitting JSON

# ---- Gate 0 -- agreement / viability floor (VACUOUS escape) ----
# Arithmetic (PREREG 8, shown so the thresholds are JOINTLY satisfiable):
#   full run = 36 conversations (the WHOLE gen_real_outputs prompt bank) x 7 assistant
#   turns = 252 turns, and 36 x 6 = 216 possible (N -> N+1) pairs.
#   A pair needs a consensus label at BOTH ends, so pairs ~= 216 * c^2 where c is
#   consensus coverage:   c=0.70 -> 106 pairs   c=0.65 -> 91   c=0.60 -> 78.
#   The pair floor is therefore 90 and the consensus floor 0.70, which are jointly
#   satisfiable with margin. Rev 0.3 set a 100-pair floor on 30x6 = 150 possible pairs,
#   which silently DEMANDED c >= 0.82 while stating 0.70 in the same table -- mutually
#   inconsistent, and an automatic VACUOUS at this panel's measured coverage
#   (l1_real 0.556 complete-case, l2_wiring 0.694).
G0_FLEISS_MIN = 0.35             # 3 readers, 6 classes, complete cases only
G0_RAW_AGREE_ABS_MIN = 0.50      # absolute floor; the BINDING floor is derived from
                                 # the observed marginals (see derived_raw_floor)
G0_COMPLETE_COV_MIN = 0.60       # all 3 readers returned -> honest kappa denominator
G0_COMPLETE_N_MIN = 60           # kappa on fewer complete cases is not interpretable
G0_CONSENSUS_COV_MIN = 0.70      # >=2 AGREEING among >=2 PRESENT labels
G0_B0_SHARE_MAX = 0.40
G0_MIN_PAIRS = 90                # relaxed automatically under --smoke

# ---- Gates 1..8 ----
G1_MARGIN_OVER_SURFACE = 0.05    # PRIMARY KILL; surface = max(char, word, length)
G2_MARGIN_OVER_MARGINAL = 0.05
G3_ALPHA = 0.05
G5_MARGIN_OVER_PERSISTENCE = 0.05
G6_MARGIN_OVER_USERMOVE = 0.05   # HARD KILL in Rev 0.4 (was a downgrade)
G7_MARGIN_OVER_TURNPOS = 0.05
G8_MARGIN_OVER_ALT_TAXONOMY = 0.05
BOOT_LOWER_Q = 5.0               # paired cluster-bootstrap percentile that must exceed 0

# ---- Kill / downgrade flags ----
KILL_FLEISS_BELOW = 0.20         # taxonomy kill
KILL_B0_SHARE_ABOVE = 0.60       # fit kill
SAME_TURN_SURFACE_FLAG = 0.667   # 4x chance for a 6-way task -> surface-artifact flag

BOARDS = ["B1", "B2", "B3", "B4", "B5", "B0"]
ALTCODES = ["D1", "D2", "D3", "D4", "D5", "D0"]
CHANCE = 1.0 / len(BOARDS)

# Internal mapping -- NEVER shown to a reader.
BOARD_TO_CCB = {
    "B1": "CCB-1 CSB Cognitive Safety Board",
    "B2": "CCB-2 COB Cognitive Oscillator Board",
    "B3": "CCB-3 CDAB Cognitive Differential Amplifier Board",
    "B4": "CCB-4 CMB Cognitive Memory Board",
    "B5": "CCB-5 CPMB Cognitive Power Management Board",
    "B0": "(none dominates)",
}

# Board-agnostic follow-up moves. Rev 0.4: drawn i.i.d. WITH REPLACEMENT, one
# independent draw per (conversation, turn). Rev 0.3 drew a PERMUTATION (each used
# exactly once), which makes f_t and f_{t+1} dependent -- P(f_{t+1}=u | f_t=u) = 0
# against an unconditional 1/5 -- and therefore manufactures a b_N -> b_{N+1}
# dependence with zero board content. That was a TRUE-BY-CONSTRUCTION defect.
FOLLOWUPS = [
    ("U1", "Say more about that."),
    ("U2", "What's the strongest case against what you just said?"),
    ("U3", "I don't think that's right. Convince me, or change your mind."),
    ("U4", "Okay - what should I actually do first?"),
    ("U5", "How would you know if you were wrong here?"),
]

# =====================================================================
# SDG FORCED-TRANSITION ARM (ADDED at v2; nothing above this block is edited)
# =====================================================================
# TEMPLATE DISCLOSURE -- decisive, and repeated in the first paragraph of the
# preregistration and in the first key of every SDG report.
SDG_TEMPLATE_DISCLOSURE = (
    "cas-synthetic's multi-turn generator is TEMPLATE-RENDERED. It calls no model, "
    "makes no network request and runs no inference: _render_turn selects a string "
    "from a fixed table and does template.format(cas=...). Its ENTIRE live surface "
    "vocabulary is 22 authored strings (7 user openers, 4 user repairs, 2 user "
    "closes, 15 assistant templates, of which 6 differ only by a substituted CAS "
    "expression; a further 6 authored strings are unreachable dead constants). Only "
    "7 distinct CAS expressions exist in the whole generator. CONSEQUENCE: a lens "
    "applied to this text is evidence about THE LENS and THE TEMPLATES and carries "
    "NO information whatsoever about model outputs. Because the phrasing is fixed, "
    "the SURFACE CONTROL MATTERS MORE HERE, NOT LESS: a char/word model will learn "
    "the template table almost perfectly. A surface WIN on this corpus KILLS the arm "
    "outright (GATE RA-2). MEASURED: char 1.0000, word 1.0000, RAW CHARACTER COUNT "
    "1.0000 -- the surface control did not merely win, it is a BIJECTION onto the "
    "answer key, so GATE RA-2 is unsatisfiable by any accuracy whatsoever."
)
SDG_MODEL_ID = ("cas-synthetic/generator/multi_turn/conversation_generator.py "
                "(template renderer, NO model inference)")

# ---- MAPPING CIRCULARITY -- A NAMED KILL, NOT A CAVEAT (added at v2.1) ----
# The defect that VOIDS the primary statistic, disclosed here and in PREREG v2
# section 3B.0. The turn-type -> board answer key was authored by READING THE
# RENDERED TEMPLATE STRINGS THROUGH THE SAME RUBRIC the reader panel is given.
# REFUSE renders exactly one string -- "I can't take that turn -- it would break
# the admissibility of the dialog. Want to try a different angle?" -- and the B1
# rubric's lead clause is "Decides whether to answer or to decline ... a real
# answer OR an explicit refusal". That is a near-verbatim cue, not an independent
# construction. So the statistic measures "does an LLM panel applying rubric R to
# string S reproduce the label an author assigned to string S by applying rubric
# R". It has NO INFORMATIVE RANGE: a pass is guaranteed by the authoring, a fail
# indicates only reader noise. The phrase "known ground truth" is therefore
# UNEARNED -- the truth was not known independently, it was authored by the
# process under test. The statistic is consequently reported as a RUBRIC-ADHERENCE
# / READER-RELIABILITY check and is NOT LICENSED as calibration.
SDG_MAPPING_CIRCULARITY_KILL = True      # standing kill for THIS answer key
SDG_MAPPING_CIRCULARITY_DISCLOSURE = (
    "MAPPING CIRCULARITY -- NAMED KILL. The turn-type -> board answer key was "
    "authored by reading the rendered template strings THROUGH THE SAME RUBRIC "
    "the reader panel is given. B1's answer key is ONE byte-identical string "
    "whose wording ('it would break the admissibility of the dialog', an explicit "
    "decline citing a standing principle) is a near-verbatim cue for the B1 "
    "rubric's lead clause; B5's is one template ('the next step on the pathway "
    "would be to strengthen the prerequisite that's currently weakest') against a "
    "rubric containing 'sequences explicitly before engaging'. The statistic "
    "therefore measures whether an LLM panel applying rubric R to string S "
    "reproduces the label an author assigned to string S by applying rubric R. It "
    "has NO INFORMATIVE RANGE: a pass is guaranteed by the authoring, a fail "
    "indicates reader noise only. It is NOT CALIBRATION and the truth is NOT "
    "INDEPENDENTLY KNOWN. Reported as RUBRIC ADHERENCE / READER RELIABILITY. The "
    "words CALIBRATED and KNOWN GROUND TRUTH are not available verdicts anywhere "
    "in this arm."
)

# ---- SURFACE DETERMINISM -- MEASURED AT $0, BEFORE ANY LABELLING CALL ----
# The second reason the arm as specified is unfalsifiable. Measured on the realised
# 36-conversation corpus (228 labelled turns) with LOCO folds grouped by
# conversation, on the ground-truth task itself:
#     char TF-IDF(3,5) = 1.0000    word unigram = 1.0000    RAW CHAR COUNT = 1.0000
# The corpus is 38 DISTINCT STRINGS with ZERO ambiguity across boards, so exact
# string lookup is a BIJECTION onto the prescribed board; and the three classes
# have DISJOINT LENGTH DISTRIBUTIONS (B0 30-97 chars, B1 exactly 104, B5 108-117),
# so a ONE-FEATURE LENGTH CLASSIFIER is perfect. Any surface-margin gate of the
# form (acc - 1.0000) >= margin is UNSATISFIABLE for any accuracy whatsoever, so
# the arm's verdict is decided before a single labelling call is made.
# Preregistering a foregone kill is not a study. The kill is therefore taken at $0
# by sdg_precheck() -- no reader panel, no ~256 label calls, no GLM serialisation --
# and stage_label REFUSES TO SPEND MONEY while the precheck fails.
SDG_PRECHECK_SURFACE_MAX = 0.60  # surface acc on the ground-truth task at or above
                                 # which the corpus is SURFACE-DETERMINED and the arm
                                 # is WITHDRAWN. 0.60 is well above the 0.3947 modal
                                 # -prescribed-class rate and far below the measured
                                 # 1.0000, so the bar is neither trivial nor unreachable.
SDG_ARM_STATUS = (
    "WITHDRAWN BY DEFAULT. The corpus is surface-determined (measured 1.0000 on "
    "char, word AND raw length), so the primary-kill gate cannot be passed by any "
    "accuracy and the answer key is circular with the rubric. Both defects are "
    "obtained on the record at $0 by `--stage precheck`. Labelling is BLOCKED "
    "unless --allow-surface-determined-corpus is passed, which is PREREG-DEVIATING "
    "and must be logged in the amendment log. To revive the arm, replace the corpus "
    "with text whose surface does not determine the label -- not by relaxing a bar."
)

# ---- THE TURN-TYPE -> BOARD MAPPING IS OURS ----
# cas-synthetic speaks DIALOG ACTS (OPEN/ACK/CLARIFY/ANSWER/PLAN/REFUSE/...); the
# taxonomy speaks BOARDS (CSB/COB/CDAB/CMB/CPMB). NOTHING in either framework
# supplies a correspondence between them. The mapping below is an ASSUMPTION WE
# ARE MAKING and is preregistered as such (PREREG v2 section 3B), exactly like the
# sequencing claim in PREREG section 3. Where no board is defensible the turn type
# maps to None and is EXCLUDED from the labelled corpus rather than forced.
SDG_TURN_TYPE_TO_BOARD = {
    # MAPPED
    "REFUSE":       "B1",   # the single REFUSE template is an explicit decline that
                            # cites a firm standing principle ("it would break the
                            # admissibility of the dialog") -- B1's core behaviour.
    "PLAN":         "B5",   # the single PLAN template is an explicit prerequisite-
                            # ordering move ("strengthen the prerequisite that's
                            # currently weakest") -- B5's ordering-gate clause. WEAK:
                            # it carries NO capacity/budget/throttle/silence content,
                            # which is the clause B5's rubric LEADS with. Flagged.
    # PRESCRIBED "none dominates" -- not a forced fit: a turn constructed to exhibit
    # none of the five board behaviours is exactly what B0 names.
    "ACK":          "B0",
    "MIRROR":       "B0",
    "CLARIFY":      "B0",
    "EMPATHIZE":    "B0",
    "ANSWER":       "B0",
    "REFUSE_CLAIM": "B0",   # WEAK -- flagged on the SAME FOOTING as PLAN->B5.
    # EXCLUDED (mapped to None): no defensible board, or never an assistant turn.
    "CLOSE":        None,   # terminator; also role-ambiguous (50/50 coin flip)
    "OPEN":         None,   # user-side
    "REPAIR":       None,   # user-side
}
# ---- WEAK MAPPINGS, MACHINE-READABLE ----
# A weak mapping is one where a reader choosing a DIFFERENT board is making a
# defensible judgement, yet is scored WRONG against an author judgement that has no
# greater standing than the reading being tested. Both are disclosed; neither is
# quietly presented as settled.
SDG_WEAK_MAPPINGS = {
    "PLAN->B5": "the single PLAN template is an explicit prerequisite-ordering move "
                "('strengthen the prerequisite that's currently weakest'), which is "
                "B5's ordering-gate clause -- but it carries NO capacity / budget / "
                "throttle / silence content, which is the clause B5's rubric LEADS "
                "with.",
    "REFUSE_CLAIM->B0": "the single REFUSE_CLAIM template ('I don't think the "
                "structure you're proposing fits. The closer reading I'd stand "
                "behind is <cas>') is an EXPLICIT DECLINE plus a COMPETING READING. "
                "It plausibly reads as B1 (the rubric's 'decides whether to answer "
                "or to decline ... an explicit refusal') or as B3 (two readings held "
                "side by side); PREREG 3B.2 already concedes it 'comes nearest' to "
                "B3. Any reader choosing B1 or B3 here is scored WRONG against an "
                "author judgement with the same standing as the one under test. B0 "
                "is a POSITIVE PRESCRIPTION readers are scored against, not a "
                "neutral residue -- so it is flagged, not presented as 'the honest "
                "read'.",
}
# ---- REALISED vs NOMINAL MAPPING ----
# The 11-row table above OVERSTATES what actually governs. No forced path in
# SDG_FORCED_PATHS contains ACK or EMPATHIZE, so realised B0 mass comes only from
# MIRROR / ANSWER / CLARIFY / REFUSE_CLAIM and the EFFECTIVE mapping is SIX turn
# types, not eleven. Worse, every ACK and EMPATHIZE template is under the 30-char
# floor gen_conversation_sdg applies ("Got it." = 7, "Yeah. That's heavy." = 19,
# "That sounds like a lot." = 23), so a path using them would be SILENTLY TRUNCATED
# at that turn. sdg_validated_paths() now refuses such a path outright rather than
# leaving the trap latent for whoever next edits the path bank.
SDG_SHORT_TEMPLATE_TURN_TYPES = ("ACK", "EMPATHIZE")
SDG_MIN_TURN_CHARS = 30
# STRUCTURAL CEILING, preregistered: three of the five boards CANNOT BE CONSTRUCTED
# from this generator at all. No turn type renders a rate/cycle/rigidity claim (B2),
# a two-input comparison with cancellation of the shared part (B3), or a
# resemblance-of-shape memory retrieval (B4). The SDG arm therefore calibrates the
# instrument on B1 / B5 / B0 ONLY and is SILENT about B2 / B3 / B4 whatever it finds.
SDG_UNREACHABLE_BOARDS = ("B2", "B3", "B4")
# Structurally unrealisable transition: PLAN is admissible only after MIRROR or
# ANSWER (both B0), so a B1 turn can never be immediately followed by a B5 turn.
SDG_UNREALISABLE_TRANSITIONS = ("B1->B5",)

# ---- FORCED PATHS ----
# Constructed, not sampled. Every path is validated at load time against
# dialog_grammar.is_admissible (an inadmissible path is not a valid conversation),
# and every path is constructed so that CONSECUTIVE LABELLED TURNS CARRY DIFFERENT
# PRESCRIBED BOARDS -- persistence is 0.000 BY CONSTRUCTION, which is the whole
# point: the api-corpus smoke was REJECTED because natural conversation is sticky
# (persistence 0.5238 vs Markov 0.5079, i.e. almost nothing left to predict).
SDG_FORCED_PATHS = (
    ("P1", ("OPEN", "REFUSE", "OPEN", "MIRROR", "PLAN", "OPEN", "REFUSE",
            "OPEN", "ANSWER", "PLAN", "OPEN", "REFUSE", "CLOSE")),
    ("P2", ("OPEN", "ANSWER", "PLAN", "OPEN", "REFUSE", "REPAIR", "MIRROR",
            "PLAN", "OPEN", "REFUSE", "CLOSE")),
    ("P3", ("OPEN", "REFUSE", "OPEN", "MIRROR", "PLAN", "OPEN", "ANSWER",
            "OPEN", "REFUSE", "OPEN", "MIRROR", "PLAN", "CLOSE")),
    ("P4", ("OPEN", "REFUSE_CLAIM", "OPEN", "REFUSE", "OPEN", "ANSWER",
            "PLAN", "OPEN", "REFUSE", "CLOSE")),
    ("P5", ("OPEN", "REFUSE", "REPAIR", "MIRROR", "PLAN", "OPEN", "REFUSE",
            "OPEN", "ANSWER", "PLAN", "OPEN", "REFUSE", "CLOSE")),
    ("P6", ("OPEN", "REFUSE", "OPEN", "CLARIFY", "OPEN", "REFUSE", "OPEN",
            "MIRROR", "PLAN", "OPEN", "REFUSE", "CLOSE")),
)
SDG_MAX_REPLICATES = 6           # 6 paths x 6 replicates = 36 conversations, the
                                 # same corpus size as the api arm

# ---- RUBRIC-ADHERENCE GATES (added v2 as "calibration"; RENAMED at v2.1) ----
# RENAMED because the answer key is CIRCULAR with the rubric (see
# SDG_MAPPING_CIRCULARITY_DISCLOSURE): this is a RUBRIC-ADHERENCE / READER-
# RELIABILITY check, NOT calibration, and "CALIBRATED" / "known ground truth" are
# not available verdicts anywhere in this arm. The threshold VALUES are unchanged;
# only the name and the licensed interpretation changed.
RA_ACC_MIN = 0.60                # absolute floor for "readers apply the rubric the way
                                 # the answer key's author applied it"
RA_MARGIN_OVER_CHANCE = 0.10     # over always-predict-the-modal-PRESCRIBED-class
RA_MARGIN_OVER_SURFACE = 0.05    # over max(char, word, length) on the SAME task.
                                 # MEASURED AT 1.0000 ON THIS CORPUS, so this gate is
                                 # UNSATISFIABLE for ANY accuracy here -- which is why
                                 # sdg_precheck() takes the kill at $0 and blocks the
                                 # spend instead of confirming arithmetic with money.

# =====================================================================
# READER RUBRICS (zero CAS/TKS/board vocabulary; no Noetic renamed to a function)
# =====================================================================
RUBRIC_BOARD = """You will read short excerpts of assistant answers, one at a time.
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

# MATCHED-TAXONOMY ARM (CONTROL 8). An independently constructed 6-class discourse
# taxonomy of EQUAL granularity (5 named classes + a "none dominates" class), built
# from ordinary discourse/speech-act categories with no CCB content whatsoever. Same
# panel, same corpus, same prediction test. Without this arm a GATE 1 pass licenses
# only "an LLM ensemble reading beats char-ngrams", which any competent 6-class
# taxonomy would also achieve.
RUBRIC_ALT = """You will read short excerpts of assistant answers, one at a time.
For EACH excerpt, choose the ONE label below that best describes what the answer is
mainly doing. These are descriptions of behaviour, nothing more.

D1 - Tells the reader what to DO.
   Instructions, steps, a plan, a recommendation to act. Imperatives, ordered actions,
   "start with", "next", "then". The centre of gravity is a course of action, not an
   explanation of how something works.

D2 - EXPLAINS how or why something is the way it is.
   Describes a mechanism, defines terms, gives background, walks through causes. The
   centre of gravity is understanding, not action and not persuasion.

D3 - ARGUES for a position.
   Advances a claim and supports it, or weighs claims against each other and comes down
   somewhere. Concessions, rebuttals, "the stronger case is". The centre of gravity is
   persuading the reader that something is so.

D4 - Attends to the reader's FEELINGS and situation.
   Acknowledges difficulty, validates, reassures, expresses care or regret, softens.
   The centre of gravity is the relationship and the reader's state, not information.

D5 - Talks about ITSELF - its own knowledge, limits, or process.
   Flags uncertainty, states what it cannot know or do, describes how it is approaching
   the question, corrects or revises its own earlier statement. The centre of gravity is
   the speaker's own standing, not the subject matter.

D0 - None of the five above is clearly doing the dominant work in this excerpt.

HOW TO CHOOSE:

1. PICK THE DOMINANT ONE. Real answers mix. Choose the single label doing the most work.
2. D1 vs D2. If the reader is being told to act, it is D1. If the reader is being told
   how something works, it is D2, even when the topic is a procedure.
3. D2 vs D3. Explaining a mechanism neutrally is D2. Taking a side and defending it is D3.
4. D5 IS ABOUT THE SPEAKER. A passing hedge ("roughly", "about") is not enough. D5 needs
   the answer's main work to be about its own knowledge, limits, or process.
5. If none dominates, choose D0. D0 is a legitimate answer, not a failure - choosing it
   honestly is better than forcing a fit."""

TAXONOMY = {
    "board": {"rubric": RUBRIC_BOARD, "codes": BOARDS, "re": r"\b(B[0-5])\b",
              "none": "B0", "menu": "B0|B1|B2|B3|B4|B5"},
    "alt":   {"rubric": RUBRIC_ALT,   "codes": ALTCODES, "re": r"\b(D[0-5])\b",
              "none": "D0", "menu": "D0|D1|D2|D3|D4|D5"},
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
    """Return (answer_text, reasoning_text) separately.

    deepseek-v4-pro and glm-4.6 routinely return an EMPTY message.content with the
    trace in reasoning_content. Rev 0.3 concatenated the two and scanned the result,
    which lets a chain-of-thought aside ("not B1, so B3") be harvested as a confident
    label. Rev 0.4 keeps them apart: only the ANSWER may yield labels (see parse_labels).
    The reasoning text is still captured, but only to diagnose and to route the batch
    into the repair pass.
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
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    return rows


# =====================================================================
# STAGE 1 -- GENERATE
# =====================================================================
def build_conversation_plan(n_convos, n_turns):
    """Deterministic plan: seed prompt, generator, follow-up draws per conversation.

    Follow-ups are i.i.d. WITH REPLACEMENT (Rev 0.4 fatal fix). A given move may
    appear twice in one conversation or not at all; that is the point. f_t is then
    independent of f_{t+1}, so the sampling scheme cannot manufacture a b_N -> b_{N+1}
    dependence.
    """
    if n_convos > len(PROMPTS):
        # Rev 0.3 silently shrank n_convos to len(PROMPTS)=36, which quietly broke the
        # Gate 0 pair arithmetic. Fail loudly instead: reusing a seed prompt would also
        # put two topically-correlated conversations in different LOCO folds.
        raise SystemExit(f"--n-convos {n_convos} exceeds the {len(PROMPTS)}-prompt seed bank "
                         f"(gen_real_outputs.PROMPTS). Use --n-convos <= {len(PROMPTS)}; the "
                         f"preregistered full run is {len(PROMPTS)} conversations x 7 turns.")
    seeds = random.Random(SEED_PROMPT_SAMPLE).sample(list(PROMPTS), n_convos)
    plan = []
    for cid, seed_prompt in enumerate(seeds):
        rng = random.Random(SEED_FOLLOWUP_BASE + cid)
        fups = [rng.choice(FOLLOWUPS) for _ in range(max(0, n_turns - 1))]
        plan.append({
            "conv_id": cid,
            "seed_prompt": seed_prompt,
            "gen_provider": ORDER[cid % len(ORDER)],
            "gen_model": MODELS[ORDER[cid % len(ORDER)]],
            "followups": fups,
        })
    return plan


def gen_conversation(spec, n_turns, max_tokens, min_turns):
    """Run one conversation. Rev 0.4: a short/empty turn TRUNCATES the conversation at
    the last good turn instead of discarding every good turn before it (n is the binding
    constraint, and discarding also skews the generator mix)."""
    prov, model = spec["gen_provider"], spec["gen_model"]
    client = _client(prov, model)
    msgs = [{"role": "user", "content": spec["seed_prompt"]}]
    turns, truncated_at = [], None
    for t in range(n_turns):
        if t == 0:
            fid, user_text = "SEED", spec["seed_prompt"]
        else:
            fid, user_text = spec["followups"][t - 1]
            msgs.append({"role": "user", "content": user_text})
        try:
            r = call_with_retry(client, prov, model=model, max_tokens=max_tokens,
                                temperature=0.7, messages=msgs)
            out = _split_text(r)[0].strip()
        except Exception as e:
            truncated_at = f"turn {t}: call failed ({str(e)[:90]})"
            break
        if len(out) < 30:                       # same floor as gen_real_outputs.py
            truncated_at = f"turn {t}: short/empty ({len(out)} chars)"
            break
        msgs.append({"role": "assistant", "content": out})
        turns.append({"turn_idx": t, "followup_id": fid, "user": user_text, "assistant": out})
    if len(turns) < min_turns:
        raise RuntimeError(f"conv {spec['conv_id']}: only {len(turns)} usable turns "
                           f"({truncated_at})")
    return {"conv_id": spec["conv_id"], "seed_prompt": spec["seed_prompt"],
            "gen_provider": prov, "gen_model": model,
            "truncated_at": truncated_at, "turns": turns}


# ---------------------------------------------------------------------
# SDG forced-transition generator (local, template-rendered, no API)
# ---------------------------------------------------------------------
def sdg_validated_paths():
    """Materialise the forced-path bank as real TurnType members and VALIDATE it.

    Three checks, all fatal:
      1. every (prev, next) pair satisfies dialog_grammar.is_admissible -- the SDG
         itself never checks the path it renders (is_admissible is imported into
         conversation_generator.py and never called), so an illegal path would
         render happily and produce a grammar-violating record;
      2. no two CONSECUTIVE LABELLED turns carry the same prescribed board, i.e.
         persistence is 0 by construction;
      3. real TurnType members are used, never bare strings -- TurnType subclasses
         str, so a string path survives every dict lookup and every == comparison
         and then dies at the .value call inside to_dict()/_stable_id();
      4. (v2.1) no path may use a turn type whose every template is under the
         30-char floor. ACK and EMPATHIZE templates are all shorter than that
         ("Got it." = 7, "Yeah. That's heavy." = 19, "That sounds like a lot." = 23),
         so a path using them would hit gen_conversation_sdg's `len(out) < 30` break
         and be SILENTLY TRUNCATED mid-conversation. That was a latent trap for
         whoever next edits the path bank; it is now a load-time failure.
    """
    sdg = load_sdg()
    tt_enum = sdg.TurnType
    out = []
    for name, seq in SDG_FORCED_PATHS:
        path = [tt_enum[s] for s in seq]
        prev = None
        for step in path:
            if not sdg.is_admissible(prev, step):
                raise SystemExit(f"forced path {name}: INADMISSIBLE transition "
                                 f"{prev} -> {step}. Fix SDG_FORCED_PATHS.")
            if step.value in SDG_SHORT_TEMPLATE_TURN_TYPES:
                raise SystemExit(
                    f"forced path {name}: turn type {step.value} has NO template "
                    f"reaching the {SDG_MIN_TURN_CHARS}-char floor, so the "
                    f"conversation would be silently TRUNCATED there. Remove it "
                    f"from SDG_FORCED_PATHS or lower SDG_MIN_TURN_CHARS knowingly.")
            prev = step
        boards = [SDG_TURN_TYPE_TO_BOARD[t.value] for t in path
                  if SDG_TURN_TYPE_TO_BOARD[t.value]]
        for a, b in zip(boards, boards[1:]):
            if a == b:
                raise SystemExit(f"forced path {name}: consecutive prescribed board "
                                 f"{a}->{b}. Persistence must be 0 by construction.")
        if len(boards) < 2:
            raise SystemExit(f"forced path {name}: fewer than 2 labelled turns.")
        out.append((name, path))
    return out


def build_sdg_conversation_plan(n_convos):
    """Deterministic forced-path plan. There is no sampling of the dialog path.

    gen_provider is the literal sentinel 'sdg' so provenance is never lost when
    these records sit next to api records (the SDG's own output carries no marker
    of being synthetic). Because 'sdg' is outside ORDER, no reader can ever equal
    it and GATE 4 would be VACUOUSLY true while FOUR readers labelled every turn --
    which would silently break fleiss_kappa's fixed row width and build_arm's
    hardcoded combinations(range(3), 2). excluded_reader therefore carries a
    deterministic STRUCTURE-PRESERVING holdout so the panel stays exactly 3 wide.
    """
    paths = sdg_validated_paths()
    cap = len(paths) * SDG_MAX_REPLICATES
    if n_convos > cap:
        raise SystemExit(f"--n-convos {n_convos} exceeds the SDG bank capacity "
                         f"({len(paths)} forced paths x {SDG_MAX_REPLICATES} replicates "
                         f"= {cap}).")
    plan = []
    for cid in range(n_convos):
        name, path = paths[cid % len(paths)]
        plan.append({
            "conv_id": cid,
            "path_name": name,
            "path": path,
            "seed_prompt": f"[SDG forced path {name}: {'>'.join(t.value for t in path)}]",
            "render_seed": SEED_SDG_BASE + cid,
            "gen_provider": "sdg",
            "gen_model": SDG_MODEL_ID,
            "excluded_reader": ORDER[cid % len(ORDER)],
        })
    return plan


def gen_conversation_sdg(spec, min_turns):
    """Render ONE forced-path conversation. NO API call, NO model, NO network.

    Drives cas-synthetic's _render_turn directly (option B of the three documented
    drive strategies) rather than generate_conversation, because generate_conversation
    hardcodes `path = generate_dialog_path(seed, target_turns)` and exposes no path=
    parameter. Turn types whose board mapping is None are rendered for context but
    NEVER labelled.

    NO CAS EVOLUTION HAPPENS HERE. current_cas is threaded into _render_turn because
    that is its signature, but _render_turn NEVER READS IT: on every CAS-load-bearing
    turn it re-samples an INDEPENDENT (bucket, _, cas, transition) row from
    _USER_TEMPLATES. cas-synthetic's own module docstring says so ("There is NO
    coherence constraint across CAS states within a single record"). The
    cas_state_after sequence of these records is therefore NOISE and must never be
    described as evolution, refinement, or a response to a REPAIR turn. It is
    irrelevant to the prescribed boards, which come from the turn TYPE alone.
    """
    sdg = load_sdg()
    rng = random.Random(spec["render_seed"])
    turns, truncated_at = [], None
    pending_user_text, pending_user_type = "", None
    current_cas = ""
    for tt in spec["path"]:
        r = sdg._render_turn(tt, rng, current_cas=current_cas, target_buckets=None)
        if r["cas_state_after"]:
            current_cas = r["cas_state_after"]
        board = SDG_TURN_TYPE_TO_BOARD.get(tt.value)
        if r["role"] == "user" or board is None:
            if r["role"] == "user":
                pending_user_text, pending_user_type = r["text"], tt.value
            continue
        out = r["text"]
        if len(out) < SDG_MIN_TURN_CHARS:      # same floor as the api arm. Reachable
                                               # only if the path bank is edited to use
                                               # a short-template turn type, which
                                               # sdg_validated_paths() now refuses.
            truncated_at = f"turn {len(turns)}: short/empty ({len(out)} chars)"
            break
        turns.append({
            "turn_idx": len(turns),
            "followup_id": ("SEED" if not turns else
                            (f"U-{pending_user_type}" if pending_user_type else "U-NONE")),
            "user": pending_user_text,
            "assistant": out,
            "gt_board": board,
            "gt_turn_type": tt.value,
        })
        pending_user_text, pending_user_type = "", None
    if len(turns) < min_turns:
        raise RuntimeError(f"conv {spec['conv_id']}: only {len(turns)} usable turns "
                           f"({truncated_at})")
    return {"conv_id": spec["conv_id"], "seed_prompt": spec["seed_prompt"],
            "gen_provider": "sdg", "gen_model": SDG_MODEL_ID,
            "excluded_reader": spec["excluded_reader"],
            "truncated_at": truncated_at, "turns": turns,
            "sdg": {"path_name": spec["path_name"],
                    "forced_path": [t.value for t in spec["path"]],
                    "render_seed": spec["render_seed"],
                    "prescribed_boards": [t["gt_board"] for t in turns],
                    "source": SDG_PATH,
                    "TEMPLATE_DISCLOSURE": SDG_TEMPLATE_DISCLOSURE}}


def stage_generate_sdg(A):
    plan = build_sdg_conversation_plan(A.n_convos)
    existing = {r["conv_id"] for r in _jsonl_read(A.conv_file)}
    todo = [s for s in plan if s["conv_id"] not in existing]
    print("*** SDG ARM: TEMPLATE-RENDERED CORPUS, NO MODEL CALL ***")
    print(f"    {SDG_TEMPLATE_DISCLOSURE}\n", flush=True)
    print(f"forced-path corpus: {len(todo)} conversations over "
          f"{len(SDG_FORCED_PATHS)} constructed paths ({len(existing)} already "
          f"checkpointed). --n-turns is IGNORED here: path length is prescribed.",
          flush=True)
    if not todo:
        print("nothing to do -- all conversations already in the checkpoint file.")
        return
    n_ok = 0
    for s in todo:                       # serial: local, no rate limit, no pool needed
        try:
            conv = gen_conversation_sdg(s, A.min_turns)
        except Exception as e:
            print(f"  [conv {s['conv_id']}] DROPPED: {str(e)[:140]}", flush=True)
            continue
        _jsonl_append(A.conv_file, conv)
        n_ok += 1
        print(f"  [conv {conv['conv_id']}] {conv['sdg']['path_name']}: "
              f"{conv['sdg']['prescribed_boards']} "
              f"({[len(t['assistant']) for t in conv['turns']]} chars/turn)", flush=True)
    rows = _jsonl_read(A.conv_file)
    all_turns = [t for c in rows for t in c["turns"]]
    pres = Counter(t["gt_board"] for t in all_turns)
    # realised transition matrix + persistence of the CORPUS ITSELF
    trans, same, tot = Counter(), 0, 0
    for c in rows:
        seq = [t["gt_board"] for t in sorted(c["turns"], key=lambda x: x["turn_idx"])]
        for a, b in zip(seq, seq[1:]):
            trans[(a, b)] += 1; tot += 1; same += int(a == b)
    print(f"\n{n_ok} new; file now holds {len(rows)} conversations / {len(all_turns)} "
          f"labelled turns -> {A.conv_file}")
    print(f"  prescribed board mix: {dict(sorted(pres.items()))} "
          f"(B0 share {pres.get('B0', 0) / max(1, len(all_turns)):.4f}; "
          f"Gate 0 cap {G0_B0_SHARE_MAX})")
    print(f"  UNREACHABLE boards (zero prescribed instances, by construction): "
          f"{list(SDG_UNREACHABLE_BOARDS)}")
    print(f"  realised prescribed transition matrix ({tot} pairs): "
          f"{ {f'{a}->{b}': n for (a, b), n in sorted(trans.items())} }")
    print(f"  CORPUS PERSISTENCE RATE (prescribed b_N == b_N+1): "
          f"{(same / tot) if tot else 0.0:.4f}   <- stickiness removed by construction")
    print(f"  structurally unrealisable transitions: {list(SDG_UNREALISABLE_TRANSITIONS)}")
    if rows:
        s = sorted(rows, key=lambda c: c["conv_id"])[0]
        print(f"\nSAMPLE conv {s['conv_id']} path {s['sdg']['forced_path']}")
        for t in s["turns"][:3]:
            print(f"  t{t['turn_idx']} [{t['gt_turn_type']} -> {t['gt_board']}] "
                  f"{t['assistant'][:110]}")
    print("\n>>> RUN `--stage precheck --generator sdg` NEXT. Labelling is BLOCKED "
          "until the corpus passes the $0 surface-determinism precheck.")


# ---------------------------------------------------------------------
# $0 PRECHECK -- take both kills BEFORE any labelling call (added v2.1)
# ---------------------------------------------------------------------
def sdg_precheck(conv_file, out_path=None):
    """Decide the SDG arm's fate for $0: no reader panel, no label call, no network.

    A preregistered study must be able to fail. This arm as originally specified
    could not: the primary-kill gate is (ra_acc - surface_acc) >= 0.05, and the
    surface accuracy on the ground-truth task is 1.0000 on char, on word AND on raw
    character count, so no accuracy whatsoever can satisfy it. The verdict was
    therefore decided before the first labelling call, and running the panel would
    have bought nothing but an arithmetic confirmation at the price of ~256 label
    calls and hours of GLM serialisation.

    This function obtains that kill on the record at zero cost, and reports the
    second, independent kill (mapping circularity) beside it. stage_label refuses to
    spend money while either fires.

    Returns a dict; writes it beside the corpus when out_path is given.
    """
    rows = load_conversations(conv_file)
    turns = [t for c in rows for t in c["turns"] if t.get("gt_board")]
    if len(turns) < 2:
        return {"ran": False, "why": f"{conv_file} carries no prescribed boards."}
    txt = [t["assistant"] for t in turns]
    y = [t["gt_board"] for t in turns]
    grp = [c["conv_id"] for c in rows for t in c["turns"] if t.get("gt_board")]

    # exact-string -> board relation. If it is a function (no string maps to two
    # boards) then string lookup ALONE recovers the answer key.
    by_string = defaultdict(set)
    for s, b in zip(txt, y):
        by_string[s].add(b)
    ambiguous = sum(1 for v in by_string.values() if len(v) > 1)
    bijective = bool(ambiguous == 0)

    # per-class length ranges: disjoint ranges mean ONE FEATURE suffices.
    lens = defaultdict(list)
    for s, b in zip(txt, y):
        lens[b].append(len(s))
    ranges = {b: [min(v), max(v)] for b, v in sorted(lens.items())}
    disjoint = True
    ordered = sorted(ranges.items(), key=lambda kv: kv[1][0])
    for (_b1, r1), (_b2, r2) in zip(ordered, ordered[1:]):
        if r1[1] >= r2[0]:
            disjoint = False

    folds = loco_folds(grp)
    by_kind, strongest, surface_acc = {}, None, None
    if folds and len(set(y)) >= 2:
        for kind in ("char", "word", "length"):
            a, _c = loco_surface(kind, txt, y, grp, folds)
            by_kind[kind] = round(a, 4)
            if surface_acc is None or a > surface_acc:
                strongest, surface_acc = kind, a
    # FAIL CLOSED: an uncomputable control is NOT a pass.
    surface_determined = True if surface_acc is None else bool(
        surface_acc >= SDG_PRECHECK_SURFACE_MAX)

    mix = Counter(y)
    n = sum(mix.values())
    modal = max(mix.values()) / n
    # The gate the arm would have had to clear, evaluated in advance.
    gate_satisfiable = bool(surface_acc is not None
                            and (1.0 - surface_acc) >= RA_MARGIN_OVER_SURFACE)

    rep = {
        "ran": True,
        "WHAT_THIS_IS": "a $0 precheck that decides the SDG arm BEFORE any labelling "
                        "call. No reader panel, no API call, no network. It exists "
                        "because preregistering a foregone kill is not a study.",
        "conv_file": conv_file,
        "n_prescribed_turns": n,
        "prescribed_mix": dict(sorted(mix.items())),
        "n_distinct_assistant_strings": len(by_string),
        "n_strings_mapping_to_more_than_one_board": ambiguous,
        "EXACT_STRING_LOOKUP_IS_A_BIJECTION_ONTO_THE_ANSWER_KEY": bijective,
        "per_class_length_ranges_chars": ranges,
        "length_ranges_are_disjoint_one_feature_suffices": disjoint,
        "surface_on_ground_truth_task_LOCO": {
            "strongest": strongest, "acc": (round(surface_acc, 4)
                                            if surface_acc is not None else None),
            "by_kind": by_kind,
            "note": "LOCO folds grouped by conversation. `length` is RAW CHARACTER "
                    "COUNT -- a one-feature classifier."},
        "modal_prescribed_class_rate": round(modal, 4),
        "bar": SDG_PRECHECK_SURFACE_MAX,
        "KILL_1_SURFACE_DETERMINED_CORPUS": surface_determined,
        "KILL_1_DETAIL": (
            f"surface accuracy on the ground-truth task is "
            f"{('UNCOMPUTABLE' if surface_acc is None else round(surface_acc, 4))} "
            f"against a bar of {SDG_PRECHECK_SURFACE_MAX}. The primary-kill gate "
            f"requires (ra_acc - surface_acc) >= {RA_MARGIN_OVER_SURFACE}; with the "
            f"measured surface accuracy that is SATISFIABLE={gate_satisfiable}. When "
            f"it is not satisfiable the arm's verdict is fixed before any reader "
            f"sees a single excerpt, so labelling would buy nothing. An UNCOMPUTABLE "
            f"control counts as a KILL, never as a pass."),
        "PRIMARY_KILL_GATE_IS_SATISFIABLE_AT_ALL": gate_satisfiable,
        "KILL_2_MAPPING_CIRCULARITY": SDG_MAPPING_CIRCULARITY_KILL,
        "KILL_2_DETAIL": SDG_MAPPING_CIRCULARITY_DISCLOSURE,
        "TEMPLATE_DISCLOSURE": SDG_TEMPLATE_DISCLOSURE,
        "weak_mappings": dict(SDG_WEAK_MAPPINGS),
        "ARM_STATUS": SDG_ARM_STATUS,
        "PRECHECK_VERDICT": (
            "ARM WITHDRAWN -- DO NOT LABEL" if (surface_determined
                                                or SDG_MAPPING_CIRCULARITY_KILL)
            else "precheck clear -- labelling permitted"),
        "HOW_TO_REVIVE": "replace the corpus with text whose SURFACE DOES NOT "
                         "DETERMINE THE LABEL, and derive the answer key from "
                         "something other than reading the same strings through the "
                         "same rubric. Relaxing a bar does not revive the arm; it "
                         "only hides the defect.",
    }
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
    return rep


def stage_precheck(A):
    if A.generator != "sdg":
        raise SystemExit("--stage precheck applies to the sdg arm only. The api arm "
                         "has no answer key to be surface-determined against.")
    rep = sdg_precheck(A.conv_file, A.precheck_report)
    if not rep.get("ran"):
        raise SystemExit(f"precheck could not run: {rep.get('why')}")
    print("\n=== SDG ARM $0 PRECHECK (no labelling call, no network) ===")
    print(f"  corpus                        : {rep['n_prescribed_turns']} prescribed "
          f"turns, mix {rep['prescribed_mix']}")
    print(f"  distinct assistant strings    : {rep['n_distinct_assistant_strings']} "
          f"({rep['n_strings_mapping_to_more_than_one_board']} ambiguous)")
    print(f"  exact-string lookup bijective : "
          f"{rep['EXACT_STRING_LOOKUP_IS_A_BIJECTION_ONTO_THE_ANSWER_KEY']}")
    print(f"  per-class length ranges       : {rep['per_class_length_ranges_chars']} "
          f"(disjoint={rep['length_ranges_are_disjoint_one_feature_suffices']})")
    print(f"  surface on the GT task (LOCO) : "
          f"{rep['surface_on_ground_truth_task_LOCO']['by_kind']} "
          f"-> {rep['surface_on_ground_truth_task_LOCO']['acc']} "
          f"[{rep['surface_on_ground_truth_task_LOCO']['strongest']}]  bar {rep['bar']}")
    print(f"  primary-kill gate satisfiable : "
          f"{rep['PRIMARY_KILL_GATE_IS_SATISFIABLE_AT_ALL']}")
    print(f"\n  KILL 1 surface-determined corpus : {rep['KILL_1_SURFACE_DETERMINED_CORPUS']}")
    print(f"  KILL 2 mapping circularity       : {rep['KILL_2_MAPPING_CIRCULARITY']}")
    print(f"\n  PRECHECK VERDICT: {rep['PRECHECK_VERDICT']}")
    if rep["PRECHECK_VERDICT"].startswith("ARM WITHDRAWN"):
        print("  *** Labelling is BLOCKED. The kill is now on the record at $0: no "
              "reader panel,\n      no ~256 label calls, no GLM serialisation. "
              "--allow-surface-determined-corpus\n      overrides this, is "
              "PREREG-DEVIATING, and must be logged in the amendment log. ***")
    if A.precheck_report:
        print(f"  wrote {A.precheck_report}")
    return rep


def stage_generate(A):
    if A.generator == "sdg":
        return stage_generate_sdg(A)
    plan = build_conversation_plan(A.n_convos, A.n_turns)
    existing = {r["conv_id"] for r in _jsonl_read(A.conv_file)}
    todo = [s for s in plan if s["conv_id"] not in existing]
    print(f"generating {len(todo)} conversations x up to {A.n_turns} assistant turns "
          f"(generator rotated over {ORDER}; {len(existing)} already checkpointed)", flush=True)
    if not todo:
        print("nothing to do -- all conversations already in the checkpoint file.")
        return
    # Sized to the sum of the per-provider semaphores so a worker blocked on the GLM
    # Semaphore(1) never starves gemini/deepseek/qwen. Raising it further does NOT
    # raise GLM concurrency (the semaphore caps it) and does not re-trigger 429 storms.
    pool = A.workers or sum(PROVIDER_CONCURRENCY.values())
    n_ok = 0
    with ThreadPoolExecutor(max_workers=pool) as ex:
        futs = {ex.submit(gen_conversation, s, A.n_turns, A.gen_max_tokens, A.min_turns):
                s["conv_id"] for s in todo}
        for fut in as_completed(futs):
            cid = futs[fut]
            try:
                conv = fut.result()
            except Exception as e:
                print(f"  [conv {cid}] DROPPED: {str(e)[:140]}", flush=True)
                continue
            _jsonl_append(A.conv_file, conv)       # checkpoint as it lands
            n_ok += 1
            note = f" TRUNCATED@{conv['truncated_at']}" if conv["truncated_at"] else ""
            print(f"  [conv {cid}] {conv['gen_provider']}: "
                  f"{[len(t['assistant']) for t in conv['turns']]} chars/turn{note}", flush=True)
    rows = _jsonl_read(A.conv_file)
    n_turns_total = sum(len(c["turns"]) for c in rows)
    print(f"\n{n_ok} new; file now holds {len(rows)} conversations / {n_turns_total} "
          f"assistant turns -> {A.conv_file}")
    if rows:
        s = sorted(rows, key=lambda c: c["conv_id"])[0]
        print(f"\nSAMPLE conv {s['conv_id']} ({s['gen_model']})")
        print(f"  seed: {s['seed_prompt'][:90]}")
        print(f"  t0  : {s['turns'][0]['assistant'][:220]}")


# =====================================================================
# STAGE 2 -- LABEL
# =====================================================================
def load_conversations(path):
    rows = _jsonl_read(path)
    seen, out = set(), []
    for c in sorted(rows, key=lambda r: r["conv_id"]):     # de-dup on restart-append
        if c["conv_id"] in seen:
            continue
        seen.add(c["conv_id"])
        out.append(c)
    return out


def _excluded_reader(meta):
    """Which panel model is held out for this turn.

    api arm: the model that GENERATED the turn -- GATE 4 / requirement 4 separation.
    sdg arm: gen_provider is the sentinel 'sdg', which is OUTSIDE ORDER, so nothing
    would be held out and FOUR readers would label every turn. That silently breaks
    two hardcoded 3-reader assumptions (build_arm's combinations(range(3), 2), which
    would score only the first 3 of 4, and fleiss_kappa's fixed row width, which
    would change what G0_FLEISS_MIN=0.35 means) and raises labelling cost 33%. The
    sdg arm therefore carries a deterministic STRUCTURE-PRESERVING holdout. It is
    NOT a separation control there -- GATE 4 is VACUOUSLY true in the sdg arm and
    the report says so in those words.
    """
    return meta.get("excluded_reader") or meta.get("gen_provider")


def flatten_turns(convs, truncate):
    """Flat turn list with a stable integer uid used ONLY on the analysis side.

    The uid is never shown to a reader (Rev 0.4 fix): uid = 6*conv_position + turn_idx
    deterministically encodes conversation and turn position, so printing it in the
    prompt leaked position. read_batch emits per-batch ALIAS ids instead.

    v2: gt_board / gt_turn_type are carried through for the sdg arm (None in the api
    arm, which has no answer key at all -- its labels come only from readers).
    """
    turns, uid = [], 0
    for c in convs:
        for t in c["turns"]:
            turns.append({
                "uid": uid, "conv_id": c["conv_id"], "turn_idx": t["turn_idx"],
                "followup_id": t["followup_id"], "gen_provider": c["gen_provider"],
                "excluded_reader": _excluded_reader(c),
                "gt_board": t.get("gt_board"), "gt_turn_type": t.get("gt_turn_type"),
                "text": t["assistant"][:truncate],
            })
            uid += 1
    return turns


def make_batches(turn_list, batch_size, seed):
    """Shuffle then deterministically repair, so no batch holds two turns from the
    same conversation. A reader that saw turn N and N+1 together could smooth its own
    labels and manufacture the dependence under test."""
    items = list(turn_list)
    random.Random(seed).shuffle(items)
    batches = [items[k:k + batch_size] for k in range(0, len(items), batch_size)]
    swaps = 0
    for bi, b in enumerate(batches):
        seen = set()
        for pos, t in enumerate(b):
            if t["conv_id"] not in seen:
                seen.add(t["conv_id"])
                continue
            moved = False
            for bj in range(len(batches)):                       # deterministic scan
                if bj == bi:
                    continue
                other_convs = {x["conv_id"] for x in batches[bj]}
                if t["conv_id"] in other_convs:
                    continue
                for opos, o in enumerate(batches[bj]):
                    if o["conv_id"] in seen or o["conv_id"] == t["conv_id"]:
                        continue
                    batches[bi][pos], batches[bj][opos] = o, t
                    seen.add(o["conv_id"]); swaps += 1; moved = True
                    break
                if moved:
                    break
            if not moved:
                seen.add(t["conv_id"])                            # unfixable; HARD-FAILED below
    collisions = sum(len(b) - len({x["conv_id"] for x in b}) for b in batches)
    return batches, swaps, collisions


def parse_labels(answer_text, alias_to_uid, code_re):
    """STRICT parse (Rev 0.4). Returns (mapping, status).

    Requirements, all mandatory:
      * a JSON array must be parseable out of the ANSWER text (never the trace);
      * every id must be an alias actually shown in THIS batch -- a fabricated id can
        no longer overwrite a genuine label from another batch;
      * every alias in the batch must appear exactly once.
    Anything less returns an empty mapping and a status the caller routes to repair.
    """
    m = re.search(r"\[.*\]", answer_text, re.S)
    if not m:
        return {}, "no_json_array"
    raw = m.group(0)
    rows = None
    try:
        rows = json.loads(raw)
    except Exception:
        # tolerate trailing commas / stray prose inside the array, but still require
        # object-shaped records -- never a bare code scraped from prose.
        rows = []
        for block in re.findall(r"\{[^{}]*\}", raw, re.S):
            idm = re.search(r'"id"\s*:\s*(\d+)', block)
            if not idm:
                continue
            lm = re.search(code_re, block[idm.end():])
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
        lm = re.search(code_re, str(row.get("label", "")))
        if not lm or aid not in alias_to_uid:      # hallucinated id -> dropped
            continue
        out.setdefault(alias_to_uid[aid], lm.group(1))
    if len(out) != len(alias_to_uid):
        return {}, f"incomplete_{len(out)}_of_{len(alias_to_uid)}"
    return out, "ok"


def read_batch(provider, model, batch, alias_seed, taxonomy, allow_reasoning_only):
    """Return a dict describing ONE labelling call. One turn per excerpt, no context."""
    tx = TAXONOMY[taxonomy]
    aliases = random.Random(alias_seed).sample(range(1000, 10000), len(batch))
    alias_to_uid = {a: t["uid"] for a, t in zip(aliases, batch)}
    client = _client(provider, model)
    blocks = [f'--- EXCERPT {a} ---\n{t["text"]}' for a, t in zip(aliases, batch)]
    prompt = (tx["rubric"] + "\n\nExcerpts to label:\n" + "\n\n".join(blocks) +
              '\n\nReturn ONLY a JSON array as your FINAL ANSWER: '
              f'[{{"id": <number>, "label": "<{tx["menu"]}>"}}]. '
              "Every excerpt id above must appear exactly once. Use only the labels above. "
              "Do not put the array only in your reasoning - it must be in the answer.")
    r = call_with_retry(client, provider, model=model, max_tokens=MAXTOK_LABEL,
                        temperature=0.0, messages=[{"role": "user", "content": prompt}])
    ans, rea = _split_text(r)
    finish = r.choices[0].finish_reason
    if finish != "stop":
        return {"provider": provider, "labels": {}, "status": f"finish_{finish}",
                "n_ans": len(ans), "n_rea": len(rea), "uids": [t["uid"] for t in batch]}
    if not ans.strip():
        if not allow_reasoning_only:
            return {"provider": provider, "labels": {}, "status": "reasoning_only_refused",
                    "n_ans": 0, "n_rea": len(rea), "uids": [t["uid"] for t in batch]}
        ans = rea
    mapping, status = parse_labels(ans, alias_to_uid, tx["re"])
    return {"provider": provider, "labels": {str(k): v for k, v in mapping.items()},
            "status": status, "n_ans": len(ans), "n_rea": len(rea),
            "uids": [t["uid"] for t in batch]}


def _batch_key(reader, taxonomy, uids):
    return f"{taxonomy}|{reader}|" + hashlib.sha256(
        ",".join(str(u) for u in sorted(uids)).encode()).hexdigest()[:16]


def _run_jobs(jobs, pool, ckpt_path, taxonomy, allow_reasoning_only, done_keys, label):
    """Execute labelling jobs, checkpointing every completed call. Returns stats."""
    todo = [j for j in jobs if j["key"] not in done_keys]
    print(f"  {label}: {len(todo)} calls to make ({len(jobs) - len(todo)} already "
          f"checkpointed)", flush=True)
    stats, t0 = Counter(), time.time()
    if not todo:
        return stats
    with ThreadPoolExecutor(max_workers=pool) as ex:
        futs = {ex.submit(read_batch, j["reader"], MODELS[j["reader"]], j["batch"],
                          j["alias_seed"], taxonomy, allow_reasoning_only): j for j in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            j = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                print(f"    [{j['reader']}] call ERROR {str(e)[:110]}", flush=True)
                stats["call_error"] += 1
                continue
            res["key"] = j["key"]
            res["reader"] = j["reader"]
            res["taxonomy"] = taxonomy
            _jsonl_append(ckpt_path, res)          # checkpoint as it lands
            done_keys.add(j["key"])
            stats[res["status"]] += 1
            if n % 5 == 0 or res["status"] != "ok":
                print(f"    {n}/{len(todo)} ({time.time()-t0:.0f}s) "
                      f"{j['reader']}: {res['status']} ({len(res['labels'])} labels)", flush=True)
    return stats


def stage_label(A):
    tax = A.taxonomy
    # ---- v2.1: THE SPEND GATE. Refuse to buy a foregone conclusion. -------
    # The SDG arm's primary-kill gate is unsatisfiable on a surface-determined
    # corpus, so labelling it would confirm arithmetic with money. Both kills are
    # obtainable at $0; take them here before the first call.
    if A.generator == "sdg":
        pre = sdg_precheck(A.conv_file, getattr(A, "precheck_report", None))
        if pre.get("ran") and pre["PRECHECK_VERDICT"].startswith("ARM WITHDRAWN"):
            msg = (
                "\nABORT -- SDG ARM WITHDRAWN, NO LABELLING CALL MADE.\n"
                f"  KILL 1 surface-determined corpus : "
                f"{pre['KILL_1_SURFACE_DETERMINED_CORPUS']} "
                f"(surface {pre['surface_on_ground_truth_task_LOCO']['acc']} "
                f"[{pre['surface_on_ground_truth_task_LOCO']['strongest']}] "
                f"vs bar {pre['bar']}; primary-kill gate satisfiable at all: "
                f"{pre['PRIMARY_KILL_GATE_IS_SATISFIABLE_AT_ALL']})\n"
                f"  KILL 2 mapping circularity       : "
                f"{pre['KILL_2_MAPPING_CIRCULARITY']}\n"
                f"  {pre['HOW_TO_REVIVE']}\n"
                "  --allow-surface-determined-corpus proceeds anyway; that is "
                "PREREG-DEVIATING and must be logged in the amendment log.")
            if not A.allow_surface_determined_corpus:
                raise SystemExit(msg)
            print(msg)
            print("\n*** PROCEEDING UNDER --allow-surface-determined-corpus. The "
                  "resulting numbers are NOT LICENSED as calibration and the report "
                  "will say so. ***\n", flush=True)
    convs = load_conversations(A.conv_file)
    turns = flatten_turns(convs, A.truncate)
    by_uid = {t["uid"]: t for t in turns}
    ckpt = A.label_ckpt
    print(f"[{tax}] labelling {len(turns)} turns from {len(convs)} conversations; "
          f"3 blind readers each (never the turn's own generator)", flush=True)

    jobs, batch_meta = [], []
    for ri, reader in enumerate(ORDER):
        # GATE 4 / requirement 4: a model never labels a turn it generated.
        # (sdg arm: a structure-preserving holdout, not a separation control.)
        mine = [t for t in turns if _excluded_reader(t) != reader]
        batches, swaps, collisions = make_batches(mine, A.batch_size, SEED_BATCH_BASE + ri)
        batch_meta.append({"reader": reader, "n_turns": len(mine), "n_batches": len(batches),
                           "repair_swaps": swaps, "residual_same_conv_collisions": collisions})
        if collisions:
            # Rev 0.4: HARD FAIL. A residual collision means a reader would see two turns
            # from one conversation in a single prompt -- exactly the contamination the
            # prereg forbids, and exactly the route by which a reader could smooth its own
            # labels and manufacture the dependence under test.
            raise SystemExit(f"ABORT: reader {reader} has {collisions} residual same-conversation "
                             f"batch collisions. Lower --batch-size or raise --n-convos.")
        for bi, b in enumerate(batches):
            jobs.append({"reader": reader, "batch": b,
                         "alias_seed": SEED_ALIAS_BASE + ri * 10000 + bi,
                         "key": _batch_key(reader, tax, [t["uid"] for t in b])})

    done = {r["key"] for r in _jsonl_read(ckpt) if r.get("taxonomy") == tax and r.get("key")}
    pool = A.workers or sum(PROVIDER_CONCURRENCY.values())
    print(f"{len(jobs)} labelling calls (batch={A.batch_size}); repair swaps "
          f"{[(m['reader'], m['repair_swaps']) for m in batch_meta]}", flush=True)
    stats = _run_jobs(jobs, pool, ckpt, tax, A.allow_reasoning_only, done, "main pass")

    # ---- REPAIR PASS ----------------------------------------------------
    # Coverage on this panel is lost to parse/drop, not to call failure, so re-asking
    # only the missing uids in small batches is cheap and is what makes the Gate 0
    # coverage floors reachable at all (Rev 0.3 was an auto-VACUOUS at measured
    # coverage 0.556-0.694).
    for rnd in range(A.repair_rounds):
        marks = collect_marks(ckpt, tax, by_uid)
        missing = []
        for ri, reader in enumerate(ORDER):
            want = {t["uid"] for t in turns if _excluded_reader(t) != reader}
            have = set(marks.get(reader, {}))
            gap = sorted(want - have)
            if gap:
                missing.append((ri, reader, gap))
        if not missing:
            print(f"  repair round {rnd+1}: nothing missing.", flush=True)
            break
        print(f"  repair round {rnd+1}: " +
              ", ".join(f"{r}:{len(g)}" for _, r, g in missing), flush=True)
        rjobs = []
        for ri, reader, gap in missing:
            batches, swaps, collisions = make_batches(
                [by_uid[u] for u in gap], A.repair_batch_size,
                SEED_BATCH_BASE + ri + 100 * (rnd + 1))
            if collisions:
                raise SystemExit(f"ABORT: repair batches for {reader} have {collisions} "
                                 f"residual same-conversation collisions.")
            for bi, b in enumerate(batches):
                rjobs.append({"reader": reader, "batch": b,
                              "alias_seed": SEED_ALIAS_BASE + 500000 * (rnd + 1) + ri * 10000 + bi,
                              "key": _batch_key(reader, tax, [t["uid"] for t in b])})
        stats += _run_jobs(rjobs, pool, ckpt, tax, A.allow_reasoning_only, done,
                           f"repair round {rnd+1}")

    marks = collect_marks(ckpt, tax, by_uid)
    payload = {
        "taxonomy": tax, "conv_file": A.conv_file, "n_convs": len(convs), "n_turns": len(turns),
        "generator": A.generator,
        "truncate": A.truncate, "batch_size": A.batch_size, "readers_panel": MODELS,
        "batch_meta": batch_meta, "call_status_counts": dict(stats),
        # THIS PROJECTION IS THE SILENT-BREAK POINT. Any per-turn field that is not
        # named here is dropped WITHOUT AN ERROR and never reaches build_arm or
        # stage_analyze. excluded_reader / gt_board / gt_turn_type were ADDED at v2
        # for exactly that reason -- the ground-truth answer key would otherwise
        # vanish between the label stage and the primary statistic.
        "turns": [{k: t[k] for k in ("uid", "conv_id", "turn_idx", "followup_id",
                                     "gen_provider", "excluded_reader",
                                     "gt_board", "gt_turn_type")}
                  for t in turns],
        "turn_text": {str(t["uid"]): t["text"] for t in turns},
        "labels": {p: {str(k): v for k, v in d.items()} for p, d in marks.items()},
    }
    with open(A.label_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    got = Counter(len([p for p in ORDER if str(t["uid"]) in payload["labels"].get(p, {})])
                  for t in turns)
    print(f"\nwrote {A.label_file}")
    print(f"  call statuses: {dict(stats)}")
    print(f"  readers-per-turn distribution: {dict(sorted(got.items()))} (3 = complete case)")


def collect_marks(ckpt_path, taxonomy, by_uid):
    """Rebuild reader -> {uid: code} from the checkpoint, enforcing separation and
    never letting a later batch overwrite an earlier genuine label."""
    marks = defaultdict(dict)
    for row in _jsonl_read(ckpt_path):
        if row.get("taxonomy") != taxonomy or row.get("status") != "ok":
            continue
        prov = row.get("reader") or row.get("provider")
        for suid, code in (row.get("labels") or {}).items():
            uid = int(suid)
            if uid not in by_uid:
                continue
            if _excluded_reader(by_uid[uid]) == prov:    # separation, enforced structurally
                continue
            marks[prov].setdefault(uid, code)            # first write wins; no overwrite
    return marks


# =====================================================================
# STAGE 3 -- ANALYZE
# =====================================================================
def loco_folds(groups):
    """Leave-one-conversation-out index folds. A conversation is never in both sides."""
    uniq = sorted(set(groups))
    out = []
    for g in uniq:
        test = [i for i, x in enumerate(groups) if x == g]
        train = [i for i, x in enumerate(groups) if x != g]
        if train and test:
            out.append((train, test))
    return out


def _mode(seq, fallback=None, prior=None):
    """Most frequent element. Ties break on the TRAIN-FOLD overall frequency (`prior`),
    then on sorted class name. Rev 0.3 broke ties on name alone, which made every tie
    resolve to 'B0' because 'B0' sorts before B1..B5 -- a systematic tilt toward the
    'none dominates' class. The prior tie-break removes that arbitrary tilt; the
    residual name tie-break is disclosed in PREREG section 6."""
    if not seq:
        return fallback
    c = Counter(seq)
    top = max(c.values())
    cands = [k for k, v in c.items() if v == top]
    if len(cands) == 1:
        return cands[0]
    if prior:
        best = max(prior.get(k, 0) for k in cands)
        cands = [k for k in cands if prior.get(k, 0) == best]
    return sorted(cands)[0]


def _acc(corr):
    return (sum(corr) / len(corr)) if corr else 0.0


def loco_markov(bn, bnext, folds):
    """First-order Markov: argmax_{b'} count[b_N][b']. Returns (acc, per-pair correct)."""
    corr = [0] * len(bn)
    for train, test in folds:
        trans = defaultdict(list)
        for i in train:
            trans[bn[i]].append(bnext[i])
        prior = Counter(bnext[i] for i in train)
        backoff = _mode([bnext[i] for i in train], prior=prior)
        table = {k: _mode(v, backoff, prior) for k, v in trans.items()}
        for i in test:
            corr[i] = int(table.get(bn[i], backoff) == bnext[i])
    return _acc(corr), corr


def loco_conditional(cond, bnext, folds):
    """Predict the train-fold mode of b_{N+1} given a discrete conditioning value."""
    corr = [0] * len(bnext)
    for train, test in folds:
        buckets = defaultdict(list)
        for i in train:
            buckets[cond[i]].append(bnext[i])
        prior = Counter(bnext[i] for i in train)
        backoff = _mode([bnext[i] for i in train], prior=prior)
        table = {k: _mode(v, backoff, prior) for k, v in buckets.items()}
        for i in test:
            corr[i] = int(table.get(cond[i], backoff) == bnext[i])
    return _acc(corr), corr


def loco_marginal(bnext, folds):
    corr = [0] * len(bnext)
    for train, test in folds:
        prior = Counter(bnext[i] for i in train)
        m = _mode([bnext[i] for i in train], prior=prior)
        for i in test:
            corr[i] = int(bnext[i] == m)
    return _acc(corr), corr


def loco_persistence(bn, bnext, folds):
    """CONTROL 6. No fitted parameters, but computed over the SAME LOCO test indices so
    the prereg's 'all controls use the identical fold split' statement is literally true."""
    corr = [0] * len(bn)
    for _, test in folds:
        for i in test:
            corr[i] = int(bn[i] == bnext[i])
    return _acc(corr), corr


def _inner_group_splits(train, groups, k=3):
    """Deterministic grouped splits INSIDE a training fold, for tuning C without ever
    touching the held-out conversation."""
    gs = sorted({groups[i] for i in train})
    if len(gs) < 2:
        return []
    k = min(k, len(gs))
    buckets = [[] for _ in range(k)]
    for n, g in enumerate(gs):
        buckets[n % k].append(g)
    splits = []
    for b in buckets:
        held = set(b)
        va = [i for i in train if groups[i] in held]
        tr = [i for i in train if groups[i] not in held]
        if tr and va:
            splits.append((tr, va))
    return splits


C_GRID = (0.25, 1.0, 4.0, 16.0)


def loco_surface(kind, texts, bnext, groups, folds):
    """CONTROL 1 / PRIMARY KILL, one baseline. Same recipes as
    acceptance_gate.gate_surface_separability:
        char  : TfidfVectorizer(analyzer='char', ngram_range=(3,5), max_features=5000)
        word  : CountVectorizer(max_features=3000, stop_words='english', binary=True)
        length: raw character count
    on turn N's raw text -> LogisticRegression(max_iter=500, random_state=42) -> b_{N+1}.

    Rev 0.4 fixes two handicaps: (a) word-unigram and length now run on the PREDICTIVE
    task (topic is the single most likely surface route from turn N to turn N+1, and
    Rev 0.3 never ran it); (b) C is tuned INSIDE the training fold on grouped inner
    splits, so a default-C model on ~195 sparse rows cannot regularise to the majority
    class and collapse GATE 1 into GATE 2.
    Vectorisers are refit per fold, so no test text informs the training vocabulary.
    """
    def build(tr_texts, te_texts):
        if kind == "char":
            v = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=5000)
        elif kind == "word":
            v = CountVectorizer(max_features=3000, stop_words="english", binary=True)
        else:
            return (np.array([[len(t)] for t in tr_texts], dtype=float),
                    np.array([[len(t)] for t in te_texts], dtype=float))
        return v.fit_transform(tr_texts), v.transform(te_texts)

    corr = [0] * len(bnext)
    for train, test in folds:
        ytr = [bnext[i] for i in train]
        if len(set(ytr)) < 2:                       # degenerate fold -> fall back to the mode
            m = _mode(ytr, prior=Counter(ytr))
            for i in test:
                corr[i] = int(bnext[i] == m)
            continue
        # --- tune C inside the training fold only ---
        best_c, best_s = C_GRID[1], -1.0
        for c in C_GRID:
            hits = tot = 0
            for tr, va in _inner_group_splits(train, groups):
                ytr2 = [bnext[i] for i in tr]
                if len(set(ytr2)) < 2:
                    continue
                Xa, Xb = build([texts[i] for i in tr], [texts[i] for i in va])
                try:
                    clf = LogisticRegression(max_iter=500, random_state=42, C=c).fit(Xa, ytr2)
                except Exception:
                    continue
                hits += sum(int(p == bnext[i]) for p, i in zip(clf.predict(Xb), va))
                tot += len(va)
            s = hits / tot if tot else -1.0
            if s > best_s:
                best_s, best_c = s, c
        Xtr, Xte = build([texts[i] for i in train], [texts[i] for i in test])
        try:
            clf = LogisticRegression(max_iter=500, random_state=42, C=best_c).fit(Xtr, ytr)
        except Exception:
            m = _mode(ytr, prior=Counter(ytr))
            for i in test:
                corr[i] = int(bnext[i] == m)
            continue
        for p, i in zip(clf.predict(Xte), test):
            corr[i] = int(p == bnext[i])
    return _acc(corr), corr


def within_group_permutation(bnext, groups, rng):
    """CONTROL 3. Permute b_{N+1} WITHIN each conversation.

    Rev 0.3 permuted globally, which also destroyed CONVERSATION-LEVEL CLUSTERING.
    Each conversation is one seed prompt on one topic from one model, so its turns are
    label-homogeneous for reasons that have nothing to do with transitions; a global
    shuffle lets that homogeneity alone push board_acc far above the null, and GATE 3
    then passes with no transition structure whatsoever. A within-conversation
    (block) permutation preserves each conversation's label composition and isolates
    exactly the temporal link."""
    out = list(bnext)
    idx = defaultdict(list)
    for i, g in enumerate(groups):
        idx[g].append(i)
    for g in sorted(idx):
        ii = idx[g]
        vals = [bnext[i] for i in ii]
        rng.shuffle(vals)
        for i, v in zip(ii, vals):
            out[i] = v
    return out


def nmi(a, b):
    """Normalised mutual information (arithmetic-mean normalisation).
    Upward-biased at small n, so it is ALWAYS reported against its own within-group
    permutation null (Rev 0.4) and is descriptive, never gating."""
    n = len(a)
    if n == 0:
        return 0.0
    ca, cb, cj = Counter(a), Counter(b), Counter(zip(a, b))
    hi = -sum((v / n) * np.log(v / n) for v in ca.values())
    hj = -sum((v / n) * np.log(v / n) for v in cb.values())
    mi = sum((v / n) * np.log((v / n) / ((ca[x] / n) * (cb[y] / n)))
             for (x, y), v in cj.items())
    denom = 0.5 * (hi + hj)
    return float(mi / denom) if denom > 1e-12 else 0.0


def paired_cluster_bootstrap(corr_a, corr_b, groups, n_boot, seed):
    """Paired bootstrap over CONVERSATIONS of (acc_a - acc_b).

    Observations cluster (up to 5 pairs per conversation), so effective n is well below
    the pair count and a plain 0.05 margin is roughly 1.2 SE. The preregistered margins
    are therefore thresholds on THIS statistic: the point margin must clear the margin
    AND the lower percentile must exceed 0."""
    if not corr_a:
        return {"mean": 0.0, "p5": 0.0, "p2.5": 0.0, "p97.5": 0.0, "n_boot": 0}
    idx = defaultdict(list)
    for i, g in enumerate(groups):
        idx[g].append(i)
    gs = sorted(idx)
    rng = np.random.default_rng(seed)
    a = np.asarray(corr_a, dtype=float)
    b = np.asarray(corr_b, dtype=float)
    diffs = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(gs), len(gs))
        sel = [i for p in pick for i in idx[gs[p]]]
        if not sel:
            continue
        diffs.append(float(a[sel].mean() - b[sel].mean()))
    if not diffs:
        return {"mean": 0.0, "p5": 0.0, "p2.5": 0.0, "p97.5": 0.0, "n_boot": 0}
    d = np.asarray(diffs)
    return {"mean": round(float(d.mean()), 4),
            "p2.5": round(float(np.percentile(d, 2.5)), 4),
            "p5": round(float(np.percentile(d, BOOT_LOWER_Q)), 4),
            "p97.5": round(float(np.percentile(d, 97.5)), 4),
            "n_boot": len(diffs)}


# ---------------------------------------------------------------------
def build_arm(payload, none_code):
    """Consensus, agreement and (turn N -> turn N+1) pairs for one taxonomy arm.

    Rev 0.4 DECOUPLES the two metrics (fatal fix 3c):
      * agreement (Fleiss / raw pairwise) is computed on COMPLETE cases only, so the
        number is never inflated by non-random dropout on hard items;
      * consensus may be formed from >=2 AGREEING among >=2 PRESENT labels, so a
        single missing reader does not destroy a usable turn.
    """
    turn_meta = {t["uid"]: t for t in payload["turns"]}
    turn_text = {int(k): v for k, v in payload["turn_text"].items()}
    labels = {p: {int(k): v for k, v in d.items()} for p, d in payload["labels"].items()}

    per_turn, complete, consensus = {}, [], {}
    for uid, meta in turn_meta.items():
        readers = [p for p in ORDER if p != _excluded_reader(meta)]
        got = {p: labels.get(p, {}).get(uid) for p in readers}
        codes = [c for c in got.values() if c]
        per_turn[uid] = {"readers": readers, "codes": got}
        if len(codes) == len(readers):
            complete.append(uid)
        if len(codes) >= 2:
            cnt = Counter(codes)
            top, n_top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            if n_top >= 2:
                consensus[uid] = top

    n_turns = len(turn_meta)
    complete_cov = len(complete) / n_turns if n_turns else 0.0
    consensus_cov = len(consensus) / n_turns if n_turns else 0.0

    combos = list(itertools.combinations(range(3), 2))
    pair_scores, kappa_rows = [], []
    for uid in complete:
        cs = [per_turn[uid]["codes"][p] for p in per_turn[uid]["readers"]]
        pair_scores.append(sum(cs[i] == cs[k] for i, k in combos) / len(combos))
        kappa_rows.append(cs)
    raw_agree = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    kappa = fleiss_kappa(kappa_rows) if len(kappa_rows) >= 2 else 0.0

    usage = Counter(consensus.values())
    none_share = usage.get(none_code, 0) / len(consensus) if consensus else 1.0

    # Derived raw-agreement floor. The kappa floor and a flat raw floor are two
    # INDEPENDENT hurdles whose joint difficulty was never computed in Rev 0.3 (with
    # 6 classes and B0 <= 0.40, Pe ~ 0.25, so raw 0.50 implies kappa ~ 0.33 < 0.35).
    # Rev 0.4 derives the binding raw floor from the OBSERVED marginals so the two are
    # one hurdle expressed twice, and keeps an absolute 0.50 as a second, explicit one.
    tot = sum(usage.values()) or 1
    pe = sum((v / tot) ** 2 for v in usage.values())
    derived_raw_floor = pe + G0_FLEISS_MIN * (1 - pe)

    by_conv = defaultdict(dict)
    for uid, meta in turn_meta.items():
        by_conv[meta["conv_id"]][meta["turn_idx"]] = uid
    bn, bnext, groups, texts, cond_user, cond_pos = [], [], [], [], [], []
    for cid, idxs in sorted(by_conv.items()):
        for ti in sorted(idxs):
            if (ti + 1) not in idxs:
                continue
            u0, u1 = idxs[ti], idxs[ti + 1]
            if u0 in consensus and u1 in consensus:
                bn.append(consensus[u0]); bnext.append(consensus[u1])
                groups.append(cid); texts.append(turn_text[u0])
                cond_user.append(turn_meta[u1]["followup_id"])
                cond_pos.append(ti)

    return {
        "turn_meta": turn_meta, "turn_text": turn_text, "labels": labels,
        "n_turns": n_turns, "n_complete": len(complete), "n_consensus": len(consensus),
        "complete_cov": complete_cov, "consensus_cov": consensus_cov,
        "raw_agree": raw_agree, "kappa": kappa, "n_kappa_rows": len(kappa_rows),
        "usage": usage, "none_share": none_share, "pe": pe,
        "derived_raw_floor": derived_raw_floor,
        "bn": bn, "bnext": bnext, "groups": groups, "texts": texts,
        "cond_user": cond_user, "cond_pos": cond_pos, "consensus": consensus,
    }


def prescribed_corpus_structure(arm):
    """The corpus's OWN structure, read off the answer key and NOT off any reader.

    Mandatory disclosure for a forced-transition corpus: a reader must be able to
    see that stickiness was actually removed. Returns None in the api arm, which
    has no answer key.
    """
    by_conv = defaultdict(dict)
    for uid, m in arm["turn_meta"].items():
        if m.get("gt_board"):
            by_conv[m["conv_id"]][m["turn_idx"]] = m["gt_board"]
    if not by_conv:
        return None
    trans, same, tot = Counter(), 0, 0
    for _cid, d in sorted(by_conv.items()):
        for ti in sorted(d):
            if (ti + 1) in d:
                trans[(d[ti], d[ti + 1])] += 1
                tot += 1
                same += int(d[ti] == d[ti + 1])
    mix = Counter(m["gt_board"] for m in arm["turn_meta"].values() if m.get("gt_board"))
    n = sum(mix.values()) or 1
    return {
        "n_prescribed_turns": sum(mix.values()),
        "prescribed_board_mix": {b: mix.get(b, 0) for b in BOARDS},
        "prescribed_none_share": round(mix.get("B0", 0) / n, 4),
        "n_prescribed_pairs": tot,
        "realised_transition_matrix": {f"{a}->{b}": c for (a, b), c in sorted(trans.items())},
        "CORPUS_PERSISTENCE_RATE": round((same / tot) if tot else 0.0, 4),
        "why_this_is_reported": "the api-corpus smoke was REJECTED because natural "
                                "conversation is STICKY (persistence 0.5238 vs Markov "
                                "0.5079 -- almost nothing left to predict). Forced "
                                "paths break persistence BY CONSTRUCTION; this number "
                                "is the evidence that it was actually removed.",
        "unreachable_boards_zero_prescribed_instances": list(SDG_UNREACHABLE_BOARDS),
        "structurally_unrealisable_transitions": list(SDG_UNREALISABLE_TRANSITIONS),
    }


def rubric_adherence_check(arm, n_boot, boot_seed):
    """RUBRIC ADHERENCE / READER RELIABILITY -- NOT calibration, NOT ground truth.

    RENAMED AT v2.1. This function was called ground_truth_calibration and its
    statistic was called gt_acc. Both names were UNEARNED and are withdrawn.

    WHY (the defect that voids the statistic, preregistered as a NAMED KILL in
    PREREG v2 section 3B.0 alongside GATE RA-2): the answer key was authored by
    reading the rendered template strings THROUGH THE SAME RUBRIC the reader panel
    is given. B1's entire prescribed class is ONE byte-identical string whose
    wording is a near-verbatim cue for the B1 rubric's lead clause; B5's is one
    template against a rubric clause it paraphrases. So this statistic measures
    whether an LLM panel applying rubric R to string S reproduces the label an
    author assigned to string S by applying rubric R. It HAS NO INFORMATIVE RANGE:
    a high value is guaranteed by the authoring, a low value indicates reader noise
    only. Nothing here is calibration, and the truth is not independently known.

    What it CAN legitimately be read as: a reader-reliability probe -- do three
    blind commercial readers apply this rubric to fixed strings the way its author
    did? That is a fact about READERS and a RUBRIC, never about model behaviour and
    never about the world.

    Returns None in the api arm (no answer key exists there).
    """
    # ---- denominators, honestly split -------------------------------------
    # PRESCRIBED = the design count. WITH CONSENSUS = what survived to a consensus
    # label. Reporting only the second hides NON-RANDOM DROPOUT: if readers
    # systematically fail to reach consensus on one prescribed class, the accuracy
    # is computed on a survivor set and the loss is invisible.
    prescribed_all = Counter(m["gt_board"] for m in arm["turn_meta"].values()
                             if m.get("gt_board"))
    if not prescribed_all:
        return None
    uids = [u for u in sorted(arm["consensus"]) if arm["turn_meta"][u].get("gt_board")]
    if len(uids) < 2:
        return None
    y_true = [arm["turn_meta"][u]["gt_board"] for u in uids]
    y_read = [arm["consensus"][u] for u in uids]
    grp = [arm["turn_meta"][u]["conv_id"] for u in uids]
    txt = [arm["turn_text"][u] for u in uids]

    corr_ra = [int(a == b) for a, b in zip(y_true, y_read)]
    ra_acc = _acc(corr_ra)

    survived = Counter(y_true)
    folds = loco_folds(grp)

    # ---- chance level, LOCO (not in-sample) -------------------------------
    # v2.1: the in-sample modal-class rate was mixed with a LOCO surface control.
    # The gating chance level is now LOCO-measured on the same folds; the in-sample
    # value is still reported so the two are visibly separated.
    maj_in_sample = _mode(y_true, prior=survived)
    corr_chance_in_sample = [int(t == maj_in_sample) for t in y_true]
    chance_in_sample = _acc(corr_chance_in_sample)
    if folds:
        chance_majority, corr_chance = loco_marginal(y_true, folds)
    else:
        chance_majority, corr_chance = chance_in_sample, corr_chance_in_sample

    conf = Counter(zip(y_true, y_read))
    per_class = {}
    for b in BOARDS:
        n_pres = prescribed_all.get(b, 0)
        n_cons = survived.get(b, 0)
        per_class[b] = {
            # v2.1: the field formerly called n_prescribed was NOT the prescribed
            # count -- it counted only instances that reached a consensus label.
            "n_prescribed_by_design": n_pres,
            "n_prescribed_with_consensus": n_cons,
            "consensus_coverage_for_this_prescribed_class": (
                round(n_cons / n_pres, 4) if n_pres else None),
            "recall_among_those_with_consensus": (
                round(conf.get((b, b), 0) / n_cons, 4) if n_cons else None),
            "note": ("UNREACHABLE -- this board cannot be constructed from the SDG "
                     "template table at all, so it has zero prescribed instances by "
                     "construction and nothing here speaks to it."
                     if n_pres == 0 else
                     ("NO CONSENSUS SURVIVED -- every prescribed instance of this "
                      "class was lost before scoring; the accuracy above is computed "
                      "on a survivor set that excludes it entirely."
                      if n_cons == 0 else None)),
            "weak_mapping": sorted(
                k for k in SDG_WEAK_MAPPINGS if k.endswith("->" + b)) or None,
        }

    # ---- SURFACE CONTROL ON THE SAME TASK -- FAILS CLOSED ------------------
    # v2.1 FIX: this used to initialise surface_acc = 0.0 and run the battery only
    # `if folds and len(set(y_true)) >= 2`. When it did not run, the comparison
    # corr vector was filled with zeros and the PRIMARY KILL silently PASSED with
    # NO SURFACE CONTROL HAVING BEEN COMPUTED. A kill gate must FAIL CLOSED: an
    # uncomputable control yields None gates and a VACUOUS verdict, never a pass.
    surf, surf_name, corr_surf, surface_acc = {}, None, None, None
    if folds and len(set(y_true)) >= 2:
        for kind in ("char", "word", "length"):
            a, c = loco_surface(kind, txt, y_true, grp, folds)
            surf[kind] = round(a, 4)
            if surface_acc is None or a > surface_acc:
                surf_name, surface_acc, corr_surf = kind, a, c
    surface_computed = bool(corr_surf)

    boot = {"ra_minus_chance": paired_cluster_bootstrap(corr_ra, corr_chance, grp,
                                                        n_boot, boot_seed + 1)}
    if surface_computed:
        boot["ra_minus_surface"] = paired_cluster_bootstrap(corr_ra, corr_surf, grp,
                                                            n_boot, boot_seed + 2)

    ra1 = bool(ra_acc >= RA_ACC_MIN
               and (ra_acc - chance_majority) >= RA_MARGIN_OVER_CHANCE
               and boot["ra_minus_chance"]["p5"] > 0.0)
    # GATE RA-2 is None (NOT False, NOT True) when the control could not be run.
    ra2 = (None if not surface_computed else
           bool((ra_acc - surface_acc) >= RA_MARGIN_OVER_SURFACE
                and boot["ra_minus_surface"]["p5"] > 0.0))

    # ---- VERDICT VOCABULARY: CALIBRATED IS NOT AVAILABLE -------------------
    if SDG_MAPPING_CIRCULARITY_KILL:
        verdict = ("NOT LICENSED -- MAPPING CIRCULAR (the answer key was authored "
                   "from these same strings through this same rubric)")
    elif ra2 is None:
        verdict = "VACUOUS -- the surface control could not be computed"
    elif not ra2:
        verdict = "NOT LICENSED -- SURFACE CONTROL WON"
    elif ra1:
        verdict = "RUBRIC-ADHERENT (readers reproduce the author's rubric application)"
    else:
        verdict = "NOT RUBRIC-ADHERENT"

    return {
        "STATISTIC": "RUBRIC ADHERENCE / READER RELIABILITY. NOT calibration, NOT "
                     "validation against known ground truth. Renamed at v2.1: the "
                     "words CALIBRATED and KNOWN GROUND TRUTH are UNEARNED here and "
                     "are not available verdicts anywhere in this arm.",
        "KILL_MAPPING_CIRCULARITY": SDG_MAPPING_CIRCULARITY_KILL,
        "KILL_MAPPING_CIRCULARITY_DETAIL": SDG_MAPPING_CIRCULARITY_DISCLOSURE,
        "WHAT_IT_MEASURES": "whether an LLM panel applying rubric R to string S "
                            "reproduces the label an author assigned to string S by "
                            "applying rubric R. A pass is guaranteed by the "
                            "authoring; a fail indicates reader noise. NO "
                            "INFORMATIVE RANGE.",
        "TEMPLATE_DISCLOSURE": SDG_TEMPLATE_DISCLOSURE,
        "MAPPING_IS_OURS": "cas-synthetic emits DIALOG ACTS; the taxonomy names "
                           "BOARDS. Neither framework supplies a correspondence. The "
                           "turn-type -> board mapping used here is AN ASSUMPTION WE "
                           "ARE MAKING, preregistered in PREREG v2 section 3B, on the "
                           "same disclosure footing as the sequencing claim of "
                           "section 3. Turn types with no defensible board are mapped "
                           "to NONE and EXCLUDED, never forced.",
        "turn_type_to_board": dict(SDG_TURN_TYPE_TO_BOARD),
        "WEAK_MAPPINGS": dict(SDG_WEAK_MAPPINGS),
        "EFFECTIVE_MAPPING_IS_SIX_TURN_TYPES_NOT_ELEVEN":
            "no forced path uses ACK or EMPATHIZE, so realised B0 mass comes only "
            "from MIRROR / ANSWER / CLARIFY / REFUSE_CLAIM. The 11-row table "
            "overstates what governs.",
        "n_scored_turns": len(uids),
        "n_prescribed_turns_by_design": sum(prescribed_all.values()),
        "consensus_coverage_overall_on_prescribed_turns":
            round(len(uids) / sum(prescribed_all.values()), 4),
        "rubric_adherence_acc": round(ra_acc, 4),
        "chance_uniform_1_over_6": round(CHANCE, 4),
        "chance_modal_prescribed_class_LOCO": round(chance_majority, 4),
        "chance_modal_prescribed_class_in_sample_not_gating":
            round(chance_in_sample, 4),
        "chance_note": "1/6 is NOT the operative chance level. The gating one is the "
                       "LOCO-measured always-predict-the-modal-PRESCRIBED-class rate. "
                       "v2.1: this was formerly computed IN-SAMPLE while the surface "
                       "control was LOCO -- inconsistent, and conservative in the "
                       "wrong direction to be left unstated. Both are now printed.",
        "confusion_prescribed_x_read": {f"{a}|{b}": c for (a, b), c in sorted(conf.items())},
        "per_class_recall": per_class,
        "n_boards_with_zero_prescribed_instances": sum(
            1 for b in BOARDS if prescribed_all.get(b, 0) == 0),
        "surface_control_on_the_same_task": {
            "computed": surface_computed,
            "strongest": surf_name,
            "acc": (round(surface_acc, 4) if surface_acc is not None else None),
            "by_kind": surf,
            "kill_rule": "a surface WIN (or the margin failing) KILLS the arm "
                         "outright -- the reader would be doing nothing a "
                         "bag-of-chars over the template table could not do. "
                         "v2.1: if this control CANNOT BE COMPUTED the gate is None "
                         "and the verdict is VACUOUS. It never fails open.",
            "measured_at_precheck": "1.0000 on char, word AND raw character count "
                                    "over the realised 36-conversation corpus, so "
                                    "GATE RA-2 is UNSATISFIABLE by any accuracy. See "
                                    "`--stage precheck`."},
        "uncertainty": boot,
        "GATE_RA1_reads_above_chance": ra1,
        "GATE_RA2_beats_surface_PRIMARY_KILL": ra2,
        "GATE_RA_thresholds": {"ra_acc_min": RA_ACC_MIN,
                               "margin_over_chance": RA_MARGIN_OVER_CHANCE,
                               "margin_over_surface": RA_MARGIN_OVER_SURFACE},
        "RUBRIC_ADHERENCE_VERDICT": verdict,
        "CEILING": f"Whatever this run finds, nothing here speaks to "
                   f"{list(SDG_UNREACHABLE_BOARDS)}: no SDG turn type renders a "
                   f"rate/cycle/rigidity claim, a two-input comparison with "
                   f"cancellation, or a resemblance-of-shape memory retrieval, so "
                   f"those three boards have ZERO prescribed instances by "
                   f"construction. And nothing here speaks to model behaviour at "
                   f"all: the text is a 38-string lookup table and the answer key is "
                   f"circular with the rubric.",
    }


def agreement_block(arm, min_pairs, none_code):
    raw_floor = max(G0_RAW_AGREE_ABS_MIN, arm["derived_raw_floor"])
    return {
        "fleiss_kappa": {"value": round(arm["kappa"], 4), "min": G0_FLEISS_MIN,
                         "n_complete_cases": arm["n_kappa_rows"],
                         "pass": bool(arm["kappa"] >= G0_FLEISS_MIN)},
        "raw_pairwise_agreement": {
            "value": round(arm["raw_agree"], 4),
            "min_absolute": G0_RAW_AGREE_ABS_MIN,
            "min_derived_from_marginals": round(arm["derived_raw_floor"], 4),
            "chance_agreement_Pe": round(arm["pe"], 4),
            "min_binding": round(raw_floor, 4),
            "pass": bool(arm["raw_agree"] >= raw_floor)},
        "complete_case_coverage": {"value": round(arm["complete_cov"], 4),
                                   "min": G0_COMPLETE_COV_MIN,
                                   "n": arm["n_complete"], "n_min": G0_COMPLETE_N_MIN,
                                   "pass": bool(arm["complete_cov"] >= G0_COMPLETE_COV_MIN
                                                and arm["n_complete"] >= G0_COMPLETE_N_MIN)},
        "consensus_coverage": {"value": round(arm["consensus_cov"], 4),
                               "min": G0_CONSENSUS_COV_MIN,
                               "note": ">=2 agreeing among >=2 present labels",
                               "pass": bool(arm["consensus_cov"] >= G0_CONSENSUS_COV_MIN)},
        "none_class_share": {"code": none_code, "value": round(arm["none_share"], 4),
                             "max": G0_B0_SHARE_MAX,
                             "pass": bool(arm["none_share"] <= G0_B0_SHARE_MAX)},
        "usable_pairs": {"value": len(arm["bn"]), "min": min_pairs,
                         "pass": bool(len(arm["bn"]) >= min_pairs)},
    }


def stage_gate0(A):
    """Gate 0 ONLY. Prints agreement and coverage and nothing else, so the prereg's
    'Gate 0 is read BEFORE any prediction number' is enforceable rather than aspirational."""
    payload = json.load(open(A.label_file, encoding="utf-8"))
    arm = build_arm(payload, TAXONOMY[A.taxonomy]["none"])
    min_pairs = 8 if A.smoke else G0_MIN_PAIRS
    g0 = agreement_block(arm, min_pairs, TAXONOMY[A.taxonomy]["none"])
    g0_pass = all(v["pass"] for v in g0.values())
    out = {"stage": "gate0", "taxonomy": A.taxonomy, "smoke": bool(A.smoke),
           "n_turns": arm["n_turns"], "n_complete": arm["n_complete"],
           "n_consensus": arm["n_consensus"], "n_usable_pairs": len(arm["bn"]),
           "consensus_usage": dict(arm["usage"]), "GATE0": g0, "GATE0_pass": g0_pass,
           "note": "NO prediction statistic is computed or shown by this stage."}
    with open(A.gate0_report, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n=== GATE 0 ONLY ({A.taxonomy}) ===")
    print(f"  turns {arm['n_turns']} | complete {arm['n_complete']} | "
          f"consensus {arm['n_consensus']} | usable pairs {len(arm['bn'])}")
    for k, v in g0.items():
        print(f"  {k:28s} {v['value']}  {'ok' if v['pass'] else 'FAIL'}")
    print(f"  GATE 0: {'PASS' if g0_pass else 'FAIL -> VACUOUS'}")
    if A.smoke:
        print("  NOTE: --smoke can never PASS Gate 0 (min_pairs 8 == the only 8 possible "
              "pairs, i.e. 100% coverage required). Smoke is a RED-LIGHT-ONLY check: a "
              "smoke kappa near zero is a stop signal; a smoke VACUOUS is not.")
    print(f"  wrote {A.gate0_report}")


def stage_analyze(A):
    payload = json.load(open(A.label_file, encoding="utf-8"))
    arm = build_arm(payload, "B0")

    # ---- v2.1: PROVENANCE IS DECIDED BY THE DATA, NOT BY A CLI FLAG -------
    # --label-file has a CLI override and --stage analyze does not require
    # --generator, so `--stage analyze --label-file labels_board_sdg.json` with the
    # flag omitted used to analyse TEMPLATE data as an api run: the verdict came off
    # the sequential ladder, every sdg claim-ceiling entry was dropped, and
    # TEMPLATE_DISCLOSURE was affirmatively written as "n/a -- the api arm's turns
    # are real model outputs" -- a FALSE PROVENANCE STATEMENT in the report, on the
    # exact axis this design spends most of its length defending. is_sdg is now read
    # off the payload and off the presence of an answer key, and a disagreement with
    # the flag is FATAL rather than silent.
    gen_in_payload = payload.get("generator")
    has_answer_key = any(t.get("gt_board") for t in payload.get("turns", []))
    is_sdg = bool(gen_in_payload == "sdg" or has_answer_key)
    if gen_in_payload not in (None, A.generator):
        raise SystemExit(
            f"ABORT: provenance mismatch. {A.label_file} was labelled with "
            f"generator='{gen_in_payload}' but --generator is '{A.generator}'. "
            f"Re-run with --generator {gen_in_payload}. (Analysing an sdg label "
            f"file as an api run writes a FALSE provenance statement into the "
            f"report.)")
    if is_sdg and A.generator != "sdg":
        raise SystemExit(
            f"ABORT: {A.label_file} carries a prescribed-board answer key, so it is "
            f"a TEMPLATE-RENDERED sdg corpus, but --generator is '{A.generator}'. "
            f"Re-run with --generator sdg.")
    if A.generator == "sdg" and not is_sdg:
        raise SystemExit(
            f"ABORT: --generator sdg was requested but {A.label_file} carries no "
            f"answer key and no generator marker. Refusing to label api data as "
            f"template-rendered.")

    bn, bnext, groups, texts = arm["bn"], arm["bnext"], arm["groups"], arm["texts"]
    n_pairs = len(bn)
    folds = loco_folds(groups)
    min_pairs = 8 if A.smoke else G0_MIN_PAIRS

    # ---- GATE 0 (read first; computed here but printed and gated before prediction) --
    g0 = agreement_block(arm, min_pairs, "B0")
    g0_collisions = sum(m.get("residual_same_conv_collisions", 0)
                        for m in payload.get("batch_meta", []))
    g0["no_same_conversation_batch_collisions"] = {
        "value": g0_collisions, "max": 0, "pass": bool(g0_collisions == 0)}
    g0_pass = all(v["pass"] for v in g0.values())

    # ---- prediction + controls ------------------------------------------
    board_acc, corr_board = loco_markov(bn, bnext, folds) if folds else (0.0, [])
    char_acc, corr_char = loco_surface("char", texts, bnext, groups, folds) if folds else (0.0, [])
    word_acc, corr_word = loco_surface("word", texts, bnext, groups, folds) if folds else (0.0, [])
    len_acc, corr_len = loco_surface("length", texts, bnext, groups, folds) if folds else (0.0, [])
    marg_acc, corr_marg = loco_marginal(bnext, folds) if folds else (0.0, [])
    pers_acc, corr_pers = loco_persistence(bn, bnext, folds) if folds else (0.0, [])
    user_acc, corr_user = loco_conditional(arm["cond_user"], bnext, folds) if folds else (0.0, [])
    pos_acc, corr_pos = loco_conditional(arm["cond_pos"], bnext, folds) if folds else (0.0, [])

    # PRIMARY KILL uses the STRONGEST surface baseline, not just char.
    # v2.1 FAIL-CLOSED: when there are no LOCO folds every control above collapses to
    # (0.0, []) and GATE 1 used to evaluate (board_acc - 0.0) >= 0.05 -- i.e. the
    # PRIMARY KILL silently PASSED with no surface control having been computed at
    # all. controls_computed now forces every gate to None and the verdict to
    # VACUOUS. A kill gate must fail closed.
    controls_computed = bool(folds and corr_char and corr_board)
    surf = {"char": (char_acc, corr_char), "word": (word_acc, corr_word),
            "length": (len_acc, corr_len)}
    surf_name = max(surf, key=lambda k: surf[k][0]) if folds else "char"
    surface_acc, corr_surface = surf[surf_name]

    # CONTROL 3 -- WITHIN-CONVERSATION permutation null
    null_trials, null_nmi = [], []
    if n_pairs and folds:
        rng = random.Random(SEED_PERM_NULL)
        for _ in range(A.perm_trials):
            perm = within_group_permutation(bnext, groups, rng)
            null_trials.append(loco_markov(bn, perm, folds)[0])
            null_nmi.append(nmi(bn, perm))
    null_mean = float(np.mean(null_trials)) if null_trials else 0.0
    null_p95 = float(np.percentile(null_trials, 95)) if null_trials else 0.0
    p_perm = ((sum(1 for x in null_trials if x >= board_acc) + 1) /
              (len(null_trials) + 1)) if null_trials else 1.0
    real_nmi = nmi(bn, bnext) if n_pairs else 0.0
    p_nmi = ((sum(1 for x in null_nmi if x >= real_nmi) + 1) /
             (len(null_nmi) + 1)) if null_nmi else 1.0

    # paired cluster bootstrap on every gating margin
    boot = {
        "board_minus_surface": paired_cluster_bootstrap(corr_board, corr_surface, groups,
                                                        A.n_boot, SEED_BOOTSTRAP),
        "board_minus_marginal": paired_cluster_bootstrap(corr_board, corr_marg, groups,
                                                         A.n_boot, SEED_BOOTSTRAP + 1),
        "board_minus_persistence": paired_cluster_bootstrap(corr_board, corr_pers, groups,
                                                            A.n_boot, SEED_BOOTSTRAP + 2),
        "board_minus_usermove": paired_cluster_bootstrap(corr_board, corr_user, groups,
                                                         A.n_boot, SEED_BOOTSTRAP + 3),
        "board_minus_turnpos": paired_cluster_bootstrap(corr_board, corr_pos, groups,
                                                        A.n_boot, SEED_BOOTSTRAP + 4),
    }

    # ---- CONTROL 8 -- matched-taxonomy arm (same panel, same corpus) -----
    alt = alt_g0 = None
    alt_acc, corr_alt = None, []
    if os.path.exists(A.alt_label_file):
        alt_payload = json.load(open(A.alt_label_file, encoding="utf-8"))
        alt = build_arm(alt_payload, "D0")
        alt_g0 = agreement_block(alt, min_pairs, "D0")
        # Restrict the comparison to pairs usable in BOTH arms so the margin is paired.
        key_b = {(arm["turn_meta"][u]["conv_id"], arm["turn_meta"][u]["turn_idx"]): u
                 for u in arm["consensus"]}
        key_a = {(alt["turn_meta"][u]["conv_id"], alt["turn_meta"][u]["turn_idx"]): u
                 for u in alt["consensus"]}
        shared, an, anext, agroups = [], [], [], []
        bn2, bnext2 = [], []
        for cid, ti in sorted(k for k in key_b if k in key_a):
            if (cid, ti + 1) in key_b and (cid, ti + 1) in key_a:
                shared.append((cid, ti))
                an.append(alt["consensus"][key_a[(cid, ti)]])
                anext.append(alt["consensus"][key_a[(cid, ti + 1)]])
                bn2.append(arm["consensus"][key_b[(cid, ti)]])
                bnext2.append(arm["consensus"][key_b[(cid, ti + 1)]])
                agroups.append(cid)
        afolds = loco_folds(agroups)
        if afolds:
            alt_acc, corr_alt = loco_markov(an, anext, afolds)
            board_acc_shared, corr_board_shared = loco_markov(bn2, bnext2, afolds)
            boot["board_minus_alt_taxonomy_on_shared_pairs"] = paired_cluster_bootstrap(
                corr_board_shared, corr_alt, agroups, A.n_boot, SEED_BOOTSTRAP + 5)
            alt_g0["_shared_pairs"] = len(an)
            alt_g0["_board_acc_on_shared_pairs"] = round(board_acc_shared, 4)
            alt_g0["_alt_acc_on_shared_pairs"] = round(alt_acc, 4)

    # ---- companion diagnostic: same-turn surface separability ------------
    # LOCO-GROUPED version is the one that flags. acceptance_gate's own function is
    # StratifiedKFold with NO conversation grouping, so same-conversation text leaks
    # across folds and inflates it; it is reported for comparability only, never gated.
    same_turn_grouped, same_turn_ungrouped = {}, {}
    uids = sorted(arm["consensus"])
    if len(uids) >= 12 and len(set(arm["consensus"].values())) >= 2:
        st_y = [arm["consensus"][u] for u in uids]
        st_g = [arm["turn_meta"][u]["conv_id"] for u in uids]
        st_x = [arm["turn_text"][u] for u in uids]
        st_folds = loco_folds(st_g)
        if st_folds:
            for kind in ("char", "word", "length"):
                same_turn_grouped[kind] = round(
                    loco_surface(kind, st_x, st_y, st_g, st_folds)[0], 4)
        try:
            same_turn_ungrouped = gate_surface_separability(
                [{"text": t} for t in st_x], st_y, chance=CHANCE)
        except Exception as e:
            same_turn_ungrouped = {"error": str(e)[:200]}
    st_max = max(same_turn_grouped.values()) if same_turn_grouped else None

    # ---- gates -----------------------------------------------------------
    def gate(margin_name, acc_a, acc_b, margin):
        # v2.1: None (not False, not True) when the control could not be computed.
        if not controls_computed:
            return None
        b = boot.get(margin_name, {})
        return bool((acc_a - acc_b) >= margin and b.get("p5", -1.0) > 0.0)

    g1 = gate("board_minus_surface", board_acc, surface_acc, G1_MARGIN_OVER_SURFACE)
    g2 = gate("board_minus_marginal", board_acc, marg_acc, G2_MARGIN_OVER_MARGINAL)
    g3 = bool(p_perm < G3_ALPHA and board_acc > null_p95)
    # GATE 4 is COMPUTED, not asserted -- a violation must produce REJECTED, not a crash.
    violations = {p: sorted(u for u in d if arm["turn_meta"].get(u, {}).get("gen_provider") == p)
                  for p, d in arm["labels"].items()}
    violations = {p: v for p, v in violations.items() if v}
    g4 = bool(not violations)
    g5 = gate("board_minus_persistence", board_acc, pers_acc, G5_MARGIN_OVER_PERSISTENCE)
    # GATE 6 is a HARD KILL in Rev 0.4: with i.i.d. follow-ups the scripted stimulus is
    # the remaining route to a design-induced signal, and a design-induced signal must
    # REJECT, not merely downgrade.
    g6 = gate("board_minus_usermove", board_acc, user_acc, G6_MARGIN_OVER_USERMOVE)
    g7 = gate("board_minus_turnpos", board_acc, pos_acc, G7_MARGIN_OVER_TURNPOS)
    # GATE 8 speaks to CAS-specificity. v2.1: it is FORCED TO None in the sdg arm --
    # claim-ceiling 10B.14 says no CAS-specificity claim is available from a
    # template corpus, so a bare `true` sitting in gates/ is a lift surface even
    # though the cas_spec prose overrides it.
    g8 = None
    if alt_acc is not None and not is_sdg:
        g8 = gate("board_minus_alt_taxonomy_on_shared_pairs",
                  alt_g0["_board_acc_on_shared_pairs"], alt_acc, G8_MARGIN_OVER_ALT_TAXONOMY)

    if not controls_computed:
        verdict = "VACUOUS -- controls could not be computed (no LOCO folds)"
    elif not g0_pass:
        verdict = "VACUOUS"
    elif not (g1 and g2 and g3 and g4 and g6):
        verdict = "REJECTED"
    elif g5 and g7:
        verdict = "SUPPORTED"
    else:
        verdict = "SUPPORTED (weak)"

    if verdict.startswith("SUPPORTED"):
        if g8 is True:
            cas_spec = ("BOARD-TAXONOMY-SPECIFIC beyond one matched 6-class discourse "
                        "taxonomy on the same corpus and panel. Still NOT 'CAS-specific' "
                        "in any deeper sense -- one matched control is not the space of "
                        "possible taxonomies.")
        elif g8 is False:
            cas_spec = ("GREY -- the matched discourse taxonomy predicts as well. Any "
                        "sequential signal found is generic conversational structure, "
                        "NOT specific to the board taxonomy.")
            verdict = "SUPPORTED (weak)"
        else:
            cas_spec = "GREY -- the matched-taxonomy arm did not run (no alt label file)."
    else:
        cas_spec = "GREY -- not licensed to be assessed; the primary test did not pass."

    killed_by_surface = bool(g0_pass and surface_acc >= board_acc)
    taxonomy_kill = bool(arm["kappa"] < KILL_FLEISS_BELOW and arm["n_kappa_rows"] >= 10)
    fit_kill = bool(arm["none_share"] > KILL_B0_SHARE_ABOVE and arm["n_consensus"] >= 10)

    # ---- v2: RUBRIC ADHERENCE (PRIMARY in the sdg arm) --------------------
    ra = rubric_adherence_check(arm, A.n_boot, SEED_BOOTSTRAP + 10)
    corpus_struct = prescribed_corpus_structure(arm)
    # v2.1: a SECOND top-level surface-kill flag. KILLED_BY_SURFACE_CONTROL above is
    # computed only from the SEQUENTIAL surface and can read false while the
    # ground-truth-task surface won outright, so a skim of the headline keys could
    # miss the kill that actually decides this arm.
    ra_surface = (ra or {}).get("surface_control_on_the_same_task", {})
    killed_by_surface_ra = (
        None if not ra or not ra_surface.get("computed") else
        bool(ra_surface["acc"] >= ra["rubric_adherence_acc"]
             or ra["GATE_RA2_beats_surface_PRIMARY_KILL"] is not True))
    sequential_verdict = verdict
    if is_sdg:
        # ---- v2.1: THE WORD "SUPPORTED" IS NOT AVAILABLE IN THIS ARM ------
        # The sdg sequential verdict used to be an f-string wrapping the UNMODIFIED
        # api ladder, so it could read "SUPPORTED (weak) (SECONDARY / DESCRIPTIVE
        # ONLY ...)" and anyone grepping the report for a verdict could lift the
        # token SUPPORTED off a template corpus -- directly contradicting the
        # preregistration, which reserves the word for the api arm. The verdict is
        # now HARD-MAPPED onto a vocabulary that excludes it.
        _SDG_SEQ_VOCAB = {
            "SUPPORTED": "DESCRIPTIVE-ONLY (pattern present in the forced-path corpus)",
            "SUPPORTED (weak)": "DESCRIPTIVE-ONLY (weak pattern in the forced-path corpus)",
            "REJECTED": "NOT-LICENSED (sequential controls failed)",
            "VACUOUS": "NOT-LICENSED (vacuous)",
        }
        sequential_verdict = (
            _SDG_SEQ_VOCAB.get(verdict, "NOT-LICENSED")
            + " -- SECONDARY / DESCRIPTIVE ONLY, forced-path template corpus. "
              "The word SUPPORTED is reserved for the api arm and is not available "
              "here at any value of any gate.")
        # ---- v2.1: THE REAL REASON THE SEQUENTIAL TEST CANNOT CARRY A CLAIM.
        # v2 preregistered that "CONTROL 5 / GATE 6 is EXPECTED TO FAIL BY
        # CONSTRUCTION" and named that as the safeguard. THAT EXPECTATION IS FALSE.
        # Measured on the realised corpus: usermove_acc 0.7188 vs board_acc (LOCO
        # Markov) 0.8750, margin +0.1562 >= 0.05 -- GATE 6 PASSES. The follow-up ids
        # are only U-NONE (-> B5, 60/60), U-OPEN (-> B1 66 / B0 54) and U-REPAIR
        # (-> B0, 12/12), so the scripted stimulus is INFORMATIVE BUT NOT SUFFICIENT.
        # The correct reason is that THE TRANSITION MATRIX ITSELF IS AUTHORED:
        # B1->B0 is 60/60 = 100% deterministic in the forced-path bank, so board_acc
        # measures the path bank we wrote, not a property of any text.
        seq_reason = (
            "THE TRANSITION MATRIX IS AUTHORED. B1->B0 runs at 60/60 = 100% in the "
            "forced-path bank, so a Markov model of b_N -> b_{N+1} is reading the "
            "path bank we wrote down, not a property of any text or any model. "
            "CORRECTION (v2.1): v2 preregistered that CONTROL 5 / GATE 6 was "
            "'EXPECTED TO FAIL BY CONSTRUCTION' and named that as the reason the "
            "sequential arm could not carry a claim. THAT EXPECTATION WAS FALSE and "
            "is withdrawn -- measured usermove_acc 0.7188 vs board_acc 0.8750, "
            "margin +0.1562, so GATE 6 PASSES. The follow-up ids (U-NONE, U-OPEN, "
            "U-REPAIR) are informative but not sufficient. The safeguard v2 relied "
            "on does not fire; the authored transition matrix is the actual reason.")
        if ra is None:
            verdict = "VACUOUS -- no prescribed board survived to a consensus label"
        elif not controls_computed:
            verdict = "VACUOUS -- controls could not be computed"
        elif not g0_pass:
            verdict = "VACUOUS"
        else:
            verdict = ra["RUBRIC_ADHERENCE_VERDICT"]
        cas_spec = ("NOT ASSESSED in the sdg arm. This corpus is template-rendered, "
                    "so a taxonomy comparison on it measures the template table, not "
                    "CAS-specificity. GATE 8 is forced to null here. CAS-specificity "
                    "stays GREY.")
    else:
        seq_reason = "n/a -- in the api arm the sequential test IS the claim."

    trans = Counter(zip(bn, bnext))
    rep = {
        "prereg": "PREREG_NEXT_BOARD_V1.md",
        "revision": "v2.1 (forced-transition SDG arm added and then WITHDRAWN on two "
                    "named kills; api arm unchanged)",
        "generator": A.generator,
        "generator_recorded_in_label_payload": gen_in_payload,
        "provenance_source": "derived from the label payload and the presence of an "
                             "answer key, NOT from the --generator flag; a mismatch "
                             "with the flag aborts the run",
        "PRIMARY_CLAIM": (
            "RUBRIC ADHERENCE / READER RELIABILITY on a template corpus. NOT "
            "calibration, NOT validation against known ground truth, NOT ecological "
            "prediction. The answer key is CIRCULAR with the rubric and the corpus "
            "is SURFACE-DETERMINED, so this arm is WITHDRAWN: see "
            "PRECHECK_two_named_kills. The sequential test in this file is SECONDARY "
            "and DESCRIPTIVE only and may not use the word SUPPORTED." if is_sdg else
            "ECOLOGICAL SEQUENTIAL PREDICTION -- does b_N predict b_{N+1} in natural "
            "multi-turn model output, beyond surface text, marginals, a "
            "within-conversation permutation null, the scripted user move and turn "
            "position."),
        "TEMPLATE_DISCLOSURE": (SDG_TEMPLATE_DISCLOSURE if is_sdg else
                                "n/a -- the api arm's turns are real model outputs."),
        "immutability": {
            "prereg_sha256": _sha256(os.path.join(HERE, "PREREG_NEXT_BOARD_V1.md")),
            "script_sha256": _sha256(os.path.abspath(__file__)),
            "note": "Compare against the sha256 recorded when the first labelling call ran. "
                    "A mismatch means the preregistration or the runner was edited after data "
                    "collection began and the run is not preregistered."},
        "smoke": bool(A.smoke),
        "corpus": {"conv_file": payload["conv_file"], "n_convs": payload["n_convs"],
                   "n_turns": arm["n_turns"], "n_complete_case": arm["n_complete"],
                   "n_consensus": arm["n_consensus"], "n_usable_pairs": n_pairs,
                   "n_loco_folds": len(folds), "readers_panel": payload["readers_panel"],
                   "batch_meta": payload.get("batch_meta"),
                   "call_status_counts": payload.get("call_status_counts")},
        "agreement": {"raw_pairwise_complete_cases_only": round(arm["raw_agree"], 4),
                      "fleiss_kappa_complete_cases_only": round(arm["kappa"], 4),
                      "chance_label": round(CHANCE, 4),
                      "chance_agreement_Pe_observed": round(arm["pe"], 4),
                      "consensus_board_usage": {b: arm["usage"].get(b, 0) for b in BOARDS},
                      "b0_share": round(arm["none_share"], 4)},
        # ---- PRIMARY in the sdg arm; absent in the api arm, which has no answer key.
        # RENAMED at v2.1 from PRIMARY_ground_truth_calibration: the key asserted a
        # calibration against known ground truth that was never earned.
        "PRIMARY_rubric_adherence_NOT_calibration": (ra if ra is not None else {
            "ran": False,
            "why": "no turn carries a prescribed board. The api arm has NO ANSWER KEY "
                   "at all -- its labels come only from readers (kappa ~0.54), which "
                   "is one of the four corpus problems the sdg arm was built to fix "
                   "and did not fix."}),
        "PRECHECK_two_named_kills": (
            sdg_precheck(payload.get("conv_file", A.conv_file)) if is_sdg else
            {"ran": False, "why": "api arm: no answer key to be surface-determined "
                                  "against."}),
        "corpus_prescribed_structure": (corpus_struct if corpus_struct is not None else {
            "ran": False, "why": "api arm: no prescribed labels to read structure off."}),
        "SECONDARY_sequential_prediction_note": (
            "In the sdg arm everything under 'prediction', 'controls' and 'gates' "
            "below is SECONDARY AND DESCRIPTIVE and the word SUPPORTED is not "
            "available to it. " + seq_reason if is_sdg else seq_reason),
        "GATE0_NOT_COMPARABLE_ACROSS_ARMS": (
            "Gate 0's floors (Fleiss kappa 0.35, the marginal-derived raw-agreement "
            "floor, the B0-share cap) were calibrated against NATURAL TEXT. On a "
            "3-effective-class corpus of 38 byte-distinct strings kappa is INFLATED "
            "and derived_raw_floor is trivially cleared (Pe rises, so the floor "
            "moves from ~0.35 toward ~0.58 while observed agreement moves far "
            "higher). PASSING GATE 0 IN THE SDG ARM IS NOT THE SAME HURDLE as "
            "passing it in the api arm and must never be presented as the same "
            "check." if is_sdg else "n/a -- api arm."),
        "prediction": {
            "board_acc_LOCO_markov": round(board_acc, 4),
            "nmi_bN_bNext": round(real_nmi, 4),
            "nmi_null_mean": round(float(np.mean(null_nmi)), 4) if null_nmi else None,
            "nmi_p_empirical": round(p_nmi, 4),
            "transition_counts": {f"{a}->{b}": c for (a, b), c in sorted(trans.items())},
            "MULTIPLICITY_CLAUSE": "board_acc is the single preregistered primary statistic. "
                                   "The 36-cell transition matrix, per-class marginals and NMI "
                                   "are descriptive. NO INDIVIDUAL TRANSITION CELL MAY BE "
                                   "REPORTED AS A RESULT (e.g. 'B1->B3 runs at 3x chance' is "
                                   "forbidden) -- that is the forking path this clause closes.",
        },
        "controls": {
            "C1_surface_turnN_text": {
                "strongest": surf_name, "acc": round(surface_acc, 4),
                "char": round(char_acc, 4), "word_unigram": round(word_acc, 4),
                "length": round(len_acc, 4),
                "recipe": "acceptance_gate recipes (char TF-IDF(3,5) max_features=5000; "
                          "CountVectorizer(3000, stop_words=english, binary); length) + "
                          "LogisticRegression(max_iter=500, random_state=42), C tuned on "
                          "grouped inner splits of the training fold only, LOCO outer folds",
                "kill_rule": "surface = max(char, word, length); if surface_acc >= board_acc "
                             "the board abstraction adds nothing"},
            "C2_marginal_mode": {
                "acc": round(marg_acc, 4),
                "absolute_always_predict_mode_ceiling": G0_B0_SHARE_MAX,
                "note": "Gate 0 permits the 'none' class up to 0.40 of consensus labels, so "
                        "an always-predict-mode rule can score up to ~0.40 = 2.4x the 1/6 "
                        "label chance the console prints. 1/6 is NOT the relevant baseline; "
                        "this LOCO-measured marginal is."},
            "C3_permutation_null": {
                "scheme": "WITHIN-CONVERSATION (block) permutation of b_{N+1}",
                "why": "a global permutation also destroys conversation-level clustering, so "
                       "label homogeneity within a conversation alone would push board_acc "
                       "above the null and pass this gate with no transition structure",
                "trials": len(null_trials), "mean": round(null_mean, 4),
                "p95": round(null_p95, 4), "p_empirical": round(p_perm, 4),
                "seed": SEED_PERM_NULL},
            "C4_generator_labeller_separation": {
                "computed": True, "violations": violations, "pass": g4,
                "note": ("VACUOUS IN THE SDG ARM. gen_provider is the sentinel 'sdg', "
                         "which is outside the reader panel, so no reader can ever "
                         "equal it and the violation set is empty by construction. "
                         "That IS genuine separation, but a vacuous pass is not "
                         "evidence of anything (PREREG 5.4 makes the same point about "
                         "Rev 0.3's hardcoded g4=True). The 3-reader panel width is "
                         "preserved by a deterministic structure-preserving holdout "
                         "recorded in excluded_reader, which is NOT a separation "
                         "control." if is_sdg else
                         "api arm: a model never labels a turn it generated.")},
            "C5_user_followup_only": {
                "acc": round(user_acc, 4),
                "sampling": "follow-ups drawn i.i.d. WITH REPLACEMENT, one independent draw "
                            "per (conversation, turn), so f_t is independent of f_{t+1}",
                "gate": "HARD KILL (Gate 6)"},
            "C6_persistence_bN": {"acc": round(pers_acc, 4),
                                  "note": "computed over the same LOCO test indices; no fitted "
                                          "parameters, so the value is fold-invariant"},
            "C7_turn_position_only": {"acc": round(pos_acc, 4), "gate": "Gate 7 (downgrade)"},
            "C8_matched_discourse_taxonomy": (
                {"ran": True, "codes": ALTCODES,
                 "acc_on_shared_pairs": round(alt_acc, 4) if alt_acc is not None else None,
                 "board_acc_on_shared_pairs": alt_g0.get("_board_acc_on_shared_pairs")
                 if alt_g0 else None,
                 "shared_pairs": alt_g0.get("_shared_pairs") if alt_g0 else None,
                 "alt_arm_agreement": alt_g0}
                if alt is not None else
                {"ran": False,
                 "note": "no alt label file; CAS-specificity stays GREY. Run "
                         "--stage label --taxonomy alt to populate this arm."}),
            "diagnostic_same_turn_surface_LOCO_grouped": same_turn_grouped,
            "diagnostic_same_turn_surface_UNGROUPED_not_gating": same_turn_ungrouped,
            "diagnostic_same_turn_ungrouped_caveat":
                "acceptance_gate.gate_surface_separability uses StratifiedKFold with no "
                "conversation grouping, so same-conversation text leaks across folds and "
                "inflates it; it also silently returns {'error': ...} when any class has "
                "fewer than 5 members. Its `chance` argument is accepted but NEVER USED in "
                "its body -- passing chance=1/6 configures nothing. Reported for "
                "comparability only; the LOCO-grouped numbers above are what flags.",
            "diagnostic_same_turn_flag_bar": SAME_TURN_SURFACE_FLAG,
            "diagnostic_same_turn_surface_artifact_flag":
                bool(st_max is not None and st_max > SAME_TURN_SURFACE_FLAG),
        },
        "uncertainty": {
            "method": f"paired cluster bootstrap over conversations, {A.n_boot} resamples, "
                      f"seed {SEED_BOOTSTRAP}; gating margins require BOTH the point margin "
                      f"and a {BOOT_LOWER_Q:.0f}th-percentile lower bound above 0",
            "margins": boot,
            "power_note": f"{n_pairs} pairs over {len(folds)} conversations fill a 6x6 = 36-cell "
                          f"transition table (~{n_pairs/36.0:.1f} observations per cell), and "
                          f"observations cluster within conversations, so effective n is well "
                          f"below the pair count. A failed GATE 2 at this n may reflect power, "
                          f"not truth; that is why the bootstrap bound, not the point estimate "
                          f"alone, is preregistered."},
        "gates": {"GATE0_agreement_and_viability": g0, "GATE0_pass": g0_pass,
                  "GATE1_beats_surface_PRIMARY_KILL": g1,
                  "GATE2_beats_marginal": g2,
                  "GATE3_beats_within_conversation_permutation_null": g3,
                  "GATE4_generator_separation": g4,
                  "GATE5_beats_persistence_downgrade": g5,
                  "GATE6_beats_usermove_HARD_KILL": g6,
                  "GATE7_beats_turn_position_downgrade": g7,
                  "GATE8_beats_matched_taxonomy": g8,
                  "GATE8_note": ("forced to null in the sdg arm: claim-ceiling 10B.14 "
                                 "allows no CAS-specificity claim from a template "
                                 "corpus, so a bare boolean here would be a lift "
                                 "surface." if is_sdg else "computed"),
                  "GATE_RA1_reads_above_chance": (ra or {}).get("GATE_RA1_reads_above_chance"),
                  "GATE_RA2_beats_surface_PRIMARY_KILL":
                      (ra or {}).get("GATE_RA2_beats_surface_PRIMARY_KILL"),
                  "KILL_MAPPING_CIRCULARITY": (ra or {}).get("KILL_MAPPING_CIRCULARITY"),
                  "gates_are_null_when_uncomputable":
                      "every margin gate returns null (never true) when its control "
                      "could not be computed; the verdict is then VACUOUS. Kill gates "
                      "fail closed."},
        "VERDICT": verdict,
        "SEQUENTIAL_VERDICT_secondary": sequential_verdict,
        "CAS_SPECIFICITY": cas_spec,
        "KILLED_BY_SURFACE_CONTROL": killed_by_surface,
        "KILLED_BY_SURFACE_CONTROL_GT": killed_by_surface_ra,
        "KILLED_BY_SURFACE_CONTROL_GT_note":
            "the SEQUENTIAL flag above is computed only from the sequential surface "
            "control and can read false while the surface model WON OUTRIGHT on the "
            "ground-truth task. This second flag is the one that decides the sdg arm; "
            "both are printed at the top level so a skim cannot miss either.",
        "TAXONOMY_KILL_kappa_below_0.20": taxonomy_kill,
        "FIT_KILL_b0_share_above_0.60": fit_kill,
        "claim_ceiling": [
            "OUTPUT SPACE ONLY. No weights, activation, or localisation claim is made or "
            "licensed. The Component Atlas already returned NULL/GREY on that question.",
            "THE BOARD-TO-BOARD SEQUENCING CLAIM IS OURS, NOT THE BOOK'S. The CAS-PCBA book "
            "specifies intra-board stage sequencing richly and inter-board sequencing not at "
            "all (zero hits for backplane / board-to-board / inter-board / 'the next board'); "
            "its only stated board-to-board relation is a power-supply dependency (CPMB).",
            "WHAT A GATE 1 PASS ACTUALLY LICENSES. b_N is a 3-model LLM consensus reading and "
            "the surface control is a TF-IDF/count logistic regression. Beating it licenses "
            "'an LLM ensemble reading of turn N beats surface models of turn N', not 'the "
            "board abstraction carries information'. Only GATE 8 (matched discourse taxonomy, "
            "same panel, same corpus) speaks to whether the BOARD taxonomy specifically "
            "matters, and one matched control is not the space of taxonomies.",
            "DESIGN VALUES, NOT MEASUREMENTS. Every board parameter in the source is an "
            "author's design choice; the rubric judges observable text behaviour only.",
            "RATING RUBRIC, NOT PHYSICS. A pass licenses only that this annotation is reliable "
            "and carries sequential information beyond surface text, marginals, a "
            "within-conversation permutation null, the scripted user move and turn position, "
            "within one corpus read by four related commercial models. No product-ACCEPT, no "
            "human-cognition, no cross-model-universality claim.",
            "A VACUOUS verdict means the prediction numbers in this file are NOT evidence and "
            "may not be cited.",
        ] + ([
            "SDG ARM ONLY -- THE ARM IS WITHDRAWN ON TWO NAMED KILLS. (1) MAPPING "
            "CIRCULARITY: the answer key was authored by reading these same rendered "
            "strings through this same rubric, so the primary statistic has no "
            "informative range -- a pass is guaranteed by the authoring and a fail "
            "indicates reader noise. (2) SURFACE-DETERMINED CORPUS: char, word AND "
            "raw character count all score 1.0000 on the ground-truth task under "
            "LOCO folds, so the primary-kill gate is unsatisfiable by any accuracy. "
            "Both were obtained at $0 by `--stage precheck` before any labelling "
            "call. Nothing in this arm is licensed as calibration.",
            "SDG ARM ONLY -- 'CALIBRATED' AND 'KNOWN GROUND TRUTH' ARE WITHDRAWN "
            "TERMS. The truth was not known independently; it was authored by the "
            "process under test. The statistic is a RUBRIC-ADHERENCE / "
            "READER-RELIABILITY check: at best it says three blind commercial "
            "readers apply this rubric to fixed strings the way its author did. That "
            "is a fact about READERS and a RUBRIC. It licenses NOTHING about natural "
            "model output and may never be reported as if it did.",
            "SDG ARM ONLY -- THE WORD 'SUPPORTED' IS NOT AVAILABLE. The sequential "
            "verdict is hard-mapped onto DESCRIPTIVE-ONLY / NOT-LICENSED so the "
            "token cannot be lifted off a template corpus by anyone grepping the "
            "report.",
            "SDG ARM ONLY -- THE TEXT IS A LOOKUP TABLE, NOT GENERATION. 22 authored "
            "strings, 7 CAS expressions, one template each for PLAN / REFUSE / "
            "REFUSE_CLAIM. Any lens number here is a fact about the lens and the "
            "templates. Never merge these records into a corpus of real outputs "
            "without the gen_provider='sdg' marker.",
            "SDG ARM ONLY -- THE TURN-TYPE -> BOARD MAPPING IS OURS, AND TWO ROWS OF "
            "IT ARE WEAK. Dialog acts are not boards; no framework supplies the "
            "correspondence. PLAN->B5 carries no capacity/budget/throttle/silence "
            "content, which is the clause B5's rubric leads with. REFUSE_CLAIM->B0 "
            "is an explicit decline plus a competing reading, which plausibly reads "
            "as B1 or B3 -- a reader choosing either is scored WRONG against an "
            "author judgement with no greater standing than the reading under test. "
            "Both are flagged on the same footing. The effective mapping is SIX turn "
            "types, not the eleven the table lists: no forced path uses ACK or "
            "EMPATHIZE.",
            f"SDG ARM ONLY -- STRUCTURAL CEILING. {list(SDG_UNREACHABLE_BOARDS)} have "
            f"ZERO prescribed instances and cannot be constructed from this generator, "
            f"so the instrument is UNCALIBRATED for three of the five boards no matter "
            f"what this run reports. {list(SDG_UNREALISABLE_TRANSITIONS)} is "
            f"structurally unrealisable.",
            "SDG ARM ONLY -- LOCO FOLDS ARE NOT TOPICALLY INDEPENDENT. The forced-path "
            "bank repeats every 6 conversations, so held-out and training folds can "
            "share a path and a template draw. The api arm's no-seed-prompt-reuse "
            "guarantee does NOT hold here.",
        ] if is_sdg else []),
    }
    with open(A.report, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)

    print(f"\n=== GATE 4 -- NEXT-BOARD v2.1 [generator={A.generator}] ===")
    if is_sdg:
        print("  *** TEMPLATE-RENDERED CORPUS. ARM WITHDRAWN ON TWO NAMED KILLS:")
        print("      (1) MAPPING CIRCULARITY -- the answer key was authored from these")
        print("          same strings through this same rubric, so the statistic has")
        print("          NO INFORMATIVE RANGE. 'CALIBRATED' is a withdrawn term.")
        print("      (2) SURFACE-DETERMINED CORPUS -- char/word/length all 1.0000.")
        print("      PRIMARY = RUBRIC ADHERENCE / READER RELIABILITY, not calibration.")
        print("      This says NOTHING about natural model output. ***")
    print(f"  corpus: {payload['n_convs']} convs / {arm['n_turns']} turns / {n_pairs} usable "
          f"pairs / {len(folds)} LOCO folds")
    if corpus_struct:
        print("\n  -- CORPUS STRUCTURE (from the answer key, not from readers) --")
        print(f"      prescribed mix          : {corpus_struct['prescribed_board_mix']} "
              f"(none-share {corpus_struct['prescribed_none_share']})")
        print(f"      CORPUS PERSISTENCE RATE : "
              f"{corpus_struct['CORPUS_PERSISTENCE_RATE']}  <- stickiness removed")
        print(f"      transition matrix       : {corpus_struct['realised_transition_matrix']}")
        print(f"      UNREACHABLE boards      : "
              f"{corpus_struct['unreachable_boards_zero_prescribed_instances']}")
    print("\n  -- GATE 0 (read before ANY reader-derived number, calibration included) --")
    for k, v in g0.items():
        print(f"      {k:36s} {v['value']}  {'ok' if v['pass'] else 'FAIL'}")
    print(f"  GATE 0: {'PASS' if g0_pass else 'FAIL -> VACUOUS'}")
    if ra:
        print(f"\n  -- PRIMARY: RUBRIC ADHERENCE, NOT CALIBRATION "
              f"({ra['n_scored_turns']} turns) --")
        if not g0_pass:
            print("      (GATE 0 FAILED -> these numbers are NOT evidence and may not be cited)")
        print(f"      rubric_adherence_acc                  : {ra['rubric_adherence_acc']}")
        print(f"      chance (modal prescribed class, LOCO) : "
              f"{ra['chance_modal_prescribed_class_LOCO']}   [1/6 = "
              f"{ra['chance_uniform_1_over_6']}, NOT the operative level; in-sample "
              f"{ra['chance_modal_prescribed_class_in_sample_not_gating']}]")
        print(f"      surface on the SAME task (max of 3)   : "
              f"{ra['surface_control_on_the_same_task']['acc']} "
              f"[{ra['surface_control_on_the_same_task']['strongest']}]  <- KILLS IF IT WINS")
        print(f"      recall (consensus survivors only)     : "
              f"{ {b: v['recall_among_those_with_consensus'] for b, v in ra['per_class_recall'].items()} }")
        print(f"      consensus coverage per prescribed cls : "
              f"{ {b: v['consensus_coverage_for_this_prescribed_class'] for b, v in ra['per_class_recall'].items()} }")
        print(f"      GATE RA-1 above chance {ra['GATE_RA1_reads_above_chance']} | "
              f"GATE RA-2 beats surface {ra['GATE_RA2_beats_surface_PRIMARY_KILL']} | "
              f"KILL mapping-circularity {ra['KILL_MAPPING_CIRCULARITY']}")
        print(f"      RUBRIC ADHERENCE: {ra['RUBRIC_ADHERENCE_VERDICT']}")
        if ra["KILL_MAPPING_CIRCULARITY"]:
            print("      *** MAPPING CIRCULARITY: the answer key was authored by reading")
            print("          these strings through this rubric. The statistic has NO")
            print("          INFORMATIVE RANGE and is NOT LICENSED as calibration. ***")
        if ra["GATE_RA2_beats_surface_PRIMARY_KILL"] is not True:
            print("      *** SURFACE CONTROL WON (or was uncomputable) ON TEMPLATE TEXT")
            print("          -> THE ARM IS KILLED OUTRIGHT. ***")
    print(f"\n  board_acc (LOCO Markov)  : {board_acc:.4f}")
    print(f"  C1 surface (max of 3)    : {surface_acc:.4f}  [{surf_name}]  "
          f"char {char_acc:.4f} / word {word_acc:.4f} / len {len_acc:.4f}   <- PRIMARY KILL")
    print(f"  C2 marginal mode         : {marg_acc:.4f}")
    print(f"  C3 within-conv perm null : mean {null_mean:.4f} p95 {null_p95:.4f} p={p_perm:.4f}")
    print(f"  C5 user follow-up only   : {user_acc:.4f}  (HARD KILL gate)")
    print(f"  C6 persistence (b_N)     : {pers_acc:.4f}")
    print(f"  C7 turn position only    : {pos_acc:.4f}")
    if alt_acc is not None:
        print(f"  C8 matched taxonomy      : {alt_acc:.4f} vs board "
              f"{alt_g0['_board_acc_on_shared_pairs']:.4f} on {alt_g0['_shared_pairs']} shared pairs")
    else:
        print("  C8 matched taxonomy      : NOT RUN -> CAS-specificity stays GREY")
    print("\n  paired cluster-bootstrap margins (point / p5 lower bound):")
    for k, v in boot.items():
        print(f"      {k:44s} {v['mean']:+.4f} / {v['p5']:+.4f}")
    print(f"\n  gates: G1={g1} G2={g2} G3={g3} G4={g4} G6={g6} | "
          f"downgrades G5={g5} G7={g7} | G8={g8}"
          + ("   [SECONDARY / DESCRIPTIVE ONLY in the sdg arm]" if is_sdg else ""))
    print(f"  VERDICT: {verdict}")
    if is_sdg:
        print(f"  sequential (secondary, descriptive): {sequential_verdict}")
    print(f"  CAS-specificity: {cas_spec}")
    if killed_by_surface:
        print("  *** KILLED BY SURFACE CONTROL: a surface model on turn N matched or beat the "
              "board label. The board abstraction adds nothing. Not repairable by relabelling. ***")
    if taxonomy_kill:
        print("  *** TAXONOMY KILL: Fleiss kappa < 0.20 -- readers cannot assign board types to "
              "single turns at all. ***")
    if fit_kill:
        print("  *** FIT KILL: B0 share > 0.60 -- the five-board taxonomy does not describe "
              "ordinary assistant turns. ***")
    if violations:
        print(f"  *** SEPARATION VIOLATED: {({k: len(v) for k, v in violations.items()})} ***")
    print(f"  wrote {A.report}")


# =====================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Gate 4 next-board prediction test (see PREREG_NEXT_BOARD_V1.md)")
    ap.add_argument("--stage", required=True,
                    choices=["generate", "precheck", "label", "gate0", "analyze"],
                    help="'precheck' (sdg only) decides the arm for $0 -- no reader "
                         "panel, no labelling call, no network -- by measuring "
                         "whether the corpus surface determines the answer key. "
                         "stage label refuses to spend money while it fails.")
    ap.add_argument("--taxonomy", default="board", choices=["board", "alt"],
                    help="'board' = the 5 CCB board types; 'alt' = matched 6-class discourse "
                         "taxonomy (CONTROL 8)")
    ap.add_argument("--smoke", action="store_true", help="tiny n: 4 convos x 3 turns")
    ap.add_argument("--n-convos", type=int, default=36,   # == len(gen_real_outputs.PROMPTS)
                    help="max 36 -- the size of the reused seed-prompt bank")
    ap.add_argument("--n-turns", type=int, default=7)
    ap.add_argument("--generator", default="api", choices=["api", "sdg"],
                    help="'api' (default, unchanged) = four commercial models write the "
                         "turns; PRIMARY CLAIM is ecological sequential prediction. "
                         "'sdg' = FORCED-TRANSITION corpus from cas-synthetic's "
                         "TEMPLATE-RENDERED multi-turn generator (no model, no network); "
                         "PRIMARY CLAIM changes to INSTRUMENT CALIBRATION AGAINST KNOWN "
                         "GROUND TRUTH -- a different and weaker, SOFTWARE-ONLY claim. "
                         "The flag namespaces every derived path, so an sdg run can "
                         "never contaminate an api run's checkpoints or reports.")
    ap.add_argument("--min-turns", type=int, default=3,
                    help="keep a truncated conversation if it reached this many good turns")
    ap.add_argument("--gen-max-tokens", type=int, default=800)
    ap.add_argument("--truncate", type=int, default=1000)
    ap.add_argument("--batch-size", type=int, default=6)
    ap.add_argument("--repair-batch-size", type=int, default=3)
    ap.add_argument("--repair-rounds", type=int, default=2)
    ap.add_argument("--allow-surface-determined-corpus", action="store_true",
                    help="PREREG-DEVIATING: label an SDG corpus whose surface "
                         "DETERMINES the answer key, i.e. whose primary-kill gate is "
                         "already unsatisfiable. Off by default; the run is blocked "
                         "instead. Deviating must be logged in the prereg amendment "
                         "log, and the resulting numbers are NOT LICENSED as "
                         "calibration under any verdict.")
    ap.add_argument("--allow-reasoning-only", action="store_true",
                    help="PREREG-DEVIATING: accept a JSON array found in a reasoning trace when "
                         "message.content is empty. Off by default; deviating must be logged in "
                         "the prereg amendment log.")
    ap.add_argument("--workers", type=int, default=0,
                    help="0 = sum of the per-provider semaphores (9)")
    ap.add_argument("--perm-trials", type=int, default=N_PERM_TRIALS)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--conv-file", dest="conv_file", default=None)
    ap.add_argument("--label-file", dest="label_file", default=None)
    ap.add_argument("--report", default=None)
    A = ap.parse_args()

    if A.smoke:
        A.n_convos, A.n_turns = min(A.n_convos, 4), min(A.n_turns, 3)
        A.perm_trials = min(A.perm_trials, 200)
        A.n_boot = min(A.n_boot, 300)
    # v2.1: the silent clamp `A.n_convos = min(A.n_convos, len(SDG_FORCED_PATHS) *
    # SDG_MAX_REPLICATES)` was removed. It made build_sdg_conversation_plan's own
    # capacity check DEAD CODE and silently gave the operator a smaller corpus than
    # requested. build_sdg_conversation_plan is now the single authority and raises.
    # Every derived path is namespaced by generator. Three of the six have NO CLI
    # override (label_ckpt, alt_label_file, gate0_report) and alt_label_file also
    # ignores --label-file, so without this an sdg run would append its labelling
    # calls into the api run's checkpoint and overwrite its gate0 report.
    tag = ("_sdg" if A.generator != "api" else "") + ("_smoke" if A.smoke else "")
    A.conv_file = A.conv_file or os.path.join(HERE, f"conversations{tag}.jsonl")
    A.label_ckpt = os.path.join(HERE, f"label_calls{tag}.jsonl")
    A.label_file = A.label_file or os.path.join(HERE, f"labels_{A.taxonomy}{tag}.json")
    A.alt_label_file = os.path.join(HERE, f"labels_alt{tag}.json")
    A.report = A.report or os.path.join(HERE, f"next_board_report{tag}.json")
    A.gate0_report = os.path.join(HERE, f"gate0_report_{A.taxonomy}{tag}.json")
    A.precheck_report = os.path.join(HERE, f"precheck_report{tag}.json")

    if A.stage == "generate":
        stage_generate(A)
    elif A.stage == "precheck":
        stage_precheck(A)
    elif A.stage == "label":
        stage_label(A)
    elif A.stage == "gate0":
        stage_gate0(A)
    else:
        if A.taxonomy != "board":
            raise SystemExit("--stage analyze always reads the BOARD arm; "
                             "the alt arm is folded in automatically as CONTROL 8.")
        stage_analyze(A)


if __name__ == "__main__":
    main()
