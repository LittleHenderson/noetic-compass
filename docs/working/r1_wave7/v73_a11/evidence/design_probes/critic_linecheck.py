"""CRITIC: a line-level honesty check (proposed fix for A-R1W7-11 (d)) from fields a CHAT record already carries: the
question turn's loop sentence (`turns[-1].loop.loop_sentence`, HELM's say_wide G1 text) names every unlearned support
name; each must be the frozen-grammar head of a SECOND-amount tail of a tagged line, and that head must pass a frozen
deny list. Prototype on the critic probe's authored items (sentences copied from critic_probe output).
usage: python -X utf8 -B -I critic_linecheck.py <critic pkgs dir>"""
import os
import re
import sys

pk = sys.argv[1]
sys.path.insert(0, os.path.join(pk, "HELM_RBW1T_20261019"))
from rbw1t import common_rbw1t as RC  # noqa: E402
RC.vendor_path()
from xreal import grammar as G  # noqa: E402

SENT_RX = re.compile(r"^I can't say yet how much (?P<p>.+?) we can make\. I still need (?:one batch where (?P<one>.+?) "
                     r"ran out first while everything else was left over|one batch for each of (?P<many>.+?): a batch "
                     r"where that one ran out first while everything else was left over)\. I didn't guess\.$")
SEP_RX = re.compile(r",|;|&|\band\b|\bor\b|\bplus\b", re.IGNORECASE)      # = multi_qty_w7.SEP_RX
PAREN_RX = re.compile(r"\s*\([^()]*\)|\s*\[[^\]]*\]")                    # = multi_qty_w7.PAREN_RX
DENY = {"more", "less", "extra", "reserved", "divided", "separated", "beaten", "whites", "yolks", "them", "it", "each",
        "garnish", "serving", "dusting", "glazing", "brushing", "frying"}     # frozen; owner-reviewable
PARTICIPLE_RX = re.compile(r"^[a-z]+(?:ed|en)$")


def tail_heads(raw, i):
    s = PAREN_RX.sub("", raw[i])
    starts = list(G.qty_starts(s))
    lead = G.qty_at(s, starts[0])
    lead_end = lead["end"] if lead else starts[0]
    out = []
    for p in starts[1:]:
        if p >= lead_end and SEP_RX.search(s[lead_end:p]):
            t = G.parse_line(s[p:])
            if t and t["head"] and not PARTICIPLE_RX.match(t["head"]) and t["head"] not in DENY:
                out.append(RC.head_norm(t["head"]))
            lead_end = p
    return out


def honest(raw, tagged, key_heads, sentence):
    m = SENT_RX.match(sentence or "")
    if not m:
        return False, "sentence is not the unlearned-requirement ask"
    names = [m.group("one")] if m.group("one") else re.split(r",\s*and\s+|,\s*|\s+and\s+", m.group("many"))
    allowed = {h for i in tagged for h in tail_heads(raw, i)} - {RC.head_norm(h) for h in key_heads}
    got = [RC.head_norm(RC.last_word(n)) for n in names]
    return bool(names) and all(g in allowed for g in got), {"unlearned": names, "allowed_tail_heads": sorted(allowed)}


CASES = {
    "M1": (["2 cups barley", "5 cloves, 10 juniper berries", "1 cup broth"], [1], ["barley", "cloves", "broth"],
           "I can't say yet how much stew we can make. I still need one batch where juniper berry ran out first while "
           "everything else was left over. I didn't guess."),
    "C56-analogue": (["2 cups rice", "6 cloves and 12 peppercorns", "1 cup stock"], [1], ["rice", "cloves", "stock"],
                     "I can't say yet how much pilaf we can make. I still need one batch where peppercorn ran out first "
                     "while everything else was left over. I didn't guess."),
    "C1": (["3 eggs, 1 beaten", "2 cups flour", "1 cup milk"], [0], ["eggs", "flour", "milk"],
           "I can't say yet how much bread we can make. I still need one batch where beaten ran out first while "
           "everything else was left over. I didn't guess."),
    "C2": (["1 cup sugar, 2 tablespoons reserved", "2 cups flour", "1 cup milk"], [0], ["sugar", "flour", "milk"],
           "I can't say yet how much cake we can make. I still need one batch where reserved ran out first while "
           "everything else was left over. I didn't guess."),
    "C3": (["2 cups flour, plus 2 tablespoons", "1 pound beef, a lean cut", "1 cup broth"], [0], ["flour", "beef", "broth"],
           "I can't say yet how much pie we can make. I still need one batch where lean cut ran out first while "
           "everything else was left over. I didn't guess."),
    "ABSENT": (["2 cups barley", "5 cloves, 10 juniper berries", "1 cup broth"], [1], ["barley", "cloves", "broth"],
               "I can't say how much stew we can make yet, because I don't know how much broth we have. How much broth "
               "is there? I didn't guess."),
}
for tag, (raw, tagged, heads, sent) in CASES.items():
    print(tag, honest(raw, tagged, heads, sent))
