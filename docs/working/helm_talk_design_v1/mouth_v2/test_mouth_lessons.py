"""Tests for mouth_lessons.py (A-TALK-4 W3-W6), written before the code. Run: python -m pytest -q test_mouth_lessons.py"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mouth_lessons as ML  # noqa: E402


def test_fact_inputs_are_deterministic_and_cover_the_three_situations():
    a, b = ML.fact_inputs(30), ML.fact_inputs(30)
    assert a == b
    assert {x["situation"] for x in a} == {"ANSWER", "SAYBACK", "ASK"}
    for x in a:
        r = x["reading"]
        assert r["thing"] and r["value"] and r["slot"]
        assert x["input_text"].startswith(x["situation"].lower())


def test_tone_rule_is_frozen_and_never_from_a_model():
    assert ML.tone("ANSWER", "") == ("^1", "|A")
    assert ML.tone("OFF", "I'm so tired today") == ("^1", "|f")
    assert ML.tone("OFF", "The weather was strange") == ("^1", "|A")
    assert ML.tone("SMALL", "hi") == ("^1", "|f")


def test_rule_check_refuses_a_new_fact():
    inp = {"situation": "ANSWER", "reading": {"thing": "oxley", "slot": ["buses", "line", "september"], "value": "eight",
                                              "replaces": None}, "input_text": "answer oxley buses line september eight"}
    ok, _ = ML.rule_check(inp, "You told me the Oxley line ran eight buses in September.")
    assert ok
    for bad in ("You told me the Oxley line ran nine buses in September.",        # a number not in the input
                "You told me the Dunmere line ran eight buses in September.",     # a name not in the input
                "You told me the Oxley line ran eight buses in October.",         # a month not in the input
                "I think the Oxley line ran eight buses in September.",            # an opinion
                "The Oxley line. Eight buses. September. Really. Yes."):           # over three sentences
        ok, why = ML.rule_check(inp, bad)
        assert not ok, bad


def test_rule_check_off_needs_one_question_from_the_persons_words():
    inp = {"situation": "OFF", "person_line": "My sister is moving to Denver next month.",
           "input_text": "off My sister is moving to Denver next month."}
    assert ML.rule_check(inp, "That's a big change. When does she leave for Denver?")[0]
    assert not ML.rule_check(inp, "That's a big change.")[0]                                  # no question
    assert not ML.rule_check(inp, "Is she moving to Chicago? Or Denver?")[0]                  # a new name, two questions


def test_ask_must_end_with_a_question_and_carry_the_value():
    inp = {"situation": "ASK", "reading": {"thing": "oxley", "slot": ["buses", "line", "september"], "value": "eight",
                                           "replaces": None}, "input_text": "ask oxley buses line september eight"}
    assert ML.rule_check(inp, "Was it still eight buses on the Oxley line in September?")[0]
    assert not ML.rule_check(inp, "Was it still eight buses on the Oxley line in September.")[0]


def test_template_share_is_capped():
    rows = [{"source": "LLM_WRITTEN"}] * 90 + [{"source": "TEMPLATE"}] * 30
    capped = ML.cap_templates(rows)
    assert sum(r["source"] == "TEMPLATE" for r in capped) <= 0.10 * len(capped) + 1e-9


def test_split_holds_inputs_out_whole():
    rows = [{"input_key": f"k{i % 20}", "source": "LLM_WRITTEN"} for i in range(60)]
    tr, dv = ML.split(rows)
    assert not ({r["input_key"] for r in tr} & {r["input_key"] for r in dv})
    assert dv


def test_helms_own_name_is_allowed():
    inp = ML.line_input("SELF", "What are you called?", "k")
    assert ML.rule_check(inp, "I'm HELM, a program that keeps what you tell me in this chat.")[0]



def test_v2_word_list_keeps_everyday_words_and_drops_facts_and_world_nouns():
    """A-TALK-7 H1 F1: the everyday-word rule keeps 'what' and drops only fact words and the world's nouns."""
    rows = [{"source": "LLM_WRITTEN", "input_text": "off i got a new dog", "target": t} for t in
            ("What a day! What about the dog?", "What about Oxley and the colonies in March? Tell me.")]
    fw = ML.function_words(rows)
    assert "what" in fw and "about" in fw
    for w in ("oxley", "colonies", "march"):
        assert w not in fw


def test_v2_rule_check_refuses_a_line_that_repeats_a_word():
    x = ML.line_input("OFF", "Our basement has a bat in it.", "t:1")
    assert not ML.rule_check(x, "A bat bat in your basement. How did it get in?")[0]
    assert ML.rule_check(x, "A bat in your basement. How did it get in?")[0]


def test_v2_vocab_words_and_their_forms_join_the_lock_but_never_facts():
    """A-TALK-9 J1: vetted vocabulary + regular forms join the word list; names, numbers, months, world nouns never."""
    fw = ML.function_words([], vocab=["snow", "pick", "doze", "early", "oxley", "march", "seven", "colonies"])
    for w in ("snow", "snows", "pick", "picking", "picked", "doze", "dozing", "dozed", "early"):
        assert w in fw, w
    for w in ("oxley", "march", "seven", "colonies"):
        assert w not in fw, w


def test_v2_off_topic_template_lines_are_not_lessons():
    """A-TALK-9 J2: the off-topic template is the fallback only."""
    rows = [{"situation": "OFF", "source": "TEMPLATE"}, {"situation": "SMALL", "source": "TEMPLATE"},
            {"situation": "OFF", "source": "LLM_WRITTEN"}]
    assert [r["situation"] + r["source"] for r in ML.lesson_templates_ok(rows)] == ["SMALLTEMPLATE", "OFFLLM_WRITTEN"]


def test_v2_doubled_consonant_and_est_forms():
    """A-TALK-10 K1: stop -> stopped / stopping, jam -> jamming, cut -> cutting, fast -> fastest."""
    for base, form in (("stop", "stopped"), ("stop", "stopping"), ("jam", "jamming"), ("cut", "cutting"),
                       ("fast", "fastest"), ("noise", "noisy"), ("happy", "happier"), ("happy", "happiest")):
        assert form in ML.word_forms(base), (base, form)


def test_v2_possessive_keeps_the_thing():
    """A-TALK-10 K2: "Longmoor's line" states the thing longmoor."""
    x = {"situation": "ANSWER", "input_text": "answer longmoor line rerouted september through cresswell",
         "reading": {"thing": "longmoor", "slot": ["line", "rerouted", "september", "through"], "value": "cresswell",
                     "replaces": None}, "tone": ["^1", "|A"]}
    assert ML.rule_check(x, "You said Longmoor's line got rerouted through Cresswell in September.")[0]
