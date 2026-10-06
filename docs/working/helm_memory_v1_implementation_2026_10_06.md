# Lasting memory v1 — implementation note (survival level (a), development data)

**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` ability 3, roadmap step 3; directive `docs/directives/2026_10_06_helm_lasting_memory_and_restart_recovery.md`; contract `docs/working/helm_memory_contract_v1_draft_2026_10_06.md`; audit `docs/working/helm_reuse_audit_2026_10_06.md` §7.
**Code:** `scripts/cas_rpu/history.py`, `scripts/tests/test_cas_rpu_memory.py`.
**Label:** preparation and a development demonstration. Not the frozen result.

## Gate answer

Ability 3. Behavior: on a development stream, a fact taught in process 1 makes `ask(A, D)` answer YES; the state is saved; process 2 restores it and answers YES from the held record without being retaught; a retraction in process 2 withdraws every dependent and the asks answer UNKNOWN; process 3 restores that and agrees. Control: the recompute oracle over the same rows (`ctl_recompute`), with no held state. Criterion: exact agreement on every recorded ask; zero stale answers after any restart; every refusal and outcome replays identically. Does not show: survival of machine replacement (level b), retention on a frozen held-out set, or any speed claim.

## What survives, and how

Everything the organism holds is a deterministic function of the identity record and the ordered events, beat count included (audit §3). The document therefore stores the identity header, the rows, and a reference digest of the rebuilt state; the memory board's charge and the motivation levels are excluded from that digest as path-dependent diagnostics (contract M12a item 5). Restore is replay plus verification, and nothing is served before the verification passes.

## Measured (this container, 104 rows)

| commit median | commit p95 | commit max | document | restore | bytes written |
|---|---|---|---|---|---|
| 3.6 ms | 5.9 ms | 9.0 ms | 45 KB | 16 ms | 2.4 MB |

Whole-document rewrite per commit, retained copies included. Reported, not optimized; the evaluation plan's dry run on the target instance replaces these numbers.

## Which survival was demonstrated

**(a)** a clean process exit and a restart on the same machine, in fresh operating-system processes under test. **(b)** machine termination and replacement: **not demonstrated**; it needs the authorized storage arrangement identified (directive amendment item 1).

## Record-first (contract M8), landed the same day

`Organism(record_first=True, record_invalidation="context" | "dependency")`. Off by default; the organism is then unchanged. On, `_ask` first checks the held record for the exact query key: the pid must be in `standing` and ASSERTIVE, its denial neither asserted nor disputed, the organism unfaulted, and — in dependency mode — every root ASSERTIVE; in context mode, additionally no accepted mutation since the record was last validated. A validated hit is served with no walk and no `Workspace.ask` call, and the response carries `route = "hit"` with the number of dependency edges checked as its work. Everything else routes to the walk and names why (`miss`, `rejected:<check>`).

Hard law: on generated streams in both worlds, both modes agree with walk-first and with the oracle on every probe. Zero faults. Routes at n=80 per world: dependency 11 hits / 170 misses; context 1 hit / 10 rejected / 170 misses — the generator's interleaved facts invalidate almost every record under whole-context invalidation, as the directive's order of work anticipated. Cost, within the organism's own counters: repeat asks 10.9 (dependency) vs 13.7 (walk-first) at n=40; a hit costs the size of its support set. Under the no-cascade ablation the record check refuses the dead-rooted record and the walk reproduces that ablation's own known defect, so the fast path adds no stale answer beyond walk-first. Through `Stream`, the flag is identity and a restored stream hits from the replayed record.

Not implemented: `rpa_routing` and the external index/atlas lookup (M8.6). The comparison "record-first without RPA versus with RPA" therefore cannot run yet.

## Next

The RPA-assisted lookup as a narrowing step over the same records (M8.6), the generator classes the evaluation plan needs (§4), then the development-seed dry run on the target instance before anything is frozen.
