# Pinned known-example fit diagnostic

Source: `6a71e01c3689a1debe56eed842f101dfa4990556`.
Archive SHA-256: `17cdaaf25a9d07439598bf24ab9105193da1a15614fe9b41a2ba037a49849d4b`.

The cold checker passed: 508 source/input files matched Git and disk, and 316
protected baseline files matched. The preceding full pure suite passed 1,324
test functions and 178 subtests; 55 focused tests passed after the final builder
status-label correction. GPU checks have not been counted as executed here.

The registered diagnostic trains fresh CAS and generic candidates on the same
24 known training examples, eight at each depth 1, 2, and 3. It uses 200 epochs
and 600 optimizer steps per model. It records free generation and decision-role
measurements, with initial and final checkpoints. It does not load the accepted
checkpoint or use development/test examples. There is no best-checkpoint selection.

Purpose: determine whether candidate training can fit familiar nested programs
before choosing another generalization experiment. Success on these examples
is not a new held-out skill, native task correctness, memory qualification, or
completion of the cognitive-machine goal.

The intended single AWS launch reserves $7 against the shared $400 total cap,
uses the registered Blackwell g7.2xlarge fallback, and has a two-hour resource
cutoff. Source package 001 was superseded before launch by this corrected
builder-label package. Source package 002 is the launch input.

Launch, if provider preflight passes:

```powershell
C:/Python314/python.exe -B aws/launch_fit_v5.py --execute --archive records/aws_fit_v5_source_002/source.zip --sha256 17cdaaf25a9d07439598bf24ab9105193da1a15614fe9b41a2ba037a49849d4b --source-sha 6a71e01c3689a1debe56eed842f101dfa4990556 --approved-cap-usd 400.00 --subnet-id subnet-0eb3ca4bf5ca98f24 --receipt-dir records/aws_fit_v5_001
```

This source record is not evidence that the launch or training finished. Consult
the separate launch receipt for actual job, resource, execution, and cleanup state.
