"""Tests for the canonical 28 Foundations coordinate.

Every expected value below was TYPED BY HAND from the owner's document "28 Foundations 1.0" (the page-1
table and the 28 numbered definitions), not produced by the module under test.

Run:  python -m pytest research/helm_cas_expression_lab/test_foundations28.py -q      (under a second)
"""
import hashlib
import json
import pathlib
import re
import shutil

import pytest

import foundations28 as F

HERE = pathlib.Path(__file__).resolve().parent

# the document's own numbering (1..28) -> symbol, typed from the numbered definitions
NUMBERED = {1: "1a", 2: "2a", 7: "7a", 8: "1b", 9: "2b", 12: "5b", 14: "7b", 15: "1c", 19: "5c", 21: "7c", 22: "1d", 26: "5d", 28: "7d"}
# headings typed from the page-1 table
TITLES = {
    "1a": "Spiritual desire to be and be with God",
    "4a": "Spiritual companionship, love, and friendship",
    "3b": "Mental life, vitality, and health",
    "2c": "Emotional wisdom, insight, and knowledge",
    "5c": "Emotional worldly power, influence, and control",
    "6d": "Physical material food and things",
    "7d": "Physical lust, sex, and reproduction",
}
# opening words typed from the numbered definitions
OPENINGS = {
    "1a": "The core drive to merge with the divine.",
    "1d": "Bodily expressions of spiritual longing.",
    "5d": "Dominance through bodily strength and presence.",
    "7d": "Bodily drive for pleasure and procreation.",
    "2b": "Cultivating discernment through rigorous analysis and intuition.",
}
ENTRY_7B_WHOLE = ("Yearning for intellectual debate, intellectual exercise, to be bored out of one's mind and or spread the ideas "
                  "one holds replicating one's mentality in the mind of another.")


def test_there_are_exactly_28_and_the_order_is_the_documents_numbering():
    syms = F.symbols()
    assert len(syms) == 28 and len(set(syms)) == 28
    for number, sym in NUMBERED.items():
        assert syms[number - 1] == sym and F.index(sym) == number - 1 and F.symbol(number - 1) == sym


def test_index_and_symbol_are_inverse_on_all_28():
    for position in range(28):
        assert F.index(F.symbol(position)) == position
    assert sorted(F.index(s) for s in F.symbols()) == list(range(28))


def test_titles_are_the_documents_headings():
    for sym, heading in TITLES.items():
        assert F.title(sym) == heading


def test_definitions_are_verbatim_and_complete():
    for sym, opening in OPENINGS.items():
        assert F.definition(sym).startswith(opening), sym
    assert F.definition("7b") == ENTRY_7B_WHOLE
    assert all(len(F.definition(s).split()) >= 20 for s in F.symbols())


def test_cas_positions_are_positions_only():
    assert F.to_cas_position("1a") == "F1|T" and F.to_cas_position("3b") == "F3|A"
    assert F.to_cas_position("7c") == "F7|f" and F.to_cas_position("5d") == "F5|E"
    for sym in F.symbols():
        position = F.to_cas_position(sym)
        assert re.fullmatch(r"F[1-7]\|[TAfE]", position) and F.from_cas_position(position) == sym
    # the CAS drive labels are a positional relabelling, never the meaning of a Foundation
    for label in ("Unity", "Vitality", "Connection", "Agency", "Structure", "Purpose"):
        assert all(label not in F.title(s) for s in F.symbols())
        assert label not in json.dumps([F.to_cas_position(s) for s in F.symbols()])


@pytest.mark.parametrize("bad", ["8a", "0a", "3e", "3B", "b3", "3", "3bb", "", 3, None, 3.0, ["3b"]])
def test_malformed_symbols_are_refused(bad):
    with pytest.raises(F.Foundation28Error):
        F.index(bad)


@pytest.mark.parametrize("bad", [True, False, 3.0, "3", -1, 28, None])
def test_malformed_indices_are_refused(bad):
    with pytest.raises(F.Foundation28Error):
        F.symbol(bad)


@pytest.mark.parametrize("bad", ["F8|A", "F0|T", "F3|F", "F3|a", "f3|A", "F3A", "F3|", "3b", 3, None])
def test_malformed_cas_positions_are_refused(bad):
    with pytest.raises(F.Foundation28Error):
        F.from_cas_position(bad)


def test_the_source_is_pinned_and_a_changed_source_is_refused(tmp_path, monkeypatch):
    raw = F.SOURCE.read_bytes()
    assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == F.SOURCE_SHA256
    tampered = tmp_path / "tootra_28_full_definitions.json"
    data = json.loads(raw.decode("utf-8"))
    data["definitions"]["5a"] = "Agency."                     # the exact substitution the canon rule forbids
    tampered.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(F, "SOURCE", tampered)
    with pytest.raises(F.Foundation28Error, match="FOUNDATIONS28_SOURCE_CHANGED"):
        F.definition("5a")


def test_the_vendored_copy_equals_the_repository_capture_when_that_is_on_disk():
    for parent in HERE.parents:
        origin = parent / F.SOURCE_ORIGIN
        if origin.is_file():
            assert origin.read_bytes().replace(b"\r\n", b"\n") == F.SOURCE.read_bytes().replace(b"\r\n", b"\n")
            return
    pytest.skip("the repository capture is not in this checkout (sparse); the pinned hash still guards the copy")


def test_known_discrepancies_are_recorded_not_fixed():
    ids = [d["id"] for d in F.KNOWN_DISCREPANCIES]
    assert ids == ["F28-1", "F28-2", "F28-3", "F28-4", "F28-5", "F28-6"]
    # the capture still carries its own punctuation -- this module does not rewrite the canon text
    assert F.definition("3b").endswith("Curiosity.") and "'caught up'" in F.definition("1c")
    assert F.CANON_DOCUMENT["sha256_raw"].startswith("2c27443f447bd699") and F.CANON_DOCUMENT["owner_ruling"] == "CANONICAL 28 FOUNDATIONS"
