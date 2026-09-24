# Q4-SDG-1: coordinator decisions queued for revision 3c (2026-09-24)

Answers the fresh review of revision 3b (commit `003b051a`, verdict CHANGES_REQUIRED: one MINOR Y1, notes N1-N6). The
round is queued because the laptop is low on memory (about 450 MB free). The Helm spend-gate fixes (`codex-0007` on
the agent bus) run first.

1. **Y1 (apply).** A result file is **expected** when the run's own later files prove it was written:
   - FINAL: `run_result.json` or `reload_check.json` exists;
   - checkpoint 0: any later checkpoint, `run_result.json` or `reload_check.json` exists;
   - when `job_result.json` is COMPLETE, every run it lists is expected.

   An expected file that is absent gets the same flag as a present file without a reading, so it fails closed. It may
   only make decisive labels rarer.
2. **N1 (apply).** Arm labels are **withheld**, with a named reason, whenever the calibration state is not SILENT
   (that is, FIRES or CALIBRATION_UNREADABLE). This fails closed.
3. **N2 (confirm).** Decision 2 withholds only `SHOWS_NO_INPUT_USE`. That is the builder's reading, and it is
   confirmed. Change the spec wording from "open" to "confirmed".
4. **N3 (apply).** Check run identity: the manifest's arm, seed and `pool_ids_digest` must match the folder name and
   `prep.json`, or the run fails closed.
5. **N5 (skip).** `q4_error_panel.py` stays unchanged. It is a reviewed, already-run diagnostic.
6. **Absent checkpoint-0 file** (the builder's open question): same fail-closed shape. A run that has a FINAL reading
   but no starting file is flagged.

After revision 3c: a fresh review; then the freeze; then the approved hashes in `ab_job/launch.py`, in a commit of
their own; then the data build; then training within the $5.00 ceiling.
