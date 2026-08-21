"""Offline tests for the missed-tick induction tool.

No boto3, no sockets, no AWS, and no real sleeping.

This is the only tool in the set that disables a safety schedule, so the tests
concentrate on the guards and on one property above all: **the schedule is
always re-enabled**, including when the wait raises.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import induce_missed_ticks as ind  # noqa: E402

PREPROD = "123456789012"
RULE = "cas-harness-preprod-guardian-RecoverySchedule-ABC"


class _FakeEvents:
    def __init__(self, state="ENABLED"):
        self.state = state
        self.calls: list[str] = []

    def describe_rule(self, Name):
        self.calls.append(f"describe:{Name}")
        return {"Name": Name, "State": self.state}

    def disable_rule(self, Name):
        self.calls.append(f"disable:{Name}")
        self.state = "DISABLED"

    def enable_rule(self, Name):
        self.calls.append(f"enable:{Name}")
        self.state = "ENABLED"


class _FakeSession:
    def __init__(self, account, events):
        self._account, self._events = account, events

    def client(self, service, **_):
        if service == "sts":
            return self
        return self._events

    def get_caller_identity(self):
        return {"Account": self._account, "Arn": f"arn:aws:sts::{self._account}:x"}


def factory(account, events):
    return lambda _acct: _FakeSession(account, events)


# --- guard 1: never production ----------------------------------------------


def test_management_account_is_refused():
    ev = _FakeEvents()
    with pytest.raises(ind.InductionRefused, match="management/production"):
        ind.induce(account_id=ind.MANAGEMENT_ACCOUNT, rule_name=RULE,
                   disable_seconds=60, session_factory=factory(ind.MANAGEMENT_ACCOUNT, ev),
                   sleep=lambda _s: None)
    assert ev.calls == [], "nothing may be touched when a guard refuses"


@pytest.mark.parametrize("bad", ["1234", "not-an-account", ""])
def test_malformed_account_is_refused(bad):
    with pytest.raises(ind.InductionRefused, match="malformed"):
        ind.check_not_management(bad)


# --- guard 2: the session must land where asked ------------------------------


def test_session_landing_elsewhere_is_refused_before_any_change():
    ev = _FakeEvents()
    with pytest.raises(ind.InductionRefused, match="session landed in account"):
        ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                   session_factory=factory("999999999999", ev), sleep=lambda _s: None)
    assert "disable:" not in " ".join(ev.calls)


# --- guard 3: the rule must look like preproduction --------------------------


@pytest.mark.parametrize("name", [
    "cas-runpod-guardian-v1-RecoverySchedule",
    "prod-guardian-schedule",
    "RecoverySchedule",
])
def test_rule_without_preproduction_marker_is_refused(name):
    with pytest.raises(ind.InductionRefused, match="no preproduction marker"):
        ind.check_preproduction_rule(name)


@pytest.mark.parametrize("name", [
    "cas-harness-preprod-RecoverySchedule",
    "CAS-PRE-PROD-Rule",
    "guardian-staging-tick",
    "some-TEST-rule",
])
def test_preproduction_markers_are_accepted_case_insensitively(name):
    ind.check_preproduction_rule(name)


# --- guard 4: the window is bounded on both sides ----------------------------


def test_only_exactly_one_cadence_is_accepted():
    ind.check_window(ind.CADENCE_SECONDS)          # the one admissible window
    assert ind.MIN_DISABLE_SECONDS == ind.MAX_DISABLE_SECONDS == ind.CADENCE_SECONDS


@pytest.mark.parametrize("bad", [59, 61, 75, 119, 120, 240, 600])
def test_every_other_window_is_refused(bad):
    with pytest.raises(ind.InductionRefused, match="must be exactly"):
        ind.check_window(bad)


# --- regressions taken from TWO real live failures ---------------------------
#
# 2026-08-21 attempt 1: a 240 s window produced a 311,788 ms gap.
# 2026-08-21 attempt 2: a 120 s window produced a 210,900 ms gap.
# Both breached the 180,000 ms bound. The tool manufactured the failure it
# exists to detect, and the second attempt exposed a parameter that asserted an
# alignment the code never performed.


@pytest.mark.parametrize("window,observed_gap_ms", [(240, 311788), (120, 210900)])
def test_the_windows_that_actually_broke_live_runs_are_refused(window, observed_gap_ms):
    assert observed_gap_ms > ind.GAP_ACCEPTANCE_BOUND_MILLISECONDS
    with pytest.raises(ind.InductionRefused, match="must be exactly"):
        ind.check_window(window)


def test_worst_case_counts_TWO_cadences_because_the_tool_does_not_align():
    # The tool disables the instant it is called, so slop occurs on both sides.
    assert ind.worst_case_gap_milliseconds(60) == (60 + 120) * 1000
    assert ind.worst_case_gap_milliseconds(60) == ind.GAP_ACCEPTANCE_BOUND_MILLISECONDS


def test_no_alignment_parameter_survives_in_the_CODE():
    # A parameter claiming a property the code does not implement is worse than
    # no parameter: it makes the arithmetic look sound. It must stay deleted.
    #
    # Comments are excluded deliberately: the note recording WHY it was removed
    # is the most valuable line in the file and must not be tested away.
    src = (TOOLS / "induce_missed_ticks.py").read_text(encoding="utf-8")
    code = chr(10).join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    assert "aligned" not in code, "the alignment parameter came back"
    # and the explanatory comment must still be there
    assert "never aligns" in src


def test_the_admissible_window_sits_exactly_on_the_bound_not_inside_it():
    # There is no headroom left. That is why there is no range to tune.
    assert ind.worst_case_gap_milliseconds(ind.CADENCE_SECONDS) == (
        ind.GAP_ACCEPTANCE_BOUND_MILLISECONDS)


def test_bool_is_not_an_int_here():
    with pytest.raises(ind.InductionRefused, match="must be an int"):
        ind.check_window(True)


def test_expected_missed_ticks_is_stated_up_front():
    # One cadence always spans exactly one tick boundary.
    assert ind.expected_missed_ticks(60) == 1
    assert ind.expected_missed_ticks(59) == 0


# --- refusing to fabricate a scenario ----------------------------------------


def test_already_disabled_rule_is_refused_as_fictional():
    ev = _FakeEvents(state="DISABLED")
    with pytest.raises(ind.InductionRefused, match="fictional"):
        ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                   session_factory=factory(PREPROD, ev), sleep=lambda _s: None)


# --- the property that matters most ------------------------------------------


def test_happy_path_disables_then_re_enables():
    ev = _FakeEvents()
    rec = ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                     session_factory=factory(PREPROD, ev), sleep=lambda _s: None)
    assert rec["verdict"] == "MISSED_TICK_WINDOW_INDUCED_AND_SCHEDULE_RESTORED"
    # One cadence spans exactly one tick boundary -- all section 6 asks for,
    # and all the 180,000 ms gap bound leaves room for.
    assert rec["expected_missed_ticks"] == 1
    assert ev.state == "ENABLED"
    assert f"disable:{RULE}" in ev.calls and f"enable:{RULE}" in ev.calls


def test_schedule_is_re_enabled_even_when_the_wait_raises():
    ev = _FakeEvents()

    def boom(_s):
        raise RuntimeError("network died mid-window")

    with pytest.raises(RuntimeError, match="network died"):
        ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                   session_factory=factory(PREPROD, ev), sleep=boom)
    assert ev.state == "ENABLED", "a crash must never leave recovery disabled"
    assert f"enable:{RULE}" in ev.calls


def test_schedule_is_re_enabled_on_keyboard_interrupt():
    ev = _FakeEvents()

    def interrupt(_s):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                   session_factory=factory(PREPROD, ev), sleep=interrupt)
    assert ev.state == "ENABLED"


def test_failure_to_restore_is_raised_as_CRITICAL():
    class _Stuck(_FakeEvents):
        def enable_rule(self, Name):
            self.calls.append(f"enable:{Name}")  # pretends, stays DISABLED

    ev = _Stuck()
    with pytest.raises(ind.InductionRefused, match="CRITICAL"):
        ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                   session_factory=factory(PREPROD, ev), sleep=lambda _s: None)


def test_the_measurement_harness_does_not_import_this_tool():
    # Inducing a fault and measuring it must stay separate jobs; a harness that
    # could induce its own inputs would be measuring itself.
    harness = (TOOLS / "measure_guardian_timing_evidence.py").read_text(encoding="utf-8")
    assert "induce_missed_ticks" not in harness


def test_there_is_no_override_flag():
    source = (TOOLS / "induce_missed_ticks.py").read_text(encoding="utf-8")
    for bypass in ("--force", "--yes", "allow_production", "skip_guards"):
        assert bypass not in source
