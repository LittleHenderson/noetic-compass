"""cube_task/audit_judge.py -- the write-audit judgement of the c45 package (ctt_ears/client.audit_violations,
amendment A-CTT-2), copied by value so this package stays self-contained. Standard library only.

Every recorded write-open of an audited process is judged: its own audit log -> allowed; under a FORBIDDEN root (this
package's data and weights) -> violation, even inside an allowed folder; the null device -> allowed; under the
process's own temporary folder or a torch / CUDA cache (as it reported them) -> allowed; anything else -> violation.
A missing report, any network call and any process start are violations.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence


def _norm(p: str) -> str:
    return os.path.normcase(os.path.realpath(p))


def _under(p: str, root: str) -> bool:
    return p == root or p.startswith(root.rstrip(os.sep) + os.sep)


def audit_violations(report: Optional[Dict[str, object]], audit_path: str, forbidden_roots: Sequence = ()) -> List[str]:
    if not report:
        return ["no audit report"]
    bad: List[str] = []
    own = _norm(audit_path)
    allowed = [_norm(r) for r in report.get("allowed_scratch_roots") or []]
    forb = [_norm(str(f)) for f in forbidden_roots if f]
    nulls = {os.devnull, "/dev/null", str(report.get("devnull") or os.devnull)}
    for w in report.get("write_opens") or []:
        w = str(w)
        if w.startswith("fd:"):
            bad.append(w)
            continue
        nw = _norm(w)
        if nw == own:
            continue
        if any(_under(nw, f) for f in forb):
            bad.append("FORBIDDEN " + w)
            continue
        if w in nulls or nw in {_norm(n) for n in nulls}:
            continue
        if any(_under(nw, r) for r in allowed):
            continue
        bad.append(w)
    bad += ["network " + str(e) for e in report.get("network_calls") or []]
    bad += ["process " + str(e) for e in report.get("process_starts") or []]
    return bad
