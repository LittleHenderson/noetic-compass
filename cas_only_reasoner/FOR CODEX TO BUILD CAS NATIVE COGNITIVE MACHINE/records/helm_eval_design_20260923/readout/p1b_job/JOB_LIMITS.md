# P1b job: the unchanged-arm reproduction reader on one g7.2xlarge (readout plan item 8)

Label: CLAUDE_BUILT_CLAUDE_CHECKED. EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.
Status: BUILT, NOT LAUNCHED. No AWS call was made to build or test it. Only the coordinator launches.

## What it is for, in plain words

The U17 reading asks one question: did today's re-run of the unchanged Helm 2.0 code (seed 20260917) give exactly
the same learned model as the original run? A program answers that by comparing the two final models tensor by
tensor and by running both over the same 564 public course questions.

Before that comparison can be trusted, the comparison program itself must be tested on the real GPU type
("acceptance"). The acceptance run builds 11 fake variants of the original model, each with a known right answer
(for example "one number changed" must read as not reproduced). The program must give every registered answer.

So this folder launches two separate machines, one at a time:

| Mode | When | What runs | What comes back |
|---|---|---|---|
| `acceptance` | after U17 ends (GPU quota) | stage 0: the reader's own 112 tests; timing preflight; the 11 cases | `reader_acceptance_receipt.json` (READER_ACCEPTANCE_PASS or FAIL) |
| `reading` | once, only after READING_ELIGIBILITY.json is committed | timing preflight; the real comparison (Helm 2.0 final.pt vs U17 final.pt) | `reproduction_evidence.json` (evidence only, no verdict) |

The verdict is never given on the machine. It comes from `read_reproduction.py` on the laptop, after the evidence is
committed once.

## AWS job record (owner rule 2026-09-23: source, purpose, instance, limits, cleanup)

| Field | Acceptance | Reading |
|---|---|---|
| Source | reader commit `fee4ebec` (branch `claude/helm-unchanged-reader-rev-20260924`; pass `--reader-commit` for the reviewed revision), Helm 2.0 receipt `c8d5c430`, freeze `3344ae5d` | the ONE receipt commit that holds the U17 receipt, the eligibility record and the reader it binds |
| Purpose | P1b: test the reproduction reader on the admitted GPU | the U17 reproduction evidence (one shot) |
| Instance | g7.2xlarge (NVIDIA RTX PRO 4500), us-west-2, AMI `ami-0fbbd0facbc9e3cff`, 75 GiB gp3 | same |
| Rate | $2.52/h on-demand (the quote in Helm 2.0's preflight.json) + $0.005/h address + 75 GiB gp3 = $2.533219/h. The launcher re-reads the on-demand quote and refuses above $2.52. | same |
| Time | 60-minute session: in-machine timer 57 min, OS power-off 59 min, client deadline 62 min (`watch.py` terminates) | same |
| Timing preflight | refuses when the projected end is past 55 min of job time | same |
| Cost cap | worst case at the client deadline $2.6177 <= $2.64, plus the $0.10 allowance = $2.74 in the ledger | same |
| Expected | about 35-50 min, about $1.48-$2.11 | about 20-32 min, about $0.84-$1.35 |
| Retries | none: one launch attempt, one zone; `launch_record_<mode>.json` refuses a second | none; the evidence is one shot |
| Cleanup | shutdown behaviour = terminate; three kill switches on the machine plus the client watcher; the root disk is deleted with the machine; no credentials on the machine (presigned links only); `watch.py` confirms the machine is gone before it downloads | same |
| GPU quota | refuses while any GPU machine (g4dn ... g7 ... p5en) is pending, running, stopping or shutting down | same |

Spend rule before each launch (readout plan): measured spend S plus this job's cap ($2.74) must be at most $60.00.
Never between R18 and R19.

## The machine, step by step

1. IMDSv2: the machine writes its own instance id, AMI and instance type into `env.txt`, and stops if the AMI or type
   is not the pinned one.
2. The bundle (built from git objects only) is checked by its sha256, then every file against `anchors.json`.
3. Acceptance only: the reader's own tests, `python -B test_unchanged_repro.py -v`, with `CAS_META2_RUN_TEACHING_CYCLE`
   UNSET (one test expects the fail-closed stop). `Ran N tests` must equal the launcher's static count (112 at
   `fee4ebec`), with no failure or error. A failure stops the job before any GPU work.
4. The historical environment, exactly as the Helm 2.0 worker built it: the pinned `source.zip` (`c42370c4...`)
   unpacked at `/opt/cas-graph6curr/package`; `python3.12|3.11|3 -m venv` (outside the package root, so the reader's
   "no extra .py file" check holds); `pip install torch==2.11.0` from the cu128 index; the two wheels with
   `--no-deps`; `requirements-gpu.txt` (`9d0be781...`). `pip --report` adds a name/version/sha256 record of every
   installed wheel (for the R3-I environment lock). `pip freeze`, `pip inspect`, `nvidia-smi` and the relevant
   environment variables are saved.
5. Timing preflight (`p1b_machine.py preflight`, GPU): it repeats the reader's own setup, restores the Helm 2.0
   final.pt through the pinned historical loader, and times 2 warm-up plus 24 spread-out panel records (prediction
   plus historical grading). Projection: elapsed + 1 x setup + restores x restore time + panels x panel time x 1.2 +
   180 s (acceptance: 6 panels, 8 restores; reading: 2 and 2). It refuses (exit 5) past 55 minutes, and refuses
   (exit 6) when the recorded environment is not the pinned numerical environment, so no paid panel work runs on the
   wrong machine and the one-shot evidence is never written there.
6. The reader's own module, `recompute_reproduction_evidence.py --mode <mode>`, once.
7. `p1b_machine.py decide`. Acceptance: the receipt must be READER_ACCEPTANCE_PASS, list the 11 registered cases in
   order, and every case must pass `repro_common.acceptance_case_violations` (the reader's frozen table, fix 7) when
   re-derived from its observed fields; it must be made by the bundled reader (digest check). Reading: the evidence
   exists, is mode READING, was made by the bundled reader for the bound U17 final.pt. No verdict, no level summary.

## Refusals before any spend (dry run and launch alike, unless noted)

- Reading: no `--receipt-commit` (ELIGIBILITY_RECEIPT_COMMIT_REQUIRED); no READING_ELIGIBILITY.json at that commit
  (ELIGIBILITY_RECORD_REQUIRED); a record that fails the launcher's gate (ELIGIBILITY_RECORD_INVALID): not a strict
  JSON object, wrong schema/label/state or field set, not the frozen job, not the byte-identical NOT_READY admission,
  not the reader this bundle ships, pins or panel not the committed ones, decide() not the freeze's, not exactly one
  committed (non-merge) version, not committed after the freeze, evidence already committed, a bound receipt missing,
  committed after the record or with another sha256, or an acceptance receipt that is not READER_ACCEPTANCE_PASS of
  this same reader. This gate runs FIRST. The reader's own `eligibility_violations` stays the deciding check.
- Reading: U17's final.pt not named, with the same sha256 and size, by all three receipt records
  (manifest, collected_inventory, final_checkpoint), or those records are for another job (CANDIDATE_NOT_BOUND).
- Any pin mismatch: package archive and its requirements file and wheels, panel manifest `a27b3839...`, frozen study
  `60140ae0...`, as-is admission `5042681a...`, decide() equal to the freeze's, Helm 2.0 final.pt `c6c49e98...` and
  its record (blob `123f14c8`, equal to the panel manifest's pin); a file the tests read that is not bundled.
- Custody: forbidden words in any bundle name or archive member; no archive, S3, salt, sealed or HSET file.
- Machine script over 16,000 bytes (checked with 2,048-byte links), an unfilled placeholder, or bash-only syntax
  (the historical launcher's rule for this AMI).
- Worst case over the cap; a second launch of the same mode.
- Launch only: job files not committed; the source commit not on its pushed branch; the on-demand quote above $2.52;
  any GPU machine alive; no subnet; an open default security group; `--rehearsal`.

## How to run (the coordinator)

    python -B launch.py --mode acceptance --dry-run [--reader-commit SHA]          # no AWS, no network
    python -B launch.py --mode acceptance [--reader-commit SHA]                     # after U17; S + $2.74 <= $60
    python -B watch.py --mode acceptance
    python -B read_results.py --mode acceptance       # prints the acceptance receipt sha256 for the eligibility record
    # commit the receipt once; write and commit READING_ELIGIBILITY.json once (after the freeze, before evidence);
    # recommended: run read_reproduction.py WITHOUT --write at the receipt commit: the only invalid reasons left
    # should be the missing evidence
    python -B launch.py --mode reading --receipt-commit SHA --receipt-branch BRANCH [--dry-run]
    python -B watch.py --mode reading
    python -B read_results.py --mode reading          # prints the evidence sha256; commit the evidence ONCE
    # then, on the laptop: read_reproduction.py --receipt-commit ... --receipt-branch ... (the verdict)

`python -B launch.py --mode reading --dry-run --rehearsal` builds the reading bundle's shape with public stand-ins
(the Helm 2.0 final.pt as the candidate). It can never launch.

## Checks run (2026-09-24, laptop, no AWS, no network, no torch)

`python -B -m pytest test_p1b_job.py -q -p no:cacheprovider`: 12 passed in 16.77 s (the first run had 11 passed and
1 failed; the failure was a shared dictionary in the test's own fixture, fixed in the test only). They cover:
- the acceptance dry run builds the bundle (29 files, 8.3 MB compressed), custody passes, every file matches
  anchors.json, the machine's anchor check passes on the real bundle and catches a change, and the machine script
  carries the IMDSv2 lines, the timers, the historical install and `--expected-tests 112`;
- the reading rehearsal builds the reading bundle (candidate = Helm 2.0 final.pt, stand-in);
- the reading mode is refused without a receipt commit and without the eligibility record, dry run and launch alike,
  before anything is built; usage errors are refused;
- the eligibility contract (15 named defects plus a duplicate-key record), the launcher's pins against the reader's own constants, the candidate
  binding on the real Helm 2.0 records, the timing projection, the cost cap and session order, the machine decide
  step against the reader's frozen table, the laptop result reader, and the custody filter.

Not run anywhere yet: every part that imports torch (`p1b_machine.py preflight`, the reader's recompute module), and
the machine script itself. Their first run is the paid acceptance launch.

## What this does not show

- Nothing about whether U17 reproduces. The acceptance run tests the reader on synthetic variants of one public
  checkpoint.
- The stage-0 tests run on a machine with no git history, so the reader's git-backed tests are SKIPPED there (they
  count as run; skips are recorded, not deciding). The reader builder's laptop run is the only run of those.
- The Helm 2.0 run's Python, cuDNN and driver versions are not in its public records (its result.json records torch,
  CUDA and the GPU only). This job records them for P1b; it cannot prove they equal the historical ones.

## Open questions (for Codex's one check)

1. Stage-0 skips on the machine (no git history): record-and-continue, or must stage 0 carry the git history?
2. The preflight repeats the reader's setup once (about 3-4 min, about $0.15). Accepted?
3. The preflight refuses both modes in a non-pinned environment, so no FAIL acceptance receipt is written there.
   Accepted, or must the acceptance still write its FAIL receipt?
4. The 55-minute projection with a 1.2 safety factor refuses the acceptance if a prediction plus grading takes more
   than about 0.49 s (with 15 minutes elapsed and a 200-second setup). If it refuses, the measured times are in `preflight.json`; splitting
   the acceptance across two sessions would need a design change.
5. The reading needs ONE commit holding the U17 receipt, the eligibility record and the reader: in practice a merge.
   The eligibility record must stay exactly one non-merge commit, and the merge must not change it.
6. R3-I: the historical Python, cuDNN and driver values cannot be established from public records. Per R3-I they stay
   an explicit blocker for the environment lock, not something this job can settle.
7. Plan money fix 1 (acceptance and reading in one session) is not built; it needs Codex's ruling on the hash order.
