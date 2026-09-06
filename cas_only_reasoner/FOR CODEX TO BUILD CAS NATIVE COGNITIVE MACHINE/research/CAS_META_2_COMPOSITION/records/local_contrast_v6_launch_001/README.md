# Contrast campaign and launcher pure checks

51 tests passed in 1.21 seconds. The run covered
`tests/test_contrast_v6_campaign.py`, `tests/test_contrast_v6_profile.py`, and
`tests/test_launch_contrast_v6.py`, with neural/provider imports blocked,
pytest plugin autoload/cache disabled, and retained homebase scratch
`_tmp/contrast-launch-v6-001`. XML is in `tests.xml`.

The launcher and source builder were derived from the completed v5 fit-launch
implementation using explicit profile/entrypoint substitutions and replacement
of the remote campaign-dispatch/success checks. An AST comparison confirms the
shared budget, instance ownership, termination, collection, execution lock,
and core execution helpers are unchanged. The generated remote program compiles
without executing. Mocked parent tests cover phase order and stopping on errors.

The new fixed experiment uses seed 2026092601, which was not generated during
these local checks. Historical input exceptions are exact pinned development
fixtures and exclusions, not new test answers. Source is not launch-ready until
the complete included files are committed, a source archive is built and checked,
current provider/budget preflight passes, and the AWS GPU gate succeeds.

No AWS reservation, instance launch, or neural execution occurred in these tests.
