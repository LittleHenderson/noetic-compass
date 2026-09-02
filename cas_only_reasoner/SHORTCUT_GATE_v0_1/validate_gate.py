"""Validate the shortcut gate against the leaks we ALREADY KNOW about.

A gate that does not catch known leaks is worthless, and a gate that fails everything is
equally worthless. Four cases, with the required verdict stated in advance:

  A  synthetic world with a deliberate ONE-HOP shortcut     must FAIL at 2_one_hop
  B  cmb_p0.build_world   (content leak + two-hop present)  must FAIL at 1_content and 3_two_hop
  C  cmb_p1.build_world_p1(content repaired, two-hop left)  must FAIL at 3_two_hop, PASS content
  D  clean synthetic world, no shortcut by construction     must PASS everything

Run: python validate_gate.py
"""
import os
import sys

import torch

_H = os.path.dirname(os.path.abspath(__file__))
for rel in ("../CMB_P0_v0_1", "../CMB_P1_v0_1"):
    d = os.path.join(_H, rel)
    if os.path.isdir(d):
        sys.path.insert(0, d)
sys.path.insert(0, _H)
from shortcut_gate import run_gate, format_report          # noqa: E402

DEV = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
DT = torch.float64
N, Q, POOL = 300, 64, 6


def synthetic(one_hop_shortcut):
    """A small world. The gold is a random member of the candidate set; the only difference
    between the two cases is whether the cue gets a privileged edge to its own answer."""
    g = torch.Generator(device=DEV); g.manual_seed(7)
    A = (torch.rand((N, N), generator=g, device=DEV, dtype=DT) < 0.03).to(DT) * 0.3
    A = torch.maximum(A, A.T); A.fill_diagonal_(0)
    cand = torch.arange(POOL, device=DEV)                      # nodes 0..5 are the answers
    cues = torch.arange(POOL, 2 * POOL, device=DEV)            # nodes 6..11 are the cues
    for c in cues:                                             # every cue -> every answer, flat
        for a in cand:
            A[c, a] = 1.0; A[a, c] = 1.0
    tgt = torch.randint(0, POOL, (Q,), generator=g, device=DEV)
    cue, gold = cues[tgt], cand[tgt]
    if one_hop_shortcut:                                       # the privileged edge
        for i in range(POOL):
            A[cues[i], cand[i]] = 2.0; A[cand[i], cues[i]] = 2.0
    content = torch.randn((N, 16), generator=g, device=DEV, dtype=DT)
    allowed = torch.zeros((Q, N), dtype=torch.bool, device=DEV)
    allowed[:, cand] = True
    return dict(A=A, cue=cue, gold=gold, content=content, candidates=allowed)


def cmb_world(builder, k=3, wid=990001):
    import cmb_p0 as P0
    w = builder(wid, k)
    q = P0.build_queries(w)
    amp = P0.propagate_scalar(q["seeds"], w["W"])
    return dict(A=w["A"], cue=q["cue"], gold=q["gold"], content=w["content"],
                exclude=(q["seeds"] > 0), amplitude=amp)


CASES = []
CASES.append(("A. synthetic, deliberate ONE-HOP shortcut", synthetic(True), ["2_one_hop"]))
CASES.append(("D. synthetic, clean by construction", synthetic(False), []))
try:
    import cmb_p0 as P0
    import cmb_p1 as P1
    if torch.cuda.is_available():
        P0.require_cuda()
    else:
        P0.DEV = DEV                                    # graph algebra only; no neural inference
    CASES.insert(1, ("B. cmb_p0.build_world (content leak + two-hop)",
                     cmb_world(P0.build_world), ["1_content", "3_two_hop"]))
    CASES.insert(2, ("C. cmb_p1.build_world_p1 (content repaired)",
                     cmb_world(P1.build_world_p1), ["3_two_hop"]))
except Exception as e:
    print(f"[cmb worlds unavailable: {type(e).__name__}: {e}]")

print(f"device={DEV}\n")
ok = True
for label, kw, must_fail in CASES:
    r = run_gate(**kw)
    print(f"=== {label} ===")
    print(format_report(r))
    got = {n for n, v in r["verdicts"].items() if v == "FAIL"}
    missing = [d for d in must_fail if d not in got]
    unexpected = "" if must_fail or not got else f"  (expected all PASS, got FAIL at {sorted(got)})"
    verdict = "OK" if not missing and (must_fail or not got) else "GATE VALIDATION FAILED"
    if verdict != "OK":
        ok = False
    print(f"required to FAIL at {must_fail or 'nothing'} -> {verdict}"
          f"{'  missing ' + str(missing) if missing else ''}{unexpected}\n")
print("GATE SELF-VALIDATION:", "PASS -- it catches every known leak and clears a clean world"
      if ok else "FAIL -- do not use this gate until it is fixed")
