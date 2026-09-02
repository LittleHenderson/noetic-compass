"""SHORTCUT GATE v0.1 -- the five-depth mechanism-free baseline.

Registered as the return condition for phase work (owner ruling 2026-09-02) and as the
construct-validity gate for CMB-R1 / RGM-0.2 item 4, "confirm results across new independent
memory worlds".

WHY THIS EXISTS. Three benches in the phase arc were each solvable WITHOUT the capability
under test, and each shortcut was created by the repair for the previous one:

    CMB-P0  the gold was the unique non-seed weight-1.0 neighbour of the cue   1152/1152
    CMB-P0  the content vector carried the chain's own flavour onto its gold   25/36, 25/42
    CMB-P2  two-hop mass from the cue identified the gold, BEATING THE ORACLE  0.826 vs 0.768

Every one of them survived reviewers who were reasoning about the code. None survived a
measurement. So this module measures, at every depth a mechanism can see, and it is meant to
be run BEFORE any mechanism arm is scored and RE-RUN after any change to the world builder.

THE TELL WORTH REMEMBERING: when the cheapest rule beats an ORACLE that is handed the true
labels, the task does not require the capability under test at all.

Device-agnostic: it runs wherever the tensors already are. This is graph algebra and construct
validation, not neural inference, so it does not fall under the GPU-only compute law -- but it
will happily run on CUDA if the caller's tensors are there.
"""
import math

import torch

VERSION = "shortcut_gate_v0.1"

# A depth FAILS if its top-1 exceeds chance by more than the threshold. The task is supposed
# to be unsolvable at every depth, so anything meaningfully above chance is a shortcut.
TOLERANCE_OVER_CHANCE = 0.05
# ...but "meaningfully" has to account for sampling noise, and the sample size is NOT the
# number of queries -- it is the number of DISTINCT (cue, gold) pairs. CMB-P0 shipped with 64
# queries per world that were only 2-4 distinct; a fixed tolerance on a handful of distinct
# pairs flags noise as a leak. Threshold = chance + max(TOLERANCE, SIGMA * standard error).
SIGMA = 3.0


def _top1(scores, gold, allowed):
    """Top-1 with ties counted PESSIMISTICALLY, over the allowed candidate set only."""
    s = scores.clone().double()
    s[~allowed] = -float("inf")
    g = s.gather(1, gold.view(-1, 1))
    better = (s > g).sum(dim=1)
    tied = (s == g).sum(dim=1) - 1
    return float(((better + tied) == 0).double().mean().item())


def _effective_n(cue, gold):
    """Distinct (cue, gold) pairs -- the real sample size, not the query count."""
    pairs = torch.stack([cue, gold], dim=1)
    return max(1, int(torch.unique(pairs, dim=0).shape[0]))


def _threshold(chance, n_eff, tolerance):
    se = math.sqrt(max(chance * (1.0 - chance), 1e-12) / n_eff)
    return chance + max(tolerance, SIGMA * se)


def _allowed_mask(n_nodes, n_q, candidates, exclude, device):
    if candidates is None:
        a = torch.ones((n_q, n_nodes), dtype=torch.bool, device=device)
    elif candidates.dim() == 1:
        a = candidates.view(1, -1).expand(n_q, -1).clone()
    else:
        a = candidates.clone()
    if exclude is not None:
        a = a & ~(exclude if exclude.dim() == 2 else exclude.view(1, -1).expand(n_q, -1))
    return a


def candidate_set_recoverable(A, gold, tol=1e-9):
    """DEPTH 5. Is the answer SET itself recoverable from the graph alone?

    In CMB-P2 a completion was exactly the node carrying `pool` edges of weight 1.0, so the
    candidate set fell out of the adjacency matrix with no seeds and no labels -- which is
    half of what let a two-hop rule beat the oracle.

    Tries every distinct edge weight in the graph as a fingerprint and reports the best
    overlap with the true answer set.
    """
    truth = torch.unique(gold)
    best = {"recovered_exactly": False, "best_jaccard": 0.0, "weight": None, "count": None}
    w = torch.unique(A[A > 0])
    if w.numel() > 64:                       # keep it cheap on dense-valued graphs
        w = torch.quantile(w.double(), torch.linspace(0, 1, 64, device=A.device).double())
    for wv in w:
        deg = ((A - wv).abs() < tol).sum(dim=0)
        for c in torch.unique(deg[truth]):
            pred = (deg == c).nonzero(as_tuple=True)[0]
            if pred.numel() == 0:
                continue
            inter = len(set(pred.tolist()) & set(truth.tolist()))
            union = len(set(pred.tolist()) | set(truth.tolist()))
            j = inter / union if union else 0.0
            if j > best["best_jaccard"]:
                best = {"recovered_exactly": bool(j == 1.0), "best_jaccard": j,
                        "weight": float(wv.item()), "count": int(c.item())}
    return best


def run_gate(A, cue, gold, content=None, candidates=None, exclude=None,
             amplitude=None, oracle_top1=None, tolerance=TOLERANCE_OVER_CHANCE):
    """Measure the cheapest rule at every depth a mechanism can see.

    A          (N, N)  adjacency / link weights
    cue        (Q,)    the node each query is cued from
    gold       (Q,)    the correct answer per query
    content    (N, D)  semantic vectors, or None
    candidates (N,) or (Q, N) bool -- the admissible answer set, or None for "anything"
    exclude    (Q, N) bool -- nodes that cannot be answers (e.g. seeds), or None
    amplitude  (Q, N)  an optional per-query score (e.g. the scalar engine's output). Each
                       depth is ALSO measured multiplied by this, because in CMB-P2 it was
                       `two-hop x amplitude` that reached 0.966 -- the product beat both parts.
    oracle_top1        the label-using ceiling, if known. If any depth beats it, the task
                       does not require the capability under test AT ALL.
    """
    dev = A.device
    n, q = A.shape[0], cue.shape[0]
    allowed = _allowed_mask(n, q, candidates, exclude, dev)
    chance = float((1.0 / allowed.sum(dim=1).clamp_min(1).double()).mean().item())
    n_eff = _effective_n(cue, gold)
    thresh = _threshold(chance, n_eff, tolerance)

    depths = {}
    A2 = A @ A
    depths["2_one_hop"] = A[cue]
    depths["3_two_hop"] = A2[cue]
    if content is not None:
        c = content / content.norm(dim=1, keepdim=True).clamp_min(1e-12)
        depths["1_content"] = (c[cue] @ c.T)
    # DEPTH 4 -- topology: can the answer be picked by a structural fingerprint that does not
    # look at the cue at all? Best over several cue-independent statistics.
    deg_w = A.sum(dim=0)
    deg_b = (A > 0).sum(dim=0).double()
    tri = ((A > 0).double() @ (A > 0).double() * (A > 0).double()).sum(dim=0)
    topo = {"weighted_degree": deg_w, "binary_degree": deg_b, "triangles": tri}

    results = {}
    for name, sc in depths.items():
        base = _top1(sc.double(), gold, allowed)
        row = {"top1": base, "top1_times_amplitude": None}
        if amplitude is not None:
            row["top1_times_amplitude"] = _top1((sc.double() * amplitude.double()), gold, allowed)
        results[name] = row
    best_topo, best_topo_name = 0.0, None
    for name, v in topo.items():
        t = _top1(v.view(1, -1).expand(q, -1).double(), gold, allowed)
        if t > best_topo:
            best_topo, best_topo_name = t, name
    results["4_topology"] = {"top1": best_topo, "statistic": best_topo_name,
                             "top1_times_amplitude": None}
    cand = candidate_set_recoverable(A, gold)
    results["5_candidate_identity"] = {"recovered_exactly": cand["recovered_exactly"],
                                       "best_jaccard": cand["best_jaccard"],
                                       "fingerprint_weight": cand["weight"],
                                       "fingerprint_count": cand["count"]}

    verdicts, worst, worst_name = {}, 0.0, None
    for name, row in results.items():
        if name == "5_candidate_identity":
            verdicts[name] = "FAIL" if row["recovered_exactly"] else "PASS"
            continue
        top = max(row["top1"], row["top1_times_amplitude"] or 0.0)
        verdicts[name] = "FAIL" if top > thresh else "PASS"
        if top > worst:
            worst, worst_name = top, name
    beats_oracle = bool(oracle_top1 is not None and worst > oracle_top1)

    return {
        "version": VERSION,
        "chance": chance,
        "tolerance_over_chance": tolerance,
        "effective_n_distinct_cue_gold_pairs": n_eff,
        "fail_threshold": thresh,
        "depths": results,
        "verdicts": verdicts,
        "gate": "PASS" if all(v == "PASS" for v in verdicts.values()) else "FAIL",
        "strongest_shortcut": worst_name,
        "strongest_shortcut_top1": worst,
        "oracle_top1": oracle_top1,
        "shortcut_beats_oracle": beats_oracle,
        "note": ("A mechanism-free rule beating the ORACLE means the task does not require the "
                 "capability under test at all." if beats_oracle else
                 "Re-run this after ANY change to the world builder: in the phase arc, the "
                 "repair for one shortcut manufactured the next one, twice."),
    }


def format_report(r):
    out = [f"SHORTCUT GATE {r['version']}   chance={r['chance']:.4f}   "
           f"n_eff={r['effective_n_distinct_cue_gold_pairs']}   "
           f"fail above {r['fail_threshold']:.4f}",
           f"{'depth':>22}{'top1':>9}{'x amplitude':>13}  verdict"]
    for name in sorted(r["depths"]):
        d, v = r["depths"][name], r["verdicts"][name]
        if name == "5_candidate_identity":
            out.append(f"{name:>22}{'':>9}{'':>13}  {v}   "
                       f"jaccard={d['best_jaccard']:.3f} exact={d['recovered_exactly']}")
        else:
            amp = "" if d["top1_times_amplitude"] is None else f"{d['top1_times_amplitude']:>13.4f}"
            out.append(f"{name:>22}{d['top1']:>9.4f}{amp:>13}  {v}")
    out.append(f"GATE: {r['gate']}   strongest={r['strongest_shortcut']} "
               f"({r['strongest_shortcut_top1']:.4f})")
    if r["oracle_top1"] is not None:
        out.append(f"oracle={r['oracle_top1']:.4f}   shortcut_beats_oracle="
                   f"{r['shortcut_beats_oracle']}")
    return "\n".join(out)
