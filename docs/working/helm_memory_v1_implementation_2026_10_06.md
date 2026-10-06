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

## Next

Guarded record-first answering behind a feature flag (contract M8; roadmap step 4), the generator classes the evaluation plan needs (§4), the work meter that counts actual work rather than `len(ws.props)`, then the development-seed dry run on the target instance before anything is frozen.
