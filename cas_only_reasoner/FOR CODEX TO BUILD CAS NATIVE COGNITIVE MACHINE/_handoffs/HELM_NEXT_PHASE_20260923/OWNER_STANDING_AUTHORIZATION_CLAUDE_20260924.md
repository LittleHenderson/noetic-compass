# Owner confirmation (2026-09-24, verbatim): the standing approval extends to Claude

**The question Claude asked in chat, exactly:**

> does your standing approval to Codex also cover me, as the job runner, within the $60 ceiling and only once each
> technical check passes?

**The owner's answer, exactly:**

> YES IT ABSOLUTELY DOES EXTEND TO THE SAME APPROVAL

**The standing approval it extends** (quoted in Codex's record `records/helm_controlled_prelaunch_20260924/OWNER_STANDING_AUTHORIZATION_20260924.md`,
branch `codex/helm-controlled-prelaunch-20260924`, commit `bc46b36e`):

> DO YOU NEED MY APPROVAL FOR ANYTHING? IF SO I HEREBY GRANT YOU IN ADVANCE ALL FUTURE AND CURRENT APPROVAL FOR THIS
> PROJECT

Recorded by the Claude coordinator. This is not an owner signature.

## How Claude applies it: two separate states

| State | Value |
|---|---|
| `owner_authorization` | `STANDING_PROJECT_AUTHORIZATION` (Codex and Claude) |
| `execution_admission` | `NOT_READY` until every technical prerequisite passes |
| `launch_enabled` (main comparison) | `false` until then |

- **Authority is not readiness.** A job runs only when its own bounded admission passes its technical checks. No
  approval word is inserted to get past a check.
- **The limits stay.** Option C; the **$60.00 actual-spend ceiling** for the comparison; the per-job check (measured
  spend so far + $15.00 <= $60.00); the stop if spend passes $30 before the third training job; one machine at a
  time; no automatic retries; protected-test custody; policies fixed before results; Q4 separate.
- **The budget does not grow.** The standing approval adds no dollars and makes no missing evidence exist.
- **Prerequisite jobs** (for example the larger-question T4 checks, the HSET-2 build, the rescorer reading) run under
  this authority once their own admission and review pass. Each is recorded: source, purpose, instance, limits,
  results and cleanup.
