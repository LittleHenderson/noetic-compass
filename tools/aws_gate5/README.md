# tools/aws_gate5 — Gate 5 AWS package regression guard

Static, offline, read-only regression linter for the Gate 5 AWS CloudShell staging
package (`aws_cloudshell_unarmed_YYYYMMDD`). It encodes the three failure **classes**
that each killed a package generation **live**, after every prior static audit had
passed. It exists so no future generation can re-ship a defect we already paid to
discover on a real AWS attempt.

This is a **floor, not a ceiling.** Passing it does not mean a package is stage-ready;
it means the package is clean on the three specific classes below. The full triple
audit (forensic delta / adversarial / timing) is still required, and staging still
requires the owner's fresh explicit `stage AWS now` bound to the package identity.

## The three known live-fatal classes

| Class | Killed | Defect | Fix |
|---|---|---|---|
| **C1** | 20260815 | `windows/*.ps1` binds a bare `-or`/`-and` as a parameter to `Test-Path` → PowerShell runtime throw on every invocation | parenthesize each call: `((Test-Path …) -or (Test-Path …))` |
| **C2** | 20260816 (live) | one script both hard-requires the caller to be account **root** (or pins its provisioner trust policy to the root ARN) **and** calls `sts assume-role` — which AWS categorically denies to root | reject root (`!=`), pin trust to a named IAM operator principal |
| **C3** | 20260817 (live) | an STS/role duration knob > **3600 s** (`--duration-seconds 21600`, `--max-session-duration 21600`, `MaxSessionDuration == '21600'`) — illegal for the role-chained credentials a console-signed-in IAM user carries in CloudShell (hard cap 3600 s) | every such knob == 3600 |

Each rule is anchored to the exact real defect site (see the header comment in the
script). C3 scans only the three duration **knobs**, so legitimate large integers
(the 18000 s host-life floor, 7320 s SSM timeout, 15000 s verifier budget) do not
false-positive. C2 is evaluated per-file, so the `99_*` recovery-cleanup lane that
merely *accepts* root and never assumes a role is correctly **not** flagged.

## Usage

```bash
tools/aws_gate5/known_live_failure_lint.sh <extracted_package_dir>
```

Exit `0` = clean on all three classes; exit `1` = a known-fatal class is present
(details printed); exit `2` = usage error. Run it against every new generation
**before** the triple audit — a FAIL means "don't even bother auditing, fix this
first," a PASS means "the three known killers are gone; proceed to full audit."

## Calibration (positive control)

`CALIBRATION_EVIDENCE.txt` is the committed transcript of running the linter across
all four generations from the canonical build dir. The result grid is strictly
monotone and matches the real defect history exactly:

```
           C1    C2    C3
20260815   FAIL  FAIL  FAIL
20260816   PASS  FAIL  FAIL
20260817   PASS  PASS  FAIL
20260818   PASS  PASS  PASS   <- current GO package (identity 525365c4...)
```

Regenerate the transcript any time; it contacts nothing and costs nothing. The
packages themselves are **not** in git (policy: the AWS staging package lives in the
Codex build dir and the `D:\tksCAS-archive\` backup, never committed) — the linter
and its calibration evidence are the tracked artifacts.
