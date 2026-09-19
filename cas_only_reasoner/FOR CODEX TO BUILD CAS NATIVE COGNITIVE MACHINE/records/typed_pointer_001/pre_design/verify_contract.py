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

# --- the FROZEN population -------------------------------------------------------------------------
try:
    pop = pc.relational_population(frozen)
    raised = False
except Exception as exc:                                     # noqa: BLE001
    pop, raised = None, True
    detail = "%s: %s" % (type(exc).__name__, str(exc)[:140])

check("relational_population computes against the frozen removals", not raised,
      "" if not raised else detail)
if pop is not None:
    check("eligible RELATIONAL is still the verified 29",
          pop["eligible_total"] == pc.VERIFIED_ELIGIBLE_RELATIONAL == 29
          and pop["eligible_by_kind"] == pc.VERIFIED_RELATIONAL_BY_KIND, json.dumps(pop["by_kind"]))
    check("FROZEN population is 18, as analogy 5 / edge_account 5 / parts 2 / reach 6",
          pop["total"] == pc.VERIFIED_POPULATION == 18
          and pop["by_kind"] == pc.VERIFIED_POPULATION_BY_KIND,
          json.dumps(pop["by_kind"]))
    check("population digest equals the pinned constant",
          pop["digest"] == pc.VERIFIED_POPULATION_DIGEST, pop["digest"][:16])
    check("eleven removals across four classes, none duplicated",
          len(pop["removed_questions"]) == 11 and len(set(pop["removed_questions"])) == 11
          and len(pc.REMOVAL_RULES) == 4,
          "classes=%s" % (pc.REMOVAL_RULES,))
    check("the population reports itself COMPLETE once removals are filled",
          pop["removals_measured"] is True and pop["population_complete"] is True)
    check("the rank-last questions are NOT removed (rank is excluded)",
          "rank_rule" not in pc.REMOVAL_RULES and pc.DESIGN["node_rank_feature"] is False
          and pop["verified_inputs"]["unreconciled_removal_readings"][
              "rank_last_pointing_not_removed"] == 5)

# --- the schedule: the AS-IS branch must stay faithful; the STRATIFIED branch is the owner's decision ---------
pb, pstats = pc.pointer_schedule(frozen, pc.practice.PASSES, stratified=False)
check("AS-IS pointer_schedule(10) reproduces the practice batches digest",
      pstats["batches_digest"] == "daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857",
      pstats["batches_digest"][:16])
check("AS-IS pointer_schedule(10) has 147 updates/pass and 818 presentations/pass",
      (pstats["updates_per_pass"], pstats["presentations_per_pass"]) == (147, 818),
      "%d / %d" % (pstats["updates_per_pass"], pstats["presentations_per_pass"]))
check("AS-IS pointer_schedule(10) matches the practice schedule line for line",
      pstats == stats, "" if pstats == stats else "differs from practice stats")

sb, sstats = pc.pointer_schedule(frozen, pc.practice.PASSES)
check("STRATIFIED is the default (owner decision)",
      pc.STRATIFIED is True and sstats["batches_digest"] != pstats["batches_digest"],
      "digest=%s" % sstats["batches_digest"][:16])
check("STRATIFIED keeps 147 updates per pass and reaches 1176 presentations",
      (sstats["updates_per_pass"], sstats["presentations_per_pass"]) == (147, 1176),
      "%d / %d" % (sstats["updates_per_pass"], sstats["presentations_per_pass"]))
kind_of = {row["record_id"]: row["query"]["kind"] for row in frozen["registry"]}
p1 = [b for b in sb if b["pass"] == 1]
absent = {k: sum(1 for b in p1 if k not in {kind_of[r] for r in b["record_ids"]})
          for k in sorted(set(kind_of.values()))}
check("STRATIFIED: every kind appears in every update of pass 1",
      all(v == 0 for v in absent.values()), str({k: v for k, v in absent.items() if v}))
check("STRATIFIED: every batch carries all 8 kinds",
      all(len(b["record_ids"]) == 8 for b in p1), "batch sizes %s" % sorted({len(b["record_ids"]) for b in p1}))

try:
    lb, lstats = pc.pointer_schedule(frozen, 20)
    ok20 = (lstats["main_updates"] == 2940 and lstats["passes"] == 20
            and lstats["batches_digest"] != sstats["batches_digest"])
    detail20 = "main=%d digest=%s" % (lstats["main_updates"], lstats["batches_digest"][:12])
except Exception as exc:                                     # noqa: BLE001
    ok20, detail20 = False, "%s: %s" % (type(exc).__name__, str(exc)[:100])
check("pointer_schedule(20) runs and differs from the 10-pass digest", ok20, detail20)

check("ceiling permits 24 passes and refuses 25",
      pc.LEARNER_MAX_UPDATES_CEILING == 24 * 147 + 16
      and 24 * 147 + 16 <= pc.LEARNER_MAX_UPDATES_CEILING,
      "ceiling=%d, 24 passes=%d" % (pc.LEARNER_MAX_UPDATES_CEILING, 24 * 147 + 16))

try:
    pc.pointer_schedule(frozen, 25)
    refused = False
except Exception:                                            # noqa: BLE001
    refused = True
check("pointer_schedule refuses more than MAX_PASSES_PERMITTED", refused)

check("the practice ceiling would have capped this study at 13 passes",
      pc.practice.LEARNER_MAX_UPDATES_CEILING == 2048 and 13 * 147 + 16 <= 2048 < 14 * 147 + 16,
      "practice ceiling=%d" % pc.practice.LEARNER_MAX_UPDATES_CEILING)

print()
failed = [n for n, ok, _ in results if not ok]
print("VERDICT: %s  (%d checks, %d failed)" % ("ALL PASS" if not failed else "FAILURES", len(results), len(failed)))
for n in failed:
    print("   FAILED:", n)
