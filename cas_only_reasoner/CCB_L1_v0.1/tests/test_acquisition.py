"""Word learning: unknown detection, examples, held-out, contrast,
promotion, novel composition (charter tests 3, 4, 7)."""

from conftest import load_fixture
from lang.l1 import CCB_L1


def _l1():
    return CCB_L1(load_fixture("seed_lexicon.json"))


def test_unknown_word_reported_typed_and_located():
    from lang.grammar import ParseError
    l1 = _l1()
    try:
        l1.parse("the cat is flurpy.")
        assert False, "expected ParseError"
    except ParseError as exc:
        assert exc.token == "flurpy"
        assert exc.index == 3
        assert "word 4" in exc.message()


def test_flurpy_gray_promoted_loud_rejected():
    l1 = _l1()
    cycle = l1.teach(load_fixture("teach_flurpy.json"))
    verdicts = {d["candidate_sense"]: d["verdict"]
                for d in cycle["decisions"]}
    assert verdicts["gray"] == "PROMOTED"
    assert verdicts["loud"] == "REJECTED"
    assert cycle["promoted_sense"] == "gray"
    entry = l1.lexicon.lookup("flurpy")
    assert entry.status == "verified"
    assert entry.sense == "gray"


def test_promoted_word_used_in_held_out_form():
    l1 = _l1()
    l1.teach(load_fixture("teach_flurpy.json"))
    meaning = l1.parse("the cat is not flurpy.")
    assert meaning["pred"] == "negation"
    assert meaning["args"][0] == {"pred": "property", "args": ["cat", "gray"]}


def test_novel_composition_unseen_combination():
    l1 = _l1()
    l1.teach(load_fixture("teach_flurpy.json"))
    l1.lexicon.add_provisional("zorp", "noun", "zorp", provenance="teacher")
    meaning = l1.parse("the zorp is flurpy.")
    assert meaning == {"pred": "property", "args": ["zorp", "gray"]}


def test_correction_retention_versions_verified_entry():
    l1 = _l1()
    l1.teach(load_fixture("teach_flurpy.json"))
    result = l1.correct("flurpy", "black")
    assert result["action"] == "CORRECTION"
    assert result["new_sense"] == "black"
    # The old sense is retained in history - no silent change.
    assert any(h.get("sense") == "gray" for h in result["history"])
    meaning = l1.parse("the cat is flurpy.")
    assert meaning == {"pred": "property", "args": ["cat", "black"]}


def test_acquisition_cycle_deterministic():
    a = _l1().teach(load_fixture("teach_flurpy.json"))
    b = _l1().teach(load_fixture("teach_flurpy.json"))
    assert a["cycle_digest"] == b["cycle_digest"]
    assert a["promoted_sense"] == b["promoted_sense"] == "gray"


def test_rollback_preserves_parent_digest():
    l1 = _l1()
    l1.teach(load_fixture("teach_flurpy.json"))
    result = l1.rollback()
    assert result["action"] == "ROLLBACK"
    assert l1.history[0]["lexicon_digest"] in result["note"]
