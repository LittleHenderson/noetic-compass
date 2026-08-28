"""Round-trip meaning and paraphrase convergence (charter tests 1-2)."""

from conftest import load_fixture
from lang.l1 import CCB_L1


def _l1():
    return CCB_L1(load_fixture("seed_lexicon.json"))


def test_property_roundtrip():
    l1 = _l1()
    result = l1.roundtrip("the cat is gray.")
    assert result["stable"] is True
    assert result["meaning"] == {"pred": "property", "args": ["cat", "gray"]}
    assert result["surface"] == "the cat is gray."


def test_relation_roundtrip():
    l1 = _l1()
    result = l1.roundtrip("the dog chases the cat.")
    assert result["stable"] is True
    assert result["meaning"] == {"pred": "relation",
                                 "args": ["chase", "dog", "cat"]}


def test_negation_roundtrip():
    l1 = _l1()
    result = l1.roundtrip("the cat is not brown.")
    assert result["stable"] is True
    assert result["meaning"]["pred"] == "negation"


def test_question_roundtrip():
    l1 = _l1()
    meaning = l1.parse("is the cat gray?")
    assert meaning["pred"] == "question"
    surface = l1.generate(meaning)
    assert surface == "is the cat gray?"
    meaning2 = l1.parse(surface)
    assert meaning2 == meaning


def test_paraphrase_via_pronoun():
    l1 = _l1()
    first = l1.parse("the cat is gray.")
    second = l1.parse("it is gray.")
    assert first == second == {"pred": "property", "args": ["cat", "gray"]}


def test_reference_last_mentioned():
    l1 = _l1()
    l1.parse("the cat chases the dog.")
    meaning = l1.parse("it is brown.")
    assert meaning == {"pred": "property", "args": ["dog", "brown"]}
