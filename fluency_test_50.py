"""fluency_test_50.py -- 50 frozen situations, two renderers, automatic checks only (no human judging yet).

Renderers:
  (i)  OLD  -- what HELM said before Fix F: HELMVoiceAdapter in helm_end_to_end_loop.py (success / missing /
              clarify) plus the fixed CCE surface forms in docs/working/noetic_council/language_v3/cce.py
              (UNDETERMINED "I cannot tell.", REFUSE "I will not do that: ...", CLARIFY "I need the amount for ...").
              learned / repaired / never-learned / faded have NO old form; the old loop answered anything it could
              not route with its clarify sentence, so that is what is used (flagged no_old_form in the output).
  (ii) NEW  -- helm_voice.HELMVoice, the 50 receipts played as ONE conversation (so repeats and memory reuse count).

Automatic checks, the same for both renderers:
  CAS tokens (notation + jargon words), repeated sentences (back-to-back identical outputs; any sentence said more
  than once), facts preserved (key receipt facts said, no invented numbers, no invented names), outcome words right,
  reading grade (Flesch-Kincaid, simple syllable count), sentence-length mean and variance, sentences per output.

Writes (next to the situations file): FLUENCY_50_OUTPUT.json, RATING_SHEET.md (blind A/B for human judges),
RATING_KEY.json (which of A/B is old/new; keep away from judges).

Usage:  python -X utf8 -B fluency_test_50.py
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import statistics
import sys
from decimal import Decimal, getcontext
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT_DIR = os.path.join(HERE, "docs", "working", "voice_20261018")
SITUATIONS_PATH = os.path.join(OUT_DIR, "FLUENCY_50_SITUATIONS.json")
CCE_DIR = os.path.join(HERE, "docs", "working", "noetic_council", "language_v3")

import helm_voice as hv  # noqa: E402

OLD_FORM = {"success", "blocked_missing", "dont_know", "cant_determine", "clarify", "refused"}


def _old_adapter():
    from helm_end_to_end_loop import HELMVoiceAdapter  # still used for format_clarify (unchanged by Fix C)
    return HELMVoiceAdapter


# The pre-Fix-C renderer text, frozen here verbatim (commit b322a0ac^ helm_end_to_end_loop.py:71-94) so the
# 50-situation baseline stays the same text the recorded results were measured against. Fix C (2026-10-18,
# PR #346) rewrote the live adapter's signatures, so the live module no longer carries these strings.
def _old_format_success(output_val, limiting_reagent, inputs, entropy, aperture, receipt_hash=None):
    rounded_val = round(float(output_val), 3)
    limiting_qty = inputs.get(limiting_reagent, 0)
    h_str = f" [receipt: {receipt_hash}]" if receipt_hash else ""
    return (
        f"All set! Based on your ingredients, we can produce exactly {rounded_val:,.3f} units.\n"
        f"Your bottleneck (limiting ingredient) is {limiting_reagent} with {limiting_qty} on hand, "
        f"which sets the ceiling for this batch.\n"
        f"(Verified with exact 40-digit Decimal precision; novelty entropy: {entropy:.2f}, "
        f"valve aperture: {aperture}){h_str}"
    )


def _old_format_missing_prerequisite(missing_items, reason):
    missing_str = ", ".join(missing_items)
    return (
        f"I can't run this batch just yet because we're missing essential ingredients: {missing_str}.\n"
        f"The system automatically halted to prevent guessing, errors, or wasting materials."
    )


def _cce_forms():
    sys.path.insert(0, CCE_DIR)
    import cce  # language_v3 fixed surface forms
    return cce


def old_render(r, adapter, cce):
    sit = hv.situation_of(r)
    tel = r.get("telemetry") or {}
    getcontext().prec = 40
    if sit == "success" or (sit == "repaired" and r.get("yield_value") is not None):
        fr = hv._as_fraction(r["yield_value"])
        y = Decimal(fr.numerator) / Decimal(fr.denominator)
        lim = r.get("limiting") or "Flour"
        inputs = {lim: Decimal(r["limiting_qty"])} if r.get("limiting_qty") else {}
        return _old_format_success(output_val=y, limiting_reagent=lim, inputs=inputs,
                                   entropy=float(tel.get("entropy", "0")), aperture=Decimal(tel.get("aperture", "0.5")),
                                   receipt_hash=r.get("receipt_id"))
    if sit == "blocked_missing":
        return _old_format_missing_prerequisite(list(r["missing"]), "G-ABSENT")
    if sit == "cant_determine":
        return cce.FIXED_UNDETERMINED
    if sit == "clarify":
        return "I need the amount for Ω_%s. What is it?" % hv.say_name(r["clarify_item"]).replace(" ", "_")
    if sit == "refused":
        return cce.REFUSE_LEAD + "%s." % r["reason"]
    return adapter.format_clarify()  # dont_know, and the four situations with no old form


def _sentences(text):
    import re
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()]


def _words(s):
    import re
    return re.findall(r"[A-Za-z']+|\d[\d.,/]*", s)


def measure(outputs, receipts, user_haves):
    rows = []
    all_sents = []
    seen = {}
    for i, (text, r, uh) in enumerate(zip(outputs, receipts, user_haves)):
        sit = hv.situation_of(r)
        toks = hv.cas_tokens(text)
        sents = _sentences(text)
        all_sents += sents
        for s in sents:
            seen[s] = seen.get(s, 0) + 1
        probs_outcome = [p for p in hv.verify(text, r, sit, user_have=uh, max_sentences=None)
                         if p.startswith(("NO_OUTCOME_WORD", "WRONG_OUTCOME_WORD"))]
        rows.append({"n": i + 1, "situation": sit, "text": text, "cas_tokens": toks,
                     "facts_preserved": hv.facts_preserved(text, r, user_have=uh),
                     "fact_problems": [p for p in hv.verify(text, r, sit, user_have=uh, check_outcome=False,
                                                            max_sentences=None) if not p.startswith("CAS_TOKENS")],
                     "outcome_words_right": not probs_outcome, "outcome_problems": probs_outcome,
                     "sentences": len(sents), "grade": round(hv.reading_grade(text), 2),
                     "repeat_of_previous": i > 0 and text == outputs[i - 1]})
    lens = [len(_words(s)) for s in all_sents]
    with_form = [x for x in rows if x["situation"] in OLD_FORM]
    summary = {
        "outputs": len(rows),
        "cas_tokens_total": sum(len(x["cas_tokens"]) for x in rows),
        "outputs_with_cas_tokens": sum(1 for x in rows if x["cas_tokens"]),
        "back_to_back_identical_outputs": sum(1 for x in rows if x["repeat_of_previous"]),
        "sentences_said_more_than_once": sum(1 for s, c in seen.items() if c > 1),
        "repeat_sentence_instances": sum(c - 1 for c in seen.values() if c > 1),
        "facts_preserved_pass": sum(1 for x in rows if x["facts_preserved"]),
        "facts_preserved_pass_on_34_with_old_form": sum(1 for x in with_form if x["facts_preserved"]),
        "facts_preserved_pass_if_40_digit_boilerplate_ignored": sum(
            1 for t, r, uh in zip(outputs, receipts, user_haves) if hv.facts_preserved(t.replace("40-digit", "digit"), r, user_have=uh)),
        "outcome_words_right": sum(1 for x in rows if x["outcome_words_right"]),
        "grade_mean": round(statistics.mean(x["grade"] for x in rows), 2),
        "grade_median": round(statistics.median(x["grade"] for x in rows), 2),
        "sentence_words_mean": round(statistics.mean(lens), 2),
        "sentence_words_variance": round(statistics.pvariance(lens), 2),
        "sentences_total": len(lens),
        "outputs_with_1_to_3_sentences": sum(1 for x in rows if 1 <= x["sentences"] <= 3),
    }
    return rows, summary


def main():
    with open(SITUATIONS_PATH, "rb") as f:
        raw = f.read()
    sit_sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    situations = data["situations"]
    assert len(situations) == 50
    adapter, cce = _old_adapter(), _cce_forms()
    receipts = [s["receipt"] for s in situations]

    old_out = [old_render(r, adapter, cce) for r in receipts]

    voice = hv.HELMVoice()
    new_out, new_trace, new_uh = [], [], []
    for s in situations:
        res = voice.render(s["receipt"], user_text=s.get("user_text"))
        new_out.append(res.text)
        new_trace.append(res.trace)
        r = s["receipt"]
        said = voice.state.user_said.get(hv._norm_name(r["limiting"])) if r.get("limiting") else None
        new_uh.append(said["words"] if said else None)

    old_rows, old_sum = measure(old_out, receipts, [None] * 50)
    new_rows, new_sum = measure(new_out, receipts, new_uh)
    for row, tr in zip(new_rows, new_trace):
        row["register"] = tr["register_used"]
        row["act"] = tr["act"]
        row["phrasing"] = tr["main"].get("kept") if tr["main"] else None
        row["fallback_fired"] = bool(tr["main"] and tr["main"].get("fallback_fired"))
        row["fallback_seed"] = tr["main"].get("fallback_seed") if tr["main"] else None
        row["first_seed"] = tr["main"].get("first_seed") if tr["main"] else None
        row["plain_used"] = tr["plain_used"]
        row["guard"] = tr["guard"]
        row["memory_flags"] = tr["memory_flags"]
    for row in old_rows:
        row["no_old_form"] = row["situation"] not in OLD_FORM

    new_sum["fallback_fired"] = sum(1 for r in new_rows if r["fallback_fired"])
    new_sum["plain_template_used"] = sum(1 for r in new_rows if r["plain_used"])
    new_sum["guard_pass"] = sum(1 for r in new_rows if r["guard"] == "PASS")
    new_sum["distinct_phrasings_used"] = len({r["phrasing"] for r in new_rows if r["phrasing"]})
    new_sum["registers_used"] = {k: sum(1 for r in new_rows if r["register"] == k) for k in hv.REGISTERS}
    new_sum["acts_used"] = {k: sum(1 for r in new_rows if r["act"] == k) for k in hv.ACTS}
    new_sum["user_words_quoted"] = sum(1 for r in new_rows if r["memory_flags"]["user_said"] and r["situation"] == "success")

    book = hv.load_phrasebook()
    with open(hv.PHRASEBOOK_PATH, "rb") as f:
        book_sha = hashlib.sha256(f.read()).hexdigest()
    out = {"schema": "helm.voice.fluency50.output/1", "situations_sha256": sit_sha, "phrasebook_sha256": book_sha,
           "phrasebook_phrasings": len(book["entries"]), "phrasebook_tails": len(book["tails"]),
           "summary": {"old": old_sum, "new": new_sum}, "old": old_rows, "new": new_rows}
    with open(os.path.join(OUT_DIR, "FLUENCY_50_OUTPUT.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")

    # ---- blind rating sheet for human judges (A/B order by a saved seed; key kept separately)
    rng = random.Random(20261018)
    key = {}
    lines = ["# HELM voice rating sheet (50 situations, blind A/B)", "",
             "For each situation you see what the user asked and two replies, A and B. Score EACH reply 1-5 on three",
             "questions. 1 = not at all, 3 = so-so, 5 = completely.", "",
             "- **Q1 Sounds like a person.** Would a friendly, sensible person say this?",
             "- **Q2 No jargon.** Could anyone follow it without special words or symbols?",
             "- **Q3 Says only what's true.** Compare with the 'Facts' line: does the reply say those facts, and nothing extra?",
             "", "Situations are one conversation, in order. Do not look at RATING_KEY.json until you are done.", "",
             "| | Q1 person | Q2 no jargon | Q3 only true |", "|---|---|---|---|",
             "| example | 4 | 5 | 5 |", ""]
    for s, o, n in zip(situations, old_out, new_out):
        r = s["receipt"]
        flip = rng.random() < 0.5
        a, b = (n, o) if flip else (o, n)
        key[s["n"]] = {"A": "new" if flip else "old", "B": "old" if flip else "new"}
        facts = {k: v for k, v in r.items() if k not in ("receipt_id", "telemetry", "kind", "situation")}
        lines += ["## %d. %s" % (s["n"], hv.situation_of(r).replace("_", " ")), "",
                  "User: %s" % (s.get("user_text") or "(no new words; same request again)"), "",
                  "Facts: `%s`" % json.dumps(facts, ensure_ascii=False), "",
                  "**A:** %s" % a.replace("\n", " / "), "", "**B:** %s" % b.replace("\n", " / "), "",
                  "| | Q1 person | Q2 no jargon | Q3 only true |", "|---|---|---|---|", "| A | | | |", "| B | | | |", ""]
    with open(os.path.join(OUT_DIR, "RATING_SHEET.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    with open(os.path.join(OUT_DIR, "RATING_KEY.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"seed": 20261018, "key": key}, f, indent=1)
        f.write("\n")

    print("situations sha256:", sit_sha)
    print("phrasebook:", len(book["entries"]), "phrasings,", len(book["tails"]), "tails, sha256", book_sha[:16])
    cols = ["cas_tokens_total", "outputs_with_cas_tokens", "back_to_back_identical_outputs",
            "sentences_said_more_than_once", "repeat_sentence_instances", "facts_preserved_pass",
            "facts_preserved_pass_on_34_with_old_form", "facts_preserved_pass_if_40_digit_boilerplate_ignored",
            "outcome_words_right", "grade_mean", "grade_median",
            "sentence_words_mean", "sentence_words_variance", "outputs_with_1_to_3_sentences"]
    print("%-44s %10s %10s" % ("check", "OLD", "NEW"))
    for c in cols:
        print("%-44s %10s %10s" % (c, old_sum[c], new_sum[c]))
    for c in ("fallback_fired", "plain_template_used", "guard_pass", "distinct_phrasings_used", "registers_used",
              "acts_used", "user_words_quoted"):
        print("new %-40s %s" % (c, new_sum[c]))
    return out


if __name__ == "__main__":
    main()
