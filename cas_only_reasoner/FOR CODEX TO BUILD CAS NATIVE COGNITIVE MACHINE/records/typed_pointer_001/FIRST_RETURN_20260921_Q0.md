# First return — Q0 closed, evidence boundary verified, lineage reconciled

**Answering:** `FABLE_HELM_CAS_Implementation_Directive_v1.md` §15 ("the first return") and the
owner's instruction of 2026-09-21 on versioning, preservation and the best seed.
**Date:** 2026-09-21. **Cost:** `$0`. No GPU, no reservation, no claim promoted.
**Plain English throughout; every literal exact.**

---

## 1. Resolved branch and HEAD

| | |
|---|---|
| worktree | `…/_worktrees/vision-next` (the CNCM package root is two directories below it) |
| branch | `research/helm-2.0-iterating-rounds` |
| HEAD at the start of this return | `27fd569831660f35f49c342ceef139c8110a766c` |
| merge-base with `codex/cncm-vision-next` | `6580add44bd1c748f9691d36d72cf86d4e6ea173` |
| remote | `origin` → `https://github.com/LittleHenderson/noetic-compass.git` |
| pushed? | **No** — the branch did not exist on `origin` at the start of this return. Pushed at the end of it (see §9). |
| working tree | clean at the start; the files this return adds are committed by explicit path |

## 2. The five reported commits, resolved — and the six that were not reported

| short | full | author session | what |
|---|---|---|---|
| `7f3a656f` | `7f3a656f60a9b112d6127f1c36f4db38fd2bc4ac` | this session | F1/F2a/F2b/F4 |
| `9f61ffbb` | `9f61ffbb030f5aa75442d9bedf9de8cc8bbf62d8` | this session | audit check 4 → COULD NOT RUN |
| `c8d5c430` | `c8d5c430eec23a8fadd98bbcd045fecf03d86239` | this session | F3 ladder — **and 1,544 swept files, see §3** |
| `3459ea38` | `3459ea3868804b1db6e25fd054cdee900c54836d` | this session | expression-space review |
| `27fd5698` | `27fd569831660f35f49c342ceef139c8110a766c` | this session | review addendum — **and swept files, see §3** |

Between `9f61ffbb` and `c8d5c430` sit commits from **a second agent session working on this same
branch in this same worktree on 2026-09-20**, which the directive's sources did not see:

| commit | time (−07:00) | what |
|---|---|---|
| `df20eb46` | 11:44 | moved the certified Helm 1.0 evidence to `receipt_helm1_certified_*` / `admission_helm1_certified/` — a pure rename, 2,554 files, zero content changes |
| `26de5ec6` | 11:48 | froze the Helm 2.0 three-job study |
| `f4e5b3a4` | 11:52 | launched Helm 2.0 on AWS; `PREFLIGHT_PASS` |
| `a321fdf2` | 12:25 | recorded a first-update gradient blow-up, and that its own warm-up hypothesis was wrong |
| `9e9ba62a` | 14:02 | fixed the NaN: `sqrt(clamp(mean_sq))` instead of `clamp(sqrt(mean_sq))` in `_rms_unit` — forward bitwise unchanged, backward finite. A defect my F1 made reachable (a node with no parents or children now yields a zero row). Correct fix, well recorded. |
| `20208c92` | 14:02 | preserved the failed run as `receipt_helm2_gradfail_20260917/`; cleared the canonical names |
| `3da10d84` | 14:06 | refroze the study at `20208c92` |

The unattributed `RESULT~1(6).JSO` the directive flags names source
`9b84b35c82bda422f744e76a170892313bc8b61b`. **That is a commit dated 2026-09-19** ("Supersede the
smoke admission again") — a Helm **1.0** smoke package, one day before 1.0 was certified and two
days before any Helm 2.0 code existed. It must not be attributed to Helm 2.0.

## 3. The evidence boundary — what was found, what is true

**Finding.** After `3da10d84`, the three Helm 2.0 AWS jobs completed and their receipts were
collected into the working tree under the *old* certified names (`receipt_2026091x/`,
`admission_001/`), uncommitted. My `git add -A` in `c8d5c430` and `27fd5698` then committed them
under my own messages. I did not know a second session was on the branch.

**Consequence checked, not assumed.**
- The certified Helm 1.0 evidence is **intact**. Every checked file under
  `receipt_helm1_certified_2026091{7,8,9}/` matches the `c95dc6ac` bytes;
  `admission_helm1_certified/gate_reading.json` is still `475379d2f9d47387…`;
  `study_helm1_certified.json` points at the renamed receipts;
  `verify_evidence_hashes.py` (the other session's implementation of the digest check my audit
  asked for) → 297 files, `EVIDENCE_HASH_CHECK:PASS`.
- The three new `receipt_2026091x/` are Helm 2.0-experimental runs, source `20208c92`, all
  `COMPLETE_TYPED_POINTER_ARM`, hashes `PASS` 297/297 each.
- **An archive copy I made at the start of this return was wrong**: I copied the new
  `receipt_20260918` (Helm 2.0) into `D:\tksCAS-archive\helm_1_0_certified\`. Removed and replaced
  with `receipt_helm1_certified_20260918`, verified against `c95dc6ac`. Recorded here so it is not
  repeated.

**Claim ledger for this section:** *reproduced* — the 1.0 evidence hashes, the 2.0 evidence hashes,
the 2.0 grader label, all 2.0 numbers recomputed from raw `correct` flags; *contradicted* — nothing;
*unresolved* — none on the boundary itself.

## 4. Helm 2.0-experimental: the result, in the directive's four statuses

Full tables are in `BRAIN_LINEAGE.md` ("Helm 2.0-experimental — RAN") and the CHANGELOG entry of
2026-09-21. The short form:

| status | reading |
|---|---|
| `engineering_status` | **PASS** |
| `representation_status` | **PARTIAL** — `correspondence` 0 → **20/20** on never-shown worlds, all three seeds; `analogy` 0/17 unchanged |
| `operation_status` | **N/A** — no CAS operation modules in this lineage |
| `benefit_status` | **MIXED. Not an upgrade on the certified instrument.** Label `NO_TRANSFER_TO_NEW_WORLDS`; two seeds broke one frozen question each; above-floor 2/2/2, level with 1.0. Held-back 127: +19/+17/+18. Whole course: +103/+73/+83. Retention: **−15**, 0, **−5**. `reach` −2/0/−3. |

**Mechanism-free baseline registered before the correspondence number is quoted:** on the same 20
held-back questions, exact match against the checker's admissible answers — unique-signature
structural match **4/20**, positional 0/20, always `NO_MATCH` 0/20. Helm 2.0: 20/20. **Open:** a
full isomorphism matcher with lexical tie-breaks (stronger baseline) is not yet registered.

**Best seed:** 20260918. **Preserved** at `D:\tksCAS-archive\helm_2_0_experimental_20208c92\`.
**Best certified seed:** Helm 1.0's 20260918, preserved at `D:\tksCAS-archive\helm_1_0_certified\`.
Both hash-confirmed. Neither will be overwritten.

## 5. Lineage reconciliation (the owner's progression, mapped onto the file's rules)

`BRAIN_LINEAGE.md` now carries, marked **proposed, owner to ratify**:

- **X.0-experimental** — shape changed, `$0` gate passed, whatever the grader printed is recorded. Claims nothing.
- **X.0-rc** — grader printed `LEARNS_NEW_WORLDS` on three seeds **and** comparative acceptance recorded in four statuses across every task family.
- **X.0** — rc + independent audit + release notes naming every regression.

Under it: **Helm 1.0 = release. Helm 2.0 = 2.0-experimental, cannot be rc** (gate failed).
**Helm 3.0-experimental** = reserved for the CAS-integrated shape; nothing built. The owner's
"preserve Helm 2.0 as baseline and rollback target" is honoured as: **both** 1.0 (certified baseline)
and 2.0-experimental (engineering baseline) are preserved and both are comparison arms for any 3.0
run. Any weight reuse needs a migration record listing every tensor as carried / reshaped / absent /
fresh.

## 6. Permissions in force (the execution-authorization record)

The directive's `templates/EXECUTION_AUTHORIZATION.json` is not on this machine — only the `.md`
was supplied — so the record is written here from the standing rules:

| action | status |
|---|---|
| reversible source inspection, isolated development, deterministic tests, `$0` CPU checks | **permitted** (standing) |
| local **CPU** neural training | **prohibited** (GPU-first rule, fail closed `GPU_REQUIRED`) |
| local RTX 4070 | **smoke / dev only** (standing) |
| AWS claim-bearing runs | **per-job owner authorisation**; the 2.0 study ran under the campaign ledger (`15.00` per job) |
| push after commit | **standing instruction; obeyed in §9** (no force, no deletion, no merge) |
| changing the frozen 18, the pass mark, `evaluate_gates.py`, the rehearsal copy | **prohibited** |
| editing `BRAIN_LINEAGE.md` verdict rows | done only as **new rows / marked proposals**, never edits to old rows |

**The one narrow resource question (directive §3):** may the standalone Expression Lab's
engineering smoke — one seed, ≤ 128 updates, ≤ 2,048 records, width 64 — run on the **local RTX
4070** as dev/smoke under the standing rule? It is not claim-bearing. If no, it is prepared and left
`ENGINEERING_READY / EXECUTION_BLOCKED_RESOURCE`.

## 7. Existing code to reuse (verified on disk this session)

| what | where | note |
|---|---|---|
| executable CAS operations: `compose`, `involute`, `is_admissible` | `noetic-compass-scaffold/noetic-compass/cas-engine/src/ontology/operators.rs:79-110` | the `T_k` for Q2 |
| `domain_descent`, `rpm_gate`/`PrerequisiteGate`, `RegisterFiLM`, `OmegaRegistry`, `CognitiveStateEmbedding`, `StructuredPredictionHead` | `…/cas-native/model/` | CAS-Native; **Helm imports none of it** |
| the frozen 388-token CAS vocabulary with a passing round-trip test | `cas-synthetic/data/native_nl/cas_hybrid_tokenizer_v2_2026_05_07.json` | |
| the SDG (CAS → English) | `cas-synthetic/` | not an inverse translator |
| evidence digest check | `records/typed_pointer_001/verify_evidence_hashes.py` | other session; **passes both evidence sets** |
| the ruler / ladder | `records/typed_pointer_001/ladder/` (instrument of record), `ruler.py` (the other session's; the two agree, bar 0.53) | |
| F1 gate | `records/typed_pointer_001/rounds_iterate_check.py` | 6 checks |

## 8. Open evidence defects (Q0/Q1 items that remain)

1. **The grader still does not verify evidence digests itself.** `verify_evidence_hashes.py` is a
   separate check; `evaluate_gates.py` is frozen and must stay so. Q0 asks for the scorer anchor to
   live *outside* the run directory and for **independent rescoring of raw predictions**. Not done.
2. **`planned_main_updates` is not wired** — F4's schedule was dormant in all three 2.0 runs.
3. **Correspondence decoding**: soft Sinkhorn rows are argmaxed independently; the directive's D08
   is right that this does not guarantee a discrete bijection. The 20/20 is real under the current
   decoder, but joint decoding and separate soft/decoded reporting are owed.
4. **No ablation separates F1 from the NaN repair from F2b.** "The loop repair did it" cannot be said.
5. **Stronger correspondence baseline** (isomorphism + lexical tie-break) not registered.
6. **Two-session hazard.** Same worktree, same branch, `git add -A`. Fixed by §9.
7. The directive's companion package (`sources/`, `templates/`, `TASKS.json`, `ACCEPTANCE_TESTS.json`)
   is not on this machine.

## 9. Tasks assigned, and the next actual command

Roles per the directive, honestly collapsed to what exists:

| role | who | first task |
|---|---|---|
| F0 lead | this session | this return; then Q2 |
| F1 Helm engineer | the *other* session, on `research/helm-2.0-iterating-rounds` | wire `planned_main_updates`; joint correspondence decoding; the F1-vs-NaN-vs-F2b ablation |
| F2 CAS semantics | this session, in its own worktree | `OPERATION_CONTRACTS.json` from `operators.rs`, `composition.py`, `rpm_gate.py` |
| F3 data | this session | behaviour-paired SDG adapter (Q3) after Q2 |
| F4 representation | this session | R0 / R1 encoders (Q4) after Q3 |
| F5 evaluation custody | **nobody independent exists** → any protected claim is `EVALUATION_NOT_INDEPENDENT` until a separate session holds the final split |
| F6 adversarial | a fresh session, on request | reproduce this return |

**Next actual commands, in order:**

```bash
git worktree add "../helm3-lab" -b research/helm-3.0-cas-lab
```
then, in that worktree, Q2:
```bash
python research/helm_cas_expression_lab/build_operation_contracts.py   # to be written first
```

**Pushed:** `research/helm-2.0-iterating-rounds` to `origin`, after a secret scan of the whole
branch diff, at the end of this return.
