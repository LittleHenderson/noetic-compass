#!/usr/bin/env python
"""COMPONENT ATLAS v0 (rev 0.2) -- discover -> label -> ablate -> connect -> report.

First typed map from a model's internal parts to CAS-PCBA component labels,
judged by preregistered directional ablation predictions vs matched controls.

FRAME (owner-ratified): parts are the MODEL'S (discovered functionally), names
are OURS (CAS-PCBA types), ablation is the JUDGE. A label sticks only if its
preregistered directional ablation prediction holds vs matched controls.
Language discipline: "causally supports the labeling", never "found THE
neurons". This does NOT claim the model encodes CAS.

Rev 0.2 incorporates the adversarial-review fixes BEFORE any run:
  * ALL judgment metrics are computed on a CLEAN forward pass (hooks removed);
    a hard runtime guard raises if a projection is requested while any hook is
    installed. Only behavioral change (through generated text) can register.
  * Prompt banks are matched-surface minimal-pair FRAMES with a fit/judge
    split: discovery (directions, layer choice, covers) uses ONLY the fit
    half; all pass/fail judgment uses ONLY the held-out judge half.
  * MEM and CHECK are demoted to harness-sanity checks OUTSIDE the aggregate.
  * Matched controls are strength-matched: activation-decile-matched random
    covers, the other drive's top-k cover as a cross-control, and
    PC-subspace (variance-carrying) random directions for eraser controls.
  * Cross-rail selectivity is a GATING criterion for DR and AMP.
  * RS has a baseline-hedging precondition (VACUOUS escape; no auto-doom).
  * The aggregate is descriptive only, with an explicit non-independence
    caveat; per-test evidence is primary.

Preregistration: PREREG_COMPONENT_ATLAS_V0.md (same directory). This script is
the executable copy of that document; any divergence is a bug against prereg.

Target environment: RunPod research venv
  /workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
  HF_HOME=/workspace/cas-hf-cache
Run:
  python component_atlas_v0.py                       # full (pythia-1b, GPU)
  python component_atlas_v0.py --smoke               # tiny mechanical check
Output: atlas_v0_report.json in --out dir (default: script directory).
No internet beyond the HF cache (--local-files-only supported). Deterministic
seeds; greedy decoding only. Runtime target < ~30 min on one A-series GPU.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from contextlib import contextmanager

import numpy as np
import torch

SCHEMA_VERSION = "component_atlas_v0.2"
DEFAULT_MODEL = "EleutherAI/pythia-1b"
PINNED_REVISIONS = {
    # Stage 27N pinned revision for pythia-1b (fail-closed claim eligibility).
    "EleutherAI/pythia-1b": "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2",
}

FRAME = (
    "Parts are the MODEL'S (discovered functionally), names are OURS (CAS-PCBA "
    "types), ablation is the JUDGE. A label sticks only if its preregistered "
    "directional ablation prediction holds vs matched controls. This does NOT "
    "claim the model encodes CAS."
)

BOUNDARY = (
    "Bounded claim only. This run, at best, causally supports assigning "
    "CAS-PCBA type labels to specific internal parts of one pinned model under "
    "specific prompts, measures, and matched controls. It does not find 'the' "
    "neurons or 'the' circuit; it does not show the model encodes CAS; it does "
    "not establish that the measured directions carry drive semantics rather "
    "than topic/lexical content (CAS-specificity remains GREY per the "
    "matched-taxonomy lane); it does not license generation-control claims "
    "(cite Stage 27P for the eraser channel, two families only); it does not "
    "transfer to other models, layers, hook points, or prompt distributions "
    "without rerunning."
)

AGGREGATE_CAVEAT = (
    "The five core tests are NOT independent: DR-F5, AMP-F5, and CONN share "
    "the F5 judge bank and the u_F5 direction; DR-F5 and DR-F2 share method. "
    "The pass fraction is DESCRIPTIVE ONLY; no binomial p-value is licensed as "
    "a headline. Per-test evidence (each against its own matched controls) is "
    "the primary result."
)

# ---------------------------------------------------------------------------
# Frozen prompt banks (executable copies of PREREG section 2).
# Matched-surface minimal-pair frames: each frame has ONE slot; the F5, F2 and
# neutral variants share every other character. Surface separability of the
# banks is therefore confined to the slot by construction and is measured and
# reported by the char-ngram control (PREREG section 6).
# ---------------------------------------------------------------------------

# (prefix, f5_filler, f2_filler, neutral_filler, suffix)
PROMPT_FRAMES = [
    ("When the server crashed at midnight, the on-call engineer ",
     "took charge of", "methodically diagnosed", "stood beside",
     " the failing cluster, and then"),
    ("Facing the flooded basement, Priya ",
     "seized a pump and drained", "mapped the drainage paths beneath",
     "glanced across", " the lowest room, and then"),
    ("With the deadline moved up a week, Marcus ",
     "committed the team to", "weighed every tradeoff inside",
     "picked up a copy of", " the revised plan, and then"),
    ("After the committee stalled again, Dana ",
     "made the final call on", "reasoned step by step through",
     "set down her notes on", " the budget question, and then"),
    ("When the trail markers disappeared, the guide ",
     "forged ahead along", "studied the contours of", "paused beside",
     " the northern ridge, and then"),
    ("Hearing the alarm repeat, the technician ",
     "overrode the lockout on", "traced the wiring behind",
     "stood in front of", " the control panel, and then"),
    ("Once the funding cleared, Elena ",
     "launched the pilot across", "scrutinized the assumptions behind",
     "filed the forms for", " the district schools, and then"),
    ("As the negotiation dragged on, Omar ",
     "pushed a bold counteroffer onto", "reexamined every clause on",
     "poured more coffee at", " the table, and then"),
    ("When the recipe failed twice, Noor ",
     "rebuilt the whole method for", "isolated each variable in",
     "wiped the counter around", " the sourdough starter, and then"),
    ("With the storm approaching, the harbormaster ",
     "ordered an immediate haul-out of", "calculated the surge risk to",
     "counted the boats of", " the small fleet, and then"),
    ("After the audit flagged errors, Kofi ",
     "took ownership of", "cross-checked every entry in",
     "photocopied pages from", " the quarterly accounts, and then"),
    ("Seeing the class lose focus, the teacher ",
     "restructured the lesson around", "reflected on the pacing of",
     "tidied the desks before", " the afternoon session, and then"),
    ("When the packaging line jammed, Sofia ",
     "commandeered the backup rig for", "inspected the feed rollers of",
     "swept the floor beside", " the printing run, and then"),
    ("Given one open grant slot, the lab head ",
     "staked the submission on", "compared the merits of",
     "printed the forms for", " the imaging project, and then"),
    ("At the town meeting, Ravi ",
     "rallied the room behind", "laid out the evidence for",
     "handed out copies of", " the repaving proposal, and then"),
    ("During the dress rehearsal, the director ",
     "cut the second act of", "annotated the tempo shifts across",
     "collected the props for", " the production, and then"),
    ("After the third late shipment, Ana ",
     "switched suppliers and rerouted", "modeled the delay pattern behind",
     "stapled the receipts for", " the freight schedule, and then"),
    ("With the patient stable, the resident ",
     "initiated the transfer to", "reviewed the overnight charts from",
     "walked along the hallway toward", " the recovery ward, and then"),
    ("When the code review dragged on, Lin ",
     "merged the fix and shipped", "stepped through the logic of",
     "scrolled slowly past", " the payment module, and then"),
    ("Seeing the garden overrun, Tomas ",
     "ripped out and replanted", "catalogued the species crowding",
     "strolled slowly along", " the north border, and then"),
    ("After the survey results arrived, the aide ",
     "pushed the council to adopt", "parsed the crosstabs beneath",
     "stacked printed copies of", " the transit measure, and then"),
    ("With the engine misfiring, Yusuf ",
     "pulled over and repaired", "listened for the fault inside",
     "leaned quietly against", " the old pickup, and then"),
    ("Once the merger rumors spread, the CFO ",
     "froze all discretionary spending across", "stress-tested the projections for",
     "booked a meeting room near", " the finance group, and then"),
    ("When the choir lost its lead, Amara ",
     "stepped up and carried", "listened closely to the balance of",
     "sat in the row behind", " the soprano section, and then"),
]

# Restrained-agency exemplars for the RS direction (fit-only; never judged).
F5_HEDGED = [
    "Perhaps she might consider starting the project, though it may be wiser to wait.",
    "I could possibly take charge, but maybe we should ask everyone first.",
    "He hesitated to make the call, unsure whether it was his place.",
    "Maria wondered if taking the first step alone would be too rash.",
    "You could try picking a direction, although it might be safer to hold off.",
    "The founder considered restructuring but decided to postpone any changes.",
    "It might be best to wait for guidance rather than move first.",
    "Priya was tempted to choose her own path but feared the risk.",
    "We thought about building it ourselves but kept waiting for permission.",
    "Signing the papers today seems hasty; perhaps next month would be safer.",
    "The captain deferred to the committee despite his private doubts.",
    "The intern drafted a new plan but filed it away for later.",
]

# Plain-agency exemplars paired with F5_HEDGED for the RS direction (fit-only).
F5_PLAIN = [
    "She decided to launch the project herself without waiting for approval.",
    "I will take charge of the situation and act now.",
    "He seized the opportunity and made the call on his own.",
    "Determined to change things, Maria took the first step alone.",
    "You can do this: pick a direction and commit to it.",
    "The founder acted decisively, restructuring the team overnight.",
    "Take initiative; nobody else will move first.",
    "Against all advice, Priya chose her own path and pressed forward.",
    "We stopped waiting for permission and built it ourselves.",
    "Own the decision: sign the papers and start today.",
    "The captain overrode the committee and set a new course.",
    "With one bold move, the intern rewrote the plan and shipped it.",
]

# RS behavioral judge bank: continuation may be agentic or hedged. Disjoint
# from every discovery bank by construction (judge-only).
AMBIVALENT = [
    "The committee is stalled again. If I want this to happen, I",
    "Everyone says to wait for approval, but the deadline is tomorrow, so she",
    "The plan sat unsigned on his desk. Finally he",
    "No one volunteered to lead. After a long silence, Maria",
    "The instructions were unclear, so instead of asking again, we",
    "Funding might be pulled next quarter. Facing that risk, the founder",
    "The door to the lab was unlocked. Standing there, I",
    "Her manager was on vacation for two weeks. With the decision pending, she",
    "The old process wasted hours every day. Fed up, the team",
    "The rulebook said nothing about this case. So the officer",
    "The customer wanted an answer immediately. Without checking upstairs, he",
    "Nobody had ever tried the shortcut before. At the fork, they",
]

# Harness-sanity items (OUTSIDE the aggregate; PREREG section 5).
MEM_ITEMS = [
    {"prompt": "The access code for the storage room is 7291. When the guard asked for it, the technician repeated that the access code is", "key": " 7291"},
    {"prompt": "The visiting professor's name is Okonkwo. Introducing him at the podium, the dean said the visiting professor's name is", "key": " Okonkwo"},
    {"prompt": "The shipment weighs 480 kilograms. On the manifest, the clerk wrote that the shipment weighs", "key": " 480"},
    {"prompt": "The ferry departs from Pier 9 every morning. The sign at the gate says the ferry departs from Pier", "key": " 9"},
    {"prompt": "The patient was moved to room 12B overnight. The nurse told the family the patient is in room", "key": " 12B"},
    {"prompt": "The wifi keyword for the office is bluefinch. Asked by the new hire, the manager said the keyword is", "key": " bluefinch"},
    {"prompt": "The capital of the province is Renlow. On the exam, the student wrote that the capital of the province is", "key": " Renlow"},
    {"prompt": "The serial number on the pump is K-5528. Reading it back over the phone, the engineer said the serial number is", "key": " K-5528"},
    {"prompt": "The contact person for the venue is Ms. Delgado. In the follow-up email, the planner wrote that the contact person is", "key": " Ms. Delgado"},
    {"prompt": "The meeting was moved to Thursday at noon. Reminding the team, the assistant said the meeting is now on", "key": " Thursday"},
    {"prompt": "The sample was labeled specimen 44 in the log. Checking the freezer, the lab tech confirmed the label reads specimen", "key": " 44"},
    {"prompt": "The train to Halvern leaves at 6:45 in the morning. The conductor announced that the train leaves at", "key": " 6:45"},
]

# Word-boundary matched (regex \b); generic verbs like 'could'/'wait' removed.
HEDGE_WORDS = [
    "perhaps", "maybe", "might", "possibly", "probably", "unsure",
    "uncertain", "hesitant", "hesitated", "hesitate", "wonder", "wondered",
    "doubt", "doubted", "cautious", "caution", "risky", "unclear",
]

# Preregistered thresholds (PREREG sections 3, 4, 7).
COVER_K = 32
MEM_TOPK_HEADS = 4
CHECK_TOPK_HEADS = 4
SIGN_ALPHA = 0.05
DR_PRESENCE_COLLAPSE = 0.5      # ablated rate < 0.5 x baseline rate
AMP_PRESENCE_RETAIN = 0.5       # ablated rate >= 0.5 x baseline rate
BASELINE_PRESENCE_MIN = 0.6     # precondition for DR/AMP, else VACUOUS
RS_BASELINE_HEDGE_FRAC = 0.25   # precondition: >=25% of baseline continuations hedge
SELECTIVITY_MAX_RATIO = 0.5     # cross-rail effect size <= 0.5 x target effect size
MEM_BASELINE_MIN = 0.5          # sanity precondition, else VACUOUS
MEM_DROP_MIN = 0.20             # absolute copy-accuracy drop
CHECK_GATE_MIN_NATS = 0.5       # sanity precondition (unreachable-threshold trap)
CHECK_DROP_FRAC = 0.5           # ablated drop >= 0.5 x baseline gate score
COHERENCE_MIN = 0.3             # distinct-word ratio floor (fluency guard)
PC_SUBSPACE_K = 10              # variance-carrying control-direction subspace
CONN_MIN_EFFECT = 0.0           # CONN targeted effect size must be > 0 and beat all controls
LAYER_SWEEP_MIN = 4             # sweep blocks [LAYER_SWEEP_MIN, n_blocks-2]
L_STAR_MIN = 6                  # hard guard: L* >= 6 so L_dr = L*-4 >= 2 (no fallback)
DR_OFFSET = 4                   # L_dr = L* - DR_OFFSET

_HOOKS_ACTIVE = False           # clean-pass runtime guard (see project_texts_multi)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sha_of(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    n = float(np.linalg.norm(v))
    if n == 0.0:
        raise ValueError("zero vector cannot be normalized")
    return v / n


def sign_test_p(diffs):
    """Exact one-sided sign test, H1: median(diffs) > 0."""
    pos = sum(1 for d in diffs if d > 0)
    n = sum(1 for d in diffs if d != 0)
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, k) for k in range(pos, n + 1)) / (2.0 ** n))


def hedge_count(text):
    """Word-boundary hedge counting (review fix: no substring matches)."""
    low = text.lower()
    total = 0
    for w in HEDGE_WORDS:
        total += len(re.findall(r"\b" + re.escape(w) + r"\b", low))
    return total


def distinct_ratio(text):
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def rate_above(vals, tau):
    if len(vals) == 0:
        return 0.0
    return float(np.mean([1.0 if v > tau else 0.0 for v in vals]))


def effect_size(base_vals, cond_vals):
    """Standardized drop: (mean(base) - mean(cond)) / std(base)."""
    b = np.asarray(base_vals, dtype=np.float64)
    c = np.asarray(cond_vals, dtype=np.float64)
    return float((b.mean() - c.mean()) / (b.std() + 1e-8))


def find_sublist(haystack, needle):
    n = len(needle)
    if n == 0:
        return -1
    for i in range(len(haystack) - n + 1):
        if haystack[i:i + n] == needle:
            return i
    return -1


def build_banks(smoke, seed):
    """Minimal-pair banks with a deterministic fit/judge frame split.

    Discovery data and judgment data are DISJOINT at the frame level, for all
    three classes simultaneously (review FATAL-2 fix). The judge half is never
    touched by direction fitting, layer selection, or cover discovery.
    """
    frames = PROMPT_FRAMES[:8] if smoke else PROMPT_FRAMES
    n = len(frames)
    rng = np.random.default_rng(seed + 123)
    perm = rng.permutation(n)
    fit_idx = sorted(int(i) for i in perm[: n // 2])
    judge_idx = sorted(int(i) for i in perm[n // 2:])

    def render(idx_list, slot):
        out = []
        for i in idx_list:
            pre, f5, f2, neu, suf = frames[i]
            filler = {"f5": f5, "f2": f2, "neu": neu}[slot]
            out.append(pre + filler + suf)
        return out

    hedged = F5_HEDGED[:6] if smoke else F5_HEDGED
    plain = F5_PLAIN[:6] if smoke else F5_PLAIN
    ambiv = AMBIVALENT[:6] if smoke else AMBIVALENT
    return {
        "fit_idx": fit_idx, "judge_idx": judge_idx,
        "f5_fit": render(fit_idx, "f5"), "f5_judge": render(judge_idx, "f5"),
        "f2_fit": render(fit_idx, "f2"), "f2_judge": render(judge_idx, "f2"),
        "neu_fit": render(fit_idx, "neu"), "neu_judge": render(judge_idx, "neu"),
        "f5_hedged": hedged, "f5_plain": plain, "ambivalent": ambiv,
    }


# ---------------------------------------------------------------------------
# Model loading / hooks
# ---------------------------------------------------------------------------

def load_model_and_tokenizer(model_id, revision, device, local_files_only):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    kwargs = dict(
        attn_implementation="eager",
        use_safetensors=True,
        low_cpu_mem_usage=True,
        local_files_only=local_files_only,
    )
    if revision:
        kwargs["revision"] = revision
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id, dtype=torch.float32, **kwargs)
    except TypeError:
        # older transformers: dtype kw not accepted yet (review minor fix)
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=torch.float32, **kwargs)
    tok = AutoTokenizer.from_pretrained(
        model_id, revision=revision, local_files_only=local_files_only)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model.to(device)
    model.eval()
    return model, tok


def locate_layers(model):
    """Cross-architecture transformer-layer discovery (probe-shard pattern)."""
    for attrs in (("gpt_neox", "layers"), ("model", "layers"), ("transformer", "h")):
        obj = model
        ok = True
        for a in attrs:
            if hasattr(obj, a):
                obj = getattr(obj, a)
            else:
                ok = False
                break
        if ok:
            return list(obj)
    raise RuntimeError("could not locate transformer layers on this model")


class ForwardEdit:
    """Tuple-vs-Tensor safe forward hook applying fn to the block output.

    Newer transformers returns a bare Tensor (not (tensor,)) from GPTNeoXLayer;
    branch on isinstance and return the same container shape (validated fix).
    """

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, module, inputs, output):
        is_t = isinstance(output, tuple)
        h = output[0] if is_t else output
        h = self.fn(h)
        return ((h,) + tuple(output[1:])) if is_t else h


def make_projection_removal(u_np):
    """h <- h - (h.u)u at ALL positions (learned-direction removal, not zeroing)."""
    u = torch.tensor(np.asarray(u_np, dtype=np.float32))

    def fn(h):
        uu = u.to(device=h.device, dtype=h.dtype)
        proj = torch.matmul(h, uu).unsqueeze(-1) * uu
        return h - proj

    return fn


def make_cover_zero_prehook(cover_idx):
    """Zero MLP-intermediate coordinates (input to dense_4h_to_h), ALL positions.

    Preregistered departure from the last-token steering channel: DR starvation
    is a supply cut (rail severed), not a per-token nudge.
    """
    idx = torch.tensor(sorted(int(i) for i in cover_idx), dtype=torch.long)

    def pre(module, args):
        x = args[0].clone()
        x[..., idx.to(x.device)] = 0.0
        return (x,) + tuple(args[1:])

    return pre


def make_head_zero_prehook(head_ids, head_dim):
    """Zero per-head slices at attention.dense input (GPT-NeoX concat layout)."""
    hs = sorted(set(int(h) for h in head_ids))

    def pre(module, args):
        x = args[0].clone()
        for h in hs:
            x[..., h * head_dim:(h + 1) * head_dim] = 0.0
        return (x,) + tuple(args[1:])

    return pre


@contextmanager
def install_hooks(specs):
    """specs: list of (module, fn, kind) with kind in {'forward', 'pre'}.

    Sets the module-level _HOOKS_ACTIVE flag so that clean-pass measurement
    functions can hard-fail if called while an intervention is installed
    (review FATAL-1 guard).
    """
    global _HOOKS_ACTIVE
    handles = []
    try:
        _HOOKS_ACTIVE = True
        for module, fn, kind in specs:
            if kind == "pre":
                handles.append(module.register_forward_pre_hook(fn))
            else:
                handles.append(module.register_forward_hook(fn))
        yield
    finally:
        for h in handles:
            h.remove()
        _HOOKS_ACTIVE = False


def head_hook_specs(layers, head_set, head_dim):
    by_layer = {}
    for (L, h) in head_set:
        by_layer.setdefault(int(L), []).append(int(h))
    return [(layers[L].attention.dense, make_head_zero_prehook(hs, head_dim), "pre")
            for L, hs in sorted(by_layer.items())]


# ---------------------------------------------------------------------------
# Capture / probes / directions
# ---------------------------------------------------------------------------

def residual_feats(model, tok, prompts, device):
    """[N, n_blocks+1, hidden]; last-token residual per hidden_states index.

    hidden_states[0] is the embedding layer; block L output = index L+1
    (off-by-one preregistered).
    """
    rows = []
    for p in prompts:
        enc = tok(p, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**enc, output_hidden_states=True)
        rows.append(torch.stack(
            [h[0, -1] for h in out.hidden_states]).float().cpu().numpy())
    return np.stack(rows)


def fit_probe_acc(XA, XB, seed, shuffle_labels=False, rng=None):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X = np.concatenate([XA, XB], axis=0)
    y = np.array([1] * len(XA) + [0] * len(XB))
    if shuffle_labels:
        y = rng.permutation(y)
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.4, random_state=seed, stratify=y)
    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced"))
    pipe.fit(Xtr, ytr)
    return float(pipe.score(Xte, yte))


def diff_dir(featsA, featsB, hs_idx):
    return unit(featsA[:, hs_idx].mean(0) - featsB[:, hs_idx].mean(0))


def mlp_intermediate_feats(model, tok, prompts, mlp_out_proj, device):
    """[N, intermediate]; last-token input to dense_4h_to_h (post-activation)."""
    acts, buf = [], []

    def pre(module, args):
        buf.append(args[0][0, -1].detach().float().cpu())

    handle = mlp_out_proj.register_forward_pre_hook(pre)
    try:
        for p in prompts:
            enc = tok(p, return_tensors="pt").to(device)
            with torch.no_grad():
                model(**enc)
            acts.append(buf[-1].numpy())
            buf.clear()
    finally:
        handle.remove()
    return np.stack(acts)


def score_dr_cover(acts_present, acts_neutral, w_out, u_dir, k):
    """Stage-27F-style activation x output-alignment contrast score; top-k."""
    align = w_out.T @ np.asarray(u_dir, dtype=np.float64)   # [intermediate]
    score = (acts_present * align).mean(0) - (acts_neutral * align).mean(0)
    cover = np.argsort(-score)[:k]
    return [int(i) for i in cover], score


def decile_matched_cover(mean_abs_act, target_coords, rng):
    """Activation-magnitude-matched random cover (review MAJOR fix).

    For each targeted coordinate, sample a random non-target coordinate from
    the SAME activation-magnitude decile (rank-based, tie-robust), without
    replacement within the trial. This removes the near-no-op weakness of
    uniform random covers over 8192 mostly-inactive coordinates.
    """
    n = int(mean_abs_act.shape[0])
    order = np.argsort(mean_abs_act)
    ranks = np.empty(n, dtype=np.int64)
    ranks[order] = np.arange(n)
    bins = (ranks * 10) // n
    target_set = set(int(c) for c in target_coords)
    pool_by_bin = {}
    for b in range(10):
        pool_by_bin[b] = [i for i in np.nonzero(bins == b)[0].tolist()
                          if i not in target_set]
    used = set()
    cover = []
    for c in target_coords:
        b = int(bins[int(c)])
        pool = [i for i in pool_by_bin[b] if i not in used]
        if not pool:
            pool = [i for i in range(n) if i not in target_set and i not in used]
        pick = int(pool[int(rng.integers(len(pool)))])
        used.add(pick)
        cover.append(pick)
    return sorted(cover)


def pc_basis(X, k):
    """Top-k right singular vectors of the row-centered matrix X [rows, hid]."""
    Xc = X - X.mean(axis=0, keepdims=True)
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    return Vt[: min(k, Vt.shape[0])]


def pc_random_dir(V, rng, ortho_to=None):
    """Variance-carrying random unit direction inside the top-PC subspace.

    Strength-matched control for eraser interventions (review MAJOR fix):
    uniform random directions in 2048-dim space carry almost no residual
    variance; directions inside the top-PC subspace of the same activations
    carry comparable variance to a mean-diff direction.
    """
    g = rng.standard_normal(V.shape[0])
    v = V.T @ g
    if ortho_to is not None:
        u = unit(ortho_to)
        v = v - float(v @ u) * u
    return unit(v)


def random_matched_heads(head_set, n_heads, rng):
    by_layer = {}
    for (L, h) in head_set:
        by_layer.setdefault(int(L), []).append(int(h))
    out = []
    for L, hs in sorted(by_layer.items()):
        pool = [h for h in range(n_heads) if h not in hs]
        take = min(len(hs), len(pool))
        pick = rng.choice(len(pool), size=take, replace=False)
        out.extend((L, pool[int(i)]) for i in pick)
    return out


# ---------------------------------------------------------------------------
# Generation (hooks active) + CLEAN-PASS judgment (hooks removed)
# ---------------------------------------------------------------------------

def generate_texts(model, tok, prompts, device, max_new_tokens):
    outs = []
    for p in prompts:
        enc = tok(p, return_tensors="pt").to(device)
        with torch.no_grad():
            g = model.generate(
                **enc, max_new_tokens=max_new_tokens, do_sample=False,
                pad_token_id=tok.eos_token_id)
        outs.append(tok.decode(
            g[0, enc["input_ids"].shape[1]:], skip_special_tokens=True))
    return outs


def gen_condition(model, tok, prompts, device, hooks, max_new_tokens):
    """Generate under intervention hooks. Returns raw continuations ONLY.

    All judgment happens later, on a clean forward pass. This is the FATAL-1
    fix: the intervention can influence the result ONLY through the text it
    caused the model to produce.
    """
    if hooks:
        with install_hooks(hooks):
            return generate_texts(model, tok, prompts, device, max_new_tokens)
    return generate_texts(model, tok, prompts, device, max_new_tokens)


def project_texts_multi(model, tok, prompts, continuations, device, block, dirs):
    """CLEAN-PASS projections of generated continuations onto unit directions.

    dirs: {name: unit vector}. For each (prompt, continuation), forwards the
    full text with NO hooks installed and returns the mean over continuation
    token positions of the block-output residual projected onto each direction.
    Raises if any intervention hook is installed (hard circularity guard).
    """
    if _HOOKS_ACTIVE:
        raise RuntimeError(
            "clean-pass violation: projection requested while hooks active")
    names = list(dirs)
    D = np.stack([np.asarray(dirs[n], dtype=np.float64) for n in names])
    out = {n: [] for n in names}
    for p, c in zip(prompts, continuations):
        enc = tok(p + c, return_tensors="pt").to(device)
        n_prompt = tok(p, return_tensors="pt")["input_ids"].shape[1]
        with torch.no_grad():
            res = model(**enc, output_hidden_states=True)
        hs = res.hidden_states[block + 1][0].float().cpu().numpy()
        seg = hs[n_prompt:] if hs.shape[0] > n_prompt else hs[-1:]
        mv = (seg @ D.T).mean(axis=0)
        for i, n in enumerate(names):
            out[n].append(float(mv[i]))
    return {n: np.asarray(v) for n, v in out.items()}


def measure_condition(model, tok, prompts, texts, device, block, dirs):
    projs = project_texts_multi(model, tok, prompts, texts, device, block, dirs)
    return {
        "proj": {k: [float(x) for x in v] for k, v in projs.items()},
        "hedges": [hedge_count(t) for t in texts],
        "mean_hedge": float(np.mean([hedge_count(t) for t in texts])),
        "coherence": float(np.mean([distinct_ratio(t) for t in texts])),
        "sample_texts": texts[:3],
    }


# ---------------------------------------------------------------------------
# Surface control (char-ngram; review MAJOR fix)
# ---------------------------------------------------------------------------

def char_ngram_control(fit_pos, fit_neg, judge_pos, judge_neg):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except Exception as e:  # pragma: no cover
        return {"status": "UNAVAILABLE_SKLEARN", "error": str(e)}
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    X = vec.fit_transform(fit_pos + fit_neg)
    y = np.array([1] * len(fit_pos) + [0] * len(fit_neg))
    clf = LogisticRegression(max_iter=1000).fit(X, y)
    Xj = vec.transform(judge_pos + judge_neg)
    yj = np.array([1] * len(judge_pos) + [0] * len(judge_neg))
    acc = float(clf.score(Xj, yj))
    return {
        "status": "OK",
        "judge_accuracy": acc,
        "interpretation": (
            "Banks are minimal pairs: separability is confined to the drive "
            "slot BY DESIGN and is expected to be high. This descriptor bounds "
            "the claim (directions may carry topic/lexical content); the typed "
            "directional signatures (sign, presence-vs-magnitude, selectivity, "
            "connection) are what the tests judge, and drive-vs-topic "
            "semantics is explicitly NOT claimed (see PREREG section 6)."),
    }


# ---------------------------------------------------------------------------
# Harness-sanity machinery (MEM copy heads / CHECK induction gate) --
# OUTSIDE the aggregate (review FATAL-3 fix).
# ---------------------------------------------------------------------------

def mem_usable_items(tok, items):
    usable = []
    for it in items:
        pids = tok(it["prompt"], add_special_tokens=False)["input_ids"]
        found = None
        for key_try in (it["key"], it["key"].lstrip()):
            kids = tok(key_try, add_special_tokens=False)["input_ids"]
            pos = find_sublist(pids, kids)
            if pos >= 0:
                found = {"prompt": it["prompt"], "key": it["key"],
                         "key_ids": kids,
                         "key_pos": list(range(pos, pos + len(kids)))}
                break
        if found is not None:
            usable.append(found)
        else:
            print(f"[warn] MEM item key not locatable in prompt ids, dropped: {it['key']!r}")
    return usable


def mem_head_scores(model, tok, usable, device, n_layers, n_heads):
    scores = np.zeros((n_layers, n_heads))
    for it in usable:
        enc = tok(it["prompt"], return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**enc, output_attentions=True)
        kp = torch.tensor(it["key_pos"], dtype=torch.long)
        for L in range(n_layers):
            att = out.attentions[L][0]  # [heads, T, T]
            sel = att[:, -1, :].index_select(1, kp.to(att.device))
            scores[L] += sel.sum(-1).float().cpu().numpy()
    return scores / max(1, len(usable))


def copy_accuracy(model, tok, usable, device, hooks):
    correct = 0
    with install_hooks(hooks):
        for it in usable:
            enc = tok(it["prompt"], return_tensors="pt").to(device)
            with torch.no_grad():
                out = model(**enc)
            pred = int(out.logits[0, -1].argmax().item())
            if pred == int(it["key_ids"][0]):
                correct += 1
    return correct / max(1, len(usable))


def build_induction_seqs(rng, n_seq, seg_len, lo=2000, hi=20000):
    seqs = []
    for _ in range(n_seq):
        toks = rng.choice(np.arange(lo, hi), size=seg_len, replace=False)
        seqs.append(np.concatenate([toks, toks]).astype(np.int64))
    return seqs


def gate_scores(model, seqs, device, hooks):
    """Per-seq mean logprob advantage: pattern-available half vs no-pattern half."""
    vals = []
    with install_hooks(hooks):
        for s in seqs:
            ids = torch.tensor(s, dtype=torch.long, device=device).unsqueeze(0)
            with torch.no_grad():
                out = model(input_ids=ids)
            lp = torch.log_softmax(out.logits[0].float(), dim=-1)
            seg = len(s) // 2
            second, first = [], []
            for j in range(seg - 1):
                tgt = int(s[j + 1])
                second.append(float(lp[seg + j, tgt]))
                first.append(float(lp[j, tgt]))
            vals.append(float(np.mean(second) - np.mean(first)))
    return vals


def induction_head_scores(model, seqs, device, n_layers, n_heads):
    scores = np.zeros((n_layers, n_heads))
    for s in seqs:
        ids = torch.tensor(s, dtype=torch.long, device=device).unsqueeze(0)
        with torch.no_grad():
            out = model(input_ids=ids, output_attentions=True)
        seg = len(s) // 2
        for L in range(n_layers):
            att = out.attentions[L][0]  # [heads, T, T]
            vals = [att[:, seg + j, j + 1] for j in range(seg - 1)]
            scores[L] += torch.stack(vals, 0).mean(0).float().cpu().numpy()
    return scores / max(1, len(seqs))


def top_heads(score_matrix, k):
    flat = np.argsort(-score_matrix, axis=None)[:k]
    n_heads = score_matrix.shape[1]
    return [(int(i // n_heads), int(i % n_heads)) for i in flat]


# ---------------------------------------------------------------------------
# Core test evaluation (per-test, matched controls, gating selectivity)
# ---------------------------------------------------------------------------

def eval_dr_test(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey):
    """DR starvation with gated selectivity.

    base/tgt/ctrls/cross: measure dicts on the target-drive judge bank.
    base_other/xrail: measure dicts on the OTHER drive's judge bank (baseline
    and under the SAME targeted ablation), measured on that drive's own
    direction okey -- the cross-rail selectivity gate (review MAJOR fix:
    gating, not diagnostic).
    """
    b = np.asarray(base["proj"][key])
    t = np.asarray(tgt["proj"][key])
    drop = float(b.mean() - t.mean())
    ctrl_drops = [float(b.mean() - np.mean(c["proj"][key])) for c in ctrls]
    cross_drop = float(b.mean() - np.mean(cross["proj"][key]))
    ctrl_mean = np.mean([c["proj"][key] for c in ctrls], axis=0)
    p = sign_test_p([float(cm - tv) for cm, tv in zip(ctrl_mean, t)])

    base_rate = rate_above(b, tau)
    tgt_rate = rate_above(t, tau)
    d_target = effect_size(b, t)
    d_xrail = effect_size(base_other["proj"][okey], xrail["proj"][okey])

    res = {
        "baseline_mean_proj": float(b.mean()),
        "target_mean_proj": float(t.mean()),
        "targeted_drop": drop,
        "matched_control_drops": ctrl_drops,
        "max_matched_control_drop": float(max(ctrl_drops)),
        "cross_cover_drop": cross_drop,
        "sign_test_p": p,
        "baseline_presence_rate": float(base_rate),
        "target_presence_rate": float(tgt_rate),
        "effect_size_target": d_target,
        "effect_size_cross_rail": d_xrail,
        "selectivity_gate": f"|d_cross_rail| <= {SELECTIVITY_MAX_RATIO} x d_target",
        "coherence_target": tgt["coherence"],
        "sample_texts_target": tgt["sample_texts"],
    }
    if base_rate < BASELINE_PRESENCE_MIN:
        res["status"] = "VACUOUS"
        res["reason"] = (f"baseline presence rate {base_rate:.2f} below "
                         f"precondition {BASELINE_PRESENCE_MIN}; nothing "
                         "demonstrably fires to be lost")
        return res
    if tgt["coherence"] < COHERENCE_MIN:
        res["status"] = "CONFOUNDED"
        res["reason"] = "target condition failed the coherence guard (fluency confound)"
        return res
    beats_controls = (drop > max(ctrl_drops)) and (drop > cross_drop) and (p < SIGN_ALPHA)
    starves = tgt_rate < DR_PRESENCE_COLLAPSE * base_rate
    selective = (d_target > 0) and (abs(d_xrail) <= SELECTIVITY_MAX_RATIO * d_target)
    res["beats_matched_and_cross_controls"] = bool(beats_controls)
    res["starvation_signature_holds"] = bool(starves)
    res["selectivity_gate_holds"] = bool(selective)
    res["status"] = "PASS" if (beats_controls and starves and selective) else "FAIL"
    return res


def eval_amp_test(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey):
    """AMP attenuation: magnitude shrinks, presence retained, selectivity gated."""
    b = np.asarray(base["proj"][key])
    t = np.asarray(tgt["proj"][key])
    drop = float(b.mean() - t.mean())
    ctrl_drops = [float(b.mean() - np.mean(c["proj"][key])) for c in ctrls]
    cross_drop = float(b.mean() - np.mean(cross["proj"][key]))
    ctrl_mean = np.mean([c["proj"][key] for c in ctrls], axis=0)
    p = sign_test_p([float(cm - tv) for cm, tv in zip(ctrl_mean, t)])

    base_rate = rate_above(b, tau)
    tgt_rate = rate_above(t, tau)
    d_target = effect_size(b, t)
    d_xrail = effect_size(base_other["proj"][okey], xrail["proj"][okey])

    res = {
        "baseline_mean_proj": float(b.mean()),
        "target_mean_proj": float(t.mean()),
        "targeted_drop": drop,
        "matched_control_drops": ctrl_drops,
        "max_matched_control_drop": float(max(ctrl_drops)),
        "cross_direction_drop": cross_drop,
        "sign_test_p": p,
        "baseline_presence_rate": float(base_rate),
        "target_presence_rate": float(tgt_rate),
        "effect_size_target": d_target,
        "effect_size_cross_rail": d_xrail,
        "coherence_target": tgt["coherence"],
        "sample_texts_target": tgt["sample_texts"],
    }
    if base_rate < BASELINE_PRESENCE_MIN:
        res["status"] = "VACUOUS"
        res["reason"] = (f"baseline presence rate {base_rate:.2f} below "
                         f"precondition {BASELINE_PRESENCE_MIN}")
        return res
    if tgt["coherence"] < COHERENCE_MIN:
        res["status"] = "CONFOUNDED"
        res["reason"] = "target condition failed the coherence guard (fluency confound)"
        return res
    beats_controls = (drop > max(ctrl_drops)) and (drop > cross_drop) and (p < SIGN_ALPHA)
    retains = tgt_rate >= AMP_PRESENCE_RETAIN * base_rate
    selective = (d_target > 0) and (abs(d_xrail) <= SELECTIVITY_MAX_RATIO * d_target)
    res["beats_matched_and_cross_controls"] = bool(beats_controls)
    res["attenuation_signature_holds"] = bool(retains)
    res["selectivity_gate_holds"] = bool(selective)
    res["status"] = "PASS" if (beats_controls and retains and selective) else "FAIL"
    return res


def eval_rs_test(base, tgt, ctrls, key):
    """RS disinhibition: the increase-sign anchor, with a VACUOUS escape.

    Precondition (review MAJOR fix): the brake behavior must demonstrably fire
    at baseline (hedging present in >= RS_BASELINE_HEDGE_FRAC of continuations
    AND mean hedge > 0); otherwise the test is VACUOUS, not FAIL, and the run
    verdict does not require it.
    """
    b = np.asarray(base["proj"][key])
    t = np.asarray(tgt["proj"][key])
    inc = float(t.mean() - b.mean())
    ctrl_incs = [float(np.mean(c["proj"][key]) - b.mean()) for c in ctrls]
    ctrl_mean = np.mean([c["proj"][key] for c in ctrls], axis=0)
    p = sign_test_p([float(tv - cm) for cm, tv in zip(ctrl_mean, t)])

    base_hedges = base["hedges"]
    frac_hedged = float(np.mean([1.0 if h > 0 else 0.0 for h in base_hedges]))
    hedge_drop = float(base["mean_hedge"] - tgt["mean_hedge"])
    ctrl_hedge_drops = [float(base["mean_hedge"] - c["mean_hedge"]) for c in ctrls]

    res = {
        "baseline_mean_proj": float(b.mean()),
        "target_mean_proj": float(t.mean()),
        "targeted_increase": inc,
        "matched_control_increases": ctrl_incs,
        "max_matched_control_increase": float(max(ctrl_incs)),
        "sign_test_p": p,
        "baseline_mean_hedge": base["mean_hedge"],
        "target_mean_hedge": tgt["mean_hedge"],
        "baseline_frac_hedged": frac_hedged,
        "targeted_hedge_drop": hedge_drop,
        "matched_control_hedge_drops": ctrl_hedge_drops,
        "max_matched_control_hedge_drop": float(max(ctrl_hedge_drops)),
        "coherence_target": tgt["coherence"],
        "sample_texts_target": tgt["sample_texts"],
    }
    if base["mean_hedge"] <= 0.0 or frac_hedged < RS_BASELINE_HEDGE_FRAC:
        res["status"] = "VACUOUS"
        res["reason"] = (f"baseline hedging too sparse (mean {base['mean_hedge']:.2f}, "
                         f"frac {frac_hedged:.2f} < {RS_BASELINE_HEDGE_FRAC}); the "
                         "brake never demonstrably fires, so its removal predicts "
                         "no change (unreachable-threshold logic)")
        return res
    if tgt["coherence"] < COHERENCE_MIN:
        res["status"] = "CONFOUNDED"
        res["reason"] = "target condition failed the coherence guard (fluency confound)"
        return res
    ok = (inc > 0.0 and inc > max(ctrl_incs) and p < SIGN_ALPHA
          and hedge_drop > 0.0 and hedge_drop > max(ctrl_hedge_drops))
    res["status"] = "PASS" if ok else "FAIL"
    return res


def eval_conn_test(base, tgt, ctrls, key, okey, rand_keys):
    """CONN: upstream DR-F5 cut selectively starves the downstream AMP site.

    Judged ENTIRELY on clean re-forwards of ablation-generated text (FATAL-1
    fix: no tautological hooked-pass projection). Direction selectivity is the
    non-trivial content: the standardized drop on u_F5 at L* must exceed the
    drop on u_F2 and on every variance-carrying random direction at the same
    site, AND exceed the u_F5 drop produced by every activation-matched random
    cover at the same upstream layer.
    """
    d_target = effect_size(base["proj"][key], tgt["proj"][key])
    d_other = effect_size(base["proj"][okey], tgt["proj"][okey])
    d_rand = [effect_size(base["proj"][rk], tgt["proj"][rk]) for rk in rand_keys]
    d_ctrl_covers = [effect_size(base["proj"][key], c["proj"][key]) for c in ctrls]
    ctrl_mean = np.mean([c["proj"][key] for c in ctrls], axis=0)
    p = sign_test_p([float(cm - tv) for cm, tv in
                     zip(ctrl_mean, np.asarray(tgt["proj"][key]))])
    res = {
        "effect_size_uF5_downstream": d_target,
        "effect_size_uF2_downstream": d_other,
        "effect_sizes_random_dirs_downstream": d_rand,
        "max_random_dir_effect": float(max(d_rand)),
        "effect_sizes_matched_cover_controls": d_ctrl_covers,
        "max_matched_cover_effect": float(max(d_ctrl_covers)),
        "sign_test_p": p,
        "note": ("clean-pass only; correlated with DR-F5 (shared bank and "
                 "direction) -- counted with that caveat in the aggregate"),
    }
    ok = (d_target > CONN_MIN_EFFECT
          and d_target > max(d_rand)
          and d_target > d_other
          and d_target > max(d_ctrl_covers)
          and p < SIGN_ALPHA)
    res["status"] = "PASS" if ok else "FAIL"
    return res


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="COMPONENT ATLAS v0 (rev 0.2)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--revision", default=None,
                    help="HF revision; defaults to the pinned revision for known models")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny mechanical run; never evidence")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--max-new-tokens", type=int, default=24)
    ap.add_argument("--controls", type=int, default=6,
                    help="matched control trials per test")
    ap.add_argument("--local-files-only", action="store_true")
    return ap.parse_args()


def write_report(report, report_path):
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_json_default)


def main():
    args = parse_args()
    t0 = time.time()
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    revision = args.revision or PINNED_REVISIONS.get(args.model)
    claim_eligible = bool(revision) and not args.smoke
    if not revision:
        print(f"[warn] no pinned revision for {args.model}; claim_eligible=False (fail-closed)")

    out_dir = args.out or os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "atlas_v0_report.json")

    n_controls = 2 if args.smoke else args.controls
    max_new = 10 if args.smoke else args.max_new_tokens
    n_conn_dirs = 3 if args.smoke else 8
    banks = build_banks(args.smoke, args.seed)
    mem_items = MEM_ITEMS[:6] if args.smoke else MEM_ITEMS
    n_seq = 4 if args.smoke else 12

    bank_sha = sha_of({"frames": PROMPT_FRAMES, "hedged": F5_HEDGED,
                       "plain": F5_PLAIN, "ambivalent": AMBIVALENT,
                       "mem": mem_items, "hedge_words": HEDGE_WORDS,
                       "fit_idx": banks["fit_idx"],
                       "judge_idx": banks["judge_idx"], "seed": args.seed})

    print(f"[load] {args.model} rev={revision} device={device}")
    model, tok = load_model_and_tokenizer(
        args.model, revision, device, args.local_files_only)
    layers = locate_layers(model)
    n_blocks = len(layers)
    n_heads = int(model.config.num_attention_heads)
    hidden = int(model.config.hidden_size)
    head_dim = hidden // n_heads
    print(f"[arch] blocks={n_blocks} heads/layer={n_heads} hidden={hidden}")

    report = {
        "schema_version": SCHEMA_VERSION,
        "frame": FRAME,
        "boundary": BOUNDARY,
        "aggregate_caveat": AGGREGATE_CAVEAT,
        "provenance": {
            "model": args.model,
            "revision": revision,
            "claim_eligible": claim_eligible,
            "seed": args.seed,
            "device": device,
            "smoke": bool(args.smoke),
            "n_controls": n_controls,
            "max_new_tokens": max_new,
            "prompt_bank_sha256": bank_sha,
            "fit_frame_indices": banks["fit_idx"],
            "judge_frame_indices": banks["judge_idx"],
            "torch": torch.__version__,
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }

    # ---------------- Stage: SURFACE CONTROL ----------------
    print("[surface] char-ngram control on the banks (fit->judge)")
    report["surface_control"] = {
        "f5_vs_neutral": char_ngram_control(
            banks["f5_fit"], banks["neu_fit"],
            banks["f5_judge"], banks["neu_judge"]),
        "f2_vs_neutral": char_ngram_control(
            banks["f2_fit"], banks["neu_fit"],
            banks["f2_judge"], banks["neu_judge"]),
    }

    # ---------------- Stage: DISCOVER (fit split ONLY) ----------------
    print("[discover] capturing residual features (fit banks only)")
    feats = {
        "f5_fit": residual_feats(model, tok, banks["f5_fit"], device),
        "f2_fit": residual_feats(model, tok, banks["f2_fit"], device),
        "neu_fit": residual_feats(model, tok, banks["neu_fit"], device),
        "hedged": residual_feats(model, tok, banks["f5_hedged"], device),
        "plain": residual_feats(model, tok, banks["f5_plain"], device),
    }

    print("[discover] probe sweep across blocks (inner split of fit rows)")
    sweep_lo = LAYER_SWEEP_MIN
    sweep_hi = n_blocks - 2
    accs_f5, accs_f2, sweep_blocks = [], [], []
    for L in range(sweep_lo, sweep_hi + 1):
        sweep_blocks.append(L)
        accs_f5.append(fit_probe_acc(
            feats["f5_fit"][:, L + 1], feats["neu_fit"][:, L + 1], args.seed))
        accs_f2.append(fit_probe_acc(
            feats["f2_fit"][:, L + 1], feats["neu_fit"][:, L + 1], args.seed))
    mean_accs = [(a + b) / 2.0 for a, b in zip(accs_f5, accs_f2)]
    l_star = int(sweep_blocks[int(np.argmax(mean_accs))])
    best_acc = float(max(mean_accs))

    rng_floor = np.random.default_rng(args.seed + 555)
    floor = [fit_probe_acc(feats["f5_fit"][:, l_star + 1],
                           feats["neu_fit"][:, l_star + 1],
                           args.seed + tr, shuffle_labels=True, rng=rng_floor)
             for tr in range(3)]
    floor_max = float(max(floor))

    report["discover"] = {
        "n_blocks": n_blocks,
        "sweep_blocks": sweep_blocks,
        "probe_acc_f5_per_block": accs_f5,
        "probe_acc_f2_per_block": accs_f2,
        "L_star": l_star,
        "best_mean_acc": best_acc,
        "shuffled_label_floor": floor,
        "shuffled_label_floor_max": floor_max,
    }

    # Hard layer guard (review minor fix: abort, never silently accept).
    if l_star < L_STAR_MIN:
        report["aggregate"] = {
            "status": "ABORT_GUARD_LAYER",
            "reason": (f"L*={l_star} < {L_STAR_MIN}: L_dr = L*-{DR_OFFSET} would "
                       "not be strictly upstream with margin; preregistered "
                       "hard abort, no fallback")}
        write_report(report, report_path)
        print("[abort] ABORT_GUARD_LAYER")
        return 0
    l_dr = l_star - DR_OFFSET
    report["discover"]["L_dr"] = l_dr
    print(f"[discover] L*={l_star} (acc={best_acc:.3f}) L_dr={l_dr} "
          f"floor_max={floor_max:.3f}")

    if best_acc <= floor_max:
        report["aggregate"] = {
            "status": "NO_SIGNAL_ATLAS_V0",
            "reason": "best probe accuracy does not beat shuffled-label floor"}
        write_report(report, report_path)
        print("[abort] NO_SIGNAL: probe does not beat shuffled floor")
        return 0

    # Directions (fit split only).
    u_f5_star = diff_dir(feats["f5_fit"], feats["neu_fit"], l_star + 1)
    u_f2_star = diff_dir(feats["f2_fit"], feats["neu_fit"], l_star + 1)
    u_f5_dr = diff_dir(feats["f5_fit"], feats["neu_fit"], l_dr + 1)
    u_f2_dr = diff_dir(feats["f2_fit"], feats["neu_fit"], l_dr + 1)
    raw_rs = (feats["hedged"][:, l_star + 1].mean(0)
              - feats["plain"][:, l_star + 1].mean(0))
    raw_rs = raw_rs - float(raw_rs @ u_f5_star) * u_f5_star
    u_rs_star = unit(raw_rs)

    # Variance-carrying control-direction subspace at L* (fit banks).
    X_star = np.concatenate([feats["f5_fit"][:, l_star + 1],
                             feats["f2_fit"][:, l_star + 1],
                             feats["neu_fit"][:, l_star + 1]], axis=0)
    V_star = pc_basis(X_star, PC_SUBSPACE_K)

    # CONN random downstream directions (variance-carrying, fixed seed).
    rng_conn = np.random.default_rng(args.seed + 901)
    conn_dirs = {f"r{i}": pc_random_dir(V_star, rng_conn)
                 for i in range(n_conn_dirs)}
    measure_dirs = {"uF5": u_f5_star, "uF2": u_f2_star}
    measure_dirs.update(conn_dirs)
    rand_keys = sorted(conn_dirs)

    # DR covers (Stage-27F-style scoring at L_dr, fit banks only).
    print("[discover] scoring DR covers at L_dr")
    mlp_mod = layers[l_dr].mlp.dense_4h_to_h
    w_out = mlp_mod.weight.detach().float().cpu().numpy()   # [hidden, intermediate]
    acts_f5 = mlp_intermediate_feats(model, tok, banks["f5_fit"], mlp_mod, device)
    acts_f2 = mlp_intermediate_feats(model, tok, banks["f2_fit"], mlp_mod, device)
    acts_nt = mlp_intermediate_feats(model, tok, banks["neu_fit"], mlp_mod, device)
    cover_f5, _ = score_dr_cover(acts_f5, acts_nt, w_out, u_f5_dr, COVER_K)
    cover_f2, _ = score_dr_cover(acts_f2, acts_nt, w_out, u_f2_dr, COVER_K)
    mean_abs_f5 = np.abs(acts_f5).mean(0)
    mean_abs_f2 = np.abs(acts_f2).mean(0)

    # RS cover site is the residual direction u_rs (rank-1 eraser at L*).

    # ---------------- Stage: LABEL ----------------
    atlas = [
        {"component_id": "DR-F5", "type_label": "DR",
         "location": {"kind": "mlp_intermediate_cover", "block": l_dr,
                      "coords": cover_f5}},
        {"component_id": "DR-F2", "type_label": "DR",
         "location": {"kind": "mlp_intermediate_cover", "block": l_dr,
                      "coords": cover_f2}},
        {"component_id": "RS-F5", "type_label": "RS",
         "location": {"kind": "residual_direction", "block": l_star,
                      "note": "restraint direction, orthogonalized vs drive direction"}},
        {"component_id": "AMP-F5", "type_label": "AMP",
         "location": {"kind": "residual_direction", "block": l_star,
                      "note": "drive subspace rank-1"}},
    ]
    report["atlas"] = atlas

    def dr_hooks(cover):
        return [(mlp_mod, make_cover_zero_prehook(cover), "pre")]

    def eraser_hooks(u_dir):
        return [(layers[l_star], ForwardEdit(make_projection_removal(u_dir)),
                 "forward")]

    # ---------------- Stage: ABLATE (generate hooked, judge CLEAN) --------
    print("[ablate] baselines (judge banks, no hooks)")
    txt_base_f5 = gen_condition(model, tok, banks["f5_judge"], device, [], max_new)
    txt_base_f2 = gen_condition(model, tok, banks["f2_judge"], device, [], max_new)
    txt_base_neu = gen_condition(model, tok, banks["neu_judge"], device, [], max_new)
    txt_base_amb = gen_condition(model, tok, banks["ambivalent"], device, [], max_new)

    base_f5 = measure_condition(model, tok, banks["f5_judge"], txt_base_f5,
                                device, l_star, measure_dirs)
    base_f2 = measure_condition(model, tok, banks["f2_judge"], txt_base_f2,
                                device, l_star, measure_dirs)
    base_neu = measure_condition(model, tok, banks["neu_judge"], txt_base_neu,
                                 device, l_star, measure_dirs)
    base_amb = measure_condition(model, tok, banks["ambivalent"], txt_base_amb,
                                 device, l_star, {"uF5": u_f5_star})

    # Presence thresholds from BASELINE conditions only (preregistered formula:
    # midpoint of drive-judge and neutral-judge baseline clean projections).
    tau_f5 = 0.5 * (float(np.mean(base_f5["proj"]["uF5"]))
                    + float(np.mean(base_neu["proj"]["uF5"])))
    tau_f2 = 0.5 * (float(np.mean(base_f2["proj"]["uF2"]))
                    + float(np.mean(base_neu["proj"]["uF2"])))
    report["discover"]["tau_F5"] = tau_f5
    report["discover"]["tau_F2"] = tau_f2

    tests = {}

    # ---- DR-F5 ----
    print("[ablate] DR-F5")
    txt_tgt = gen_condition(model, tok, banks["f5_judge"], device,
                            dr_hooks(cover_f5), max_new)
    tgt_dr5 = measure_condition(model, tok, banks["f5_judge"], txt_tgt,
                                device, l_star, measure_dirs)
    ctrls_dr5 = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + tr)
        cov = decile_matched_cover(mean_abs_f5, cover_f5, rng)
        txt_c = gen_condition(model, tok, banks["f5_judge"], device,
                              dr_hooks(cov), max_new)
        ctrls_dr5.append(measure_condition(
            model, tok, banks["f5_judge"], txt_c, device, l_star, measure_dirs))
    txt_cross = gen_condition(model, tok, banks["f5_judge"], device,
                              dr_hooks(cover_f2), max_new)
    cross_dr5 = measure_condition(model, tok, banks["f5_judge"], txt_cross,
                                  device, l_star, measure_dirs)
    txt_xrail = gen_condition(model, tok, banks["f2_judge"], device,
                              dr_hooks(cover_f5), max_new)
    xrail_dr5 = measure_condition(model, tok, banks["f2_judge"], txt_xrail,
                                  device, l_star, {"uF2": u_f2_star})
    tests["DR_F5"] = eval_dr_test(base_f5, tgt_dr5, ctrls_dr5, cross_dr5,
                                  tau_f5, base_f2, xrail_dr5, "uF5", "uF2")

    # ---- DR-F2 ----
    print("[ablate] DR-F2")
    txt_tgt2 = gen_condition(model, tok, banks["f2_judge"], device,
                             dr_hooks(cover_f2), max_new)
    tgt_dr2 = measure_condition(model, tok, banks["f2_judge"], txt_tgt2,
                                device, l_star, measure_dirs)
    ctrls_dr2 = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 100 + tr)
        cov = decile_matched_cover(mean_abs_f2, cover_f2, rng)
        txt_c = gen_condition(model, tok, banks["f2_judge"], device,
                              dr_hooks(cov), max_new)
        ctrls_dr2.append(measure_condition(
            model, tok, banks["f2_judge"], txt_c, device, l_star, measure_dirs))
    txt_cross2 = gen_condition(model, tok, banks["f2_judge"], device,
                               dr_hooks(cover_f5), max_new)
    cross_dr2 = measure_condition(model, tok, banks["f2_judge"], txt_cross2,
                                  device, l_star, measure_dirs)
    txt_xrail2 = gen_condition(model, tok, banks["f5_judge"], device,
                               dr_hooks(cover_f2), max_new)
    xrail_dr2 = measure_condition(model, tok, banks["f5_judge"], txt_xrail2,
                                  device, l_star, {"uF5": u_f5_star})
    tests["DR_F2"] = eval_dr_test(base_f2, tgt_dr2, ctrls_dr2, cross_dr2,
                                  tau_f2, base_f5, xrail_dr2, "uF2", "uF5")

    # ---- AMP-F5 ----
    print("[ablate] AMP-F5")
    txt_amp = gen_condition(model, tok, banks["f5_judge"], device,
                            eraser_hooks(u_f5_star), max_new)
    tgt_amp = measure_condition(model, tok, banks["f5_judge"], txt_amp,
                                device, l_star, measure_dirs)
    ctrls_amp = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 300 + tr)
        u_rand = pc_random_dir(V_star, rng)
        txt_c = gen_condition(model, tok, banks["f5_judge"], device,
                              eraser_hooks(u_rand), max_new)
        ctrls_amp.append(measure_condition(
            model, tok, banks["f5_judge"], txt_c, device, l_star, measure_dirs))
    txt_amp_cross = gen_condition(model, tok, banks["f5_judge"], device,
                                  eraser_hooks(u_f2_star), max_new)
    cross_amp = measure_condition(model, tok, banks["f5_judge"], txt_amp_cross,
                                  device, l_star, measure_dirs)
    txt_amp_xrail = gen_condition(model, tok, banks["f2_judge"], device,
                                  eraser_hooks(u_f5_star), max_new)
    xrail_amp = measure_condition(model, tok, banks["f2_judge"], txt_amp_xrail,
                                  device, l_star, {"uF2": u_f2_star})
    tests["AMP_F5"] = eval_amp_test(base_f5, tgt_amp, ctrls_amp, cross_amp,
                                    tau_f5, base_f2, xrail_amp, "uF5", "uF2")

    # ---- RS-F5 (increase-sign anchor) ----
    print("[ablate] RS-F5")
    txt_rs = gen_condition(model, tok, banks["ambivalent"], device,
                           eraser_hooks(u_rs_star), max_new)
    tgt_rs = measure_condition(model, tok, banks["ambivalent"], txt_rs,
                               device, l_star, {"uF5": u_f5_star})
    ctrls_rs = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 200 + tr)
        u_rand = pc_random_dir(V_star, rng, ortho_to=u_f5_star)
        txt_c = gen_condition(model, tok, banks["ambivalent"], device,
                              eraser_hooks(u_rand), max_new)
        ctrls_rs.append(measure_condition(
            model, tok, banks["ambivalent"], txt_c, device, l_star,
            {"uF5": u_f5_star}))
    tests["RS_F5"] = eval_rs_test(base_amb, tgt_rs, ctrls_rs, "uF5")

    # ---------------- Stage: CONNECT ----------------
    # Reuses the DR-F5 conditions (no new generation); judged on the clean
    # re-forward projections onto u_F5, u_F2 and the variance-carrying random
    # directions at the AMP site L*.
    print("[connect] DR-F5 (L_dr) -> AMP-F5 site (L*), clean-pass direction selectivity")
    tests["CONN_DRF5_to_AMPF5"] = eval_conn_test(
        base_f5, tgt_dr5, ctrls_dr5, "uF5", "uF2", rand_keys)
    tests["CONN_DRF5_to_AMPF5"]["upstream"] = {
        "kind": "mlp_intermediate_cover", "block": l_dr}
    tests["CONN_DRF5_to_AMPF5"]["downstream_site_block"] = l_star

    # ---------------- Stage: HARNESS SANITY (outside aggregate) ----------
    sanity = {}

    print("[sanity] MEM copy heads (generic transformer phenomenon; not a CAS-PCBA discriminator)")
    usable_all = mem_usable_items(tok, mem_items)
    half = len(usable_all) // 2
    mem_disc, mem_judge = usable_all[:half], usable_all[half:]
    if len(mem_disc) >= 3 and len(mem_judge) >= 3:
        mem_scores = mem_head_scores(model, tok, mem_disc, device, n_blocks, n_heads)
        mem_heads = top_heads(mem_scores, MEM_TOPK_HEADS)
        base_copy = copy_accuracy(model, tok, mem_judge, device, [])
        mem_specs = head_hook_specs(layers, mem_heads, head_dim)
        abl_copy = copy_accuracy(model, tok, mem_judge, device, mem_specs)
        ctrl_copies = []
        for tr in range(n_controls):
            rng = np.random.default_rng(args.seed * 10000 + 400 + tr)
            rnd = random_matched_heads(mem_heads, n_heads, rng)
            ctrl_copies.append(copy_accuracy(
                model, tok, mem_judge, device,
                head_hook_specs(layers, rnd, head_dim)))
        drop = base_copy - abl_copy
        ctrl_drops = [base_copy - c for c in ctrl_copies]
        mem_res = {
            "heads": mem_heads,
            "n_discovery_items": len(mem_disc),
            "n_judgment_items": len(mem_judge),
            "baseline_copy_acc": float(base_copy),
            "ablated_copy_acc": float(abl_copy),
            "targeted_drop": float(drop),
            "control_drops": [float(d) for d in ctrl_drops],
            "max_control_drop": float(max(ctrl_drops)),
        }
        if base_copy < MEM_BASELINE_MIN:
            mem_res["status"] = "VACUOUS"
            mem_res["reason"] = (f"baseline copy accuracy {base_copy:.2f} below "
                                 f"precondition {MEM_BASELINE_MIN}")
        else:
            ok = (drop >= MEM_DROP_MIN) and (drop > max(ctrl_drops))
            mem_res["status"] = "SANITY_PASS" if ok else "SANITY_FAIL"
    else:
        mem_res = {"status": "VACUOUS",
                   "reason": "not enough usable copy items after tokenization"}
    sanity["MEM_SANITY"] = mem_res

    print("[sanity] CHECK induction gate (held-out judgment sequences)")
    rng_disc = np.random.default_rng(args.seed + 777)
    rng_judge = np.random.default_rng(args.seed + 778)   # held-out (review fix)
    seqs_disc = build_induction_seqs(rng_disc, n_seq, seg_len=12)
    seqs_judge = build_induction_seqs(rng_judge, n_seq, seg_len=12)
    ind_scores = induction_head_scores(model, seqs_disc, device, n_blocks, n_heads)
    check_heads = top_heads(ind_scores, CHECK_TOPK_HEADS)
    base_gate = float(np.mean(gate_scores(model, seqs_judge, device, [])))
    check_specs = head_hook_specs(layers, check_heads, head_dim)
    abl_gate = float(np.mean(gate_scores(model, seqs_judge, device, check_specs)))
    ctrl_gates = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 500 + tr)
        rnd = random_matched_heads(check_heads, n_heads, rng)
        ctrl_gates.append(float(np.mean(gate_scores(
            model, seqs_judge, device, head_hook_specs(layers, rnd, head_dim)))))
    gate_drop = base_gate - abl_gate
    ctrl_gate_drops = [base_gate - g for g in ctrl_gates]
    check_res = {
        "heads": check_heads,
        "baseline_gate_score_nats": base_gate,
        "ablated_gate_score_nats": abl_gate,
        "targeted_drop": float(gate_drop),
        "control_drops": [float(d) for d in ctrl_gate_drops],
        "max_control_drop": float(max(ctrl_gate_drops)),
    }
    if base_gate < CHECK_GATE_MIN_NATS:
        check_res["status"] = "VACUOUS"
        check_res["reason"] = (f"baseline gate score {base_gate:.2f} nats below "
                               f"precondition {CHECK_GATE_MIN_NATS} "
                               "(unreachable-threshold trap)")
    else:
        ok = (gate_drop >= CHECK_DROP_FRAC * base_gate) and \
             (gate_drop > max(ctrl_gate_drops))
        check_res["status"] = "SANITY_PASS" if ok else "SANITY_FAIL"
    sanity["CHECK_SANITY"] = check_res

    # ---------------- Stage: REPORT ----------------
    core_order = ["DR_F5", "DR_F2", "AMP_F5", "RS_F5", "CONN_DRF5_to_AMPF5"]
    evaluable = [n for n in core_order
                 if tests[n].get("status") in ("PASS", "FAIL", "CONFOUNDED")]
    n_pass = sum(1 for n in evaluable if tests[n]["status"] == "PASS")
    n_eval = len(evaluable)
    fraction = (n_pass / n_eval) if n_eval else 0.0

    rs_status = tests["RS_F5"].get("status")
    rs_ok_or_vacuous = rs_status in ("PASS", "VACUOUS")

    kill = None
    if n_eval < 3:
        status = "GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE"
    elif (rs_status == "FAIL") and (fraction <= 0.5):
        status = "NULL_ATLAS_V0"
        kill = ("KILL condition met: the increase-sign anchor (RS) was evaluable "
                "and FAILED against matched controls AND the evaluable pass "
                "fraction is <= 0.5. Directional component-type labeling adds "
                "nothing over generic localization at this substrate; "
                "CAS-PCBA internal labeling does not proceed to v1 in its "
                "current form.")
    elif fraction <= 0.5:
        status = "NULL_ATLAS_V0"
    elif n_eval >= 4 and (n_eval - n_pass) <= 1 and rs_ok_or_vacuous:
        status = "PASS_BOUNDED_ATLAS_V0"
    else:
        status = "GREY_ATLAS_V0"

    dr_amp_separate = (
        tests["DR_F5"].get("starvation_signature_holds") is True
        and tests["AMP_F5"].get("attenuation_signature_holds") is True)
    if (rs_status == "FAIL") and (not dr_amp_separate) and n_eval >= 4:
        status = "NULL_ATLAS_V0"
        kill = ("KILL condition met: the increase-sign anchor (RS) failed AND "
                "the DR/AMP presence-vs-magnitude discriminator did not "
                "separate; the vocabulary is reading as decoration on generic "
                "interventions.")

    report["tests"] = tests
    report["harness_sanity"] = sanity
    report["aggregate"] = {
        "core_test_order": core_order,
        "n_evaluable": n_eval,
        "n_pass": n_pass,
        "fraction_pass_descriptive": float(fraction),
        "non_independence_caveat": AGGREGATE_CAVEAT,
        "rs_sign_anchor_status": rs_status,
        "harness_sanity_excluded_from_aggregate": True,
        "status": status,
        "kill_statement_triggered": kill,
        "language": ("Every PASS is worded 'causally supports the <TYPE> "
                     "labeling'; never 'found THE neurons' or 'the circuit'."),
    }
    report["provenance"]["runtime_seconds"] = round(time.time() - t0, 1)
    if args.smoke:
        report["provenance"]["note"] = ("SMOKE RUN -- mechanical validation only; "
                                        "numbers are never evidence")

    write_report(report, report_path)
    print(f"[done] status={status} pass={n_pass}/{n_eval} "
          f"report={report_path} "
          f"({report['provenance']['runtime_seconds']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
