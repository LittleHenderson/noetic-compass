# Bounded native procedure integration

Status: **implemented and exercised for one exact-rational capability**.
The full CNCM vision remains open. Runtime 0.1.0 remains the default.

The opt-in NativeMachine / NativeCoordinator path now suspends an actual caller
with no installed procedure, selects among twelve authored six-instruction forms,
reconstructs independent engineering qualification, installs through a kernel
transition, resumes the same caller and debited budget, and checks its produced
answer before ordinary inference, comparison and commitment.

Authoritative retained demonstration: acceptance_002/receipt.json, source profile
`c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607`.
The source profile lists and hashes the implementation, controlling charter,
versioned contract/manifest, and engineering schema dependency closure.

- Acquisition for a=3,b=5,c=26 concludes with x=7 in 14 transitions.
- Conservative work allocations total 210 instructions / 35 checker calls.
  The installation panel actually executes 58 instructions / 8 checks, but its
  allocated charge is 60/10. These are policy units, not measured FLOPs or bills.
- A separate Python process semantically replays the journal, then solves
  a=-4,b=7,c=13 with x=-3/2 using the installed bytes. Selection and qualification
  entry points are patched to fail during the new call; they are not invoked.
  That call charges 6 instructions / 1 checker call.
- A new quiescent episode rolls the first installed head back to absence. Its
  next call, with acquisition disabled, returns NEEDS_CAPABILITY and no answer.
  All old artifacts and records remain. The parent process replays that full
  three-episode journal again.

To reproduce into a new directory:

```powershell
python -B tools/reproduce_native_procedure.py --output records/native_procedure_001/reproduction_new
```

The public journal recovery API requires a caller-trusted genesis and an external
complete-journal digest. It reconstructs transitions, qualifications, checks and
charges; it never imports saved registry state. Hashes and Python role boundaries
do not authenticate an external principal.

Verification retained here:

- final_native_suite_tests.xml: 467 tests plus 448 subtests passed across the
  complete homebase tests directory, including native wire/authority/recovery,
  preserved reasoning/math/conversation, apprenticeship and browser bridges.
- golden_verification.json: all 14 retained fixtures match their saved evidence;
  8 are reasoning fixtures, 5 executable math fixtures, 1 math contract-only case.
- native_recovery_tests.xml: 59 focused recovery tests, including every one of the
  15 cut points from genesis through ordinary commitment/halt.
- native_kernel_tests.xml and native_application_refusal_initial.xml: direct
  authority, stale caller, budget, retained qualification and failed-application
  checks. The latter is a passing expanded 114-test kernel/model run.
- native_v02_schema_tests.xml: 21 engineering schema checks, including all six
  stages and all seven record kinds. Runtime uses typed parsers and semantic
  replay; it does not invoke JSON Schema as an authority gate.

Review found and repaired a root-aware comparison omission and loss of rejected
proposal information during recovery. Native journals now retain normalized
occurrence order, duplicate multiplicity and malformed flags, and reproduce
rejections through the kernel. Earlier test failures remain retained.
acceptance_001 is the successful pre-publication CRLF-source demonstration;
acceptance_002 repeats it after ten new JSON contract files were normalized to
the repository's LF rule. The first source profile is historical, not a current
replay anchor.

Limits remain explicit: one branch/capability, finite authored selection, public
engineering panels, conservative counters, trusted host, first-install rollback
to absence. Low tick budgets can end with an unresolved acquisition frame;
replay preserves that failure and cannot create a fresh-budget episode from it.
There is no new neural learning, general procedure synthesis, empirical CAS-Ohm
benefit, broad reasoning result, secret evaluation custody or full-machine claim.

The user's subsequent CAS-RPA proposal is being applied as a separate typed,
read-only projection of these records. It does not change this source profile
or grant the viewer state-write authority.

