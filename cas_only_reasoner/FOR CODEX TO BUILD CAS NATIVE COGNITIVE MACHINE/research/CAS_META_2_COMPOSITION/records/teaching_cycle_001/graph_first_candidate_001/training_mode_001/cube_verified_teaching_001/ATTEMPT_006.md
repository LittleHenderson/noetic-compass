# Attempt 006 of the checked-component pilot — the infrastructure held, the data could not reach the encoder

Written 2026-09-10. Every number is copied from a file on disk.

This attempt produced **no learning measurement**. It is the first attempt whose
launch, delivery and cleanup all behaved correctly, and the first to find a defect
in the *experiment's own data* rather than in the plumbing.

## What was authorised

`OWNER_AUTHORIZATION_CANDIDATE_PILOT_004.json`, sha256
`c0568c1fe08c4be1de5571b1e790a3a268765af1acab2ceb62c02576241aae7b`, recording the
owner's instruction verbatim:

> come on bro I believe in you 🙏🏿 ...you can do this...you got got this man ...GO!!!

## What was bound

| item | value |
| --- | --- |
| job | `cas-meta2-graph6cand-20260910171323-5c8b9efd` |
| request | `candidate_request_004.json`, sha256 `79e96e9fffed9697969fa679ab5adc3d9f3d7e3081bc7951cbc93fe0526bd3ac` |
| authority | `candidate_authority_004.json`, sha256 `45402aba591aa2b9d348e63be43cdb0eb28f79f62b151578c0a2cd5017f7bd18` |
| source commit | `889c37e00fd8cd75aace74b5161f0186ab5a6a99` |
| package | `candidate_package_005/`, archive sha256 `5c8b9efd3c7fc2dd54bb8d739dd38f78a1a703175a08843a03e70074c374f9b9`, manifest sha256 `858352a7e209b02e9eeac9c59d43e3e98cd0785a41f6b5c1df6e83900104d2d4` |
| reservation | `$7.00`, ledger revision 55, `RESERVED_NO_AUTOMATIC_REFUND` |

## What happened

- 17:26:03–17:26:22 UTC — reservation recorded, package uploaded, instance
  `i-0fd38cdd941e7ffc7` (g7.2xlarge) launched.
- 17:29:57 UTC — the worker reported a failure. This time the venv was created,
  `torch==2.11.0` installed from the CUDA index, the frozen wheels and the
  requirements installed, and the training body ran under the venv python. It
  then died inside the encoder builder:

  ```
  File ".../_inner_runner.py", line 32, in <module>
      encoder = build_encoder(torch, publics, d_model=64, ...
  File ".../real_framework.py", line 142, in build_encoder
      node_id = vocabulary.index(_word_token("node"))
  ValueError: tuple.index(x): x not in tuple
  ```

- Launcher verdict: `AWS_CANDIDATE_FAILED`; stages `execution: FAILED`,
  `collection: VERIFIED`, `cleanup: COMPLETE`; elapsed 563.7 s. Cleanup:
  instance `CONFIRMED_TERMINATED`, security group deleted, roles removed,
  `schedule_removed: NOT_APPLICABLE`, bucket deleted because collection was
  verified, and **no cleanup failures**. The collected result is
  `curriculum_result.json` (sha256 `e4bfcd6fa1942c807b256d61853cc03c969ff8a423f17c150c2a0a703eddb0bd`)
  with the preserved `results/failure.json` beside it.

Actual EC2 time was roughly four minutes, about `$0.17` at the `$2.52/h` ceiling.
The `$7.00` is a ledger reservation, not an invoice.

## Why it failed

The training adapter rendered each cube graph as prose:

```
Facts:
Bicycle contains Wheel
...
```

The frozen problem encoder is specified over the graph's own presentation. It
fits its vocabulary on the very publics it is given and then requires a `node`
token, a `rel` token, a newline token and at least one structural segment per
problem; a problem without them fails closed
(`PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED`). Prose gives it none of the three
tokens, so **no cube lesson could ever have reached the encoder**. The failure
was in the pilot's own serialization, not in the encoder and not in the cube
data: `cube_node.containment_graph` already returns a `graph.Graph` whose
`render()` is documented as the structure-only teaching presentation, and the
adapter had bypassed it.

## The fix

`verified_training.public_problem` now builds the learner-visible problem from
`containment_graph(bundle, view_id).render()` for the taught records and the
probe records alike, keeping the same request line and the same trailing choice
line.

Unchanged: the nodes, the containment branches, the question, the three unmarked
observations, the teacher answer, the scoring, the frozen encoder, the option
contract, and the declared visibility profile (which makes the fact refs and the
direct-branch inventory public at the unassisted level these records declare).
Changed: the syntax of the facts block, from prose to the lines the encoder
parses. No answer, target, witness or option marking enters the prompt.

Verified before any further spend:

- a new test fits the frozen tokenizer on all 52 publics (8 taught plus the
  44-question probe) and requires the three markers, a structural segment per
  problem and three encoded slots — the exact failure cannot return silently;
- the verified-teaching check was re-run. The previous report is preserved as
  `check_report_rev4.json`, because its record ids belong to the superseded
  presentation, and `check_report.json` is the new reading: still
  `TEACHING_DATA_READY_NEURAL_UNTESTED`, still `actual_optimizer_updates: 0`,
  still `stub_training_step_calls: 64`;
- 171 tests pass across the cube, candidate and launcher suites.

## State afterwards

- No learning result exists for this pilot. The campaign's only measured
  graph-learning status remains `VARIED_CURRICULUM_NOT_ESTABLISHED`.
- Ledger revision 55: `$298.00` reserved, `$102.00` free against the `$400.00` cap.
- `candidate_package_006/` (archive sha256
  `e33a64975fddb794706f3995688ebda7df86a7f821091b7fdbedecdeab3134fc`, manifest
  sha256 `becda10cebca22076be9556d87eafdcd6ace638b3a9a53c82deb8830c463c165`,
  499,899 bytes, 46 members) was built from commit
  `b2ff5a4bbdd3` after the fix, and the rehearsal passes 13 tests against it,
  including that the packaged worker is byte-for-byte the worker exercised.
- A further paid attempt requires a new owner instruction. Nothing is reserved,
  queued or scheduled, and no instance or bucket remains from any attempt.
