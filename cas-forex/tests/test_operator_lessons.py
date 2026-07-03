"""Tests: durable cross-operator lessons journal (learn-once, inherit-forever)."""

from __future__ import annotations

import json

import pytest

from cas_forex import ai_operator, model_provider, operator_lessons
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests


@pytest.fixture(autouse=True)
def _isolated_lessons(tmp_path):
    operator_lessons.set_lessons_path_for_tests(tmp_path / "lessons.json")
    yield
    operator_lessons.set_lessons_path_for_tests(None)


def test_record_and_list_newest_first():
    operator_lessons.record_lesson("Trailing stop nets worse than holding on M1 scalps", category="exit_policy", evidence="-$67 over 72 trades")
    operator_lessons.record_lesson("GBP/USD LONG blend is a chronic loser", category="market")
    lessons = operator_lessons.list_lessons()
    assert len(lessons) == 2
    assert lessons[0]["text"].startswith("GBP/USD LONG")  # newest first
    assert lessons[1]["category"] == "exit_policy"


def test_near_duplicate_reinforces_instead_of_duplicating():
    operator_lessons.record_lesson("US30 SHORT profit was a lucky cluster not edge")
    operator_lessons.record_lesson("US30 SHORT profit was a lucky cluster, not a real edge at all")
    lessons = operator_lessons.list_lessons()
    assert len(lessons) == 1
    assert lessons[0]["reinforced_count"] == 2


def test_empty_lesson_ignored():
    assert operator_lessons.record_lesson("   ") is None
    assert operator_lessons.lessons_count() == 0


def test_bad_category_falls_back_to_general():
    stored = operator_lessons.record_lesson("something", category="nonsense")
    assert stored["category"] == "general"


class _StubProvider:
    def __init__(self, text):
        self._text = text

    def generate(self, prompt, system=None):
        return {"ok": True, "text": self._text, "provider": "claude", "provider_label": "stub",
                "paid": True, "failover": False, "error": None}


def test_operator_records_lessons_from_a_tick(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    decision = {
        "observations": "trailing nets negative",
        "actions": [{"type": "adjust_dial", "lever": "trailing_stop_enabled", "value": 0, "reason": "measured worse"}],
        "lessons": [
            {"text": "Trailing stop nets worse than holding on these M1 scalps", "category": "exit_policy", "evidence": "-$67/72 trades"},
            {"text": "Raw paper P&L is inflated by burst clusters — trust the de-clustered net", "category": "data_quality"},
        ],
        "summary": "disabled trailing, recorded lessons",
    }
    model_provider.set_model_provider_for_tests(_StubProvider(json.dumps(decision)))
    try:
        op = ai_operator.AIOperator(actions_path=tmp_path / "actions.jsonl")
        tick = op.tick()
        assert tick.ok is True
        # The two tick lessons land on top of the seeded founding principles.
        lessons = operator_lessons.list_lessons()
        texts = " ".join(l["text"] for l in lessons)
        assert "Trailing stop nets worse" in texts
        assert "de-clustered" in texts
    finally:
        model_provider.set_model_provider_for_tests(None)
        set_authority_for_tests(None)


def test_inherited_lessons_reach_the_next_operators_context(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    try:
        operator_lessons.record_lesson("Do not re-enable trailing on M1 — it nets worse than holding", category="exit_policy")
        context = ai_operator.gather_context()
        inherited = context.get("inherited_lessons") or []
        assert any("Do not re-enable trailing" in (l.get("lesson") or "") for l in inherited)
    finally:
        set_authority_for_tests(None)
