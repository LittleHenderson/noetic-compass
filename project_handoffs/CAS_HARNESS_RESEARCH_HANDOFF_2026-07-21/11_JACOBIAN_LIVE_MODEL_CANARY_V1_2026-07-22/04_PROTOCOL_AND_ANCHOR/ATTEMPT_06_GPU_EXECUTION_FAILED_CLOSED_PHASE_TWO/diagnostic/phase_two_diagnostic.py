"""NON-OFFICIAL bounded diagnostic: reproduce the JLCV1 seccomp two-phase
guard sequence to surface the exact exception raised inside
install_phase_two_guard on the CUDA 13.0 / torch 2.12 stack.

This is a SHADOW diagnostic. It writes nothing into any official attempt
root, produces no receipt, and makes no scientific or product claim. It
installs real seccomp filters in ITS OWN process only, then reports where
phase two fails.
"""

from __future__ import annotations

import faulthandler
import json
import os
import sys
import traceback
from pathlib import Path

WORKER = Path(
    "/workspace/cas-jlcv1-official-29551624-f3e3adad/"
    "repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
)
sys.path.insert(0, str(WORKER))
faulthandler.enable()

from research import jacobian_lens_network_guard as guard  # noqa: E402

EXPECTED_LIBSECCOMP = (
    "d60148325d84cab666b226676c5009a61eea24f3902598829fe714da87ef3587"
)

report: dict[str, object] = {"diagnostic": "PHASE_TWO_NON_OFFICIAL", "stage": None}


def _fd_inventory(label: str) -> None:
    root = Path("/proc/self/fd")
    socks, iou, other = [], [], []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        try:
            tgt = os.readlink(entry)
        except OSError:
            continue
        if tgt.startswith("socket:["):
            socks.append((entry.name, tgt))
        elif "io_uring" in tgt:
            iou.append((entry.name, tgt))
        elif tgt.startswith("anon_inode") or "cuda" in tgt.lower():
            other.append((entry.name, tgt))
    print(f"[fd:{label}] sockets={socks} io_uring={iou} anon/cuda={other[:12]}")


try:
    report["stage"] = "PHASE_ONE_INSTALL"
    phase_one = guard.install_phase_one_guard(
        expected_libseccomp_sha256=EXPECTED_LIBSECCOMP
    )
    print("[phase-one] installed OK; filter_count=",
          phase_one.seccomp_filter_count)

    report["stage"] = "IMPORT_TORCH"
    import torch  # noqa: E402
    print("[torch]", torch.__version__)

    report["stage"] = "CUDA_BOOTSTRAP"
    bootstrap = guard.initialize_cuda_bootstrap(torch, device_index=0)
    print("[cuda] bootstrap sum=", bootstrap.observation.initial_sum,
          "device_count=", bootstrap.observation.device_count)
    _fd_inventory("post-cuda")

    report["stage"] = "IDENTIFY_UVM_LISTENER"
    uvm = guard.identify_sole_cuda_uvm_listener()
    print("[uvm] fd=", uvm.descriptor, "name=", uvm.abstract_name)

    report["stage"] = "PHASE_TWO_INSTALL"
    phase_two = guard.install_phase_two_guard(
        phase_one_observation=phase_one,
        uvm_listener=uvm,
        expected_libseccomp_sha256=phase_one.libseccomp_sha256,
    )
    print("[phase-two] installed OK; filter_count=",
          phase_two.seccomp_filter_count)
    report["stage"] = "COMPLETE"
    report["result"] = "PHASE_TWO_UNEXPECTEDLY_PASSED_IN_DIAGNOSTIC"
except BaseException as exc:  # noqa: BLE001 - diagnostic must surface everything
    report["result"] = "FAILED"
    report["exception_type"] = type(exc).__name__
    report["exception_str"] = str(exc)
    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        report["cause_type"] = type(cause).__name__
        report["cause_str"] = str(cause)
    print("=== DIAGNOSTIC TRACEBACK ===", file=sys.stderr)
    traceback.print_exc()
    try:
        _fd_inventory("at-failure")
    except Exception:  # noqa: BLE001
        pass

print("=== DIAGNOSTIC REPORT ===")
print(json.dumps(report, sort_keys=True))
