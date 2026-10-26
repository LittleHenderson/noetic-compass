"""Tests for the speech gateway: variety where there are no facts, strictness where there are."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from speech_gateway import Frame, SpeechGateway, validate  # noqa: E402


def test_greetings_vary():
    gw = SpeechGateway(seed=5)
    outs = [gw.speak(Frame(intent="GREETING"))["text"] for _ in range(20)]
    assert len(set(outs)) >= 12, len(set(outs))
    assert all(o.endswith("?") for o in outs)


def test_refusals_vary():
    gw = SpeechGateway(seed=5)
    outs = [gw.speak(Frame(intent="REFUSE"))["text"] for _ in range(20)]
    assert len(set(outs)) >= 12, len(set(outs))


def test_unlicensed_number_rejected():
    f = Frame(intent="ANSWER", slots={}, licensed=["stonewick"], facts=True)
    ok, why = validate(f, "Stonewick yard had 42 colonies in September.")
    assert not ok and "42" in why


def test_unlicensed_name_rejected():
    f = Frame(intent="ANSWER", slots={}, licensed=["stonewick", "eight", "september"], facts=True)
    ok, why = validate(f, "In September, Stonewick yard had eight colonies at Vellmoor.")
    assert not ok and "Vellmoor" in why


def test_licensed_answer_passes():
    f = Frame(intent="ANSWER", slots={"name": "Stonewick", "place": "yard", "month": "September",
                                      "num": "eight", "thing": "colonies"},
              licensed=["stonewick", "yard", "september", "eight", "colonies"], facts=True)
    ok, why = validate(f, "In September, Stonewick yard had eight colonies.")
    assert ok, why


def test_composer_used_when_proposer_unavailable():
    class Dead:
        available = False

        def render(self, frame, seed=0):
            return None

    gw = SpeechGateway(proposer=Dead(), seed=1)
    out = gw.speak(Frame(intent="SMALLTALK"))
    assert out["ok"] is False
    assert out["renderer"] == "refusal"
    assert out["text"].endswith(".")
