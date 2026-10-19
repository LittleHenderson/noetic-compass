"""score_scribe_l4.py -- score the existing small English model (Scribe L4) on the sealed 98. PREPARED, NOT RUN.

Status: NOT_RUN pending the owner's word. See SCORE_SCRIBE_L4_PLAN.md in this folder.

What it scores, and nothing else:
  1. Round-trip check   parse(render(C_hat)) == C_hat
       a. the Scribe's own shim (cce_shim.verify_round_trip, the check it was trained against), and
       b. the real language_v3 cce.py (cce.round_trip), through a declared adapter (scribe_to_cce below).
  2. Exact match        cce.normalize(scribe_to_cce(C_hat)) == cce.normalize(gold), where gold is the row's own
                        bridge-v2 parse turned into CCE content by language_v3 scoring.content_from_parse.
It never prints or stores sealed row text. It writes counts only, plus hashes.

Needs torch (CPU is enough: inference only, 98 sentences). It must NOT run on the owner's laptop (about 300 MB free
RAM; no torch import locally). Intended host: an AWS CPU instance such as t3.medium. It refuses to start without
an owner approval file that names this job.

Inputs (all checked by sha256 before anything runs):
  --weights   scribe_l4_weights.pt  from branch helm/creativity-rpa-valve-v1, commit 84812689,
              path HELM_DISTRIBUTION_PACKAGE/scribe_l4_aws_gpu_training/outputs/scribe_l4_weights.pt
  --vocab     scribe_vocab.json     same folder
  --scribe-src a folder holding scribe_model.py and cce_shim.py taken from the same commit
              (scribe_l4_aws_gpu_training/scribe_model.py, scribe_l4_aws_gpu_training/cce_shim.py)
  --lang-v3   docs/working/noetic_council/language_v3 (cce.py, scoring.py, aliaswide.py)
  --bridge    the folder that holds sdg_bridge_v2 (scoring.py imports it)
  --sealed    cas-synthetic/data/l4_split/real_heldout_unparseables_98.jsonl
  --approval  owner approval file; must contain the line  APPROVE SCORE_SCRIBE_L4_SEALED_98
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

WEIGHTS_SHA = "e36cf3cb50fe8ae168b2986a97000a47e7632b058b34b44629f4f17f99af9dc1"
VOCAB_SHA = "6746e5dbd77dc6ddaa7bd7270b21ca2558c4da2e439522a2fbcffc66ce4dbc1a"
SEALED_SHA = "e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe"
APPROVAL_LINE = "APPROVE SCORE_SCRIBE_L4_SEALED_98"
SOURCE_COMMIT = "84812689b6fb6de4250dc9bf2e400df88a95944c"

# Scribe subject / object words -> Noetic numbers (the canonical names, CLAUDE.md "The 10 Noetics").
NOETIC_OF_NAME = {"Idea": 0, "Mind": 1, "Positive": 2, "Negative": 3, "Vibration": 4, "Female": 5, "Male": 6,
                  "Rhythm": 7, "Above/Cause": 8, "Below/Effect": 9}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scribe_to_cce(pred, cce):
    """Declared adapter: Scribe content -> language_v3 CCE content.

    Returns (content, None) or (None, reason). CLARIFY -> (None, "CLARIFY").

    The Scribe emits ONE clause: subject, verb, object, domain, register, drive (no coefficients, no recipe).
    The real CCE has exactly one frame family that says such a clause: the ^1 Mind act frames
    '{M} intakes / processes / stores / outputs {I}' (cce.py TEMPLATES). So:
      * subject 'Mind'  -> one ^1 term, slots M='Mind' (declared by the relation 'Mind is a Mind'),
                           I='"<object word>"' (a quoted Idea, the CCE Idea slot form), ACT=<verb>,
                           plus the Scribe's own domain, register and drive. Nothing is added or dropped.
      * any other subject (Positive, Negative, Male, Female) -> (None, "NO_CCE_FRAME"): no CCE frame lets a
        non-Mind subject intake / process / store / output. Counted as a round-trip failure, never patched.
    Checked on the laptop (stdlib, no torch, no sealed row): all 4 verbs x {Idea, Above/Cause} round-trip ok.
    Every sealed gold is a recipe (two or three weighted states and a named outcome), so exact match is
    expected to be 0 of 98 by construction; the plan says so before the run.
    """
    if pred.get("turn_type") != "ANSWER":
        return None, "CLARIFY"
    if pred["subject"] != "Mind":
        return None, "NO_CCE_FRAME"
    c = cce.empty_content()
    c["relations"] = [["is_a", "Mind", "Mind"]]
    c["terms"] = [{"noetic": NOETIC_OF_NAME["Mind"], "domain": pred["domain"], "register": [pred["register"]],
                   "drive": pred["drive"], "polarity": "ASSERTED",
                   "slots": {"M": "Mind", "I": '"%s"' % pred["object"], "ACT": pred["verb"]}}]
    return c, None


def predict(model, tokenizer, english, lists, torch):
    """Same decoding as train_scribe_job.py at commit 84812689 (argmax per head)."""
    ids = tokenizer.encode(english)
    with torch.no_grad():
        out = model(torch.tensor([ids], dtype=torch.long))
    pick = {k: int(v.argmax(dim=-1).item()) for k, v in out.items()}
    if lists["TURN_TYPES"][pick["turn_type"]] == "CLARIFY":
        return {"turn_type": "CLARIFY", "missing_slot": "meaning"}
    return {"turn_type": "ANSWER", "domain": lists["DOMAINS_LIST"][pick["domain"]],
            "register": lists["REGISTERS_LIST"][pick["register"]], "drive": lists["DRIVES_LIST"][pick["drive"]],
            "verb": lists["VERBS_LIST"][pick["verb"]], "subject": lists["SUBJECTS_LIST"][pick["subject"]],
            "object": lists["OBJECTS_LIST"][pick["object"]]}


def input_stats(tokenizer, english):
    words = english.lower().replace("-", " ").replace("/", " ").split()
    known = sum(1 for w in words if w.strip(".,:;!?()[]{}'\"") in tokenizer.vocab)
    return len(words), known


def main():
    ap = argparse.ArgumentParser()
    for name in ("weights", "vocab", "scribe-src", "lang-v3", "bridge", "sealed", "approval", "out"):
        ap.add_argument("--" + name, required=True)
    a = ap.parse_args()

    # Gate 0: owner approval and input hashes, before torch is even imported.
    if APPROVAL_LINE not in Path(a.approval).read_text("utf-8"):
        raise SystemExit("REFUSED: approval file lacks the line %r (status stays NOT_RUN)" % APPROVAL_LINE)
    out = Path(a.out)
    if out.exists():
        raise SystemExit("REFUSED: %s exists; the sealed 98 are scored once" % out)
    for path, want in ((a.weights, WEIGHTS_SHA), (a.vocab, VOCAB_SHA), (a.sealed, SEALED_SHA)):
        got = sha256(path)
        if got != want:
            raise SystemExit("REFUSED: %s sha256 %s, expected %s" % (path, got, want))
    sealed_before = sha256(a.sealed)

    for p in (a.scribe_src, a.lang_v3, a.bridge):
        sys.path.insert(0, str(Path(p).resolve()))
    import cce            # language_v3 (the real round-trip)
    import scoring        # language_v3 (gold content from the bridge-v2 parse)
    import cce_shim       # Scribe's own shim, commit 84812689
    import scribe_model   # Scribe architecture + tokenizer, commit 84812689
    import torch          # only here, on the approved host

    t0 = time.perf_counter()
    torch.set_num_threads(1)
    vocab = json.loads(Path(a.vocab).read_text("utf-8"))
    tok = scribe_model.SimpleTokenizer()
    tok.vocab = dict(vocab)
    tok.inv_vocab = {i: w for w, i in vocab.items()}
    model = scribe_model.create_pytorch_model(len(vocab))
    model.load_state_dict(torch.load(a.weights, map_location="cpu", weights_only=True))
    model.eval()
    lists = {k: getattr(scribe_model, k) for k in
             ("TURN_TYPES", "DOMAINS_LIST", "REGISTERS_LIST", "DRIVES_LIST", "VERBS_LIST", "SUBJECTS_LIST",
              "OBJECTS_LIST")}

    rows = [json.loads(x) for x in Path(a.sealed).read_bytes().decode("utf-8").splitlines() if x.strip()]
    c = Counter()
    words_total = words_known = 0
    for r in rows:
        n_words, n_known = input_stats(tok, r["english"])
        words_total += n_words
        words_known += n_known
        c["truncated_over_30_words"] += n_words > 30   # 32 ids = BOS + 30 words + EOS
        pred = predict(model, tok, r["english"], lists, torch)
        if pred["turn_type"] == "CLARIFY":
            c["clarify"] += 1
            continue
        c["answer"] += 1
        shim_ok, _, _ = cce_shim.verify_round_trip(pred)
        c["shim_round_trip_ok"] += bool(shim_ok)
        adapted, why = scribe_to_cce(pred, cce)
        if adapted is None:
            c["cce_round_trip_fail_" + why] += 1
            c["answered_without_cce_form"] += 1
            continue
        rt = cce.round_trip(adapted)
        c["cce_round_trip_ok"] += bool(rt["ok"])
        if not rt["ok"]:
            c["cce_round_trip_fail_" + str(rt["rejection"])] += 1
        gold = scoring.content_from_parse(r["parsed"])
        exact = cce.normalize(adapted) == cce.normalize(gold)
        c["exact_match_gold"] += exact
        c["exact_match_gold_and_cce_round_trip"] += exact and bool(rt["ok"])
        # The dangerous cell: a confident answer that passes the round trip yet is not the gold content.
        c["answered_round_trip_ok_but_not_gold"] += bool(rt["ok"]) and not exact

    sealed_after = sha256(a.sealed)
    receipt = {"job": "SCORE_SCRIBE_L4_SEALED_98", "source_commit": SOURCE_COMMIT,
               "scored_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "seconds": round(time.perf_counter() - t0, 3), "torch_version": torch.__version__,
               "rows": len(rows), "weights_sha256": WEIGHTS_SHA, "vocab_sha256": VOCAB_SHA,
               "sealed_sha256_before": sealed_before, "sealed_sha256_after": sealed_after,
               "sealed_unchanged": sealed_before == sealed_after == SEALED_SHA,
               "input_word_coverage": {"words": words_total, "known_to_vocab": words_known},
               "counts": dict(sorted(c.items())),
               "policy": "counts only; no row text, seed id or per-row prediction recorded; scored once"}
    out.write_text(json.dumps(receipt, indent=2) + "\n", "utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
