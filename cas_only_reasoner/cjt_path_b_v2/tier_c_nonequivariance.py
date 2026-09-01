"""tier_c_nonequivariance.py -- PROOF_OF_NON_EQUIVARIANCE (C0 gate G-C0-2/3/4).

The scientific object is the relational ISOMORPHISM CLASS, not literal
coordinate names (owner ruling section 3). Any structure can be consistently
renamed; the proof establishes, over the COMPLETE neural pathway of every
tournament transform:

  Test A (consistent-renaming invariance, must PASS all 24 perms):
    permute operation profiles + every class-indexed axis of R + the
    class-indexed parameter (W_r rows; AdamW state follows values) ->
    PER-EXAMPLE per-step training losses equal within TOL_A.

  Test B (structure-held-fixed sensitivity, absorption must FAIL):
    permute profiles while R is HELD FIXED, apply the full class-indexed
    absorption recipe -> PER-EXAMPLE divergence >= FLOOR_B for every
    permutation that is not a genuine automorphism of the transform's
    structure view, on EVERY data seed tested.

  Criterion law (C0 review hardening): conformance/divergence is measured
  on per-example loss trajectories (steps x n residuals), not batch means.
  A free init-search can curve-fit 5 batch-mean scalars with hundreds of
  free parameters; it cannot fit steps x n per-example residuals (the
  review's own attack, which matched means to 1e-4, diverges at 1.68 per
  example). Scope law: Test B refutes the CLASS-INDEXED recipe -- the
  complete canonical group action on the only class-indexed parameter.
  Divergence proves the recipe twin is not functionally equivalent, hence
  the canonical action is not a symmetry when R is frozen. It does not
  claim no curve-fit of scalar summaries exists.

  Recipe validity baseline: the SAME absorption recipe on a no-structure
  model must conform within TOL_A on per-example trajectories (mirrors
  A1's S-PERM CONFIRMED 7.15e-07) -- proving Test B's divergence comes
  from the frozen structure, not from a broken recipe.

Two independent data seeds guard the universally-quantified gate against a
single lucky draw. Every per-permutation number is persisted (no
Boolean-only gates). Development-only, non-claim-bearing. CPU.
"""
from __future__ import annotations

import itertools

import torch

import tier_c_structure as ts
import tier_c_transforms as tt

TOL_A = 1e-6
FLOOR_B = 1e-3
STEPS = 5
LR = 1e-2
DATA_SEEDS = (20260901, 20260902)
MODEL_SEED = 7


def _pair_run(kind, struct, perm, mode, data_seed=None):
    """Train original + twin; return (max per-example divergence,
    mean-loss lists). mode 'A': twin = permuted labels + permuted structure
    + absorbed W_r. mode 'B': twin = permuted labels + FIXED structure +
    absorbed W_r."""
    data = tt.make_synth(data_seed if data_seed is not None
                         else DATA_SEEDS[0])
    base = tt.ConformanceModel(kind, struct, seed=MODEL_SEED)
    twin = tt.ConformanceModel(kind, struct, seed=MODEL_SEED)
    if mode == "A":
        twin.swap_structure(ts.permute_structure(struct, perm))
    tt.absorb_wr(twin, perm)
    m0, pe0 = tt.train_losses(base, data, steps=STEPS, lr=LR)
    m1, pe1 = tt.train_losses(twin, data, steps=STEPS, lr=LR,
                              label_perm=perm)
    diff = float((pe0 - pe1).abs().max())
    return diff, m0, m1


def _recipe_validity(struct):
    """No-structure model: absorption must conform for ALL 24 perms."""
    rows = []
    for perm in itertools.permutations(range(4)):
        data = tt.make_synth(DATA_SEEDS[0])
        base = tt.ConformanceModel("T1", struct, seed=MODEL_SEED)
        twin = tt.ConformanceModel("T1", struct, seed=MODEL_SEED)
        for m in (base, twin):
            with torch.no_grad():
                m.w_phi.zero_()
                m.lam_str.zero_()
            m.w_phi.requires_grad_(False)
            m.lam_str.requires_grad_(False)
        tt.absorb_wr(twin, perm)
        _, pe0 = tt.train_losses(base, data, steps=STEPS, lr=LR)
        _, pe1 = tt.train_losses(twin, data, steps=STEPS, lr=LR,
                                 label_perm=list(perm))
        rows.append({"perm": list(perm),
                     "max_per_example_diff":
                         float((pe0 - pe1).abs().max())})
    worst = max(r["max_per_example_diff"] for r in rows)
    return {"per_perm": rows, "max_divergence": worst,
            "conforms": worst <= TOL_A}


def run_proof(struct):
    """The complete proof over T1-T4. Returns the full report dict."""
    auto = ts.automorphism_report(struct)
    report = {"proof_id": "PROOF_OF_NON_EQUIVARIANCE_v2",
              "non_claim_bearing": True,
              "criterion": "per-example loss trajectories (steps x n "
                           "residuals); scope: the class-indexed recipe "
                           "(see module docstring)",
              "tol_a": TOL_A, "floor_b": FLOOR_B, "steps": STEPS, "lr": LR,
              "data_seeds": list(DATA_SEEDS), "model_seed": MODEL_SEED,
              "structure_automorphisms": auto,
              "join_cell_counterfactual":
                  ts.join_cell_counterfactual(struct),
              "recipe_validity_no_structure": _recipe_validity(struct),
              "transforms": {}}
    for kind in tt.TRANSFORMS:
        view_auts = tt.view_automorphisms(struct, kind)
        rows_a, rows_b = [], []
        for perm in itertools.permutations(range(4)):
            da, la, lta = _pair_run(kind, struct, list(perm), "A")
            rows_a.append({"perm": list(perm), "max_per_example_diff": da,
                           "mean_losses_base": la, "mean_losses_twin": lta})
            per_seed = []
            for sd in DATA_SEEDS:
                db, _, _ = _pair_run(kind, struct, list(perm), "B",
                                     data_seed=sd)
                per_seed.append(db)
            rows_b.append({"perm": list(perm),
                           "max_per_example_diff_by_seed": per_seed,
                           "min_over_seeds": min(per_seed),
                           "is_view_automorphism": list(perm) in view_auts})
        worst_a = max(r["max_per_example_diff"] for r in rows_a)
        non_auto_b = [r for r in rows_b if not r["is_view_automorphism"]]
        min_b = min(r["min_over_seeds"] for r in non_auto_b) \
            if non_auto_b else None
        report["transforms"][kind] = {
            "view_automorphisms": view_auts,
            "view_group_trivial": view_auts == [[0, 1, 2, 3]],
            "test_a_per_perm": rows_a,
            "test_a_max_divergence": worst_a,
            "test_a_conforms_all": worst_a <= TOL_A,
            "test_b_per_perm": rows_b,
            "test_b_min_divergence_non_automorphism": min_b,
            "test_b_all_non_automorphisms_diverge":
                (min_b is not None and min_b >= FLOOR_B)}
    report["gates"] = {
        "G_C0_2_automorphism_trivial": auto["trivial"],
        "G_C0_3_test_a_all_transforms": all(
            v["test_a_conforms_all"] for v in report["transforms"].values()),
        "G_C0_4_test_b_all_transforms": all(
            v["test_b_all_non_automorphisms_diverge"]
            for v in report["transforms"].values()),
        "recipe_validity": report["recipe_validity_no_structure"]["conforms"],
    }
    return report
