"""Machine-neutral hashing for HELM test pins (2026-10-21).

Why this exists. Job c53 (SPEC 7.106) read INSTRUMENT_ERROR because `test_helm_cas_address.py` pinned the sha256 of the loop's
records, and those records carry the licensed brain's folder as an ABSOLUTE PATH (`trace[].brain.brain_dir`). The pin was computed on
Windows; on the Linux host the path differed, so the hash differed, and HELM's own suite failed there while passing on the laptop.
Every stored pin of runtime records must therefore be taken over a machine-neutral form of the records. This module is the one place
that defines that form, and `test_helm_pin_hygiene.py` refuses any test pin that bypasses it or any fixture that still carries
machine-bound material.

    neutral(obj)        -> the same structure with machine-bound strings replaced (absolute paths -> their last component; see RULES)
    canon(obj)          -> compact, sorted, machine-neutral JSON text
    canon_sha256(obj)   -> sha256 of canon(obj)
    offending(text)     -> the list of machine-bound substrings still present in a canon text (empty = neutral)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from typing import Any, List

#: an absolute path on Windows (C:\... or C:/...), a UNC path, or a POSIX absolute path under the usual roots
ABS_PATH_RX = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users|tmp|opt|mnt|var|usr|root|c|d)(?:/|$))")
#: words that name a machine, a platform or an interpreter build and must never be hashed into a pin
MACHINE_WORDS = ("win32", "linux", "darwin", "cygwin", "Windows", "Ubuntu", "x86_64", "AMD64", "Python 3.", "python3.", "CPython")

RULES = {
    "PATH-NEUTRAL": "an absolute path is replaced by its last component (the folder or file name), so Windows and POSIX forms hash alike",
    "NO-MACHINE-WORDS": "platform, OS and interpreter build words may not appear in pinned material",
    "NO-HOME": "the current user's home directory and user name may not appear in pinned material",
    "SORTED-COMPACT": "JSON with sorted keys, compact separators, ensure_ascii=False, default=str",
}


def _neutral_str(s: str) -> str:
    if ABS_PATH_RX.match(s):
        tail = re.split(r"[\\/]+", s.rstrip("\\/"))[-1]
        return "<path>/" + tail if tail else "<path>"
    return s


def neutral(obj: Any) -> Any:
    """Return obj with every machine-bound string replaced by its neutral form (recursively)."""
    if isinstance(obj, dict):
        return {str(k): neutral(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [neutral(v) for v in obj]
    if isinstance(obj, str):
        return _neutral_str(obj)
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return _neutral_str(str(obj))


def canon(obj: Any) -> str:
    return json.dumps(neutral(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def canon_sha256(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def offending(text: str) -> List[str]:
    """Every machine-bound substring still present in an already-canonical text; empty means neutral."""
    hits: List[str] = []
    for m in re.finditer(r'"((?:[A-Za-z]:\\\\|[A-Za-z]:/|\\\\\\\\|/(?:home|Users|tmp|opt|mnt|var|usr|root)/)[^"]{0,120})"', text):
        hits.append(m.group(1))
    for w in MACHINE_WORDS:
        if w in text:
            hits.append(w)
    home = os.path.expanduser("~")
    user = os.path.basename(home.rstrip("\\/"))
    for needle in (home, home.replace("\\", "\\\\"), home.replace("\\", "/")):
        if needle and needle in text:
            hits.append(needle)
    if user and len(user) > 2 and re.search(r"(?<![A-Za-z0-9_])" + re.escape(user) + r"(?![A-Za-z0-9_])", text):
        hits.append("<user name>")
    if sys.version.split()[0] in text:
        hits.append(sys.version.split()[0])
    return hits
