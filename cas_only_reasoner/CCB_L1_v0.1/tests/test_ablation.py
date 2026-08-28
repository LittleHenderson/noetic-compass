"""Ablation: removing an entry breaks parsing, typed and located."""

import pytest

from conftest import load_fixture
from lang.grammar import ParseError
from lang.l1 import CCB_L1


def test_ablation_breaks_parsing_with_location():
    l1 = CCB_L1(load_fixture("seed_lexicon.json"))
    l1.lexicon.remove("gray")
    with pytest.raises(ParseError) as exc_info:
        l1.parse("the cat is gray.")
    assert exc_info.value.token == "gray"
    assert exc_info.value.index == 3
    assert "I did not understand 'gray' at word 4" in \
        exc_info.value.message()


def test_ablation_does_not_break_other_sentences():
    l1 = CCB_L1(load_fixture("seed_lexicon.json"))
    l1.lexicon.remove("gray")
    meaning = l1.parse("the dog chases the cat.")
    assert meaning == {"pred": "relation", "args": ["chase", "dog", "cat"]}
