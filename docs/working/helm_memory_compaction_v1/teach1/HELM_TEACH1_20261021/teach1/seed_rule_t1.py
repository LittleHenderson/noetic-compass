"""The TEACH-1 seed rule (pre-code section 12; the house rule of RB-W1T / wave 6 / wave 7). Standard library only; pure.

H = sha256 of the UTF-8 bytes of (the owner's typed line + ":" + the full sha256 of the sealed zip), no trailing newline.
Four parts, each from its own 16-hex slice of H: WORLD H[0:16], QUIZ H[16:32], PERSON H[32:48], RANDOM_REFRESH H[48:64].
First slot = k mod 1,000,000; seed = band low + slot; a seed inside the used table (or within the gap of it) steps
s <- (s + 1) mod 1,000,000; no free slot = STOP. Bands (A-TEACH1-1): 2,036 M / 2,038 M / 2,040 M / 2,042 M.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Optional

from . import common_t1 as C

SCHEMA = "helm.teach1.seed-derivation/1"


def seed_text(owner_line: str, zip_sha256: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", zip_sha256 or ""):
        raise ValueError("zip sha256 must be 64 lower-case hex")
    if owner_line != owner_line.strip() or "\n" in owner_line or "\r" in owner_line:
        raise ValueError("owner line must be the typed line with no surrounding whitespace or newline")
    return owner_line + ":" + zip_sha256


def blocked(seed: int) -> bool:
    return any(lo - C.SEED_GAP <= seed <= hi + C.SEED_GAP for _n, lo, hi in C.USED_RANGES)


def part_seed(h: str, part: str, start_slot: Optional[int] = None) -> Dict[str, Any]:
    lo, hi = C.BANDS[part]
    a, b = C.HEX_SLICES[part]
    k = int(h[a:b], 16)
    first = k % C.SLOTS
    slot = first if start_slot is None else start_slot % C.SLOTS
    steps = 0
    while blocked(lo + slot) or lo + slot > C.INT32_MAX or lo + slot > hi:
        slot = (slot + 1) % C.SLOTS
        steps += 1
        if steps >= C.SLOTS:
            return {"part": part, "result": "STOP", "reason": "NO_FREE_SLOT", "band": [lo, hi]}
    seed = lo + slot
    return {"part": part, "hex_slice": [a, b], "k_hex": format(k, "016x"), "first_slot": first, "slot": slot,
            "overlap_steps": steps, "seed": seed, "in_band": lo <= seed <= hi, "band": [lo, hi], "result": "PASS"}


def derive(owner_line: str, zip_sha256: str) -> Dict[str, Any]:
    text = seed_text(owner_line, zip_sha256)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    parts = {p: part_seed(h, p) for p in C.BANDS}
    seeds = [v["seed"] for v in parts.values() if "seed" in v]
    ok = (all(v.get("result") == "PASS" and v.get("in_band") for v in parts.values())
          and len(set(seeds)) == len(seeds) and not any(blocked(s) for s in seeds) and all(s < C.INT32_MAX for s in seeds))
    out = {"schema": SCHEMA, "practice_mock": False, "owner_line_verbatim": owner_line,
           "owner_line_utf8_bytes": len(owner_line.encode("utf-8")),
           "owner_line_sha256": hashlib.sha256(owner_line.encode("utf-8")).hexdigest(),
           "zip_sha256": zip_sha256, "input_sha256": h, "parts": parts,
           "used_ranges": [list(r) for r in C.USED_RANGES], "gap": C.SEED_GAP, "slots": C.SLOTS,
           "overlap_check": "PASS" if ok else "FAIL"}
    for p in C.BANDS:
        out[p] = parts[p].get("seed")
    return out


def practice_seeds() -> Dict[str, Any]:
    out: Dict[str, Any] = dict(C.PRACTICE_SEED_TEXTS)
    out.update({"schema": SCHEMA, "practice_mock": True, "owner_line_verbatim": None, "zip_sha256": None,
                "overlap_check": "NOT_APPLICABLE_PRACTICE"})
    return out
