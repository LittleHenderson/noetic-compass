"""Canon guard for the example sentences shown by the offline CAS tool and by the dashboard compiler page.

Found 2026-09-21: twelve example sentences called F2 "Vitality" (F2 is Wisdom), called F6 "Purpose" (F6 is
Structure), and stuck nicknames onto Noetic names ("Female/Differentiation", "Negative/Boundary",
"Male/Structure", "Positive/affirming"). The reference tables in the same files were always right; only the
hand-written sentences drifted. These tests read every sentence and check it against the tables.

A DESCRIPTION of what a Noetic does is allowed. A REPLACEMENT NAME is not.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
NOETICS = ["Idea", "Mind", "Positive", "Negative", "Vibration", "Female", "Male", "Rhythm", "Above/Cause", "Below/Effect"]
DRIVES = {1: "Unity", 2: "Wisdom", 3: "Vitality", 4: "Connection", 5: "Agency", 6: "Structure", 7: "Purpose"}
DOMAINS = {"Principled", "Cognitive", "Evaluative", "Operational"}
RETIRED_NAMES = [
    # Scheme A
    "Reflection", "Abstraction", "Concretization", "Differentiation", "Unification", "Transformation", "Expansion", "Contraction",
    # Scheme B
    "Generative Potential", "Directed Attention", "Attraction/Affinity", "Critical Evaluation", "Encoding Intensity",
    "Receptive Integration", "Projective Assertion", "Pattern Entrainment", "Causal Initiation", "Causal Reasoning",
    "Consequential Grounding",
]
TERMINAL_COPIES = [REPO / "offline-cas" / "cas_terminal.py", REPO / "dist" / "cas-offline" / "cas_terminal.py"]
DASHBOARD_PAGE = REPO / "noetic-compass-scaffold" / "noetic-compass" / "dashboard" / "src" / "pages" / "CompilerPage.tsx"


def _load(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("cas_terminal_under_test_%d" % abs(hash(str(path))), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _examples():
    rows = []
    for path in TERMINAL_COPIES:
        if path.is_file():
            for row in _load(path).EXAMPLES:
                rows.append((path.parent.name, row["expr"], row["natural"]))
    if DASHBOARD_PAGE.is_file():
        text = DASHBOARD_PAGE.read_text(encoding="utf-8")
        for expr, natural in re.findall(r"\{ expr: '([^']*)',[^\n]*?natural: '([^']*)' \}", text):
            rows.append(("dashboard", expr, natural))
    return rows


EXAMPLES = _examples()


def test_there_are_sentences_to_check():
    if not EXAMPLES:
        pytest.skip("neither the offline tool nor the dashboard page is checked out here")
    assert len(EXAMPLES) >= 30


@pytest.mark.parametrize("where,expr,natural", EXAMPLES)
def test_a_drive_is_named_only_when_the_expression_uses_it(where, expr, natural):
    for number, name in DRIVES.items():
        if re.search(r"\b%s\b" % name, natural):
            uses_it = re.search(r"F_?%d\b" % number, expr) or ("Foundation_%d" % number) in expr
            assert uses_it, "%s: the sentence names the %s drive (F%d) but the expression %r does not use F%d" % (where, name, number, expr, number)


@pytest.mark.parametrize("where,expr,natural", EXAMPLES)
def test_a_drive_used_with_a_state_is_called_by_its_own_name(where, expr, natural):
    wrong = {n: name for n, name in DRIVES.items()}
    for number in re.findall(r"_\{F(\d)\}", expr):
        for other, name in wrong.items():
            if other != int(number) and not re.search(r"F_?%d\b" % other, expr):
                assert not re.search(r"\b%s (?:drive|state)\b|under %s\b|/%s\b" % (name, name, name), natural), (
                    "%s: %r uses F%s (%s) but the sentence says %s" % (where, expr, number, DRIVES[int(number)], name))


@pytest.mark.parametrize("where,expr,natural", EXAMPLES)
def test_a_noetic_keeps_its_one_canonical_name(where, expr, natural):
    for retired in RETIRED_NAMES:
        assert retired not in natural, "%s: retired name %r in %r" % (where, retired, natural)
    for name in NOETICS:
        for follower in re.findall(re.escape(name) + r"/([A-Za-z]+)", natural):
            assert follower in DOMAINS, "%s: %s/%s is a nickname; only Noetic/Domain pairs such as Positive/Principled are allowed" % (where, name, follower)


# --- The three guards below were written on this line, then deleted by my own merge resolution on 2026-09-21
# --- while they were PASSING (an independent checker ran the 9-function version against the merged help text
# --- and got 454 passed). Restored 2026-09-22. They are the difference between 273 and 454 collected cases.

BARE_NICKNAMES = ["Boundary", "boundary signal", "Differentiation", "affirming", "Concretization", "Abstraction", "Reflection",
                  "Unification", "Transformation", "Expansion", "Contraction", "Structure/", "Integration", "Attraction", "Aversion"]
NOETIC_OF = {"^%d" % i: name for i, name in enumerate(NOETICS)}


@pytest.mark.parametrize("where,expr,natural", EXAMPLES)
def test_no_bare_nickname_word_stands_in_for_a_noetic(where, expr, natural):
    """A retired Scheme-A/B/C name must not appear even WITHOUT a slash. `test_a_noetic_keeps_its_one_canonical_name`
    only catches the `Female/Differentiation` shape; this catches a bare `Boundary` standing in for ^3."""
    for word in BARE_NICKNAMES:
        assert word not in natural, "%s: nickname word %r in %r" % (where, word, natural)


@pytest.mark.parametrize("where,expr,natural", EXAMPLES)
def test_every_noetic_named_in_the_sentence_is_in_the_expression(where, expr, natural):
    """A sentence may not name a Noetic its own expression does not contain."""
    present = {NOETIC_OF[m] for m in re.findall(r"\^\d", expr)} | {NOETICS[int(d)] for d in re.findall(r"CO-(\d)", expr)}
    present |= {NOETICS[int(d)] for d in re.findall(r"Phi<([\d:]+)>", expr) for d in d.split(":")}
    if not present:
        return                                          # sentences about sets, drives or yields name no Noetic by position
    for name in NOETICS:
        if re.search(r"\b%s\b" % re.escape(name), natural):
            assert name in present, "%s: the sentence names %s but %r has no such Noetic" % (where, name, expr)


def test_dictionary_entries_carry_the_canonical_notation():
    """The glossary tables, not just the example sentences: every Noetic on its own number, every Drive on its own
    number, no nickname word in a definition, and no '4 Domains = 28' for a set of Drive|Register positions."""
    for path in TERMINAL_COPIES:
        if not path.is_file():
            continue
        rows = {(row["category"], row["term"]): row["notation"] for row in _load(path).DICTIONARY}
        for i, name in enumerate(NOETICS):
            assert rows[("Noetic Operators", name)] == "^%d" % i, (path.parent.name, name)
        for k, name in DRIVES.items():
            assert rows[("Drives", name)] == "F%d" % k, (path.parent.name, name)
        for row in _load(path).DICTIONARY:
            for word in BARE_NICKNAMES:
                assert word not in row["definition"] and word not in row["learn"], (path.parent.name, row["term"], word)
            assert "4 Domains = 28" not in row["definition"], "the compiler's SubFoundations are Drive|Register positions"


def test_the_name_tables_themselves_are_canonical():
    for path in TERMINAL_COPIES:
        if path.is_file():
            module = _load(path)
            assert list(module.OPERATOR_NAMES) == NOETICS
            assert list(module.DRIVE_NAMES) == [DRIVES[k] for k in range(1, 8)]


def test_the_shipped_copy_is_the_build_source():
    source, shipped = TERMINAL_COPIES
    if source.is_file() and shipped.is_file():
        assert source.read_bytes().replace(b"\r\n", b"\n") == shipped.read_bytes().replace(b"\r\n", b"\n"), (
            "dist/cas-offline/cas_terminal.py is no longer the same text as offline-cas/cas_terminal.py; rebuild the package")
