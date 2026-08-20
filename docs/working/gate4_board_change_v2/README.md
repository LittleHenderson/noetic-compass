# Board-change v2 successor

**Current status: `DESIGN_ONLY / INERT / NOT AUTHORIZED / NOT RUN / NOT VALIDATED`.**

This directory is a new successor to `docs/working/gate4_next_board/`. It does not edit,
replace, or reinterpret v1. The v1 pilot remains immutable historical evidence. This
package hardens the known implementation defects before any new model call:

1. production authorization is structurally unavailable: callers cannot inject a verifier
   or clock, and the offline Git/remote lock is explicitly `UNVERIFIED_OFFLINE`;
2. a future prompt plan must contain exactly **72 neutral + 20 shifting fresh, unique
   seed prompts** before the protocol can freeze;
3. every provider attempt, retry, response rejection, and repair round has distinct,
   hash-chained evidence; and
4. Claim 2 fixes the registered learner, seed `0`, and 1,000 trials and mechanically refits
   inside every permutation;
5. the exact plan, lock, run, authority receipt, phase event, budget, raw response content,
   and (for labels) corpus seal are welded into accepted evidence; and
6. raw generation requests must exactly equal the frozen seed/follow-up/accepted-response
   history, model, and parameters; provider origins and paths are allowlisted exactly; and
7. low-level imports are permanently `AUDIT_ONLY_UNTRUSTED_NEVER_ACCEPTABLE` and live in a
   different hash chain from production attempts.

There is deliberately no provider SDK, HTTP client, API key loader, or dispatch command in
this directory. The local CLI is an offline control plane. A separately reviewed adapter
is still required before a real run. The bundled CLI has no external signature verifier;
therefore `authorize-full` intentionally fails with
`PRODUCTION_AUTHORITY_INTEGRATION_ABSENT`.

## What exists

- `PREREG_BOARD_CHANGE_V2.md` — successor protocol and claim ceiling.
- `core.py` — prompt-plan validation, fail-closed production state plus a structurally
  non-production mock state, frozen run bundle, split audit/mock attempt ledgers, raw-response
  extraction, corpus sealing, and corrected Claim-2 permutation.
- `board_change_v2.py` — offline CLI only.
- `schemas/` — exact machine-readable evidence contracts.
- `tests/` — mocked, temporary-directory tests. They make no network calls.
- `V1_HISTORICAL_EVIDENCE.md` — the preserved v1 pilot boundary and artifact identities.
- `PROMPT_PLAN_AUTHORING_CONTRACT.md` — instructions for an actually blind prompt author.

## What does not exist yet

- `prompt_plan_v2.json` with the 92 claim-bearing prompts;
- a `protocol_lock_v2.json` made from a committed and remotely observed exact source tree;
- a full-run authorization tied to those two exact hashes;
- an audited external signature/key-registry verifier and trusted production clock;
- a provider adapter and any real request/response evidence;
- a sealed-corpus-derived label manifest, completed labels, Gate 0 report, or scientific result.

Because these are absent, this package cannot authorize or make a provider call.

## Acceptance boundary

For a future run directory, the reserved evidence locations are fixed:

- `prompt_plan.frozen.json`, `protocol_lock.frozen.json`, and `frozen_bundle.json`;
- `provider_attempts.jsonl` and `artifacts/`;
- `provider_attempts.jsonl.audit_imports.jsonl` for untrusted historical imports only;
- `corpus.sealed.jsonl` and `corpus_seal.json`.

`AttemptLedger.append()` is intentionally not an accepted append. It writes only the
untrusted import journal. In this package `record_authorized_attempt()` admits only
`MOCK_ONLY_NEVER_PRODUCTION` evidence. Cost is derived from token usage and a frozen mock
rate table and is explicitly not a provider billing receipt. Any real path remains blocked
until authenticated authority, Git/remote, transport, usage, and pricing verifiers exist.

## State path

```text
DRAFT
  -> PROTOCOL_FROZEN
  -> [FULL_RUN_AUTHORIZED is unavailable in this package]

MOCK_TEST_ONLY:
PROTOCOL_FROZEN
  -> MOCK_RUN_AUTHORIZED
  -> MOCK_GENERATING
  -> MOCK_GENERATION_COMPLETE
  -> MOCK_CORPUS_SEALED
  -> MOCK_LABELING
```

`HALTED` is terminal from every nonterminal phase. Label completion, Gate 0, and analysis
completion edges are absent until evidence-completing functions exist. Mock phases and
artifacts can never satisfy production acceptance.

## Safe offline checks

From this directory:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_ADDOPTS='-p no:cacheprovider'
C:\Python314\python.exe -B -m pytest tests -q
C:\Python314\python.exe -B board_change_v2.py --help
```

After a blind author supplies the plan, the first permitted command is only validation:

```powershell
C:\Python314\python.exe -B board_change_v2.py validate-plan `
  --plan prompt_plan_v2.json `
  --forbidden-seed-hashes v1_seed_fingerprints.json
```

That command is offline and creates no run authorization.

## Claim boundary

This remains an **output-space lens study**. Even a future `HOLDS` result would not prove
hidden-state analysis, pre-speech interception, architecture discovery, semantic circuits,
ablation, causal steering, prompt-injection detection, hallucination detection, or
reasoning-break detection.

The current Claim-2 computation output is marked
`NOT_CLAIM_ELIGIBLE_UNTIL_SEALED_LABEL_GATE0_BINDING`; it is an algorithm check, not a
scientific result.
