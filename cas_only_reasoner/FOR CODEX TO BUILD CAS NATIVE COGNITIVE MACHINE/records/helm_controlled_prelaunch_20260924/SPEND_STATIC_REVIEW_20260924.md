# Spending gate: separate-reviewer public static review, 2026-09-24

**Gate verdict: CHANGES_REQUIRED. Route reader: conditionally source-conformant.** This is a source review, not a test result or launch authorization. No project code, tests, builds, models or AWS jobs were executed. No result archive, protected answers, salts, sealed material or Q3 material was read. The subreview wrote only an untracked scratch report; the coordinator incorporated it into this public amendment record.

## Source identity and scope

- Implementation: `4e292912a1efe0a85312574a69291a1af5af5427`.
- Builder verification: `6ba8ec1ce8a7d83c88cb9f9e59e52f2b1c1476a6`.
- Integration snapshot: `0618c72fa0f3e54482321a438968f44cdc481c54`.
- `study_spend.py`, `STUDY_SLOTS.json`, `PREREQUISITE_SLOTS.md` and `larger_question_t4_job/read_results.py` are byte-identical at all three refs. Source was read through the isolated audit clone with explicit refs and Git long-path support.

Line references below use integration snapshot `0618c72f`. Unless qualified otherwise, file names are under CNCM `records/helm_eval_design_20260923/study_spend/`; the route reader is under sibling `larger_question_t4_job/`.

## Required corrections

### 1. Each retry needs its own preventive spending and cleanup decision

`PREREQUISITE_SLOTS.md:73-90` expressly allows several launches under one admission, including a manual retry inside the live admission window. However, `study_spend.py:1537-1543` reserves only one next-attempt cap. Re-admission is refused while the slot is RUNNING (`1518-1521`). Earlier attempts are added only on subsequent accounting reads (`1355-1366`, `1445-1448`).

Thus a runner can preserve and list every attempt, consume part of the first cap, and launch a replacement without first reserving its additional cost. Using the document's $57.08 plan, a first attempt costing more than its $2.92 headroom plus a replacement consuming the originally reserved cap exceeds $60. The retry path also has no new enforced decision that the preceding attempt's cleanup is confirmed. These are static control-flow conclusions, not executed probes.

Require a per-attempt decision covering prior spend, confirmed cleanup, the replacement cap, the owner stop and remaining mandatory reserves; alternatively prohibit additional launches under an existing admission. This concern applies inside the live window and is additional to Q9 about expired windows.

### 2. Known finding L remains a material omission-detection gap

The source independently confirms the verifier's three shapes of missed attempt:

- `study_spend.py:1281-1285` skips a listed job ID everywhere and ignores training attempts with another source prefix.
- `study_spend.py:1295-1297` skips a watched record solely because its path matches a listed path, even when HEAD and disk contain different attempts.
- With no unlisted finding, `1461-1476` adds no corresponding cleanup stop.

`REVIEW.md:1335-1368` calls these MINOR because they require an omitted attempt. That assumes perfect manual enumeration, which the claimed fail-closed search is supposed to check. Fix source-prefix filtering and compare attempt identities/pins rather than treating a reused job ID or path as proof that every attempt is listed. The historical verifier's probe results are its claims, not independently rerun here.

## What is implemented, and its limits

The source implements exact decimal cap arithmetic, finite receipt-number checks and upward rounding (`study_spend.py:172-213`, `237-269`); pin, identity, cleanup and admission-binding checks (`568-589`, `653-680`, `829-905`, `975-1073`); full-history forward-only state with append-only committed attempts (`362-400`, `425-431`); remaining mandatory reserve, the coded $30 stop, RUNNING exclusion and fetched-upstream comparison (`505-529`, `1499-1558`); and RUNNING plus admission-record writes (`1561-1576`, `1644-1659`). These findings do not resolve the two defects above.

The gate does not reject every INVALID slot. An INVALID slot with accepted cleanup can permit onward admission while its cost is counted conservatively (`1430-1436`, `1512-1521`). The money gate explicitly does not assess technical readiness (`1556-1558`). Committed metadata is not proof of provider truth, and a carefully constructed committed admission record can pass provenance checks (`788-826`; `PREREQUISITE_SLOTS.md:160-164`).

The stated all-services basis remains conditional: declared launcher ancillary allowance; a $0.10 per-job S3/transfer/retention allowance covering only 12 months; retention after that period outside the bound (`PREREQUISITE_SLOTS.md:206-221`). These are disclosed assumptions, not measured invoices or enforced storage limits. P1b/E1 timing feasibility and implementation remain separate prerequisites (`278-305`). Policy and cost redesign are outside this subreview.

## Route reader source conformance

`larger_question_t4_job/read_results.py:88-147` compares machine identity, bundle/wheel hash lines, launch-window job start and instance identity. `188-201` requires PASS identity/status/exit evidence. `221-279` requires complete d/c/b/a checks, reviewed source/bundle, launch provenance and same-instance/time termination with no remaining volumes. Exit 0 is available only for `ROUTE_ACCEPTED` (`276-279`).

The historical missing-instance-line exemption is restricted to both template hash and instance `i-09e14d4afd0e0ebfa` (`53-58`, `141-146`). No new substantive route-reader bug was found under its stated metadata-trust assumptions. This is source conformance only: no reader execution, result revalidation, live cleanup verification or accuracy claim. A future job still needs the required machine-instance line and separate technical review.

## Exact Q6-Q9 wording

Quoted from `REVIEW.md:1247-1251`:

6. `(NOTE-D) Does a training job that launched and then failed count as "started" for the $30.00 stop?`
7. `Should a slot that was never admitted and never launched have a way to be cancelled?`
8. `Should a wrong source commit on a training receipt stop the study, or stay a rejection reason only? To decide with it: should watched slots bind the admitted bundle and source, not only the launch time (NOTE K, probe R3)?`
9. `Where does a retry go after its admission window has closed? No retry slot exists, and the definitions are frozen.`

`PREREQUISITE_SLOTS.md:339-357` adds: failed launched jobs currently count as started if their receipts are accepted; cancelling a never-launched slot currently causes UNCONFIRMED while PLANNED preserves its reserve; training-source mismatch permanently blocks cleanup confirmation, whereas watched cleanup binds by launch time only; and live-window retries are currently allowed manually. Q6-Q9 are not in the frozen `STUDY_SLOTS.json` question list. This report records them without deciding policy.

## S1 capacity-refusal accounting rule

`STUDY_SLOTS.json:25-53` fixes S1 as a DONE `pointer_capacity_refusal` at pinned receipt/provider records. `study_spend.py:908-938` requires a failed launch/execution, no launch record or instances/pending terminations, only `INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT`, deleted security group and removed roles, the AWS `InsufficientInstanceCapacity` response to `RunInstances` with zero client retries, and a matching last numbered provider record. Common identity/rate/finite elapsed checks still apply (`701-732`). The last-provider test proves last logged record, not a new provider query.

An accepted refusal counts elapsed seconds x $2.52/hour + $1.48 declared ancillary + $0.10 allowance, rounded upward (`891-904`), rather than the full $11.66 cap; the document records S1 at $1.60 (`PREREQUISITE_SLOTS.md:227`). This overrides the launcher's identity-uncertain flag. It remains explicitly `CLAUDE_PROPOSED` and load-bearing, awaiting Codex/owner acceptance (`199-204`; `STUDY_SLOTS.json:20`). It is not an independently established receipt fact in this review.

## Declared M1-M6 preconditions

These are the exact strings in `STUDY_SLOTS.json`; they are declared preconditions outside the money gate, not established completion claims.

- **M1** (`225-231`, UNCHANGED seed 20260917): "the unchanged source (Helm 2.0, 20208c92) and M1's launch folder are reviewed"; "M1 is the first training slot admitted (plan order)"; "P1b passed"; "E1 is built and reviewed".
- **M2/M3/M4** (`261-267`, `297-303`, `333-339`, REPAIRED seeds 20260917/20260918/20260919): "the repaired source is built and reviewed"; "M1 was admitted first"; "P1b passed"; "E1 is built and reviewed".
- **M5/M6** (`406-412`, `441-447`, optional UNCHANGED seeds 20260918/20260919): "fallback B was chosen by the owner"; "the unchanged source (Helm 2.0, 20208c92) is reviewed"; "P1b passed"; "E1 is built and reviewed".

Each row's note states: "listed from the plan text and the builder review of bb942461; checked by the separate technical admission, NOT by the money gate; Codex or the owner to confirm".
