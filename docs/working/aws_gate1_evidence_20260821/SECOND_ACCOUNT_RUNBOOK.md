# Second AWS account — owner steps, then agent steps

**Decision taken 2026-08-21: "second account".** This unblocks Gate 1 item 1, which unblocks Gate 2, which is the only route to Gates 4 and 5.

**Why a second account at all:** the guardian keeps one control table named after the account — `cas-runpod-guardian-global-v1-${AWS::AccountId}` — and the runtime hardcodes that same derivation with no stack component. One guardian per account, deliberately. A practice guardian therefore cannot live in `807562639912`. This is a safety property, not a defect, and it must not be worked around by renaming the table (that would break the account-wide single-active guarantee).

---

## READ FIRST — the account is necessary but NOT sufficient

**Found 2026-08-21, before the account was created.** One of the three required timing measurements — `observed_provider_stop_execution_milliseconds` — **cannot be taken by any deployment that is not already `LIVE`**, because `_activation_gate` raises `DEPLOYMENT_IS_INERT` before any handler reaches the provider. And `LIVE` cannot be reached without that measurement, because the template asserts a non-zero `TimingValidationEvidenceSha256`.

**The account still gets three of the four counted values** — recovery gap, worker startup, and missed ticks are all obtainable in an `INERT` preproduction stack with `RecoveryScheduleState: ENABLED`. **So this work is not wasted.** But it stops one measurement short, and closing that last one is an owner/reviewer decision.

Full analysis and the three options: **`BOOTSTRAP_CIRCULARITY.md`**. Read it before deciding how far to take the preproduction run.

---

## What the agent must NOT do

**Creating an AWS account is off-limits to the agent.** Not because of permissions — `cas-g5-operator` holds `AdministratorAccess`, and a simulation confirms `organizations:CreateOrganization` and `organizations:CreateAccount` both evaluate to **allowed**. It is off-limits by rule: agents do not create accounts, even when explicitly asked and even when technically able.

So the account creation is yours. Everything after it is mine.

---

## Owner steps — about 5 minutes

Current state, measured: **no organization exists**; `807562639912` is standalone.

1. Sign in to `807562639912`. **Organizations → Create an organization.** Free, about a minute. Choose **All features**.
2. **Add an AWS account → Create an AWS account.**
   - **Account name:** `cas-harness-preprod`
   - **Email:** must be one AWS has never seen. Gmail plus-addressing works — e.g. `wakillorenzo+casharnesspreprod@gmail.com`. It still arrives in your normal inbox.
   - Leave the IAM role name at its default, `OrganizationAccountAccessRole`.
3. Wait for the account to finish creating, then tell me the **new account ID** (12 digits).

That is all. **Do not create any access keys for the new account.**

## Why you will not need to hand over new keys

A member account created this way automatically gets the role `OrganizationAccountAccessRole`, trusted by the management account. `cas-g5-operator` already has `sts:AssumeRole` allowed, so I reach the new account by **assuming that role** with the credentials I already have.

That matters for more than convenience: **it creates no new long-lived secret.** Role sessions are short-lived and expire on their own. Given that the one existing key is already flagged as exposed and still unrotated, adding a second permanent key would be the wrong direction.

## Agent steps, once you give me the account ID

1. Assume `OrganizationAccountAccessRole` in the new account and confirm the identity.
2. Deploy the guardian there at **the same artifact version and hashes** as production — runtime ZIP `326f483639b8b48ec8718ddf166663a721710e353968cde59d601bc22858baf9`, core lock `cfbefb0df13f6b8b3636e7b0fecd2fe20dacdef4754b3505c0ff19eefe95d0f7`. **A preproduction stack at different hashes proves nothing about production.**
3. Enable the recovery schedule **in preproduction only** and let it tick long enough to collect samples.
4. Induce at least one consecutive missed-tick window, per the preregistration.
5. Exercise the exact-ID STOP transport path.
6. Run `measure_guardian_timing_evidence.py`. It will emit a document **only** if every bound holds; otherwise it refuses and LIVE stays `NO_GO`.
7. Bring the evidence back, then build the deployment binding, then present the `LIVE` change set **for your review**.

## Standing rules that do not relax

- **Production `807562639912` stays `INERT` throughout.** Nothing in this plan touches it.
- The preproduction stack must never have its `ActivationMode` softened to make measurement easier.
- Bounds are not negotiable: recovery gap ≤ **180,000 ms**, worker startup ≤ **8,000 ms**, provider STOP ≤ **8,000 ms**, at least **one** observed missed tick, STOP lead **300 s**.
- **A `NO_GO` outcome is a real possible result.** If the numbers miss, LIVE does not happen, and that is the process working rather than failing.
- Nothing here authorises a GPU. Gate 4 remains a separate, reviewed step.

## Cost

The organization is free. The preproduction guardian is Lambda, on-demand DynamoDB, one KMS key, and EventBridge — cents per day, and it can be deleted once the evidence is captured. **The GPU is not part of this**; the timing test uses no GPU at all.
