# POST-GATE-0 BACKLOG — nonblocking minors (owner disposition, 2026-08-31)

**Gate 0 is FROZEN PERMANENTLY at anchor `83f57d6f724505f2c2c68593b2625c36c3e07a4d`
(owner status: VERIFIED_PASS, independent cross-model software audit in a fresh
environment: 246/246 tests, 26/26 scenarios, 8/8 injections, 22/22 semantic
mutations, deterministic replay, 9/9 independently constructed target probes;
0 critical and 0 major findings surviving).**

The two surviving MINOR findings are recorded here under the owner's explicit
disposition. They:
- do NOT alter the frozen Gate-0 claim;
- do NOT delay Gate 1A;
- do NOT justify new controller architecture;
- may be fixed later on a MAINTENANCE branch, which must not quietly redefine what
  passed — the immutable Gate-0 qualification anchor remains `83f57d6f…`.

## F-04 — Deferred causes need a clearer terminal disposition
Owner wording, recorded verbatim: "Deferred causes need a clearer terminal
disposition." (RC-0.4E added typed `CAUSE_DROPPED` dispositions for dropped causes;
DEFERRED causes — `CAUSE_DEFERRED` events — still terminate the run without a
per-cause ledger row.) Nonblocking. Maintenance-branch candidate.

## F-05 — Three existing tripwires need direct tests
Owner wording, recorded verbatim: "Three existing tripwires need direct tests."
Nonblocking. Maintenance-branch candidate.

## Standing law
No RC-0.4F/G/H patch carousel: the deterministic controller is the frozen reference
machine. Further Gate-0-area work happens only as explicitly-labeled maintenance,
anchored comparisons stay against `83f57d6f…`, and no maintenance commit may be
presented as a new Gate-0 qualification.
