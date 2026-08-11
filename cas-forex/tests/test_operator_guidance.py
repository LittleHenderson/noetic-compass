"""Tests: standing owner guidance + operator chat (conversational only)."""

from __future__ import annotations

import json

import pytest

from cas_forex import ai_operator, model_provider, operator_guidance
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests


@pytest.fixture(autouse=True)
def _isolated_guidance(tmp_path, monkeypatch):
    import cas_forex.spec_context as spec_context

    operator_guidance.set_guidance_path_for_tests(tmp_path / "guidance.json")
    monkeypatch.setattr(spec_context, "operator_constitution", lambda: "")
    yield
    operator_guidance.set_guidance_path_for_tests(None)


def test_guidance_crud_and_prompt_order():
    a = operator_guidance.add_note("bank big winners early, then restart the cycle")
    operator_guidance.add_note("prefer London session for GBP pairs")
    notes = operator_guidance.list_notes()
    assert len(notes) == 2
    assert notes[0]["text"].startswith("prefer London")  # newest first
    prompt_lines = operator_guidance.guidance_for_prompt()
    assert prompt_lines[1].startswith("bank big winners")
    assert operator_guidance.remove_note(a["note_id"]) is True
    assert len(operator_guidance.list_notes()) == 1


def test_empty_note_rejected():
    with pytest.raises(ValueError):
        operator_guidance.add_note("   ")


def test_guidance_reaches_operator_context(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    try:
        operator_guidance.add_note("shorten the WASTE cycle by taking profit on big wins")
        context = ai_operator.gather_context()
        assert any("shorten the WASTE cycle" in g for g in context.get("owner_guidance", []))
    finally:
        set_authority_for_tests(None)


class _StubProvider:
    def __init__(self):
        self.last_prompt = ""
        self.last_system = ""

    def generate(self, prompt, system=None):
        self.last_prompt = prompt
        self.last_system = system or ""
        return {
            "ok": True,
            "text": "Banking big winners early trades tail size for cycle speed; on paper it accelerates learning.",
            "provider": "claude",
            "provider_label": "Claude (stub)",
            "paid": True,
            "failover": False,
            "error": None,
        }


def test_chat_answers_with_context_and_never_moves_dials(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    stub = _StubProvider()
    model_provider.set_model_provider_for_tests(stub)
    try:
        operator_guidance.add_note("bank big winners early")
        op = ai_operator.AIOperator(actions_path=tmp_path / "actions.jsonl")
        before = AiControlAuthority(tmp_path / "authority.json").control.get("edge_threshold")
        reply = op.chat("would it be prudent to take profit on big wins then repeat WASTE?")
        assert reply["ok"] is True
        assert "cycle speed" in reply["reply"]
        assert reply["dials_changed"] is False
        # The guidance and the learning context both reached the model.
        assert "bank big winners early" in stub.last_prompt
        assert "OWNER'S MESSAGE" in stub.last_prompt
        assert "Chat is not a direct order or money-movement surface" in stub.last_system
        assert "autonomous side effects" in stub.last_system
        assert reply["chat_path_status"] == "MODEL_PRIMARY"
        # No dial moved.
        from cas_forex.ai_control_authority import get_authority

        assert get_authority().control.get("edge_threshold") == before
        # Chat is logged.
        log = (tmp_path / "ai-operator-chat.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(log) == 1
        assert json.loads(log[0])["question"].startswith("would it be prudent")
    finally:
        model_provider.set_model_provider_for_tests(None)
        set_authority_for_tests(None)


def test_chat_no_model_is_honest(tmp_path):
    class _Down:
        def generate(self, prompt, system=None):
            return {"ok": False, "text": "", "provider": None, "error": "no model reachable", "paid": False}

    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    model_provider.set_model_provider_for_tests(_Down())
    try:
        op = ai_operator.AIOperator(actions_path=tmp_path / "actions.jsonl")
        reply = op.chat("hello?")
        assert reply["ok"] is True
        assert reply["model_ok"] is False
        assert reply["fallback"] is True
        assert reply["error"] == "no model reachable"
        assert "local Operator fallback" in reply["reply"]
    finally:
        model_provider.set_model_provider_for_tests(None)
        set_authority_for_tests(None)


def test_chat_answers_floating_pnl_status_through_model_first(tmp_path):
    class _Provider:
        called = False
        prompt = ""

        def generate(self, prompt, system=None):
            self.called = True
            self.prompt = prompt
            return {
                "ok": True,
                "text": "Floating P&L is unchanged because there are no open broker positions.",
                "provider": "claude",
                "provider_label": "Claude (stub)",
                "paid": True,
            }

    provider = _Provider()
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    model_provider.set_model_provider_for_tests(provider)
    try:
        op = ai_operator.AIOperator(actions_path=tmp_path / "actions.jsonl")
        reply = op.chat("why hasn't the floating P&L changed in 24 hours?")
        assert reply["ok"] is True
        assert reply["model_ok"] is True
        assert reply["fallback"] is False
        assert reply["chat_path_status"] == "MODEL_PRIMARY"
        assert reply["response_source"] == "MODEL"
        assert "no open broker positions" in reply["reply"]
        assert provider.called is True
        assert "OWNER'S MESSAGE" in provider.prompt
    finally:
        model_provider.set_model_provider_for_tests(None)
        set_authority_for_tests(None)
