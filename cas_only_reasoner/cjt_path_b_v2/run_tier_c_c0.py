"""run_tier_c_c0.py -- Tier C C0 orchestrator (owner-authorized CPU build).

Runs the full C0 gate battery (TIER_C_SPEC_v0_2.md section 10), persists
every gate's raw deciding quantities (no Boolean-only gates), and emits the
deterministic receipt tier_c/TIER_C_C0_RECEIPT.json whose verdict is either
the FIRST FAILED GATE or TIER_C_C0_READY_FOR_FOCUSED_REVIEW. The receipt is
byte-reproducible (wall clock goes to stdout only; library versions are
recorded as environment facts).

No GPU. No protected read (train/val files only; QC entities from the
train/val bundles). No claim promotion. Development-only, non-claim-bearing.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
from exec.fsio import write_utf8_lf  # noqa: E402

import tier_c_cache_binding as cbind  # noqa: E402
import tier_c_controls as tc  # noqa: E402
import tier_c_mutations as tm  # noqa: E402
import tier_c_nonequivariance as tn  # noqa: E402
import tier_c_qc_valid as qc  # noqa: E402
import tier_c_ronly_probe as rp  # noqa: E402
import tier_c_structure as ts  # noqa: E402

OUT = HERE / "tier_c"


def jdump(obj, path):
    write_utf8_lf(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_jsonl(records):
    return "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"))
                     for r in records) + "\n"


def library_versions():
    import numpy
    import sklearn
    import torch
    return {"python": sys.version.split()[0], "torch": torch.__version__,
            "sklearn": sklearn.__version__, "numpy": numpy.__version__}


def check_r_cas_schema(r_cas):
    """Strengthened G-C0-1 (C0 review fix): every typed field validated
    against its vocabulary; M an int (not bool) in {0,1}; J planes typed."""
    why = []
    for key, c in r_cas["cells"].items():
        if c["status"] not in ("DERIVED", "UNDEFINED"):
            why.append(f"{key}: bad status {c['status']}")
        if not c.get("source_rule"):
            why.append(f"{key}: missing source rule")
        if type(c["M"]) is not int or c["M"] not in (0, 1):
            why.append(f"{key}: M must be int 0/1, got {c['M']!r}")
        if c["result_type"] not in ts.RESULT_TYPES:
            why.append(f"{key}: result_type {c['result_type']!r} not in "
                       "vocabulary")
        if c["mediator_type"] not in ts.MEDIATOR_TYPES:
            why.append(f"{key}: mediator_type {c['mediator_type']!r} not "
                       "in vocabulary")
        if (c["M"] == 1) != (c["status"] == "DERIVED"):
            why.append(f"{key}: M/status coupling broken")
    for key, v in r_cas["J"]["pair"].items():
        if v not in ts.J_PAIR_TYPES:
            why.append(f"J.pair {key}: {v!r} not in vocabulary")
    for cls, v in r_cas["J"]["sign"].items():
        if v not in ts.SIGN_TYPES:
            why.append(f"J.sign {cls}: {v!r} not in vocabulary")
    for cls, v in r_cas["J"]["dual_present"].items():
        if type(v) is not bool:
            why.append(f"J.dual_present {cls}: not a bool")
    return why


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    gates = []
    artifacts = {}

    def gate(gid, ok, fail_status, detail):
        gates.append({"gate": gid, "pass": bool(ok),
                      "fail_status": fail_status, "detail": detail})
        print(f"[{gid}] {'PASS' if ok else 'FAIL -> ' + fail_status} "
              f"| {detail}")
        return ok

    # ---- G-C0-1: structure derivation + strengthened schema -----------------
    r_cas = ts.build_r_cas()
    schema_why = check_r_cas_schema(r_cas)
    n_derived = sum(1 for c in r_cas["cells"].values()
                    if c["status"] == "DERIVED")
    artifacts["R_CAS.json"] = jdump(r_cas, OUT / "R_CAS.json")
    gate("G-C0-1", not schema_why and n_derived == 4,
         "TIER_C_CONSTRUCTION_FAILED",
         f"{n_derived}/16 cells DERIVED with source rules; all typed "
         f"fields vocabulary-checked; M int 0/1 with status coupling; "
         f"no continuous strengths"
         + ("" if not schema_why else f"; defects: {schema_why}"))

    # ---- G-C0-2/3/4: PROOF_OF_NON_EQUIVARIANCE ------------------------------
    proof = tn.run_proof(r_cas)
    artifacts["PROOF_OF_NON_EQUIVARIANCE.json"] = jdump(
        proof, OUT / "PROOF_OF_NON_EQUIVARIANCE.json")
    g = proof["gates"]
    auto = proof["structure_automorphisms"]
    jcc = proof["join_cell_counterfactual"]
    gate("G-C0-2", g["G_C0_2_automorphism_trivial"],
         "TIER_C_CONSTRUCTION_FAILED",
         f"Aut(R_CAS) = {auto['automorphisms']} (size {auto['group_size']})"
         f"; join-cell counterfactual disclosed: M-only without (^6,^6) -> "
         f"{jcc['m_only_automorphisms_without_join']}, full R without it "
         f"trivial: {jcc['full_structure_trivial_without_join']}")
    ta = {k: v["test_a_max_divergence"]
          for k, v in proof["transforms"].items()}
    gate("G-C0-3", g["G_C0_3_test_a_all_transforms"]
         and g["recipe_validity"], "TIER_C_CONSTRUCTION_FAILED",
         f"Test A max per-example divergence per transform {ta} (tol "
         f"{tn.TOL_A}); no-structure recipe validity max "
         f"{proof['recipe_validity_no_structure']['max_divergence']:.3g}")
    tb = {k: v["test_b_min_divergence_non_automorphism"]
          for k, v in proof["transforms"].items()}
    gate("G-C0-4", g["G_C0_4_test_b_all_transforms"],
         "TIER_C_CONSTRUCTION_FAILED",
         f"Test B min per-example divergence (non-automorphism, min over "
         f"{len(tn.DATA_SEEDS)} data seeds) per transform {tb} (floor "
         f"{tn.FLOOR_B}); view groups all trivial: "
         f"{all(v['view_group_trivial'] for v in proof['transforms'].values())}")

    # ---- G-C0-5a: control pool / G-C0-5b: R_EMPIRICAL -----------------------
    manifest, r_random, _pool = tc.build_pool(r_cas)
    artifacts["CONTROL_POOL_MANIFEST.json"] = jdump(
        manifest, OUT / "CONTROL_POOL_MANIFEST.json")
    if r_random is not None:
        artifacts["R_RANDOM.json"] = jdump(r_random, OUT / "R_RANDOM.json")
    rr_sha = (manifest["r_random_canonical_sha256"][:16] + "..."
              if manifest["r_random_canonical_sha256"] else "NONE")
    gate("G-C0-5a", manifest["sufficient"], "CONTROL_POOL_INSUFFICIENT",
         f"pool {manifest['pool_size']} matched non-isomorphic controls "
         f"(target {manifest['target']}); R_RANDOM sha {rr_sha} "
         f"[{manifest['r_random_classification']}]")
    r_emp = ts.build_r_empirical(HERE / "data" / "train.jsonl")
    artifacts["R_EMPIRICAL.json"] = jdump(r_emp, OUT / "R_EMPIRICAL.json")
    overlap = ts.overlap_report(r_cas, r_emp)
    artifacts["R_EMPIRICAL_OVERLAP.json"] = jdump(
        overlap, OUT / "R_EMPIRICAL_OVERLAP.json")
    c50 = tc.build_r_corrupted50(r_cas)
    artifacts["R_CORRUPTED50.json"] = jdump(c50, OUT / "R_CORRUPTED50.json")
    emp_auto = ts.automorphism_report(r_emp)
    gate("G-C0-5b", emp_auto["trivial"], "TIER_C_CONSTRUCTION_FAILED",
         f"R_EMPIRICAL from {r_emp['n_trace_records_used']} traces "
         f"(slot/pool-typed estimator law), M/C overlap "
         f"{overlap['m_cells_equal']}/16 cells (MEASURED, estimator has no "
         f"family->type table), J planes equal: {overlap['j_planes_equal']}"
         f", Aut trivial: {emp_auto['trivial']}; R_CORRUPTED50 v2 "
         f"cell-transplant law: corruption counts {c50['corruption_counts']}"
         f", defined density {c50['defined_cell_density']}/16 (R_CAS 4/16)")

    # ---- G-C0-6: QC_VALID ---------------------------------------------------
    qc_train = qc.build_qc_split("train")
    qc_val = qc.build_qc_split("val")
    g_train = qc.qc_gates(qc_train, r_cas)
    g_val = qc.qc_gates(qc_val, r_cas)
    surface = qc.qc_surface_ceiling(qc_train, qc_val)
    for name, recs in (("qc_valid_train.jsonl", qc_train),
                       ("qc_valid_val.jsonl", qc_val)):
        body = canonical_jsonl(recs)
        write_utf8_lf(OUT / name, body)
        artifacts[name] = hashlib.sha256(body.encode()).hexdigest()
    artifacts["QC_VALID_GATES.json"] = jdump(
        {"train": g_train, "val": g_val, "surface_ceiling": surface},
        OUT / "QC_VALID_GATES.json")
    gate("G-C0-6", g_train["pass"] and g_val["pass"],
         "TIER_C_CONSTRUCTION_FAILED",
         f"train {g_train['n_records']} recs rt={g_train['roundtrip_pass_rate']:.3f} "
         f"balance={g_train['balance_valid_fraction']:.3f} "
         f"oracle={g_train['r_only_oracle_accuracy']:.3f} "
         f"gold-first={g_train['gold_candidate_first_fraction']:.3f} "
         f"pid-decorrelated={g_train['pid_tag_decorrelated']}; "
         f"val {g_val['n_records']} recs rt={g_val['roundtrip_pass_rate']:.3f} "
         f"gold-first={g_val['gold_candidate_first_fraction']:.3f}; "
         f"surface ceiling (disclosure): char-ngram "
         f"{surface['char_ngram_val_accuracy']:.4f}, length-order rule "
         f"{surface['length_order_rule_val_accuracy_best_side']:.4f}; "
         f"diagnostic-only, contrast readout")

    # ---- G-C0-7: R-only shortcut probe on primary families ------------------
    probe = rp.run_probe(HERE / "data" / "train.jsonl",
                         HERE / "data" / "val.jsonl")
    probe["library_versions"] = library_versions()
    artifacts["RONLY_PROBE.json"] = jdump(probe, OUT / "RONLY_PROBE.json")
    pf = {k: f"{v['accuracy']:.4f} (chance {v['candidate_chance']:.4f}, "
             f"bound {v['bound']:.4f})"
          for k, v in probe["per_family"].items()}
    gate("G-C0-7", probe["pass"], "RONLY_SHORTCUT_DETECTED",
         f"per-family: {pf}")

    # ---- G-C0-8: cache-binding law ------------------------------------------
    cbt = cbind.unit_tests()
    artifacts["CACHE_BINDING_TESTS.json"] = jdump(
        cbt, OUT / "CACHE_BINDING_TESTS.json")
    n_classes = sum(1 for k, v in cbt.items()
                    if v is True and k not in ("clean_pass", "pass"))
    gate("G-C0-8", cbt["pass"], "TIER_C_CONSTRUCTION_FAILED",
         f"clean verify + {n_classes} violation classes each rejected "
         f"fail-closed (incl. duplicate pids and model/tokenizer/"
         f"extraction sha checks)")

    # ---- G-C0-9: mutation battery -------------------------------------------
    battery = tm.run_battery()
    artifacts["TIERC_MUTATION_BATTERY.json"] = jdump(
        battery, OUT / "TIERC_MUTATION_BATTERY.json")
    gate("G-C0-9", battery["pass"], "TIER_C_CONSTRUCTION_FAILED",
         f"{battery['n_detected']}/5 mutants detected under the 7-point law "
         f"with per-point MEASURED/BY_CONSTRUCTION basis "
         f"({', '.join(m['mutant'] for m in battery['mutants'])})")

    # ---- receipt (deterministic bytes; wall clock to stdout only) -----------
    failed = [g_ for g_ in gates if not g_["pass"]]
    verdict = failed[0]["fail_status"] + f" (gate {failed[0]['gate']})" \
        if failed else "TIER_C_C0_READY_FOR_FOCUSED_REVIEW"
    receipt = {"receipt_id": "TIER_C_C0_RECEIPT",
               "non_claim_bearing": True,
               "spec": "TIER_C_SPEC_v0_2.md",
               "owner_authorization": "TIER C v0.2 -- C0 CONSTRUCTION "
                                      "AUTHORIZED (2026-09-01); C1/C2 GPU "
                                      "NOT YET AUTHORIZED",
               "compute": "local CPU only, $0; no GPU; no protected read; "
                          "no claim promotion",
               "library_versions": library_versions(),
               "gates": gates, "verdict": verdict,
               "artifact_sha256": artifacts}
    jdump(receipt, OUT / "TIER_C_C0_RECEIPT.json")
    print(f"\nVERDICT: {verdict}  (wall {round(time.time() - t0, 1)}s -- "
          f"stdout only, receipt is byte-deterministic)")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
