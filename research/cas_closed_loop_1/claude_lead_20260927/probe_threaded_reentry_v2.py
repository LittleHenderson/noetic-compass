"""Corrected probe (v2): direct host-entry proof; refusal is the ONLY pass.

Attacker class: the same one the adapter's own in-scope test uses
(test_internal_reentry_that_clears_meter_never_publishes_a_count): an
in-memory monkeypatch of CompoundMachine._execute. No interpreter hook is
installed, replaced or cleared by this probe, so it stays inside the trust
model HARNESS_SPEC.md states ("not an isolation boundary against arbitrary
Python code that changes interpreter hooks").

Direct proof of entry: the pinned CompoundMachine.advance calls _execute at
most once per entry. The patched _execute records the identity of its caller
frame when that frame runs the pinned advance code object on this machine.
Each distinct (thread, frame) pair is one real host entry. Two native events
are NOT used as proof of two host calls.

Pass condition (the only one): when the probe directly observed more than
one host entry for a grant of one, execute_grant must raise
InvalidNativeObservation and return no receipt. A returned receipt with
I_executed == 1 is a false measurement; a receipt with I_executed == 2 is a
violated grant. Both fail. If a hardened adapter prevents the second entry
before it happens, the probe records that too, and still requires refusal
of the observation window in which a foreign thread attempted entry.
"""
import sys
import threading

import pytest

from cncm.compound_engine import CompoundMachine
from cncm.compound_model import create_problem
from cncm.compound_profile import load_compound_profile
from research.cas_closed_loop_1.native_step_adapter import (
    InvalidNativeObservation, execute_grant, grant_for, verify_receipt)

_ADVANCE_CODE = CompoundMachine.advance.__code__


@pytest.fixture
def machine():
    machine = CompoundMachine(load_compound_profile(), trusted_ingress=())
    machine.start(create_problem({"a": "2", "b": "3", "c": "5", "d": "7", "e": "35"}))
    return machine


def test_probe_v2_grant_of_one_never_yields_receipt_after_second_host_entry(machine, monkeypatch):
    original_execute = CompoundMachine._execute
    original_advance = CompoundMachine.advance
    direct_entries = []      # (thread_ident, id(advance frame)) per real entry into pinned advance
    attempted_on_thread = []  # the foreign thread's attempt and its outcome
    reentered = []

    def entering_execute(self, *args, **kwargs):
        caller = sys._getframe(1)
        if caller.f_code is _ADVANCE_CODE and caller.f_locals.get("self") is machine:
            key = (threading.get_ident(), id(caller))
            if key not in direct_entries:
                direct_entries.append(key)
        result = original_execute(self, *args, **kwargs)
        if not reentered:
            reentered.append(True)
            def second_entry():
                attempted_on_thread.append("ATTEMPTED")
                try:
                    original_advance(self, allow_acquisition=True)
                    attempted_on_thread.append("RETURNED")
                except BaseException as error:  # record, never hide
                    attempted_on_thread.append("RAISED:" + type(error).__name__)
            worker = threading.Thread(target=second_entry, name="probe-foreign-entry")
            worker.start()
            worker.join()
        return result

    monkeypatch.setattr(CompoundMachine, "_execute", entering_execute)
    events_before = len(machine.coordinator.trace.events)
    outcome = {"receipt": None, "error": None}
    try:
        outcome["receipt"] = execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True))
    except InvalidNativeObservation as error:
        outcome["error"] = error
    events_after = len(machine.coordinator.trace.events)
    threads = {key[0] for key in direct_entries}
    print("PROBE2 direct_entries:", len(direct_entries), "distinct threads:", len(threads))
    print("PROBE2 foreign thread:", attempted_on_thread)
    print("PROBE2 trace grew by:", events_after - events_before, "(not used as proof of entries)")
    if outcome["receipt"] is not None:
        r = outcome["receipt"]
        print("PROBE2 RECEIPT RETURNED: I_allocated/I_executed/I_attempted:", r["I_allocated"], r["I_executed"], r["I_attempted"],
              "verify_receipt:", verify_receipt(r))
    else:
        print("PROBE2 refused:", type(outcome["error"]).__name__, str(outcome["error"]),
              "measurement_status:", getattr(outcome["error"], "measurement_status", None))
    # A foreign-thread entry attempt happened inside the window in every case.
    assert attempted_on_thread and attempted_on_thread[0] == "ATTEMPTED"
    # The only acceptable outcome: no usable receipt for this window.
    assert outcome["receipt"] is None, (
        "GRANT_OF_ONE_PRODUCED_A_RECEIPT_WITH_%d_DIRECT_ENTRIES_ON_%d_THREADS" % (len(direct_entries), len(threads)))
    assert isinstance(outcome["error"], InvalidNativeObservation)
    assert outcome["error"].measurement_status == "INVALID" and not hasattr(outcome["error"], "receipt")
