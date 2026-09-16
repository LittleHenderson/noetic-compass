"""Read the RDCJT launcher's own view of seed state and cost. No neural work."""

import json
import sys
from pathlib import Path

COMPOSITION = Path(__file__).resolve().parents[2] / "_worktrees" / "meta1" / (
    "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
    "research/CAS_META_2_COMPOSITION")
sys.path.insert(0, str(COMPOSITION))

from aws import recurrent_cjt_launch as L  # noqa: E402

RECORD_DIR = COMPOSITION / "records" / "recurrent_cjt_001"

out = {}
out["frozen_seeds"] = list(L.FROZEN_SEEDS)
out["frozen_arms"] = list(L.FROZEN_ARMS)
out["frozen_updates_per_arm"] = L.FROZEN_UPDATES_PER_ARM
out["frozen_decisions_per_arm"] = L.FROZEN_DECISIONS_PER_ARM
out["reservation_usd"] = str(L.RESERVATION_USD)
out["max_wall_seconds"] = L.FROZEN_MAX_WALL_SECONDS
out["declared_cost"] = L.frozen_cost()
out["record_dir"] = str(RECORD_DIR)
out["record_dir_exists"] = RECORD_DIR.is_dir()

used = L.seeds_already_used(RECORD_DIR)
out["seeds_consumed_by_a_delivered_run"] = sorted(used)

remaining = []
for seed in L.FROZEN_SEEDS:
    try:
        out.setdefault("require_unused_seed", {})[str(seed)] = L.require_unused_seed(
            seed, RECORD_DIR)
        remaining.append(seed)
    except Exception as exc:
        out.setdefault("require_unused_seed", {})[str(seed)] = {"refused": repr(exc)}

out["seeds_that_may_be_run_now"] = remaining
out["replication_status_if_all_three_deliver"] = L.replication_status(3)
out["replication_status_today"] = L.replication_status(len(used))

print(json.dumps(out, indent=2, sort_keys=True, default=str))
