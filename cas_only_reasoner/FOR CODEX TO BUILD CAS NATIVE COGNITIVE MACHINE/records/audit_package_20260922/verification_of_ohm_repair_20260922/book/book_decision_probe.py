"""Read-only probe for three PCBA-book owner-decision issues.

Reads book text ONLY through `git show <commit>:<path>` (no checkout, no write
to the repo).  Standard library only.  Writes one JSON file beside itself.
"""
import hashlib
import itertools
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

REPO = ("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/"
        "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm3-lab")
COMMIT = "65ad3008"
BOOK = "book/CAS_PCBA_Engineer/"
OUT = Path(__file__).with_name("book_decision_probe.json")


def git_show(commit, path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{commit}:{path}"],
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git show failed {commit}:{path}: {r.stderr!r}")
    return r.stdout.decode("utf-8")


_cache = {}


def line(fname, n, commit=COMMIT):
    key = (commit, fname)
    if key not in _cache:
        _cache[key] = git_show(commit, BOOK + fname).split("\n")
    text = _cache[key][n - 1]
    return {"file": fname, "line": n, "commit": commit, "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


# ---------------------------------------------------------------- Issue 1
ISSUE1_CONDITIONAL = [("Appendix_B_Component_Datasheets.md", 59),
                      ("Appendix_B_Component_Datasheets.md", 79)]
ISSUE1_AUTOMATIC = [
    ("Appendix_A_Notation_Quick_Reference.md", 40),
    ("Appendix_A_Notation_Quick_Reference.md", 121),
    ("Appendix_C_CCDL_Language_Reference.md", 549),
    ("Appendix_C_CCDL_Language_Reference.md", 765),
    ("Appendix_C_CCDL_Language_Reference.md", 1041),
    ("Appendix_D_CCB_Reference_Designs.md", 545),
    ("Appendix_D_CCB_Reference_Designs.md", 764),
    ("Appendix_E_Exercise_Answers.md", 74),
    ("Appendix_F_Lab_Setup_Guide.md", 172),
    ("Appendix_G_Glossary.md", 47), ("Appendix_G_Glossary.md", 48),
    ("Appendix_G_Glossary.md", 49), ("Appendix_G_Glossary.md", 50),
    ("Appendix_G_Glossary.md", 238), ("Appendix_G_Glossary.md", 324),
    ("Appendix_G_Glossary.md", 325), ("Appendix_G_Glossary.md", 397),
    ("Appendix_G_Glossary.md", 398),
    ("Chapter_02_CAS_Notation_in_One_Chapter.md", 56),
    ("Chapter_02_CAS_Notation_in_One_Chapter.md", 220),
    ("Chapter_03_The_Transistor_That_Changed_Everything.md", 101),
    ("Chapter_03_The_Transistor_That_Changed_Everything.md", 103),
    ("Chapter_03_The_Transistor_That_Changed_Everything.md", 188),
    ("Chapter_03_The_Transistor_That_Changed_Everything.md", 199),
    ("Chapter_04_Your_First_Cognitive_Circuit.md", 161),
    ("Chapter_04_Your_First_Cognitive_Circuit.md", 176),
    ("Chapter_05_Resistors.md", 171),
    ("Chapter_05_Resistors.md", 177),
    ("Chapter_06_Capacitors.md", 195),
    ("Chapter_09_CJT_Deep_Dive.md", 5),
    ("Chapter_09_CJT_Deep_Dive.md", 203),
    ("Chapter_09_CJT_Deep_Dive.md", 215),
    ("Chapter_11_Amplifiers.md", 21),
    ("Chapter_14_Power_Management.md", 216),
    ("Chapter_14_Power_Management.md", 285),
    ("Chapter_21_CMB_Cognitive_Memory_Board.md", 296),
    ("Chapter_22_CPMB_Power_Management_Board.md", 19),
    ("Chapter_22_CPMB_Power_Management_Board.md", 361),
    ("STYLE_GUIDE.md", 125), ("STYLE_GUIDE.md", 126),
]
ISSUE1_ADJACENT = [  # configuration-driven involution, not breakdown
    ("Chapter_09_CJT_Deep_Dive.md", 157),
    ("Chapter_09_CJT_Deep_Dive.md", 178),
    ("Appendix_E_Exercise_Answers.md", 279),
    ("Chapter_10_Special_Purpose_Components.md", 46),
    ("Appendix_B_Component_Datasheets.md", 307),
]
ISSUE1_SYNTAX = [("Appendix_C_CCDL_Language_Reference.md", 185),
                 ("Appendix_C_CCDL_Language_Reference.md", 531)]

INVOLUTION = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}
SELF_DUAL = {0, 1, 4, 7}


def breakdown_output(noetic, explicit_rule_declared, reading):
    """Output Noetic of a CJT effect in the breakdown region.

    reading 'AUTOMATIC'  = Appendix A:40/121, C:549, Ch3:101, Glossary:47-49 ...
    reading 'CONDITIONAL' = Appendix B:59 (flip only when rule declared).
    Returns (noetic_out, note).
    """
    if noetic in SELF_DUAL:
        return noetic, "self-dual: nowhere to flip"
    if reading == "AUTOMATIC":
        return INVOLUTION[noetic], "flipped to involution pair"
    if explicit_rule_declared:
        return INVOLUTION[noetic], "declared rule licenses the flip"
    return noetic, ("no flip; 'engineered failure behavior' otherwise "
                    "unspecified by Appendix B:59")


def issue1_matrix():
    rows = []
    for n in range(10):
        for rule in (False, True):
            a = breakdown_output(n, rule, "AUTOMATIC")
            c = breakdown_output(n, rule, "CONDITIONAL")
            rows.append({"effect_noetic": f"^{n}", "explicit_rule": rule,
                         "automatic_out": f"^{a[0]}",
                         "conditional_out": f"^{c[0]}",
                         "differ": a[0] != c[0]})
    return rows


# ---------------------------------------------------------------- Issue 2
ISSUE2 = [
    ("Appendix_C_CCDL_Language_Reference.md", 379),
    ("Appendix_C_CCDL_Language_Reference.md", 444),
    ("Appendix_C_CCDL_Language_Reference.md", 447),
    ("Appendix_C_CCDL_Language_Reference.md", 452),
    ("Appendix_C_CCDL_Language_Reference.md", 453),
    ("Appendix_C_CCDL_Language_Reference.md", 890),
    ("Chapter_10_Special_Purpose_Components.md", 87),
    ("Chapter_10_Special_Purpose_Components.md", 96),
    ("Chapter_10_Special_Purpose_Components.md", 97),
    ("Chapter_10_Special_Purpose_Components.md", 99),
    ("Chapter_10_Special_Purpose_Components.md", 115),
    ("Chapter_10_Special_Purpose_Components.md", 116),
    ("Chapter_10_Special_Purpose_Components.md", 118),
    ("Chapter_10_Special_Purpose_Components.md", 324),
    ("Chapter_10_Special_Purpose_Components.md", 356),
    ("Appendix_B_Component_Datasheets.md", 367),
    ("Appendix_B_Component_Datasheets.md", 389),
    ("Appendix_B_Component_Datasheets.md", 390),
    ("Appendix_B_Component_Datasheets.md", 392),
    ("Appendix_B_Component_Datasheets.md", 401),
    ("Appendix_A_Notation_Quick_Reference.md", 137),
    ("Appendix_E_Exercise_Answers.md", 337),
    ("STYLE_GUIDE.md", 145),
]

XOR_READINGS = {
    "odd_parity": lambda b: sum(b) % 2 == 1,
    "exactly_one": lambda b: sum(b) == 1,
    "not_all_equal ('inputs differ', Ch10:96, AppE:337)":
        lambda b: len(set(b)) > 1,
}
XNOR_READINGS = {
    "even_parity (NOT odd_parity)": lambda b: sum(b) % 2 == 0,
    "NOT exactly_one": lambda b: sum(b) != 1,
    "all_equal ('inputs agree', AppB:390, AppC:447, Ch10:97/116)":
        lambda b: len(set(b)) == 1,
}


def table(n):
    rows = []
    for bits in itertools.product((0, 1), repeat=n):
        r = {"inputs": "".join(map(str, bits)), "k_active": sum(bits)}
        for name, f in XOR_READINGS.items():
            r["XOR:" + name] = int(f(bits))
        for name, f in XNOR_READINGS.items():
            r["XNOR:" + name] = int(f(bits))
        rows.append(r)
    return rows


def diffs(rows, a, b):
    return [r["inputs"] for r in rows if r[a] != r[b]]


# ---------------------------------------------------------------- Issue 3
ISSUE3 = [("Chapter_16_Feedback_Systems.md", n) for n in
          (17, 25, 31, 47, 180, 182, 184, 198, 199, 200, 203, 204, 206, 207,
           211, 213, 278, 291, 311, 330)] + [
    ("Appendix_E_Exercise_Answers.md", 519)]


def closed(A, beta):
    return A / (1 + A * beta)


def fr(x):
    return {"fraction": f"{x.numerator}/{x.denominator}",
            "float_repr": repr(float(x))}


def issue3():
    b333 = Fraction("0.333")
    b13 = Fraction(1, 3)
    out = {"beta_0.333": str(b333), "beta_1/3": str(b13)}
    for bname, b in (("0.333", b333), ("1/3", b13)):
        for A in (12, 10, 18, 15):
            out[f"A={A},beta={bname}"] = fr(closed(Fraction(A), b))
            out[f"loop_gain A={A},beta={bname}"] = fr(Fraction(A) * b)
        out[f"limit 1/beta, beta={bname}"] = fr(1 / b)
        out[f"exactly 3? A=12,beta={bname}"] = closed(Fraction(12), b) == 3
        out[f"exactly 3? A=10,beta={bname}"] = closed(Fraction(10), b) == 3
        out[f"exactly 3? A=18,beta={bname}"] = closed(Fraction(18), b) == 3
        out[f"exactly 3? limit,beta={bname}"] = (1 / b) == 3
    # finite A solving A/(1+A*b) == 3  ->  A = 3/(1-3b)
    A_star = Fraction(3) / (1 - 3 * b333)
    out["A such that A/(1+A*0.333)==3"] = fr(A_star)
    out["check A*=3000 gives exactly 3 (beta=0.333)"] = (
        closed(A_star, b333) == 3)
    out["beta=1/3: 1-3b"] = str(1 - 3 * b13)  # 0 -> no finite solution
    # at beta=1/3, closed = 3A/(3+A) < 3 for every finite A>0
    out["beta=1/3 closed-form"] = "3A/(3+A)"
    out["beta=1/3, A=297 (1% below 3)"] = fr(closed(Fraction(297), b13))
    out["beta=1/3, A=297 equals 297/100"] = (
        closed(Fraction(297), b13) == Fraction(297, 100))
    # drift claim: 12 vs 10 (beta=1/3)
    g12 = closed(Fraction(12), b13)
    g10 = closed(Fraction(10), b13)
    out["beta=1/3: gain(12)-gain(10)"] = fr(g12 - g10)
    out["beta=1/3: (gain(12)-gain(10))/gain(12)"] = fr((g12 - g10) / g12)
    out["beta=1/3: 1 - gain(12)/3"] = fr(1 - g12 / 3)
    out["beta=1/3: forward drop (12-10)/12"] = fr(Fraction(2, 12))
    g12b = closed(Fraction(12), b333)
    g10b = closed(Fraction(10), b333)
    out["beta=0.333: gain(12)-gain(10)"] = fr(g12b - g10b)
    # full chain as listed: c_fwd 12 -> 10 means A 18 -> 15 (c_eval in loop)
    g18b = closed(Fraction(18), b333)
    g15b = closed(Fraction(15), b333)
    out["beta=0.333 full chain: gain(18)-gain(15)"] = fr(g18b - g15b)
    out["beta=0.333 full chain: (gain(18)-gain(15))/gain(18)"] = fr(
        (g18b - g15b) / g18b)
    out["beta=0.333 full chain: 1 - gain(18)/3"] = fr(1 - g18b / 3)
    out["beta=0.333 A=12: 1 - gain(12)/3"] = fr(1 - g12b / 3)
    # non-standard reading: c_eval (1.5) placed OUTSIDE the loop
    out["NONSTANDARD 1.5*A12/(1+12*0.333)"] = fr(
        Fraction(3, 2) * closed(Fraction(12), b333))
    out["NONSTANDARD 1.5*A12/(1+12/3)"] = fr(
        Fraction(3, 2) * closed(Fraction(12), b13))
    # the peer-audit decimals
    out["peer_audit_floats"] = {
        "A12": 2.401921537229784, "A10": 2.3094688221709005,
        "A18": 2.5736345438947668, "limit": 3.003003003003003}
    out["peer_audit_floats_match"] = {
        "A12": float(closed(Fraction(12), b333)) == 2.401921537229784,
        "A10": float(closed(Fraction(10), b333)) == 2.3094688221709005,
        "A18": float(closed(Fraction(18), b333)) == 2.5736345438947668,
        "limit": float(1 / b333) == 3.003003003003003,
        "A12_exact_third": closed(Fraction(12), b13) == Fraction(12, 5),
    }
    return out


def main():
    res = {"repo": REPO, "commit": COMMIT,
           "commit_full": subprocess.run(
               ["git", "-C", REPO, "rev-parse", COMMIT],
               capture_output=True, text=True).stdout.strip()}
    res["issue1"] = {
        "conditional": [line(f, n) for f, n in ISSUE1_CONDITIONAL],
        "automatic": [line(f, n) for f, n in ISSUE1_AUTOMATIC],
        "adjacent_configuration_involution":
            [line(f, n) for f, n in ISSUE1_ADJACENT],
        "syntax": [line(f, n) for f, n in ISSUE1_SYNTAX],
        "matrix": issue1_matrix(),
    }
    res["issue1"]["differing_cells"] = [
        r for r in res["issue1"]["matrix"] if r["differ"]]
    t3, t4 = table(3), table(4)
    res["issue2"] = {"quotes": [line(f, n) for f, n in ISSUE2],
                     "table3": t3, "table4": t4, "diff_rows": {}}
    for n, t in (("3", t3), ("4", t4)):
        xk = list(XOR_READINGS)
        nk = list(XNOR_READINGS)
        d = {}
        for i in range(3):
            for j in range(i + 1, 3):
                d[f"XOR {xk[i]} vs {xk[j]}"] = diffs(
                    t, "XOR:" + xk[i], "XOR:" + xk[j])
                d[f"XNOR {nk[i]} vs {nk[j]}"] = diffs(
                    t, "XNOR:" + nk[i], "XNOR:" + nk[j])
        res["issue2"]["diff_rows"][n] = d
        # book's own pairing: XOR = exactly-one (Ch10:115, AppB:389,
        # AppC:447) and XNOR = inputs agree (AppB:390, AppC:447, Ch10:116).
        # Rows where these two are NOT complements (XNOR != NOT XOR):
        res["issue2"].setdefault("book_pair_not_complement", {})[n] = [
            r["inputs"] for r in t
            if r["XNOR:" + nk[2]] != 1 - r["XOR:" + xk[1]]]
    # sanity: with 2 inputs every reading agrees
    t2 = table(2)
    res["issue2"]["two_input_book_pair_complement"] = all(
        r["XNOR:" + list(XNOR_READINGS)[2]] ==
        1 - r["XOR:" + list(XOR_READINGS)[1]] for r in t2)
    res["issue2"]["two_input_all_agree"] = all(
        len({r["XOR:" + k] for k in XOR_READINGS}) == 1 and
        len({r["XNOR:" + k] for k in XNOR_READINGS}) == 1 for r in t2)
    res["issue3"] = {"quotes": [line(f, n) for f, n in ISSUE3],
                     "numbers": issue3()}
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    # compact console report
    print("commit", res["commit_full"])
    for k, v in res["issue3"]["numbers"].items():
        print("I3", k, "=>", v)
    print("I2 two_input_all_agree", res["issue2"]["two_input_all_agree"])
    print("I2 two_input_book_pair_complement",
          res["issue2"]["two_input_book_pair_complement"])
    print("I2 book_pair_not_complement",
          res["issue2"]["book_pair_not_complement"])
    # markdown truth tables
    md = []
    for n, t in (("3", t3), ("4", t4)):
        cols = list(t[0].keys())
        short = {c: c.split(" (")[0].split(" ('")[0] for c in cols}
        md.append(f"\n#### {n} inputs\n")
        md.append("| " + " | ".join(short[c] for c in cols) + " |")
        md.append("|" + "---|" * len(cols))
        for r in t:
            md.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    Path(__file__).with_name("truth_tables.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8", newline="\n")
    for n in ("3", "4"):
        for k, v in res["issue2"]["diff_rows"][n].items():
            print(f"I2 n={n}", k, "=>", v)
    print("I1 differing cells:",
          [(r["effect_noetic"], r["automatic_out"], r["conditional_out"])
           for r in res["issue1"]["differing_cells"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
