# DeepSeek review packet: Claude's pinned public implementation (2026-09-27)

**Reviewer:** DeepSeek, through the owner's bus (Claude cannot reach it; the owner relays this file).
**Reviewed commit:** `238d195ea7aa369f107833563aa5f589489d9812` (recorded in `PINNED_COMMIT.txt`) on `claude/focused-mccarthy-uj45ul` (base `aa6006683d9e798c85667dc0d389a604b0e99053`,
`codex/cas-closed-loop-1-aws-validation-20260925`). The pull request for this branch targets that base.

Scope: only the files listed below plus the lineage `CHANGELOG.md` entry. No Codex-owned file in
`research/cas_closed_loop_1/` was modified. The proposed repair is a diff file, not an applied change.

## Questions for review

1. **Minimality.** Is `PROPOSED_PATCH_test_native_step_adapter_import.diff` the smallest correct repair for the
   `NameError` at `test_native_step_adapter.py:138` and `:285`? Does it alter any adapter, control or runner
   semantics? (Claude's finding: no; only the test module's import list changes.)
2. **Fidelity of the local runner.** Does `run_local_protocol.py` mirror `aws_validation/worker.py` closely enough
   that a local PASS is evidence about the same source, while stating every divergence? Known divergences: Python
   3.11 here versus the 3.12 pin; no hash-locked wheelhouse; no pinned Ubuntu git package; no S3 upload.
3. **Exact nested return.** Does `NESTED_RETURN_TRACE.json` show the property the addendum requires (two nested
   acquisition levels returning to the exact waiting frames, eleven-field identity on every live frame, `null` with
   no frame) without giving the projection any resume authority?
4. **Measurement separation.** In the witness receipts, are `I_predicted`, `I_allocated`, `I_executed`,
   `I_attempted`, reservations and event-bound measured work kept distinct, with the one counter-less record
   reported as `JOINED_PARTIAL` rather than filled in?
5. **Claim boundary.** Is every claim in `HANDOFF_REQUEST_TO_CODEX.md`, `ACCEPTANCE_GAP.md` and `README.md`
   bounded correctly (local check, not `CAS_AWS_ENGINEERING_VALIDATED`, no model, no comparative advantage)?
6. **The three CHANGES_REQUIRED items.** With the repair, the amended regression cases execute and pass locally
   (61/61). Do you accept that as evidence the items are implemented, with AWS execution still pending?

## Pinned files at the reviewed commit

| Path (under `research/cas_closed_loop_1/claude_lead_20260927/`) | Bytes | SHA-256 |
|---|---:|---|
| `.gitattributes` | 55 | `f5d5b0c512b86ad7fe5525e065f4f5152ce44c69cd3ab78904a9467c911b75ba` |
| `A2_acceptance_audit.json` | 85359 | `53e5a679d3dc21a2c8d131649a1b87261a532d22bde7bc8b2a2861bec6ac6971` |
| `A2_acceptance_audit.md` | 6862 | `1fa3de7595e7c080555a198840df2b2edfad2845353999d9bc4acd7edc65c338` |
| `A3_adapter_review.json` | 25791 | `47a50264ee06dc69eddc950bba04e469d1eafcef076eb3873f3af7a3420066ea` |
| `A3_adapter_review.md` | 6852 | `93a081d829cb39d2b71ea8c8780f9be655325111926cc3e98e204d9da7959b43` |
| `ACCEPTANCE_GAP.md` | 5311 | `db859ec66d25ef96e0aa72ad3c6b309e5a87c9cd17347e24790e1ae12adcf471` |
| `HANDOFF_REQUEST_TO_CODEX.md` | 12718 | `af4fbda7afbda7a4f024674a84c9ea828e845bbfe5590380f0c18799cc8b3215` |
| `NESTED_RETURN_TRACE.json` | 8779 | `294794112e3c8a6e40efe56ce982a415184664300501210e2ba78048e427244e` |
| `PROPOSED_PATCH_test_native_step_adapter_import.diff` | 738 | `d88c14c9381ff86260023426ce7b1f4bcd1896a401eb1f5e2f125882ce411aeb` |
| `README.md` | 1911 | `93828c841d8303c14cdf04eee9d94a2379e279da9df5e168ebd8f28eb7ebd04d` |
| `WORKERS.json` | 3564 | `85a04466b16fe0673eeb948c98651388c43e30220378b425de244a2019ca0798` |
| `probe_threaded_reentry.py` | 2656 | `594a503c0510977e9781fc4c003397ce75ab748304f476f1ffbd3df64add2da8` |
| `probe_threaded_reentry_result.txt` | 430 | `131bc928d29a9bf6ef49430d90d700feab821eb8ac9793ac1de6a7018ef5e045` |
| `run_20260927T045459Z/artifact_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/artifact_check.stdout` | 249 | `898e46f835ada295059542b9625b4ec2a58909a5ea162b280fa7c63e05ef7e21` |
| `run_20260927T045459Z/committed_artifact_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/committed_artifact_check.stdout` | 287 | `05985770249987b772737104d2a775baf98eb7c448139b264ba345f502d22d48` |
| `run_20260927T045459Z/exception.txt` | 289 | `8cff8e165fd233f1965a1c489821cd2fcc3574428b72c10d707e568755833c83` |
| `run_20260927T045459Z/focused_tests.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/focused_tests.stdout` | 4226 | `6b9b05f3cb069842729076712fa1f4ad5cbb65bd766948b123e8bd1b9fe05a5f` |
| `run_20260927T045459Z/git_branch.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/git_branch.stdout` | 31 | `46ef180f584b3238e19e400ae72d4a1fb4648e8d7ed01a331b599eca64478aa7` |
| `run_20260927T045459Z/git_head.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/git_head.stdout` | 41 | `5df8208072eface0970a5cb62a17a09f804e6ab9483df280a87dca5f56bd35ba` |
| `run_20260927T045459Z/git_status.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/git_status.stdout` | 52 | `14bfbcb3c96529458bfbaee2b102c9ca167eacfbe5c247f1b986819b725e6c1e` |
| `run_20260927T045459Z/git_version.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/git_version.stdout` | 19 | `25f3602b5caaf92437be1e76b53698e8d73f14a6c71c2e91c8d5875f923ab29f` |
| `run_20260927T045459Z/historical_object_2636bbb6.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/historical_object_2636bbb6.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/historical_object_348638c9.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/historical_object_348638c9.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/pin_pydantic.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/pin_pydantic.stdout` | 7 | `927b51cf165a5c12be3de8a0116ed5e8ae74f9020e2607ccc32060b7d6b89ae3` |
| `run_20260927T045459Z/pin_pydantic_core.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/pin_pydantic_core.stdout` | 7 | `7fbf8cb7ef3f8a8af8a9d274021400502157f56e4414582989d34077b8f87f06` |
| `run_20260927T045459Z/pin_pytest.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/pin_pytest.stdout` | 6 | `cb59c54a0c419202b393c39beebcdbef094e480bdea5c82290050c265a1f7508` |
| `run_20260927T045459Z/pytest.xml` | 12777 | `ea9cfbed7e42fb6c2dce0a543f3f02b84e09e7065d4427711eb8487c22a12bba` |
| `run_20260927T045459Z/record.json` | 9668 | `5933c7728f7a61d95dae62efcb438822324fce0bd11cbbf7b55152b092fddafc` |
| `run_20260927T045459Z/runtime_bootstrap.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/runtime_bootstrap.stdout` | 124 | `b26c5c04916f42fc0552946472a4a202ebc1167cabd9dd4c7c75ae1b9122164e` |
| `run_20260927T045459Z/runtime_commit_exists.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/runtime_commit_exists.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/source_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045459Z/source_check.stdout` | 294 | `c6ca5405058987d067e3c3d7670f6af6be426ad3b2fc8ba7e196bbf0b4802ce5` |
| `run_20260927T045944Z/artifact_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/artifact_check.stdout` | 249 | `898e46f835ada295059542b9625b4ec2a58909a5ea162b280fa7c63e05ef7e21` |
| `run_20260927T045944Z/committed_artifact_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/committed_artifact_check.stdout` | 287 | `05985770249987b772737104d2a775baf98eb7c448139b264ba345f502d22d48` |
| `run_20260927T045944Z/exception.txt` | 289 | `8cff8e165fd233f1965a1c489821cd2fcc3574428b72c10d707e568755833c83` |
| `run_20260927T045944Z/focused_tests.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/focused_tests.stdout` | 2995 | `66d46571056168a4813a782c10a60eba5f8bffc2061f6c9dd5be7810f9de5165` |
| `run_20260927T045944Z/git_branch.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/git_branch.stdout` | 31 | `46ef180f584b3238e19e400ae72d4a1fb4648e8d7ed01a331b599eca64478aa7` |
| `run_20260927T045944Z/git_head.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/git_head.stdout` | 41 | `5df8208072eface0970a5cb62a17a09f804e6ab9483df280a87dca5f56bd35ba` |
| `run_20260927T045944Z/git_status.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/git_status.stdout` | 52 | `14bfbcb3c96529458bfbaee2b102c9ca167eacfbe5c247f1b986819b725e6c1e` |
| `run_20260927T045944Z/git_version.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/git_version.stdout` | 19 | `25f3602b5caaf92437be1e76b53698e8d73f14a6c71c2e91c8d5875f923ab29f` |
| `run_20260927T045944Z/historical_object_2636bbb6.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/historical_object_2636bbb6.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/historical_object_348638c9.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/historical_object_348638c9.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/pin_pydantic.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/pin_pydantic.stdout` | 7 | `927b51cf165a5c12be3de8a0116ed5e8ae74f9020e2607ccc32060b7d6b89ae3` |
| `run_20260927T045944Z/pin_pydantic_core.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/pin_pydantic_core.stdout` | 7 | `7fbf8cb7ef3f8a8af8a9d274021400502157f56e4414582989d34077b8f87f06` |
| `run_20260927T045944Z/pin_pytest.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/pin_pytest.stdout` | 6 | `cb59c54a0c419202b393c39beebcdbef094e480bdea5c82290050c265a1f7508` |
| `run_20260927T045944Z/pytest.xml` | 11845 | `93eba334935cdff6955fac508cc0d0009279728679b91120649b5c9616617db1` |
| `run_20260927T045944Z/record.json` | 9668 | `ca2e104ad3be19357000bf3d8e310fd2a62365d1faf7c7a6cc0438f30228f85f` |
| `run_20260927T045944Z/runtime_bootstrap.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/runtime_bootstrap.stdout` | 124 | `b26c5c04916f42fc0552946472a4a202ebc1167cabd9dd4c7c75ae1b9122164e` |
| `run_20260927T045944Z/runtime_commit_exists.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/runtime_commit_exists.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/source_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T045944Z/source_check.stdout` | 294 | `c6ca5405058987d067e3c3d7670f6af6be426ad3b2fc8ba7e196bbf0b4802ce5` |
| `run_20260927T050137Z_patched_worktree/artifact_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/artifact_check.stdout` | 249 | `898e46f835ada295059542b9625b4ec2a58909a5ea162b280fa7c63e05ef7e21` |
| `run_20260927T050137Z_patched_worktree/caller_retained_digest.txt` | 65 | `ddb7c1a64d6da3c3c67bd1fbfce36c73425ce4ff9c4b0e50b7f12c27ed100db4` |
| `run_20260927T050137Z_patched_worktree/committed_artifact_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/committed_artifact_check.stdout` | 287 | `05985770249987b772737104d2a775baf98eb7c448139b264ba345f502d22d48` |
| `run_20260927T050137Z_patched_worktree/focused_tests.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/focused_tests.stdout` | 111 | `2eed8c14b11f56f15f6a2bfab80ec006fc4a20fca33e7083337b1d4d98f9a6c4` |
| `run_20260927T050137Z_patched_worktree/fresh_process_replay.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/fresh_process_replay.stdout` | 241 | `e51f2c082d5d61cbb9267d36d140ecfa7b640b8fca5b3702fabb86d46a9ba7c9` |
| `run_20260927T050137Z_patched_worktree/git_branch.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/git_branch.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/git_head.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/git_head.stdout` | 41 | `5df8208072eface0970a5cb62a17a09f804e6ab9483df280a87dca5f56bd35ba` |
| `run_20260927T050137Z_patched_worktree/git_status.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/git_status.stdout` | 110 | `e66619c75c46fe37ab027b43997fd5ddcd0d16f54f32966dc164ed679eb48d07` |
| `run_20260927T050137Z_patched_worktree/git_version.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/git_version.stdout` | 19 | `25f3602b5caaf92437be1e76b53698e8d73f14a6c71c2e91c8d5875f923ab29f` |
| `run_20260927T050137Z_patched_worktree/historical_object_2636bbb6.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/historical_object_2636bbb6.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/historical_object_348638c9.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/historical_object_348638c9.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/pin_pydantic.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/pin_pydantic.stdout` | 7 | `927b51cf165a5c12be3de8a0116ed5e8ae74f9020e2607ccc32060b7d6b89ae3` |
| `run_20260927T050137Z_patched_worktree/pin_pydantic_core.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/pin_pydantic_core.stdout` | 7 | `7fbf8cb7ef3f8a8af8a9d274021400502157f56e4414582989d34077b8f87f06` |
| `run_20260927T050137Z_patched_worktree/pin_pytest.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/pin_pytest.stdout` | 6 | `cb59c54a0c419202b393c39beebcdbef094e480bdea5c82290050c265a1f7508` |
| `run_20260927T050137Z_patched_worktree/pytest.xml` | 9495 | `6958484e3ebda0e008512ea628e21d5ec891d59a47108cca0e90783ffadf58cf` |
| `run_20260927T050137Z_patched_worktree/record.json` | 15580 | `5de1b2b48e26d68bacb96ee5f1472443d465436d9d4e99a0f99409fe59177914` |
| `run_20260927T050137Z_patched_worktree/retained_replay.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/retained_replay.stdout` | 241 | `e51f2c082d5d61cbb9267d36d140ecfa7b640b8fca5b3702fabb86d46a9ba7c9` |
| `run_20260927T050137Z_patched_worktree/runtime_bootstrap.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/runtime_bootstrap.stdout` | 124 | `b26c5c04916f42fc0552946472a4a202ebc1167cabd9dd4c7c75ae1b9122164e` |
| `run_20260927T050137Z_patched_worktree/runtime_commit_exists.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/runtime_commit_exists.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/source_check.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/source_check.stdout` | 294 | `c6ca5405058987d067e3c3d7670f6af6be426ad3b2fc8ba7e196bbf0b4802ce5` |
| `run_20260927T050137Z_patched_worktree/witness/atlas.json` | 1068385 | `034884a8675938230c46a73329df3ae2e2b5a71719ab00ce715e6e626b3c9964` |
| `run_20260927T050137Z_patched_worktree/witness/bundle.json` | 2147 | `cefb8277a070e0b7f7d41efb4003d260724b35da2336d7621740fd4dd1782d78` |
| `run_20260927T050137Z_patched_worktree/witness/events.jsonl` | 174604 | `3c1a75314b47c813fec34f6feb559b3f51095325dd48d471441d38e0a6ae75c2` |
| `run_20260927T050137Z_patched_worktree/witness/journal.json` | 1063475 | `c260e7e4bfcf93aea5032876de498847a54d58ea302b990a908583971f11b254` |
| `run_20260927T050137Z_patched_worktree/witness/result.json` | 1112 | `832cdb28854cee596d8d27672798fd7229842d320b4c2eaeedce0700040483b7` |
| `run_20260927T050137Z_patched_worktree/witness.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run_20260927T050137Z_patched_worktree/witness.stdout` | 1030 | `358bb0b94f1de0fda5015b3c897ba96a5b53c55dde3d0be9ab9f5fe6ba2bb6f5` |
| `run_local_protocol.py` | 9249 | `41250166111cf059f4f46399e229723bcae775649407431938a471801d1658e7` |

Hashes are content digests for identification. They are not signatures or attestation.
