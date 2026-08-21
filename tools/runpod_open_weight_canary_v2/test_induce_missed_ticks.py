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


def test_window_range_is_bounded_on_both_sides():
    ind.check_window(ind.MIN_DISABLE_SECONDS)
    ind.check_window(ind.MAX_DISABLE_SECONDS)


@pytest.mark.parametrize("bad", [0, 59, 121, 240, 600])
def test_windows_outside_the_range_are_refused(bad):
    with pytest.raises(ind.InductionRefused, match="window must be between"):
        ind.check_window(bad)


# --- what THREE real live runs proved ----------------------------------------
#
#     window 240 s -> gap 311,788 ms   over the bound
#     window 120 s -> gap 210,900 ms   over the bound
#     window  60 s -> gap  94,900 ms   in bound, but ZERO missed ticks
#
# The admissible band is [120_000, 180_000] ms -- 60 s wide -- while measured
# overhead varied by ~56 s. No fixed window can guarantee it.


@pytest.mark.parametrize("gap_ms,expected", [
    (311788, "TOO_LONG_EXCEEDS_ACCEPTANCE_BOUND"),   # live run 1
    (210900, "TOO_LONG_EXCEEDS_ACCEPTANCE_BOUND"),   # live run 2
    (94900,  "TOO_SHORT_NO_MISSED_TICK"),            # live run 3
    (120000, "IN_BAND"),
    (180000, "IN_BAND"),
    (119999, "TOO_SHORT_NO_MISSED_TICK"),
    (180001, "TOO_LONG_EXCEEDS_ACCEPTANCE_BOUND"),
])
def test_every_real_observed_gap_is_classified_correctly(gap_ms, expected):
    assert ind.classify_induced_gap(gap_ms) == expected


def test_the_admissible_band_matches_the_harness_rules():
    low, high = ind.ADMISSIBLE_GAP_BAND_MILLISECONDS
    # low: the smallest gap that registers >=1 missed tick under (gap//cadence)-1
    assert low == 2 * ind.CADENCE_SECONDS * 1000
    # high: the acceptance bound itself
    assert high == ind.GAP_ACCEPTANCE_BOUND_MILLISECONDS


# --- the defect that survived three live runs --------------------------------


def test_verdict_does_NOT_claim_the_induction_succeeded():
    ev = _FakeEvents()
    rec = ind.induce(account_id=PREPROD, rule_name=RULE, disable_seconds=60,
                     session_factory=factory(PREPROD, ev), sleep=lambda _s: None)
    # The tool cannot see the resulting gap, so it must not claim one was induced.
    assert rec["verdict"] == "SCHEDULE_DISABLED_AND_RESTORED_OUTCOME_UNVERIFIED"
    assert "INDUCED" not in rec["verdict"].replace("_OUTCOME_UNVERIFIED", "")
    assert rec["admissible_gap_band_milliseconds"] == [120000, 180000]
    assert "must be repeated, not reinterpreted" in rec["next_step"]


def test_the_old_overclaiming_verdict_string_is_gone():
    src = (TOOLS / "induce_missed_ticks.py").read_text(encoding="utf-8")
    code = chr(10).join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    assert "MISSED_TICK_WINDOW_INDUCED_AND_SCHEDULE_RESTORED" not in code


def test_bool_is_not_an_int_here():
    with pytest.raises(ind.InductionRefused, match="must be an int"):
        ind.check_window(True)


def test_expected_missed_ticks_is_only_an_expectation():
    # Named honestly: three live runs showed the expectation is not the outcome.
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
    assert rec["verdict"] == "SCHEDULE_DISABLED_AND_RESTORED_OUTCOME_UNVERIFIED"
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
