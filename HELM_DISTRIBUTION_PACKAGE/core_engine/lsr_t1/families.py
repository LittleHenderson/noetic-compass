"""LSR-T1 families. Evaluator-owned. The loop sees only train + validation rows of one Omega at a time.

Reused by import, unchanged:
* fair_data_experiment_v2_sdg.data: v1_make_family (families a, b, c), make_family('S1_sdg_recipes_clean'),
  frozen() (expected sha256s); sdg_source.load_recipe_seeds (seed file with sha256 check).
* sdg_bridge_v2.parse_recipe: reads every SDG recipe seed (clean 2- and 3-input families, shape library).
* scale_benchmark_v1.data: request(), digest().
New here: S2v2 / S3v2 (clean SDG recipes read through bridge v2) and a2 (best-of-two recipes, positive
control "designed to fit", TEST_PLAN.md s.3 / OPEN_QUESTIONS Q9). Seeds frozen in FROZEN.json.
"""
import itertools
import json
import random
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from scale_benchmark_v1.data import request, digest
from fair_data_experiment_v2_sdg import data as v2data
from fair_data_experiment_v2_sdg import sdg_source
from sdg_bridge_v2 import parse_recipe

from .engine import Row

HERE = Path(__file__).resolve().parent
RECIPES = 16
SEED_SHA256 = "df68d2447ccd7371f8b9a18e48fa90269914be2505f1a96d92e4164aabe91639"
V1_FAMILIES = {"a": "a_ces_substitutable_bound", "b": "b_additive_saturating_bound",
               "c": "c_minratio_noisy_corrupt_bound"}


def frozen():
    return json.loads((HERE / "FROZEN.json").read_text("utf-8"))


# ------------------------------------------------------------------ SDG seeds through bridge v2
_SEEDS = {}


def parsed_seeds():
    if "rows" not in _SEEDS:
        rows = []
        for line, record in sdg_source.load_recipe_seeds(SEED_SHA256):
            p = parse_recipe(record["expression"])
            rows.append({"seed_id": record["seed_id"], "line": line, "expression": record["expression"],
                         "parsed": p})
        _SEEDS["rows"] = rows
    return _SEEDS["rows"]


def shape_library_counts():
    """Attested shapes: accepted recipe seeds by number of core prerequisites (leakage tails counted apart)."""
    counts, leak = {}, {}
    rejected = 0
    for r in parsed_seeds():
        p = r["parsed"]
        if not p["accepted"]:
            rejected += 1
            continue
        n = len(p["core"])
        counts[n] = counts.get(n, 0) + 1
        if p["leakage"]:
            leak[n] = leak.get(n, 0) + 1
    return {"by_prerequisite_count": counts, "with_leakage_tail": leak, "rejected": rejected,
            "seed_file_sha256": SEED_SHA256, "reader": "sdg_bridge_v2.parse_recipe"}


def _sdg_rows(name, recipes, rng, count, split, lo, hi):
    """Row structure of fair_data_experiment_v2_sdg.data._sdg_atomic; pad slots repeat slot 0 (PAD_ALIAS)."""
    rows = []
    for rid, recipe in enumerate(recipes):
        n = len(recipe["a"])
        af = [float(v) for v in recipe["a"]]
        for k in range(count):
            x = [rng.uniform(lo, hi) for _ in range(n)]
            if k % 2:
                x[(k // 2) % n] *= .08
            if split == "heldout" and k % 8 == 0:
                x[(k // 8) % n] = 0.
            slots = x + [x[0]] * (4 - n)
            req = request(rid, slots, "outer" if split == "heldout" else "inner")
            y = min(x[i] / af[i] for i in range(n))
            rows.append({"id": "%s-%s-%d-%d" % (name, split, rid, k), "rid": rid, "x": req["activations"],
                         "y": y, "corrupted": False})
    return rows


def sdg_v2_family(name, n_prereq, selection_seed, data_seed):
    eligible = []
    for r in parsed_seeds():
        p = r["parsed"]
        if p["accepted"] and not p["leakage"] and len(p["core"]) == n_prereq and all(
                t["kind"] == "state" for t in p["core"]):
            eligible.append(r)
    ids = sorted(r["seed_id"] for r in eligible)
    chosen = sorted(random.Random(selection_seed).sample(ids, RECIPES))
    by_id = {r["seed_id"]: r for r in eligible}
    recipes = []
    for sid in chosen:
        p = by_id[sid]["parsed"]
        recipes.append({"seed_id": sid, "line": by_id[sid]["line"], "expression": by_id[sid]["expression"],
                        "cells": [t["cell"] for t in p["core"]],
                        "a": [Fraction(Decimal(t["coefficient"])) for t in p["core"]]})
    rng = random.Random(data_seed)
    ds = {"family": name, "kind": "SYNTHETIC_ONLY", "eligible_seeds": len(ids),
          "parameters": [{k: (v if k != "a" else [str(x) for x in v]) for k, v in r.items()} for r in recipes],
          "train": _sdg_rows(name, recipes, rng, 64, "train", .1, 5.),
          "validation": _sdg_rows(name, recipes, rng, 16, "validation", .01, 7.),
          "heldout": _sdg_rows(name, recipes, rng, 32, "heldout", 6., 12.)}
    ds["sha256"] = digest({k: v for k, v in ds.items() if k != "sha256"})
    return ds


# ------------------------------------------------------------------ a2: best of two recipes
def a2_parameters(seed):
    rng = random.Random(seed)
    subsets = list(itertools.combinations(range(4), 3))
    out = []
    for _ in range(RECIPES):
        s1, s2 = rng.sample(subsets, 2)
        out.append({"routes": [{"cells": list(s), "a": [rng.uniform(.75, 3.25) for _ in s]} for s in (s1, s2)]})
    return out


def a2_law(p, x):
    return max(min(x[c] / a for c, a in zip(route["cells"], route["a"])) for route in p["routes"])


def a2_family(parameter_seed, data_seed):
    name = "a2_best_of_two"
    params = a2_parameters(parameter_seed)
    rng = random.Random(data_seed)

    def rows(count, split, lo, hi):
        out = []
        for rid in range(RECIPES):
            for k in range(count):
                x = [rng.uniform(lo, hi) for _ in range(4)]
                if k % 2:
                    x[(k // 2) % 4] *= .08
                if split == "heldout" and k % 8 == 0:
                    x[(k // 8) % 4] = 0.
                req = request(rid, x, "outer" if split == "heldout" else "inner")
                out.append({"id": "%s-%s-%d-%d" % (name, split, rid, k), "rid": rid, "x": req["activations"],
                            "y": a2_law(params[rid], req["activations"]), "corrupted": False})
        return out
    ds = {"family": name, "kind": "SYNTHETIC_ONLY_POSITIVE_CONTROL_DESIGNED_TO_FIT", "parameters": params,
          "train": rows(64, "train", .1, 5.), "validation": rows(16, "validation", .01, 7.),
          "heldout": rows(32, "heldout", 6., 12.)}
    ds["sha256"] = digest({k: v for k, v in ds.items() if k != "sha256"})
    return ds


# ------------------------------------------------------------------ imported families
def _from_v1_shape(name, dataset):
    def conv(panel):
        return [{"id": r["id"], "rid": r["request"]["recipe_id"], "x": list(r["request"]["activations"]),
                 "y": r["target_yield"], "corrupted": bool(r.get("label_corrupted", False))}
                for r in dataset[panel]]
    return {"family": name, "kind": dataset.get("kind", "SYNTHETIC_ONLY"), "sha256": dataset["sha256"],
            "train": conv("train"), "validation": conv("validation"), "heldout": conv("heldout")}


def v1_family(letter):
    name = V1_FAMILIES[letter]
    ds = v2data.v1_make_family(v2data.V1_NAME[name])
    expected = v2data.frozen()["families"][name]["expected_dataset_sha256_v1"]
    if ds["sha256"] != expected:
        raise ValueError("v1 dataset drift: " + name)
    return _from_v1_shape(letter, ds)


def s1_family():
    ds = v2data.make_family("S1_sdg_recipes_clean")
    if ds["sha256"] != frozen()["families"]["S1"]["expected_dataset_sha256"]:
        raise ValueError("S1 dataset drift")
    return _from_v1_shape("S1", ds)


def build(key):
    spec = frozen()["families"][key]
    if key == "S1":
        ds = s1_family()
    elif key in ("S2v2", "S3v2"):
        ds = sdg_v2_family(key, spec["n_prerequisites"], spec["selection_seed"], spec["data_seed"])
    elif key == "a2":
        ds = a2_family(spec["parameter_seed"], spec["data_seed"])
    else:
        ds = v1_family(key)
    want = spec.get("expected_dataset_sha256")
    if want is not None and ds["sha256"] != want:
        raise ValueError("dataset sha256 drift: %s %s" % (key, ds["sha256"]))
    return ds


def omega_rows(ds, rid):
    """Engine rows for one Omega (train, validation, heldout) plus the corrupted flags (scoring only)."""
    out = {}
    for panel in ("train", "validation", "heldout"):
        out[panel] = [Row.make(r["id"], r["x"], r["y"]) for r in ds[panel] if r["rid"] == rid]
    out["corrupted"] = {r["id"] for r in ds["train"] if r["rid"] == rid and r["corrupted"]}
    return out
