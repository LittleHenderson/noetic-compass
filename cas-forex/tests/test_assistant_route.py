from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from api.routes import assistant


class _FakeBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class _FakeMessages:
    def __init__(self, text: str):
        self._text = text
        self.last_system = ""

    def create(self, **kwargs):
        self.last_system = kwargs.get("system", "")
        return SimpleNamespace(content=[_FakeBlock(self._text)])


class _FakeAnthropic:
    def __init__(self, messages: _FakeMessages):
        self._messages = messages

    def Anthropic(self, api_key: str):
        return SimpleNamespace(messages=self._messages)


@pytest.fixture(autouse=True)
def _no_default_spec_context(monkeypatch):
    import cas_forex.spec_context as spec_context

    monkeypatch.setattr(spec_context, "assistant_spec_context", lambda: "")
    monkeypatch.setattr(assistant, "_assistant_active_local_model_provider", lambda: None)
    monkeypatch.setattr(assistant, "_assistant_active_shared_model_provider", lambda: None)


def test_assistant_chat_returns_command_preview(monkeypatch):
    text = (
        "Yes, I can preview that change.\n"
        "```command\n"
        '{"command": "set_ai_dial", "params": {"lever": "edge_threshold", "value": 0.7}}\n'
        "```"
    )
    fake_messages = _FakeMessages(text)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropic(fake_messages))

    res = asyncio.run(assistant.assistant_chat(assistant.ChatRequest(message="raise edge threshold", history=[])))

    assert res["source"] == "ai"
    assert res["proposed_command"]["command"] == "set_ai_dial"
    assert res["command_preview"]["ready"] is True
    assert res["command_preview"]["confirm_phrase"]
    assert "```" not in res["reply"]
    assert "COMMAND_CATALOG" in fake_messages.last_system


def test_assistant_system_prompt_includes_full_spec_context(monkeypatch):
    text = "The tracker is part of the current spec."
    fake_messages = _FakeMessages(text)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropic(fake_messages))

    import cas_forex.spec_context as spec_context

    monkeypatch.setattr(
        spec_context,
        "assistant_spec_context",
        lambda: (
            "SPEC_CONTEXT_FULL_READ_ONLY\n"
            "Product Requirements: human insight through chat\n"
            "Tracker page: proof, money, markets, phone, and gates"
        ),
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="summarize the current spec context for the tracker page", history=[])
        )
    )

    assert res["source"] == "ai"
    assert "SPEC_CONTEXT_FULL_READ_ONLY" in fake_messages.last_system
    assert "Product Requirements: human insight through chat" in fake_messages.last_system
    assert "Tracker page: proof, money, markets, phone, and gates" in fake_messages.last_system


def test_assistant_system_prompt_includes_public_launch_gate_truth(monkeypatch):
    text = "Public launch is blocked by legal review."
    fake_messages = _FakeMessages(text)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropic(fake_messages))

    import cas_forex.public_launch_gate as public_launch_gate

    monkeypatch.setattr(
        public_launch_gate,
        "build_public_launch_gate",
        lambda: {
            "launch_gate_status": "BLOCK_PUBLIC_LAUNCH",
            "public_launch_status": "BLOCKED",
            "live_money_production_status": "BLOCKED",
            "pass_count": 4,
            "block_count": 4,
            "hard_blockers": ["Counsel legal review is missing."],
            "release_policy": "Treat BLOCK_PUBLIC_LAUNCH as a hard stop.",
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="write a short QA note about the release policy and blockers", history=[])
        )
    )

    assert res["source"] == "ai"
    assert "REQUESTED PUBLIC-LAUNCH EVIDENCE" in fake_messages.last_system
    assert '"launch_gate_status": "BLOCK_PUBLIC_LAUNCH"' in fake_messages.last_system
    assert '"public_launch_status": "BLOCKED"' in fake_messages.last_system
    assert '"live_money_production_status": "BLOCKED"' in fake_messages.last_system
    assert "Counsel legal review is missing." in fake_messages.last_system


def test_assistant_system_prompt_includes_mobile_readiness_truth(monkeypatch):
    text = "The phone package is ready, but phone verification is still pending."
    fake_messages = _FakeMessages(text)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropic(fake_messages))

    import cas_forex.mobile_readiness_latest as mobile_latest
    import cas_forex.mobile_final_verification as final_verification
    import cas_forex.mobile_proof_session as proof_session
    import cas_forex.mobile_verification_plan as verification_plan
    import cas_forex.phone_verification_session as phone_session

    monkeypatch.setattr(
        mobile_latest,
        "latest_mobile_readiness_report",
        lambda: {
            "package_ready_for_phone_install": True,
            "phone_browser_observed": True,
            "phone_browser_verified": False,
            "phone_proof_fresh": False,
            "phone_proof_age_seconds": 90100,
            "phone_proof_expires_at": "2026-07-05T00:00:00+00:00",
            "phone_observation_fresh": True,
            "phone_observation_age_seconds": 18,
            "phone_observation_expires_at": "2026-07-06T00:00:00+00:00",
            "apk_runtime_status": "local_only",
            "apk_runtime_observed": True,
            "apk_runtime_verified": False,
            "apk_runtime_fresh": True,
            "apk_install_pairing_verified": False,
            "apk_install_pairing_attempt_status": "install_failed",
            "apk_install_pairing_attempt_fresh": True,
            "apk_install_pairing_attempt_message": "No ready Android device is attached.",
            "android_release_signing_ready": False,
            "android_release_signing_status": "missing_config",
            "android_release_signing_detail": "Android release signing is missing: storeFile.",
            "android_release_apk_exists": False,
            "android_device_ready": False,
            "android_device_count": 0,
            "android_device_ready_count": 0,
            "android_device_detail": "No ready Android device is attached.",
            "docker_available": False,
            "docker_engine_status": "external",
            "docker_engine_detail": "Docker CLI not found on PATH.",
            "docker_server_version": None,
            "docker_wsl_checked": True,
            "docker_desktop_elevated_install_command": "npm --prefix ui run mobile:docker-install-elevated",
            "docker_desktop_install_attempt_status": "admin_elevation_required",
            "web_base": "http://10.0.0.6:4173",
            "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
            "verification_commands": {
                "phone_proof_watcher": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                "phone_verification_session": "npm --prefix ui run mobile:verify-session",
                "mobile_proof_session": "npm --prefix ui run mobile:proof-session",
                "mobile_readiness": "npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173",
                "mobile_stack": "npm --prefix ui run mobile:stack -- --web-base http://10.0.0.6:4173",
                "release_bundle": "python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --exit-code-on-failure",
                "apk_debug_build": "npm --prefix ui run mobile:apk:debug",
                "apk_release_build": "npm --prefix ui run mobile:apk:release",
                "apk_device_list": "npm --prefix ui run mobile:apk:devices",
                "apk_install_pair": "npm --prefix ui run mobile:apk:install-pair",
                "apk_wait_install_pair": "npm --prefix ui run mobile:apk:wait-install-pair",
                "docker_engine_diagnose": "npm --prefix ui run mobile:docker-check",
                "docker_desktop_install": "npm --prefix ui run mobile:docker-install",
                "docker_desktop_install_elevated": "npm --prefix ui run mobile:docker-install-elevated",
                "docker_engine_check": 'docker version --format "{{.Server.Version}}"',
                "docker_compose_build": "docker compose build",
            },
            "next_verification_actions": [
                {
                    "action_id": "phone_browser_proof",
                    "title": "Verify real phone Quick Start",
                    "detail": "Open the URL from the phone.",
                    "command": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                    "target_url": "http://10.0.0.6:4173/?page=quick-start",
                    "secondary_commands": ["npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173"],
                    "blocks_completion": True,
                }
            ],
            "remaining_external_gates": [
                "Open Quick Start from a real phone over the LAN preview.",
                "Attach an Android phone and run npm --prefix ui run mobile:apk:wait-install-pair.",
            ],
        },
    )
    monkeypatch.setattr(proof_session, "build_mobile_proof_session", lambda: "proof-session")
    monkeypatch.setattr(
        proof_session,
        "mobile_proof_session_to_dict",
        lambda session: {  # noqa: ARG005
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external proof gate(s) remain.",
            "package_ready_for_phone_install": True,
            "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
            "phone_proof_target_url": "http://10.0.0.6:4173/?page=quick-start",
            "phone_proof_target_kind": "quick_start_with_live_pairing_if_needed",
            "phone_pairing_handoff": "Use the live desktop Quick Start or Owner Access controls for a copyable pairing QR/link.",
            "pairing_context": {
                "redacted_pairing_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=REDACTED",
                "redacted_native_pairing_url": "casforex://pair?cas_owner_token=REDACTED",
            },
            "gates": [
                {"title": "Real phone Quick Start proof", "satisfied": False},
                {"title": "Android APK install and native pairing proof", "satisfied": False},
                {"title": "Docker Engine proof", "satisfied": False},
            ],
            "owner_commands": {
                "mobile_proof_session": "npm --prefix ui run mobile:proof-session",
                "docker_desktop_install_elevated": "npm --prefix ui run mobile:docker-install-elevated",
            },
        },
    )
    monkeypatch.setattr(
        phone_session,
        "build_phone_verification_session",
        lambda: {
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external verification gate(s) remain.",
            "pairing_context": {
                "pwa_api_base": "http://10.0.0.6:4173/api/forex",
                "direct_api_base": "http://10.0.0.6:8765/api/forex",
                "redacted_pairing_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=REDACTED",
                "redacted_native_pairing_url": "casforex://pair?cas_owner_token=REDACTED",
            },
            "release_artifact_summary": {
                "all_required_present": True,
                "android_debug_apk_sha256": "apk-sha",
                "web_index_sha256": "index-sha",
                "service_worker_sha256": "sw-sha",
            },
            "phone_verification_steps": ["Open Owner Access.", "Open Quick Start from phone."],
        },
    )
    monkeypatch.setattr(
        verification_plan,
        "build_mobile_verification_plan",
        lambda: {
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external verification gate(s) remain.",
            "text": (
                "CAS Forex mobile/web verification plan\n"
                "Status: external_proof_pending\n"
                "Docker elevated install: npm --prefix ui run mobile:docker-install-elevated"
            ),
            "owner_commands": {"mobile_verification_plan": "npm --prefix ui run mobile:verification-plan"},
            "next_verification_actions": [{"title": "Verify real phone Quick Start"}],
        },
    )
    monkeypatch.setattr(final_verification, "build_mobile_final_verification", lambda: "final-verification")
    monkeypatch.setattr(
        final_verification,
        "mobile_final_verification_to_dict",
        lambda report: {  # noqa: ARG005
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 2 final external gate(s) remain.",
            "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
            "phone_browser_verified": False,
            "apk_install_pairing_verified": False,
            "docker_available": True,
            "next_owner_step": (
                "Open http://10.0.0.6:4173/?page=quick-start on the real phone, then run "
                "`npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing`."
            ),
            "gates": [
                {"title": "Real phone Quick Start proof", "satisfied": False},
                {"title": "Android APK install and native pairing proof", "satisfied": False},
                {"title": "Docker Engine proof", "satisfied": True},
            ],
            "owner_commands": {
                "mobile_final_verification": "npm --prefix ui run mobile:finish",
                "mobile_final_verification_watch": "npm --prefix ui run mobile:finish -- --watch-phone",
                "mobile_final_verification_watch_all": "npm --prefix ui run mobile:finish -- --watch-all",
                "mobile_final_verification_watch_all_live_links": "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links",
            },
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="summarize the phone proof-session commands for my install notes", history=[])
        )
    )

    assert res["source"] == "ai"
    assert "Phone/Web Readiness Evidence" in fake_messages.last_system
    assert "REQUESTED MOBILE/PHONE EVIDENCE" in fake_messages.last_system
    assert '"package_ready_for_phone_install": true' in fake_messages.last_system
    assert '"phone_browser_verified": false' in fake_messages.last_system
    assert '"apk_runtime_status": "local_only"' in fake_messages.last_system
    assert '"docker_engine_status": "external"' in fake_messages.last_system
    assert "http://10.0.0.6:4173/?page=quick-start" in fake_messages.last_system
    assert "npm --prefix ui run mobile:proof-session" in fake_messages.last_system
    assert "npm --prefix ui run mobile:finish -- --watch-all" in fake_messages.last_system
    assert '"phone_proof_target_kind": "quick_start_with_live_pairing_if_needed"' in fake_messages.last_system
    assert '"pwa_api_base": "http://10.0.0.6:4173/api/forex"' in fake_messages.last_system
    assert '"direct_api_base": "http://10.0.0.6:8765/api/forex"' in fake_messages.last_system
    assert '"android_debug_apk_sha256": "apk-sha"' in fake_messages.last_system
    assert '"all_required_present": true' in fake_messages.last_system
    assert '"verification_step_count": 2' in fake_messages.last_system
    assert "cas_owner_token=REDACTED" not in fake_messages.last_system


def test_assistant_unconfigured_response_has_no_command(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    res = asyncio.run(assistant.assistant_chat(assistant.ChatRequest(message="hello", history=[])))

    assert res["source"] == "unconfigured"
    assert res["proposed_command"] is None
    assert res["command_preview"] is None
    assert "left nav" not in res["reply"]
    assert "phone menu button" in res["reply"]


def test_assistant_unconfigured_tracker_question_uses_local_navigation(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="where is the tracker page on phone?", history=[])
        )
    )

    assert res["source"] == "local"
    assert res["proposed_command"] is None
    assert res["command_preview"] is None
    assert "Tracker is a real page." in res["reply"]
    assert "tap the menu button near the top" in res["reply"]


def test_assistant_treats_open_compound_trades_as_trading_question(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import cas_forex.dispatch_loop as dispatch_loop

    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_management_status": "WATCHING_NO_ACTION",
            "last_scale_in_status": "NO_SCALE_IN_CANDIDATE",
            "last_scale_in_action_count": 0,
            "last_scale_in_blockers": [
                {
                    "symbol": "NAS100",
                    "parent_broker_ticket": "45944857",
                    "reason": "per-symbol position cap is already full (1 / 1)",
                }
            ],
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message=(
                    "do you think you should open compound trades to increase profits "
                    "faster since we know the current trades are winning?"
                ),
                history=[],
            )
        )
    )

    assert res["source"] == "local"
    assert "Operator is allowed to compound" in res["reply"]
    assert "dispatch running=True, lane=PAPER" in res["reply"]
    assert "status=NO_SCALE_IN_CANDIDATE" in res["reply"]
    assert "per-symbol position cap is already full (1 / 1)" in res["reply"]
    assert "Trade is a real top-bar page" not in res["reply"]


def test_assistant_answers_active_account_from_shared_runtime_truth(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import api.data as api_data
    import cas_forex.ai_operator as ai_operator

    monkeypatch.setattr(
        ai_operator,
        "_profit_and_balance",
        lambda: {
            "scope": "PAPER_SIMULATOR_PERFORMANCE",
            "honest_paper_balance_usd": 3040.87,
            "balance_growth_net_pnl_usd": 1040.87,
        },
    )
    monkeypatch.setattr(
        api_data,
        "active_account_truth",
        lambda: {
            "status": "PRIMARY_MT5_DEMO_ACCOUNT_ACTIVE",
            "objective_account_established": True,
            "authoritative_account_source": "mt5_account_snapshot",
            "account": {
                "login": 1000694,
                "server": "Hugosway-Demo",
                "is_demo": True,
                "balance_usd": 45080.90,
                "equity_usd": 45110.36,
            },
            "open_exposure": {"open_position_count": 6},
            "snapshot": {
                "observed_at": "2026-07-14T19:00:34+00:00",
                "age_seconds": 1.2,
                "fresh": True,
            },
            "growth_measurement": {
                "cashflow_adjusted_realized_growth_usd": -54919.10,
                "realized_today_usd": 39.41,
                "realized_month_usd": -54918.97,
                "net_external_capital_flow_usd": 100000.0,
                "account_growth_reconciliation": {"reconciled": True},
                "open_pnl_decomposition": {
                    "price_pnl_usd": 32.71,
                    "swap_or_carry_usd": -3.25,
                    "commission_usd": 0.0,
                    "account_net_open_pnl_usd": 29.46,
                    "unattributed_open_pnl_usd": 0.0,
                },
            },
            "secondary_simulator": {
                "scope": "SEPARATE_PAPER_SIMULATOR_EVIDENCE",
                "account": {"balance_usd": 5000.0},
            },
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message="What is our current account balance, P&L, and realized growth?",
                history=[],
            )
        )
    )

    assert res["source"] == "local"
    assert "MT5 demo #1000694 on Hugosway-Demo" in res["reply"]
    assert "Net open P&L after reported costs +$29.46" in res["reply"]
    assert "all time -$54,919.10" in res["reply"]
    assert "Neither is added to the active MT5 account" in res["reply"]
    assert res["proposed_command"] is None


def test_assistant_prioritizes_account_truth_over_short_generic_context_budget(monkeypatch):
    import time

    monkeypatch.setattr(assistant, "ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS", 0.001)
    monkeypatch.setattr(
        assistant,
        "ASSISTANT_ACCOUNT_TRUTH_RESPONSE_BUDGET_SECONDS",
        0.2,
    )

    def delayed_account_truth(_question):
        time.sleep(0.02)
        return "Current active execution account: authoritative delayed truth."

    monkeypatch.setattr(
        assistant,
        "_assistant_local_active_account_truth_reply",
        delayed_account_truth,
    )
    monkeypatch.setattr(
        assistant,
        "_assistant_local_reply",
        lambda _question: (_ for _ in ()).throw(AssertionError("generic route ran")),
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message="What is our current account balance, P&L, and realized growth?",
                history=[],
            )
        )
    )

    assert res["source"] == "local"
    assert res["model"] == "local-runtime-truth"
    assert "authoritative delayed truth" in res["reply"]
    assert res["proposed_command"] is None


def test_assistant_current_strategy_comparison_refuses_to_invent_regime(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import cas_forex.dispatch_loop as dispatch_loop

    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "running": True,
            "execution_lane": "PAPER",
            "last_entry_timeframe": "M15",
            "last_entry_lane": "INTRADAY",
            "last_entry_risk_operator_candidate_count": 0,
            "last_filtered_intent_count": 0,
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message=(
                    "Compare mean reversion and trend continuation for the current "
                    "PAPER lane without proposing a command."
                ),
                history=[],
            )
        )
    )

    assert res["source"] == "local"
    assert "lane=PAPER, timeframe=M15, entry lane=INTRADAY" in res["reply"]
    assert "does not contain a validated current regime classification" in res["reply"]
    assert "cannot truthfully claim" in res["reply"]
    assert "No command or order ran" in res["reply"]


def test_assistant_local_current_state_answer_does_not_claim_model_start_failure(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        assistant,
        "_assistant_local_status_reply",
        lambda _question: (
            "I received your message. This current-state question is answered "
            "directly from the local CAS runtime so it does not wait for the model."
        ),
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="What is the current account state?", history=[])
        )
    )

    assert res["source"] == "local"
    assert "directly from the local CAS runtime" in res["reply"]
    assert "model path could not be started" not in res["reply"].lower()


def test_assistant_model_outage_question_returns_fast_local_truth(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.model_provider as model_provider

    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {"running": True, "execution_lane": "PAPER"},
    )
    monkeypatch.setattr(
        model_provider.get_model_provider(),
        "status",
        lambda: {
            "active_provider": "local-fallback",
            "active_provider_label": "Local model (llama3.1:70b-instruct)",
            "active_is_paid": False,
            "budget_remaining": 0,
            "budget_capped": True,
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="Neither AI system is responding", history=[])
        )
    )

    assert res["source"] == "local"
    assert "Both free-form chat paths are configured" in res["reply"]
    assert "Local model (llama3.1:70b-instruct)" in res["reply"]
    assert "running=True in lane=PAPER" in res["reply"]
    assert "Claude budget is exhausted" in res["reply"]
    assert res["proposed_command"] is None


def test_assistant_model_call_has_bounded_response_time(monkeypatch):
    class _SlowMessages:
        def create(self, **_kwargs):
            import time

            time.sleep(0.2)
            return SimpleNamespace(content=[_FakeBlock("too late")])

    class _SlowAnthropic:
        def Anthropic(self, **_kwargs):
            return SimpleNamespace(messages=_SlowMessages())

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _SlowAnthropic())
    monkeypatch.setattr(assistant, "ASSISTANT_MODEL_RESPONSE_BUDGET_SECONDS", 0.01)

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="Explain an unfamiliar strategy concept", history=[])
        )
    )

    assert res["source"] == "error"
    assert "model request failed (TimeoutError)" in res["reply"]
    assert "No command, order, or dial change ran" in res["reply"]


def test_assistant_uses_selected_local_model_without_anthropic_key(monkeypatch):
    class _LocalProvider:
        def __init__(self):
            self.last_prompt = ""
            self.last_system = ""

        def status(self):
            return {
                "active_provider": "local-fallback",
                "active_provider_label": "Local model (deepseek-r1:latest)",
                "active_is_paid": False,
            }

        def generate(self, prompt, system, **kwargs):
            self.last_prompt = prompt
            self.last_system = system
            assert kwargs["request_kind"] == "assistant_chat"
            assert kwargs["request_timeout"] == assistant.ASSISTANT_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS
            assert kwargs["max_attempts"] == 1
            assert kwargs["max_output_tokens"] == 512
            return {
                "ok": True,
                "text": "Mean reversion expects return toward an average; trend continuation follows momentum.",
                "provider": "local-fallback",
                "provider_label": "Local model (deepseek-r1:latest)",
                "model_ref": "deepseek-r1:latest",
            }

    provider = _LocalProvider()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(assistant, "_assistant_active_shared_model_provider", lambda: provider)
    monkeypatch.setattr(assistant, "_assistant_local_reply", lambda _question: None)

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message="Compare mean reversion with trend continuation.",
                history=[],
            )
        )
    )

    assert res["source"] == "ai-local"
    assert res["model"] == "deepseek-r1:latest"
    assert "Mean reversion expects" in res["reply"]
    assert "USER: Compare mean reversion" in provider.last_prompt
    assert "CURRENT LIVE STATE" in provider.last_system


def test_assistant_and_operator_share_deepseek_flash_provider(monkeypatch):
    class _DeepSeekProvider:
        def __init__(self):
            self.kwargs = {}

        @staticmethod
        def status():
            return {
                "active_provider": "deepseek-flash",
                "active_provider_label": "DeepSeek V4 Flash (DeepSeek API)",
                "active_is_paid": True,
                "provider_reachability": "NOT_PROBED",
            }

        def generate(self, prompt, system, **kwargs):  # noqa: ARG002
            self.kwargs = dict(kwargs)
            return {
                "ok": True,
                "text": "Flash is handling the continuous CAS reasoning lane.",
                "provider": "deepseek-flash",
                "provider_label": "DeepSeek V4 Flash (DeepSeek API)",
                "model_ref": "deepseek-v4-flash",
                "paid": True,
            }

    provider = _DeepSeekProvider()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        assistant,
        "_assistant_active_shared_model_provider",
        lambda: provider,
    )
    monkeypatch.setattr(assistant, "_assistant_local_reply", lambda _question: None)

    response = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message="Explain the active model routing.",
                history=[],
            )
        )
    )

    assert response["source"] == "ai-provider"
    assert response["model"] == "deepseek-v4-flash"
    assert response["reply"].startswith("Flash is handling")
    assert provider.kwargs["request_kind"] == "assistant_chat"
    assert provider.kwargs["max_attempts"] == 1


def test_assistant_context_timeout_does_not_block_event_loop(monkeypatch):
    import time

    fake_messages = _FakeMessages("I can still answer.")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropic(fake_messages))
    monkeypatch.setattr(assistant, "_assistant_local_reply", lambda _question: None)
    monkeypatch.setattr(
        assistant,
        "_assistant_fast_model_state_block",
        lambda: (time.sleep(0.2), "too late")[1],
    )
    monkeypatch.setattr(assistant, "_assistant_model_spec_context_block", lambda: "")
    monkeypatch.setattr(assistant, "_command_catalog_block", lambda: "COMMAND_CATALOG: test")
    monkeypatch.setattr(assistant, "ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS", 0.01)

    async def exercise() -> tuple[dict, float]:
        started = time.perf_counter()
        chat = asyncio.create_task(
            assistant.assistant_chat(
                assistant.ChatRequest(message="Explain an unfamiliar regime concept", history=[])
            )
        )
        await asyncio.sleep(0.03)
        heartbeat_delay = time.perf_counter() - started
        return await chat, heartbeat_delay

    res, heartbeat_delay = asyncio.run(exercise())

    assert heartbeat_delay < 0.1
    assert res["source"] == "ai"
    assert res["reply"] == "I can still answer."
    assert "CURRENT LIVE STATE: unavailable within the 0.01-second chat context budget" in fake_messages.last_system


def test_fast_model_state_block_exposes_entry_and_management_truth(monkeypatch):
    import cas_forex.dispatch_loop as dispatch_loop
    import cas_forex.model_provider as model_provider

    monkeypatch.setattr(
        dispatch_loop,
        "loop_status_fast",
        lambda: {
            "status": "RUNNING",
            "running": True,
            "desired_running": True,
            "execution_active": True,
            "requested_mode": "LIVE",
            "mode": "PAPER_FALLBACK",
            "execution_lane": "PAPER",
            "last_bridge_class": "MT5Bridge",
            "last_bridge_selection_status": "PAPER_MT5_ORDER_SEND_READY",
            "last_run_iso": "2026-07-14T07:00:00+00:00",
            "cycles_run": 41,
            "management_cycles_run": 41,
            "last_management_status": "WATCHING_NO_BROKER_POSITIONS",
            "last_management_account_position_count": 0,
            "last_entry_timeframe": "M5",
            "last_entry_lane": "MICRO_SCALP",
            "last_entry_risk_operator_candidate_count": 0,
            "last_filtered_intent_count": 0,
            "last_scale_in_status": "NO_SCALE_IN_CANDIDATE",
            "last_summary": "lane=PAPER entry_timeframe=M5 operator_candidates=0 intents=0",
            "last_error": None,
        },
    )
    monkeypatch.setattr(
        model_provider.get_model_provider(),
        "status",
        lambda: {
            "active_provider": "local-fallback",
            "active_provider_label": "Local model (deepseek-r1:latest)",
            "last_ok": True,
            "budget_remaining": 0,
        },
    )

    block = assistant._assistant_fast_model_state_block()

    assert "status=RUNNING" in block
    assert "mode=PAPER_FALLBACK, lane=PAPER" in block
    assert "bridge=MT5Bridge" in block
    assert "management=WATCHING_NO_BROKER_POSITIONS" in block
    assert "selected_timeframe=M5, entry_lane=MICRO_SCALP" in block
    assert "entry=ai_operator_trade_edge.v11" in block
    assert "provider=local-fallback" in block


def test_assistant_educational_profit_question_uses_model(monkeypatch):
    fake_messages = _FakeMessages("Floating profit is open; realized profit is closed.")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _FakeAnthropic(fake_messages))
    monkeypatch.setattr(assistant, "_assistant_fast_model_state_block", lambda: "")
    monkeypatch.setattr(assistant, "_spec_context_block", lambda: "")
    monkeypatch.setattr(assistant, "_command_catalog_block", lambda: "")

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(
                message="Explain the difference between floating and realized profit.",
                history=[],
            )
        )
    )

    assert res["source"] == "ai"
    assert res["reply"] == "Floating profit is open; realized profit is closed."


def test_assistant_status_question_uses_local_readiness_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import cas_forex.ai_operator as ai_operator

    monkeypatch.setattr(
        ai_operator,
        "gather_chat_context",
        lambda: {
            "professional_readiness": {
                "available": True,
                "status": "ATTENTION",
                "item_count": 37,
                "ok_count": 34,
                "partial_count": 3,
                "gap_count": 0,
                "satisfied_count": 34,
                "internal_partial_count": 0,
                "external_blocked_count": 3,
                "missing_count": 0,
                "top_attention_items": [
                    "Obtain legal/compliance review before public launch or advising others for compensation.",
                ],
                "remaining_rows": [
                    {
                        "item_number": 13,
                        "key": "compliance_awareness",
                        "status": "PARTIAL",
                        "completion_state": "EXTERNAL_BLOCKED",
                        "blocked_by_external_dependency": True,
                        "external_dependency": "Qualified legal/compliance review and accepted counsel record.",
                        "next_action": "Obtain legal/compliance review before public launch or advising others for compensation.",
                    },
                    {
                        "item_number": 32,
                        "key": "legal_disclosures",
                        "status": "PARTIAL",
                        "completion_state": "EXTERNAL_BLOCKED",
                        "blocked_by_external_dependency": True,
                        "external_dependency": "Counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures.",
                        "next_action": "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
                    },
                    {
                        "item_number": 34,
                        "key": "production_operations",
                        "status": "PARTIAL",
                        "completion_state": "EXTERNAL_BLOCKED",
                        "blocked_by_external_dependency": True,
                        "external_dependency": "Hosted uptime monitor and error-tracking DSN configured in the deployment environment.",
                        "next_action": "Add external uptime/error monitoring before public cloud deployment.",
                    },
                ],
            }
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="what remains from the 37-item checklist?", history=[])
        )
    )

    assert res["source"] == "local"
    assert res["proposed_command"] is None
    assert res["command_preview"] is None
    assert "Professional readiness matrix: status=ATTENTION, ok=34/37, partial=3, gaps=0." in res["reply"]
    assert "Completion states: satisfied=34, internal_partial=0, external_blocked=3, missing=0." in res["reply"]
    assert "External blockers: #13 Qualified legal/compliance review and accepted counsel record." in res["reply"]
    assert "#13 compliance_awareness=PARTIAL" in res["reply"]


def test_assistant_general_health_question_stays_local_even_when_api_key_exists(monkeypatch):
    class _ExplodingAnthropic:
        def Anthropic(self, api_key: str):  # noqa: ARG002
            raise AssertionError("assistant should not call Anthropic for local-first status questions")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _ExplodingAnthropic())

    import cas_forex.ai_operator as ai_operator

    monkeypatch.setattr(ai_operator, "gather_chat_context", lambda: {})
    monkeypatch.setattr(
        ai_operator,
        "_operator_briefing_context",
        lambda: {
            "available": True,
            "loop_health_status": "running",
            "decisions_today": 5,
            "executions_today": 1,
            "blocked_today": 2,
            "open_position_count": 2,
            "total_floating_pnl": 15.0,
            "mt5_terminal_connected": True,
            "readiness_gates_open": 3,
            "readiness_gates_total": 5,
            "diagnostic_hints": ["MT5 broker verification is not current."],
        },
    )
    monkeypatch.setattr(
        ai_operator,
        "_stack_health_context",
        lambda briefing=None: {  # noqa: ARG005
            "available": True,
            "overall_status": "DEGRADED",
            "ok_count": 4,
            "degraded_count": 1,
            "missing_count": 1,
            "unknown_count": 0,
            "checks": [
                {"name": "uvicorn-api", "status": "OK"},
                {"name": "mt5-terminal", "status": "DEGRADED"},
            ],
            "next_actions": ["Connect MT5 terminal API verification."],
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="is everything working correctly?", history=[])
        )
    )

    assert res["source"] == "local"
    assert "System health: overall=DEGRADED" in res["reply"]
    assert "Operator briefing: loop=running" in res["reply"]


def test_live_state_block_includes_operator_briefing_source_truth(monkeypatch):
    import cas_forex.ai_operator as ai_operator

    monkeypatch.setattr(
        ai_operator,
        "_operator_briefing_context",
        lambda: {
            "available": True,
            "loop_health_status": "running",
            "open_position_count": 2,
            "total_floating_pnl": 0.0,
            "live_position_feed_label": "SIM PROOF",
            "live_telemetry_source": "movement_stream",
            "live_price_source_status": "STATIC_SIMULATION_FALLBACK",
            "live_telemetry_stale": False,
            "live_telemetry_last_update_iso": "2026-07-09T12:00:00+00:00",
            "live_position_feed_detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. Static simulator fallback is active for 2/2 row(s), so prices and floating P&L can remain at entry until usable provider or MT5 quotes arrive.",
            "broker_truth_monitor_status": "BROKER_TRUTH_RECONCILIATION_FAILED",
            "broker_truth_ready_for_live": False,
            "broker_truth_paper_force_latched": True,
            "broker_truth_halt_reason_summary": "Stop-Loss Protection, Terminal Reconciliation",
            "broker_truth_position_protection_label": "UNPROTECTED POSITIONS",
            "broker_truth_unprotected_position_count": 2,
            "broker_truth_position_protection_detail": "2 broker-visible live positions have no stop-loss protection.",
            "broker_truth_mt5_connected": True,
            "broker_truth_mt5_is_demo": False,
            "broker_truth_open_position_count": 2,
        },
    )

    block = assistant._live_state_block()

    assert "position_feed=SIM PROOF" in block
    assert "telemetry_source=movement_stream" in block
    assert "price_source_status=STATIC_SIMULATION_FALLBACK" in block
    assert "operator position feed detail: Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions." in block
    assert "broker truth briefing:" in block
    assert "status=BROKER_TRUTH_RECONCILIATION_FAILED" in block
    assert "paper_force_latched=true" in block
    assert "halt_reasons=Stop-Loss Protection, Terminal Reconciliation" in block
    assert "position_protection=UNPROTECTED POSITIONS" in block
    assert "unprotected_positions=2" in block
    assert "broker truth protection detail: 2 broker-visible live positions have no stop-loss protection." in block


def test_live_state_block_prefers_nested_operator_movement_truth(monkeypatch):
    import cas_forex.ai_operator as ai_operator

    monkeypatch.setattr(
        ai_operator,
        "_operator_briefing_context",
        lambda: {
            "available": True,
            "loop_health_status": "running",
            "open_position_count": 2,
            "total_floating_pnl": 0.0,
            "live_position_feed_label": "WRONG",
            "live_telemetry_source": "wrong_source",
            "live_price_source_status": "WRONG_STATUS",
            "live_telemetry_stale": True,
            "live_telemetry_last_update_iso": "wrong-update",
            "live_position_feed_detail": "wrong detail",
            "live_movement_source_truth": {
                "position_feed_label": "SIM PROOF",
                "telemetry_source": "movement_stream",
                "price_source_status": "STATIC_SIMULATION_FALLBACK",
                "telemetry_stale": False,
                "telemetry_last_update_iso": "2026-07-09T12:00:00+00:00",
                "position_feed_detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions.",
                "detail": "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions.",
            },
        },
    )

    block = assistant._live_state_block()

    assert "position_feed=SIM PROOF" in block
    assert "telemetry_source=movement_stream" in block
    assert "price_source_status=STATIC_SIMULATION_FALLBACK" in block
    assert "telemetry_stale=false" in block
    assert "last_update=2026-07-09T12:00:00+00:00" in block
    assert "wrong_source" not in block
    assert "WRONG_STATUS" not in block


def test_assistant_navigation_question_falls_back_locally_when_model_errors(monkeypatch):
    class _ExplodingAnthropic:
        def Anthropic(self, api_key: str):  # noqa: ARG002
            raise RuntimeError("boom")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", _ExplodingAnthropic())

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="where do I change the phone API address?", history=[])
        )
    )

    assert res["source"] == "local"
    assert "Settings > Phone / APK Connection" in res["reply"]


def test_assistant_startup_question_uses_local_mobile_readiness_guidance(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import cas_forex.mobile_readiness_latest as mobile_latest

    monkeypatch.setattr(
        mobile_latest,
        "latest_mobile_readiness_report",
        lambda: {
            "web_base": "http://10.0.0.6:4173",
            "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
            "verification_commands": {
                "mobile_stack": "npm --prefix ui run mobile:stack -- --web-base http://10.0.0.6:4173",
                "phone_proof_watcher": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                "mobile_proof_session": "npm --prefix ui run mobile:proof-session",
                "phone_verification_session": "npm --prefix ui run mobile:verify-session",
            },
        },
    )

    res = asyncio.run(
        assistant.assistant_chat(
            assistant.ChatRequest(message="how do I start the app on my laptop and phone step by step?", history=[])
        )
    )

    assert res["source"] == "local"
    assert "npm --prefix ui run mobile:stack -- --web-base http://10.0.0.6:4173" in res["reply"]
    assert "http://10.0.0.6:4173/?page=quick-start" in res["reply"]
    assert "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing" in res["reply"]
    assert "npm --prefix ui run mobile:proof-session" in res["reply"]


def test_assistant_status_reports_latest_local_model_failure(monkeypatch):
    class _FailedLocalProvider:
        @staticmethod
        def status():
            return {
                "active_provider_label": "Local model (deepseek-r1:latest)",
                "provider_reachability": "FAILED",
                "provider_last_error": (
                    "AI backend call failed: HTTP 500: model requires more system memory"
                ),
                "provider_last_attempt_at": "2026-07-14T22:00:00+00:00",
                "provider_health_age_seconds": 3,
            }

    monkeypatch.setattr(
        assistant,
        "_assistant_active_shared_model_provider",
        lambda: _FailedLocalProvider(),
    )

    status = asyncio.run(assistant.assistant_status())

    assert status["configured"] is True
    assert status["provider_reachability"] == "FAILED"
    assert "requires more system memory" in status["provider_last_error"]
    assert "Configuration alone is not being reported as readiness" in status["detail"]
