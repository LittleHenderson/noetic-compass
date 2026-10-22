"""FEASIBILITY PROBE ONLY (finalize step of DESIGN_V73_A11.md; not the build). In-process replacements, on a scratch
copy of the v9 helm_now, for the FINAL v7.3 rules: R1 (a dangling "or" is never part of a name), R1a (a batch or stock
holding a dangling-"or" line asks which one: CLARIFY_WIDE_ALTERNATIVE_WHICH_ONE, nothing saved), R2 (ambiguity before
any one-candidate guess that is not exact), R2g (an exact hit is not taken when another batch line's name is the same
phrase followed by a frozen STOP word). install(WT) patches the given module object and returns nothing."""
import re

DANGLING_OR_RX = re.compile(r"(?:^|[\s,;]+)or[\s,;]*$", re.IGNORECASE)
ALTERNATIVE_CODE = "ALTERNATIVE_WHICH_ONE"
RAN_OUT_CODE = "RAN_OUT_WHICH_LINE"
WHICH_ONE_CODES = (ALTERNATIVE_CODE, RAN_OUT_CODE)
#: the frozen xreal.grammar.STOP_WORDS, copied (a frozen neighbour is never imported by HELM)
STOP_WORDS = frozenset(("and", "or", "but", "for", "in", "on", "at", "to", "with", "from", "into", "the", "a", "an",
                        "left", "that", "which", "if", "as", "per", "each"))


def install(WT):
    orig_parse_line = WT.parse_line
    orig_say_reader_question = WT.say_reader_question
    orig_take_over = WT.take_over
    orig_wide_turn = WT.wide_turn

    def parse_line_v73(line, notes=""):
        s = line.strip().strip(".").strip()
        dangling = False
        m = DANGLING_OR_RX.search(s)
        if m and s[:m.start()].strip():
            s_own, dangling = s[:m.start()].rstrip(" ,;"), True
        else:
            s_own = s
        n_own = notes
        mn = DANGLING_OR_RX.search(notes or "")
        if mn is not None:
            n_own, dangling = notes[:mn.start()].rstrip(" ,;"), True
        rec = orig_parse_line(s_own, n_own)
        if dangling and "clarify" not in rec:
            rec = dict(rec)
            rec["said"] = s + (", " + notes.strip().strip(".").strip() if notes and notes.strip() else "")
            rec["dangling_or"] = True
        return rec

    def parse_lines_v73(text):
        # a copy of v7.2 parse_lines with ONE added step (R1a) before the SAME_INGREDIENT_TWICE check
        lines = []
        for m in WT.SEP_RX.finditer(text):
            piece = text[m.end():].strip()
            if WT.CLAUSE_RX.match(piece):
                return [], WT._ask("UNREAD_CLAUSE", words=piece.split(",")[0].strip().rstrip("."))
        stage_1c = WT.W.units_note_on()
        for seg, notes in WT.split_lines(text):
            rec = WT.parse_line(seg, notes)
            if "clarify" in rec:
                return [], rec["clarify"]
            lines.append(rec)
            if stage_1c and rec.get("note") and rec.get("note_why") == "NO_AMOUNT" and notes:
                for piece in WT.SEP_RX.split(notes):
                    nm = WT.note_name(piece)
                    if nm:
                        lines.append(WT._note_line(nm, piece.strip().strip(".").strip(), "NO_AMOUNT"))
        for i, x in enumerate(lines):                                   # R1a
            if x.get("dangling_or"):
                second = lines[i + 1]["name"] if i + 1 < len(lines) else None
                return [], WT._ask(ALTERNATIVE_CODE, first=x["name"], second=second, words=x["said"])
        names = [x["name"] for x in lines]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            return [], WT._ask("SAME_INGREDIENT_TWICE", item=dup[0])
        if not lines:
            return [], WT._ask("NO_AMOUNT")
        return lines, None

    def say_reader_question_v73(c):
        if c.get("code") == ALTERNATIVE_CODE:
            s = c.get("slots") or {}
            if s.get("second"):
                return (f"You wrote \"{s.get('words', '')}\" and then {s['second']}, so it reads as one or the other. "
                        f"Which one did you use? Tell me the batch again with just that one. Nothing was saved.")
            return (f"You wrote \"{s.get('words', '')}\" with nothing after the \"or\". Which one did you use? Tell me "
                    f"the batch again with just that one. Nothing was saved.")
        if c.get("code") == RAN_OUT_CODE:
            s = c.get("slots") or {}
            return (f"You said {s.get('item', 'it')} ran out, but that could be {WT.say_and(s.get('lines') or [])}. "
                    f"Which one ran out first? Tell me the batch again. Nothing was saved.")
        return orig_say_reader_question(c)

    def take_over_v73(loop, licensed, reading):
        if (reading.get("status") == "CLARIFY" and (reading.get("clarify") or {}).get("code") in WHICH_ONE_CODES
                and not licensed.get("cubes_written")):
            return licensed.get("loop_status") in WT.WIDE_MAY_TAKE
        return orig_take_over(loop, licensed, reading)

    def wide_turn_v73(loop, user_english, tick):
        r = WT.read_wide(user_english.strip(), last_topic=loop.last_topic)
        if r.get("status") == "CLARIFY" and (r.get("clarify") or {}).get("code") in WHICH_ONE_CODES:
            WT._withdraw_mentioned_stock(loop, user_english, tick)    # never answer from stock just restated
        return orig_wide_turn(loop, user_english, tick)

    def _rival(hit, batch):
        ph = WT._words(hit)
        return any(b != hit and len(WT._words(b)) > len(ph) and WT._words(b)[:len(ph)] == ph
                   and WT._words(b)[len(ph)] in STOP_WORDS for b in batch)

    def resolve_ran_out_v73(name, batch, said=None):
        if name in batch:
            return name
        words = name.split()
        while words:
            if len(words) > 1 and WT.W.unit_of(words[0] + words[1]) is not None:
                words = words[2:]
            elif (WT.W.unit_of(words[0]) is not None or words[0] in WT.W.OTHER_UNIT_WORDS
                  or words[0] in WT.LEADING_DROPPED
                  or words[0] in ("level", "heaping", "heaped", "rounded", "good", "scant", "generous")):
                words = words[1:]
            else:
                break
        stripped = WT.bind_name(" ".join(words)) if words else None
        if stripped and stripped in batch:
            return stripped
        name2 = stripped or name
        hits = {b for b in batch if b.startswith(name2 + " ") or b.endswith(" " + name2)}
        if said:
            needle = WT._words(name2)
            hits |= {b for b in batch if WT._contains(WT._words(said.get(b, b)), needle)}
        return next(iter(hits)) if len(hits) == 1 else name

    orig_read_wide = WT.read_wide

    def read_wide_v73(text, last_topic=None):
        out = orig_read_wide(text, last_topic)
        batch = out.get("witness") or out.get("pending")
        if batch:
            names = list(batch["stock"])
            for n in batch["ran_out"]:
                if n in batch["stock"] and _rival(n, names):
                    rivals = [b for b in names if _rival(n, [b])]
                    out.pop("pending", None)
                    out.update(status="CLARIFY", witness=None,
                               clarify=WT._ask(RAN_OUT_CODE, item=n, lines=[n] + rivals))
                    return out
        return out

    WT.read_wide = read_wide_v73
    WT.parse_line = parse_line_v73
    WT.parse_lines = parse_lines_v73
    WT.say_reader_question = say_reader_question_v73
    WT.take_over = take_over_v73
    WT.wide_turn = wide_turn_v73
    WT.resolve_ran_out = resolve_ran_out_v73
