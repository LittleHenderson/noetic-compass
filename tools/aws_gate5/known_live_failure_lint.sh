#!/usr/bin/env bash
# known_live_failure_lint.sh — regression guard for the Gate 5 AWS CloudShell package.
#
# WHY THIS EXISTS
# ---------------
# The Gate 5 staging package (aws_cloudshell_unarmed_YYYYMMDD) failed LIVE three
# times in a row — 20260815, 20260816, 20260817 — each on a defect that ALL prior
# static audits had passed. Each live failure cost operator time (though $0.00 in
# AWS charges, because every attempt fail-closed before paid compute). This linter
# encodes the three now-known failure CLASSES so no future package generation can
# re-ship a defect we have already paid to discover live. It is a positive-control
# calibrated check: run it against the three dead generations and it MUST flag each;
# run it against the current GO package and it MUST pass.
#
# It is a static, read-only, offline check. It contacts nothing, spends nothing,
# and edits nothing. It is NOT a substitute for the full triple audit — it is a
# floor: "never again ship a class we already know is fatal."
#
# USAGE
#   known_live_failure_lint.sh <package_dir>
#     Lints one extracted package directory. Exit 0 = clean on all known classes;
#     exit 1 = at least one known-fatal class present (details printed).
#
# The three classes (each anchored to the real defect site that failed live):
#
#   C1  PowerShell boolean-without-parens throw  (killed 20260815)
#       windows/materialize_stage_bridge.ps1:275 shipped
#         if (Test-Path -LiteralPath $A -or Test-Path -LiteralPath $B -or ...) {
#       PowerShell binds `-or` as a parameter to Test-Path -> runtime throw on
#       EVERY invocation. Safe form parenthesizes each call:
#         if ((Test-Path ...) -or (Test-Path ...) -or (Test-Path ...)) {
#
#   C2  root-required caller that then assumes a role  (killed 20260816, live)
#       00_root_bootstrap_and_assume.sh required the caller to BE the account root
#         [[ "$CALLER_ARN" == "arn:aws:iam::${ACCOUNT_ID}:root" ]] || die ...
#       and then called `sts assume-role`. AWS categorically denies AssumeRole to
#       root ("Roles may not be assumed by root accounts"). The provisioner trust
#       policy also pinned aws:PrincipalArn to the root ARN (unassumable by anyone).
#       Fix: reject root ( != ) and pin the trust condition to a named IAM operator.
#
#   C3  role-session duration > 3600s  (killed 20260817, live)
#       CloudShell creds for a console-signed-in IAM user are session creds, so the
#       provisioner AssumeRole is ROLE CHAINING, hard-capped by AWS at 3600s. The
#       package hard-coded `--duration-seconds 21600` (and --max-session-duration
#       21600 / an assertion of MaxSessionDuration == '21600'). Any STS/role
#       duration knob above 3600 is platform-illegal from a chained CloudShell
#       caller. Fix: every such knob == 3600 (the chaining cap and IAM minimum).
#
# Scope note for C3: only the three duration KNOBS are scanned
# (--duration-seconds, --max-session-duration, MaxSessionDuration assertion).
# Unrelated large integers that are legitimately > 3600 (e.g. the 18000s host-life
# floor, 7320s SSM command timeout, 15000s verifier budget) are NOT session/role
# durations and are intentionally out of scope, so they do not false-positive.

set -uo pipefail

PKG="${1:-}"
if [[ -z "$PKG" || ! -d "$PKG" ]]; then
  echo "usage: known_live_failure_lint.sh <package_dir>" >&2
  exit 2
fi
PKG="${PKG%/}"

fail=0
name="$(basename "$PKG")"
echo "== known-live-failure lint: $name =="

# --- C1: PowerShell boolean-without-parens throw ---------------------------
# Flag a Test-Path whose argument list runs straight into a bare -or/-and with no
# closing paren terminating the call first. `Test-Path[^)]*` cannot cross a ')',
# so a properly parenthesized "(Test-Path ...) -or (Test-Path ...)" does not match.
c1_hits="$(grep -rnE 'Test-Path[^)]*[[:space:]]-(or|and)[[:space:]]' \
            "$PKG"/windows/*.ps1 2>/dev/null || true)"
if [[ -n "$c1_hits" ]]; then
  echo "  C1 FAIL  PowerShell Test-Path bound to a bare -or/-and (runtime throw):"
  sed 's/^/    /' <<<"$c1_hits"
  fail=1
else
  echo "  C1 PASS  no unparenthesized Test-Path boolean in windows/*.ps1"
fi

# --- C2: root-required caller that then assumes a role ---------------------
# The fatal pattern is a SINGLE script that BOTH (i) hard-requires the caller to be
# account root, or pins its provisioner trust policy to the root ARN, AND (ii) calls
# `sts assume-role`. Evaluated per-file: a cleanup lane (99_*) that merely ACCEPTS
# root as a recovery branch (`if [[ ...root ]]; then`) and never assumes a role is
# NOT this bug and must not be flagged. The require-root signal must be the hard
# guard form `[[ ... == ...:root ]] ||` (die on non-root), not an `if ...; then`
# branch that handles root as one accepted option.
c2_requireroot=""
c2_rootpin=""
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  grep -qE 'sts[[:space:]]+assume-role' "$f" || continue   # (ii) this file assumes a role
  # (i-a) hard require-root guard in the same file
  rr="$(grep -nE '\[\[[[:space:]]*"\$CALLER_ARN"[[:space:]]*==[[:space:]]*"arn:aws:iam::\$\{ACCOUNT_ID\}:root"[[:space:]]*\]\][[:space:]]*\|\|' "$f" 2>/dev/null || true)"
  [[ -n "$rr" ]] && c2_requireroot+="$f:"$'\n'"$(sed 's/^/  /' <<<"$rr")"$'\n'
  # (i-b) provisioner trust policy pins aws:PrincipalArn to the root ARN in the same file
  if grep -qE '\-\-arg[[:space:]]+root[[:space:]]+"arn:aws:iam::\$\{ACCOUNT_ID\}:root"' "$f" \
     && grep -qE '"aws:PrincipalArn":[[:space:]]*\$root' "$f"; then
    c2_rootpin+="$f"$'\n'
  fi
done < <(find "$PKG" -maxdepth 1 -name '*.sh' 2>/dev/null)
if [[ -n "$c2_requireroot" || -n "$c2_rootpin" ]]; then
  echo "  C2 FAIL  a script both requires/pins root AND performs sts assume-role (root cannot AssumeRole):"
  [[ -n "$c2_requireroot" ]] && { echo "    require-root gate co-located with assume-role:"; sed 's/^/      /' <<<"${c2_requireroot%$'\n'}"; }
  [[ -n "$c2_rootpin" ]]     && { echo "    trust policy pins aws:PrincipalArn to root in:"; sed 's/^/      /' <<<"${c2_rootpin%$'\n'}"; }
  fail=1
else
  echo "  C2 PASS  no root-required-then-assume-role pattern"
fi

# --- C3: role-session duration > 3600s -------------------------------------
c3_hits=""
# knob form: --duration-seconds N  /  --max-session-duration N
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  n="$(sed -E 's/.*(--duration-seconds|--max-session-duration)[[:space:]]+([0-9]+).*/\2/' <<<"$line")"
  if [[ "$n" =~ ^[0-9]+$ ]] && (( n > 3600 )); then
    c3_hits+="$line"$'\n'
  fi
done < <(grep -rnE '(--duration-seconds|--max-session-duration)[[:space:]]+[0-9]+' "$PKG" 2>/dev/null || true)
# assertion form: MaxSessionDuration ... == 'N'
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  n="$(sed -E "s/.*== '([0-9]+)'.*/\1/" <<<"$line")"
  if [[ "$n" =~ ^[0-9]+$ ]] && (( n > 3600 )); then
    c3_hits+="$line"$'\n'
  fi
done < <(grep -rnE "MaxSessionDuration.*== '[0-9]+'" "$PKG" 2>/dev/null || true)
if [[ -n "$c3_hits" ]]; then
  echo "  C3 FAIL  STS/role duration > 3600s (illegal for role-chained CloudShell creds):"
  sed 's/^/    /' <<<"${c3_hits%$'\n'}"
  fail=1
else
  echo "  C3 PASS  no STS/role duration knob above 3600s"
fi

echo
if (( fail )); then
  echo "RESULT $name: FAIL (a known live-fatal class is present) — DO NOT STAGE"
else
  echo "RESULT $name: PASS (clean on all three known live-fatal classes)"
fi
exit "$fail"
