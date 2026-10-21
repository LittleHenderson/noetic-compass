"""multi_qty_w7.py -- amendment A-R1W7-7 (owner's word, typed 2026-10-21: "Yes to D6, the custodian MULTI_QTY rule, as
amendment A-R1W7-7"). SPEC 7.109 design packet, D6.

WHY (plain words). On job c54 (SPEC 7.108) the chat missed the K4 mark by two asks. The per-item diagnosis
(K4_ITEM_DIAGNOSIS_C54.md) found one BOOK LINE holding TWO amounts in each item ("6 cloves, 12 peppercorns"-shaped,
author's example): the frozen key (xreal.keys.key_r, RB-W1T) keeps such a line as ONE lesson named by its first head and
ignores the tail, so the exam's lessons never make the second ingredient run out and its amount is never doubled; the
wide reader reads TWO ingredients, is never taught the second one's requirement, and asks -- honestly. No general reader
rule can answer it. The general rule is on the instrument side: such a recipe is NOT REPRESENTABLE under the recipe-shape
survey's rule, as a range or an odd unit already is, and scores NOT_SCORED (an undetermined key), never ANSWER.

WHAT THIS DOES. After the frozen key is computed, every raw line that carries a SECOND amount after a separator (a quantity start of the frozen
grammar, xreal.grammar.qty_starts, after the leading amount, with ", " / "and" / "or" between; parentheses removed
first; one amount such as "1-1/2" or "one and a half" is never two) adds "line<i>:MULTI_QTY" to the key's representable.why_not, and
representable.representable becomes False. Nothing else in the key changes (answer, lessons, heads are untouched); the
frozen key package is not edited (this sits in the wave-7 package, r1w7/, and is applied by custody_w7.make_all).

CLAIM STATUS: an instrument rule; no HELM claim moves. Applies to a FRESH draw only (sealed data is never re-read).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

AMENDMENT = "A-R1W7-7"
WHY_NOT_CODE = "MULTI_QTY"
#: the survey's exact forms (mirrors rbw1t.common_rbw1t.SURVEY_EXACT_FORMS); a line already refused for its form keeps
#: its own reason and is not re-tagged here
EXACT_FORMS = ("integer", "decimal", "simple_fraction", "mixed")
#: a second amount counts only after a separator: ", 12 peppercorns", "and 1/2 cup water", "or 2 ..."; never inside one
#: amount ("1-1/2", "2 1/2", "one and a half") and never inside parentheses ("(about 240 ml)", which every reader drops)
SEP_RX = re.compile(r",|;|&|\band\b|\bor\b|\bplus\b", re.IGNORECASE)
PAREN_RX = re.compile(r"\s*\([^()]*\)|\s*\[[^\]]*\]")


def multi_qty_lines(raw_lines: Sequence[str], G: Any, forms: Optional[Sequence[str]] = None) -> List[int]:
    """Indexes of the raw lines that carry a SECOND amount: a quantity start (frozen grammar, xreal.grammar.qty_starts)
    after the leading amount's end with a separator between them, parentheses removed first. Lines whose survey form
    is not exact (`forms`, from the frozen key's representable record) are left to their own reason."""
    out = []
    for i, line in enumerate(raw_lines):
        if forms is not None and i < len(forms) and forms[i] not in EXACT_FORMS:
            continue
        s = PAREN_RX.sub("", str(line))
        try:
            starts = list(G.qty_starts(s))
            if len(starts) < 2:
                continue
            lead = G.qty_at(s, starts[0])
            lead_end = lead["end"] if lead else starts[0]
        except Exception:                                   # the grammar never raises on a string; belt and braces
            continue
        for p in starts[1:]:
            if p >= lead_end and SEP_RX.search(s[lead_end:p]):
                out.append(i)
                break
    return out


def apply(key: Dict[str, Any], raw_lines: Sequence[str], G: Any) -> Dict[str, Any]:
    """The frozen key plus A-R1W7-7: representable.why_not gains 'line<i>:MULTI_QTY' per two-amount line; the flag
    follows why_not. Idempotent. Returns the same dict (edited in place) for the custodian's list comprehension."""
    rep = key.setdefault("representable", {"representable": True, "why_not": [], "units": [], "forms": []})
    why = list(rep.get("why_not") or [])
    for i in multi_qty_lines(raw_lines, G, rep.get("forms")):
        tag = f"line{i}:{WHY_NOT_CODE}"
        if tag not in why:
            why.append(tag)
    rep["why_not"] = why
    rep["representable"] = not why
    rep["amendment"] = AMENDMENT
    return key
