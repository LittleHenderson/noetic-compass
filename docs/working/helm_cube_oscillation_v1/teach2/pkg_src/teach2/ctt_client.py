"""teach2/ctt_client.py -- the unit's side of the CTT serving process (A-TEACH2-18 P2, P3). Standard library only.

`CTTClient` starts `teach2/ctt_server.py` (one audited GPU process for the unit), and gives HELM three proposer copies
through HELM's own adapter (`helm_cube_osc.CTTProposer` -> `reading_from_ctt`). The three copies of one round share one
request: the first copy's call decodes the line with all three, the next two copies read the answers of that same
request; the next round asks again (nothing is cached across rounds). `twin(text)` reads a line with A5-s1, reported
only (P3). `close()` ends the process and judges its write-audit with the CUBE TRAIN judge (ctt/cube_task/audit_judge.py):
any violation, network call, process start, a dead server or a missing report is listed (I20).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import common_t2 as C


class CTTClient:
    def __init__(self, audit_path: Path, with_twin: bool = False, python: Optional[str] = None) -> None:
        self.audit_path = Path(audit_path)
        self.copies = list(C.VOTING_COPIES) + ([C.TWIN_COPY] if with_twin else [])
        ctt = C.ctt_dir()
        cmd = [python or sys.executable, "-X", "utf8", "-I", "-B", str(C.PKG / "teach2" / "ctt_server.py"),
               "--vocab", str(ctt / "vocab.json"), "--audit", str(self.audit_path)]
        for name in self.copies:
            cmd += ["--copy", f"{name}={ctt / 'weights' / (name + '.pt')}:{C.CTT_CONFIGS[name]}"]
        self.stderr_path = self.audit_path.with_name(self.audit_path.stem + ".stderr.log")
        self._err = open(self.stderr_path, "w", encoding="utf-8")       # a file, never a pipe nobody reads
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._err,
                                     text=True, encoding="utf-8", cwd=str(C.PKG))
        self.died = False
        self.requests = 0
        self.lines = 0
        self._pending_text: Optional[str] = None
        self._pending: Dict[str, str] = {}
        self._consumed: set = set()
        self.twin_log: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------- one request
    def _ask(self, copies: List[str], texts: List[str]) -> Dict[str, List[str]]:
        if self.died:
            return {c: [""] * len(texts) for c in copies}
        try:
            self.proc.stdin.write(json.dumps({"copies": copies, "texts": texts}, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            out = json.loads(line)["outputs"]
            if not all(isinstance(out.get(c), list) and len(out[c]) == len(texts) and all(isinstance(x, str) for x in out[c])
                       for c in copies):
                raise ValueError("a reply of the wrong shape")       # A-TEACH2-21 R5: counts as a dead server
            self.requests += 1
            self.lines += len(texts)
            return out
        except (OSError, ValueError, KeyError, TypeError):
            self.died = True
            return {c: [""] * len(texts) for c in copies}

    def read(self, copy: str, text: str) -> str:
        """One voting copy's raw output for `text`; the three copies of one round share one request."""
        if self._pending_text != text or copy in self._consumed:
            out = self._ask(list(C.VOTING_COPIES), [text])
            self._pending_text = text
            self._pending = {c: out[c][0] for c in C.VOTING_COPIES}
            self._consumed = set()
        self._consumed.add(copy)
        return self._pending.get(copy, "")

    def proposers(self, hco) -> List[Any]:
        """Three `CTTProposer`s (HELM's own class and adapter), one per voting copy, in a fixed order."""
        def serve_for(copy: str) -> Callable[[str], str]:
            return lambda text: self.read(copy, text)
        return [hco.CTTProposer(serve_for(c), name=c) for c in C.VOTING_COPIES]

    def twin(self, hco, text: str) -> Dict[str, Any]:
        """A5-s1 reads the line; reported only, never given to HELM (A-TEACH2-18 P3)."""
        raw = self._ask([C.TWIN_COPY], [text]).get(C.TWIN_COPY, [""])[0] if C.TWIN_COPY in self.copies else ""
        r = hco.reading_from_ctt(raw, text)
        row = {"text": text, "raw": raw, "reading": None if r is None else
               {"thing": r.thing, "slot": sorted(r.slot), "value": r.value, "replaces": r.replaces}}
        self.twin_log.append(row)
        return row

    # ---------------------------------------------------------------- the end
    def close(self) -> Dict[str, Any]:
        try:
            self.proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
            self.proc.stdin.flush()
        except OSError:
            self.died = True
        try:
            self.proc.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.communicate()
            self.died = True
        self._err.close()
        err = self.stderr_path.read_text(encoding="utf-8", errors="replace")
        sys.path.insert(0, str(C.ctt_dir()))
        from cube_task import audit_judge
        rep = json.loads(self.audit_path.read_text(encoding="utf-8")) if self.audit_path.is_file() else None
        forbidden = [str(C.ctt_dir()), str(C.PKG / "helm_now"), str(C.PKG / "teach2")]
        bad = audit_judge.audit_violations(rep, str(self.audit_path), forbidden)
        if self.died or self.proc.returncode != 0:
            bad = bad + [f"server died (return code {self.proc.returncode})"]
        return {"violations": bad, "died": self.died, "returncode": self.proc.returncode, "requests": self.requests,
                "lines": self.lines, "copies": self.copies, "stderr_tail": (err or "").strip().splitlines()[-3:],
                "audit_report_present": rep is not None}
