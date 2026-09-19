"""Independent verification of the built pointer_contract.py, before it is trusted.

Checks the contract against the sources it must agree with, rather than against the builder's own test:
 - the 18 checkpoint MATERIAL rows equal contract_pins/checkpoint_pins.json exactly, and total 15259777 bytes
 - the job pattern accepts the pointer token and rejects the practice one, and the bucket fits 63 characters
 - MIN_PASSING_B is 7 with 2**-7 <= 0.01
 - the hold-out digests equal the practice study's own, i.e. nothing was re-derived in a way that drifted
 - relational_population refuses to report a finished population while REMOVALS is empty

Read-only, $0, no torch. Run from a short working directory.
"""
import json
import re
import sys
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD "
            r"CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX "
            r"TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research" / "CAS_META_2_COMPOSITION")]

from cas_meta2.typed_teaching import pointer_contract as pc   # noqa: E402
from cas_meta2.typed_teaching import practice_contract as prac  # noqa: E402

PINS = json.loads((CNCM / "records" / "typed_pointer_001" / "pre_design" / "contract_pins"
                   / "checkpoint_pins.json").read_text(encoding="utf-8"))["material"]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-58s %s  %s" % (name, "PASS" if ok else "**FAIL**", detail))


# --- MATERIAL pins -------------------------------------------------------------------------------
extra = {k: v for k, v in pc.MATERIAL.items() if k.startswith("records/typed_practice_001/")}
check("18 checkpoint rows in MATERIAL", len(extra) == 18, "got %d" % len(extra))
mismatch = [k for k in PINS if k not in pc.MATERIAL or pc.MATERIAL[k] != PINS[k]]
check("every pin row equals checkpoint_pins.json", not mismatch, str(mismatch[:3]))
check("total checkpoint bytes 15259777",
      sum(v["bytes"] for v in extra.values()) == 15259777,
      "got %d" % sum(v["bytes"] for v in extra.values()))
bad_keys = [k for k, v in extra.items() if set(v) != {"bytes", "sha256"}]
check("pin rows carry exactly bytes+sha256", not bad_keys, str(bad_keys[:3]))

# --- job pattern and bucket ----------------------------------------------------------------------
JOB = "cas-meta2-tpntr-20260919000000-857af081-m-20260917"
PRAC = "cas-meta2-tprac-20260919000000-857af081-m-20260917"
check("pattern accepts the pointer job", re.fullmatch(pc.JOB_PATTERN, JOB) is not None)
check("pattern rejects the practice job", re.fullmatch(pc.JOB_PATTERN, PRAC) is None)
bucket = JOB + "-807562639912"
check("bucket <= 63 chars and valid",
      len(bucket) <= 63 and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket) is not None,
      "len=%d" % len(bucket))

# --- gate constants ------------------------------------------------------------------------------
check("MIN_PASSING_B == 7", pc.MIN_PASSING_B == 7, str(pc.MIN_PASSING_B))
check("2**-7 <= 0.01", 2 ** -pc.MIN_PASSING_B <= 0.01, "%.10f" % (2 ** -pc.MIN_PASSING_B))
check("tiers unchanged", tuple(pc.RELATIONAL) == ("parts", "edge_account", "reach", "correspondence", "analogy")
      and tuple(pc.DIRECT_READ) == ("definition", "context") and tuple(pc.TEXT) == ("role_set",))

# --- hold-out identity, against the practice study's own values -----------------------------------
frozen, tokenizer, development = prac.load_material(CNCM)
held, trained, excluded = prac.split(frozen)
batches, stats = prac.practice_schedule(frozen)
check("held digest matches practice", stats["held_back_record_ids_digest"] ==
      "668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d")
check("excluded digest matches practice", stats["excluded_record_ids_digest"] ==
      "b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621")
check("batches digest matches practice", stats["batches_digest"] ==
      "daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857")
check("split counts 127/358/79", (len(held), len(trained), len(excluded)) == (127, 358, 79),
      "%d/%d/%d" % (len(held), len(trained), len(excluded)))

# --- the population guard -------------------------------------------------------------------------
empty_removals = all(not v for v in getattr(pc, "REMOVALS", {}).values()) if isinstance(
    getattr(pc, "REMOVALS", {}), dict) else True
try:
    pop = pc.relational_population(frozen)
    raised = False
    detail = json.dumps({k: pop[k] for k in ("total", "by_kind", "removals_measured", "population_complete")})[:200] if isinstance(pop, dict) else str(pop)[:200]
except Exception as exc:                                     # noqa: BLE001
    raised = True
    detail = "%s: %s" % (type(exc).__name__, str(exc)[:120])

# The contract's guard raises only when the eligible composition DRIFTS from the verified values while the
# removals placeholder is empty. Returning an unreconciled-but-verified population is correct; what must never
# happen is that such a population looks finished. So assert the markers, not a refusal.
if isinstance(pop, dict) and not raised:
    check("empty REMOVALS -> composition equals verified values",
          pop["eligible_total"] == 29 and pop["eligible_by_kind"] == pc.VERIFIED_RELATIONAL_BY_KIND
          and pop["eligible_by_world"] == pc.VERIFIED_RELATIONAL_BY_WORLD,
          json.dumps(pop["by_kind"]))
    check("empty REMOVALS -> removals_measured is False", pop.get("removals_measured") is False)
    check("empty REMOVALS -> population_complete is False", pop.get("population_complete") is False)
    check("empty REMOVALS -> known removals recorded but not applied",
          pop.get("verified_inputs", {}).get("known_removals") == {"flag_rule": {"parts": 3},
                                                                  "rank_rule": {"reach": 2}}
          and pop["total"] == 29,
          "total=%s" % pop.get("total"))
else:
    check("population returns while REMOVALS is empty", not raised, detail)

print()
failed = [n for n, ok, _ in results if not ok]
print("VERDICT: %s  (%d checks, %d failed)" % ("ALL PASS" if not failed else "FAILURES", len(results), len(failed)))
for n in failed:
    print("   FAILED:", n)
