"""Smoke test for FRW-1 world + exact solver: builds the dataset, plays the exact policy on every
training episode of a few worlds, reports the ceiling success rate and timing. $0, CPU, no model."""
import sys
import time
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from CJT_MECH_0.frw1.world import Env, build_dataset, instance_from, K, A_EXECUTE   # noqa: E402
from CJT_MECH_0.frw1.solver import ExactSolver, BeliefTracker                        # noqa: E402


def play_exact(inst, F):
    env = Env(inst)
    env.reset(F)
    solver = ExactSolver(inst)
    tracker = BeliefTracker(solver)
    S = tracker.reset(F)
    while not env.done:
        a = solver.best_action(S, env.b)
        _, _, done, info = env.step(a)
        S = tracker.update(a, info)
        if not S and not env.done:
            raise RuntimeError(f"belief emptied: world {inst.world_id} F={sorted(F)} action {a} info {info}")
    return env.outcome(), solver.value(solver.initial_belief(F_true=F), inst.budget)


def main():
    t0 = time.time()
    ds = build_dataset(20260903, 20, 2, 424242)
    print("dataset:", {k: len(v) for k, v in ds.items() if k.endswith("episodes")}, "worlds", len(ds["worlds"]))
    print("digests:", ds["digests"])
    n = succ = rec = zero = 0
    vals = []
    by_size = {1: [0, 0], 2: [0, 0], 3: [0, 0]}
    for wid, F in ds["train_episodes"] + ds["heldout_episodes"]:
        inst = instance_from(ds, wid)
        out, v = play_exact(inst, F)
        n += 1
        succ += out["success"]
        rec += out["next_tick_recovery"]
        vals.append(v)
        zero += (v == 0.0)
        by_size[len(F)][0] += out["success"]
        by_size[len(F)][1] += 1
    print(f"exact policy on {n} episodes: success {succ / n:.4f}  next-tick recovery {rec / n:.4f}  "
          f"mean initial value {sum(vals) / len(vals):.4f}  value-0 episodes {zero}  wall {time.time() - t0:.1f}s")
    print("  success by |F|:", {s: f"{a}/{b}" for s, (a, b) in by_size.items()})
    w0 = instance_from(ds, 0)
    s0 = ExactSolver(w0)
    print("world 0 budget", w0.budget, "costs c", w0.probe_cost, "d", w0.fix_cost, "parents", w0.parents, "policy", w0.policy_local)
    for size in (1, 2, 3):
        S = s0.initial_belief(size=size, policy_closed=False)
        print(f"  |F|={size} policy open: belief {len(S)} sets, value {s0.value(S, w0.budget):.4f}")


if __name__ == "__main__":
    main()
