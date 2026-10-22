"""The translator process's write-audit (gate H-WRITE, runtime part). Standard library only.

install() adds a Python audit hook. From then on every file opened for writing, every network call and every process
start is RECORDED (all of them, nothing filtered). report() returns the record plus the folders this process itself
uses for scratch files (its temporary folder and the torch / CUDA cache folders), read inside this process.
The JUDGEMENT is made outside, by ctt_ears/client.audit_clean (amendment A-CTT-2): the audit log itself, the null
device, the temporary folder and the torch / CUDA caches are allowed; anything under a forbidden root (brain, wave
packages, store, receipts, exams, data, weights) is a violation even inside an allowed folder.
"""
from __future__ import annotations

import os
import sys

_EVENTS = {"write_opens": [], "network_calls": [], "process_starts": [], "recording": False}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
_NET = ("socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg")
_PROC = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.startfile")


def _hook(event, args):
    if not _EVENTS["recording"]:
        return
    if event == "open":
        path, mode, flags = (list(args) + [None, None, None])[:3]
        writes = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                 (isinstance(flags, int) and bool(flags & _WRITE_FLAGS))
        if writes:
            if isinstance(path, int):
                _EVENTS["write_opens"].append("fd:%d" % path)
            else:
                p = os.fsdecode(path) if isinstance(path, (bytes, bytearray)) else str(path)
                _EVENTS["write_opens"].append(os.path.abspath(p))
    elif event in _NET:
        _EVENTS["network_calls"].append(event)
    elif event in _PROC:
        _EVENTS["process_starts"].append(event)


def install() -> None:
    sys.addaudithook(_hook)
    _EVENTS["recording"] = True


def stop() -> None:
    _EVENTS["recording"] = False


def scratch_roots() -> list:
    """This process's own scratch folders (call after stop(): gettempdir may probe the folder)."""
    import tempfile
    home = os.path.expanduser("~")
    xdg = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    roots = [tempfile.gettempdir(), os.environ.get("TMPDIR"),
             os.environ.get("TORCH_HOME") or os.path.join(xdg, "torch"), os.path.join(xdg, "torch"),
             os.environ.get("CUDA_CACHE_PATH") or os.path.join(home, ".nv", "ComputeCache"),
             os.environ.get("TORCHINDUCTOR_CACHE_DIR"),
             os.environ.get("TRITON_CACHE_DIR") or os.path.join(home, ".triton")]
    out = []
    for r in roots:
        if r:
            rr = os.path.realpath(r)
            if rr not in out:
                out.append(rr)
    return out


def report(**extra) -> dict:
    stop()
    out = {"schema": "ctt.translator-audit/2", "write_opens": list(_EVENTS["write_opens"]),
           "network_calls": list(_EVENTS["network_calls"]), "process_starts": list(_EVENTS["process_starts"]),
           "allowed_scratch_roots": scratch_roots(), "devnull": os.devnull, "pid": os.getpid()}
    out.update(extra)
    return out
