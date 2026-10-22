"""honest_ask_w7.py -- amendment A-R1W7-11. The owner's words (2026-10-21), byte-exact UTF-8 on the next line:
IF HELM ANSWERED HONESTLY AND CORRECTLY THEN YES  “Exempt from K4 only”; “merge 450”; “build v7.3” each tested through the real scoring program → a new sealed package → a fresh exam only on a line you type.
Design: docs/working/r1_wave7/v73_a11/DESIGN_V73_A11.md section 3
(sha256 57fcc5143d97431f4831b9c231d02c44efc88260da357febfc0b6add17be890a). A FRESH draw only; c51-c56 are not re-scored.

WHY (plain words). A book line can hold two amounts ("6 cloves and 12 peppercorns"). The frozen key reads it as ONE
ingredient (the first), so the lessons never teach the second; HELM reads two, is never taught the second, and asks. The
frozen strict K4 rule (rbw1t.keys_rbw1t.unexplained_ask: ANSWER key, every lesson LEARNED, stock STOCK_RECORDED, question
ASKS) counts that ask as unexplained. A-R1W7-7 tags such a key `line<i>:MULTI_QTY`, but the frozen scorer never reads that
tag for the question or for K4 (spec 7.119; the builder's error). This module leaves such an ask OUT of K4's strict count
only when a program can check, from what the host already records, five things, in this order (each runs only if the one
before held; a check not reached is None):
  (a) the key is ANSWER and carries a line<i>:MULTI_QTY tag;
  (b) the frozen rule counts the ask (score_w6.real_record_view -> keys_rbw1t.score_question / score_lessons ->
      unexplained_ask, the same calls in the same order as score_w6.score_real);
  (c) the scored turn's status is UNDETERMINED_CLARIFY, the log holds n_lessons + 2 entries and its last entry's path is
      "wide" (the brain's own gate asked, not a reader);
  (d) HELM's own question sentence is the frozen G1 "I still need ..." sentence; its names count exactly the untaught slots
      of the ONE wide recipe whose learned coefficients equal the key's line count; its dish is every lesson's dish;
  (e) each name's head word is the head of a second-amount tail written on a tagged line (raw lines from
      SAMPLE_REAL_X7.json, read with the frozen grammar), not a participle, a note word, a unit word or a key line's head.
These checks are necessary, not sufficient (named limits: DESIGN_V73_A11.md 3.2). The question score is untouched: a
tagged key still scores RIGHT, WRONG or ASKS, and WRONG still fails K3. The function never raises: an exception gives
exempt False and records the exception's type name.

CLAIM STATUS: an instrument amendment, ENGINEERED-NOT-VALIDATED; no HELM claim moves; the chat stays NOT LICENSED.
Standard library + the namespace's frozen modules (ns.rb.keys_rbw1t, ns.rb.common_rbw1t, ns.XG, ns.SC6) + multi_qty_w7's
PAREN_RX / SEP_RX.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from . import multi_qty_w7 as MQ

AMENDMENT = "A-R1W7-11"
#: the one exempt status (closed allow-list), only on path "wide" with the G1 untaught-requirement sentence
EXEMPT_STATUS = "UNDETERMINED_CLARIFY"
TAG_RX = re.compile(r"^line(\d+):MULTI_QTY$")
#: frozen, copied from helm_wide_turn.say_wide's G1 template (a test ties them to the package's helm_now)
G1_ONE_RX = re.compile(r"^I can't say yet how much (?P<p>.+?) we can make\. I still need one batch where (?P<one>.+) "
                       r"ran out first while everything else was left over\. I didn't guess\.$")
G1_MANY_RX = re.compile(r"^I can't say yet how much (?P<p>.+?) we can make\. I still need one batch for each of "
                        r"(?P<many>.+): a batch where that one ran out first while everything else was left over\. "
                        r"I didn't guess\.$")
NAME_SPLIT_RX = re.compile(r", and |, | and ")
PARTICIPLE_RX = re.compile(r"^[a-z]+(?:ed|en)$")
#: frozen deny list (owner-reviewable; DESIGN_V73_A11.md section 7 question 2)
DENY = ("more", "less", "extra", "reserved", "divided", "separated", "beaten", "whites", "yolks", "them", "it", "each",
        "garnish", "serving", "dusting", "glazing", "brushing", "frying")
CHECKS = ("a", "b", "c", "d", "e")


def _dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def tagged_lines(key: Any) -> List[int]:
    """The line indexes A-R1W7-7 tagged `line<i>:MULTI_QTY` in the key's representable.why_not (sorted, unique)."""
    why = _dict(_dict(key).get("representable")).get("why_not")
    if not isinstance(why, list):
        return []
    out = set()
    for w in why:
        m = TAG_RX.match(w) if isinstance(w, str) else None
        if m:
            out.add(int(m.group(1)))
    return sorted(out)


def question_sentence(rec: Any) -> Optional[str]:
    """HELM's own sentence for the question turn. CHAT record: the loop sentence (`loop.loop_sentence`) of the LAST turn
    whose kind is "turn" (noise turns are skipped). Wave-3-shaped record (no turn has a kind; LOOP_ON): the last turn's
    `reply_adapter`. Anything else: None."""
    turns = _dict(rec).get("turns")
    if not isinstance(turns, list) or not turns:
        return None
    chat = [t for t in turns if isinstance(t, dict) and t.get("kind") == "turn"]
    if chat:
        lv = chat[-1].get("loop")
        s = lv.get("loop_sentence") if isinstance(lv, dict) else None
        return s if isinstance(s, str) else None
    if all(isinstance(t, dict) and "kind" not in t for t in turns):
        s = turns[-1].get("reply_adapter")
        return s if isinstance(s, str) else None
    return None


def tail_heads(raw_line: Any, G: Any) -> List[str]:
    """Frozen-grammar heads (lower case) of every SECOND-amount tail of one raw line: parentheses removed with
    multi_qty_w7.PAREN_RX; the lead amount ends at qty_at(s, starts[0])['end']; every later quantity start p with
    p >= lead_end and multi_qty_w7.SEP_RX between them is a tail, whose head is xreal.grammar.parse_line(s[p:])['head'];
    lead_end then moves to the end of the amount at p."""
    s = MQ.PAREN_RX.sub("", str(raw_line))
    starts = list(G.qty_starts(s))
    if len(starts) < 2:
        return []
    lead = G.qty_at(s, starts[0])
    lead_end = lead["end"] if lead else starts[0]
    out: List[str] = []
    for p in starts[1:]:
        if p >= lead_end and MQ.SEP_RX.search(s[lead_end:p]):
            t = G.parse_line(s[p:].strip())
            if t and t.get("head"):
                out.append(str(t["head"]).lower())
            q = G.qty_at(s, p)
            lead_end = q["end"] if q else p
    return out


def allowed_heads(key: Any, raw: Any, G: Any, RC: Any) -> List[str]:
    """The head_norm of every tail head on a tagged line that survives the drop rules: dropped when the head matches
    PARTICIPLE_RX, when its head_norm is in the head_norm of DENY, when it or its head_norm is a unit word (the frozen
    grammar's UNITS keys, lower-cased, and their head_norm), or when its head_norm equals the head_norm of any key line's
    head. `RC` is RB-W1T's common module (the frozen head_norm). Sorted."""
    if not isinstance(raw, list):
        return []
    hn = RC.head_norm
    deny = {hn(w) for w in DENY}
    units = {str(u).lower() for u in G.UNITS}
    units |= {hn(u) for u in list(units)}
    key_heads = {hn(k.get("head")) for k in (_dict(key).get("lessons") or []) if isinstance(k, dict) and k.get("head")}
    out = set()
    for i in tagged_lines(key):
        if i >= len(raw) or not isinstance(raw[i], str):
            continue
        for h in tail_heads(raw[i], G):
            n = hn(h)
            if PARTICIPLE_RX.match(h) or n in deny or h in units or n in units or n in key_heads:
                continue
            out.add(n)
    return sorted(out)


def rule_b(ns: Any, key: Dict[str, Any], rec: Dict[str, Any], n_lessons: int) -> bool:
    """(b): the frozen strict rule, exactly as score_w6.score_real computes it."""
    K = ns.rb.keys_rbw1t
    v = ns.SC6.real_record_view(rec, n_lessons)
    q = v["question"]
    qs = K.score_question(key, q.get("status"), q.get("value"), q.get("limiting"), v["lessons"])
    ls = K.score_lessons(key, v["lessons"])
    return bool(K.unexplained_ask(key, ls, v["stock_status"], qs))


def honest_ask(ns: Any, key: Any, rec: Any, n_lessons: Any, raw_lines: Any) -> Dict[str, Any]:
    """The five checks of DESIGN_V73_A11.md 3.2, in order, short-circuiting; never raises."""
    out: Dict[str, Any] = {"id": _dict(key).get("id"), "tagged_lines": [], "a": None, "b": None, "c": None, "d": None,
                           "e": None, "exempt": False, "unlearned": None, "allowed_tail_heads": None,
                           "raw_lines_found": isinstance(raw_lines, list) and len(raw_lines) > 0
                           and all(isinstance(x, str) for x in raw_lines)}
    try:
        tags = tagged_lines(key)
        out["tagged_lines"] = tags
        # (a) a tagged answer key
        out["a"] = isinstance(key, dict) and _dict(key.get("answer")).get("key") == "ANSWER" and bool(tags)
        if not out["a"]:
            return out
        if not isinstance(rec, dict) or not _int(n_lessons) or n_lessons < 0:
            out["b"] = False
            return out
        # (b) the frozen rule counts the ask
        out["b"] = rule_b(ns, key, rec, n_lessons)
        if not out["b"]:
            return out
        # (c) the brain's gate asked on the wide path
        st = rec.get("scored_turn")
        log = rec.get("log")
        out["c"] = (isinstance(st, dict) and st.get("status") == EXEMPT_STATUS and isinstance(log, list)
                    and len(log) == n_lessons + 2 and isinstance(log[-1], dict) and log[-1].get("path") == "wide")
        if not out["c"]:
            return out
        # (d) HELM's own sentence names exactly its untaught ingredients
        sent = question_sentence(rec)
        m1 = G1_ONE_RX.match(sent) if isinstance(sent, str) else None
        m2 = None if (m1 or not isinstance(sent, str)) else G1_MANY_RX.match(sent)
        if m1:
            names, dish = [m1.group("one")], m1.group("p")
        elif m2:
            names, dish = NAME_SPLIT_RX.split(m2.group("many")), m2.group("p")
        else:
            names, dish = [], None
        out["unlearned"] = names
        wa = rec.get("wide_audit")
        a0 = wa[0] if isinstance(wa, list) and len(wa) == 1 and isinstance(wa[0], dict) else None
        lessons = ns.SC6.real_record_view(rec, n_lessons)["lessons"]
        coef = a0.get("coefficients") if a0 else None
        slots = a0.get("support_slots") if a0 else None
        key_lines = key.get("lessons") if isinstance(key.get("lessons"), list) else None
        out["d"] = bool(
            dish is not None and names and all(isinstance(n, str) and n.strip() for n in names)
            and a0 is not None and a0.get("ok") is True and _int(coef) and _int(slots) and key_lines is not None
            and coef == len(key_lines) and slots - coef == len(names)
            and isinstance(lessons, list) and lessons and all(isinstance(x, dict) for x in lessons)
            and all(x.get("product") == dish for x in lessons))
        if not out["d"]:
            return out
        # (e) each name is the second ingredient written on a tagged line
        if not out["raw_lines_found"]:
            out["e"] = False
            return out
        allowed = allowed_heads(key, raw_lines, ns.XG, ns.rb.common_rbw1t)
        out["allowed_tail_heads"] = allowed
        RC = ns.rb.common_rbw1t
        out["e"] = bool(allowed) and all(RC.head_norm(RC.last_word(n)) in allowed for n in names)
        out["exempt"] = out["a"] is True and out["b"] is True and out["c"] is True and out["d"] is True and out["e"] is True
        return out
    except Exception as exc:                          # never raises: an error is "not exempt", recorded by type name
        out["exempt"] = False
        out["error"] = type(exc).__name__
        return out


def apply(ns: Any, out: Dict[str, Any], keys: Sequence[Dict[str, Any]], inputs: Sequence[Dict[str, Any]],
          doc: Optional[Dict[str, Any]], raw_by_id: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The K4 recount on top of the frozen wave-6 score_real output `out` (edited in place and returned). For EVERY key
    with a record, (b) is computed on its own (`a11_strict_recount`); for every key with (a) True the chain runs and
    gives one `a11_checks` row. `unexplained_asks_strict` is left exactly as the frozen code computed it."""
    by_id = {r.get("id"): r for r in ((doc or {}).get("records") or []) if isinstance(r, dict)}
    n_by_id = {it.get("id"): it.get("n_lessons") for it in inputs if isinstance(it, dict)}
    raw_map = raw_by_id if isinstance(raw_by_id, dict) else {}
    counted, rows = [], []
    for key in keys:
        kid = _dict(key).get("id")
        rec = by_id.get(kid)
        if rec is None:
            continue                                   # the frozen code counts it as missing
        n = n_by_id.get(kid)
        try:
            if _int(n) and rule_b(ns, key, rec, n):
                counted.append(kid)
        except Exception:                              # recount stays short: a11_consistent reads False, K4 stays false
            pass
        if not tagged_lines(key) or _dict(_dict(key).get("answer")).get("key") != "ANSWER":
            continue
        rows.append(honest_ask(ns, key, rec, n, raw_map.get(kid)))
    exempted = sorted(r["id"] for r in rows if r.get("exempt") is True)
    t = out.setdefault("totals", {})
    strict = t.get("unexplained_asks_strict")
    t["a11_strict_recount"] = len(counted)
    t["unexplained_asks_strict_after_a11"] = (strict - len(exempted)) if _int(strict) else None
    t["a11_consistent"] = _int(strict) and len(counted) == strict and set(exempted) <= set(counted)
    out["a11_exempted_ids"] = exempted
    out["a11_checks"] = rows
    ex = set(exempted)
    for p in out.get("per_item") or []:
        if isinstance(p, dict):
            p["a11_exempt"] = p.get("id") in ex
    return out
