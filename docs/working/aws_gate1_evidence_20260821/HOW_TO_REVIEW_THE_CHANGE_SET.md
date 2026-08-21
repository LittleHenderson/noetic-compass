# How to review the LIVE change set — plain English, step by step

**The change set now exists.** It is named **`live-activation-for-owner-review`**, on stack **`cas-harness-preprod-guardian`** in account **`063693212118`** (`us-west-2`). It is a **preview only**. Creating it changed nothing; it will keep changing nothing until someone presses Execute.

---

## What a change set is

A change set is AWS's "preview of a settings change." It computes exactly which resources would change if the new parameters were applied, and holds that list for you to read. Two buttons exist at the end: **Execute** (apply it) and **Delete** (throw the preview away). Reading it is completely safe.

## Where to look

1. Sign in to the console as `cas-g5-operator`, then switch role into the preprod account — or sign into `063693212118` directly via Organizations.
2. Go to **CloudFormation → Stacks → `cas-harness-preprod-guardian` → Change sets tab → `live-activation-for-owner-review`**.
3. Two tabs matter: **Changes** (the 23 resources that would be modified) and **Parameters** (the new values).

## What the preview says, summarised

**23 modifications. Zero deletions. Zero forced replacements.** Every change is the same kind: the nine Lambdas, their roles, the state machine, and the recovery schedule pick up the new environment bindings. Nothing is destroyed and no data is touched.

## The checklist — compare what you see against these exact values

This is the whole review: the console's Parameters tab must show precisely these, nothing else changed.

| Parameter | Must be |
|---|---|
| `ActivationMode` | `LIVE` |
| `CoreLockSha256` | `cfbefb0df13f6b8b3636e7b0fecd2fe20dacdef4754b3505c0ff19eefe95d0f7` |
| `TimingValidationEvidenceSha256` | `59462f7d469c53ae377052b953582d43663a3288977e20ff7c7c85149d962126` |
| `DeploymentBindingSha256` | `e40f34010e61098839cde9ea420233b7d50e65a7ece31cba968d326101e157f1` (shows as `****`, NoEcho) |
| `DeploymentBindingObjectSha256` | `e40f3401…` (same value) |
| `DeploymentBindingObjectKey` | `runpod-guardian/activation/PREPROD/deployment-binding.json` |
| `DeploymentBindingObjectVersion` | `13XIqvsTspxqaqYWG3.sTMxC2XjLM7dx` |
| `TimingEvidenceObjectKey` | `runpod-guardian/activation/PREPROD/timing-evidence.json` |
| `TimingEvidenceObjectVersion` | `OsjCHqefUNq6hbeGT2.TurX8ib09vhkw` |
| `ProviderAccountId` | `user_38E4xHk5H6yjrzEh4KUse08Ia8U` (an identifier, **not** a credential) |
| `RecoveryEnabled` / `RecoveryScheduleState` | `TRUE` / `ENABLED` (unchanged) |
| `LambdaArtifactVersion` / `RuntimeZipSha256` | unchanged — **same artifact version**, exactly as RUNBOOK §7 requires |

RUNBOOK §7's rule is: *same artifact version, only the listed binding changes.* If anything outside this table shows as changing, the review fails — tell me and I delete the change set.

## Three things to know before deciding

1. **Execution would currently FAIL anyway.** LIVE reserves 8 Lambda slots, and this new account's limit is still 10 (quota request `9b482ab5…` is `CASE_OPENED`). CloudFormation would refuse mid-update. So there is no rush — the review can be done calmly now, execution waits for the quota either way.
2. **Even executed, the guardian cannot reach RunPod.** The provider secret is a marked refusal payload, not a credential. At first activation attempt the runtime fails closed with `PROVIDER_SECRET_FORMAT_INVALID`. Going LIVE here exercises the activation machinery only.
3. **The STOP number inside the evidence is a declared substitute.** `908 ms` is the transport leg, not a guardian STOP. The declaration is committed by hash into the document's manifest, first key, impossible to miss — and it records that emission was your explicit instruction.

## Your three possible verdicts

- **"review passed"** — the values match, the change set stands as reviewed. Execution stays a separate, later, explicit step (RUNBOOK §7 demands action-time confirmation immediately before executing).
- **"review failed: <what>"** — I delete the change set and fix what you name.
- **Say nothing** — the change set just sits there, inert. It expires with the stack, never self-executes.

## Standing

Production is untouched and `INERT`. No GPU exists. The A40/Pythia experiment remains `NOT RUN` — neither passed nor failed.
