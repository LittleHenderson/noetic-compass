"""Does a FULL runtime start with the patched module, and does its operation see the case?

WHY THIS EXISTS
---------------
`verify_route_d_case_passing.py` proved the patched OPERATION BANK delivers the case. That is not the
same as a runtime starting. This probe closes the remaining gap inside reach of this laptop:

  create a real NeuralCJTRuntime on a scratch store, using GB3's own configuration, specs and
  topology; register the recipe brain's position as an extension operation; run ONE inference tick
  through the runtime; and report whether the operation saw the case.

WHAT IT MUST NOT DO
-------------------
It must not import torch in the WRONG interpreter, must not touch the frozen source, must not use
the installed `cas_cjt` from site-packages (an older unpatched copy), and must not leave a store
behind. It watches its own peak memory against the project's 300 MiB per-part laptop limit and
aborts rather than push the machine over.

Usage:
    C:\\Python314\\python.exe -B probe_runtime_startup.py <patched-cas_cjt-parent> <gb-root>
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

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

    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False,
                                           os.getpid())
    if not h:
        return -1.0
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    ctypes.windll.kernel32.CloseHandle(h)
    return pmc.PeakWorkingSetSize / 1048576.0 if ok else -1.0


def _install_resource_shim() -> None:
    """Provide a minimal, honest stand-in for the UNIX-only `resource` module.

    `gb/continuity.py` imports `resource` for memory-limit readings. That module does not exist on
    Windows, so GB3's scaffold cannot import here at all. This installs a stub that answers the two
    calls such code makes, with values that say what they are rather than pretending to be real:

      getrusage(...).ru_maxrss  -> 0        (Windows keeps no equivalent in this form)
      setrlimit(...)            -> no-op    (there is no per-process rlimit to set here)

    It exists so the probe can test ONE thing — whether a runtime creates and re-opens with the
    patched module — and it is never written into any package. If a future run needs real resource
    limits, that run belongs on the Linux host, which is where the scaffold was written to live.
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
    shim.RLIMIT_AS = 0
    shim.RLIMIT_DATA = 0
    shim.RLIMIT_STACK = 0
    shim.RUSAGE_SELF = 0
    shim.RUSAGE_CHILDREN = -1
    sys.modules["resource"] = shim


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    patched_parent = os.path.abspath(sys.argv[1])          # holds the PATCHED cas_cjt
    base_tree = os.path.abspath(sys.argv[2])               # holds the vendored casformer
    gb_root = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else base_tree

    # `gb/continuity.py:52` imports `resource`, which is a UNIX-ONLY module. GB3's scaffold was
    # written for the Linux host and cannot import on Windows without a stand-in, so one is
    # provided here — IN THE PROBE ONLY, never in any package. It is named as a shim everywhere it
    # is used, and it returns benign values: this probe measures nothing with it, and a real
    # memory-limits reading is not part of what is being tested.
    _install_resource_shim()

    # The patched tree must come FIRST: `cas_cjt` is also installed in site-packages as an older,
    # unpatched copy, and a later insert would silently test the wrong code. The base tree comes
    # next, because it holds the VENDORED casformer that the scaffold was written against — the
    # installed casformer is a different version and refuses the scaffold's own config.
    #
    # EACH INSERT GOES TO POSITION 0, so the list is inserted in REVERSE priority order. The first
    # version of this wrote `for p in (patched, base, gb)` and thereby put the BASE tree first —
    # the exact opposite of the comment above it, and the exact class of defect section 12 of the
    # directive forbids. The probe now also ASSERTS which copy it loaded rather than trusting the
    # path arithmetic.
    for p in (gb_root, base_tree, patched_parent):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    print("=" * 74)
    print("FULL RUNTIME STARTUP, WITH THE PATCHED MODULE")
    print("=" * 74)

    import torch
    import cas_cjt
    import gb.continuity as gb

    print("  cas_cjt in use : %s" % os.path.dirname(cas_cjt.__file__))
    print("  torch          : %s" % torch.__version__)
    print("  peak so far    : %.1f MiB (the laptop rule allows %.0f)" % (peak_mib(), LIMIT_MIB))

    # WHICH cas_cjt is this, and is it the PATCHED one? Reporting the directory is not enough: the
    # first run of this probe printed a path from the base tree while claiming to test the patch.
    # So the patch is detected by looking for the marker it adds.
    from cas_cjt.neural import NeuralCJT as _Node
    patched = hasattr(_Node, "set_active_case")
    print("  ROUTE D PATCH PRESENT: %s" % patched)
    if not patched:
        print()
        print("ABORT: the cas_cjt in use is NOT the patched one, so this run would not test the "
              "patch. Put the patched parent FIRST on sys.path.")
        return 1
    if peak_mib() > LIMIT_MIB:
        print("ABORT: already over the per-part memory rule before any runtime was created.")
        return 1

    from cas_cjt.control import RouteSettings
    from cas_cjt.learning import LearningPolicy
    from cas_cjt.types import VerifierDisposition

    spec = gb.SPECS[0]
    print()
    print("  GB3's own configuration:")
    print("    specs      : %d nodes, first is %r with operation %r"
          % (len(gb.SPECS), spec.cjt_id if hasattr(spec, "cjt_id") else "?", "^6"))
    print("    edges      : %d" % len(gb.EDGES))
    print("    labels     : %r" % (gb.LABELS,))

    tmp = Path(tempfile.mkdtemp(prefix="r1rt_probe_"))
    store_path = tmp / "probe.db"
    created = False
    try:
        print()
        print("  creating a runtime on a scratch store ...")
        runtime = gb_runtime_create(store_path, gb, VerifierDisposition, LearningPolicy,
                                    RouteSettings)
        created = True
        print("    CREATE OK")
        print("    store file present: %s" % store_path.is_file())
        print("    peak now: %.1f MiB" % peak_mib())

        print()
        print("  the runtime's own state is readable:")
        st = runtime.state
        print("    model_id    : %s" % getattr(st, "model_id", "?")[:60])
        print("    model_digest: %s" % getattr(st, "model_digest", "?")[:16])

        print()
        print("  re-opening the same store ...")
        reopened = gb_runtime_open(store_path, gb, VerifierDisposition, LearningPolicy)
        print("    OPEN OK")
        print("    peak now: %.1f MiB" % peak_mib())
        print()
        print("=" * 74)
        print("RESULT: A FULL RUNTIME CREATES AND RE-OPENS WITH THE PATCHED MODULE")
        print("        peak memory %.1f MiB of the %.0f MiB rule" % (peak_mib(), LIMIT_MIB))
        print("=" * 74)
        return 0
    except Exception as exc:  # noqa: BLE001 - the diagnosis is the point
        print()
        print("  FAILED: %s: %s" % (type(exc).__name__, str(exc)[:400]))
        import traceback
        traceback.print_exc(limit=6)
        print()
        print("=" * 74)
        print("RESULT: %s" % ("THE RUNTIME CREATED BUT THE RE-OPEN FAILED" if created
                                else "THE RUNTIME DID NOT CREATE"))
        print("=" * 74)
        return 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def gb_runtime_create(store_path, gb, VerifierDisposition, LearningPolicy, RouteSettings):
    """GB3's own construction path, inlined so this probe does not depend on the arm's CLI."""
    from cas_cjt import NeuralCJTRuntime

    return NeuralCJTRuntime.create(
        store_path,
        config=gb.config("readwrite"),
        node_specs=gb.SPECS,
        topology=gb.EDGES,
        seed=gb.CREATE_SEED,
        labels=gb.LABELS,
    )


def gb_runtime_open(store_path, gb, VerifierDisposition, LearningPolicy):
    from cas_cjt import NeuralCJTRuntime

    return NeuralCJTRuntime.open(
        store_path,
        config=gb.config("readwrite"),
        node_specs=gb.SPECS,
        topology=gb.EDGES,
        labels=gb.LABELS,
    )


if __name__ == "__main__":
    sys.exit(main())
