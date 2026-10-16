"""The process boundary, measured: does it work, and what does it cost per tick?

WHY THIS EXISTS
---------------
This is the last unknown from appendix E section 7. Items 1, 2 and 4 were answered in appendix G; item
3 was "the per-tick cost of a process boundary". A cost that is guessed is not a cost, and the envelope
cannot be re-priced without it.

WHAT IT MEASURES
----------------
1. The worker starts, has `rb` imported, and has **never** had torch or numpy in `sys.modules`.
2. Answers cross the boundary correctly: a set of known cases with answers computed here, checked
   against what comes back.
3. A NEGATIVE CONTROL: a case the worker must get right and a case it must refuse. A boundary that
   agrees with everything proves nothing.
4. The cost per tick over many ticks, reported as min, median, mean and max, with the first call
   reported separately because it pays for the brain's first argument of the minimum and for caches.

WHAT IT DOES NOT DO
-------------------
It does not touch the runtime, torch, any frozen tree, or any store. It never imports torch itself, so
it can run on the same laptop without competing with a runtime process for memory.

Usage:
    C:\\Python314\\python.exe -B probe_process_boundary.py <v3-package-root> [ticks]
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain_worker.py")
LABELS = tuple("FIRST_UNSUPPORTED_LEG_%d" % i for i in range(7)) + ("ALL_LEGS_PRESENT",)

#: (route, edges, the answer the runtime's own oracle would give, why this case is here)
CASES = [
    ([0, 1, 2], [[0, 1], [1, 2]], "ALL_LEGS_PRESENT", "every leg present"),
    ([0, 1, 2], [[0, 1]], "FIRST_UNSUPPORTED_LEG_1", "the second leg is missing"),
    ([0, 1, 2], [[1, 2]], "FIRST_UNSUPPORTED_LEG_0", "the first leg is missing"),
    ([0, 1, 2], [], "FIRST_UNSUPPORTED_LEG_0", "no legs at all: the FIRST missing one"),
    ([3, 1, 4, 1 % 8], [[3, 1]], "FIRST_UNSUPPORTED_LEG_1", "a longer route"),
    ([0, 1, 2, 3, 4, 5, 6, 7], [[0, 1], [1, 2], [2, 3]], "FIRST_UNSUPPORTED_LEG_3",
     "a seven-leg route, the longest the task has"),
    ([0, 1, 2, 3, 4, 5, 6, 7],
     [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]], "ALL_LEGS_PRESENT",
     "seven legs, all present, which is the case the constant spare cell decides"),
]


def expected(route, edges):
    """The runtime's rule, computed here so the check does not lean on the worker."""
    pairs = {tuple(e) for e in edges}
    for leg, pair in enumerate(zip(route, route[1:])):
        if pair not in pairs:
            return LABELS[leg]
    return LABELS[-1]


class Boundary:
    """One long-lived worker, JSON lines in and out."""

    def __init__(self, v3: str) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # No PYTHONPATH: the worker is given its package root as an argument, so a stray path on the
        # parent's environment cannot smuggle a torch import in.
        env.pop("PYTHONPATH", None)
        self.proc = subprocess.Popen(
            [sys.executable, "-B", WORKER, v3],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", env=env, bufsize=1)
        self.hello = self._read()

    def _read(self):
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError("the worker said nothing. stderr: %s" % err[-400:])
        return json.loads(line)

    def ask(self, route, edges):
        self.proc.stdin.write(json.dumps({"route": list(route), "edges": [list(e) for e in edges]})
                              + "\n")
        self.proc.stdin.flush()
        return self._read()

    def close(self):
        try:
            self.proc.stdin.write('{"type":"stop"}\n')
            self.proc.stdin.flush()
            self.proc.wait(timeout=15)
        except Exception:
            self.proc.kill()
        finally:
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                try:
                    stream.close()
                except Exception:
                    pass


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    v3 = os.path.abspath(sys.argv[1])
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    if not os.path.isdir(os.path.join(v3, "rb")):
        print("REFUSED: no rb package under %s" % v3)
        return 1

    print("=" * 78)
    print("THE PROCESS BOUNDARY: DOES IT WORK, AND WHAT DOES IT COST PER TICK?")
    print("=" * 78)
    print("  the worker's own report on startup:")
    boundary = Boundary(v3)
    hello = boundary.hello
    print("    %s" % json.dumps(hello, sort_keys=True))
    print()

    ok_torch = bool(hello.get("torch_absent"))
    ok_blocker = bool((hello.get("blocker") or {}).get("blocker_installed"))
    print("  it has never held torch or numpy        : %s" % ("YES" if ok_torch else "NO"))
    print("  the sealed package's blocker is installed: %s" % ("YES" if ok_blocker else "NO"))

    # ---- correctness across the boundary
    print()
    print("  the answers that crossed the boundary:")
    wrong = 0
    for route, edges, want, why in CASES:
        got = boundary.ask(route, edges)
        agree = got.get("answer") == want
        wrong += 0 if agree else 1
        print("    %-46s -> %-26s %s" % (why, got.get("answer"),
                                         "OK" if agree else "WRONG, expected %s" % want))
        if not agree:
            print("        full reply: %s" % json.dumps(got, sort_keys=True))

    # ---- negative control: the worker must REFUSE a malformed request, not answer it
    print()
    print("  NEGATIVE CONTROL, a request the worker must refuse:")
    boundary.proc.stdin.write(json.dumps({"route": [0], "edges": []}) + "\n")
    boundary.proc.stdin.flush()
    refused = boundary._read()
    is_error = refused.get("type") == "error"
    print("    a one-node route (no legs at all) -> %s" % json.dumps(refused, sort_keys=True))
    print("    it refused rather than answering      : %s" % ("YES" if is_error else "NO"))

    # ---- and it must still work afterwards, i.e. a refusal does not break the stream
    after = boundary.ask([0, 1], [[0, 1]])
    still_ok = after.get("answer") == "ALL_LEGS_PRESENT"
    print("    it still answers after refusing       : %s" % ("YES" if still_ok else "NO"))

    # ---- cost per tick
    print()
    print("  cost per tick over %d ticks:" % ticks)
    route, edges = [0, 1, 2, 3, 4, 5, 6, 7], [[0, 1], [2, 3]]
    first = time.perf_counter()
    boundary.ask(route, edges)
    first_ms = (time.perf_counter() - first) * 1000.0

    samples = []
    for i in range(ticks):
        start = time.perf_counter()
        boundary.ask(route, edges)
        samples.append((time.perf_counter() - start) * 1000.0)
    samples.sort()
    median = statistics.median(samples)
    mean = statistics.fmean(samples)
    print("    the first call (warms the brain's caches) : %8.3f ms" % first_ms)
    print("    min                                       : %8.3f ms" % samples[0])
    print("    median                                    : %8.3f ms" % median)
    print("    mean                                      : %8.3f ms" % mean)
    print("    max                                       : %8.3f ms" % samples[-1])
    print("    p99                                       : %8.3f ms"
          % samples[min(len(samples) - 1, int(len(samples) * 0.99))])
    print()
    print("    the same call made IN this process, for comparison:")
    here = []
    for _ in range(ticks):
        start = time.perf_counter()
        expected(route, edges)
        here.append((time.perf_counter() - start) * 1000.0)
    print("    in-process oracle, median                 : %8.3f ms" % statistics.median(here))
    print("    so the boundary costs about               : %8.3f ms per tick"
          % (median - statistics.median(here)))

    boundary.close()

    print()
    print("=" * 78)
    print("RESULT")
    verdict_ok = (ok_torch and ok_blocker and wrong == 0 and is_error and still_ok)
    print("  the worker never held torch              : %s" % ("YES" if ok_torch else "NO"))
    print("  the answers crossed correctly            : %s"
          % ("YES, %d of %d" % (len(CASES) - wrong, len(CASES)) if not wrong else "NO, %d wrong" % wrong))
    print("  it refuses what it must                  : %s" % ("YES" if is_error else "NO"))
    print("  and keeps working afterwards             : %s" % ("YES" if still_ok else "NO"))
    print("  cost per tick                            : %.3f ms median, %.3f ms p99"
          % (median, samples[min(len(samples) - 1, int(len(samples) * 0.99))]))
    print("  VERDICT                                  : %s"
          % ("THE BOUNDARY WORKS" if verdict_ok else "THE BOUNDARY DOES NOT WORK"))
    print("=" * 78)
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    sys.exit(main())
