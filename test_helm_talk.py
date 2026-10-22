"""test_helm_talk.py -- the talk layer (A-TALK-2): HELM_TALK (small talk, questions about HELM, off-topic M10, honest
"I don't know") and HELM_TALK_ASK (asking from what HELM knows). Written before the code (B7). Both switches OFF by
default; OFF changes nothing.
"""
from __future__ import annotations

import io
import os
import re
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "docs", "working", "helm_cube_oscillation_v1"),
          os.path.join(HERE, "docs", "working", "noetic_council", "cube_store")):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402

import helm_chat as hc  # noqa: E402
import helm_talk as ht  # noqa: E402
import helm_voice  # noqa: E402

SAMPLE_OFF = ["hi", "thanks", "how are you", "My sister is moving to Denver next month.", "I'm feeling tired today.",
              "who won the game last night?", "are you a robot?"]


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_DIR", str(tmp_path / "sessions"))
    for k in ("HELM_TALK", "HELM_TALK_ASK", "HELM_CUBE_OSC", "HELM_MEMORY_COMPACT", "HELM_EYE_ACT"):
        monkeypatch.delenv(k, raising=False)


def session(name="talk"):
    with redirect_stdout(io.StringIO()):
        return hc.HELMConversationalSession(mode="everyday", session_id=name)


def say(s, text):
    with redirect_stdout(io.StringIO()):
        s.handle_turn(text)
    t = s.memory.turns[-1]
    return t.helm_response, t


# ------------------------------------------------------------------ B1 switches
def test_switches_default_off():
    assert ht.talk_on() is False and ht.ask_on() is False


def test_ask_needs_talk(monkeypatch):
    monkeypatch.setenv("HELM_TALK_ASK", "1")
    assert ht.ask_on() is False
    monkeypatch.setenv("HELM_TALK", "1")
    assert ht.ask_on() is True


def test_off_changes_nothing(monkeypatch):
    a = session("off_a")
    replies_off = [say(a, x)[0] for x in SAMPLE_OFF]
    b = session("off_b")
    replies_again = [say(b, x)[0] for x in SAMPLE_OFF]
    assert replies_off == replies_again
    assert b.talk is None


# ------------------------------------------------------------------ B2 kinds
def test_classify_kinds():
    assert ht.classify("hi") == "SMALL"
    assert ht.classify("Thanks!") == "SMALL"
    assert ht.classify("how's it going") == "SMALL"
    assert ht.classify("are you a robot?") == "SELF"
    assert ht.classify("Do you remember things?") == "SELF"
    assert ht.classify("My sister is moving to Denver next month.") == "OFF"
    assert ht.classify("who won the game last night?") == "WORLD"


def test_small_talk_is_short_plain_and_saves_nothing(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    s = session("small")
    for line in ("hi", "thanks", "how are you", "ok"):
        reply, t = say(s, line)
        assert t.intent == "GENERAL_CONVERSATION" and t.entities.get("talk") == "SMALL"
        assert 1 <= helm_voice.sentence_count(reply) <= 3
        assert not ht.RECIPE_SPEAK_RX.search(reply)
        assert not helm_voice.cas_tokens(reply)
    assert s.memory.context.user_facts == []
    assert not s.loop.stock


def test_self_is_truthful_and_saves_nothing(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    s = session("self")
    reply, t = say(s, "are you a robot?")
    assert t.entities.get("talk") == "SELF"
    assert reply in ht.SELF_REPLIES.values()
    assert not ht.RECIPE_SPEAK_RX.search(reply) and not ht.OPINION_RX.search(reply)
    assert s.memory.context.user_facts == []


def test_world_question_is_an_honest_unknown(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    s = session("world")
    reply, t = say(s, "who won the game last night?")
    assert t.entities.get("talk") == "WORLD"
    assert helm_voice.MARKER_RX["nodata"].search(reply)
    assert s.memory.context.user_facts == []


# ------------------------------------------------------------------ M10 on OFF lines
def test_off_line_reacts_keeps_verbatim_and_asks_once(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    s = session("off")
    line = "My sister is moving to Denver next month."
    reply, t = say(s, line)
    assert t.entities.get("talk") == "OFF"
    first = re.split(r"(?<=[.!?])\s+", reply)[0]
    assert first in ht.OFF_REACT.values()
    assert line.rstrip(".") in s.memory.context.user_facts         # kept word for word (the memory drops the final period)
    assert reply.count("?") == 1
    assert "Denver" in reply                                        # the question uses the person's own word
    assert not ht.OPINION_RX.search(reply) and not ht.RECIPE_SPEAK_RX.search(reply)


def test_feeling_line_is_kept_verbatim(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    s = session("feel")
    line = "I'm feeling tired today."
    reply, t = say(s, line)
    assert t.entities.get("talk") == "OFF"
    assert line.rstrip(".") in s.memory.context.user_facts
    assert reply.split(".")[0] + "." == ht.OFF_REACT["strain"]


def test_feeling_line_with_run_never_reaches_the_tool_engine(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    s = session("rundown")
    reply, t = say(s, "I feel run down this week.")
    assert t.intent != "AGENTIC_GOAL"


def test_question_word_choice_is_deterministic():
    assert ht.pick_word("My sister is moving to Denver next month.") == "Denver"
    assert ht.pick_word("the weather has been strange lately") == "weather"
    assert ht.off_question("the weather has been strange lately") == ht.off_question("the weather has been strange lately")


# ------------------------------------------------------------------ A-TALK-3 W1-W4 wording
def test_w1_a_name_is_the_whole_capitalised_run():
    assert ht.pick_word("We went hiking at Mount Tam on Saturday.") == "Mount Tam"


def test_w2_the_before_a_common_word():
    q = ht.off_question("The weather has been strange lately.")
    assert "the weather" in q and q.endswith("?")
    assert "the Denver" not in ht.off_question("My sister is moving to Denver next month.")


def test_w3_feeling_and_time_words_are_never_the_topic():
    assert ht.pick_word("I feel run down this week.") is None
    assert ht.pick_word("Work was a long day.") == "work"


def test_w4_two_templates_and_the_open_question():
    assert ht.OFF_QUESTIONS == ("What's going on with {w}?", "What happened with {w}?")
    assert ht.off_question("I'm feeling tired today.") == "Do you want to tell me more?"


# ------------------------------------------------------------------ B3 guards
def test_guard_refuses_and_falls_back():
    for bad in ("I think that's great.", "Let's check the recipe stock.", "^3^P is the state.",
                "One. Two. Three. Four.", "No question here."):
        ok, why = ht.guard(bad, "OFF", person_words={"x"}, held=set())
        assert not ok, bad
    ok, _ = ht.guard("Thanks for telling me. What happened with Denver?", "OFF", person_words={"denver"}, held=set())
    assert ok
    assert ht.safe_reply(["I think it is good."], "SMALL", set(), set())[0] == ht.SAFE_LINE


# ------------------------------------------------------------------ B6 asking from what HELM knows
def _taught_session(monkeypatch, name):
    monkeypatch.setenv("HELM_TALK", "1")
    monkeypatch.setenv("HELM_TALK_ASK", "1")
    import helm_cube_osc as hco
    import teach2_rule_reader as trr
    s = session(name)
    hco.attach(s.memory, mode="OSC", proposers=[hco.StandInProposer(trr.rule_read) for _ in range(3)], limit_bytes=None)
    say(s, "The Oxley line ran eight buses in September.")
    return s, hco


def test_asks_about_a_held_cube_thing_and_yes_confirms(monkeypatch):
    s, hco = _taught_session(monkeypatch, "ask_cube")
    assert "thing_oxley" in s.memory.context.cube_store.nodes
    reply, t = say(s, "I took the Oxley bus again today.")
    assert t.entities.get("talk") == "OFF"
    assert "Is that still right?" in reply and "Oxley" in reply and "eight" in reply
    assert reply.count("?") == 1
    reply2, t2 = say(s, "yes")
    assert t2.entities.get("talk") == "ASK_ANSWER"
    assert s.memory.context.cube_store.nodes["thing_oxley"].provenance.source == "CHECKED"


def test_no_answer_writes_nothing(monkeypatch):
    s, hco = _taught_session(monkeypatch, "ask_no")
    say(s, "I took the Oxley bus again today.")
    before = len(s.memory.context.cube_store.branches)
    reply, t = say(s, "no, not anymore")
    assert s.memory.context.cube_store.nodes["thing_oxley"].provenance.source != "CHECKED"
    assert len(s.memory.context.cube_store.branches) == before
    assert "update" in reply.lower()


def test_never_asked_twice(monkeypatch):
    s, hco = _taught_session(monkeypatch, "ask_twice")
    r1, _ = say(s, "I took the Oxley bus again today.")
    say(s, "yes")
    r2, _ = say(s, "The Oxley bus was late again.")
    assert "Is that still right?" in r1 and "Is that still right?" not in r2


def test_asks_about_a_held_stock_name(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    monkeypatch.setenv("HELM_TALK_ASK", "1")
    s = session("ask_stock")
    say(s, "We have 12 cups of flour.")
    held = sorted(s.loop.stock)
    assert held
    name = held[0]
    reply, t = say(s, f"My neighbour keeps asking about my {name.lower()}.")
    assert t.entities.get("talk") == "OFF"
    assert "Is that still right?" in reply
    assert f"12 cups of {name.lower()}" in reply                     # A-TALK-3 W5: the person's own unit
    reply2, t2 = say(s, "yes")
    assert "keep it as it is" in reply2.lower()


def test_ask_off_means_plain_m10(monkeypatch):
    monkeypatch.setenv("HELM_TALK", "1")
    import helm_cube_osc as hco
    import teach2_rule_reader as trr
    s = session("ask_off")
    hco.attach(s.memory, mode="OSC", proposers=[hco.StandInProposer(trr.rule_read) for _ in range(3)], limit_bytes=None)
    say(s, "The Oxley line ran eight buses in September.")
    reply, _ = say(s, "I took the Oxley bus again today.")
    assert "Is that still right?" not in reply and reply.count("?") == 1
