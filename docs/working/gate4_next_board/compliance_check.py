"""COMPLIANCE CHECK -- can a real model reliably produce a PRESCRIBED dialog turn type?

STANDALONE. This file does not import, read or modify next_board_test.py or
PREREG_NEXT_BOARD_V1.md. It reuses only the shared transport infrastructure in
docs/working/gate2_closure/independent_bank/ (providers, pilot_label, l1_agreement).

WHY THIS EXISTS
    HYBRID_DESIGN_NOTE.md proposes a hybrid corpus: SDG plans the dialog path, a real
    model writes the prose, and the PRESCRIBED turn type is the ground-truth label.
    That whole design rests on ONE assumption:

        a real model, told to write a turn of type T, actually writes a turn of type T.

    If it does not, the prescribed label is not ground truth, and the hybrid is no
    better off than the API corpus it was meant to replace. This script measures that
    gap directly and cheaply, BEFORE the hybrid corpus stage is written.

WHAT IT DOES
    1. GENERATE  7 prescribed turn types x N topics. A generator model is told to write
                 ONE turn of the prescribed type, in natural prose, WITHOUT naming the
                 type and WITHOUT any meta preamble. Generator rotates over the four
                 blind-probed providers; which provider wrote each item is recorded.
    2. LABEL     3 blind readers recover the type FROM THE PROSE ALONE. A reader is
                 never the model that generated the item (generator != labeller,
                 enforced structurally at job-build time and again at collection time).
                 Readers see the text, the 7 definitions in a per-batch shuffled order,
                 and per-batch alias ids that encode neither type nor topic.
    3. SCORE     recovery vs the 1/7 = 0.1429 chance level, per-type recall, the full
                 7x7 confusion matrix, Fleiss kappa, coverage, and per-GENERATOR
                 compliance.

    The 7 definitions are used VERBATIM in both the generation instruction and the
    reader rubric, so the test is symmetric: the reader is asked exactly the question
    the generator was asked to answer.

INTERPRETATION RULE (frozen here, printed with every summary, stored in the report)
    * Recovery AT OR NEAR 0.1429  -> models CANNOT reliably hit a prescribed turn type.
      The hybrid has NO GROUND TRUTH and MUST BE ABANDONED, not repaired. A prescribed
      label that the prose does not carry is not a label.
    * Recovery HIGH (> 0.60)      -> the prescribed type IS recoverable and the hybrid
      has a FLOOR. Stated honestly: high recovery may partly reflect STYLISED,
      SURFACE-SEPARABLE text (a model told to write a PLAN may emit a numbered list
      that a word-unigram model recovers just as well), not genuine type compliance.
      A SURFACE CONTROL IS STILL REQUIRED LATER. This result does NOT validate the
      hybrid; it establishes a floor and nothing more.
    * ANYTHING BETWEEN            -> reported as-is, with no spin and no verdict.

WHAT THIS IS NOT
    Not a surface control. Not a CAS claim. Not a validation of the turn-type -> board
    mapping (which is OURS, not the framework's, and is out of scope here). Ground
    truth here is the PRESCRIBED type, i.e. an instruction, not a verified property of
    the text -- which is precisely the gap being measured.

USAGE
    python compliance_check.py --smoke          # 2 topics x 7 types = 14 items, run FIRST
    python compliance_check.py                  # 6 topics x 7 types = 42 items

    --stage {all,generate,label,score}          resume a single stage
    Both API stages CHECKPOINT to JSONL as each unit lands and SKIP completed units on
    restart, so a crash never costs the spend.

COST
    ~42 short generation calls + ~24 batched labelling calls. Well under $5.
"""
import os
import re
import sys
import json
import time
import math
import random
import hashlib
import argparse
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- sibling-directory infra ------------------------------------------------
# The independent_bank scripts import each other by BARE module name, so its
# directory must be on sys.path before we import any of them.
HERE = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.abspath(os.path.join(HERE, "..", "gate2_closure", "independent_bank"))
if BANK_DIR not in sys.path:
    sys.path.insert(0, BANK_DIR)

import providers                                          # noqa: E402,F401
from pilot_label import call_with_retry, MODELS           # noqa: E402
from l1_agreement import fleiss_kappa                     # noqa: E402
from openai import OpenAI                                 # noqa: E402

try:  # Windows console is cp1252 and provider errors carry non-latin text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# =====================================================================
# CONSTANTS
# =====================================================================
ORDER = ["gemini", "deepseek", "qwen", "glm"]
# Matched to pilot_label._SEM. The labelling pool is sized to this sum so a worker
# blocked on the GLM Semaphore(1) never starves the other three providers.
PROVIDER_CONCURRENCY = {"gemini": 4, "deepseek": 2, "qwen": 2, "glm": 1}

# GLM previously returned "0 labels, finish=length" because the reasoning trace ate
# the whole budget before any JSON was emitted. 16000 + a finish_reason=='stop'
# requirement is the fix that made the panel usable.
MAXTOK_LABEL = 16000
MAXTOK_GEN = 4000        # a cap, not a spend: the turns are 2-5 sentences

SEED_BATCH_BASE = 5150   # + reader index -> labelling batch shuffle
SEED_ALIAS_BASE = 95100  # + reader/batch -> per-batch excerpt alias ids
SEED_RUBRIC_BASE = 61700  # + reader/batch -> per-batch rubric option order

CHANCE = 1.0 / 7.0       # 0.142857...
HIGH_RECOVERY = 0.60     # the "hybrid has a floor" threshold from the interpretation rule

# ---- THE 7 TURN TYPES ------------------------------------------------------
# VERBATIM in BOTH the generation instruction and the reader rubric. Do not reword
# one without rewording the other -- the symmetry is the point of the design.
TYPES = ["ACK", "MIRROR", "CLARIFY", "EMPATHIZE", "ANSWER", "PLAN", "REFUSE"]
TYPE_DEFS = {
    "ACK":       "briefly acknowledge what was said and nothing more. No new content, no advice.",
    "MIRROR":    "reflect back the structure of what the user said, checking your understanding. "
                 "No new advice.",
    "CLARIFY":   "ask the user a question to pin down what they mean. Must end by asking, not telling.",
    "EMPATHIZE": "respond to the emotional weight of what was said. No analysis, no plan.",
    "ANSWER":    "give your substantive answer to what was asked. Assertive, not hedged into a question.",
    "PLAN":      "lay out concrete next steps to take. Actionable, sequenced.",
    "REFUSE":    "decline to do what was asked and say why. Do not comply.",
}
CODE_RE = r"\b(ACK|MIRROR|CLARIFY|EMPATHIZE|ANSWER|PLAN|REFUSE)\b"

# ---- LABEL-WORD LEAKAGE TERMS ---------------------------------------------
# A generated turn that names its own type inflates recovery for a reason that has
# nothing to do with type compliance. Items containing these are FLAGGED and a
# leak-excluded sensitivity accuracy is reported beside the headline number.
# ANSWER/PLAN/REFUSE terms are ordinary English and will fire on innocent prose too,
# which is why this is reported as a SENSITIVITY, never silently applied.
LEAK_TERMS = {
    "ACK":       ["ack", "acknowledge", "acknowledging", "acknowledgement", "acknowledgment"],
    "MIRROR":    ["mirror", "mirroring", "mirrored"],
    "CLARIFY":   ["clarify", "clarifying", "clarification"],
    "EMPATHIZE": ["empathize", "empathise", "empathizing", "empathy", "empathetic"],
    "ANSWER":    ["answer", "answering", "answered"],
    "PLAN":      ["plan", "plans", "planning", "planned"],
    "REFUSE":    ["refuse", "refusing", "refusal", "decline", "declining", "declined"],
}

# ---- TOPICS ----------------------------------------------------------------
# Mundane and non-sensitive by construction. Each topic is ONE user message; all 7
# prescribed types answer THE SAME user message, so type is the only thing that
# varies within a topic. Every message carries an explicit request, which is what
# makes REFUSE a natural (rather than contrived) turn on a mundane topic.
TOPICS = [
    ("T1", "coffee maker",
     "I've been going back and forth for weeks on which coffee maker to get for my "
     "tiny kitchen counter. Can you just tell me which one to buy?"),
    ("T2", "barking dog",
     "My neighbour's dog starts barking at about five in the morning most days and I'm "
     "not sleeping properly any more. Can you sort out what I should do?"),
    ("T3", "cooking rice",
     "Every single time I cook rice it comes out either mushy or crunchy, never right. "
     "Can you tell me what I'm doing wrong?"),
    ("T4", "full bookshelf",
     "My bookshelf is completely full and there are stacks of books on the floor now. "
     "I need you to tell me how to deal with it."),
    ("T5", "bike gears",
     "My bike keeps slipping gears on the ride to work and it's starting to feel "
     "dangerous. Can you fix this for me?"),
    ("T6", "weekend trip",
     "I want to go somewhere nearby for the weekend but I keep putting off deciding "
     "and now it's Thursday. Can you just decide for me?"),
]

_WRITE_LOCK = threading.Lock()


# =====================================================================
# shared helpers (transport patterns copied from next_board_test.py)
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
    trace in reasoning_content. Concatenating the two lets a chain-of-thought aside
    ("not ACK, so MIRROR") be harvested as a confident label, so they are kept apart:
    only the ANSWER may yield labels. The trace is captured for diagnosis only.
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


def binom_tail_ge(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p). Exact; n is at most a few hundred here."""
    if n <= 0:
        return 1.0
    k = max(0, int(k))
    return float(sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
                     for i in range(k, n + 1)))


# =====================================================================
# STAGE 1 -- GENERATE
# =====================================================================
_META_LEAD = re.compile(
    r"^(sure|certainly|absolutely|of course|okay|ok|here(?:'s| is)|below(?: is)?|"
    r"this is|example|response|turn)\b[^.!?]{0,90}:\s*$", re.I)
_LABEL_PREFIX = re.compile(
    r"^\s*(?:\*\*|__|#+\s*)?\(?(?:%s)\)?(?:\*\*|__)?\s*(?:turn)?\s*[:\-–—]\s*"
    % "|".join(TYPES), re.I)
_TRAILING_NOTE = re.compile(
    r"^\s*[\(\[\*_]*\s*(?:note|this (?:is|was)|the above)\b.*$", re.I)


def strip_meta(text):
    """Remove preamble/label/meta scaffolding a generator may wrap around the turn.

    Returns (clean_text, list_of_things_stripped). The strip is COSMETIC and is
    recorded per item: a model that needed heavy stripping is a model whose raw
    output was not a bare turn, and that is itself a compliance signal.
    """
    stripped = []
    t = (text or "").strip()
    # fenced code block -> keep the inside
    fence = re.match(r"^```[a-zA-Z]*\s*\n(.*?)\n?```\s*$", t, re.S)
    if fence:
        t = fence.group(1).strip()
        stripped.append("code_fence")
    lines = [ln.rstrip() for ln in t.splitlines()]
    # drop leading blank / meta / bare-label lines
    while lines:
        ln = lines[0].strip()
        if not ln:
            lines.pop(0)
            continue
        if _META_LEAD.match(ln):
            lines.pop(0)
            stripped.append("meta_lead_line")
            continue
        bare = re.sub(r"[\*_#\s\.\:\-]", "", ln).upper()
        if bare in TYPES:
            lines.pop(0)
            stripped.append("bare_label_line")
            continue
        break
    # drop trailing blank / explanatory-note lines
    while lines:
        ln = lines[-1].strip()
        if not ln:
            lines.pop()
            continue
        if _TRAILING_NOTE.match(ln) and any(ty.lower() in ln.lower() for ty in TYPES):
            lines.pop()
            stripped.append("trailing_note")
            continue
        break
    t = "\n".join(lines).strip()
    # inline "ACK: ..." / "**PLAN** - ..." prefix on the first line
    m = _LABEL_PREFIX.match(t)
    if m:
        t = t[m.end():].strip()
        stripped.append("inline_label_prefix")
    # blockquote markers
    if t and all(ln.strip().startswith(">") for ln in t.splitlines() if ln.strip()):
        t = "\n".join(re.sub(r"^\s*>\s?", "", ln) for ln in t.splitlines()).strip()
        stripped.append("blockquote")
    # whole-turn wrapping quotes
    for a, b in (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’")):
        if len(t) > 2 and t.startswith(a) and t.endswith(b) and b not in t[1:-1]:
            t = t[1:-1].strip()
            stripped.append("wrapping_quotes")
            break
    return t, stripped


def leak_terms_present(text, ttype):
    low = (text or "").lower()
    return [w for w in LEAK_TERMS[ttype] if re.search(r"\b%s\b" % re.escape(w), low)]


def build_items(n_topics):
    """Deterministic item plan: 7 types x n_topics, generator rotated over ORDER.

    index = type_idx * n_topics + topic_idx, provider = ORDER[index % 4]. For a given
    type the indices are consecutive, so every type is written by every provider that
    the rotation reaches -- the generator mix is balanced WITHIN type, not stacked.
    """
    topics = TOPICS[:n_topics]
    items = []
    for ti, ttype in enumerate(TYPES):
        for pi, (topic_id, topic_name, user_msg) in enumerate(topics):
            idx = ti * n_topics + pi
            items.append({
                "item_id": f"{ttype}__{topic_id}",
                "prescribed_type": ttype,
                "topic_id": topic_id,
                "topic_name": topic_name,
                "user_msg": user_msg,
                "gen_provider": ORDER[idx % len(ORDER)],
                "gen_model": MODELS[ORDER[idx % len(ORDER)]],
            })
    return items


def gen_prompt(spec):
    ttype = spec["prescribed_type"]
    return (
        "You are the assistant in an ordinary conversation. Write ONE reply turn, and "
        "nothing else.\n\n"
        f"The person said:\n\"{spec['user_msg']}\"\n\n"
        "The turn you write must be of exactly this kind:\n"
        f"  {TYPE_DEFS[ttype]}\n\n"
        "RULES - all mandatory:\n"
        "1. Write 2 to 5 sentences of natural conversational prose.\n"
        "2. Do NOT name the kind of turn. Do NOT use the word that names it, in any "
        "form, anywhere in the output.\n"
        "3. Do NOT write a preamble, heading, label, bullet header or commentary. "
        "Nothing like \"Here is ...\" or \"Turn:\". The very first character of your "
        "output must be the first character of the turn itself.\n"
        "4. Do NOT wrap the turn in quotation marks.\n"
        "5. Write it as a real reply the person would actually receive.\n\n"
        "Output the turn text only."
    )


def gen_item(spec):
    prov, model = spec["gen_provider"], spec["gen_model"]
    client = _client(prov, model)
    r = call_with_retry(client, prov, model=model, max_tokens=MAXTOK_GEN,
                        temperature=0.7,
                        messages=[{"role": "user", "content": gen_prompt(spec)}])
    ans, rea = _split_text(r)
    finish = r.choices[0].finish_reason
    if finish != "stop":
        raise RuntimeError(f"finish_reason={finish} (ans {len(ans)}c, trace {len(rea)}c)")
    clean, stripped = strip_meta(ans)
    if len(clean) < 25:
        raise RuntimeError(f"short/empty after meta strip ({len(clean)} chars)")
    out = dict(spec)
    out["text"] = clean
    out["raw_len"] = len(ans.strip())
    out["meta_stripped"] = stripped
    out["label_word_leak"] = leak_terms_present(clean, spec["prescribed_type"])
    out["n_sentences_approx"] = len([s for s in re.split(r"[.!?]+\s", clean) if s.strip()])
    return out


def stage_generate(A, items):
    existing = {r["item_id"] for r in _jsonl_read(A.gen_file)}
    todo = [s for s in items if s["item_id"] not in existing]
    print(f"[generate] {len(items)} items ({len(TYPES)} types x {A.n_topics} topics); "
          f"{len(todo)} to make, {len(existing)} already checkpointed", flush=True)
    if todo:
        pool = A.workers or sum(PROVIDER_CONCURRENCY.values())
        n_ok = 0
        with ThreadPoolExecutor(max_workers=pool) as ex:
            futs = {ex.submit(gen_item, s): s for s in todo}
            for n, fut in enumerate(as_completed(futs), 1):
                s = futs[fut]
                try:
                    rec = fut.result()
                except Exception as e:
                    print(f"    [{s['item_id']} / {s['gen_provider']}] DROPPED: "
                          f"{str(e)[:120]}", flush=True)
                    continue
                _jsonl_append(A.gen_file, rec)
                n_ok += 1
                if n % 5 == 0 or n == len(todo):
                    print(f"    {n}/{len(todo)} generated", flush=True)
        print(f"  {n_ok} new items written", flush=True)
    rows = _jsonl_read(A.gen_file)
    by_gen = Counter(r["gen_provider"] for r in rows)
    leaky = [r["item_id"] for r in rows if r.get("label_word_leak")]
    metaed = [r["item_id"] for r in rows if r.get("meta_stripped")]
    print(f"\n  corpus: {len(rows)} items -> {A.gen_file}")
    print(f"  per-generator counts: {dict(sorted(by_gen.items()))}")
    print(f"  mean chars/turn: {sum(len(r['text']) for r in rows) / max(1, len(rows)):.0f}")
    print(f"  items needing meta strip: {len(metaed)}")
    print(f"  items whose prose contains a label word (FLAGGED, sensitivity only): "
          f"{len(leaky)}")
    if rows:
        s = sorted(rows, key=lambda r: r["item_id"])[0]
        print(f"\n  SAMPLE [{s['prescribed_type']} / {s['topic_id']} / "
              f"{s['gen_provider']}]: {s['text'][:200]}")
    return rows


# =====================================================================
# STAGE 2 -- LABEL
# =====================================================================
def build_rubric(order):
    """Reader rubric. Option order is SHUFFLED per batch so no label owns a position.

    The 7 definitions are the SAME STRINGS given to the generator. That symmetry is
    deliberate: the reader is asked exactly the question the generator was told to
    answer, so a miss is a compliance failure and not a definitional mismatch.
    """
    body = "\n".join(f"{t} - {TYPE_DEFS[t]}" for t in order)
    return (
        "You will read short excerpts, each one a single reply turn from an ordinary "
        "conversation. For EACH excerpt, choose the ONE label below that best describes "
        "what the turn is mainly doing. These are descriptions of behaviour, nothing more.\n\n"
        + body +
        "\n\nHOW TO CHOOSE:\n"
        "1. PICK THE DOMINANT ONE. Real turns mix. Choose the single label doing the "
        "most work in the excerpt.\n"
        "2. Judge only what is in front of you. You do not see what the person said; do "
        "not guess it.\n"
        "3. Every excerpt gets exactly one label, and you must choose one of the labels "
        "above. There is no 'none of these' option."
    )


def make_batches(item_list, batch_size, seed, max_per_topic):
    """Shuffle, then deterministically reduce same-TOPIC duplicates inside a batch.

    A reader that sees several turns on one topic in one prompt can contrast them and
    infer structure that the prose alone does not carry. Topic carries no type
    information, so spreading topics across batches removes that crutch without
    leaking anything. Residual violations are REPORTED, not silently tolerated.
    """
    items = list(item_list)
    random.Random(seed).shuffle(items)
    batches = [items[k:k + batch_size] for k in range(0, len(items), batch_size)]
    swaps = 0
    for bi, b in enumerate(batches):
        counts = Counter(x["topic_id"] for x in b)
        for pos, t in enumerate(b):
            if counts[t["topic_id"]] <= max_per_topic:
                continue
            moved = False
            for bj in range(len(batches)):                    # deterministic scan
                if bj == bi:
                    continue
                ocounts = Counter(x["topic_id"] for x in batches[bj])
                if ocounts.get(t["topic_id"], 0) + 1 > max_per_topic:
                    continue
                for opos, o in enumerate(batches[bj]):
                    if o["topic_id"] == t["topic_id"]:
                        continue
                    if counts.get(o["topic_id"], 0) + 1 > max_per_topic:
                        continue
                    batches[bi][pos], batches[bj][opos] = o, t
                    counts[t["topic_id"]] -= 1
                    counts[o["topic_id"]] = counts.get(o["topic_id"], 0) + 1
                    swaps += 1
                    moved = True
                    break
                if moved:
                    break
            if moved:
                b = batches[bi]
    residual = 0
    for b in batches:
        for _, c in Counter(x["topic_id"] for x in b).items():
            residual += max(0, c - max_per_topic)
    return batches, swaps, residual


def parse_labels(answer_text, alias_to_item):
    """STRICT parse. Returns (mapping item_id->code, status).

    Mandatory, all three:
      * a JSON array must be parseable out of the ANSWER text (never the trace);
      * every id must be an alias actually shown in THIS batch -- BATCH-UID
        INTERSECTION, so a hallucinated id can never overwrite a real label from
        another batch;
      * every alias in the batch must appear exactly once.
    Anything less returns an empty mapping and a status the caller routes to repair.
    """
    m = re.search(r"\[.*\]", answer_text, re.S)
    if not m:
        return {}, "no_json_array"
    raw = m.group(0)
    try:
        rows = json.loads(raw)
    except Exception:
        # tolerate trailing commas / stray prose, but still require object-shaped
        # records -- never a bare code scraped out of prose.
        rows = []
        for block in re.findall(r"\{[^{}]*\}", raw, re.S):
            idm = re.search(r'"id"\s*:\s*(\d+)', block)
            if not idm:
                continue
            lm = re.search(CODE_RE, block[idm.end():], re.I)
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
        lm = re.search(CODE_RE, str(row.get("label", "")), re.I)
        if not lm or aid not in alias_to_item:        # hallucinated id -> dropped
            continue
        out.setdefault(alias_to_item[aid], lm.group(1).upper())
    if len(out) != len(alias_to_item):
        return {}, f"incomplete_{len(out)}_of_{len(alias_to_item)}"
    return out, "ok"


def read_batch(reader, model, batch, alias_seed, rubric_seed, allow_reasoning_only):
    """ONE labelling call. One excerpt per turn, no context, no topic, no ids that mean
    anything. Returns a checkpointable record."""
    aliases = random.Random(alias_seed).sample(range(1000, 10000), len(batch))
    alias_to_item = {a: it["item_id"] for a, it in zip(aliases, batch)}
    order = list(TYPES)
    random.Random(rubric_seed).shuffle(order)
    menu = "|".join(TYPES)
    blocks = [f'--- EXCERPT {a} ---\n{it["text"]}' for a, it in zip(aliases, batch)]
    client = _client(reader, model)
    prompt = (build_rubric(order) + "\n\nExcerpts to label:\n" + "\n\n".join(blocks) +
              '\n\nReturn ONLY a JSON array as your FINAL ANSWER: '
              f'[{{"id": <number>, "label": "<{menu}>"}}]. '
              "Every excerpt id above must appear exactly once. Use only the labels "
              "above. Do not put the array only in your reasoning - it must be in the "
              "answer.")
    r = call_with_retry(client, reader, model=model, max_tokens=MAXTOK_LABEL,
                        temperature=0.0, messages=[{"role": "user", "content": prompt}])
    ans, rea = _split_text(r)
    finish = r.choices[0].finish_reason
    base = {"reader": reader, "labels": {}, "n_ans": len(ans), "n_rea": len(rea),
            "rubric_order": order, "item_ids": [it["item_id"] for it in batch]}
    if finish != "stop":
        # GLM's old failure mode: the reasoning trace ate the budget, finish=='length',
        # zero labels. Enforced, never silently accepted as a partial read.
        base["status"] = f"finish_{finish}"
        return base
    if not ans.strip():
        if not allow_reasoning_only:
            base["status"] = "reasoning_only_refused"
            return base
        ans = rea
    mapping, status = parse_labels(ans, alias_to_item)
    base["labels"] = mapping
    base["status"] = status
    return base


def _batch_key(reader, item_ids):
    return f"{reader}|" + hashlib.sha256(
        ",".join(sorted(item_ids)).encode()).hexdigest()[:16]


def _run_jobs(jobs, pool, ckpt_path, allow_reasoning_only, done_keys, label):
    todo = [j for j in jobs if j["key"] not in done_keys]
    print(f"  {label}: {len(todo)} calls to make "
          f"({len(jobs) - len(todo)} already checkpointed)", flush=True)
    stats, t0 = Counter(), time.time()
    if not todo:
        return stats
    with ThreadPoolExecutor(max_workers=pool) as ex:
        futs = {ex.submit(read_batch, j["reader"], MODELS[j["reader"]], j["batch"],
                          j["alias_seed"], j["rubric_seed"], allow_reasoning_only): j
                for j in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            j = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                print(f"    [{j['reader']}] call ERROR {str(e)[:110]}", flush=True)
                stats["call_error"] += 1
                continue
            res["key"] = j["key"]
            _jsonl_append(ckpt_path, res)          # checkpoint as it lands
            done_keys.add(j["key"])
            stats[res["status"]] += 1
            if n % 5 == 0 or res["status"] != "ok":
                print(f"    {n}/{len(todo)} ({time.time()-t0:.0f}s) {j['reader']}: "
                      f"{res['status']} ({len(res['labels'])} labels)", flush=True)
    return stats


def collect_marks(ckpt_path, by_item):
    """Rebuild reader -> {item_id: code} from the checkpoint.

    Enforces generator != labeller a SECOND time, structurally, at collection: a
    checkpoint row from an earlier run with a different rotation can never contribute
    a self-read. First write wins, so a later batch never overwrites a genuine label.
    """
    marks = defaultdict(dict)
    for row in _jsonl_read(ckpt_path):
        if row.get("status") != "ok":
            continue
        reader = row.get("reader")
        for iid, code in (row.get("labels") or {}).items():
            it = by_item.get(iid)
            if it is None:
                continue
            if it["gen_provider"] == reader:          # separation, enforced structurally
                continue
            marks[reader].setdefault(iid, code)
    return marks


def stage_label(A, items):
    by_item = {it["item_id"]: it for it in items}
    ckpt = A.label_ckpt
    max_per_topic = max(1, math.ceil(A.batch_size / max(1, A.n_topics)))
    print(f"[label] {len(items)} items; 3 blind readers each "
          f"(never the item's own generator)", flush=True)

    jobs, batch_meta = [], []
    for ri, reader in enumerate(ORDER):
        # generator != labeller, enforced at job-build time.
        mine = [it for it in items if it["gen_provider"] != reader]
        batches, swaps, residual = make_batches(mine, A.batch_size,
                                                SEED_BATCH_BASE + ri, max_per_topic)
        batch_meta.append({"reader": reader, "n_items": len(mine),
                           "n_batches": len(batches), "topic_spread_swaps": swaps,
                           "residual_same_topic_excess": residual})
        for bi, b in enumerate(batches):
            jobs.append({"reader": reader, "batch": b,
                         "alias_seed": SEED_ALIAS_BASE + ri * 10000 + bi,
                         "rubric_seed": SEED_RUBRIC_BASE + ri * 10000 + bi,
                         "key": _batch_key(reader, [x["item_id"] for x in b])})

    done = {r["key"] for r in _jsonl_read(ckpt) if r.get("key")}
    pool = A.workers or sum(PROVIDER_CONCURRENCY.values())
    print(f"  {len(jobs)} labelling calls (batch={A.batch_size}, "
          f"max {max_per_topic}/topic per batch); topic-spread swaps "
          f"{[(m['reader'], m['topic_spread_swaps']) for m in batch_meta]}", flush=True)
    stats = _run_jobs(jobs, pool, ckpt, A.allow_reasoning_only, done, "main pass")

    # ---- REPAIR PASS ----
    # Coverage on this panel is lost to parse/finish_reason drops, not to call
    # failure, so re-asking only the missing items in small batches is what makes
    # 3-reader coverage reachable at all.
    for rnd in range(A.repair_rounds):
        marks = collect_marks(ckpt, by_item)
        missing = []
        for ri, reader in enumerate(ORDER):
            want = {it["item_id"] for it in items if it["gen_provider"] != reader}
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
            batches, _, _ = make_batches([by_item[i] for i in gap],
                                         A.repair_batch_size,
                                         SEED_BATCH_BASE + ri + 100 * (rnd + 1),
                                         max_per_topic)
            for bi, b in enumerate(batches):
                rjobs.append({
                    "reader": reader, "batch": b,
                    "alias_seed": SEED_ALIAS_BASE + 500000 * (rnd + 1) + ri * 10000 + bi,
                    "rubric_seed": SEED_RUBRIC_BASE + 500000 * (rnd + 1) + ri * 10000 + bi,
                    "key": _batch_key(reader, [x["item_id"] for x in b])})
        stats += _run_jobs(rjobs, pool, ckpt, A.allow_reasoning_only, done,
                           f"repair round {rnd+1}")

    marks = collect_marks(ckpt, by_item)
    got = Counter(len([p for p in ORDER if it["item_id"] in marks.get(p, {})])
                  for it in items)
    print(f"\n  call statuses: {dict(stats)}")
    print(f"  readers-per-item distribution: {dict(sorted(got.items()))} "
          f"(3 = complete case)")
    return marks, batch_meta, dict(stats)


# =====================================================================
# STAGE 3 -- SCORE
# =====================================================================
def consensus_of(codes):
    """>=2 AGREEING among the PRESENT labels -> consensus. Ties -> no consensus."""
    if not codes:
        return None, 0
    c = Counter(codes)
    top, n = c.most_common(1)[0]
    if n < 2:
        return None, n
    if sum(1 for _, v in c.items() if v == n) > 1:      # tie between two codes
        return None, n
    return top, n


def stage_score(A, items, marks, batch_meta, call_stats):
    by_item = {it["item_id"]: it for it in items}
    per_item = []
    for iid, it in sorted(by_item.items()):
        readers = [p for p in ORDER if iid in marks.get(p, {})]
        codes = [marks[p][iid] for p in readers]
        cons, votes = consensus_of(codes)
        per_item.append({
            "item_id": iid,
            "prescribed_type": it["prescribed_type"],
            "topic_id": it["topic_id"],
            "gen_provider": it["gen_provider"],
            "n_readers": len(readers),
            "reader_codes": {p: marks[p][iid] for p in readers},
            "consensus": cons,
            "consensus_votes": votes,
            "correct": (cons == it["prescribed_type"]) if cons else None,
            "label_word_leak": it.get("label_word_leak", []),
            "meta_stripped": it.get("meta_stripped", []),
        })

    n_items = len(per_item)
    n_complete = sum(1 for r in per_item if r["n_readers"] == 3)
    n_consensus = sum(1 for r in per_item if r["consensus"])
    n_correct = sum(1 for r in per_item if r["correct"])

    acc_consensus = n_correct / n_consensus if n_consensus else 0.0
    acc_all = n_correct / n_items if n_items else 0.0     # no-consensus counted WRONG

    # ---- per-type recall (both denominators, stated) ----
    per_type = {}
    for t in TYPES:
        rows = [r for r in per_item if r["prescribed_type"] == t]
        cons_rows = [r for r in rows if r["consensus"]]
        hit = sum(1 for r in cons_rows if r["correct"])
        per_type[t] = {
            "n_items": len(rows),
            "n_with_consensus": len(cons_rows),
            "n_correct": hit,
            "recall_of_consensus_items": round(hit / len(cons_rows), 4) if cons_rows else None,
            "recall_of_all_items": round(hit / len(rows), 4) if rows else None,
        }

    # ---- full 7x7 confusion matrix (prescribed rows x consensus-read cols) ----
    confusion = {p: {c: 0 for c in TYPES} for p in TYPES}
    no_consensus_by_type = {t: 0 for t in TYPES}
    for r in per_item:
        if r["consensus"]:
            confusion[r["prescribed_type"]][r["consensus"]] += 1
        else:
            no_consensus_by_type[r["prescribed_type"]] += 1

    # ---- Fleiss kappa on COMPLETE cases only (3 readers, honest denominator) ----
    rows3 = [list(r["reader_codes"].values()) for r in per_item if r["n_readers"] == 3]
    kappa = round(fleiss_kappa(rows3), 4) if len(rows3) >= 2 else None
    # raw pairwise agreement among complete cases
    pair_tot = pair_agree = 0
    for codes in rows3:
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                pair_tot += 1
                pair_agree += int(codes[i] == codes[j])
    raw_agreement = round(pair_agree / pair_tot, 4) if pair_tot else None

    # ---- per-GENERATOR compliance (a confound for the hybrid if it varies) ----
    per_generator = {}
    for p in ORDER:
        rows = [r for r in per_item if r["gen_provider"] == p]
        cons_rows = [r for r in rows if r["consensus"]]
        hit = sum(1 for r in cons_rows if r["correct"])
        per_generator[p] = {
            "model": MODELS[p],
            "n_items": len(rows),
            "n_with_consensus": len(cons_rows),
            "n_correct": hit,
            "acc_of_consensus_items": round(hit / len(cons_rows), 4) if cons_rows else None,
            "acc_of_all_items": round(hit / len(rows), 4) if rows else None,
        }
    accs = [v["acc_of_consensus_items"] for v in per_generator.values()
            if v["acc_of_consensus_items"] is not None]
    gen_spread = round(max(accs) - min(accs), 4) if len(accs) >= 2 else None

    # ---- per-READER accuracy vs prescribed (diagnostic, not the headline) ----
    per_reader = {}
    for p in ORDER:
        got = marks.get(p, {})
        hit = sum(1 for iid, code in got.items()
                  if code == by_item[iid]["prescribed_type"])
        per_reader[p] = {"model": MODELS[p], "n_labels": len(got),
                         "acc_vs_prescribed": round(hit / len(got), 4) if got else None}

    # ---- label-word-leak sensitivity ----
    clean_rows = [r for r in per_item if not r["label_word_leak"] and r["consensus"]]
    leak_rows = [r for r in per_item if r["label_word_leak"] and r["consensus"]]
    leak_sens = {
        "n_items_with_label_word": sum(1 for r in per_item if r["label_word_leak"]),
        "acc_excluding_label_word_items": (
            round(sum(1 for r in clean_rows if r["correct"]) / len(clean_rows), 4)
            if clean_rows else None),
        "n_excluding": len(clean_rows),
        "acc_on_label_word_items": (
            round(sum(1 for r in leak_rows if r["correct"]) / len(leak_rows), 4)
            if leak_rows else None),
        "n_label_word_items": len(leak_rows),
        "note": "LEAK_TERMS for ANSWER/PLAN/REFUSE are ordinary English and fire on "
                "innocent prose too. This is a SENSITIVITY, never silently applied.",
    }

    # ---- significance vs the 1/7 chance level ----
    p_consensus = binom_tail_ge(n_correct, n_consensus, CHANCE) if n_consensus else None
    p_all = binom_tail_ge(n_correct, n_items, CHANCE) if n_items else None

    verdict, verdict_text = _verdict(acc_consensus, n_consensus)

    report = {
        "INTERPRETATION_RULE": INTERPRETATION_RULE,
        "VERDICT": verdict,
        "VERDICT_TEXT": verdict_text,
        "what_this_is_not": (
            "Not a surface control, not a CAS claim, not a validation of the turn-type "
            "-> board mapping. Ground truth here is the PRESCRIBED type -- an "
            "instruction, not a verified property of the text. The gap between the two "
            "is exactly what is being measured."),
        "run": {
            "smoke": A.smoke,
            "n_topics": A.n_topics,
            "n_types": len(TYPES),
            "n_items": n_items,
            "batch_size": A.batch_size,
            "readers_panel": MODELS,
            "generator_rotation": ORDER,
            "chance_level": round(CHANCE, 4),
            "high_recovery_threshold": HIGH_RECOVERY,
            "script_sha256": _sha256(os.path.abspath(__file__)),
            "gen_file": A.gen_file,
            "label_ckpt": A.label_ckpt,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "turn_type_definitions": TYPE_DEFS,
        "topics": [{"topic_id": t[0], "name": t[1], "user_msg": t[2]}
                   for t in TOPICS[:A.n_topics]],
        "coverage": {
            "n_items": n_items,
            "n_items_with_3_readers": n_complete,
            "complete_coverage": round(n_complete / n_items, 4) if n_items else None,
            "n_items_with_consensus": n_consensus,
            "consensus_coverage": round(n_consensus / n_items, 4) if n_items else None,
            "consensus_rule": ">=2 AGREEING among the PRESENT labels; a 3-way split or "
                              "a tie is NO consensus",
        },
        "recovery": {
            "n_correct": n_correct,
            "acc_of_consensus_items": round(acc_consensus, 4),
            "acc_of_all_items_no_consensus_counted_wrong": round(acc_all, 4),
            "chance": round(CHANCE, 4),
            "margin_over_chance": round(acc_consensus - CHANCE, 4),
            "binomial_p_one_sided_consensus_items": (
                None if p_consensus is None else float(f"{p_consensus:.3e}")),
            "binomial_p_one_sided_all_items": (
                None if p_all is None else float(f"{p_all:.3e}")),
        },
        "per_type": per_type,
        "confusion_prescribed_x_consensus": confusion,
        "no_consensus_by_prescribed_type": no_consensus_by_type,
        "inter_reader": {
            "fleiss_kappa_complete_cases": kappa,
            "n_complete_cases": len(rows3),
            "raw_pairwise_agreement_complete_cases": raw_agreement,
        },
        "per_generator_compliance": per_generator,
        "per_generator_spread": gen_spread,
        "per_reader_diagnostic": per_reader,
        "label_word_leak_sensitivity": leak_sens,
        "labelling_batch_meta": batch_meta,
        "labelling_call_statuses": call_stats,
        "per_item": per_item,
    }
    with open(A.report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print_summary(report, A)
    return report


INTERPRETATION_RULE = (
    "RECOVERY AT OR NEAR 0.1429 (chance for a 7-way choice) => models CANNOT reliably "
    "hit a prescribed turn type, the hybrid corpus has NO GROUND TRUTH, and it MUST BE "
    "ABANDONED rather than repaired. | RECOVERY HIGH (>0.60) => the prescribed type IS "
    "recoverable and the hybrid has a FLOOR -- but high recovery may partly reflect "
    "STYLISED, SURFACE-SEPARABLE text rather than genuine type compliance, so a SURFACE "
    "CONTROL IS STILL REQUIRED LATER. This does NOT validate the hybrid; it establishes "
    "a floor and nothing more. | ANYTHING BETWEEN is reported as-is, with no spin."
)


def _verdict(acc, n_consensus):
    if n_consensus == 0:
        return "NO_DATA", ("No item reached a >=2 reader consensus. Nothing is "
                           "established either way.")
    if acc <= CHANCE + 0.05:
        return "AT_CHANCE__HYBRID_MUST_BE_ABANDONED", (
            f"Recovery {acc:.4f} is at or near the {CHANCE:.4f} chance level. A "
            f"prescribed type that blind readers cannot recover from the prose is not "
            f"a label. The hybrid corpus has NO GROUND TRUTH and must be ABANDONED, "
            f"not repaired.")
    if acc > HIGH_RECOVERY:
        return "FLOOR_ESTABLISHED__NOT_VALIDATED", (
            f"Recovery {acc:.4f} is above the {HIGH_RECOVERY} bar, so the prescribed "
            f"type IS recoverable from the prose and the hybrid has a FLOOR. HONESTLY: "
            f"this may partly reflect stylised, surface-separable text rather than "
            f"genuine type compliance -- a model told to write a PLAN may emit a "
            f"numbered list that a word-unigram model recovers just as well. A SURFACE "
            f"CONTROL IS STILL REQUIRED. The hybrid is NOT validated by this result.")
    return "INTERMEDIATE__REPORTED_AS_IS", (
        f"Recovery {acc:.4f} sits between the {CHANCE:.4f} chance level and the "
        f"{HIGH_RECOVERY} bar. No verdict is drawn. The number is reported as-is; "
        f"whoever decides the hybrid's fate decides it on this number, not on a label "
        f"attached to it here.")


def print_summary(rep, A):
    R, C, IR = rep["recovery"], rep["coverage"], rep["inter_reader"]
    W = 78
    print("\n" + "=" * W)
    print("PRESCRIBED-TURN-TYPE COMPLIANCE CHECK" + ("  [SMOKE]" if A.smoke else ""))
    print("=" * W)
    print(f"items {C['n_items']}  ({len(TYPES)} types x {A.n_topics} topics)   "
          f"chance = {CHANCE:.4f}")
    print("\nCOVERAGE")
    print(f"  3 readers          : {C['n_items_with_3_readers']}/{C['n_items']}  "
          f"({C['complete_coverage']})")
    print(f"  >=2 consensus      : {C['n_items_with_consensus']}/{C['n_items']}  "
          f"({C['consensus_coverage']})")
    print("\nRECOVERY")
    print(f"  accuracy on consensus items      : {R['acc_of_consensus_items']:.4f}  "
          f"({R['n_correct']}/{C['n_items_with_consensus']})")
    print(f"  accuracy on ALL items            : "
          f"{R['acc_of_all_items_no_consensus_counted_wrong']:.4f}  "
          f"(no-consensus counted WRONG)")
    print(f"  chance                           : {R['chance']:.4f}")
    print(f"  margin over chance               : {R['margin_over_chance']:+.4f}")
    print(f"  binomial p (one-sided, consensus): "
          f"{R['binomial_p_one_sided_consensus_items']}")
    print("\nINTER-READER")
    print(f"  Fleiss kappa (complete cases)    : {IR['fleiss_kappa_complete_cases']}  "
          f"(n={IR['n_complete_cases']})")
    print(f"  raw pairwise agreement           : "
          f"{IR['raw_pairwise_agreement_complete_cases']}")
    print("\nPER-TYPE RECALL (of items that reached consensus)")
    for t in TYPES:
        d = rep["per_type"][t]
        bar = "" if d["recall_of_consensus_items"] is None else \
            "#" * int(round(d["recall_of_consensus_items"] * 20))
        print(f"  {t:<10} {str(d['recall_of_consensus_items']):<7} "
              f"({d['n_correct']}/{d['n_with_consensus']} of {d['n_items']} items) {bar}")
    print("\nCONFUSION MATRIX  (rows = PRESCRIBED, cols = CONSENSUS READ)")
    hdr = "  " + " " * 11 + "".join(f"{t[:5]:>7}" for t in TYPES) + f"{'noCons':>8}"
    print(hdr)
    for p in TYPES:
        row = "".join(f"{rep['confusion_prescribed_x_consensus'][p][c]:>7}" for c in TYPES)
        print(f"  {p:<11}{row}{rep['no_consensus_by_prescribed_type'][p]:>8}")
    print("\nPER-GENERATOR COMPLIANCE  (a big spread would CONFOUND the hybrid)")
    for p in ORDER:
        d = rep["per_generator_compliance"][p]
        print(f"  {p:<9} {d['model']:<18} {str(d['acc_of_consensus_items']):<7} "
              f"({d['n_correct']}/{d['n_with_consensus']} of {d['n_items']} items)")
    print(f"  spread (max-min) : {rep['per_generator_spread']}")
    print("\nPER-READER (diagnostic only -- readers are not the object under test)")
    for p in ORDER:
        d = rep["per_reader_diagnostic"][p]
        print(f"  {p:<9} {d['model']:<18} acc_vs_prescribed={d['acc_vs_prescribed']} "
              f"(n={d['n_labels']})")
    L = rep["label_word_leak_sensitivity"]
    print("\nLABEL-WORD LEAK SENSITIVITY")
    print(f"  items whose prose contains a label word : {L['n_items_with_label_word']}")
    print(f"  accuracy EXCLUDING those items          : "
          f"{L['acc_excluding_label_word_items']} (n={L['n_excluding']})")
    print(f"  accuracy ON those items                 : "
          f"{L['acc_on_label_word_items']} (n={L['n_label_word_items']})")
    print("\n" + "-" * W)
    print("INTERPRETATION RULE (frozen in the script docstring):")
    for chunk in INTERPRETATION_RULE.split(" | "):
        print("  * " + chunk.strip())
    print("-" * W)
    print(f"VERDICT: {rep['VERDICT']}")
    print(f"  {rep['VERDICT_TEXT']}")
    print("-" * W)
    print(f"wrote {A.report_file}")


# =====================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--smoke", action="store_true",
                    help="2 topics x 7 types = 14 items. RUN THIS FIRST.")
    ap.add_argument("--stage", default="all",
                    choices=["all", "generate", "label", "score"])
    ap.add_argument("--n-topics", type=int, default=None,
                    help="override the topic count (default 6, or 2 under --smoke)")
    ap.add_argument("--batch-size", type=int, default=6)
    ap.add_argument("--repair-batch-size", type=int, default=4)
    ap.add_argument("--repair-rounds", type=int, default=2)
    ap.add_argument("--workers", type=int, default=0,
                    help="0 = sum of per-provider concurrency (9)")
    ap.add_argument("--allow-reasoning-only", action="store_true",
                    help="accept labels scraped from the reasoning trace when the "
                         "answer is empty. OFF by default: a chain-of-thought aside "
                         "is not a considered label.")
    ap.add_argument("--out-dir", default=HERE)
    A = ap.parse_args()

    if A.n_topics is None:
        A.n_topics = 2 if A.smoke else len(TOPICS)
    A.n_topics = max(1, min(A.n_topics, len(TOPICS)))
    tag = "_smoke" if A.smoke else ""
    A.gen_file = os.path.join(A.out_dir, f"compliance_gen{tag}.jsonl")
    A.label_ckpt = os.path.join(A.out_dir, f"compliance_label_ckpt{tag}.jsonl")
    A.report_file = os.path.join(A.out_dir, f"compliance_report{tag}.json")

    plan = build_items(A.n_topics)
    print(f"compliance check: {len(TYPES)} types x {A.n_topics} topics = {len(plan)} "
          f"items; generator rotates over {ORDER}", flush=True)

    if A.stage in ("all", "generate"):
        stage_generate(A, plan)
    if A.stage == "generate":
        return

    rows = _jsonl_read(A.gen_file)
    wanted = {s["item_id"] for s in plan}
    items = [r for r in rows if r["item_id"] in wanted]
    if not items:
        raise SystemExit(f"no generated items in {A.gen_file}; run --stage generate first.")
    if len(items) < len(plan):
        print(f"\n  NOTE: {len(plan) - len(items)} of {len(plan)} items failed "
              f"generation and are absent from the corpus. Reported denominators are "
              f"the {len(items)} items that exist.", flush=True)

    if A.stage in ("all", "label"):
        marks, batch_meta, call_stats = stage_label(A, items)
    else:
        by_item = {it["item_id"]: it for it in items}
        marks = collect_marks(A.label_ckpt, by_item)
        batch_meta, call_stats = [], {}
    if A.stage == "label":
        return

    stage_score(A, items, marks, batch_meta, call_stats)


if __name__ == "__main__":
    main()
