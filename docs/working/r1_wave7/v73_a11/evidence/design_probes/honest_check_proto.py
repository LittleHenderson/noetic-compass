"""PROTOTYPE ONLY of the FINAL A-R1W7-11 honesty test (DESIGN_V73_A11.md section 3.2), for the finalize probe. Pure:
reads a key, a host record and n_lessons; never raises; every check short-circuits in order a -> b -> c -> d -> e."""
import re

TAG_RX = re.compile(r"^line(\d+):MULTI_QTY$")
EXEMPT_STATUS = "UNDETERMINED_CLARIFY"
G1_ONE_RX = re.compile(r"^I can't say yet how much (?P<p>.+?) we can make\. I still need one batch where (?P<one>.+) "
                       r"ran out first while everything else was left over\. I didn't guess\.$")
G1_MANY_RX = re.compile(r"^I can't say yet how much (?P<p>.+?) we can make\. I still need one batch for each of "
                        r"(?P<many>.+): a batch where that one ran out first while everything else was left over\. "
                        r"I didn't guess\.$")
NAME_SPLIT_RX = re.compile(r", and |, | and ")
PARTICIPLE_RX = re.compile(r"^[a-z]+(?:ed|en)$")
DENY = ("more", "less", "extra", "reserved", "divided", "separated", "beaten", "whites", "yolks", "them", "it",
        "each", "garnish", "serving", "dusting", "glazing", "brushing", "frying")


def tagged_lines(key):
    why = ((key.get("representable") or {}).get("why_not") or [])
    return sorted({int(m.group(1)) for m in (TAG_RX.match(str(w)) for w in why) if m})


def tail_heads(raw_line, G, MQ, RC):
    """Frozen-grammar heads of every SECOND-amount tail of one raw line (multi_qty_w7's separator rule)."""
    s = MQ.PAREN_RX.sub("", str(raw_line))
    starts = list(G.qty_starts(s))
    if len(starts) < 2:
        return []
    lead = G.qty_at(s, starts[0])
    lead_end = lead["end"] if lead else starts[0]
    out = []
    for p in starts[1:]:
        if p >= lead_end and MQ.SEP_RX.search(s[lead_end:p]):
            t = G.parse_line(s[p:].strip())
            if t and t.get("head"):
                out.append(str(t["head"]).lower())
            q = G.qty_at(s, p)
            lead_end = q["end"] if q else p
    return out


def allowed_heads(key, raw_lines, G, MQ, RC):
    deny = {RC.head_norm(w) for w in DENY}
    units = {RC.head_norm(u) for u in G.UNITS} | {str(u).lower() for u in G.UNITS}
    key_heads = {RC.head_norm(k.get("head")) for k in key.get("lessons") or [] if k.get("head")}
    out = set()
    for i in tagged_lines(key):
        if i >= len(raw_lines):
            continue
        for h in tail_heads(raw_lines[i], G, MQ, RC):
            hn = RC.head_norm(h)
            if PARTICIPLE_RX.match(h) or hn in deny or h in units or hn in units or hn in key_heads:
                continue
            out.add(hn)
    return out


def question_sentence(rec):
    turns = rec.get("turns") if isinstance(rec.get("turns"), list) else []
    chat = [t for t in turns if isinstance(t, dict) and t.get("kind") == "turn"]
    if chat:
        lv = chat[-1].get("loop")
        return lv.get("loop_sentence") if isinstance(lv, dict) else None
    if turns and isinstance(turns[-1], dict) and "kind" not in turns[-1]:
        return turns[-1].get("reply_adapter")
    return None


def honest_ask(K, real_record_view, G, MQ, RC, key, rec, n_lessons, raw_lines):
    out = {"a": None, "b": None, "c": None, "d": None, "e": None, "exempt": False, "unlearned": None,
           "allowed_tail_heads": None}
    try:
        ans = (key.get("answer") or {}).get("key")
        out["a"] = ans == "ANSWER" and bool(tagged_lines(key))
        if not out["a"]:
            return out
        v = real_record_view(rec, n_lessons)
        q = v["question"] if isinstance(v.get("question"), dict) else {}
        qs = K.score_question(key, q.get("status"), q.get("value"), q.get("limiting"), v["lessons"])
        ls = K.score_lessons(key, v["lessons"])
        out["b"] = bool(K.unexplained_ask(key, ls, v["stock_status"], qs))
        if not out["b"]:
            return out
        log = rec.get("log") if isinstance(rec.get("log"), list) else []
        st = rec.get("scored_turn") if isinstance(rec.get("scored_turn"), dict) else {}
        out["c"] = (st.get("status") == EXEMPT_STATUS and len(log) == n_lessons + 2
                    and isinstance(log[-1], dict) and log[-1].get("path") == "wide")
        if not out["c"]:
            return out
        sent = question_sentence(rec)
        m1 = G1_ONE_RX.match(sent) if isinstance(sent, str) else None
        m2 = None if m1 else (G1_MANY_RX.match(sent) if isinstance(sent, str) else None)
        names = [m1.group("one")] if m1 else (NAME_SPLIT_RX.split(m2.group("many")) if m2 else [])
        product = (m1 or m2).group("p") if (m1 or m2) else None
        out["unlearned"] = names
        wa = rec.get("wide_audit") if isinstance(rec.get("wide_audit"), list) else []
        lessons = v["lessons"]
        prods = {x.get("product") for x in lessons if isinstance(x, dict)}
        a0 = wa[0] if len(wa) == 1 and isinstance(wa[0], dict) else {}
        coef, slots = a0.get("coefficients"), a0.get("support_slots")
        out["d"] = (bool(names) and all(n.strip() for n in names) and a0.get("ok") is True
                    and isinstance(coef, int) and isinstance(slots, int)
                    and coef == len(key.get("lessons") or []) and slots - coef == len(names)
                    and len(prods) == 1 and product is not None and prods == {product})
        if not out["d"]:
            return out
        allowed = allowed_heads(key, raw_lines, G, MQ, RC)
        out["allowed_tail_heads"] = sorted(allowed)
        out["e"] = all(RC.head_norm(RC.last_word(n)) in allowed for n in names)
        out["exempt"] = bool(out["e"])
        return out
    except Exception as exc:                          # never raises: an error is "not exempt", recorded
        out["error"] = type(exc).__name__
        out["exempt"] = False
        return out
