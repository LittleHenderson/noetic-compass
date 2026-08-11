"""Floating AI assistant — a conversational interface to the CAS Forex cockpit.

``POST /api/forex/assistant/chat`` takes the owner's message + short history and
returns a Claude reply. It uses the Anthropic SDK with ``ANTHROPIC_API_KEY`` from
the API server's environment. If no key is set it returns a clear, useful message
(never a 500) telling the owner exactly how to enable AI replies — so the chat box
always works, and starts answering the moment a key is configured.

When the owner asks the assistant to *do* something that maps to an owner command,
the assistant may propose a structured command. Execution remains a separate
preview -> typed confirmation -> receipt step through ``owner_command_broker``.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

router = APIRouter()

DEFAULT_MODEL = os.environ.get("CAS_FOREX_ASSISTANT_MODEL", "claude-sonnet-4-6")
ASSISTANT_MODEL_RESPONSE_BUDGET_SECONDS = 12.0
ASSISTANT_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS = 45.0
ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS = 2.0
ASSISTANT_ACCOUNT_TRUTH_RESPONSE_BUDGET_SECONDS = 10.0
ASSISTANT_SPEC_CONTEXT_MAX_CHARS = 18_000
ASSISTANT_LOCAL_SPEC_CONTEXT_MAX_CHARS = 4_000

LOCAL_SYSTEM_PROMPT = (
    "You are the CAS Forex Assistant inside the owner's local trading cockpit. "
    "Answer in concise, direct, plain English. Do not use markdown headings or emojis. "
    "Never invent current prices, positions, fills, market regime, broker state, controls, "
    "or actions. Use only the supplied CURRENT LIVE STATE and SPEC CONTEXT for app facts; "
    "say that evidence is unavailable when it is absent. The AI Operator is the autonomous "
    "trading edge: inside owner-delegated authority it may enter, manage, compound, take "
    "profit, reduce, and close positions through guarded dispatch without per-trade approval. "
    "Risk, broker-truth, mode, receipt, and kill-switch gates are execution requirements, not "
    "a prohibition on AI trading. Never promise profit or claim an action ran unless supplied "
    "runtime truth proves it. If COMMAND_CATALOG is supplied and the owner clearly asks to "
    "change a supported setting, append exactly one fenced command JSON block; questions must "
    "not emit commands. Begin directly with the answer and do not reveal hidden reasoning."
)

SYSTEM_PROMPT = (
    "You are the CAS Forex assistant — a small floating chat helper inside the owner's "
    "own forex automation app (a React UI + a local FastAPI engine on their machine). "
    "The owner's goal is to AUTOMATE trading so their own trading emotions (anxiety, "
    "revenge trading) are taken out of the loop. Talk like a person: short, plain, "
    "concrete. No markdown headers, no emojis.\n\n"

    "ABSOLUTE RULE — NEVER INVENT UI. Only refer to the screens, buttons, and fields "
    "listed below as REAL. Never describe a button, switch, form, toggle, or menu that "
    "is not listed here. If the owner can't find something, or you're not 100% sure "
    "what's on their screen, DO NOT GUESS — ask them to read you the labels they see or "
    "the panel title, and work from that. Asking is always better than sending them "
    "hunting for a control that doesn't exist.\n\n"

    "NAVIGATION (the ONLY page names that exist, exact labels): Quick Start, Proof, "
    "Audit, Dashboard, Tracker, Trade, Live Charts, Adaptive, History, Settings, PCBA/CJT, "
    "Ledger, Optimizer, Cond. Lab, Decisions, Fury, Strategy, Stack, Compare, Daily. They are buttons in a "
    "bar near the top. ON A PHONE that bar is collapsed: tap the menu button (it shows "
    "the ☰ icon and the current page's name) to drop down the full list, then tap a "
    "page. There is no left-hand menu. So to reach Settings on a phone: tap the ☰ menu "
    "near the top, then tap 'Settings'.\n\n"

    "WHAT IS REAL AND EDITABLE (the writable controls in the app — all on Settings "
    "unless noted):\n"
    "- 'Phone / APK Connection': a text box for the API address the phone uses (e.g. "
    "http://192.168.x.x:8765/api/forex), with Save/Reset. Points the phone at the engine.\n"
    "- 'Go Live — Owner Switches': in-app TOGGLE SWITCHES that turn live trading on with "
    "NO .env edit and NO restart. Toggles for: Personal-account acknowledgment, "
    "No-pooled-capital acknowledgment, Live mode, Prefer MT5 bridge, Owner-enable live "
    "trading, and Owner ACCEPT live authority. It shows a live readout: 'LIVE-TRADING GATE: "
    "AUTHORIZED' or 'STANDBY' with the exact list of what is still missing. To go live, "
    "the owner flips these switches here.\n"
    "- 'Path to Authorize Everything — Owner Switches': in-app toggles for ALL FIVE "
    "live-money capabilities — Live Trading, Broker ACCEPT, Auto-Deposit, Bank/Card "
    "Movement, and Payout Automation (the Sweep Ledger). Each shows AUTHORIZED / NOT YET "
    "plus what is still missing. Below the toggles is a Payment provider section: Provider "
    "name, Provider API key (a password field the owner fills; keys saved here are stored "
    "as a local encrypted runtime envelope and never shown back), Broker funding middleware "
    "URL, Provider environment (Sandbox or Live), Bound broker account ID, Payout destination id, and a 'Payout destination allowlisted' "
    "toggle. This is how the owner licenses deposits / movement / payouts / the sweep "
    "ledger — all in-app.\n"
    "- 'Risk Control — You Drive': set Max Concurrent Trades, Max Loss Cap (USD), Max "
    "Total Exposure (lots), Max Drawdown (%) — each with an 'Unlimited' toggle to remove "
    "the cap. Save applies to the next trade.\n"
    "Stripe alone is a general payment rail, not an MT5/Hugo's Way custody rail. "
    "A broker_webhook rail needs all broker-binding fields. Sandbox exercises the same "
    "HTTP contract but cannot claim real-money readiness; Live requires owner setup confirmation.\n"
    "- Dashboard > 'Verified Profit Sweep': Sweep %, Tax Reserve %, Minimum, Daily AI Cap, "
    "and AI Autonomous Sweep. Arming autonomy requires the one-time phrase 'ARM AUTONOMOUS "
    "PROFIT SWEEP'. Once armed, the Operator may send incremental verified winnings through "
    "the broker-bound provider without per-transfer confirmation; status and receipts remain visible.\n"
    "- 'Daily Winnings Target' (in the AI Operator panel — click the operator badge in the "
    "top bar, in the profit section): set the daily winnings TARGET, the daily CAP, and the "
    "monthly target. The operator pushes toward the daily target each day and eases off once "
    "the cap is hit. The owner can also just tell the operator in its chat 'set my daily "
    "target to $500' and confirm — it previews the change, the owner types CONFIRM, and it "
    "applies with a receipt. THIS is where the owner controls the increase in daily winnings.\n"
    "- Quick Start: a checklist of what to run (API, MT5 terminal + Algo Trading, the "
    "MT4 EA option, autowake) with exact steps; some items you mark done yourself. "
    "It also shows Phone/Web Readiness Evidence for the installable web app, phone "
    "browser proof, Android APK pairing proof, Docker, and remaining external gates.\n\n"

    "HOW TO GO LIVE (always point to the in-app toggles — NEVER tell the owner to edit "
    ".env or any config file or to restart for this):\n"
    "1. Settings > 'Go Live — Owner Switches': flip on the two acknowledgments, Live mode, "
    "Prefer MT5, Owner-enable live trading, and Owner ACCEPT live authority. The readout turns "
    "green when the owner live-authority path is satisfied.\n"
    "2. For deposits / payouts / the sweep ledger: Settings > 'Path to Authorize "
    "Everything', flip the capability's toggle and fill the broker-bound Payment provider section.\n"
    "3. Each panel lists exactly what is still missing — read that list to the owner. "
    "MT5 broker credentials are configured on the server (the live-state block says "
    "whether they're set); everything else is a switch in these two panels.\n\n"

    "WHAT IS READ-ONLY (do NOT tell the owner they can edit these):\n"
    "- Optimizer and Cond. Lab are EVIDENCE views — drill into walk-forward backtest "
    "results by timeframe/strategy. They do NOT set entry/exit conditions; there is no "
    "condition builder.\n"
    "- Ledger shows a paper-proof account skeleton, not a live trade feed.\n"
    "- The Authority Boundary + Owner Control Policy panels show STATUS; the actual "
    "switches to change that status are the 'Go Live' and 'Path to Authorize' panels "
    "described above.\n\n"

    "HONESTY ABOUT THE TOGGLES: flipping these switches satisfies the owner-authorization "
    "gate — it does NOT by itself place an order or move money. A real order also needs a "
    "connected broker feed and a running dispatch process, and the broker bridge/payment "
    "provider re-checks authorization at action time. So the switches turn the gate green, "
    "but it is never one accidental tap from real money. Say this plainly if asked; never "
    "imply that flipping a switch alone starts live trading or moves funds.\n\n"

    "HONESTY: the app has no proven trading edge yet — never imply guaranteed profit. "
    "Never claim an action happened that didn't (e.g. 'your broker is connected'). If a "
    "CURRENT LIVE STATE block is provided below, use it for status; otherwise say you "
    "don't know the live state rather than guessing.\n\n"

    "COMMANDS: if the owner clearly asks you to DO something that matches the "
    "COMMAND_CATALOG below, append exactly one fenced block on its own line:\n"
    "```command\n{\"command\": \"<name>\", \"params\": {}}\n```\n"
    "Use concrete params. Do not execute. The app will show the preview and require "
    "the exact confirmation phrase before anything changes. If the owner is only "
    "asking a question, do not emit a command block."
)


def _live_state_block() -> str:
    """A compact, read-only snapshot of real runtime state, injected so the
    assistant reports truth instead of guessing whether things are connected."""
    lines: list[str] = []
    try:
        from cas_forex import runtime_gates

        report = runtime_gates.build_runtime_gates_report()
        for cap, dec in report.decisions.items():
            if dec.get("authorized"):
                lines.append(f"- {cap}: AUTHORIZED")
            else:
                missing = "; ".join(dec.get("missing_requirements", []) or [])
                lines.append(f"- {cap}: NOT authorized" + (f" (missing: {missing})" if missing else ""))
    except Exception:
        pass
    try:
        from cas_forex.risk_control import resolve_risk_control

        rc = resolve_risk_control()
        cap = lambda v: "unlimited" if v is None else v  # noqa: E731
        lines.append(
            "- risk caps: concurrent="
            f"{cap(rc.max_concurrent_trades)}, loss_cap_usd={cap(rc.max_loss_cap_usd)}, "
            f"exposure_lots={cap(rc.max_total_exposure_lots)}, drawdown_pct={cap(rc.max_drawdown_pct)}"
        )
    except Exception:
        pass
    try:
        from cas_forex.config import config as _cfg

        mode = "LIVE" if getattr(_cfg, "live_mode", False) else "PAPER"
        lines.append(
            f"- mode: {mode}; broker selected: {getattr(_cfg, 'selected_broker_id', '?')}; "
            f"MT5 credentials set: {bool(getattr(_cfg, 'mt5_login', 0))}"
        )
    except Exception:
        pass
    try:
        from cas_forex.ai_operator import _operator_briefing_context  # noqa: PLC2701

        briefing = _operator_briefing_context()
        if isinstance(briefing, dict) and briefing.get("available"):
            movement_truth = (
                briefing.get("live_movement_source_truth")
                if isinstance(briefing.get("live_movement_source_truth"), dict)
                else {}
            )
            position_feed_label = movement_truth.get("position_feed_label") or briefing.get("live_position_feed_label")
            telemetry_source = movement_truth.get("telemetry_source") or briefing.get("live_telemetry_source")
            price_source_status = movement_truth.get("price_source_status") or briefing.get("live_price_source_status")
            telemetry_stale = (
                movement_truth.get("telemetry_stale")
                if movement_truth.get("telemetry_stale") is not None
                else briefing.get("live_telemetry_stale")
            )
            last_update_iso = movement_truth.get("telemetry_last_update_iso") or briefing.get("live_telemetry_last_update_iso")
            lines.append(
                "- operator briefing: "
                f"loop={briefing.get('loop_health_status') or 'unknown'}, "
                f"open_positions={briefing.get('open_position_count', 'unknown')}, "
                f"floating_pnl={briefing.get('total_floating_pnl', 'unknown')}, "
                f"position_feed={position_feed_label or 'unknown'}, "
                f"telemetry_source={telemetry_source or 'unknown'}, "
                f"price_source_status={price_source_status or 'unknown'}, "
                f"telemetry_stale={str(bool(telemetry_stale)).lower()}, "
                f"last_update={last_update_iso or 'unknown'}"
            )
            position_feed_detail = str(
                movement_truth.get("position_feed_detail")
                or movement_truth.get("detail")
                or briefing.get("live_position_feed_detail")
                or ""
            ).strip()
            if position_feed_detail:
                lines.append("- operator position feed detail: " + position_feed_detail)
            if any(str(key).startswith("broker_truth_") for key in briefing):
                lines.append(
                    "- broker truth briefing: "
                    f"status={briefing.get('broker_truth_monitor_status') or 'unavailable'}, "
                    f"ready_for_live={str(bool(briefing.get('broker_truth_ready_for_live'))).lower()}, "
                    f"paper_force_latched={str(bool(briefing.get('broker_truth_paper_force_latched'))).lower()}, "
                    f"halt_reasons={briefing.get('broker_truth_halt_reason_summary') or 'none'}, "
                    f"position_protection={briefing.get('broker_truth_position_protection_label') or 'PROTECTION UNAVAILABLE'}, "
                    f"unprotected_positions={briefing.get('broker_truth_unprotected_position_count', 0)}, "
                    f"mt5_connected={briefing.get('broker_truth_mt5_connected')}, "
                    f"demo={briefing.get('broker_truth_mt5_is_demo')}, "
                    f"open_positions={briefing.get('broker_truth_open_position_count', 0)}"
                )
                protection_detail = str(briefing.get("broker_truth_position_protection_detail") or "").strip()
                if protection_detail:
                    lines.append("- broker truth protection detail: " + protection_detail)
    except Exception:
        pass
    try:
        from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report

        mobile = latest_mobile_readiness_report()
        package_ready = bool(mobile.get("package_ready_for_phone_install"))
        phone_verified = bool(mobile.get("phone_browser_verified"))
        phone_observed = bool(mobile.get("phone_browser_observed"))
        phone_proof_fresh = bool(mobile.get("phone_proof_fresh"))
        phone_proof_age_seconds = mobile.get("phone_proof_age_seconds")
        phone_proof_expires_at = mobile.get("phone_proof_expires_at") or "unknown"
        phone_observation_fresh = bool(mobile.get("phone_observation_fresh"))
        phone_observation_age_seconds = mobile.get("phone_observation_age_seconds")
        phone_observation_expires_at = mobile.get("phone_observation_expires_at") or "unknown"
        apk_runtime_status = mobile.get("apk_runtime_status") or "none"
        apk_runtime_observed = bool(mobile.get("apk_runtime_observed"))
        apk_runtime_verified = bool(mobile.get("apk_runtime_verified"))
        apk_runtime_fresh = bool(mobile.get("apk_runtime_fresh"))
        apk_verified = bool(mobile.get("apk_install_pairing_verified"))
        apk_attempt_status = mobile.get("apk_install_pairing_attempt_status") or "none"
        apk_attempt_fresh = bool(mobile.get("apk_install_pairing_attempt_fresh"))
        apk_attempt_message = mobile.get("apk_install_pairing_attempt_message") or "none"
        release_signing_ready = bool(mobile.get("android_release_signing_ready"))
        release_signing_status = mobile.get("android_release_signing_status") or "unknown"
        release_signing_detail = mobile.get("android_release_signing_detail") or "unknown"
        release_apk_exists = bool(mobile.get("android_release_apk_exists"))
        android_device_ready = bool(mobile.get("android_device_ready"))
        android_device_count = int(mobile.get("android_device_count") or 0)
        android_device_ready_count = int(mobile.get("android_device_ready_count") or 0)
        android_device_detail = mobile.get("android_device_detail") or "unknown"
        docker_available = bool(mobile.get("docker_available"))
        docker_engine_status = mobile.get("docker_engine_status") or "unknown"
        docker_engine_detail = mobile.get("docker_engine_detail") or "unknown"
        docker_server_version = mobile.get("docker_server_version") or "unknown"
        docker_wsl_checked = bool(mobile.get("docker_wsl_checked"))
        web_base = mobile.get("web_base") or "unknown"
        phone_quick_start_url = mobile.get("phone_quick_start_url") or "unknown"
        commands = mobile.get("verification_commands") if isinstance(mobile.get("verification_commands"), dict) else {}
        mobile_proof_session_command = commands.get("mobile_proof_session") or "unknown"
        phone_verification_session_command = commands.get("phone_verification_session") or "unknown"
        phone_proof_command = commands.get("phone_proof_watcher") or "unknown"
        apk_device_command = commands.get("apk_device_list") or "unknown"
        apk_install_pair_command = commands.get("apk_install_pair") or "unknown"
        apk_wait_install_pair_command = commands.get("apk_wait_install_pair") or apk_install_pair_command
        apk_release_signing_setup_command = commands.get("apk_release_signing_setup") or "unknown"
        apk_release_build_command = commands.get("apk_release_build") or "unknown"
        docker_engine_diagnose_command = commands.get("docker_engine_diagnose") or "unknown"
        docker_desktop_install_command = commands.get("docker_desktop_install") or mobile.get("docker_desktop_install_command") or "unknown"
        docker_desktop_elevated_install_command = (
            commands.get("docker_desktop_install_elevated")
            or mobile.get("docker_desktop_elevated_install_command")
            or "unknown"
        )
        docker_desktop_install_attempt_status = mobile.get("docker_desktop_install_attempt_status") or "unknown"
        docker_engine_command = commands.get("docker_engine_check") or "unknown"
        next_actions = mobile.get("next_verification_actions") if isinstance(mobile.get("next_verification_actions"), list) else []
        next_action = next_actions[0] if next_actions and isinstance(next_actions[0], dict) else {}
        lines.append(
            "- mobile/web: "
            f"package_ready={str(package_ready).lower()}, "
            f"phone_browser_observed={str(phone_observed).lower()}, "
            f"phone_browser_verified={str(phone_verified).lower()}, "
            f"phone_proof_fresh={str(phone_proof_fresh).lower()}, "
            f"phone_proof_age_seconds={phone_proof_age_seconds}, "
            f"phone_proof_expires_at={phone_proof_expires_at}, "
            f"phone_observation_fresh={str(phone_observation_fresh).lower()}, "
            f"phone_observation_age_seconds={phone_observation_age_seconds}, "
            f"phone_observation_expires_at={phone_observation_expires_at}, "
            f"apk_runtime_status={apk_runtime_status}, "
            f"apk_runtime_observed={str(apk_runtime_observed).lower()}, "
            f"apk_runtime_verified={str(apk_runtime_verified).lower()}, "
            f"apk_runtime_fresh={str(apk_runtime_fresh).lower()}, "
            f"android_device_ready={str(android_device_ready).lower()}, "
            f"android_device_ready_count={android_device_ready_count}, "
            f"android_device_count={android_device_count}, "
            f"android_device_detail={android_device_detail}, "
            f"android_apk_pairing_verified={str(apk_verified).lower()}, "
            f"android_apk_pairing_attempt_status={apk_attempt_status}, "
            f"android_apk_pairing_attempt_fresh={str(apk_attempt_fresh).lower()}, "
            f"android_apk_pairing_attempt_message={apk_attempt_message}, "
            f"android_release_signing_ready={str(release_signing_ready).lower()}, "
            f"android_release_signing_status={release_signing_status}, "
            f"android_release_signing_detail={release_signing_detail}, "
            f"android_release_apk_exists={str(release_apk_exists).lower()}, "
            f"docker_available={str(docker_available).lower()}, "
            f"docker_engine_status={docker_engine_status}, "
            f"docker_engine_detail={docker_engine_detail}, "
            f"docker_server_version={docker_server_version}, "
            f"docker_wsl_checked={str(docker_wsl_checked).lower()}, "
            f"docker_desktop_install_command={docker_desktop_install_command}, "
            f"docker_desktop_elevated_install_command={docker_desktop_elevated_install_command}, "
            f"docker_desktop_install_attempt_status={docker_desktop_install_attempt_status}, "
            f"web_base={web_base}, "
            f"phone_quick_start_url={phone_quick_start_url}, "
            f"mobile_proof_session_command={mobile_proof_session_command}, "
            f"phone_verification_session_command={phone_verification_session_command}, "
            f"phone_proof_command={phone_proof_command}, "
            f"apk_device_command={apk_device_command}, "
            f"apk_install_pair_command={apk_install_pair_command}, "
            f"apk_wait_install_pair_command={apk_wait_install_pair_command}, "
            f"apk_release_signing_setup_command={apk_release_signing_setup_command}, "
            f"apk_release_build_command={apk_release_build_command}, "
            f"docker_engine_diagnose_command={docker_engine_diagnose_command}, "
            f"docker_engine_command={docker_engine_command}"
        )
        if next_action:
            secondary_commands = [
                str(command)
                for command in (next_action.get("secondary_commands") or [])
                if str(command).strip()
            ]
            lines.append(
                "- mobile/web next action: "
                f"{next_action.get('action_id', 'unknown')}; "
                f"title={next_action.get('title', 'unknown')}; "
                f"command={next_action.get('command', 'unknown')}; "
                f"target_url={next_action.get('target_url', 'unknown')}; "
                f"secondary_commands={' | '.join(secondary_commands[:5]) or 'none'}"
            )
        gates = [
            str(gate)
            for gate in (mobile.get("remaining_external_gates") or [])
            if str(gate).strip()
        ]
        if gates:
            lines.append("- mobile/web remaining gates: " + " | ".join(gates[:4]))
    except Exception:
        pass
    try:
        from cas_forex.mobile_verification_plan import build_mobile_verification_plan

        plan = build_mobile_verification_plan()
        owner_commands = (
            plan.get("owner_commands")
            if isinstance(plan.get("owner_commands"), dict)
            else {}
        )
        actions = (
            plan.get("next_verification_actions")
            if isinstance(plan.get("next_verification_actions"), list)
            else []
        )
        first_action = actions[0] if actions and isinstance(actions[0], dict) else {}
        plan_text = " / ".join(
            line.strip()
            for line in str(plan.get("text") or "").splitlines()
            if line.strip()
        )
        if len(plan_text) > 1800:
            plan_text = f"{plan_text[:1797]}..."
        lines.append(
            "- mobile verification plan: "
            f"status={plan.get('status', 'unknown')}, "
            f"summary={plan.get('summary', 'unknown')}, "
            f"command={owner_commands.get('mobile_verification_plan') or 'npm --prefix ui run mobile:verification-plan'}, "
            f"endpoint=/api/forex/mobile/verification-plan/latest, "
            f"first_action={first_action.get('title') or first_action.get('action_id') or 'none'}, "
            f"text={plan_text or 'unavailable'}"
        )
    except Exception:
        pass
    try:
        from cas_forex.mobile_final_verification import (
            build_mobile_final_verification,
            mobile_final_verification_to_dict,
        )

        final = mobile_final_verification_to_dict(build_mobile_final_verification())
        owner_commands = (
            final.get("owner_commands")
            if isinstance(final.get("owner_commands"), dict)
            else {}
        )
        gates = final.get("gates") if isinstance(final.get("gates"), list) else []
        pending_gates = [
            str(gate.get("title"))
            for gate in gates
            if isinstance(gate, dict) and not bool(gate.get("satisfied")) and str(gate.get("title") or "").strip()
        ]
        lines.append(
            "- mobile final verification: "
            f"status={final.get('status', 'unknown')}, "
            f"summary={final.get('summary', 'unknown')}, "
            f"phone_quick_start_url={final.get('phone_quick_start_url') or 'unknown'}, "
            f"phone_browser_verified={str(bool(final.get('phone_browser_verified'))).lower()}, "
            f"apk_install_pairing_verified={str(bool(final.get('apk_install_pairing_verified'))).lower()}, "
            f"docker_available={str(bool(final.get('docker_available'))).lower()}, "
            f"pending_gates={len(pending_gates)}, "
            f"pending_gate_titles={' | '.join(pending_gates[:4]) or 'none'}, "
            f"next_owner_step={final.get('next_owner_step') or 'unknown'}, "
            f"command={owner_commands.get('mobile_final_verification') or 'npm --prefix ui run mobile:finish'}, "
            f"watch_command={owner_commands.get('mobile_final_verification_watch') or 'npm --prefix ui run mobile:finish -- --watch-phone'}, "
            f"watch_all_command={owner_commands.get('mobile_final_verification_watch_all') or 'npm --prefix ui run mobile:finish -- --watch-all'}, "
            f"watch_all_live_links_command={owner_commands.get('mobile_final_verification_watch_all_live_links') or 'npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links'}, "
            f"endpoint=/api/forex/mobile/final-verification/latest"
        )
    except Exception:
        pass
    try:
        from cas_forex.mobile_proof_session import (
            build_mobile_proof_session,
            mobile_proof_session_to_dict,
        )

        proof_session = mobile_proof_session_to_dict(build_mobile_proof_session())
        proof_gates = (
            proof_session.get("gates")
            if isinstance(proof_session.get("gates"), list)
            else []
        )
        pending_gate_titles = [
            str(gate.get("title"))
            for gate in proof_gates
            if isinstance(gate, dict) and not bool(gate.get("satisfied")) and str(gate.get("title") or "").strip()
        ]
        owner_commands = (
            proof_session.get("owner_commands")
            if isinstance(proof_session.get("owner_commands"), dict)
            else {}
        )
        pairing_context = (
            proof_session.get("pairing_context")
            if isinstance(proof_session.get("pairing_context"), dict)
            else {}
        )
        lines.append(
            "- mobile proof session: "
            f"status={proof_session.get('status', 'unknown')}, "
            f"summary={proof_session.get('summary', 'unknown')}, "
            f"package_ready={str(bool(proof_session.get('package_ready_for_phone_install'))).lower()}, "
            f"phone_quick_start_url={proof_session.get('phone_quick_start_url') or 'unknown'}, "
            f"phone_proof_target_url={proof_session.get('phone_proof_target_url') or proof_session.get('phone_quick_start_url') or 'unknown'}, "
            f"phone_proof_target_kind={proof_session.get('phone_proof_target_kind') or 'unknown'}, "
            f"phone_pairing_handoff={proof_session.get('phone_pairing_handoff') or 'unknown'}, "
            f"pwa_pairing_context_available={str(bool(pairing_context.get('redacted_pairing_url'))).lower()}, "
            f"native_pairing_context_available={str(bool(pairing_context.get('redacted_native_pairing_url'))).lower()}, "
            f"pending_gates={len(pending_gate_titles)}, "
            f"pending_gate_titles={' | '.join(pending_gate_titles[:4]) or 'none'}, "
            f"docker_elevated_install_command={owner_commands.get('docker_desktop_install_elevated') or 'unknown'}, "
            f"command={owner_commands.get('mobile_proof_session') or 'npm --prefix ui run mobile:proof-session'}"
        )
    except Exception:
        pass
    try:
        from cas_forex.phone_verification_session import (
            DEFAULT_OUTPUT_DIR,
            build_phone_verification_session,
        )

        session = build_phone_verification_session()
        artifact_summary = (
            session.get("release_artifact_summary")
            if isinstance(session.get("release_artifact_summary"), dict)
            else {}
        )
        pairing = (
            session.get("pairing_context")
            if isinstance(session.get("pairing_context"), dict)
            else {}
        )
        steps = (
            session.get("phone_verification_steps")
            if isinstance(session.get("phone_verification_steps"), list)
            else []
        )
        default_json = Path(DEFAULT_OUTPUT_DIR) / "phone_verification_session.json"
        default_readme = Path(DEFAULT_OUTPUT_DIR) / "README.md"
        lines.append(
            "- phone verification session: "
            f"status={session.get('status', 'unknown')}, "
            f"summary={session.get('summary', 'unknown')}, "
            f"json_path={default_json}, "
            f"readme_path={default_readme}, "
            f"pwa_api_base={pairing.get('pwa_api_base') or 'unknown'}, "
            f"direct_api_base={pairing.get('direct_api_base') or 'unknown'}, "
            f"apk_sha256={artifact_summary.get('android_debug_apk_sha256') or 'unknown'}, "
            f"web_index_sha256={artifact_summary.get('web_index_sha256') or 'unknown'}, "
            f"service_worker_sha256={artifact_summary.get('service_worker_sha256') or 'unknown'}, "
            f"all_required_artifacts_present={str(bool(artifact_summary.get('all_required_present'))).lower()}, "
            f"steps_count={len(steps)}"
        )
    except Exception:
        pass
    try:
        from cas_forex.public_launch_gate import build_public_launch_gate

        launch = build_public_launch_gate()
        blockers = launch.get("hard_blockers") if isinstance(launch.get("hard_blockers"), list) else []
        lines.append(
            "- public launch gate: "
            f"launch_gate_status={launch.get('launch_gate_status', 'unknown')}, "
            f"public_launch_status={launch.get('public_launch_status', 'unknown')}, "
            f"live_money_production_status={launch.get('live_money_production_status', 'unknown')}, "
            f"pass_count={launch.get('pass_count', 0)}, "
            f"block_count={launch.get('block_count', 0)}, "
            f"top_blocker={blockers[0] if blockers else 'none'}, "
            f"release_policy={launch.get('release_policy', 'unknown')}"
        )
    except Exception:
        pass
    if not lines:
        return ""
    return (
        "CURRENT LIVE STATE (read-only truth — use this, do not guess status):\n"
        + "\n".join(lines)
    )


def _assistant_fast_model_state_block() -> str:
    """Build conversational runtime truth without running heavy diagnostics.

    The full live-state builder assembles mobile, Docker, APK, and public-launch
    evidence. Those builders belong on audit surfaces, not on every chat request.
    """

    def compact(value: Any, limit: int = 700) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= limit:
            return text or "none"
        return text[: max(0, limit - 3)] + "..."

    lines: list[str] = []
    try:
        from cas_forex.dispatch_loop import loop_status_fast

        dispatch = loop_status_fast()
        lines.append(
            "- dispatch: "
            f"status={dispatch.get('status') or 'unknown'}, "
            f"running={str(bool(dispatch.get('running'))).lower()}, "
            f"desired_running={str(bool(dispatch.get('desired_running'))).lower()}, "
            f"execution_active={str(bool(dispatch.get('execution_active'))).lower()}, "
            f"requested_mode={dispatch.get('requested_mode') or 'unknown'}, "
            f"mode={dispatch.get('mode') or 'unknown'}, "
            f"lane={dispatch.get('execution_lane') or 'NONE'}, "
            f"bridge={dispatch.get('last_bridge_class') or 'unknown'}, "
            f"bridge_status={dispatch.get('last_bridge_selection_status') or 'unknown'}"
        )
        lines.append(
            "- latest cycle: "
            f"run_at={dispatch.get('last_run_iso') or 'unknown'}, "
            f"cycles={dispatch.get('cycles_run', 0)}, "
            f"management_checks={dispatch.get('management_cycles_run', 0)}, "
            f"management={dispatch.get('last_management_status') or 'unknown'}, "
            f"open_positions={dispatch.get('last_management_account_position_count', 'unknown')}, "
            f"selected_timeframe={dispatch.get('last_entry_timeframe') or 'unknown'}, "
            f"entry_lane={dispatch.get('last_entry_lane') or 'unknown'}, "
            f"candidates={dispatch.get('last_entry_risk_operator_candidate_count', 'unknown')}, "
            f"intents={dispatch.get('last_filtered_intent_count', 'unknown')}, "
            f"scale_in={dispatch.get('last_scale_in_status') or 'unknown'}"
        )
        lines.append("- latest cycle summary: " + compact(dispatch.get("last_summary")))
        if dispatch.get("last_error"):
            lines.append("- latest dispatch error: " + compact(dispatch.get("last_error")))
    except Exception as exc:
        lines.append(f"- dispatch: unavailable ({type(exc).__name__})")

    try:
        from cas_forex.ai_operator_position_edge import (
            PROMPT_VERSION as position_prompt_version,
        )
        from cas_forex.ai_operator_trade_edge import (
            PROMPT_VERSION as entry_prompt_version,
        )

        lines.append(
            "- Operator brains: "
            f"entry={entry_prompt_version}, position={position_prompt_version}"
        )
    except Exception:
        pass

    try:
        from cas_forex.model_provider import get_model_provider

        provider = get_model_provider().status()
        lines.append(
            "- Operator model: "
            f"provider={provider.get('active_provider') or 'unavailable'}, "
            f"label={compact(provider.get('active_provider_label'), 180)}, "
            f"last_ok={provider.get('last_ok')}, "
            f"budget_remaining={provider.get('budget_remaining', 'unknown')}"
        )
    except Exception:
        pass

    try:
        from cas_forex.risk_control import resolve_risk_control

        risk = resolve_risk_control()

        def cap(value: Any) -> Any:
            return "unlimited" if value is None else value

        lines.append(
            "- effective risk caps: "
            f"concurrent={cap(risk.max_concurrent_trades)}, "
            f"loss_cap_usd={cap(risk.max_loss_cap_usd)}, "
            f"exposure_lots={cap(risk.max_total_exposure_lots)}, "
            f"drawdown_pct={cap(risk.max_drawdown_pct)}"
        )
    except Exception:
        pass

    try:
        from cas_forex.config import config as runtime_config

        lines.append(
            "- configured account lane: "
            f"live_mode={str(bool(getattr(runtime_config, 'live_mode', False))).lower()}, "
            f"broker={getattr(runtime_config, 'selected_broker_id', 'unknown')}, "
            f"mt5_credentials_set={str(bool(getattr(runtime_config, 'mt5_login', 0))).lower()}"
        )
    except Exception:
        pass

    return (
        "CURRENT LIVE STATE (fast read-only conversational truth; use this, do not guess):\n"
        + "\n".join(lines)
    )


def _assistant_active_local_model_provider() -> Any | None:
    """Return the selected free/local provider, never a paid provider."""
    try:
        from cas_forex.model_provider import get_model_provider

        provider = get_model_provider()
        status = provider.status()
        if status.get("active_provider") and not bool(status.get("active_is_paid")):
            return provider
    except Exception:
        pass
    return None


def _assistant_active_shared_model_provider() -> Any | None:
    """Use the Operator's DeepSeek route for Assistant chat when configured.

    Claude keeps its existing dedicated Assistant transport for compatibility;
    the free local fallback and DeepSeek V4 are shared with the Operator so both
    chat surfaces report and exercise the same actual model capability.
    """

    local = _assistant_active_local_model_provider()
    if local is not None:
        return local
    try:
        from cas_forex.model_provider import get_model_provider

        provider = get_model_provider()
        active_id = str(provider.status().get("active_provider") or "")
        return provider if active_id.startswith("deepseek-") else None
    except Exception:
        return None


def _command_catalog_block() -> str:
    try:
        from cas_forex.owner_command_broker import catalog

        return "COMMAND_CATALOG:\n" + str(catalog())
    except Exception:
        return "COMMAND_CATALOG: unavailable"


def _spec_context_block() -> str:
    try:
        from cas_forex.spec_context import assistant_spec_context

        return assistant_spec_context()
    except Exception:
        return ""


def _assistant_model_spec_context_block() -> str:
    """Return governing spec memory inside a predictable chat prompt budget."""
    text = _spec_context_block()
    if len(text) <= ASSISTANT_SPEC_CONTEXT_MAX_CHARS:
        return text
    suffix = (
        "\n\n[Chat spec digest truncated for response latency. The complete read-only "
        "snapshot remains available through the spec-context artifact and status API.]\n"
    )
    keep = max(0, ASSISTANT_SPEC_CONTEXT_MAX_CHARS - len(suffix))
    return text[:keep] + suffix


def _assistant_topic_evidence_context_block(question: str) -> str:
    """Load expensive evidence only when the owner asks for that exact topic."""
    low = str(question or "").lower()
    needs_mobile_evidence = any(
        marker in low
        for marker in (
            "mobile",
            "phone",
            "apk",
            "docker",
            "proof session",
            "proof-session",
        )
    )
    needs_launch_evidence = any(
        marker in low
        for marker in (
            "public launch",
            "release policy",
            "release blocker",
            "legal review",
            "compliance review",
        )
    )
    sections: list[str] = []
    if needs_mobile_evidence:
        try:
            from cas_forex.mobile_final_verification import (
                build_mobile_final_verification,
                mobile_final_verification_to_dict,
            )
            from cas_forex.mobile_proof_session import (
                build_mobile_proof_session,
                mobile_proof_session_to_dict,
            )
            from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report
            from cas_forex.mobile_verification_plan import build_mobile_verification_plan
            from cas_forex.phone_verification_session import build_phone_verification_session

            latest = latest_mobile_readiness_report()
            plan = build_mobile_verification_plan()
            final = mobile_final_verification_to_dict(build_mobile_final_verification())
            proof = mobile_proof_session_to_dict(build_mobile_proof_session())
            phone = build_phone_verification_session()
            pairing = phone.get("pairing_context") if isinstance(phone.get("pairing_context"), dict) else {}
            artifacts = (
                phone.get("release_artifact_summary")
                if isinstance(phone.get("release_artifact_summary"), dict)
                else {}
            )
            payload = {
                "latest": {
                    key: latest.get(key)
                    for key in (
                        "package_ready_for_phone_install",
                        "phone_browser_observed",
                        "phone_browser_verified",
                        "phone_proof_fresh",
                        "phone_observation_fresh",
                        "apk_runtime_status",
                        "apk_runtime_verified",
                        "apk_install_pairing_verified",
                        "android_device_ready",
                        "android_release_signing_ready",
                        "docker_available",
                        "docker_engine_status",
                        "web_base",
                        "phone_quick_start_url",
                        "verification_commands",
                        "next_verification_actions",
                        "remaining_external_gates",
                    )
                },
                "plan": {
                    "status": plan.get("status"),
                    "summary": plan.get("summary"),
                    "owner_commands": plan.get("owner_commands"),
                    "next_verification_actions": plan.get("next_verification_actions"),
                },
                "final": {
                    "status": final.get("status"),
                    "summary": final.get("summary"),
                    "next_owner_step": final.get("next_owner_step"),
                    "gates": final.get("gates"),
                    "owner_commands": final.get("owner_commands"),
                },
                "proof_session": {
                    "status": proof.get("status"),
                    "summary": proof.get("summary"),
                    "phone_proof_target_kind": proof.get("phone_proof_target_kind"),
                    "phone_pairing_handoff": proof.get("phone_pairing_handoff"),
                    "gates": proof.get("gates"),
                    "owner_commands": proof.get("owner_commands"),
                },
                "phone_session": {
                    "status": phone.get("status"),
                    "summary": phone.get("summary"),
                    "pwa_api_base": pairing.get("pwa_api_base"),
                    "direct_api_base": pairing.get("direct_api_base"),
                    "release_artifact_summary": artifacts,
                    "verification_step_count": len(phone.get("phone_verification_steps") or []),
                },
            }
            sections.append(
                "REQUESTED MOBILE/PHONE EVIDENCE (read-only):\n"
                + json.dumps(payload, sort_keys=True, ensure_ascii=True)
            )
        except Exception as exc:
            sections.append(
                f"REQUESTED MOBILE/PHONE EVIDENCE: unavailable ({type(exc).__name__})"
            )
    if needs_launch_evidence:
        try:
            from cas_forex.public_launch_gate import build_public_launch_gate

            launch = build_public_launch_gate()
            payload = {
                key: launch.get(key)
                for key in (
                    "launch_gate_status",
                    "public_launch_status",
                    "live_money_production_status",
                    "pass_count",
                    "block_count",
                    "hard_blockers",
                    "release_policy",
                    "next_action",
                )
            }
            sections.append(
                "REQUESTED PUBLIC-LAUNCH EVIDENCE (read-only):\n"
                + json.dumps(payload, sort_keys=True, ensure_ascii=True)
            )
        except Exception as exc:
            sections.append(
                f"REQUESTED PUBLIC-LAUNCH EVIDENCE: unavailable ({type(exc).__name__})"
            )
    return "\n\n".join(sections)


async def _bounded_assistant_context(builder: Any, *, label: str) -> str:
    """Run one read-only prompt builder off-loop and return an honest fallback."""
    try:
        return await asyncio.wait_for(
            run_in_threadpool(builder),
            timeout=ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS,
        )
    except asyncio.TimeoutError:
        return (
            f"{label}: unavailable within the "
            f"{ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS:g}-second chat context budget; "
            "do not guess its current value."
        )
    except Exception as exc:
        return f"{label}: unavailable ({type(exc).__name__}); do not guess its current value."


def _assistant_local_status_reply(question: str) -> str | None:
    low = str(question or "").lower().strip()
    educational_question = any(
        marker in low
        for marker in (
            "explain the difference",
            "difference between",
            "define ",
            "what does ",
            "what is the meaning",
        )
    ) and not any(
        marker in low
        for marker in (
            "current",
            "right now",
            "my account",
            "our account",
            "why hasn't",
            "why hasnt",
            "not changed",
            "not moving",
            "status",
        )
    )
    if educational_question:
        return None
    try:
        from cas_forex.ai_operator import (  # noqa: PLC2701
            _compact_mt5_snapshot,
            _is_general_system_health_question,
            _local_chat_reply,
            _operator_briefing_context,
            _safe,
            _should_answer_chat_locally_first,
            _stack_health_context,
            gather_chat_context,
        )
    except Exception:
        return None
    if not _should_answer_chat_locally_first(question):
        return None
    context = gather_chat_context()
    needs_live_mt5 = any(
        marker in low
        for marker in (
            "mt5",
            "metatrader",
            "account",
            "balance",
            "equity",
            "floating",
            "p&l",
            "pnl",
            "position",
            "trade",
            "broker",
            "margin",
        )
    )
    if needs_live_mt5 and not isinstance(context.get("live_mt5"), dict):
        context["live_mt5"] = _safe(
            lambda: _compact_mt5_snapshot(
                __import__(
                    "cas_forex.mt5_live",
                    fromlist=["get_mt5_account_snapshot"],
                ).get_mt5_account_snapshot(force=False)
            ),
            {"available": False},
        )
    if _is_general_system_health_question(question):
        context["operator_briefing"] = _operator_briefing_context()
        context["stack_health"] = _stack_health_context(context.get("operator_briefing"))
    return _local_chat_reply(question, context, model_attempted=False)


def _assistant_local_active_account_truth_reply(question: str) -> str | None:
    """Answer current-account questions from the same contract as the Operator."""

    from cas_forex.account_chat_truth import (
        asks_active_account_truth,
        compose_active_account_chat_reply,
        project_active_account_chat_truth,
    )

    if not asks_active_account_truth(question):
        return None
    try:
        from api.data import active_account_truth
        from cas_forex.ai_operator import _profit_and_balance  # noqa: PLC2701

        projection = project_active_account_chat_truth(
            active_account_truth(),
            simulator_evidence=_profit_and_balance(),
        )
        return compose_active_account_chat_reply(projection)
    except Exception as exc:
        return (
            "The active execution-account truth could not be collected, so I will not "
            "guess a balance, P&L, realized growth, or position count. "
            f"Diagnostic={type(exc).__name__}. No order ran, no dial changed, and no "
            "money moved from this chat."
        )


_LOCAL_PAGE_ORDER = [
    "Quick Start",
    "Proof",
    "Audit",
    "Dashboard",
    "Tracker",
    "Trade",
    "Live Charts",
    "Adaptive",
    "History",
    "Settings",
    "PCBA/CJT",
    "Ledger",
    "Optimizer",
    "Cond. Lab",
    "Decisions",
    "Fury",
    "Strategy",
    "Stack",
    "Compare",
    "Daily",
]

_LOCAL_PAGE_ALIASES = {
    "quick start": "Quick Start",
    "proof": "Proof",
    "audit": "Audit",
    "dashboard": "Dashboard",
    "tracker": "Tracker",
    "trade": "Trade",
    "live charts": "Live Charts",
    "charts": "Live Charts",
    "adaptive": "Adaptive",
    "history": "History",
    "settings": "Settings",
    "pcba": "PCBA/CJT",
    "cjt": "PCBA/CJT",
    "ledger": "Ledger",
    "optimizer": "Optimizer",
    "cond. lab": "Cond. Lab",
    "condition lab": "Cond. Lab",
    "decisions": "Decisions",
    "fury": "Fury",
    "strategy": "Strategy",
    "stack": "Stack",
    "compare": "Compare",
    "daily": "Daily",
}


def _assistant_page_navigation(label: str, *, phone: bool) -> str:
    if phone:
        return (
            f"{label} is a real page. On phone, tap the menu button near the top "
            f"(it shows the current page name), then tap {label}."
        )
    return f"{label} is a real top-bar page. Click {label} in the top navigation."


def _assistant_local_trading_authority_reply(question: str) -> str | None:
    low = str(question or "").lower()
    asks_compound = any(
        marker in low
        for marker in ("compound", "scale in", "scale-in", "add to", "add another")
    )
    if not asks_compound or not any(
        marker in low for marker in ("trade", "position", "winner", "winning")
    ):
        return None
    try:
        from cas_forex.dispatch_loop import loop_status_fast

        dispatch = loop_status_fast()
    except Exception:
        dispatch = {}
    running = bool(dispatch.get("running"))
    lane = str(dispatch.get("execution_lane") or "NONE")
    management = str(dispatch.get("last_management_status") or "not reported")
    scale_in_status = str(dispatch.get("last_scale_in_status") or "not evaluated")
    scale_in_options = int(dispatch.get("last_scale_in_action_count") or 0)
    scale_in_blockers = [
        row
        for row in (dispatch.get("last_scale_in_blockers") or [])
        if isinstance(row, dict)
    ]
    scale_in_truth = (
        " Current compounding feasibility: "
        f"status={scale_in_status}, broker-grid options={scale_in_options}, "
        f"blocked parents={len(scale_in_blockers)}."
    )
    if scale_in_blockers:
        scale_in_truth += " Binding blockers: " + "; ".join(
            f"{row.get('symbol') or 'unknown'} ticket "
            f"{row.get('parent_broker_ticket') or 'unknown'}: "
            f"{row.get('reason') or 'unspecified blocker'}"
            for row in scale_in_blockers[:8]
        ) + "."
    return (
        "Yes. The Operator is allowed to compound a qualifying winning position "
        "autonomously inside the owner's limits. The parent must be fresh, broker-protected, "
        "and net positive after reported costs, and the exact add must pass stop-risk, margin, "
        "exposure, position-count, and broker lot-grid checks. Floating green by itself is not "
        f"enough. Current runtime: dispatch running={running}, lane={lane}, management={management}. "
        f"{scale_in_truth} "
        "This Assistant chat does not place the add; the Operator's management runtime evaluates "
        "it and sends any qualifying action through order dispatch and the execution guard."
    )


def _assistant_local_strategy_comparison_reply(question: str) -> str | None:
    """Ground common current-regime comparisons in dispatch truth, not invention."""
    low = str(question or "").lower()
    compares_mean_and_trend = "mean reversion" in low and any(
        marker in low
        for marker in ("trend continuation", "trend following", "trend-following")
    )
    asks_current = any(
        marker in low
        for marker in ("current", "right now", "paper lane", "live lane", "today")
    )
    if not (compares_mean_and_trend and asks_current):
        return None
    try:
        from cas_forex.dispatch_loop import loop_status_fast

        dispatch = loop_status_fast()
    except Exception:
        dispatch = {}
    return (
        "Mean reversion expects price to move back toward a reference level after a "
        "deviation; trend continuation expects directional momentum to persist. "
        "Current runtime truth: "
        f"dispatch running={bool(dispatch.get('running'))}, "
        f"lane={dispatch.get('execution_lane') or 'NONE'}, "
        f"timeframe={dispatch.get('last_entry_timeframe') or 'unknown'}, "
        f"entry lane={dispatch.get('last_entry_lane') or 'unknown'}, "
        f"Operator candidates={dispatch.get('last_entry_risk_operator_candidate_count', 'unknown')}, "
        f"intents={dispatch.get('last_filtered_intent_count', 'unknown')}. "
        "That fast snapshot does not contain a validated current regime classification, "
        "so I cannot truthfully claim the market is trending or mean-reverting from it. "
        "The Operator must make that choice from fresh completed candles and quote evidence. "
        "No command or order ran from this answer."
    )


def _assistant_fast_availability_reply(question: str) -> str | None:
    low = str(question or "").lower()
    asks_availability = (
        "neither" in low and any(marker in low for marker in ("respond", "reply"))
    ) or any(
        marker in low
        for marker in (
            "not responding",
            "isn't responding",
            "isnt responding",
            "won't respond",
            "wont respond",
            "not reply",
            "no reply",
            "request failed",
            "timed out",
            "ai systems",
            "model offline",
        )
    )
    if not asks_availability:
        return None
    try:
        from cas_forex.dispatch_loop import loop_status_fast

        dispatch = loop_status_fast()
    except Exception:
        dispatch = {}
    try:
        from cas_forex.model_provider import get_model_provider

        provider = get_model_provider().status()
    except Exception:
        provider = {}
    running = bool(dispatch.get("running"))
    lane = str(dispatch.get("execution_lane") or "NONE")
    active_provider = str(provider.get("active_provider_label") or "unavailable")
    budget_remaining = provider.get("budget_remaining")
    budget_exhausted = budget_remaining is not None and int(budget_remaining) <= 0
    assistant_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    operator_paid_ready = bool(provider.get("active_is_paid")) and not budget_exhausted
    active_provider_id = str(provider.get("active_provider") or "").strip()
    operator_deepseek_selected = active_provider_id.startswith("deepseek-")
    operator_local_selected = bool(active_provider_id) and not bool(
        provider.get("active_is_paid")
    )
    operator_model_selected = operator_paid_ready or operator_local_selected
    provider_reachability = str(
        provider.get("provider_reachability") or "NOT_PROBED"
    ).upper()
    provider_error = str(provider.get("provider_last_error") or "").strip()[:260]
    if provider_reachability == "FAILED":
        availability = (
            "The selected Operator model failed its last real generation request: "
            f"{provider_error or 'provider generation failed'}. Grounded Assistant runtime "
            "answers remain available while model recovery is required."
        )
    elif provider_reachability == "STALE":
        availability = (
            "The selected Operator model has no fresh successful generation proof; its last "
            "capability result is stale. Grounded Assistant runtime answers remain available."
        )
    elif provider_reachability == "READY" and (
        assistant_key or operator_deepseek_selected
    ):
        availability = "Both free-form chat paths have a fresh successful model response."
    elif provider_reachability == "READY":
        availability = (
            "The selected Operator/local Assistant model answered its latest generation "
            "request successfully. Grounded Assistant runtime answers are also available."
        )
    elif operator_model_selected and (
        assistant_key or operator_deepseek_selected
    ):
        availability = (
            "Both free-form chat paths are configured, but the selected provider has not "
            "yet completed a capability request in this health window."
        )
    elif operator_model_selected:
        availability = (
            "The Operator has a free-form model selected. The Assistant Claude model is "
            "not configured, while grounded Assistant runtime answers remain available."
        )
    elif assistant_key:
        availability = (
            "The Assistant Claude model is configured, but no Operator language-model "
            "provider is currently selected."
        )
    else:
        availability = (
            "No free-form language-model path is currently configured; grounded local "
            "runtime answers remain available."
        )
    return (
        "The chat route is responding. "
        f"Autonomous dispatch is running={running} in lane={lane}. "
        f"The Operator currently selects {active_provider}; its legacy Claude budget is "
        f"{'exhausted' if budget_exhausted else 'available or not applicable'}. "
        f"The Assistant shared-provider path is "
        f"{'configured' if operator_deepseek_selected or operator_local_selected else 'not selected'}; "
        f"the dedicated Claude key is {'configured' if assistant_key else 'not configured'}. "
        f"{availability} "
        "Known cockpit, authority, and runtime questions use an immediate local answer "
        "instead of waiting on a dead model connection. No command or order ran from this chat."
    )


def _assistant_local_navigation_reply(question: str) -> str | None:
    low = str(question or "").lower()
    mentions_phone = "phone" in low or "mobile" in low
    navigation_intent = any(
        token in low
        for token in (
            "where",
            "find",
            "go to",
            "missing",
            "can't see",
            "cant see",
            "how do i get to",
        )
    )
    if any(token in low for token in ("what pages", "which pages", "what screens", "which screens", "page list")):
        page_list = ", ".join(_LOCAL_PAGE_ORDER)
        return (
            "These are the real page labels in the app: "
            + page_list
            + ". On phone, use the menu button near the top to open that list."
        )
    for alias, label in _LOCAL_PAGE_ALIASES.items():
        if alias in low and navigation_intent:
            return _assistant_page_navigation(label, phone=mentions_phone)
    if "go live" in low or "live trading" in low:
        return (
            "Go live from Settings > Go Live - Owner Switches. That panel holds the "
            "acknowledgments plus Live mode, Prefer MT5 bridge, Owner-enable live trading, "
            "and Owner ACCEPT live authority. It also shows whether the live-trading gate "
            "is AUTHORIZED or what is still missing."
        )
    if any(token in low for token in ("risk cap", "risk caps", "max concurrent", "max drawdown", "max loss cap", "exposure lots")):
        return (
            "Risk caps live in Settings > Risk Control - You Drive. That panel is where "
            "you set Max Concurrent Trades, Max Loss Cap (USD), Max Total Exposure (lots), "
            "and Max Drawdown (%), each with an Unlimited toggle."
        )
    if any(token in low for token in ("daily winnings target", "daily target", "monthly target")):
        return (
            "The daily winnings target lives in the AI Operator panel. Click the Operator "
            "badge in the top bar, then use the Daily Winnings Target section in its profit panel."
        )
    if any(token in low for token in ("phone / apk connection", "apk connection", "phone api", "api address", "phone address")):
        return (
            "The phone API address is in Settings > Phone / APK Connection. That panel has "
            "the text box for the phone's API address plus Save and Reset."
        )
    if any(token in low for token in ("path to authorize everything", "authorize everything", "payout automation", "sweep ledger", "auto-deposit", "bank/card movement")):
        return (
            "Money-movement and payout authorization lives in Settings > Path to Authorize Everything. "
            "That panel holds the live-money capability toggles, broker funding middleware URL, "
            "Sandbox/Live provider environment, "
            "bound broker account ID, provider key, and destination allowlist. Stripe alone is "
            "not an MT5/Hugo's Way custody rail. Sandbox contract ACCEPT is test evidence only, "
            "not proof of external movement. In Verified Profit Sweep, the owner can arm "
            "AI Autonomous Sweep once; later in-envelope incremental sweeps do not require "
            "per-transfer confirmation and remain visible in the Operator dropdown."
        )
    return None


def _assistant_local_startup_reply(question: str) -> str | None:
    low = str(question or "").lower()
    asks_startup = any(
        token in low
        for token in (
            "start the app",
            "start app",
            "start the stack",
            "start the phone app",
            "start on my phone",
            "start on phone",
            "use on my phone",
            "use on phone",
            "laptop and phone",
            "phone and laptop",
            "step by step",
        )
    )
    if not asks_startup:
        return None
    try:
        from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report

        readiness = latest_mobile_readiness_report()
    except Exception:
        readiness = {}
    commands = readiness.get("verification_commands") if isinstance(readiness.get("verification_commands"), dict) else {}
    web_base = str(readiness.get("web_base") or "unknown").strip()
    phone_quick_start_url = str(readiness.get("phone_quick_start_url") or "unknown").strip()
    mobile_stack = commands.get("mobile_stack") or "npm --prefix ui run mobile:stack"
    phone_proof = commands.get("phone_proof_watcher") or "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    proof_session = commands.get("mobile_proof_session") or "npm --prefix ui run mobile:proof-session"
    verify_session = commands.get("phone_verification_session") or "npm --prefix ui run mobile:verify-session"
    return (
        "Start path from current local evidence: "
        f"1) On the laptop, start or reuse the stack with `{mobile_stack}`. "
        f"2) On the laptop, open Quick Start at {phone_quick_start_url if phone_quick_start_url != 'unknown' else 'the Quick Start page'}. "
        f"3) On the phone on the same LAN, open {phone_quick_start_url if phone_quick_start_url != 'unknown' else 'the phone Quick Start URL from Quick Start / Owner Access'}. "
        f"4) If you need phone proof, run `{phone_proof}`. "
        f"5) For the combined phone/APK/Docker checklist, run `{proof_session}` or `{verify_session}`. "
        f"Current web base: {web_base}."
    )


def _assistant_local_reply(question: str) -> str | None:
    return (
        _assistant_local_trading_authority_reply(question)
        or _assistant_local_active_account_truth_reply(question)
        or _assistant_local_strategy_comparison_reply(question)
        or _assistant_fast_availability_reply(question)
        or _assistant_local_navigation_reply(question)
        or _assistant_local_startup_reply(question)
        or _assistant_local_status_reply(question)
    )


class AssistantTurn(BaseModel):
    role: str = Field(..., description='"user" or "assistant"')
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[AssistantTurn] = Field(default_factory=list)


@router.get("/status")
async def assistant_status() -> dict[str, Any]:
    """Report configuration truth without claiming an untested provider is reachable."""
    anthropic_configured = bool(os.environ.get("ANTHROPIC_API_KEY"))
    shared_provider = _assistant_active_shared_model_provider()
    configured = anthropic_configured or shared_provider is not None
    local_status = shared_provider.status() if shared_provider is not None else {}
    provider_reachability = str(
        local_status.get("provider_reachability") or "NOT_PROBED"
    ).upper()
    provider_error = str(local_status.get("provider_last_error") or "").strip()
    active_provider_id = str(local_status.get("active_provider") or "")
    provider_label = str(local_status.get("active_provider_label") or "")
    if shared_provider is not None and provider_reachability == "FAILED":
        detail = (
            "The selected shared model failed its latest real generation request: "
            f"{provider_error or 'provider generation failed'}. Configuration alone is not "
            "being reported as readiness."
        )
    elif shared_provider is not None and provider_reachability == "READY":
        detail = f"{provider_label or 'The selected shared model'} completed its latest generation request successfully."
    elif shared_provider is not None and provider_reachability == "STALE":
        detail = (
            "The selected shared model is configured, but its last capability result is stale; "
            "the next chat request will verify it again."
        )
    elif shared_provider is not None:
        detail = (
            "A shared Assistant model is selected, but it has not completed a capability "
            "request in the current health window."
        )
    elif anthropic_configured:
        detail = "Claude is configured; provider reachability is verified on each chat request."
    else:
        detail = "Configure a local model or ANTHROPIC_API_KEY to enable free-form AI replies."
    return {
        "report_kind": "cas_forex_assistant_status",
        "configured": configured,
        "provider_reachability": provider_reachability,
        "provider_last_error": provider_error or None,
        "provider_last_attempt_at": local_status.get("provider_last_attempt_at"),
        "provider_health_age_seconds": local_status.get("provider_health_age_seconds"),
        "model": (
            local_status.get("active_provider_label")
            if shared_provider is not None
            else DEFAULT_MODEL
        ),
        "anthropic_configured": anthropic_configured,
        "shared_provider_selected": shared_provider is not None,
        "local_fallback_selected": active_provider_id == "local-fallback",
        "deepseek_selected": active_provider_id.startswith("deepseek-"),
        "gemma4_backup_selected": active_provider_id == "gemma4-backup",
        "gemma4_backup_configured": bool(
            local_status.get("gemma4_backup_configured")
        ),
        "detail": detail,
    }


@router.post("/chat")
async def assistant_chat(body: ChatRequest) -> dict[str, Any]:
    """Return a Claude reply to the owner's message. Never raises."""
    question = str(body.message or "").strip()
    try:
        from cas_forex.account_chat_truth import asks_active_account_truth

        asks_account_truth = asks_active_account_truth(question)
    except Exception:
        asks_account_truth = False
    if asks_account_truth:
        try:
            account_reply = await asyncio.wait_for(
                run_in_threadpool(
                    _assistant_local_active_account_truth_reply,
                    question,
                ),
                timeout=ASSISTANT_ACCOUNT_TRUTH_RESPONSE_BUDGET_SECONDS,
            )
        except Exception as exc:
            account_reply = (
                "The authoritative active-account read did not complete inside its "
                "bounded response window, so I will not ask a general model to guess "
                "the balance, P&L, realized growth, or position count. "
                f"Diagnostic={type(exc).__name__}. No order ran, no dial changed, and "
                "no money moved from this chat."
            )
        return {
            "reply": account_reply,
            "source": "local",
            "model": "local-runtime-truth",
            "proposed_command": None,
            "command_preview": None,
            "claim_boundary": (
                "Current account answers come from the shared authoritative runtime "
                "truth contract, not free-form model inference."
            ),
        }
    try:
        local_reply = await asyncio.wait_for(
            run_in_threadpool(_assistant_local_reply, question),
            timeout=ASSISTANT_CONTEXT_RESPONSE_BUDGET_SECONDS,
        )
    except Exception:
        local_reply = None
    if local_reply is not None:
        return {
            "reply": local_reply,
            "source": "local",
            "model": "local-runtime-truth",
            "proposed_command": None,
            "command_preview": None,
            "claim_boundary": (
                "Assistant local replies can come straight from current local app state. "
                "They are read-only diagnostics or navigation guidance, not command execution."
            ),
        }
    shared_model_provider = _assistant_active_shared_model_provider()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and shared_model_provider is None:
        return {
            "reply": (
                "I'm here and wired into your cockpit — but my AI brain needs an "
                "model provider to actually answer you. Configure DeepSeek V4, "
                "Anthropic, or Ollama on the machine running the API and I'll start replying. "
                "In the meantime: the top navigation, or the phone menu button, gets you to Quick Start, Settings "
                "(the API-address field for your phone), Optimizer (Condition Lab), "
                "and the Ledger."
            ),
            "source": "unconfigured",
            "needs": "DEEPSEEK_CLAUDE_OR_OLLAMA_PROVIDER",
            "model": DEFAULT_MODEL,
            "proposed_command": None,
            "command_preview": None,
        }

    try:
        messages = [
            {"role": t.role, "content": t.content}
            for t in body.history
            if t.role in ("user", "assistant") and t.content.strip()
        ]
        messages.append({"role": "user", "content": question})
        live, spec_context, command_catalog, topic_evidence = await asyncio.gather(
            _bounded_assistant_context(
                _assistant_fast_model_state_block,
                label="CURRENT LIVE STATE",
            ),
            _bounded_assistant_context(
                _assistant_model_spec_context_block,
                label="SPEC CONTEXT",
            ),
            _bounded_assistant_context(
                _command_catalog_block,
                label="COMMAND CATALOG",
            ),
            _bounded_assistant_context(
                lambda: _assistant_topic_evidence_context_block(question),
                label="REQUESTED EXTENDED EVIDENCE",
            ),
        )
        system = (
            SYSTEM_PROMPT
            + "\n\n"
            + command_catalog
            + ("\n\n" + spec_context if spec_context else "")
            + ("\n\n" + live if live else "")
            + ("\n\n" + topic_evidence if topic_evidence else "")
        )
        response_source = "ai"
        response_model = DEFAULT_MODEL
        if shared_model_provider is not None:
            local_spec_context = spec_context
            if len(local_spec_context) > ASSISTANT_LOCAL_SPEC_CONTEXT_MAX_CHARS:
                local_spec_context = (
                    local_spec_context[:ASSISTANT_LOCAL_SPEC_CONTEXT_MAX_CHARS]
                    + "\n[Local chat spec digest truncated; full read-only spec remains available.]"
                )
            local_system = (
                LOCAL_SYSTEM_PROMPT
                + "\n\n"
                + command_catalog
                + ("\n\n" + local_spec_context if local_spec_context else "")
                + ("\n\n" + live if live else "")
                + ("\n\n" + topic_evidence if topic_evidence else "")
            )
            conversation_prompt = "\n\n".join(
                f"{str(message['role']).upper()}: {message['content']}"
                for message in messages
            ) + "\n\nASSISTANT:"

            def _call_shared_model() -> dict[str, Any]:
                return shared_model_provider.generate(
                    conversation_prompt,
                    local_system,
                    request_kind="assistant_chat",
                    request_timeout=ASSISTANT_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS,
                    max_attempts=1,
                    max_output_tokens=512,
                )

            local_result = await asyncio.wait_for(
                run_in_threadpool(_call_shared_model),
                timeout=ASSISTANT_LOCAL_MODEL_RESPONSE_BUDGET_SECONDS,
            )
            if not bool(local_result.get("ok")):
                raise RuntimeError(str(local_result.get("error") or "local model failed"))
            text = str(local_result.get("text") or "").strip()
            response_source = (
                "ai-local"
                if str(local_result.get("provider") or "") == "local-fallback"
                else "ai-provider"
            )
            response_model = str(
                local_result.get("model_ref")
                or local_result.get("provider_label")
                or "local-model"
            )
        else:
            import anthropic

            def _call_model() -> Any:
                try:
                    client = anthropic.Anthropic(
                        api_key=api_key,
                        timeout=ASSISTANT_MODEL_RESPONSE_BUDGET_SECONDS,
                        max_retries=0,
                    )
                except TypeError:
                    # Lightweight test doubles and older SDKs may not accept transport options.
                    client = anthropic.Anthropic(api_key=api_key)
                return client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=1024,
                    system=system,
                    messages=messages,
                )

            resp = await asyncio.wait_for(
                run_in_threadpool(_call_model),
                timeout=ASSISTANT_MODEL_RESPONSE_BUDGET_SECONDS,
            )
            text = "".join(
                getattr(block, "text", "")
                for block in resp.content
                if getattr(block, "type", None) == "text"
            ).strip()
        proposed = None
        display = text
        preview = None
        try:
            from cas_forex.ai_operator import _extract_proposed_command  # noqa: PLC2701
            from cas_forex.owner_command_broker import preview as preview_command

            proposed, display = _extract_proposed_command(text)
            if proposed is not None:
                preview = preview_command(proposed["command"], proposed.get("params") or {})
        except Exception:
            proposed = None
            display = text
            preview = None
        return {
            "reply": display or "(the assistant returned an empty reply)",
            "source": response_source,
            "model": response_model,
            "proposed_command": proposed,
            "command_preview": preview,
            "claim_boundary": (
                "Assistant chat can propose an owner command and show its preview; "
                "nothing changes until the owner confirms the exact phrase. Execution "
                "runs through the owner command broker and writes a receipt."
            ),
        }
    except Exception as exc:  # network / auth / model error — never 500 the chat
        local_reply = _assistant_local_navigation_reply(question)
        if local_reply is not None:
            return {
                "reply": local_reply,
                "source": "local",
                "model": DEFAULT_MODEL,
                "proposed_command": None,
                "command_preview": None,
                "claim_boundary": (
                    "Assistant local navigation replies are read-only guidance about real "
                    "pages and control locations. They do not execute anything."
                ),
            }
        return {
            "reply": (
                "The Assistant chat route is working, but the selected model request "
                f"failed ({type(exc).__name__}). No command, order, or dial change ran. "
                "Known cockpit and runtime questions still receive immediate local answers."
            ),
            "source": "error",
            "model": DEFAULT_MODEL,
            "proposed_command": None,
            "command_preview": None,
        }
