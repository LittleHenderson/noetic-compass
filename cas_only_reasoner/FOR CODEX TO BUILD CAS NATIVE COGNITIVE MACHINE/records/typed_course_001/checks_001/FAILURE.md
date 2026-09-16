# Preserved guarded-run failure

The first aggregate completed 247 passing tests and one failure. Its isolation
guard refused a subprocess-based fresh-import test before the process started.
No numerical or provider execution occurred. The correction reinitializes the
module under the same-process import guard; it neither skips the test nor
allows subprocesses.

The detailed XML failure body has been redacted because pytest included a local
environment mapping in its traceback. Test identity, counts and exact failure
reason remain. `report_redaction.json` binds the original report digest to the
safe publication derivative; the original FAILED receipt's report pin refers
to the original bytes. The raw trace is not retained or published.

The next runner requests short failure traces. Runtime code is unchanged by
this test/runner correction. Passing this stage still requires a fresh complete
aggregate and successful course/target artifact construction.
