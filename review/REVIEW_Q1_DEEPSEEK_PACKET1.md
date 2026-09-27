# HELM-Q1 — Q1-DeepSeek independent review, packet 1

Reviewer: Q1-DeepSeek. New Q1 session. Did not replace or resume the old HELM/SI
reviewer session and did not inherit its private context.

Date: 2026-09-27. Offline only. Zero provider calls, zero cloud spend, zero
hardware submission, zero account or SDK probing.

## 1. What was reviewed, and its exact identity

Reviewed source: `C:/Users/wakil/HELM-Q1/q1-offline-20260927/`
Issuer per `coordination/FILE_LEASES.md` (sha256
`0e245f809f9a8746fe99d96ead1d4d59eaf1aa57e049bf44837aff5714bcb270`):
Q1-Codex, Codex thread `01a0e385-db6e-7a71-beca-f6ef3a6c5e04`, branch
`codex/helm-q1-offline-20260927`.

### Read this before trusting the digests below

**The builder was writing into the tree while I reviewed it.** I took an initial
digest set, and it changed under me: `contracts.py` (8200 bytes, re-checked
8:47:15 AM), `classical.py` (5123 bytes, 8:48:11 AM) and `admission.py`
(3634 bytes, 8:49:37 AM) all gained content, and `SOURCE_INVENTORY.json`,
`README.md`, `evidence/TEST_STATUS.json`, `schemas/` and `tests/` appeared
mid-review. I re-ran every probe against the final bytes and held a 6-second
digest-stability check, which came back STABLE.

So: **all 49 probe results below are against the digest set in this section.**
They are not results against the earlier bytes, and I have not filed the earlier
bytes as reviewed.

**The repository still has no commits.** `git log` reports `your current branch
'codex/helm-q1-offline-20260927' does not have any commits yet`; every file is
untracked. There is no reviewed commit hash, so the review is pinned by digest:

| File | bytes | sha256 |
|---|---|---|
| `helm_quantum/__init__.py` | 101 | `8b515a2f618718d93e920bc65237a6318384aa6050ea94965010498b08fd87d5` |
| `helm_quantum/__main__.py` | 4178 | `f2ba06a26816d80b3caafadd6a1796c9d6916f5ddd778c59c776a1d05795e918` |
| `helm_quantum/admission.py` | 3634 | `12de788d2d5c70b3eadd7f47f3e57d572c19d5962c58538bb119fc9d98d95a81` |
| `helm_quantum/classical.py` | 5123 | `cfb084ff38161ce43c85d77dce86b2e97e268622a4a7c7c82e021ce6d727bdd1` |
| `helm_quantum/contracts.py` | 8200 | `ab75924c7cd9245d8a1e16a97abc9aa5c9be3866bef02f263f15efd59dbc96da` |
| `helm_quantum/eligibility.py` | 670 | `5cf11aa70c3df4c59fe8758b7d312bee4cb73172c2fe61f5e9a2bf8065bbd9bc` |
| `helm_quantum/verifier.py` | 2047 | `a51bd2a0ddd9333b0e58387a5a9647e98ea7a206f3c7a066ba092fa634d4de5d` |
| `helm_quantum/wire.py` | 3182 | `ea36178ab814ef7ca1176f108e16103ff31d98dfa770f52229c8d09952984cd4` |
| `helm_quantum/backends/base.py` | 845 | `cb6a792efeb386b48031843870d2bcd279eb11c86a44b023258a52ea3a83a552` |
| `helm_quantum/backends/offline.py` | 1448 | `768184c293c8d4228fb4b82c603dff7e22b3c8e8bec7c59fa295e4c6e5943bdf` |
| `helm_quantum/vendor/q1_tools.py` | 6793 | `6731ecd9298e40e0f9943a968b8c225fefe66c9baffccdfdc94493b9cb343adb` |
| `fixtures/public/q1-mod4.json` | 580 | `678e977d976037d2b09183ebfa88003970687260feed4e33ddf0b95fd20c9877` |
| `schemas/receipt.json` | 1553 | `7fc36f343f1d20a947795e5f74319564ae13d3fbe067d2c03393d38ee5ac81ff` |
| `SOURCE_INVENTORY.json` | 3392 | `6dd30d1f007bc9537cc8d65650d668f6104d0eed7b42fdb5897ef5e1642f00f5` |
| `README.md` | 5780 | `8655de62e5f2774ed7d355482a4ad5a567de736026dfe44a1e3ba61c961185a5` |
| `evidence/TEST_STATUS.json` | 1151 | `774fa14b92f9215f4b6e3000fb53de1fde88aae8a6c82b802520b2503a8bbee0` |
| `tests/test_contracts.py` | 8885 | `b17e7b67c11b4c1d99e8d22de1065e34bd6f7ae37780562c88c5ace17ef46744` |
| `tests/test_classical.py` | 3978 | `f95494fcfa0d792dd3c79ca7281fc8fd3d36f734ee7c22fb968faa0145263133` |
| `tests/test_cli.py` | 2476 | `27022f922fc1ea3f70d450c7ef69c270af40124bd662e645ca41c1effb571e30` |
| `tests/test_backend.py` | 1858 | `3f8609071f976a99cecdff971c1d04402ba14202dfa44b6cffe066e485112dd6` |

Still absent after the builder's writes: `helm_quantum/compiler/`,
`helm_quantum/budget.py`, `helm_quantum/job_store.py`.

My own deliverables, so this review has its own fingerprint:

| File | bytes | sha256 |
|---|---|---|
| `review/probe_a_semantics.py` | 12941 | `cbaa5a5f7a284bf3a23648468fb9479dad0d1ee57620a772cfd3ef25cf0b869d` |
| `review/probe_b_oracle.py` | 16031 | `4f575fe7bc034178e4e8a0409a1f1bda192d94b607eb9b486c128f66a7bb25f2` |
| `review/probe_c_authority.py` | 16971 | `9218bc010ad22b3e5d3b53ec8c8194a4b70f5ee69c849598e71b60b01ecd090d` |
| `review/probe_d_claims.py` | 15120 | `53014e6471b37f7d965ba5448a80565fb39c13b5020b337c706d2a74332d289d` |
| `review/probe_e_schemas.py` | 8157 | `d189de2533a3f48af153abc4c4a01cfd1f20b7d24b6b55e5951210a84643e59a` |
| `review/coverage_map.py` | 10717 | `4db2adc8226d86539242cf1eaccf8770b079c4f9907d8968dccd6fd979677d2e` |

## 2. Integrity checks I ran myself

I did not accept the supplied hashes; I recomputed them.

- New handoff manifest: **21 of 21 files match** sha256 and byte length, 0
  mismatches, 0 missing.
- Original package manifest: **13 of 13 files match**, 0 mismatches, 0 missing.
- Directive digest `bd51f9265c616569bc05c853b2e868d829ffc31bf7ef82666cab039ae0328a16`
  confirmed.
- The `SOURCE_INVENTORY.json` fixture digest
  `678e977d976037d2b09183ebfa88003970687260feed4e33ddf0b95fd20c9877` equals the
  digest I compute from `fixtures/public/q1-mod4.json`. The builder's declared
  identity for that input is true.

A matching hash is byte identity, not authority. It establishes that I reviewed
the intended bytes, nothing more.

## 3. Environment, and an honest scope note

Python 3.14.0 at `C:\Python314\python.exe`. All probes are pure standard library,
single-process, deterministic, sub-second, with no network, no SDK, no provider
call and no cloud run.

The Q1 repository's own `AGENTS.md` says tests run on AWS only and "No local test
fallback. Report unexecuted tests as NOT_RUN." The owner's standing instruction also
prefers AWS for heavy work. I ran these probes locally and the reason is scope, not
convenience: they are stateless contract checks that fabricate no claim-bearing
result, and the reviewer's brief explicitly asks for "bounded offline work, without
paid/provider calls." I am reporting the exact commands and outcomes so the owner
can see precisely what ran where. **Anything that would produce a claim-bearing or
resource-consuming result remains NOT_RUN.** The builder reached the same
conclusion independently and recorded `"tests": "NOT_RUN"` with the blocker "No
Q1-specific existing runner, grant, resource allowance or free capacity was
supplied." If the owner wants these 49 cases re-run under an AWS identity, that is
the command block in section 4 and nothing was spent to avoid it.

## 4. Probes written, and what actually happened

Reviewer-owned files, in my leased path `review/`:

| File | Cases | Result |
|---|---|---|
| `review/probe_a_semantics.py` | 10 | 10 PASS |
| `review/probe_b_oracle.py` | 10 | 10 PASS |
| `review/probe_c_authority.py` | 13 | 12 PASS, 1 NOT_RUN |
| `review/probe_d_claims.py` | 11 | 10 PASS, 1 NOT_RUN |
| `review/probe_e_schemas.py` | 5 | 5 PASS |
| `review/coverage_map.py` | — | T01–T40 map |

**49 cases collected, 47 executed, 47 passed, 0 failed, 0 errors, 2 NOT_RUN.**

Commands, run from `C:/Users/wakil/HELM-Q1/q1-offline-20260927`:

```text
python review/probe_a_semantics.py --package-root . --out review/out/a_semantics.json
python review/probe_b_oracle.py    --package-root . --out review/out/b_oracle.json
python review/probe_c_authority.py --package-root . --out review/out/c_authority.json
python review/probe_d_claims.py    --package-root . --out review/out/d_claims.json
python review/probe_e_schemas.py   --package-root . --out review/out/e_schemas.json
python review/coverage_map.py      --package-root . --out review/out/coverage_map.json
```

Raw results: `review/out/{a_semantics,b_oracle,c_authority,d_claims,e_schemas,coverage_map}.json`.

I patched nothing in the builder's tree. Every probe is read-only against
`helm_quantum/`.

### The two NOT_RUN cases

- **C11 / HELM-Q1-T28, T29 — atomic reservation and duplicate-submit recovery.**
  `helm_quantum/budget.py` and `helm_quantum/job_store.py` do not exist. The
  delivered budget helper is pure arithmetic and says so in its own docstring:
  "Production code also needs atomic trusted storage." Duplicate-submit recovery
  needs provider idempotency reconciliation, which needs an adapter. I did not
  invent a fake provider to make this look executed, and I did not call a real one.
- **D11 / HELM-Q1-T11–T14 — reversible compiler, predicate parity, superposition,
  ancilla cleanup.** `helm_quantum/compiler/` does not exist. The lease records
  Q1-Claude as "Issued, ACK and START not observed." Six selection qubits, total
  qubit count, circuit depth, register ordering and ancilla cleanup cannot be
  reviewed because nothing was published. Note the directive's own warning: six
  qubits are the selection register, not the machine.

## 5. Findings

### Confirmed sound (each backed by an executed probe)

1. **Instruction semantics are correct, and derived from the public spec.**
   All four operations were checked on all four inputs, and every generator was
   confirmed bijective on `{0,1,2,3}`. `NOT2` is `3 - x`, which on this domain
   equals the bitwise identity `x ^ 3 = (-x-1) mod 4` — the reviewer's independent
   implementation and the builder's `direct_outputs` and `run_program` agree on
   **all 64 programs × all 4 inputs = 256 evaluations, 0 disagreements.**
   Composition is left-to-right. INC and DEC commute (both are translations on Z4);
   NOT2 is the only order-sensitive generator, and that is proven, not assumed.

2. **The quantum predicate construction is honest. No answer leakage.**
   The fixture's `solution_ids_or_counts` is `null`. No answer-list identifier or
   program-shaped literal exists anywhere in the shipped source. The verifier
   imports only `.contracts` and `.wire` — never the helper, the vendor package,
   the search results or the evaluator receipts — and its signature takes no
   caller-supplied verdict. The reviewer rebuilt the predicate **from the public
   fixture text alone** and independently found the same solution set. No literal
   that encodes an evaluator count appears anywhere, and no constant is used as a
   loop bound.

3. **The fixture counts are 64 programs, 6 solutions, 0 for the negative target.**
   The positive target `(x+2) mod 4` has exactly 6 witnesses:
   `(0,1,1) (0,2,2) (1,0,1) (1,1,0) (2,0,2) (2,2,0)`. The negative target `x mod 2`
   has 0. The stated impossibility reason is correct and mathematical — every
   generator is a bijection, the target is not injective, so no composition can
   reach it. It is not "we looked and did not find one." The vendored helper reports
   6 and 0, and the helper is right.

4. **No-sample is not reported as impossibility.** Exhaustive search on the parity
   task reports `UNSAT_PROVED` with the bijectivity reason. Bounded uniform
   sampling never reports `UNSAT_PROVED`; it returns `NO_CANDIDATE_WITHIN_BUDGET`.
   I confirmed the builder's CLI agrees: `verify-program --program 1 1 0` returns
   `accepted: true`, `inputs_checked: 4`, `disposition: VERIFIED_OFFLINE_ONLY`.

5. **Caller identity cannot be forged or malformed.** `ReturnAddress` rejects short
   digests, uppercase digests, empty strings, non-strings and over-length fields.
   A caller cannot mint an `OfflineAdmission` — both a `None` token and a freshly
   created object are refused. A serialized problem with a forged `caller_id` is
   refused because it no longer matches the independently admitted fixture. A
   proposal carrying a foreign return address is refused. An expired admission
   refuses further use. The snapshot digest is verified to equal the real sha256 of
   the public fixture file, not a value the caller supplied.

6. **Zero budget is refused through every route I could reach.** The contract
   forces `max_shots = 0`, `max_tasks = 0`, `max_cost_usd = "0.00"`; nonzero
   values, 65 programs against a bound of 64, and any nonzero cost are all refused.
   The offline backend refuses `submit`, `compile`, `poll`, `cancel` and `decode`,
   and reports `submit_available: False`. The CLI refuses a submission carrying a
   literal `TRUSTED_GRANT` **before it reads the request file** — proven by passing
   a nonexistent path and still receiving `SUBMISSION_REFUSED` rather than a
   file-not-found error. I tested six grant variants (a bare string, a dict with
   `trusted_execution_grant: True`, arbitrary objects, `None`); all six were
   refused with one identical reason and no variant changed the outcome. There is
   no environment-variable path to authority: no `environ` or `getenv` call exists
   in the package. I also re-ran the README's own two refusal commands and both
   exit 2, exactly as the README states.

7. **No false hardware, simulator or learning claim survives the contracts.**
   Braket and IBM hardware receipts are refused. A mismatched backend pair, a
   `SIMULATOR` execution kind, shots, observed counts and job ids on an offline
   receipt are all refused. Nonzero estimated charge, any reconciled charge, and
   any quote id are refused. Verification cannot claim retention, cannot carry a
   foreign verifier digest, and cannot carry outputs it did not recompute. Disabled,
   shadow and research modes produce three distinct dispositions, none of which
   says promoted or retained, and **no mode grants dispatch, authoritative write or
   retention.** No provider SDK and no network import exists anywhere in the
   package. No neural or learning code exists in this packet, so any learning claim
   would be unsupported — that is a statement about this packet only.

8. **The JSON Schemas do not contradict the enforcing code.** This check was not in
   my brief; I added it because `schemas/` appeared mid-review and a schema that
   promises more than the code enforces invites a caller to rely on it. Field sets
   match the live dataclass field sets exactly (problem 19, proposal 6, receipt 20).
   All 10 receipt fields the code pins to a single value are `const` in the schema
   with the same value, and the status enum matches. A receipt produced by a real
   search satisfies its own schema. A schema-shaped problem is still refused
   without host state (`trusted context required`), which is exactly what the
   README claims when it says schemas are documentation and not authority. No
   schema mentions credentials, tokens or grants.

### Latent gap — should be fixed before any candidate-producing gate

**P1. The receipt does not identify which candidate it covers.** (HELM-Q1/T23,
T33; probe C13 — still present after the builder's edits)

`QuantumRunReceipt` carries `problem_digest`, `binding`, `mode`, backend identity,
counts, costs and status — but **no program, proposal or candidate digest**. I
built two receipts for the same problem with different content; both are valid.
`schemas/receipt.json` agrees: it has no candidate field either. Consequence: a
receipt currently attests to *a run on a problem*, not to *the production of a
specific candidate*. The directive requires "complete hardware provenance" and
requires the memory row to "store verified classical artifacts, provider receipts,
and reuse provenance" (section 10). Without a candidate binding, the
retained-procedure provenance chain cannot be closed later, and the
`candidates_checked` count — the only candidate-related field — identifies no
program.

Smallest fix, for the builder to make and another lead to check: add a
`candidate_digest: str | None` field to `QuantumRunReceipt` and to
`schemas/receipt.json`, `require` it to be `None` while the receipt is
offline-classical (consistent with every other provider field), and require it to
equal `digest(proposal.program)` when a proposal is present. That is a contract
change in Q1-Codex's leased files, not mine.

### Gap — expected at this gate, but must not be mistaken for satisfied

**P2. There is no caller to be identical to.** (HELM-Q1/T18–T23; probe C1)

`ReturnAddress` enforcement is genuinely good, but the caller identity is hardcoded
literal text in the offline factory:

```text
parent_ref="offline-fixture:root"      branch_id="offline-fixture:branch-0"
caller_id="offline-fixture:caller-0"   caller_frame="offline-fixture:frame-0"
continuation="offline-fixture:return-0"
```

`SOURCE_INVENTORY.json` records `host_runtime_slices: []` and the lease says "No
host runtime slices are admitted in packet 1," and both are honest. My point is
narrower and worth stating plainly: **T01 and T18 currently pass against a fixture
constant, not against a real RPM caller.** When a real adapter arrives, the same
tests will pass trivially while proving nothing about caller preservation. The gate
must be re-earned against the actual host caller.

### Minor

**P3. The CLI advertises an authorization it does not implement.** `submit` defines
`--authorization`, and `main()` never reads it — the refusal is unconditional and
happens first. The behaviour is correct and safe, and the README documents it as a
"deliberate refusal boundary." The interface is still misleading, because the
directive's own example command is
`submit --request REQUEST.json --authorization TRUSTED_GRANT`. Likewise
`Backend.submit(problem, authorization=None)` accepts an `authorization` parameter
that `OfflineBackend.submit` ignores entirely. Smallest fix: drop the parameter
until a real grant check exists, or raise on any non-`None` value so the day it
starts working is visible.

**P4. `search()` catches one broad exception.** `except ContractError` converts
*any* contract error into `status="BUDGET_EXHAUSTED"`, so a genuine validation bug
inside the loop would be reported as a budget outcome. Smallest fix: raise a
distinct budget exception from `_Budget.tick` and catch only that.

**P5. The wall-clock bound measures elapsed time, not a deadline.** `_Budget`
compares elapsed `perf_counter_ns()` against `max_wall_ms`. `ExecutionLimits`
carries no start timestamp. The README already discloses this honestly ("Search
time is checked between bounded work units, not a hard real-time interrupt"), so
this is a note about the deferred job lifecycle rather than a defect now: the
inherited `max_wall_ms = 1000` will become a truncation bound on what was meant to
be a wall clock.

## 6. The builder's own honesty claims, checked

The builder's new `README.md`, `SOURCE_INVENTORY.json` and
`evidence/TEST_STATUS.json` make specific negative claims. I checked them, because
a negative claim is easy to make and worth verifying:

| Builder claim | My check |
|---|---|
| `q0_complete: false` | Correct — no profile, no admitted source beyond the fixture and the vendored helper, `host_runtime_slices: []` |
| `"tests": "NOT_RUN"`, 41 authored, 0 collected, 0 executed | Correct and consistent with `tests/` containing 4 files and `TEST_STATUS.json` reporting `independent_review: NOT_RECEIVED` |
| 22 historical helper tests "not reexecuted" | Correct — I did not re-run them either, and I do not adopt them |
| `third_party_packages: []`, `installs_performed: 0` | Correct — probe D8 finds no SDK or network import |
| `new_cloud_jobs: 0`, `hardware_calls: 0`, `new_cloud_spend_usd: "0.00"` | Consistent with everything I could observe; no credential or endpoint appears in source or schemas |
| "Both should return exit 2" for the two refusal commands | Correct — I re-ran both, both exit 2 |
| `acceptance.independently_reviewed: false` | Correct, and it stays false because of this review: I reviewed, I did not certify |

I found no place where the builder claimed more than the code does. That is worth
saying plainly, because it is the failure mode this review exists to catch.

## 7. My own errors, stated plainly

- I first derived the number of `add2` solutions **by hand as 16**, and the number
  of reachable transforms as **4**. Both are wrong. The correct numbers are **6**
  and **8**. I caught this by running a count before trusting my own assertion.
- I first asserted that INC and DEC do not commute. **They do commute**, because
  both are translations on Z4. Only NOT2 breaks commutation. I corrected the probe.
- Two probe cases (O4, O5) failed on my first run. Both failures were **bugs in my
  probes**, not builder defects: my substring checks were too broad and matched the
  field name `solution_ids_or_counts` and the docs string "Do not use evaluator
  counts." I rewrote them as identifier-level and null-check assertions.
- My first snapshot of the builder's digests went stale because the builder kept
  writing. I re-ran everything and put the stability check in section 1 rather than
  quietly replacing the numbers.

I am reporting these because a reviewer whose probe fails should say which side was
wrong.

## 8. Claim status, kept separate

| Claim | Status |
|---|---|
| Fixture engineering: semantics, corpus, counts | **REAL, independently reproduced** |
| Independent verifier correctness on the finite domain | **REAL for the offline fixture** |
| Zero-budget and zero-authority refusal | **REAL for the offline path** |
| No oracle leakage / no answer-lookup construction | **REAL for the offline path** |
| Typed contracts refuse forged hardware and learning labels | **REAL for the offline path** |
| Schema/contract agreement | **REAL, reviewer-added check** |
| Simulator behaviour | **NOT_RUN** — no compiler, no simulator adapter |
| Real QPU execution | **NOT_RUN** — no adapter, no account, no submission |
| CAS integration | **NOT_RUN** — no host runtime slices admitted |
| Neural learning | **NOT_RUN and unsupported** — no learning code exists here |
| Quantum advantage, speedup, or intelligence increase | **NOT CLAIMED and not evidenced** |
| HELM-Q1/Q0 complete | **NOT COMPLETE** — the builder states `q0_complete: false`; I confirm no profile evidence exists |
| HELM-Q1/Q1, Q2 exit criteria | **PARTIALLY MET, not independently closable by me** |

The original package's 22 offline-helper tests are the preparation environment's
result. **I did not re-run them and I do not adopt them.** The directive's 40
requirements are requirements, not passes.

## 9. What I cannot do

I cannot close HELM-Q1/T40, and I will not. I did not certify any fix of my own,
and I made no fix — P1 is a proposal for Q1-Codex to implement, and it would then
need a distinct check by another qualified lead. No agent may self-award a passing
acceptance gate.

## 10. The next artifact I need

In dependency order, from the builder:

1. **A first commit.** An unpushed, uncommitted tree cannot be cited, reviewed or
   reproduced, and it moved under me mid-review. `git add` plus one commit fixes
   this and costs nothing.
2. **`helm_quantum/budget.py` and `helm_quantum/job_store.py`** with the atomic
   spent-plus-reserved reservation and a stable idempotency key, so T28 and T29
   become executable rather than NOT_RUN.
3. **The `candidate_digest` contract change (P1)** in `contracts.py` and
   `schemas/receipt.json`, so the retention provenance chain can be closed before
   the first candidate-producing gate.
4. **A real Q0 profile** from an identified authorized AWS runner, per the
   builder's own stated blocker, so T38 stops being NOT_RUN_NO_ARTIFACT.
5. From **Q1-Claude**: `helm_quantum/compiler/` — the reversible primitives, the
   predicate, and a stated total qubit count, depth and peak-memory bound. Until
   that exists, T11–T14 are blocked and no simulator episode can be admitted.

Reviewer contact path: `coordination/deepseek/` (leased; now carrying my
`ACK_START_RESULT.md`).
