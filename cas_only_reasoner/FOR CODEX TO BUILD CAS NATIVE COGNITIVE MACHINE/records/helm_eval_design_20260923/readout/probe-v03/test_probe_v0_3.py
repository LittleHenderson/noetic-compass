"""Unit controls for probe v0.3 (PREREG_ANALOGY_WIRING_PROBE_v0_3.md section 8). Pure Python: no torch, no course
material, no model, no GPU, no network; seconds. Run once:  python -B -m pytest -q -p no:cacheprovider test_probe_v0_3.py

The five acceptance controls are tests 1-5. v0.2's reading of the same tables is computed with v0.2's OWN functions
(`zscores`, `discordant_fraction`, `set_contrast`, constants) imported from the frozen v0.2 file, following
`probe_one`'s arithmetic line for line, so every "v0.2 would ..." statement below is measured, not assumed.
"""
import copy
import functools
import hashlib
import importlib.util
import json
import math
import pathlib
import statistics
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import item2_reader  # noqa: E402
import probe_v0_3_harness as harness  # noqa: E402
import probe_v0_3_metric as metric  # noqa: E402
import toy_bank as toy  # noqa: E402

V02_PATH = HERE.parents[1] / "analogy_wiring_probe" / "analogy_wiring_probe_v0_2.py"
KINDS = ("HELM_LIKE", "POSITIVE", "ANTI", "DOMAIN_ANTI", "UNIFORM", "COUPLED", "STRONG_OWN", "HIDDEN_AFFINE")
CANDIDATE_INDEPENDENT = ("HELM_LIKE", "POSITIVE", "ANTI", "DOMAIN_ANTI", "UNIFORM", "STRONG_OWN")


@functools.lru_cache(maxsize=None)
def v02():
    spec = importlib.util.spec_from_file_location("analogy_wiring_probe_v0_2_frozen", V02_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # module level imports the standard library only; torch is inside main()
    return module


@functools.lru_cache(maxsize=None)
def table(kind):
    return toy.build_table(kind)


@functools.lru_cache(maxsize=None)
def result(kind):
    return metric.evaluate(table(kind))


def v02_reading(t):
    """v0.2's `probe_one` arithmetic (lines 226-343 of analogy_wiring_probe_v0_2.py) applied to a score table."""
    v = v02()
    recs, foci = t["records"], t["foci"]
    base_s = {rid: r["base"] for rid, r in recs.items()}
    delta0 = max(max(abs(r["base"][c] - r["base_repeat"][c]) for c in r["base"]) for r in recs.values())
    per_focus = {}
    for f in sorted(foci):
        F = foci[f]
        rid, meta = F["record"], F["worlds"]
        domain = {w: m["domain"] for w, m in meta.items()}
        shape = {w: metric.shape_key(m["shape"]) for w, m in meta.items()}
        n = meta[f]["nodes"]
        X = [c for c in base_s[rid] if c != f and domain[c] != domain[f]]
        z0 = v.zscores(base_s[rid], X)
        A = [c for c in X if shape[c] == shape[f]]
        m3, kf, rcs, leaks = 0.0, 0.0, [], []
        for g in F["graph"]:
            new_shape = metric.canon(n, g["edges"])
            z = v.zscores(g["scores"], X)
            dz = {c: z[c] - z0[c] for c in X}
            m3 = max(m3, max(abs(x) for x in dz.values()))
            kf = max(kf, v.discordant_fraction(z0, z, X))
            A2 = [c for c in X if shape[c] == new_shape]
            rc = v.set_contrast(dz, A, A2)
            if rc is not None:
                rcs.append(rc)
        if F["bystander"]:
            b = F["bystander"]["world"]
            for run in F["bystander"]["runs"]:
                z = v.zscores(run["scores"], X)
                leaks.append(max(abs(z[c] - z0[c]) for c in X if c != b))
        rc_dom = []
        X_all = [c for c in base_s[rid] if c != f]
        zb_all = v.zscores(base_s[rid], X_all)
        for d in F["domain"]:
            z = v.zscores(d["scores"], X_all)
            dz = {c: z[c] - zb_all[c] for c in X_all}
            now_invalid = [c for c in X_all if shape[c] == shape[f] and domain[c] == d["domain"]]
            now_valid = [c for c in X_all if shape[c] == shape[f] and domain[c] == domain[f]]
            rc = v.set_contrast(dz, now_invalid, now_valid)
            if rc is not None:
                rc_dom.append(rc)
        per_focus[f] = {"M3z": m3, "K": kf, "RC": statistics.fmean(rcs) if rcs else None,
                        "L": max(leaks) if leaks else None,
                        "RC_dom": statistics.fmean(rc_dom) if rc_dom else None}
    wa_id, wb_id = t["witnesses"]
    fa, fb = recs[wa_id]["focus"], recs[wb_id]["focus"]
    wa, wb = base_s[wa_id], base_s[wb_id]
    dom_all = recs[wa_id]["candidate_domains"]
    Xw = [c for c in wa if c not in (fa, fb) and dom_all[c] != dom_all[fa] and dom_all[c] != dom_all[fb]]
    za, zb = v.zscores(wa, Xw), v.zscores(wb, Xw)
    m1z = max(abs(za[c] - zb[c]) for c in Xw)
    received = {}
    for rid, r in recs.items():
        f, dom = r["focus"], r["candidate_domains"]
        X = [c for c in r["base"] if c != f and dom[c] != dom[f]]
        for c, val in v.zscores(r["base"], X).items():
            received.setdefault((dom[f], c), []).append(val)
    m2z = max(max(x) - min(x) for x in received.values())
    floor = max(1e-3, 100 * delta0)
    items = list(per_focus.values())
    count = lambda pred: sum(1 for p in items if pred(p))  # noqa: E731
    rc_vals = [p["RC"] for p in items if p["RC"] is not None]
    summary = {"K_positive": count(lambda p: p["K"] > 0), "M3z_above_floor": count(lambda p: p["M3z"] >= floor),
               "median_RC": statistics.median(rc_vals) if rc_vals else None,
               "bystander_ok": count(lambda p: p["L"] is not None and p["L"] <= v.LEAK_RATIO * p["M3z"]),
               "RC_dom_ok": count(lambda p: p["RC_dom"] is not None and p["RC_dom"] >= v.RC_MIN),
               "max_L": max(p["L"] for p in items if p["L"] is not None)}
    graph_core = (summary["K_positive"] >= v.SHARE_FOCI and summary["M3z_above_floor"] >= v.SHARE_FOCI
                  and summary["median_RC"] is not None and summary["median_RC"] >= v.RC_MIN)
    if delta0 > v.NOISE_MAX:
        verdict = "INVALID_NONDETERMINISTIC"
    elif m1z <= v.TAU and m2z <= v.TAU and all(p["M3z"] <= v.TAU and p["K"] == 0 for p in items):
        verdict = "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
    elif graph_core and summary["bystander_ok"] >= v.SHARE_FOCI:
        verdict = "PRESENT_GRAPH_AND_DOMAIN" if summary["RC_dom_ok"] >= v.SHARE_FOCI else "PRESENT_GRAPH"
    elif graph_core:
        verdict = "COUPLED_NOT_COMPARISON"
    else:
        verdict = "MIXED"
    return {"verdict": verdict, "summary": summary, "per_focus": per_focus}


def bystander_reference(t, f):
    """sigma0(X without b) and X without b, computed here independently of the metric."""
    F = t["foci"][f]
    base = t["records"][F["record"]]["base"]
    dom = t["records"][F["record"]]["candidate_domains"]
    X = sorted(c for c in base if c != f and dom[c] != dom[f])
    b = F["bystander"]["world"]
    R = [c for c in X if c != b]
    return statistics.pstdev([base[c] for c in R]), R, b


# ============================================================ control 1: bystander interaction exactly 0
@pytest.mark.parametrize("kind", CANDIDATE_INDEPENDENT)
def test_1_candidate_independent_scorer_gives_bystander_interaction_exactly_zero(kind):
    t = table(kind)
    for f, F in t["foci"].items():  # the raw fact first: no other candidate's raw score moves
        base = t["records"][F["record"]]["base"]
        for run in F["bystander"]["runs"]:
            assert all(run["scores"][c] == base[c] for c in base if c != F["bystander"]["world"])
    r = result(kind)
    assert all(p["L"] == 0.0 for p in r["per_focus"].values())
    assert r["summary"]["max_L"] == 0.0


def test_1b_v02_reads_a_nonzero_leak_on_the_same_candidate_only_table():
    old = v02_reading(table("HELM_LIKE"))
    assert old["summary"]["max_L"] > 1e-3            # v0.2's normalization artefact, reproduced
    assert result("HELM_LIKE")["summary"]["max_L"] == 0.0


# ============================================================ control 2: injected interaction k reads k / sigma0
@pytest.mark.parametrize("kappa", [0.5, -0.25, 3.0])
def test_2_injected_interaction_reads_k_over_sigma0(kappa):
    t = metric.inject_interaction(table("HELM_LIKE"), kappa)
    r = metric.evaluate(t)
    for f, p in r["per_focus"].items():
        sigma0, R, b = bystander_reference(t, f)
        assert p["L"] == abs(kappa) / sigma0
        assert p["sigma0_X_minus_bystander"] == sigma0
    q0, q1 = metric.scored_quantities(result("HELM_LIKE")), metric.scored_quantities(r)
    assert all(q0[k] == q1[k] for k in q0 if not k.startswith("L:"))


# ============================================================ control 3: a*s+b leaves every verdict unchanged
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("a", [3.0, 0.125])
def test_3_affine_transformation_leaves_every_verdict_unchanged(kind, a):
    before = result(kind)
    after = metric.evaluate(metric.affine(table(kind), a))
    assert after["verdict"] == before["verdict"]
    q0, q1 = metric.scored_quantities(before), metric.scored_quantities(after)
    moved = [k for k in q0 if not metric._close(q0[k], q1[k])]
    assert moved == []


def test_3b_offsets_really_differ_per_packet_and_depend_on_the_focus():
    keys = [["record", r] for r in toy.RECORD_IDS[:5]] + [["graph", f, 0] for f in toy.FOCI[:5]]
    assert len({metric.default_offset(k) for k in keys}) == len(keys)


def test_3c_noise_verdict_is_also_invariant():
    t = copy.deepcopy(table("POSITIVE"))
    rid = sorted(t["records"])[3]
    c = sorted(t["records"][rid]["base_repeat"])[5]
    t["records"][rid]["base_repeat"][c] += 0.001
    assert metric.evaluate(t)["verdict"] == "INVALID_NONDETERMINISTIC"
    assert metric.evaluate(metric.affine(t, 3.0))["verdict"] == "INVALID_NONDETERMINISTIC"


# ============================================================ control 4: the signed test has the right sign
def test_4_signed_test_detects_movement_toward_and_away_with_the_right_sign():
    pos, anti, dom_anti = result("POSITIVE"), result("ANTI"), result("DOMAIN_ANTI")
    assert pos["verdict"] == "PRESENT_GRAPH_AND_DOMAIN"
    assert pos["summary"]["median_RC_signed"] >= 1e-2 and pos["summary"]["RC_negative"] == 0
    assert pos["summary"]["RC_dom_ok"] == 24
    assert anti["verdict"] == "MOVES_AWAY_FROM_FAVOURED_SET"
    assert anti["summary"]["median_RC_signed"] <= -1e-2 and anti["summary"]["RC_positive"] == 0
    assert anti["summary"]["RC_dom_wrong_direction"] == 24
    for f in pos["per_focus"]:  # the per-focus signs are opposite (own terms cancel in a change)
        p, q = pos["per_focus"][f], anti["per_focus"][f]
        if p["RC"] is not None:
            assert p["RC"] > 0 > q["RC"]
            assert math.isclose(p["RC"] * p["sigma0_X"], -(q["RC"] * q["sigma0_X"]), rel_tol=1e-12)
        assert p["RC_dom"] > 0 > q["RC_dom"]
    assert dom_anti["verdict"] == "PRESENT_GRAPH"
    assert dom_anti["summary"]["RC_dom_wrong_direction"] == 24


def test_4b_v02_passes_the_sign_flipped_scorer():
    assert v02_reading(table("ANTI"))["verdict"] == "PRESENT_GRAPH_AND_DOMAIN"   # the defect v0.3 removes
    assert v02_reading(table("DOMAIN_ANTI"))["verdict"] == "PRESENT_GRAPH_AND_DOMAIN"   # wrong domain rule too
    assert v02_reading(table("POSITIVE"))["verdict"] == "PRESENT_GRAPH_AND_DOMAIN"


# ============================================================ control 5: v0.2's normalization confound
def test_5a_confound_false_coupling_no_longer_passes():
    old, new = v02_reading(table("STRONG_OWN")), result("STRONG_OWN")
    assert old["verdict"] == "COUPLED_NOT_COMPARISON"       # v0.2: a false coupling on a real comparison
    assert old["summary"]["bystander_ok"] < 22
    assert new["verdict"] == "PRESENT_GRAPH_AND_DOMAIN"
    assert new["summary"]["max_L"] == 0.0


def test_5b_confound_hidden_coupling_no_longer_passes():
    old, new = v02_reading(table("HIDDEN_AFFINE")), result("HIDDEN_AFFINE")
    assert old["verdict"] == "PRESENT_GRAPH_AND_DOMAIN"      # v0.2: re-standardising hides the coupling
    assert old["summary"]["max_L"] <= 1e-9
    assert new["verdict"] == "COUPLED_NOT_COMPARISON"
    assert new["summary"]["bystander_ok"] < 22 and new["summary"]["max_L"] > 0


# ============================================================ further controls
def test_no_dependency_and_coupled_controls():
    assert result("HELM_LIKE")["verdict"] == "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
    assert result("HELM_LIKE")["summary"]["max_M3z"] == 0.0
    assert result("UNIFORM")["verdict"] == "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
    assert result("COUPLED")["verdict"] not in ("PRESENT_GRAPH", "PRESENT_GRAPH_AND_DOMAIN")


def _refused(t):
    with pytest.raises(metric.TableRefused) as err:
        metric.evaluate(t)
    return err.value.code


def test_incomplete_or_altered_tables_are_refused():
    base = table("POSITIVE")
    f = toy.FOCI[5]
    t = copy.deepcopy(base); t["foci"][f]["graph"].pop()
    assert _refused(t).startswith("TABLE_GRAPH_RUNS")
    t = copy.deepcopy(base); t["foci"][f]["domain"].append(copy.deepcopy(t["foci"][f]["domain"][0]))
    assert _refused(t).startswith("TABLE_DOMAIN_RUNS")
    t = copy.deepcopy(base); t["foci"][f]["bystander"]["runs"].pop()
    assert _refused(t).startswith("TABLE_BYSTANDER_RUNS")
    t = copy.deepcopy(base); t["witnesses"] = list(reversed(t["witnesses"]))
    assert _refused(t) == "TABLE_WITNESSES"
    t = copy.deepcopy(base); del t["foci"][f]["graph"][0]["scores"]["w33"]
    assert _refused(t).startswith("TABLE_CANDIDATES")
    t = copy.deepcopy(base); t["foci"][f]["graph"][0]["scores"]["w33"] = 1
    assert _refused(t).startswith("TABLE_SCORE")
    t = copy.deepcopy(base); t["records"].pop(sorted(t["records"])[10])
    assert _refused(t) == "TABLE_RECORD_COUNT"
    t = copy.deepcopy(base); t["foci"][f]["worlds"]["w33"]["domain"] = "toy-domain-a"
    assert _refused(t).startswith("TABLE_DOMAIN_DISAGREES")


def test_harness_counterfactuals_reach_the_packet_and_leave_the_originals_untouched():
    pk = toy.packets()
    snapshot = json.dumps(pk, sort_keys=True)
    seen = []

    def spy(rid, packet, changed):
        seen.append((rid, changed, toy.meta_of(packet)))
        return {c: 0.0 for c in toy.BANK_META}

    t = harness.build_score_table(pk, harness.analogy_ids_of(pk), spy, toy.node_index, model={}, provenance={},
                                  witnesses=metric.RULES["witnesses"])
    assert json.dumps(pk, sort_keys=True) == snapshot
    assert len(seen) == 2 * 70 + sum(len(F["graph"]) + len(F["bystander"]["runs"]) + len(F["domain"])
                                     for F in t["foci"].values())
    it = iter(seen[140:])
    for f in sorted(t["foci"]):
        F = t["foci"][f]
        for g in F["graph"]:
            rid, changed, m = next(it)
            assert changed == f and m[f]["shape"] == metric.canon(m[f]["nodes"], g["edges"])
            assert all(m[w] == toy.BANK_META[w] for w in m if w != f)
        for run in F["bystander"]["runs"]:
            rid, changed, m = next(it)
            b = F["bystander"]["world"]
            assert changed == b and m[b]["shape"] == metric.canon(m[b]["nodes"], run["edges"])
            assert all(m[w] == toy.BANK_META[w] for w in m if w != b)
        for d in F["domain"]:
            rid, changed, m = next(it)
            assert changed == f and m[f]["domain"] == d["domain"] and m[f]["shape"] == toy.BANK_META[f]["shape"]
    star = [w for w in toy.WORLDS if w["world_id"] == toy.FOCI[1]][0]
    rewired = harness.rewire(star, ((0, 1), (1, 2), (2, 3)), toy.node_index)
    assert rewired["contains"][0]["source"] == star["declared_whole"]   # canonical node 0 sits on the whole


def _validation_raw(**swap):
    raw = {"V1_CONTROL_UNWRAPPED": table("HELM_LIKE"), "V2_POSITIVE_COMPARISON": table("POSITIVE"),
           "V3_ANTI_COMPARISON": table("ANTI"), "V4_NEGATIVE_UNIFORM": table("UNIFORM"),
           "V5_NEGATIVE_COUPLED": table("COUPLED")}
    raw.update(swap)
    return raw


def test_validation_reader_on_the_synthetic_controls():
    good = metric.evaluate_validation(_validation_raw(), "same", "same")
    assert good["validation"] == "VALIDATION_PASS", good["failed"]
    bad = metric.evaluate_validation(_validation_raw(V2_POSITIVE_COMPARISON=table("ANTI")), "same", "same")
    assert bad["validation"] == "VALIDATION_FAIL" and "V2_POSITIVE_COMPARISON" in bad["failed"]
    assert metric.evaluate_validation(_validation_raw(), "a", "b")["failed"] == ["SOURCE_UNCHANGED"]
    raw = _validation_raw()
    del raw["V5_NEGATIVE_COUPLED"]
    assert metric.evaluate_validation(raw, "s", "s")["failed"] == ["V5_NEGATIVE_COUPLED"]


# ============================================================ ITEM2
def _sha(i):
    return hashlib.sha256(b"toy-checkpoint-%d" % i).hexdigest()


def _with_model(t, sha, switch=True):
    out = dict(t)   # shallow: records and foci are shared, never mutated
    out["model"] = dict(t["model"], checkpoint_sha256=sha, switch=switch)
    return out


def _entries(kinds=None):
    kinds = kinds or {}
    rows = []
    for i, (seed, path, updates) in enumerate(item2_reader.REGISTERED_18):
        kind = kinds.get(i, "POSITIVE")
        rows.append({"model_seed": seed, "checkpoint_relative_path": path, "main_updates": updates,
                     "checkpoint_sha256": _sha(i), "receipt_root": "toy", "_kind": kind})
    return rows


def _loader(e):
    if "_table" in e:                     # a planted table is handed over exactly as built
        return e["_table"], []
    if e.get("_kind") is None:
        return None, ["SCORE_TABLE_MISSING"]
    return _with_model(table(e["_kind"]), e["checkpoint_sha256"]), []


ACCEPT = dict(metric.frozen_hashes(), schema=item2_reader.SCHEMA_ACCEPTANCE, accepted_by="codex")


def _read(entries, raw=None, acceptance=ACCEPT, source=("s", "s")):
    return item2_reader.item2(entries, _loader, raw or _validation_raw(), source, acceptance)


def test_item2_pass_clears_the_gate_only_with_acceptance():
    r = _read(_entries())
    assert r["outcome"] == "ITEM2_PASS" and r["mechanism_gate"] == "CLEARED", r["gate_open_reasons"]
    assert {e["analogy_numbers"] for e in r["entries"]} == {"ANALOGY_MAY_BE_READ"}
    assert r["historical_gate_on_repaired_arm"] == "MAY_RUN_FROZEN_EVALUATE_GATES"
    r = _read(_entries(), acceptance=None)
    assert r["outcome"] == "ITEM2_PASS" and r["mechanism_gate"] == "MECHANISM_GATE_OPEN"
    assert r["gate_open_reasons"] == ["PREREG_V0_3_NOT_ACCEPTED"]
    assert {e["analogy_numbers"] for e in r["entries"]} == {"ANALOGY_NOT_READ_GATE_OPEN"}
    assert r["prereg_status"] == "PROPOSED"


def test_item2_fail_keeps_every_failure_and_opens_the_gate():
    r = _read(_entries({8: "HELM_LIKE", 17: "STRONG_OWN"}))
    assert r["outcome"] == ("ITEM2_FAIL:20260918/evidence/main_checkpoint_0588.pt="
                            "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT")
    assert r["mechanism_gate"] == "MECHANISM_GATE_OPEN"
    assert r["entries"][8]["analogy_numbers"] == "ANALOGY_NOT_READ_WIRING_ABSENT"
    assert r["historical_gate_on_repaired_arm"] == "G_LEARN_ON_NOT_READ"
    assert r["confirmatory_claim"] == item2_reader.Q_J
    r = _read(_entries({0: "ANTI", 5: "COUPLED"}))
    assert r["outcome"].count("=") == 2 and "MOVES_AWAY_FROM_FAVOURED_SET" in r["outcome"]


def test_item2_invalid_missing_and_binding_problems():
    noisy = copy.deepcopy(_with_model(table("POSITIVE"), _sha(4)))
    rid = sorted(noisy["records"])[0]
    noisy["records"][rid]["base_repeat"]["w40"] += 0.5
    entries = _entries({3: "HELM_LIKE"})
    entries[4]["_table"] = noisy
    r = _read(entries)
    assert r["outcome"] == "ITEM2_INVALID" and r["entries"][4]["problems"] == []

    entries = _entries()
    entries[2]["_kind"] = None                          # table missing
    entries[5]["main_updates"] = 1469                   # wrong update count
    entries[7]["checkpoint_sha256"] = entries[6]["checkpoint_sha256"]   # one file read twice
    del entries[11]                                     # entry missing altogether
    r = _read(entries)
    assert r["outcome"].startswith("ITEM2_FAIL:")
    got = {(e["model_seed"], e["checkpoint_relative_path"]): e["problems"] for e in r["entries"]}
    assert got[(20260917, "evidence/main_checkpoint_0588.pt")] == ["SCORE_TABLE_MISSING"]
    assert got[(20260917, "final.pt")] == ["UPDATE_COUNT_MISMATCH"]
    assert got[(20260918, "evidence/main_checkpoint_0294.pt")][0].startswith("CHECKPOINT_SHA256_REUSED")
    assert got[(20260918, "final.pt")] == ["MISSING"]

    entries = _entries()
    entries[1]["_table"] = _with_model(table("POSITIVE"), "0" * 64, switch=False)
    prov = _with_model(table("POSITIVE"), _sha(9))
    prov["provenance"] = dict(prov["provenance"], metric_sha256_lf="0" * 64)
    entries[9]["_table"] = prov
    refused = copy.deepcopy(_with_model(table("POSITIVE"), _sha(10)))
    refused["foci"][toy.FOCI[0]]["graph"].pop()
    entries[10]["_table"] = refused
    r = _read(entries)
    got = {(e["model_seed"], e["checkpoint_relative_path"]): e["problems"] for e in r["entries"]}
    assert got[(20260917, "evidence/main_checkpoint_0294.pt")] == ["CHECKPOINT_SHA256_MISMATCH", "SWITCH_NOT_TRUE"]
    assert got[(20260918, "evidence/main_checkpoint_0882.pt")] == ["PROVENANCE_MISMATCH"]
    assert got[(20260918, "evidence/main_checkpoint_1176.pt")][0].startswith("TABLE_REFUSED:TABLE_GRAPH_RUNS")


def test_item2_needs_a_passing_validation_and_registered_entries():
    r = _read(_entries(), raw=_validation_raw(V3_ANTI_COMPARISON=table("POSITIVE")))
    assert r["outcome"] == "ITEM2_NOT_READ_PROBE_NOT_VALIDATED" and r["mechanism_gate"] == "MECHANISM_GATE_OPEN"
    assert _read(_entries(), source=("a", "b"))["outcome"] == "ITEM2_NOT_READ_PROBE_NOT_VALIDATED"
    extra = _entries() + [dict(_entries()[0], checkpoint_relative_path="initial.pt")]
    with pytest.raises(item2_reader.ToolStop):
        _read(extra)
    with pytest.raises(item2_reader.ToolStop):
        _read(_entries() + [_entries()[0]])


def test_item2_command_line_reads_files_and_never_replaces_its_output(tmp_path):
    frozen = metric.frozen_hashes()
    files = {}
    for case, kind in (("V1_CONTROL_UNWRAPPED", "HELM_LIKE"), ("V2_POSITIVE_COMPARISON", "POSITIVE"),
                       ("V3_ANTI_COMPARISON", "ANTI"), ("V4_NEGATIVE_UNIFORM", "UNIFORM"),
                       ("V5_NEGATIVE_COUPLED", "COUPLED")):
        p = tmp_path / (case + ".json")
        p.write_bytes(json.dumps(table(kind)).encode("utf-8"))
        files[case] = {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    summary = tmp_path / "validation_summary.json"
    summary.write_bytes(json.dumps({"tables": files, "pointer_learner_sha256_lf_before_after": ["s", "s"]}).encode())
    entries = []
    for i, e in enumerate(_entries()):
        p = tmp_path / ("entry_%02d.json" % i)
        p.write_bytes(json.dumps(_with_model(table("POSITIVE"), e["checkpoint_sha256"])).encode("utf-8"))
        entries.append({k: v for k, v in e.items() if not k.startswith("_")}
                       | {"score_table": p.name, "score_table_sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    entries[4]["score_table_sha256"] = "f" * 64
    (tmp_path / "accept.json").write_text(json.dumps(dict(frozen, schema=item2_reader.SCHEMA_ACCEPTANCE,
                                                          accepted_by="owner")))
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps({"schema": item2_reader.SCHEMA_INPUTS, "entries": entries,
                                  "validation_summary": summary.name,
                                  "validation_summary_sha256": hashlib.sha256(summary.read_bytes()).hexdigest(),
                                  "acceptance_record": "accept.json"}))
    out = tmp_path / "reading.json"
    assert item2_reader.main(["--inputs", str(inputs), "--out", str(out)]) == 0
    reading = json.loads(out.read_text())
    assert reading["outcome"] == "ITEM2_FAIL:20260917/evidence/main_checkpoint_1176.pt=SCORE_TABLE_SHA256_MISMATCH"
    assert reading["validation"]["validation"] == "VALIDATION_PASS"
    assert item2_reader.main(["--inputs", str(inputs), "--out", str(out)]) == 1     # create-only
    summary.write_bytes(summary.read_bytes() + b" ")
    assert item2_reader.main(["--inputs", str(inputs)]) == 1                       # summary hash bound
