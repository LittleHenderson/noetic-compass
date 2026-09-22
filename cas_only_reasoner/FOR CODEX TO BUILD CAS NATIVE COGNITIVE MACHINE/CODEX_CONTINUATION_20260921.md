# Codex continuation — 2026-09-21

The user asked Codex to continue the Helm/CAS work. The next completed unit is
T13 input-boundary hardening, a prerequisite for Q4. This is a code/test result;
no neural training, model inference, cloud job, scientific acceptance, or release
promotion ran.

## Recovered state and ownership

- Original checkout: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\helm3-lab`.
- Branch: `research/helm-3.0-cas-lab`.
- Recovered HEAD: `c38552754388573be36a07f6863299d9db1a5f63`.
- Git common directory is the sibling `vision-next/.git`, not the main
  `tksCAS/.git`. The main checkout is on a different branch with unrelated edits.
- Original checkout contains fourteen modified tracked files plus untracked Q3
  v0.5 data, compiler tests, and the latest compiler report. They were left intact.
- Fourteen Claude processes were visible; command lines did not establish their
  source ownership. No matching local Python Helm/study process was found.
  This is not a provider-side job audit.
- Continuation branch: `codex/helm-cas-data-boundary-20260921`.
- Continuation checkout: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\codex-helm-data`.
- The isolated branch starts at the recovered local HEAD. It deliberately does
  not commit or overwrite the unfinished compiler/data edits. Compatibility
  with the newer local v0.5 data was checked separately, read-only.

## Implemented and checked

Loader 0.3 rejects overflowing JSON exponents such as `1e999`, malformed nested
visibility declarations, and `mode`/`operation_id` values that differ from the
family's existing contract. Previously, a header could contain an object such
as `{"answer": true}` and both the learner and evaluator doors accepted it.
Existing external manifest pins protected the pinned dataset; the gap affected
direct loading and validation before new data was pinned.

The fix does not change data, expected answers, split membership, reference
operations, frozen contracts, or model weights.

Validation with `C:\Python314\python.exe`, Python bytecode disabled:

| Check | Result |
|---|---|
| Existing loader/export tests before changes | 19 passed in 13.11 s |
| New regression cases before changes | 52 failed, 11 passed in 2.70 s |
| Existing tests plus new regression cases after changes | 82 passed in 15.64 s |
| New loader reading original v0.5 with its existing external pins | 10,421 records loaded; row/schema/split compatibility passed |

The original v0.5 manifest SHA-256 is
`304dc5c99c51441d432db7ef35be30b0fea97d64b9165f4ca43fa84c8b8c7616`.
An independent code reviewer found no regression in the three fixes and
verified that all 10,421 visible rows in each of v0.4 and v0.5 match the fixed
header values. This review does not establish independent scientific custody.

An initial test invocation failed to create a temporary directory whose parent
did not exist (3 passed, 16 setup errors). After creating a dedicated temporary
parent, the unmodified suite passed. No product defect was inferred from that
setup failure.

Re-run from the continuation CNCM directory:
```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:\Python314\python.exe' -B -m pytest research/helm_cas_expression_lab/test_q3_load_boundary.py research/helm_cas_expression_lab/test_q3_load_and_export.py -q -p no:cacheprovider
```

## Preserved unfinished work

The original compiler copies are not synchronized. LF-normalized SHA-256:

- Scaffold compiler: `7fb6cf2159092251856a90d8e2ffa5086fd21635f84e94675541479fd5fabaaa`.
- Offline compiler and v0.5 manifest compiler pin:
  `5c732d95f5862e5e3e5bf0a2296be092f0e9c980127a5690aec4d41567fdf775`.
- Attached report claims older `00834e0258ea6b461e019e93406256975078d7142a3750fe57dbc480a53ded5b`.

Read-only compiler review also reproduced loss of Drive-register distinctions
in nested-value set identity, a failing reserved-name diagnostic case, and
missing cross-Domain warnings on some call paths. The report's content-based
set identity claims are stale: newer code deliberately retains name identity
pending a decision. Code/tests now expose N1–N13 while that report lists N1–N9.
These observations are recorded for the next compiler continuation; this loader
change does not settle their semantics or mark the compiler bundle ready.

The loader's old universal exception-normalization statement was narrowed.
Malformed pin/contract metadata, undecodable pin bytes, and excessively large
JSON integers can still raise native Python errors. They were not newly
introduced and are separate follow-up checks, not claims closed by these tests.

## Next work and boundaries

1. Review and integrate this small T13 change with the latest source owner.
2. Reconcile the unfinished compiler source/package/pins/report, preserving
   owner decisions and history. Do not replace expected hashes solely to make
   a check green.
3. Continue the existing T14/Q4 order-blind control and encoder/decoder code.
   This turn did not implement or train those modules.

The original package's PLANNED task rows are preserved. W-A/W-B/W-C, the current
N questions, and PCBA route remain unresolved unless a later owner record settles
them. No new resource budget or neural-run authorization was inferred from the
handoff or from historical AWS receipts. Frozen Helm lineage and results remain
unchanged.
