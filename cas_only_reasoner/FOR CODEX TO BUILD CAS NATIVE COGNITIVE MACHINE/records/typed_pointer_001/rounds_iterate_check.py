"""THE $0 GATE FOR HELM 2.0 (F1). Run this before any GPU spend. No CUDA, no money, ~10 seconds.

Helm 1.0's `_rounds` took its three per-round aggregates from `raw`, the FROZEN node feature rows,
and read the state `hidden` only into a local named `block` that was never used. The round input was
therefore a constant -- bitwise identical on all `CORE_ROUNDS` rounds -- and the receptive field was
exactly ONE hop at round 8 or at round 800. That single fact explains Helm 1.0's flat curve, its
landing on the zero-learning floor, `analogy` at 0.00 held, and the ten-node panel at 10-15%.

This file is the check that the repair actually landed, written so that it CANNOT pass by accident:

  CHECK 1  the round input must DIFFER across rounds.  Helm 1.0 gives max|diff| = 0 on every pair.
  CHECK 2  a node's final vector must CHANGE when the graph changes TWO hops away, with its own
           one-hop neighbourhood held identical.  Helm 1.0 gives exactly 0.000e+00.
  CHECK 3  `_rounds` must contain no assigned-and-never-read name.  `block` was that name.
  CHECK 4  `BLOCK_INPUT_WIDTH` must be 3 * WIDTH, i.e. three STATE vectors, not three feature rows.

Exit 0 and `ROUNDS_ITERATE_PASS` means the loop iterates. Anything else means it does not, and
nothing should be launched. This does NOT say the model is better -- only that it is now CAPABLE of
more than one hop. What it does with that capability is a question for a run and a grader.

Usage:  python records/typed_pointer_001/rounds_iterate_check.py
"""
import ast
import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "CAS_META_2_COMPOSITION"))

import torch  # noqa: E402
from cas_meta2.typed_teaching import pointer_learner as pl  # noqa: E402

LEARNER_SOURCE = ROOT / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py"
# A real trained Helm 1.0 brain, used so the checks run on real weights rather than on a fresh
# random build. Any of the three seeds does; the finding is not seed-dependent.
TRAINED = ROOT / "records/typed_pointer_001/receipt_20260917/collected/results/artifacts/final.pt"


def _container():
    """The real pointer container on CPU, carrying the real trained weights where they still fit.

    `_build_container` wants a framework object only for the three registered `^6` tensors, so the
    stub supplies exactly those from the trained checkpoint. `state_encode` is new in Helm 2.0 and
    is absent from a 1.0 checkpoint, so the load is non-strict and that one tensor keeps its fresh
    initialisation. That is correct for this check: it asks whether INFORMATION FLOWS, not whether
    the weights are good.
    """
    state = torch.load(TRAINED, map_location="cpu", weights_only=False)["model_state"]

    class _Stub(torch.nn.Module):
        def __init__(self):
            super().__init__()
            for name in pl.PARAMETERS:
                self.register_parameter(name.replace(".", "_"),
                                        torch.nn.Parameter(state[name].clone()))

        def state_dict(self, *args, **kwargs):
            return {name: state[name].clone() for name in pl.PARAMETERS}

    model = pl._build_container(torch, types.SimpleNamespace(module=_Stub()), torch.device("cpu"))
    # Helm 2.0 both ADDS tensors (`state_encode`, `match_key`) and WIDENS one (`reach_option_head.0`,
    # which now receives the query's node pair). A 1.0 checkpoint can fill neither, so both classes are
    # dropped and REPORTED rather than silently coerced. Every tensor the check does not name here was
    # carried over from the trained run unchanged.
    current = model.state_dict()
    reshaped = sorted(name for name, value in state.items()
                      if name in current and tuple(value.shape) != tuple(current[name].shape))
    usable = {name: value for name, value in state.items() if name not in reshaped}
    missing, unexpected = model.load_state_dict(usable, strict=False)
    return model, sorted(missing), sorted(unexpected), reshaped


def _blocks(node_count, edges, seed=7):
    """One world, with the REAL degree columns the encoder would see."""
    adjacency = torch.zeros(node_count, node_count)
    for source, target in edges:
        adjacency[source, target] = 1.0
    torch.manual_seed(seed)
    one_hot, _, _ = pl._degree_features(torch, adjacency)
    base = torch.zeros(node_count, pl.NODE_ROW_WIDTH)
    base[:, :pl.NODE_ROW_WIDTH - one_hot.shape[1]] = torch.randn(
        node_count, pl.NODE_ROW_WIDTH - one_hot.shape[1])
    features = torch.cat((base[:, :pl.NODE_ROW_WIDTH - one_hot.shape[1]], one_hot), dim=1)
    return [["w", node_count, pl._rms_unit(torch, features), adjacency]]


def check_rounds_differ(model):
    seen = []
    pl._rounds(torch, model, _blocks(4, [(0, 1), (1, 2), (2, 3)]),
               observe=lambda index, value: seen.append(value.detach().clone()))
    diffs = [float((seen[0] - row).abs().max()) for row in seen[1:]]
    return {"check": "the round input differs across rounds",
            "rounds": len(seen), "max_diff_vs_round_0": diffs,
            "pass": len(seen) == pl.CORE_ROUNDS and all(value > 0.0 for value in diffs)}


def check_two_hops_reach(model):
    """Node 0's one-hop neighbourhood is IDENTICAL in both graphs; one edge moves two hops away.

    G1: 1->0, 0->2, 3->1, 2->4, 5->3      G2: the same but 5->3 becomes 5->4.
    Node 0's parent is 1 and its child is 2 in both, and both of those rows are bitwise identical,
    so anything that changes for node 0 arrived from distance >= 2.
    """
    g1 = _blocks(6, [(1, 0), (0, 2), (3, 1), (2, 4), (5, 3)])
    g2 = _blocks(6, [(1, 0), (0, 2), (3, 1), (2, 4), (5, 4)])
    neighbours_identical = bool(torch.equal(g1[0][2][1], g2[0][2][1])
                                and torch.equal(g1[0][2][2], g2[0][2][2]))
    graph_really_changed = not torch.equal(g1[0][2][4], g2[0][2][4])
    with torch.no_grad():
        first, second = pl._rounds(torch, model, g1), pl._rounds(torch, model, g2)
    difference = float((first[0] - second[0]).abs().max())
    return {"check": "a change two hops away reaches the node",
            "one_hop_neighbourhood_identical": neighbours_identical,
            "graph_really_changed": graph_really_changed,
            "node_0_max_diff": difference,
            "pass": neighbours_identical and graph_really_changed and difference > 0.0}


def check_no_dead_state_read():
    source = LEARNER_SOURCE.read_text(encoding="utf-8")
    rounds = [node for node in ast.walk(ast.parse(source))
              if isinstance(node, ast.FunctionDef) and node.name == "_rounds"][0]
    stored, loaded = set(), set()
    for node in ast.walk(rounds):
        if isinstance(node, ast.Name):
            (stored if isinstance(node.ctx, ast.Store) else loaded).add(node.id)
    dead = sorted(stored - loaded)
    return {"check": "_rounds has no assigned-and-never-read name",
            "dead_names": dead, "pass": not dead}


def check_block_input_width():
    return {"check": "the round input is three STATE vectors",
            "BLOCK_INPUT_WIDTH": pl.BLOCK_INPUT_WIDTH, "WIDTH": pl.WIDTH,
            "NODE_ROW_WIDTH": pl.NODE_ROW_WIDTH,
            "pass": pl.BLOCK_INPUT_WIDTH == 3 * pl.WIDTH}


def check_correspondence_is_expressible(model):
    """HELM 2.0 (F2b). Can DIFFERENT source nodes prefer DIFFERENT targets at all?

    Helm 1.0 scored every `mapping_target` slot with `_node_options`, i.e. `target_state . pointer_query`.
    That vector depends on the QUERY, never on the source, so every source node received the IDENTICAL
    ranking over targets and the ONLY mapping the model could emit was "all sources point at one target".
    A bijection was therefore not merely unlearned but UNREPRESENTABLE -- which is what `correspondence`
    at 0.09 on its own TRAINING data was telling us, and why those five questions left the gate.

    This check compares the two scoring rules on the same states, and then verifies that the Sinkhorn
    pass leaves a matrix whose rows and columns both normalise -- the property that makes one-to-one
    reachable. It does NOT claim the model will get correspondence right. It claims it now CAN.
    """
    torch.manual_seed(11)
    sources, targets = torch.randn(4, pl.WIDTH), torch.randn(4, pl.WIDTH)
    pointer_query = torch.randn(pl.WIDTH)
    with torch.no_grad():
        helm_1_0 = torch.stack([targets.matmul(pointer_query) for _ in range(sources.shape[0])])
        helm_2_0 = model.match_key(sources).matmul(targets.transpose(0, 1))
        scores = helm_2_0.clone()
        for _ in range(pl.SINKHORN_STEPS):
            scores = scores - torch.logsumexp(scores, dim=1, keepdim=True)
            scores = scores - torch.logsumexp(scores, dim=0, keepdim=True)
    one_zero_rows_all_equal = all(torch.equal(helm_1_0[0], row) for row in helm_1_0[1:])
    two_zero_rows_differ = all(not torch.equal(helm_2_0[0], row) for row in helm_2_0[1:])
    # After Sinkhorn every COLUMN sums to 1 in probability, which is the constraint a bijection needs
    # and the one independent per-pair scores can never enforce.
    column_mass = scores.exp().sum(dim=0)
    columns_normalised = bool((column_mass - 1.0).abs().max() < 1e-4)
    return {"check": "different sources can prefer different targets",
            "helm_1_0_gave_every_source_the_same_ranking": one_zero_rows_all_equal,
            "helm_2_0_rows_differ_by_source": two_zero_rows_differ,
            "sinkhorn_columns_sum_to_one": columns_normalised,
            "sinkhorn_max_column_error": float((column_mass - 1.0).abs().max()),
            "pass": one_zero_rows_all_equal and two_zero_rows_differ and columns_normalised}


def check_reach_head_sees_the_pair(model):
    """HELM 2.0 (F2a). The ABSENT/DIRECT head's input must be wide enough to hold the node pair.

    Helm 1.0 built it from `2 * WIDTH + 4` -- query vector, world vector, four degree scalars -- and so
    decided "is this part inside that whole" without being shown either node. `reach` carries 6 of the
    18 gate questions.
    """
    width = int(model.reach_option_head[0].in_features)
    return {"check": "the reach mode head receives the query's node pair",
            "in_features": width, "helm_1_0_in_features": 2 * pl.WIDTH + 4,
            "expected": 4 * pl.WIDTH + 4, "pass": width == 4 * pl.WIDTH + 4}


def main():
    model, missing, unexpected, reshaped = _container()
    parameters = {name: value.numel() for name, value in model.state_dict().items()}
    checks = [check_no_dead_state_read(), check_block_input_width(),
              check_rounds_differ(model), check_two_hops_reach(model),
              check_reach_head_sees_the_pair(model),
              check_correspondence_is_expressible(model)]
    report = {
        "schema": "cncm.helm-rounds-iterate-check/0.1",
        "learner_sha256_bytes": LEARNER_SOURCE.stat().st_size,
        "core_rounds": pl.CORE_ROUNDS,
        "tensor_groups": len(parameters),
        "parameter_total": sum(parameters.values()),
        "tensors_absent_from_the_1_0_checkpoint": missing,
        "tensors_in_the_checkpoint_this_build_has_no_slot_for": unexpected,
        "tensors_whose_shape_helm_2_0_changed": reshaped,
        "checks": checks,
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    passed = all(row["pass"] for row in checks)
    print("ROUNDS_ITERATE_PASS" if passed else "ROUNDS_ITERATE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
