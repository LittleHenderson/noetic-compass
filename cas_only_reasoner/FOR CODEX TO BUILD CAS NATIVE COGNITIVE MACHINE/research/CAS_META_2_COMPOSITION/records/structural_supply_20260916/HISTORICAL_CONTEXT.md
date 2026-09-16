# Historical audit correction and current result

Use `post_fix/REPORT.md` and `post_fix/report.json` for current working-source behavior. The original `REPORT.md`, `report.json` and test XML remain unchanged.

The first checker reconstructed the legacy merge-and-adapt algorithm instead of calling the newly added production helper. The root agent repaired the source concurrently; consequently the original report source-identity list hashes the repaired file, although its probe findings describe the reconstructed legacy path. That mismatch limits the original artifact: it is not a valid current-source probe audit.

The historical `a93d8ce4` probe blob has SHA-256 `9f9057ad75a48e5c4b9a026896c6952112fa5954aaf909ddb20f304d44f7e6b9`. Read-only Git inspection confirms that it lacks `public_probe_input` and `list_length_inputs`. Its legacy run path matches the original report's transport finding.

The revised checker calls current `public_probe_input` directly. On the same 30-case software fixture, all 30 renamed, 30 reordered and 10 rewired variants now change the public problem and use a different record ID; all ten list cases produce six slot permutations. Current combined pure validation: 25 tests passed. No model inference, checkpoint loading or provider call occurred.

These software findings do not establish model sensitivity, checkpoint restoration, causal option-length bias, or execution readiness. Source supply remains 92 exact existing topologies and 47 provisional candidates after the named conservative exclusions.
