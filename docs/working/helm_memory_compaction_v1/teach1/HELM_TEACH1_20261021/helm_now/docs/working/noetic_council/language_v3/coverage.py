"""Coverage ledger for CCE v0.1 over (fundamental x Noetic x Domain x Register), read by the Lacunarity Machine.

TRANSLATOR_SPEC section 10. Universe: 130 (fundamental, Noetic) pairs x 4 Domains x 5 Register values = 2,600 cells.
Charge = a frozen CCE rule (CHARGES below) that claims the cell, written at t=0. Probe = one round trip of a content
built for the cell from its coordinates with fixed placeholder names, at t=1. Floor = 1 of 1.
Side universes (read on their own, never joined): U-TURN, U-DRIVE, U-RECIPE, U-CATEGORY.
"""
from fractions import Fraction

import cce
from lacunarity_machine.universe import Universe, Cell
from lacunarity_machine.ledger import Ledger
from lacunarity_machine.readers import deterministic_read

NOETIC_SELECTING = {"F1": [0], "F3": [1], "F4": [2, 3], "F5": [4], "F6": [8, 9], "F8": [6], "F9": [5], "F10": [7]}
CROSS_ALL = ["F2", "F11", "F12", "F14", "F15", "F16", "F19", "F20", "F21", "F22", "F23"]
CROSS_SOME = {"F7": [6, 9], "F17": [1, 2, 3, 4, 5, 7, 8, 9]}
REG_VALUES = ["T", "A", "f", "E", None]

# Frozen charge table: which CCE v0.1 rule claims which fundamental (all Noetics listed for it, all D, all R).
CHARGES = {
    "F1": "frame ^0 '<I> is an Idea' + tail", "F2": "the ten frames + tail", "F3": "frame ^1 (ACT verbs) + tail",
    "F4": "frames ^2 / ^3 + tail", "F5": "frame ^4 with DEGREE + tail", "F6": "frames ^8 / ^9 + tail",
    "F7": "sequence 'First <^6>; then <^9>' (Q1)", "F8": "frame ^6 + tail", "F9": "frame ^5 + tail",
    "F10": "frame ^7 with RATE, UNIT, PATTERN + tail", "F11": "tail: Domain word + Register word",
    "F12": "'I checked:' evidence wrapper", "F14": "polarity 'not' at the frame verb",
    "F15": "recipe term '<number> of <state>'", "F16": "sequence 'First ...; then ...'",
    "F17": "declared Mind name in the MIND slot", "F19": "recipe '; plus' (+) and '(... combined with ... into <named result>)' (x)",
    "F20": "nesting 'that [...]' in an Idea slot (depth <= 2)", "F21": "recipe Ω + Drive tail 'for <Drive>'",
    "F22": "'<Ω_b> needs <Ω_a> first.'", "F23": "'<Idea> is one of {...}.'",
}


# Frozen charge table for U-TURN: which CCE rule claims which turn type. Every one of the six now has a form.
# REFUSE and CLOSE were LACUNA in the base build; language_v3 adds a form for each (GRAMMAR_CCE_v0_1.md
# section 6, addendum section 11). The charge is written here because the grammar has the form, not instead
# of it: the probe below still has to round-trip through cce.round_trip for the cell to read COVERED.
TURN_CHARGES = {
    "ANSWER": "turn form in GRAMMAR section 6",
    "CLARIFY": "turn form in GRAMMAR section 6",
    "REFUSE": "turn form 'I will not do that: <reason words>.' (GRAMMAR section 11)",
    "REFUSE_CLAIM": "turn form in GRAMMAR section 6",
    "ACK": "turn form in GRAMMAR section 6",
    "CLOSE": "turn form 'That closes the turn.' / 'That closes <Omega>.' (GRAMMAR section 11)",
}


def pairs():
    out = [(f, n) for f, ns in NOETIC_SELECTING.items() for n in ns]
    out += [(f, n) for f in CROSS_ALL for n in range(10)]
    out += [(f, n) for f, ns in CROSS_SOME.items() for n in ns]
    return out


def cell_id(f, n, d, r):
    return "%s|^%d|%s|%s" % (f, n, d, r or "-")


def frame_term(n, d, r, mind="I", polarity="ASSERTED", drive=None):
    slots = {0: {"I": '"p"'}, 1: {"M": mind, "I": '"p"', "ACT": "intakes"}, 2: {"M": mind, "I": '"p"'},
             3: {"M": mind, "I": '"p"'}, 4: {"I": '"p"', "M": mind, "D": "3"}, 5: {"M": mind, "I": '"p"'},
             6: {"I": '"p"', "J": '"q"'}, 7: {"M": mind, "I": '"p"', "R": "1", "U": "day", "P": "daily"},
             8: {"I": '"p"', "J": '"q"', "M": mind}, 9: {"J": '"q"', "M": mind, "I": '"p"'}}[n]
    return {"noetic": n, "domain": d, "register": [r] if r else None, "drive": drive, "polarity": polarity,
            "slots": dict(slots)}


def state(n, d, r, drive=None):
    return {"noetic": n, "domain": d, "register": [r] if r else None, "drive": drive}


def probe_content(f, n, d, r):
    c = cce.empty_content()
    if f in ("F1", "F2", "F3", "F4", "F5", "F6", "F8", "F9", "F10", "F11"):
        c["terms"] = [frame_term(n, d, r)]
    elif f == "F12":
        c["evidence"] = "CHECKED"
        c["terms"] = [frame_term(n, d, r)]
    elif f == "F14":
        c["terms"] = [frame_term(n, d, r, polarity="DENIED")]
    elif f == "F15":
        st = state(n, d, r)
        st.update({"kind": "state", "coefficient": "2"})
        c["recipe"] = {"omega": "Ω_probe", "terms": [st], "leakage": [], "catalysts": [], "inhibitors": []}
    elif f == "F16":
        c["sequence"] = [frame_term(n, d, r), frame_term(0, "C", None)]
    elif f == "F17":
        c["relations"] = [["is_a", "Ana", "Mind"]]
        c["terms"] = [frame_term(n, d, r, mind="Ana")]
    elif f == "F19":
        c["recipe"] = {"omega": "Ω_probe", "terms": [
            {"coefficient": "1", "kind": "emergent", "components": [state(n, d, r), state((n + 1) % 10, d, None)],
             "result": "Ω_probe_whole"},
            {"coefficient": "1", "kind": "outcome", "name": "Ω_probe_base"}],
            "leakage": [], "catalysts": [], "inhibitors": []}
    elif f == "F20":
        inner = frame_term(n, d, r)
        c["terms"] = [{"noetic": 1, "domain": None, "register": None, "drive": None, "polarity": "ASSERTED",
                       "slots": {"M": "I", "I": {"that": inner}, "ACT": "intakes"}}]
    elif f == "F21":
        st = state(n, d, r, drive="F2")
        st.update({"kind": "state", "coefficient": "1"})
        c["recipe"] = {"omega": "Ω_probe", "terms": [st], "leakage": [], "catalysts": [], "inhibitors": []}
    elif f == "F22":
        st = state(n, d, r)
        st.update({"kind": "state", "coefficient": "1"})
        c["recipe"] = {"omega": "Ω_probe_b", "terms": [st], "leakage": [], "catalysts": [], "inhibitors": []}
        c["relations"] = [["needs_first", "Ω_probe_b", "Ω_probe_a"]]
    elif f == "F23":
        c["relations"] = [["one_of", '"p"', ['"p"', '"q"']]]
        c["terms"] = [frame_term(n, d, r)]
    elif f == "F7":
        six = {"noetic": 6, "domain": d if n == 6 else None, "register": ([r] if r else None) if n == 6 else None,
               "drive": None, "polarity": "ASSERTED", "slots": {"M": "I", "I": '"p"', "J": '"q"'}}
        nine = {"noetic": 9, "domain": d if n == 9 else None, "register": ([r] if r else None) if n == 9 else None,
                "drive": None, "polarity": "ASSERTED", "slots": {"J": '"r"', "M": "I", "I": '"p"'}}
        c["sequence"] = [six, nine]
    else:
        raise KeyError(f)
    return c


def run_main():
    cells = []
    for f, n in pairs():
        for d in cce.DOMAINS:
            for r in REG_VALUES:
                cells.append(Cell(cell_id(f, n, d, r), True, f))
    uni = Universe("U-MAIN (fundamental x Noetic x Domain x Register)", cells)
    led = Ledger(uni)
    for cell in cells:
        if cell.label in CHARGES:
            led.charge(cell.cell_id, 0, tag=CHARGES[cell.label])
    receipts = {}
    for f, n in pairs():
        for d in cce.DOMAINS:
            for r in REG_VALUES:
                cid = cell_id(f, n, d, r)
                rec = cce.round_trip(probe_content(f, n, d, r))
                receipts[cid] = rec
                led.probe(cid, 1, 1 if rec["ok"] else 0, 1, tag="roundtrip")
    read = deterministic_read(uni, led, Fraction(1), "roundtrip")
    for row in read["rows"]:
        row["receipt_id"] = receipts[row["cell"]]["receipt_id"] if row["state"] == "COVERED" else None
        row["rejection"] = receipts[row["cell"]]["rejection"]
    return read, receipts


def _side(name, entries):
    """entries: [(cell_id, charged_rule_or_None, content_or_None)]. None content = no probe (NO_EVIDENCE)."""
    uni = Universe(name, [Cell(cid, True, rule or "") for cid, rule, _ in entries])
    led = Ledger(uni)
    for cid, rule, _ in entries:
        if rule:
            led.charge(cid, 0, tag=rule)
    for cid, _, content in entries:
        if content is not None:
            led.probe(cid, 1, 1 if cce.round_trip(content)["ok"] else 0, 1, tag="roundtrip")
    return deterministic_read(uni, led, Fraction(1), "roundtrip")


def side_universes():
    base = frame_term(2, "P", None)
    turn = {}
    for t in ("ANSWER", "CLARIFY", "REFUSE", "REFUSE_CLAIM", "ACK", "CLOSE"):
        c = cce.empty_content()
        c["turn"] = t
        if t == "ANSWER":
            c["terms"] = [base]
        elif t == "CLARIFY":
            c.update({"topic": "Ω_probe", "lacunae": ["the stock of Ω_probe_a"]})
        elif t == "REFUSE_CLAIM":
            c["reason"] = "no evidence"
        elif t == "ACK":
            c["topic"] = "Ω_probe"
        elif t == "REFUSE":
            c["reason"] = "boundary violation"
        turn[t] = c
    u_turn = _side("U-TURN (6 eligible turn types in v0.1)", [(t, TURN_CHARGES[t], c) for t, c in turn.items()])
    drives = []
    for k in list(cce.DRIVES) + [None]:
        c = cce.empty_content()
        c["terms"] = [frame_term(2, "P", None, drive=k)]
        drives.append((k or "none", "tail 'for <Drive>'", c))
    u_drive = _side("U-DRIVE (7 Drives + none)", drives)

    def rec(terms, **kw):
        c = cce.empty_content()
        r = {"omega": "Ω_probe", "terms": terms, "leakage": [], "catalysts": [], "inhibitors": []}
        r.update(kw)
        c["recipe"] = r
        return c
    s1 = dict(state(9, "O", "A"), kind="state", coefficient="2")
    u_recipe = _side("U-RECIPE", [
        ("leakage", "'Side product: b of Ω'", rec([s1], leakage=[{"coefficient": "0.1", "side": "Ω_probe_side", "implicit": False}])),
        ("leakage_implicit", "'Side product: Ω'", rec([s1], leakage=[{"coefficient": "1", "side": "Ω_probe_side", "implicit": True}])),
        ("catalyst", "'Helped by Ω'", rec([s1], catalysts=["Ω_heat"])),
        ("inhibitor", "'Slowed by Ω'", rec([s1], inhibitors=["Ω_cold"])),
        ("emergent_x", "'(... combined with ... into <result>)'", rec([{"coefficient": "1", "kind": "emergent",
            "components": [state(3, "P", "A"), state(3, "P", "f")], "result": "^3^P|Ω_firm"}])),
        ("outcome_prerequisite", "'<n> of Ω'", rec([s1, {"coefficient": "1", "kind": "outcome", "name": "Ω_base"}])),
        ("register_set", "'in A and f registers' in a recipe term",
         rec([dict(state(3, "P", None), register=["A", "f"], kind="state", coefficient="1")])),
    ])

    def rel(r):
        c = cce.empty_content()
        c["relations"] = [r]
        return c
    seq = cce.empty_content()
    seq["sequence"] = [frame_term(6, "C", None), frame_term(9, "C", None)]
    frac = cce.empty_content()
    frac["fractal"] = [8, 9, 4]
    comp = cce.empty_content()
    comp["relations"] = [["compose", "Ω_a", "Ω_b"]]
    u_cat = _side("U-CATEGORY (TRANSLATOR_SPEC section 8)", [
        ("1_state_literals", "the ten frames + Domain tail", probe_content("F2", 4, "E", None)),
        ("2_drives", "tail 'for <Drive>'", drives[0][2]),
        ("3_registers_single", "'<reg> register'", probe_content("F11", 2, "C", "f")),
        ("3_registers_set", "'in ... and ... registers'", rec([dict(state(3, "P", None), register=["T", "A", "f"], kind="state", coefficient="1")])),
        ("4_op_plus", "'; plus'", rec([s1, dict(state(8, "O", None), kind="state", coefficient="1")])),
        ("4_op_times_named", "'combined with ... into'", rec([{"coefficient": "1", "kind": "emergent",
            "components": [state(2, "P", None), state(4, "E", None)], "result": "Ω_whole"}])),
        ("4_op_arrow_omega", "'To make Ω, use'", rec([s1])),
        ("4_op_general_compose", None, comp),
        ("5_recipes", "RECIPE form", rec([s1])),
        ("6_is_a", "'<Name> is a Mind.'", rel(["is_a", "Ana", "Mind"])),
        ("6_one_of", "'is one of {...}'", rel(["one_of", '"p"', ['"p"', '"q"']])),
        ("6_leads_to", "'Fact: ... leads to ...'", rel(["leads_to", '"p"', '"q"'])),
        ("6_needs_first", "'... needs ... first.'", rel(["needs_first", "Ω_b", "Ω_a"])),
        ("6_CoverOf", None, rel(["cover_of", "Ω_a", "Ω_b"])),
        ("6_PartitionOf", None, rel(["partition_of", "Ω_a", "Ω_b"])),
        ("6_union", None, rel(["union", "Ω_a", "Ω_b"])),
        ("6_intersection", None, rel(["intersection", "Ω_a", "Ω_b"])),
        ("6_difference", None, rel(["difference", "Ω_a", "Ω_b"])),
        ("6_let", None, rel(["let", "Ω_a", "Ω_b"])),
        ("7_fractal", "'The fractal sequence is ...'", frac),
        ("16_sequence", "'First ...; then ...'", seq),
    ])
    return {"U-TURN": u_turn, "U-DRIVE": u_drive, "U-RECIPE": u_recipe, "U-CATEGORY": u_cat}
