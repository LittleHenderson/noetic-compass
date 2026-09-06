# Writer-to-reader process coordinator — GPU execution untested

`cas_meta3/learned_process.py` connects the data-only writer to the separate
AWS-only learned-program reuse entrypoint. It is not a paid AWS launcher.

The caller supplies the expected source identity, writer request digest and
reader request. The coordinator requires the same candidate, store and external
trust scope in both requests. It observes the writer exit, checks saved bytes,
and only then starts the fixed reader command in a new process. The reader
retains the unchanged runtime checks, CUDA requirement and T4 refusal.

The coordinator bounds the reader process to 1,200 seconds, records its actual
exit code and process ID, and binds a successful receipt to the same source,
candidate and database. Failures are not retried. Timeout kills only its own
child process. Existing baseline files and the active META2 experiment are not
modified. No model is trained by this coordinator.

This integration has not run on AWS. Local tests cover pure request binding and
early refusal without AWS job flags; they do not prove the subprocess ordering,
successful GPU execution or a real restart result. A future launcher still needs
an approved budget reservation, provider identity, source archive, independently
scheduled termination, artifact collection, frozen inspection and stored-trace
audit. Environment flags are not proof of AWS identity.

Even a successful process-pair result remains UNQUALIFIED. Retention, behavioral
rollback, learned retrieval and suspended-parent continuity are separate open
requirements. A newly started reader is not a resumed interrupted caller.

## Local verification

The full META3 suite passed 631 tests with zero failures/errors/skips in
`records/local_learned_process_002`: 51.49 pytest seconds, 52.9109694 runner
seconds. Tested source bytes and all 316 protected baseline files were unchanged.
A separate hash check confirmed all 461 live META2 package files unchanged.
These counts include seven new pure coordinator checks, not a GPU process-pair
test. The first run is retained; its sole failure was the refusal test expecting
ValueError instead of the existing NativeDemoError.

To rerun from META3, choose a new output directory:

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/local_learned_process_003
```
