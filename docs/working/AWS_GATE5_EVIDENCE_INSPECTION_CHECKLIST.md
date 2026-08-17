# CAS Gate 5 — evidence-inspection checklist (post-run gate-closure gate)

A passing verifier run does **not** auto-close Gate 5. Gate 5 closes only after a human
inspection walks **every** Gate 5 claim back to a sealed receipt — the project's core
law: *traceability is the whole purpose; no claim without a receipt.* This checklist is
that inspection. Run it against the exported evidence from a completed run before
recording any Gate 5 decision.

Inputs to have in hand (all copied **out of CloudShell** and re-hashed on a machine that
did not produce them):
- `cas-g5-<RUN_ID>-receipts.tar.gz` + `.sha256` (from `06`)
- `teardown.receipt.json` + `teardown.sha256` (from `07 full`)
- `root-cleanup.receipt.json` + `.sha256` (from `99`)
- The run's `state.json` (final), `preflight-summary.json`, the materialize receipt, the
  preclaim receipt, and the VM-evidence export namespace (all inside the receipts archive)
- The actual dollar spend from AWS Billing / Cost Explorer for the run window

Each item below is PASS / FAIL / N-A with the backing receipt hash written next to it.
A single FAIL blocks Gate 5 closure until explained or the run is redone.

---

## A. Identity & chain of custody (the run verified the *right*, *untampered* thing)

- [ ] **A1 Package identity.** `CAS_APPROVED_PACKAGE_SHA256` recorded in `state.json` ==
  `525365c4035ba644fb39793c88cbfcdda09ddad7fa3a84317a3c6e37e9bd61e1` (sha256 of the
  1,635-B `PACKAGE.sha256`). The archive that was uploaded re-hashes to
  `a843f37e165e00a465a6dc633b7e299986a02a510ab8b0bb0dff501e33b0c528`.
- [ ] **A2 Every receipt re-hashes externally.** For each `*.json` receipt and each
  `*.tar.gz`, the offline `sha256sum` matches its committed `.sha256` sidecar. No sidecar
  is trusted that was generated inside the same VM/session as its payload without an
  independent re-hash here.
- [ ] **A3 Sealed-source capsule identity.** The materialized codebase the verifier ran
  against traces to `capsule_manifest.json` (18,311 B) with seal
  `capsule_manifest.sha256` (88 B) — i.e. the verifier checked the frozen source capsule,
  not an arbitrary tree. Wrapper that ran == `2501ff24…a34d837a` (141,548 B); the legacy
  wrapper hash `afb3f693…ddc5da9` must appear **nowhere**.
- [ ] **A4 Materialization was externally re-verified.** `materialization.status ==
  PASS_UNARMED_EXTERNAL_REHASH_AND_SCHEMA`; `provider_calls == 18`; pinned runtimes
  (git 2.52.0 / python 3.14.0 / pwsh 7.6.4) and AMI `ami-05eea18612b5be529` (owner
  `801119661308`) recorded as observed.

## B. The verifier result itself (what the 2,672 checks actually said)

- [ ] **B1 Check accounting.** The verifier output reports a total check count and a
  per-check pass/fail. Record `passed / total`. The headline "2,672 checks" is a claim
  until this receipt shows the executed count — **verify the number, don't assume it.**
- [ ] **B2 Zero silent skips.** Any check reported `skipped`/`inconclusive` is enumerated
  and each has a stated reason. A skipped check is **not** a passed check (per the
  standing "wired ≠ works ≠ validated" and "aggregate metrics never get to be the audit"
  discipline).
- [ ] **B3 Every FAIL inspected.** If any check failed, it is listed here with the claim
  it falsifies. Gate 5 cannot close over an unexplained FAIL.
- [ ] **B4 The result is bound to A1–A3.** The verifier output receipt carries the run id
  and the materialization/package hashes, so the pass count provably describes *this*
  frozen codebase and not a different tree.

## C. One-use discipline (the strict single-run rules were honored)

- [ ] **C1 Exactly one execute.** `harness_execution` reached a terminal state
  (`CONSUMED / NO RETRY`, or the acceptance-ambiguous terminal state) with the one-use
  claim consumed **at most once**. No second `execute`, no `04` rerun against a consumed
  materialization, no resubmitted VM command.
- [ ] **C2 Preclaim window respected.** The execute bound to the same session expiration
  and access-key-id SHA that `05` recorded, inside the 600 s preclaim validity. No `00`
  refresh occurred between `05` and `05b execute`.
- [ ] **C3 Continuation, never resubmission.** If any phase outlived its session, the run
  resumed only via a documented lane (`04 watch`, `05b observe/export`) — evidenced by a
  single `ssm_command_id` and a single receipt, not duplicates.

## D. Financial & footprint (spend bounded; zero residue)

- [ ] **D1 Actual spend.** Dollar cost for the run window from AWS Billing is recorded and
  is within the expected ~$5 band (one `m7i.2xlarge` Windows On-Demand host over the
  verifier window). Any large deviation is explained.
- [ ] **D2 Zero per-run footprint.** `teardown_status == FULL_TEARDOWN_COMPLETE` and
  `aws_resources_created == 0`; instance, both EBS volumes, termination schedule/group,
  watchdog DLQ, all run-tagged security groups, and the ephemeral bucket (all versions)
  are gone. `99` root-cleanup receipt confirms the IAM roles/profile deleted.
- [ ] **D3 Protected assets untouched.** Protected bucket `cas-harness-runpod-92754088`
  preserved; default VPC and subnets unmodified.

## E. Gate 5 decision record (only after A–D fully pass)

- [ ] **E1** Write a hash-chained tracker entry recording: the run id, the pass/total
  check count (B1), every receipt hash (A2), the actual spend (D1), the zero-footprint
  confirmation (D2), and the **explicit GO / NO-GO for Gate 5** with the human inspector
  named. GO requires A1–A4, B1–B4, C1–C3, D1–D3 all PASS.
- [ ] **E2** On GO: flip Gate 5 `OPEN → CLOSED` in the tracker and back up the receipts
  archive to `D:\tksCAS-archive\` with 3 sha256 confirms (standing backup discipline).
  Only then are Stage C (960-prompt corpus) and PR #210 unblocked.
- [ ] **E3** On NO-GO: record the specific failing item(s), keep Gate 5 OPEN, and either
  remediate or schedule a fresh run with a new `CAS_RUN_ID`. Never close over a gap.

---

**Why this is the gate, not a formality.** Gate 5's whole point is that the certification
Noetic Compass will one day put in front of a regulator or a court rests on this
foundation. If Gate 5 closes on an unverified receipt, every NCCS certification built on
top inherits that gap. So the inspection above is deliberately stricter than "the run
said PASS" — it re-derives every claim from a receipt, offline, before anyone writes the
word CLOSED.
