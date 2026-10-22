"""gate.py -- the design's light-run rule (DESIGN_V73_A11.md section 6: run on the laptop only if at least 500 MB of physical
memory is free at the start; otherwise stop and report the blocker, the owner's AWS order of 2026-09-23). Every laptop step
of the fix round runs through this gate. It reads free physical memory (Windows GlobalMemoryStatusEx), waits up to
--wait seconds (rechecking every 5 s, nothing runs meanwhile) if below the floor, logs one JSON line per reading to --memlog,
then runs the command with its stdout+stderr written to --out, and logs the exit code and the free memory after.

    python -X utf8 -B -I gate.py --label L --memlog M.jsonl --out O.log [--cwd D] [--env K=V ...] -- cmd ...

Exit code: the command's, or 3 when the floor was not met (the command is NOT run). Standard library only.
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import time

FLOOR_MIB = 500


def free_mib():
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    ms = MS()
    ms.dwLength = ctypes.sizeof(MS)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
        return round(ms.ullAvailPhys / (1024 * 1024), 1)
    return None


def log(path, row):
    row = dict(row, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--memlog", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--unset-helm-env", action="store_true")
    ap.add_argument("--wait", type=int, default=300)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    t0 = time.time()
    first = f = free_mib()
    while f is not None and f < FLOOR_MIB and time.time() - t0 < a.wait:
        time.sleep(5)
        f = free_mib()
    ok = f is not None and f >= FLOOR_MIB
    log(a.memlog, {"label": a.label, "when": "before", "free_mib_first": first, "free_mib": f,
                   "waited_s": round(time.time() - t0, 1), "floor_mib": FLOOR_MIB, "floor_met": ok})
    if not ok:
        print(f"GATE STOP: free physical memory {f} MiB < {FLOOR_MIB} MiB at '{a.label}' (owner's AWS order: no local run)")
        return 3
    env = dict(os.environ)
    if a.unset_helm_env:
        env = {k: v for k, v in env.items() if not k.upper().startswith("HELM_")}
    for kv in a.env:
        k, v = kv.split("=", 1)
        env[k] = v
    t1 = time.time()
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        r = subprocess.run(cmd, cwd=a.cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=a.timeout)
    log(a.memlog, {"label": a.label, "when": "after", "exit": r.returncode, "seconds": round(time.time() - t1, 3),
                   "free_mib": free_mib()})
    print(f"[gate] {a.label}: free {f} MiB before, exit {r.returncode}, {round(time.time() - t1, 1)} s; log {a.out}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
