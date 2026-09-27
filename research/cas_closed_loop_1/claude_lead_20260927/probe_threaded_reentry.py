"""Claude probe (scratch worktree only): is the CPython call-event meter per-thread?

Same attacker class as the in-scope test
test_internal_reentry_that_clears_meter_never_publishes_a_count (in-memory
monkeypatch of CompoundMachine._execute), but the second, unauthorized
advance runs on a new thread. sys.setprofile only hooks the calling thread.
"""
import threading

import pytest

from cncm.compound_engine import CompoundMachine
from cncm.compound_model import create_problem
from cncm.compound_profile import load_compound_profile
from research.cas_closed_loop_1.native_step_adapter import execute_grant, grant_for, verify_receipt


@pytest.fixture
def machine():
    machine = CompoundMachine(load_compound_profile(), trusted_ingress=())
    machine.start(create_problem({"a": "2", "b": "3", "c": "5", "d": "7", "e": "35"}))
    return machine


def test_probe_threaded_reentry_is_counted_or_refused(machine, monkeypatch):
    original_execute = CompoundMachine._execute
    original_advance = CompoundMachine.advance
    reentered = []
    thread_error = []

    def threaded_reentrant_execute(self, *args, **kwargs):
        result = original_execute(self, *args, **kwargs)
        if not reentered:
            reentered.append(True)
            def second_entry():
                try:
                    original_advance(self, allow_acquisition=True)
                except BaseException as error:  # record, never hide
                    thread_error.append(type(error).__name__ + ": " + str(error))
            worker = threading.Thread(target=second_entry)
            worker.start()
            worker.join()
        return result

    monkeypatch.setattr(CompoundMachine, "_execute", threaded_reentrant_execute)
    events_before = len(machine.coordinator.trace.events)
    receipt = execute_grant(machine, grant_for(machine, calls=1, allow_acquisition=True))
    events_after = len(machine.coordinator.trace.events)
    print("PROBE reentered:", reentered, "thread_error:", thread_error)
    print("PROBE receipt I_allocated/I_executed/I_attempted:", receipt["I_allocated"], receipt["I_executed"], receipt["I_attempted"])
    print("PROBE native_event_count:", receipt["native_event_count"], "trace grew by:", events_after - events_before)
    print("PROBE verify_receipt:", verify_receipt(receipt), "execution_status:", receipt["execution_status"])
    # The adapter's stated rule: any unexpected re-entry invalidates the observation.
    # If this assertion FAILS, the second real entry went uncounted and unrefused.
    assert receipt["I_executed"] == 2 or receipt["native_event_count"] == 1, "SECOND_ENTRY_UNCOUNTED_AND_UNREFUSED"
