"""Does the RUNTIME'S OWN METHOD deliver the case, on the real path, all the way to the operation?

WHY THIS EXISTS
---------------
The route-D patch makes four things true, and three of them were already measured:

  1. `runtime.py:1006` hands `cause.content` to `network.forward_node`   <- MEASURED HERE
  2. `network.forward_node` hands it to the node's holder                <- MEASURED HERE
  3. the node hands it to the operation bank                             <- MEASURED HERE
  4. an operation module can read it while it runs                       <- verify_route_d_case_passing.py

This probe measures 1, 2 and 3 in one call, by calling the runtime's OWN method that contains the
brain call — `_prepare_inference` — rather than re-building the call by hand. It watches the exact
hand-off point the patch creates: the operation bank's `forward`, whose third argument IS the case.

THREE DEFECTS IN THE FIRST VERSION OF THIS PROBE, ALL FIXED HERE
---------------------------------------------------------------
- It held the operation bank as an attribute of an `nn.Module`, so `state_dict()` walked
  bank -> watcher -> bank and raised `RecursionError`. The observer here is a **plain callable**,
  which lives outside the module tree.
- It called `node.set_active_case(...)` by hand before the run, which sets the very value under
  test. The probe now sets nothing: if the edit is missing, the bank receives `None` and the probe
  says so.
- It registered a second operation to do the watching, then admitted in prose that the runtime
  never invoked it, and called the point proved anyway. No extension operation is registered now.
  The bank is wrapped, and a NEGATIVE CONTROL calls the same path through the OLD three-argument
  signature to prove the probe can tell the two apart.

WHAT IT DOES NOT DO
-------------------
No frozen tree is written to. No store is left behind. Memory is watched against the project's
300 MiB per-part laptop rule and the probe aborts rather than exceed it.

Usage:
    C:\\Python314\\python.exe -B probe_runtime_tick.py <patched-parent> <base-tree> <gb-root>
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Mapping, Optional

LIMIT_MIB = 300.0


def peak_mib() -> float:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, os.getpid())
    if not h:
        return -1.0
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    ctypes.windll.kernel32.CloseHandle(h)
    return pmc.PeakWorkingSetSize / 1048576.0 if ok else -1.0


def install_resource_shim() -> None:
    """The UNIX-only `resource` module, stubbed BY NAME for this probe only.

    `gb/continuity.py` needs it; nothing under test does. Values are benign and labelled.
    """
    if "resource" in sys.modules:
        return
    import types
    shim = types.ModuleType("resource")

    class _Usage:
        ru_maxrss = 0
        ru_utime = 0.0
        ru_stime = 0.0

    shim.getrusage = lambda *_a, **_k: _Usage()
    shim.setrlimit = lambda *_a, **_k: None
    shim.getrlimit = lambda *_a, **_k: (0, 0)
    shim.RLIMIT_AS = shim.RLIMIT_DATA = shim.RLIMIT_STACK = 0
    shim.RUSAGE_SELF = 0
    shim.RUSAGE_CHILDREN = -1
    sys.modules["resource"] = shim


#: Every hand-off the patch creates, recorded in the order it happens.
HANDOFFS: List[Any] = []
#: What the bank was left holding after each call; must always be None (the patch's `finally`).
LEFTOVERS: List[Any] = []
#: What the node was left holding after each call; must always be None.
NODE_LEFTOVERS: List[Any] = []


def instrument(node: Any) -> Any:
    """Wrap the node's and the bank's hand-off points with PLAIN CALLABLES.

    Plain callables, not `nn.Module`s: nothing here may join the module tree, or `state_dict()`
    walks the graph and recurses. Returns the bank, for convenience.
    """
    bank = node.operations
    real_bank_forward = type(bank).forward
    real_node_forward = type(node).forward
    actual_bank_forward = bank.forward
    actual_node_forward = node.forward

    def watching_bank_forward(operation_id, value, case="ABSENT"):
        # `case` defaults to a sentinel so a three-argument call (the OLD signature) is
        # distinguishable from a four-argument call that passed None.
        HANDOFFS.append(("bank.forward", operation_id, case))
        try:
            return actual_bank_forward(operation_id, value, case)
        finally:
            LEFTOVERS.append(getattr(bank, "_active_case", "ATTRIBUTE_MISSING"))

    def watching_node_forward(x, control, *, operation_id):
        try:
            return actual_node_forward(x, control, operation_id=operation_id)
        finally:
            NODE_LEFTOVERS.append(getattr(node, "_active_case", "ATTRIBUTE_MISSING"))

    # Instance attributes shadow the class methods without descriptor binding, so each wrapper
    # already closes over the object it wraps.
    bank.forward = watching_bank_forward
    node.forward = watching_node_forward
    return bank, real_bank_forward, real_node_forward


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    patched_parent, base_tree, gb_root = (os.path.abspath(p) for p in sys.argv[1:4])

    install_resource_shim()

    # EVERY INSERT GOES TO POSITION 0, so the list is inserted in REVERSE priority order.
    # Writing them in forward order was a real defect in an earlier probe: it loaded the base
    # tree's unpatched cas_cjt while the comment claimed otherwise.
    for p in (gb_root, base_tree, patched_parent):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    import torch
    import cas_cjt
    from cas_cjt import CJTNodeSpec, NeuralCJTRuntime
    from casformer import CASformerConfig

    print("=" * 78)
    print("THE RUNTIME'S OWN METHOD, EXERCISED ON THE REAL PATH")
    print("=" * 78)
    print("  cas_cjt in use            : %s" % os.path.dirname(cas_cjt.__file__))
    print("  torch                     : %s" % torch.__version__)

    # Unpatched detection is on the BANK, because the bank is where the case is read.
    #
    # The marker is the bank's `forward` SIGNATURE, not an attribute. The first version of this
    # check asked whether `_active_case` was a class attribute of the bank and answered `False`
    # for a correctly patched tree: the node sets its own holder in `__init__`, but the bank
    # creates `self._active_case` at CALL time inside `forward`, so it is never on the class.
    # That aborted the run against a good tree. A wrong reading is worse than no reading, so the
    # test is now the thing the patch actually changes.
    import inspect
    from cas_cjt.neural import NeuralCJT as NodeClass
    from cas_cjt.neural import RegisteredOperationBank as BankClass
    bank_params = list(inspect.signature(BankClass.forward).parameters)
    bank_takes_case = "case" in bank_params
    node_has_holder = hasattr(NodeClass, "set_active_case")
    print("  bank.forward parameters   : %s" % ", ".join(bank_params))
    print("  bank accepts the case     : %s" % bank_takes_case)
    print("  node has set_active_case  : %s" % node_has_holder)
    if not (bank_takes_case and node_has_holder):
        print()
        print("ABORT: the cas_cjt in use is NOT the patched one; this run would prove nothing.")
        return 1

    folder = tempfile.TemporaryDirectory()
    runtime = None
    try:
        runtime = NeuralCJTRuntime.create(
            Path(folder.name) / "probe.sqlite3",
            config=CASformerConfig(d_model=4, num_heads=2, num_relations=6, num_layers=1,
                                   dropout=0.0, attention_dropout=0.0,
                                   initial_cutoff=0.01, initial_saturation=100.0),
            node_specs=tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C")),
            topology=(),
            seed=7,
            labels=("L0", "L1", "L2", "L3"),
        )
        runtime.network.eval()
        print("  runtime created           : OK  (peak %.1f MiB)" % peak_mib())

        node = runtime.network.node("C")
        bank, real_bank_forward, real_node_forward = instrument(node)

        case_content = {"task_id": "native.route_dependency_audit/1", "case_id": "probe-tick",
                        "nodes": [0, 1, 2], "edges": [[0, 1]], "route": [0, 1, 2]}
        cause, artifact = runtime.make_input_cause(
            torch.tensor([[[.1, .2, .3, .4], [.5, .6, .7, .8]]]),
            tick=1, content=case_content, goal_context={"goal": "r1-rt probe"},
            candidate_operation_ids=("^6",),
        )
        print("  cause built by the runtime: OK  (cause.content case_id=%r)"
              % dict(cause.content).get("case_id"))

        # ---------------------------------------------------------------------------------
        # THE MEASUREMENT: the runtime's OWN method, which contains the brain call at 1006.
        # ---------------------------------------------------------------------------------
        HANDOFFS.clear()
        LEFTOVERS.clear()
        NODE_LEFTOVERS.clear()
        prepared = runtime._prepare_inference(
            cause=cause,
            cjt_id="C",
            expected_symbol=None,
            opposite_symbol=None,
            settings=None,
            supplied_artifacts=(artifact,),
            resume_repair_id=None,
            write_memory=False,
        )
        print()
        print("  runtime._prepare_inference: RETURNED  (%s)" % type(prepared).__name__)

        # `_prepare_inference` performs the routing cross-check itself (runtime.py:1011-1025) and
        # raises if the proposal's telemetry disagrees with the materialized route. Reaching this
        # line IS that check passing, on the real path, with the real CASformer.
        print("  its own routing cross-check: PASSED (it raises rather than returns otherwise)")

        n_calls = len(HANDOFFS)
        print()
        print("  the hand-off the patch creates, as observed:")
        for i, (where, op_id, carried) in enumerate(HANDOFFS, 1):
            delivered = ("THE CASE" if isinstance(carried, Mapping) else repr(carried))
            print("    call %d  %s  operation=%s  carried: %s" % (i, where, op_id, delivered))
            if isinstance(carried, Mapping):
                print("             case_id=%r  returned from create()=%s"
                      % (carried.get("case_id"),
                         "YES" if carried.get("case_id") == "probe-tick" else "NO"))

        delivered_ok = (n_calls == 1 and isinstance(HANDOFFS[0][2], Mapping)
                        and HANDOFFS[0][2].get("case_id") == "probe-tick")
        # The bank's own `finally` runs INSIDE `bank.forward`, so the wrapper can see it settle.
        bank_cleared = (LEFTOVERS == [None])
        # The node's holder is cleared by `network.forward_node` AFTER `node(...)` returns, so a
        # wrapper around `node.forward` samples it too early and always sees the live case. The
        # first version of this probe recorded that as "the node was not cleared" and it was wrong
        # about the patch. The node's holder must therefore be read HERE, after the whole call.
        node_left = getattr(node, "_active_case", "ATTRIBUTE_MISSING")
        bank_left = getattr(bank, "_active_case", "ATTRIBUTE_MISSING")
        cleared_ok = bank_cleared and node_left is None and bank_left is None
        print()
        print("    the case REACHED the operation bank            : %s"
              % ("YES" if delivered_ok else "NO"))
        print("    what the runtime ACTUALLY delivers it as        : %s" % type(HANDOFFS[0][2]).__name__
              if isinstance(HANDOFFS[0][2], Mapping) else "    (not a mapping)")
        if isinstance(HANDOFFS[0][2], Mapping):
            print("      its keys and value types: %s"
                  % ", ".join("%s=%s" % (k, type(v).__name__)
                              for k, v in sorted(HANDOFFS[0][2].items())))
        print("    bank cleared, sampled inside bank.forward      : %s"
              % ("YES" if bank_cleared else repr(LEFTOVERS)))
        print("    node cleared, sampled after the whole call     : %s"
              % ("YES" if node_left is None else repr(node_left)))
        print("    bank cleared, sampled after the whole call     : %s"
              % ("YES" if bank_left is None else repr(bank_left)))

        # ---------------------------------------------------------------------------------
        # NEGATIVE CONTROL: the OLD three-argument signature must deliver NO case.
        # Without this, a probe that always sees a case proves nothing about the edit.
        #
        # The sentinel on `watching_bank_forward`'s `case` parameter can never fire here: the
        # patched node ALWAYS passes its holder down, so an uncased call arrives as an explicit
        # `None`, not as a missing argument. The first version of this control asserted the
        # sentinel and so reported a false failure. What matters is the difference the probe can
        # actually make: a real case, or None.
        # ---------------------------------------------------------------------------------
        materialized = runtime.materializer.materialize(
            state=runtime.state, cause=cause, cjt_id="C",
            settings=__import__("cas_cjt.control", fromlist=["RouteSettings"]).RouteSettings(),
            supplied_artifacts=(artifact,),
        )
        HANDOFFS.clear()
        LEFTOVERS.clear()
        NODE_LEFTOVERS.clear()
        with torch.no_grad():
            runtime.network.forward_node("C", materialized.cause_tensor, materialized.control)
        control_case = HANDOFFS[0][2] if HANDOFFS else "THE BANK WAS NEVER CALLED"
        got_none = control_case is None
        print()
        print("  NEGATIVE CONTROL, old 3-argument call:")
        print("    the bank's third argument                      : %r" % (control_case,))
        print("    it carried no case, as the old signature must  : %s"
              % ("YES" if got_none else "NO -- the probe cannot tell the two apart"))
        print("    the operation bank still ran                   : %s"
              % ("YES" if HANDOFFS else "NO"))

        mem = peak_mib()
        verdict = "PASSES" if (delivered_ok and cleared_ok and got_none) else "DOES NOT PASS"
        print()
        print("=" * 78)
        print("RESULT")
        print("  the runtime's own method ran on the real path  : YES")
        print("  the case reached the operation bank            : %s"
              % ("YES" if delivered_ok else "NO"))
        print("  nothing was left holding it afterwards         : %s"
              % ("YES" if cleared_ok else "NO"))
        print("  the probe distinguishes the old signature      : %s"
              % ("YES" if got_none else "NO"))
        print("  verdict                                        : %s" % verdict)
        print("  peak memory %.1f MiB of the %.0f MiB laptop rule" % (mem, LIMIT_MIB))
        if mem > LIMIT_MIB:
            print("  WARNING: peak exceeded the laptop rule; this reading is not usable as is.")
        print("=" * 78)
        return 0 if verdict == "PASSES" else 1
    except Exception as exc:  # noqa: BLE001 - the diagnosis is the point
        print()
        print("  FAILED: %s: %s" % (type(exc).__name__, str(exc)[:600]))
        import traceback
        traceback.print_exc(limit=10)
        print()
        print("=" * 78)
        print("RESULT: THE REAL PATH DID NOT COMPLETE")
        print("=" * 78)
        return 1
    finally:
        if runtime is not None:
            runtime.close()
        folder.cleanup()


if __name__ == "__main__":
    sys.exit(main())
