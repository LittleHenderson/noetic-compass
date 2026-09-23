"""Probe v0.2 SELF-TEST (Claude). Rules and expected outcomes: PREREG_PROBE_SELF_TEST.md, written before any run.

A probe that reads zero on a model with no focus-to-candidate path is only informative if it would read NON-zero
on a model that has one, and would REFUSE the known fakes. This runs `analogy_wiring_probe_v0_2.probe_one`
UNCHANGED on a fresh Helm 2.0 container whose `GraphForward._world_scores` is wrapped IN MEMORY (the source file on
disk is never modified) by three hand-built variants:

  POSITIVE_COMPARISON   extra_c = -2 * L1(degree histogram of focus, of c) - 2 * [domain tokens of c == of focus]
                        a genuine focus-to-candidate comparison of graph AND domain
  NEGATIVE_UNIFORM      extra_c = 3 * (focus edge count + focus node count)      -- the same for every candidate
  NEGATIVE_COUPLED      extra_c = 0.5 * <mean over ALL worlds of degree histograms, histogram of c>
                        depends on the focus only through a pool over every world

These are probe calibration controls, not repairs. Nothing here is a Helm result.
"""
import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analogy_wiring_probe_v0_2 as probe  # noqa: E402


def degree_hist(torch, adjacency, steps=5):
    ind = torch.clamp(adjacency.sum(dim=0).to(torch.int64), max=steps - 1)
    outd = torch.clamp(adjacency.sum(dim=1).to(torch.int64), max=steps - 1)
    hist = torch.zeros(steps * steps, dtype=torch.float32, device=adjacency.device)
    for a, b in zip(ind.tolist(), outd.tolist()):
        hist[a * steps + b] += 1.0
    return hist


def make_variant(torch, PL, original, kind):
    def wrapped(self, field, symbols):
        rows = original(self, field, symbols)
        hists = {row[0]: degree_hist(torch, row[3]) for row in self.blocks}
        focus = self.focus_world_id
        dom = {w: tuple(self.reading["worlds"][w]["declaration_ids"]["domain"]) for w in self.world_ids}
        extras = []
        for symbol in symbols:
            if symbol == "NO_MATCH":
                extras.append(0.0)
                continue
            c = PL._world_alias_table_for(self.reading, symbol)
            if kind == "POSITIVE_COMPARISON":
                extras.append(float(-2.0 * (hists[focus] - hists[c]).abs().sum() - 2.0 * (dom[c] == dom[focus])))
            elif kind == "NEGATIVE_UNIFORM":
                block = [row for row in self.blocks if row[0] == focus][0]
                extras.append(float(3.0 * (block[3].sum() + block[1])))
            elif kind == "NEGATIVE_COUPLED":
                pool = torch.stack(list(hists.values())).mean(dim=0)
                extras.append(float(0.5 * torch.dot(pool, hists[c])))
            else:
                raise ValueError(kind)
        # float64 on purpose: adding a constant in float32 perturbs every logit by rounding (~1e-6 at |s| ~ 20),
        # which would test float32 arithmetic rather than the probe's shift-invariance.
        return rows.double() + torch.tensor(extras, dtype=torch.float64, device=rows.device)
    return wrapped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260917)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    started = time.monotonic()
    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED"); sys.exit(2)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
    admission = probe.gpu_telemetry()
    if admission["temperature_c"] > probe.MAX_START_C or admission["memory_free_mib"] < probe.MIN_FREE_MIB:
        print("GPU_UNAVAILABLE", admission); sys.exit(3)
    device = torch.device("cuda", 0)
    package = probe.DEFAULT_PACKAGE
    sys.dont_write_bytecode = True
    for p in (package, package / "research" / "CAS_META_2_COMPOSITION"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from cas_meta2.typed_teaching import pointer_contract as contract, pointer_inputs, pointer_learner as PL, slots
    from cncm.typed_matched_worker import _framework
    frozen = contract.load_material(package)[0]
    packets = dict(contract.public_packets(frozen))
    analogy_ids = sorted(rid for rid, pk in packets.items() if pk["record"]["query"]["kind"] == "analogy")
    focus_of = {rid: packets[rid]["source"]["focus_world_id"] for rid in analogy_ids}
    rep = {}
    for rid in analogy_ids:
        rep.setdefault(focus_of[rid], rid)
    original = PL.GraphForward._world_scores
    source_before = probe.lf_sha(package / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py")

    class _Args:
        switch_attr, switch_expect = None, None
    results = {}
    for kind in ("POSITIVE_COMPARISON", "NEGATIVE_UNIFORM", "NEGATIVE_COUPLED"):
        PL.GraphForward._world_scores = make_variant(torch, PL, original, kind)
        try:
            r = probe.probe_one(torch, device, PL, slots, pointer_inputs, _framework, pointer_inputs._node_index, packets,
                                analogy_ids, focus_of, rep, {}, _Args, label="selftest_" + kind, init_seed=args.seed,
                                checkpoint=None, started=started)
        finally:
            PL.GraphForward._world_scores = original
        results[kind] = r
        print(json.dumps({"variant": kind, "verdict": r["verdict"], "M0": r["M0_delta0"], "summary": r["summary"]}))
    source_after = probe.lf_sha(package / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py")
    out = {"schema": "claude.analogy-wiring-probe-selftest/0.1", "results": results,
           "probe_sha256_lf": probe.lf_sha(HERE / "analogy_wiring_probe_v0_2.py"),
           "selftest_sha256_lf": probe.lf_sha(__file__),
           "prereg_sha256_lf": probe.lf_sha(HERE / "PREREG_PROBE_SELF_TEST.md"),
           "pointer_learner_sha256_lf_before_after": [source_before, source_after],
           "wall_seconds": time.monotonic() - started, "gpu_admission": admission,
           "work": "forward passes only; _world_scores wrapped in memory; no source file modified"}
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
