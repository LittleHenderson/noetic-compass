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

STAGES
    --stage generate                 multi-turn conversations, generator rotated
    --stage label --taxonomy board   3 blind readers per turn; never its generator
    --stage label --taxonomy alt     matched 6-class discourse taxonomy, same panel
    --stage gate0                    agreement/coverage ONLY (read before prediction)
    --stage analyze                  prediction + all controls + all gates

    python next_board_test.py --stage generate --smoke
    python next_board_test.py --stage label --taxonomy board --smoke
    python next_board_test.py --stage gate0 --smoke
    python next_board_test.py --stage analyze --smoke

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


def stage_generate(A):
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


def flatten_turns(convs, truncate):
    """Flat turn list with a stable integer uid used ONLY on the analysis side.

    The uid is never shown to a reader (Rev 0.4 fix): uid = 6*conv_position + turn_idx
    deterministically encodes conversation and turn position, so printing it in the
    prompt leaked position. read_batch emits per-batch ALIAS ids instead.
    """
    turns, uid = [], 0
    for c in convs:
        for t in c["turns"]:
            turns.append({
                "uid": uid, "conv_id": c["conv_id"], "turn_idx": t["turn_idx"],
                "followup_id": t["followup_id"], "gen_provider": c["gen_provider"],
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
    convs = load_conversations(A.conv_file)
    turns = flatten_turns(convs, A.truncate)
    by_uid = {t["uid"]: t for t in turns}
    ckpt = A.label_ckpt
    print(f"[{tax}] labelling {len(turns)} turns from {len(convs)} conversations; "
          f"3 blind readers each (never the turn's own generator)", flush=True)

    jobs, batch_meta = [], []
    for ri, reader in enumerate(ORDER):
        # GATE 4 / requirement 4: a model never labels a turn it generated.
        mine = [t for t in turns if t["gen_provider"] != reader]
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
            want = {t["uid"] for t in turns if t["gen_provider"] != reader}
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
        "truncate": A.truncate, "batch_size": A.batch_size, "readers_panel": MODELS,
        "batch_meta": batch_meta, "call_status_counts": dict(stats),
        "turns": [{k: t[k] for k in ("uid", "conv_id", "turn_idx", "followup_id", "gen_provider")}
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
            if by_uid[uid]["gen_provider"] == prov:      # separation, enforced structurally
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
        readers = [p for p in ORDER if p != meta["gen_provider"]]
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
    g8 = None
    if alt_acc is not None:
        g8 = gate("board_minus_alt_taxonomy_on_shared_pairs",
                  alt_g0["_board_acc_on_shared_pairs"], alt_acc, G8_MARGIN_OVER_ALT_TAXONOMY)

    if not g0_pass:
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

    trans = Counter(zip(bn, bnext))
    rep = {
        "prereg": "PREREG_NEXT_BOARD_V1.md",
        "revision": "Rev 0.4 (post-adversarial-review)",
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
                "computed": True, "violations": violations, "pass": g4},
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
                  "GATE8_beats_matched_taxonomy": g8},
        "VERDICT": verdict,
        "CAS_SPECIFICITY": cas_spec,
        "KILLED_BY_SURFACE_CONTROL": killed_by_surface,
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
        ],
    }
    with open(A.report, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)

    print("\n=== GATE 4 -- NEXT-BOARD PREDICTION v1 (Rev 0.4) ===")
    print(f"  corpus: {payload['n_convs']} convs / {arm['n_turns']} turns / {n_pairs} usable "
          f"pairs / {len(folds)} LOCO folds")
    print("\n  -- GATE 0 (read before any prediction number) --")
    for k, v in g0.items():
        print(f"      {k:36s} {v['value']}  {'ok' if v['pass'] else 'FAIL'}")
    print(f"  GATE 0: {'PASS' if g0_pass else 'FAIL -> VACUOUS'}")
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
          f"downgrades G5={g5} G7={g7} | G8={g8}")
    print(f"  VERDICT: {verdict}")
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
    ap.add_argument("--stage", required=True, choices=["generate", "label", "gate0", "analyze"])
    ap.add_argument("--taxonomy", default="board", choices=["board", "alt"],
                    help="'board' = the 5 CCB board types; 'alt' = matched 6-class discourse "
                         "taxonomy (CONTROL 8)")
    ap.add_argument("--smoke", action="store_true", help="tiny n: 4 convos x 3 turns")
    ap.add_argument("--n-convos", type=int, default=36,   # == len(gen_real_outputs.PROMPTS)
                    help="max 36 -- the size of the reused seed-prompt bank")
    ap.add_argument("--n-turns", type=int, default=7)
    ap.add_argument("--min-turns", type=int, default=3,
                    help="keep a truncated conversation if it reached this many good turns")
    ap.add_argument("--gen-max-tokens", type=int, default=800)
    ap.add_argument("--truncate", type=int, default=1000)
    ap.add_argument("--batch-size", type=int, default=6)
    ap.add_argument("--repair-batch-size", type=int, default=3)
    ap.add_argument("--repair-rounds", type=int, default=2)
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
    tag = "_smoke" if A.smoke else ""
    A.conv_file = A.conv_file or os.path.join(HERE, f"conversations{tag}.jsonl")
    A.label_ckpt = os.path.join(HERE, f"label_calls{tag}.jsonl")
    A.label_file = A.label_file or os.path.join(HERE, f"labels_{A.taxonomy}{tag}.json")
    A.alt_label_file = os.path.join(HERE, f"labels_alt{tag}.json")
    A.report = A.report or os.path.join(HERE, f"next_board_report{tag}.json")
    A.gate0_report = os.path.join(HERE, f"gate0_report_{A.taxonomy}{tag}.json")

    if A.stage == "generate":
        stage_generate(A)
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
