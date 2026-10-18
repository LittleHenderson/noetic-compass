"""RB-OH1 worlds (FROZEN.json world_sets): the LSR families and F1 draws of ORIGINAL and FRESH, their core and start
capacities, their data (built once per process through the unchanged upstream builders, every dataset checked against
its FROZEN sha256 before use), the real input cells of an outcome, and each family's own law function (the generator's
own float code), which only the shape sweep uses. Standard library only. Nothing executes on import.
"""
from __future__ import annotations

import json
import random
from fractions import Fraction
from pathlib import Path

from rb_g1 import caps as C
from rb_g1 import units as U
from rb_g6 import units_g6 as U6
from rb_w import run_w as RW

HERE = Path(__file__).resolve().parent
ORIGINAL, FRESH = "ORIGINAL", "FRESH"
SETS = (ORIGINAL, FRESH)

BASE = C.GCfg(4, 1, 8, True, True, 2)          # s4_r1_v8_e1_l1_d2
V12 = C.GCfg(4, 1, 12, True, True, 2)          # a_approx ORACLE
V4 = C.GCfg(4, 1, 4, True, True, 2)            # a_approx START (and its shuffled control)
NOTERMS = C.GCfg(4, 1, 8, False, False, 2)     # scale_leak START (and its shuffled control)
F1_ORACLE = C.GCfg(8, 2, 8, True, True, 3)
F1_START = C.GCfg(4, 2, 8, True, True, 3)

# data family -> (world set, role family, core capacity, start capacity or None (R-CAP / R-RET only))
LSR = {
    "a": (ORIGINAL, "a", BASE, None),
    "a_approx": (ORIGINAL, "a_approx", V12, V4),
    "c": (ORIGINAL, "c", BASE, None),
    "scale_leak": (ORIGINAL, "scale_leak", BASE, NOTERMS),
    "S2v2": (ORIGINAL, "S2v2", BASE, None),
    "S3v2": (ORIGINAL, "S3v2", BASE, None),
    "b": (ORIGINAL, "b", BASE, None),
    "a_offladder": (ORIGINAL, "a_offladder", BASE, None),
    "a_approx_shuffled": (ORIGINAL, "a_approx_shuffled", V4, None),
    "scale_leak_shuffled": (ORIGINAL, "scale_leak_shuffled", NOTERMS, None),
    "a_fresh": (FRESH, "a", BASE, None),
    "a_approx_fresh": (FRESH, "a_approx", V12, None),
    "scale_leak_fresh": (FRESH, "scale_leak", BASE, None),
    "S2v2_fresh": (FRESH, "S2v2", BASE, None),
    "S3v2_fresh": (FRESH, "S3v2", BASE, None),
    "a_approx_shuffled_fresh": (FRESH, "a_approx_shuffled", V4, None),
    "scale_leak_shuffled_fresh": (FRESH, "scale_leak_shuffled", NOTERMS, None),
}
ORDER_ORIGINAL = ("a", "a_approx", "c", "scale_leak", "S2v2", "S3v2", "b", "a_offladder", "a_approx_shuffled",
                  "scale_leak_shuffled")
ORDER_FRESH = ("a_fresh", "a_approx_fresh", "scale_leak_fresh", "S2v2_fresh", "S3v2_fresh",
               "a_approx_shuffled_fresh", "scale_leak_shuffled_fresh")
START_UNITS = ("a_approx", "scale_leak")
SHUFFLED_ROLES = ("a_approx_shuffled", "scale_leak_shuffled")
MAIN = {ORIGINAL: ("a", "a_approx", "c", "scale_leak", "S2v2", "S3v2"),
        FRESH: ("a_fresh", "a_approx_fresh", "scale_leak_fresh", "S2v2_fresh", "S3v2_fresh")}
F1_DRAWS = {ORIGINAL: tuple(range(40, 60)), FRESH: tuple(range(60, 80))}
F1_SWEEP_DRAW = {ORIGINAL: 40, FRESH: 60}
EYE_TWIN = {"a": "a_fresh", "a_approx": "a_approx_fresh"}          # R-EYE panels (clean, changed law)
OFFLADDER_RHO = 0.37
OFFLADDER_DATA_SEED = 2026101571
V1_A = "a_ces_substitutable"
V1_B = "b_additive_saturating"
V1_C = "c_minratio_noisy_corrupt"

_FROZEN = {}
_DS = {}


def frozen():
    if "f" not in _FROZEN:
        _FROZEN["f"] = json.loads((HERE / "FROZEN.json").read_text("utf-8"))
    return _FROZEN["f"]


def frozen_dataset_sha256(fam):
    ws = LSR[fam][0]
    return frozen()["world_sets"][ws]["lsr_families"][fam]["dataset_sha256"]


# ------------------------------------------------------------------ a_offladder (FROZEN world_sets a_offladder)
def v1_wrapper(rho, data_seed, name=V1_A):
    """fair_data_experiment_v1 data.synthetic_family's no-dirt branch with rho and the data seed as arguments (the
    SAME functions family_parameters, atomic_rows, chain_rows, _finish), as rb_g6 units_g6.v1_synthetic_with_data_seed."""
    from fair_data_experiment_v1 import data as V1
    params = V1.family_parameters(name)
    params["rho"] = float(rho)
    rng = random.Random(data_seed)
    dataset = {"family": name, "kind": "SYNTHETIC_ONLY", "parameters": params,
               "train": V1.atomic_rows(name, params, rng, 64, "train", .1, 5.),
               "validation": V1.atomic_rows(name, params, rng, 16, "validation", .01, 7.),
               "heldout": V1.atomic_rows(name, params, rng, 32, "heldout", 6., 12.),
               "second": V1.chain_rows(name, params, rng), "second_kind": "composition",
               "truth": None, "corrupted": None}
    return V1._finish(dataset, ("train", "validation", "heldout", "second"))


def build_offladder():
    from lsr_t1 import families as F1M
    return F1M._from_v1_shape("a_offladder", v1_wrapper(OFFLADDER_RHO, OFFLADDER_DATA_SEED))


# ------------------------------------------------------------------ data
def world_data(fam):
    """(dataset, seed recipes) of a data family, checked against FROZEN.json (raises on any drift)."""
    if fam in _DS:
        return _DS[fam]
    if fam == "a_offladder":
        ds = build_offladder()
        seeds = RW.lsr_seeds("a", ds)                     # the bridge v2 seed with its assertion (key unused)
    elif U6.is_fresh(fam):
        ds, seeds = U6.world_data(fam)                    # rb_g6 frozen-hash check inside
    else:
        ds, seeds = U.lsr_world(fam)                      # unchanged upstream builders and their own checks
    want = frozen_dataset_sha256(fam)
    if ds["sha256"] != want:
        raise ValueError("RB-OH1 dataset sha256 drift: %s %s (frozen %s)" % (fam, ds["sha256"], want))
    _DS[fam] = (ds, seeds)
    return _DS[fam]


def omega_rows(ds, fam, rid):
    return U.omega_rows(ds, fam, rid)


def real_cells(train):
    """FROZEN vocabulary: drop a column equal to an earlier column on every training row (padding copies)."""
    n = len(train[0].xF)
    keep = []
    for j in range(n):
        if any(all(r.xF[i] == r.xF[j] for r in train) for i in keep):
            continue
        keep.append(j)
    return tuple(keep)


# ------------------------------------------------------------------ each family's own law (the sweep's labels)
def _sdg_af(p):
    return [float(Fraction(s)) for s in p["a"]]


def law(fam, ds, rid):
    """The generator's own float law for outcome rid, as a function of the 4 slots (padding included)."""
    role = LSR[fam][1]
    if role in SHUFFLED_ROLES:
        return None                                       # no clean law to ask (FROZEN DV-09)
    from fair_data_experiment_v1 import data as V1
    if fam == "a_offladder":
        params = V1.family_parameters(V1_A)
        params["rho"] = OFFLADDER_RHO
        return lambda x, p=params: V1.clean_law(V1_A, p, rid, x)
    if role == "a":
        params = V1.family_parameters(V1_A)
        return lambda x, p=params: V1.clean_law(V1_A, p, rid, x)
    if role == "b":
        params = V1.family_parameters(V1_B)
        return lambda x, p=params: V1.clean_law(V1_B, p, rid, x)
    if role == "c":
        params = V1.family_parameters(V1_C)
        return lambda x, p=params: V1.clean_law(V1_C, p, rid, x)
    from lsr_t4 import families4 as F4
    if role == "a_approx":
        p = ds["parameters"][rid]
        return lambda x, p=p: F4.ces2(p, x)
    if role == "scale_leak":
        p = ds["parameters"][rid]
        return lambda x, p=p: F4.scale_leak_law(p, x)
    if role in ("S2v2", "S3v2"):
        af = _sdg_af(ds["parameters"][rid])
        n = len(af)
        return lambda x, af=af, n=n: min(x[i] / af[i] for i in range(n))
    raise KeyError(fam)


def law_check_rows(fam, ds, rid):
    """The rows on which the law must reproduce the dataset's own labels exactly: training rows, except c (noisy
    training labels): its clean held-out rows."""
    rows = omega_rows(ds, fam, rid)
    return rows["heldout"] if LSR[fam][1] == "c" else rows["train"]


def pad_slots(real_values, cells, n_slots=4):
    """Rebuild the 4 slots as the generators build them: real inputs in cells 0..n-1, padding slots copy slot 0."""
    if tuple(cells) != tuple(range(len(cells))):
        raise ValueError("real cells are not a prefix: %r" % (cells,))
    x = list(real_values) + [real_values[0]] * (n_slots - len(real_values))
    return x


# ------------------------------------------------------------------ the frozen unit list (FROZEN run_plan.units_rule)
def unit_specs():
    out = []
    for fam in ORDER_ORIGINAL:
        for h in (0, 1):
            out.append(("lsr", ORIGINAL, fam, "ORACLE", h))
    for fam in START_UNITS:
        for h in (0, 1):
            out.append(("lsr", ORIGINAL, fam, "START", h))
    for fam in ORDER_FRESH:
        for h in (0, 1):
            out.append(("lsr", FRESH, fam, "ORACLE", h))
    for ws in SETS:
        d = F1_DRAWS[ws]
        for shuffled in (False, True):
            out.append(("f1", ws, list(d[:10]), shuffled))
            out.append(("f1", ws, list(d[10:]), shuffled))
    for ws in SETS:
        out.append(("f1sweep", ws))
    return out


def unit_key(spec):
    if spec[0] == "lsr":
        return "OH1|LSR|%s|%s|%s|h%d" % spec[1:]
    if spec[0] == "f1":
        return "OH1|F1|%s|d%d-%d|%s" % (spec[1], spec[2][0], spec[2][-1], "shuf" if spec[3] else "true")
    return "OH1|F1SWEEP|%s" % spec[1]


def capacity(fam, tag):
    ws, role, core, start = LSR[fam]
    return core if tag == "ORACLE" else start
