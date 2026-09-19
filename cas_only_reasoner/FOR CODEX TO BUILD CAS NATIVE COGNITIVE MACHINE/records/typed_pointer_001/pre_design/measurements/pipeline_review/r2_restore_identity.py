"""Can PracticeCourseLearner.restore_checkpoint's pure identity checks pass on today's source? (no torch)"""
import json, sys, hashlib
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
for p in (CNCM, CNCM / "research/CAS_META_2_COMPOSITION"):
    sys.path.insert(0, str(p))
from cas_meta2.typed_teaching import practice_contract as c, learner, practice_learner, encoder, source
assert "torch" not in sys.modules
frozen, tok, dev = c.load_material(CNCM)
prof = learner.profile()
pprof = practice_learner.practice_profile()
ident = encoder.expected_identity(tok, seed=c.ENCODER_SEED)
for seed in (20260917, 20260918, 20260919):
    d = CNCM / ("records/typed_practice_001/receipt_%d/checkpoints" % seed)
    for name in ("initial", "pass_01", "final"):
        meta = json.loads((d / (name + "_checkpoint.json")).read_bytes())
        m = meta["metadata"]
        rid = m["run_identity"]
        raw = (d / (name + ".pt")).read_bytes()
        row = {
            "seed": seed, "ckpt": name,
            "pt_sha_matches_json": hashlib.sha256(raw).hexdigest() == meta["sha256"] and len(raw) == meta["bytes"],
            "run_identity_digest_ok": source.digest(rid) == m["run_identity_digest"] == meta["run_identity_digest"],
            "learner_profile_equal_today": source.canonical(rid["learner_profile"]) == source.canonical(prof),
            "practice_profile_equal_today": source.canonical(rid["practice_learner_profile"]) == source.canonical(pprof),
            "encoder_identity_equal_today": source.canonical(rid["encoder_identity"]) == source.canonical(ident),
            "elapsed_s": round(m["elapsed_seconds"], 1), "cursor": m["cursor"],
            "core_attempts": m["counters"]["core_forward_attempts"],
            "limits": rid["limits"], "context": rid["context"],
        }
        print(json.dumps(row))
# identical across the three seeds' collected copies?
for seed in (20260917, 20260918, 20260919):
    a = CNCM / ("records/typed_practice_001/receipt_%d/checkpoints/final.pt" % seed)
    b = CNCM / ("records/typed_practice_001/receipt_%d/collected/results/artifacts/final.pt" % seed)
    print(seed, "checkpoints/ == collected/", a.read_bytes() == b.read_bytes())
# input inventory size today and with checkpoint rows added
rows = c.input_inventory(CNCM)
extra = []
for seed in (20260917, 20260918, 20260919):
    for name in ("initial", "pass_01", "final"):
        for suf in (".pt", "_checkpoint.json"):
            p = CNCM / ("records/typed_practice_001/receipt_%d/checkpoints/%s%s" % (seed, name, suf))
            extra.append(p.stat().st_size)
print("inventory rows", len(rows), "bytes", sum(r["bytes"] for r in rows), "extra rows", len(extra), "extra bytes", sum(extra),
      "max extra", max(extra), "bound rows<=2000 bytes<=", 96 * 1024 ** 2)
