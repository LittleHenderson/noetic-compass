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

**(a)** a clean process exit and a restart on the same machine, in fresh operating-system processes under test: demonstrated.

**(b)** machine termination and replacement. The owner's instruction (2026-10-06): use a dedicated persistent location in the existing AWS setup, save there, prove a replacement machine can restore. Status:

- *Mechanism proven offline.* `Stream(mirror=...)` mirrors every sealed document to a second location; `Stream.restore_from` rebuilds on a machine with none of the local state. Test: three fresh processes, each machine's directory destroyed before the next restores from the remote alone; the taught fact is answered, a retraction withdraws its dependents, and the retraction survives the third restart. The second location in that test is a directory, so this proves that nothing is read from the destroyed machine; it does not prove AWS durability.
- *Live location not yet reached.* The S3 client is written (`scripts/cas_memory/s3store.py`, Signature V4 over the standard library, signer verified against AWS's published example, never deletes, never leaves its prefix) and the live test exists, gated on `HELM_S3_BUCKET` and a valid key. The sandbox's AWS key was rejected by the service on 2026-10-06 (`InvalidAccessKeyId`, against both buckets the repository names, `nc-api-build-807562639912-usw2` and `cas-harness-runpod-92754088`). **What is needed:** a key with `s3:PutObject`, `s3:GetObject` and `s3:ListBucket` on one dedicated prefix of an existing bucket (proposed `s3://nc-api-build-807562639912-usw2/helm-memory/`), set as `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` with `HELM_S3_BUCKET` in the environment; the test then runs unchanged. A genuine second EC2 host is the final step and needs the AWS execution route.

## Record-first (contract M8), landed the same day

`Organism(record_first=True, record_invalidation="context" | "dependency")`. Off by default; the organism is then unchanged. On, `_ask` first checks the held record for the exact query key: the pid must be in `standing` and ASSERTIVE, its denial neither asserted nor disputed, the organism unfaulted, and — in dependency mode — every root ASSERTIVE; in context mode, additionally no accepted mutation since the record was last validated. A validated hit is served with no walk and no `Workspace.ask` call, and the response carries `route = "hit"` with the number of dependency edges checked as its work. Everything else routes to the walk and names why (`miss`, `rejected:<check>`).

Hard law: on generated streams in both worlds, both modes agree with walk-first and with the oracle on every probe. Zero faults. Routes at n=80 per world: dependency 11 hits / 170 misses; context 1 hit / 10 rejected / 170 misses — the generator's interleaved facts invalidate almost every record under whole-context invalidation, as the directive's order of work anticipated. Cost, within the organism's own counters: repeat asks 10.9 (dependency) vs 13.7 (walk-first) at n=40; a hit costs the size of its support set. Under the no-cascade ablation the record check refuses the dead-rooted record and the walk reproduces that ablation's own known defect, so the fast path adds no stale answer beyond walk-first. Through `Stream`, the flag is identity and a restored stream hits from the replayed record.

## Record-first with RPA (contract M8.6), landed the same day — measured zero

The fourth path. `scripts/cas_memory/rpa_adapter.py` imports the RPA model from the mounted checkout (`eb99855`, never copied) and projects one organism's workspace into an atlas that validates under the model's own rules: givens OBSERVED, standing conclusions VERIFIED and reachable from the present with their supports as evidence, told guesses HYPOTHETICAL, contradicted records UNKNOWN, retracted ones REJECTED. `RpaNarrower` is injected as `Organism(record_narrow=...)`; it may only remove candidates (E-ORG-007 otherwise).

Pre-registered expectation: zero difference from the dependency-mode path. **Measured: zero.** On every probe of both worlds at n=40 and n=80 the RPA path has identical verdicts, lacunae, contested keys and routes to record-first without RPA (5 hits / 84 misses per world at n=40), the atlas removed no candidate, no faults. On this family the atlas adds nothing an ordinary record check does not already decide. It stays as the comparison path and for inspection of branches; the experiment reports it as "not run", with the reason, when the checkout is not mounted (CI).

## Next

The generator classes the evaluation plan needs (§4), the live S3 run once a valid key is present, then the development-seed dry run on the target instance before anything is frozen.
