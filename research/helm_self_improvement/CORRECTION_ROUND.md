# Correction record — 2026-09-27

Owner request: first CAS + SI correction round. Base SI export was
`52d625ac62f06fa947c0ff5c141fcbf0027456bc`. Only the SI namespace changes here;
all original public CAS/runtime bytes are retained. This record is source work,
not an executed or accepted episode.

| Finding | Source change | Evidence/status |
|---|---|---|
| D1-B2 foreign parent | External trusted-host policy; exact parent/source/harness checks at build/execute/reload | Implemented; behavioral recheck pending |
| D1-B3 constructor bypass | Constructor validation repeated at every host boundary; permitted provenance only | Implemented; behavioral recheck pending |
| Fabricated observation | Host-recorded run/input/journal/sequence; build ledger order | Implemented; behavioral recheck pending |
| Baseline modes | Disabled/shadow execute actual admitted baseline; mode and measured overhead retained | Implemented; behavioral recheck pending |
| Persisted summary | Finalized bundle/replay/timing before summary write; host anchored reload | Implemented; behavioral recheck pending |
| Actual modification | H1 Boolean configuration and H2 existing-component composition; rejected NO_CHANGE retained | Implemented; actual witness/reload NOT_RUN |
| Export provenance | Exact 152 public files checked against allowlisted original Git blobs | Source inspection only; no upstream bootstrap |
| D1-B1 TerminalStatus | Claude owns accepted CAS lease | Open here; no CAS edits |
| Threaded call-entry/refusal and atlas addresses | Claude owns accepted CAS lease | Corrected packet and AWS checks pending |
| CAS 52/61 mismatch | Claude XML has 61 cases; DeepSeek reports 52 after patch | Open; missing DeepSeek exact run/case evidence |

DeepSeek identified the SI parent/constructor/baseline/evidence/persistence issues.
Codex authored this source correction. Claude and DeepSeek independently identified
the import correction. Codex source inspection is not an independent behavioral
review. No paid reviewer call, new child agent, cloud job or training retry was
made for this packet. Protected data and credentials were not read. Historical
failures and receipts remain preserved.

The accessible Claude route is PR #245. Package commit
`880957f5a38c08d36a92c0cdbe500287dd87719a` was acknowledged in comment
`5853300431`; accepted CAS lease is `CAS-CORRECTION-20260927-01`.
Claude session `session_011hJxopymaeoPQ67KvchtwW` reports model
`claude-fable-5-1` and zero active children. Prior A2/A3 internal IDs are withheld
and remain null. DeepSeek's reported completed D1 worker is
`a3c4ca69-29d0-4c89-82c5-536eeecd1299`; its current remote count is not independently
queried. Codex created no children. No recursive teams or duplicate operators.

Remaining blocker: the corrected joint CAS/SI package lacks a new exact AWS
execution admission under reconciled current resources. The owner note supplies
no new cap; this source record does not authorize the stale $1 proposal or reuse
the active HELM worker. Next eligible action is the focused source review and
joint-package assembly after Claude's source return. Next behavioral acceptance
command is recorded verbatim in README.md and SOURCE_INSPECTION.json.
