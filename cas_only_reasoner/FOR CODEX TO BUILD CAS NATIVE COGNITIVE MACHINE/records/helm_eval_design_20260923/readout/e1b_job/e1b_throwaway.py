"""A tiny THROWAWAY fixture for the E1b laptop acceptance run. Never a result; never sealed material.

Label: CLAUDE_BUILT_CLAUDE_CHECKED. Everything here is drawn from a PUBLIC seed string ("E1B-THROWAWAY|" + seed), so
it can never reproduce the sealed TEST. The fixture has the SHAPE of the real inputs:
  * THROWAWAY_HSET2_SEALED_TEST.json: splits, items (with evaluation.admissible_values) and claim-cell cluster tables
    with every registered bar's per-cluster verdict (random, public), in the builder's schema and field names;
  * THROWAWAY_HSET2_BUILD_SUMMARY.json: the "before any model" table, computed with the builder's OWN floor_block and
    views_block on those clusters, and bound to the sealed file by its sha256 as the builder binds them;
  * runs, stand-in strengths, the four prerequisite records and three H1/H2 documents (gate rows made by the wave-1
    reader's own `paired_regression`), for one named scenario;
  * touched-world files for stage 0 (optionally with a planted collision: a relabelled TEST_NEW_6 class).
Its "packets" are tiny: an item carries no worlds, so the stand-in engine answers from the item's admissible values.
The folder it writes to must be outside every git work tree (e1b_machine refuses otherwise).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import e1b_scorer as S  # noqa: E402

PREFIX = "E1B-THROWAWAY|"
SCENARIOS = ("all_clear", "gate_open_no_ruling", "controls_not_admitted", "matched_start_failed", "custody_collision")
SIZES = {S.ANALOGY_CELL: 16, S.CORR6: 6, S.CORR5: 14, S.REACH_CELLS[0]: 14, S.REACH_CELLS[1]: 12}


def _rng(seed, *parts):
    return random.Random(int(hashlib.sha256("|".join((PREFIX + seed,) + parts).encode()).hexdigest(), 16))


def _dump(path, value):
    data = json.dumps(value, indent=1, sort_keys=True).encode("utf-8")
    pathlib.Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def shapes(seed, oracle, S0, n, count):
    """`count` distinct weakly connected DAG classes on n nodes (degrees <= 4), as class keys, in draw order."""
    rng, out, seen = _rng(seed, "shapes", str(n)), [], set()
    while len(out) < count:
        order = list(range(n))
        rng.shuffle(order)
        edges = [(order[i], order[j]) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.38]
        if not edges:
            continue
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x
        for a, b in edges:
            parent[find(a)] = find(b)
        ind = [sum(1 for _, b in edges if b == v) for v in range(n)]
        outd = [sum(1 for a, _ in edges if a == v) for v in range(n)]
        if len({find(v) for v in range(n)}) != 1 or max(ind + outd) > 4:
            continue
        key = S0.class_key(oracle.canonical_form(n, edges))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def build(seed, out_dir, hset2_dir, scenario="all_clear"):
    """Write the fixture for `scenario` into out_dir; return the machine's argv (minus the builder and output folders)
    and the paths a test needs. `hset2_dir`: the builder code at the pinned commit (hset2/, hset1a/, d1_acceptance/)."""
    if scenario not in SCENARIOS:
        raise ValueError(scenario)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    B, A = S.load_builder(hset2_dir)
    import hset2_stage0_public as S0
    import oracle_isomorphism as oracle
    sys.path.insert(0, str(HERE.parent / "h1h2"))
    import h1h2_paired as H
    three, four = B.reach_claim_names()
    six, five = shapes(seed, oracle, S0, 6, 120), shapes(seed, oracle, S0, 5, 60)
    test6, withheld6, public6 = six[:60], six[60:100], six[100:]
    test5, withheld5, public5 = five[:24], five[24:44], five[44:]
    group = {k: S0.group_key(S0.key_shape(k)) for k in six + five}

    def distinct_group_foci(pool, count):
        chosen, used = [], set()
        for k in pool:
            if group[k] not in used:
                chosen.append(k)
                used.add(group[k])
            if len(chosen) == count:
                break
        return chosen

    bars = {S.ANALOGY_CELL: list(B.analogy_comparators()), S.CORR6: list(B.CORRESPONDENCE_COMPARATORS),
            S.CORR5: list(B.CORRESPONDENCE_COMPARATORS)}
    reach_bars = list(B.reach_comparators())
    items, clusters = [], {}
    for cell, size in SIZES.items():
        split, name = cell.split("/")
        pool = test5 + withheld5 if split == "TEST_NEW_5" else test6
        foci = distinct_group_foci(pool, size) if cell == S.ANALOGY_CELL else [pool[i % len(pool)] for i in range(size)]
        rng = _rng(seed, "cell", cell)
        names = reach_bars if cell in S.REACH_CELLS else bars[cell]
        right_count = {x: rng.randint(0, 2) for x in names}                 # every bar is wrong on most clusters
        rows = []
        for idx, focus in enumerate(foci):
            cid = "%s|%s|%s" % (split, name, hashlib.sha256((seed + cell + str(idx)).encode()).hexdigest()[:16])
            filler = withheld6[(idx * 7 + len(name)) % len(withheld6)] if split == "TEST_NEW_6" else withheld5[idx % len(withheld5)]
            c = {"cluster_id": cid, "split": split, "cell": name, "shape_key": focus,
                 "comparators": {x: idx < right_count[x] for x in names}}
            if cell in S.REACH_CELLS:
                c.update(role="PRIMARY", group_key=None, view_group=group[focus], role_classes=[focus],
                         state=("ABSENT", "DIRECT", "VIA")[idx % 3], whole=0)
                statuses = [None]
            else:
                c.update(group_key=group[focus], view_group=group[focus], role_classes=sorted({focus, filler}),
                         with_distractor=idx % 2 == 0, items=[])
                statuses = ["MATCH", "NO_MATCH"] if cell == S.ANALOGY_CELL else ["MAPPING", "NO_MATCH"]
            for status in statuses:
                for pres in (0, 1):
                    iid = "%s|%spres%d" % (cid, (status + "|") if status else "", pres)
                    if status in (None,):
                        value = {"state": c["state"], "via": None}
                    elif status == "MATCH":
                        value = {"world_id": "world-%s" % hashlib.sha256((iid + "p").encode()).hexdigest()}
                    elif status == "MAPPING":
                        value = {"status": "MAPPING", "pairs": [{"source": "a", "target": "b%d" % idx}]}
                    else:
                        value = {"world_id": None} if cell == S.ANALOGY_CELL else {"status": "NO_MATCH", "pairs": []}
                    items.append({"item_id": iid, "cluster_id": cid, "split": split, "cell": name, "presentation": pres,
                                  "kind": "reach" if cell in S.REACH_CELLS else name.lower(), "status": status,
                                  "evaluation": {"admissible_values": [value], "record_id": "typed-input-throwaway-" + iid,
                                                 "packet_sha256": hashlib.sha256(iid.encode()).hexdigest()}})
                    if "items" in c:
                        c["items"].append(iid)
            rows.append(c)
        if cell in S.REACH_CELLS:                                            # two surplus clusters, never read
            rows += [dict(rows[0], cluster_id=rows[0]["cluster_id"] + "-surplus%d" % k, role="SURPLUS_NON_TIE")
                     for k in range(2)]
            items += [dict(it, item_id=it["item_id"] + "-surplus%d" % k, cluster_id=it["cluster_id"] + "-surplus%d" % k)
                      for k in range(2) for it in items if it["cluster_id"] == rows[0]["cluster_id"]]
        clusters[cell] = rows

    # ---- the sealed file, with the identity the builder records
    identity = dict(S.builder_identity(B), mode="THROWAWAY_SALTS_NOT_A_BUILD", label=S.LABEL,
                    registered_comparators=B.registered_comparators())
    names_out = B.output_names("THROWAWAY_SALTS_NOT_A_BUILD")
    sealed_path = out / names_out["sealed"]
    sealed_sha = _dump(sealed_path, {"schema": S.SEALED_SCHEMA, "custody": "THROWAWAY_NOT_SEALED", "label": S.LABEL,
                                     "identity": identity,
                                     "splits": {"TEST_NEW_6": test6, "WITHHELD_6": withheld6, "TEST_NEW_5": test5,
                                                "WITHHELD_5": withheld5},
                                     "items": items, "clusters": clusters})

    # ---- the public summary, from the builder's own floor functions
    cells = {}
    for cell in S.CLAIM_CELLS:
        members = [c for c in clusters[cell] if c.get("role", "PRIMARY") == "PRIMARY"]
        if cell in S.REACH_CELLS:
            s = {"claims": {}}
            for claim, cbars in B.reach_claim_bars().items():
                block = B.floor_block(A, members, list(cbars))
                block["a2_views"] = B.views_block(members, list(cbars))
                s["claims"][claim] = block
            s["can_carry_a_claim"], s["why_not"] = s["claims"][three]["can_carry_a_claim"], s["claims"][three]["why_not"]
        else:
            s = B.floor_block(A, members, bars[cell], need_groups=cell == S.ANALOGY_CELL)
            s["a2_views"] = B.views_block(members, bars[cell], confirmatory_analogy=cell == S.ANALOGY_CELL)
            if cell == S.ANALOGY_CELL:
                s["distractor_split_diagnostic"] = {
                    half: B.floor_block(A, [c for c in members if c["with_distractor"] == flag], bars[cell], need_groups=True)
                    for half, flag in S.HALVES}
        cells[cell] = s
    claim_cells = {three: S.REACH_CELLS, four: S.REACH_CELLS, "ANALOGY_BEYOND_DEGREE_6": (S.ANALOGY_CELL,),
                   "CORRESPONDENCE_BEYOND_DEGREE_6": (S.CORR6,), "CORRESPONDENCE_BEYOND_DEGREE_5": (S.CORR5,)}
    cbm = {}
    for claim, cs in claim_cells.items():
        floors = [cells[c]["claims"][claim] if "claims" in cells[c] else cells[c] for c in cs]
        cbm[claim] = {"cells": list(cs), "can_carry_a_claim_before_any_model": all(f["can_carry_a_claim"] for f in floors)}
    for claim, why in B.DECLARED_NOT_TESTABLE.items():
        cbm[claim] = {"cells": [], "can_carry_a_claim_before_any_model": False, "declared_before_any_build": why}
    an = cells[S.ANALOGY_CELL]
    reasons = ([] if an["can_carry_a_claim"] else ["original floor: %s" % an["why_not"]]) + [
        "A2.4: %s" % r for r in an["a2_views"]["floors"]["not_testable_reasons"]]
    cbm[S.CONFIRMATORY] = {"cells": [S.ANALOGY_CELL], "can_carry_a_claim_before_any_model": not reasons,
                           "not_testable_reasons": reasons}
    v_cells = sorted({c for claim, cs in claim_cells.items() for c in cs
                      if (cells[c]["claims"][claim] if "claims" in cells[c] else cells[c])["can_carry_a_claim"]})
    summary = {"schema": B.SCHEMA_SUMMARY, "label": S.LABEL, "mode": "THROWAWAY_SALTS_NOT_A_BUILD", "build_ok": True,
               "identity": identity, "files": {names_out["sealed"]: sealed_sha}, "cells": cells,
               "claims_before_any_model": cbm,
               "no_regression_gates": {"V": [{"cell": c} for c in v_cells],
                                       "left_out_cells_cannot_carry_a_claim": [c for c in S.CLAIM_CELLS if c not in v_cells],
                                       "smallest_detectable_regression_c_prime_with_b_prime_0": 7},
               "throwaway_warning": "THROWAWAY_NOT_DEV"}
    summary_path = out / names_out["summary"]
    _dump(summary_path, summary)
    public_cells_path = out / names_out["public"]
    _dump(public_cells_path, {"schema": "claude.hset2-public-cells/0.1", "items": [], "clusters": {}})

    # ---- runs and stand-in strengths (repaired strong on analogy; both arms identical elsewhere: no regression)
    run_rows = []
    for seed_n in S.SEEDS:
        tail = str(seed_n)[-2:]
        run_rows += [{"run_id": "R" + tail, "arm": "repaired", "seed": seed_n, "provenance": "fresh_repaired",
                      "switch": True, "checkpoint": None},
                     {"run_id": ("U" if seed_n == S.SEEDS[0] else "H") + tail, "arm": "unchanged", "seed": seed_n,
                      "provenance": "fresh_unchanged" if seed_n == S.SEEDS[0] else "historical_helm2", "switch": False,
                      "checkpoint": None}]
    for r in run_rows:
        r["checkpoint_sha256"] = hashlib.sha256(("throwaway-checkpoint-" + seed + r["run_id"]).encode()).hexdigest()
    runs_path = out / "runs.json"
    _dump(runs_path, {"schema": S.SCHEMA_RUNS, "runs": run_rows, "note": "THROWAWAY: no checkpoint exists"})
    strength = {}
    for r in run_rows:
        rep = r["arm"] == "repaired"
        strength[r["run_id"]] = {c: {"p": 0.7, "key": "shared-%d" % r["seed"]} for c in S.CLAIM_CELLS}
        strength[r["run_id"]][S.ANALOGY_CELL] = {"p": 1.0 if rep else 0.0, "key": r["run_id"]}
    strength_path = out / "stand_in_strength.json"
    _dump(strength_path, strength)

    # ---- prerequisites for the scenario
    finals = {r["seed"]: r["checkpoint_sha256"] for r in run_rows if r["arm"] == "repaired"}
    cleared = scenario != "gate_open_no_ruling"
    entries = [{"model_seed": s, "checkpoint_relative_path": p, "main_updates": u,
                "checkpoint_sha256": finals[s] if p == "final.pt" else hashlib.sha256((p + str(s)).encode()).hexdigest(),
                "verdict": "PRESENT_GRAPH_AND_DOMAIN" if cleared or p != "final.pt" else "ABSENT", "problems": []}
               for s in S.SEEDS for p, u in (("pass_01.pt", 147), ("evidence/main_checkpoint_0294.pt", 294),
                                             ("evidence/main_checkpoint_0588.pt", 588),
                                             ("evidence/main_checkpoint_0882.pt", 882),
                                             ("evidence/main_checkpoint_1176.pt", 1176), ("final.pt", 1470))]
    paths = {"item2": out / "item2_reading.json", "matched": out / "matched_start.json",
             "repro": out / "reproduction_reading.json", "ruling": out / "inference_ruling.json"}
    _dump(paths["item2"], {"schema": S.SCHEMA_ITEM2, "outcome": "ITEM2_PASS" if cleared else "ITEM2_FAIL:20260917/final.pt=ABSENT",
                           "mechanism_gate": "CLEARED" if cleared else "MECHANISM_GATE_OPEN",
                           "historical_gate_on_repaired_arm": "MAY_RUN_FROZEN_EVALUATE_GATES" if cleared else "G_LEARN_ON_NOT_READ",
                           "entries": entries, "labels": ["THROWAWAY"]})
    _dump(paths["matched"], {"schema": S.SCHEMA_MATCHED_START, "verdict": "MATCHED_START_NOT_REPRODUCED"
                             if scenario == "matched_start_failed" else S.MATCHED})
    _dump(paths["repro"], {"schema": S.SCHEMA_REPRODUCTION, "verdict": "DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY"
                           if scenario == "controls_not_admitted" else S.REPRODUCED_U17})
    _dump(paths["ruling"], {"schema": S.SCHEMA_INFERENCE_RULING, "ruling": "SUPPORTED",
                            "ruled_by": "THROWAWAY_FIXTURE_NOT_A_RULING", "basis": "throwaway fixture"})
    h1h2 = {}
    kinds = {"q%02d" % i: ("analogy" if i < 5 else "reach") for i in range(45)}
    for s in S.SEEDS:
        rng = _rng(seed, "h1h2", str(s))
        unchanged = {q: rng.random() < 0.6 for q in kinds}
        repaired = dict(unchanged)
        gates = []
        for gate, keys in (("H1", sorted(kinds)[:18]), ("H2", sorted(kinds))):
            view_keys = keys if cleared else [q for q in keys if kinds[q] != "analogy"]
            row = H.paired_regression(unchanged, repaired, view_keys, kinds)
            row.update(gate=gate, historical_gate="G_LEARN_population" if gate == "H1" else "G_LEARN_all_kinds",
                       question_set=gate if cleared else gate + "_non_analogy")
            gates.append(row)
        h1h2[s] = out / ("h1h2_%d.json" % s)
        _dump(h1h2[s], {"reader": H.READER, "status": "READ", "seed": s, "claim_bearing_inputs": True,
                        "view": "REGISTERED_H1_H2" if cleared else "NON_ANALOGY_VIEW_EXPLORATORY", "gates": gates,
                        "old_gate_crossings": {"status": "READ" if cleared else "NOT_SHOWN_IN_NON_ANALOGY_VIEW",
                                               "crossings": []}})

    # ---- touched worlds (stage 0)
    def built(n, edges, tag):
        refs = ["%s/n%d" % (tag, i) for i in range(n)]
        return {"world_id": tag, "nodes": [{"ref": r} for r in refs],
                "contains": [{"source": refs[a], "target": refs[b]} for a, b in edges]}
    course = {"packets": [{"source": {"worlds": [built(4, [(0, 1), (0, 2), (2, 3)], "w-a"), built(3, [(0, 1), (1, 2)], "w-b")]}}]}
    fixture = {"shapes": {"P%d" % i: {"nodes": S0.key_shape(k)[0], "edges": [list(e) for e in S0.key_shape(k)[1]]}
                          for i, k in enumerate(public6[:6] + public5[:4])}}
    if scenario == "custody_collision":
        n, edges = S0.key_shape(test6[3])
        perm = list(range(n))[::-1]
        fixture["planted"] = {"labels": ["x%d" % i for i in range(n)], "edges": [[perm[a], perm[b]] for a, b in edges]}
    touched_paths = {"updates": out / "touched_course.json", "fixture": out / "touched_fixtures.json",
                     "probe": out / "touched_probe.json"}
    _dump(touched_paths["updates"], course)
    _dump(touched_paths["fixture"], fixture)
    _dump(touched_paths["probe"], {"bank": [public6[10], public5[5]]})
    touched = ["updates=%s" % touched_paths["updates"], "development_evaluation=%s" % touched_paths["updates"],
               "dev_reading=NONE:throwaway fixture: no DEV reading", "probe=%s" % touched_paths["probe"],
               "smoke=NONE:throwaway fixture: no smoke input", "fixture=%s" % touched_paths["fixture"]]
    argv = ["--sealed-file", str(sealed_path), "--build-summary", str(summary_path), "--public-cells", str(public_cells_path),
            "--runs", str(runs_path), "--item2-reading", str(paths["item2"]), "--matched-start", str(paths["matched"]),
            "--reproduction-reading", str(paths["repro"]), "--stand-in-seed", seed,
            "--stand-in-strength", str(strength_path)]
    if scenario != "gate_open_no_ruling":
        argv += ["--inference-ruling", str(paths["ruling"])]
    for s in S.SEEDS:
        argv += ["--h1h2", "%d=%s" % (s, h1h2[s])]
    for t in touched:
        argv += ["--touched", t]
    return {"argv": argv, "sealed": sealed_path, "summary": summary_path, "items": items, "test6": test6}
