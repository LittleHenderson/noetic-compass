# Attempt 4 remote preparation command transcript

Recorded at remote UTC `2026-07-22T23:15:32Z` on host `d808fa853c3b`.

All Python validation payloads were transported through standard input and run
with `-I -B`, except the two intentional negative entry tests and the disposable
ordinary-`-I` mutation probe. No command below invokes PRE capture, nonce or
protocol construction, `anchor-request`, RFC3161, Torch, CUDA, or a model.

## Initial read-only inspection

```text
ssh -p 22151 -i C:\Users\wakil\.ssh\id_ed25519 -o BatchMode=yes root@69.30.85.51 "hostname; uname -srm; python3 --version; find /workspace -mindepth 1 -maxdepth 1 ..."
```

Result:

```text
d808fa853c3b
Linux 6.8.0-65-generic x86_64
Python 3.11.10
Attempt 3 roots present; no active Jacobian or Python process was returned.
```

Fresh-path collision checks returned `ABSENT` for the new bundle, manifest,
freeze record, repository, exact dependency root, and disposable probe paths.

## Transfer and bundle verification

```text
scp -P 22151 -i C:\Users\wakil\.ssh\id_ed25519 -o BatchMode=yes jacobian_lens_canary_v1_implementation.bundle root@69.30.85.51:/workspace/cas-jlcv1-implementation-be97bc7f.bundle
scp -P 22151 -i C:\Users\wakil\.ssh\id_ed25519 -o BatchMode=yes jacobian_lens_canary_v1_implementation_manifest.json root@69.30.85.51:/workspace/cas-jlcv1-implementation-manifest-be97bc7f.json
scp -P 22151 -i C:\Users\wakil\.ssh\id_ed25519 -o BatchMode=yes ATTEMPT_04_IMPLEMENTATION_FREEZE_RECORD.json root@69.30.85.51:/workspace/cas-jlcv1-implementation-freeze-record-be97bc7f.json
sha256sum /workspace/cas-jlcv1-implementation-be97bc7f.bundle /workspace/cas-jlcv1-implementation-manifest-be97bc7f.json /workspace/cas-jlcv1-implementation-freeze-record-be97bc7f.json
wc -c /workspace/cas-jlcv1-implementation-be97bc7f.bundle /workspace/cas-jlcv1-implementation-manifest-be97bc7f.json /workspace/cas-jlcv1-implementation-freeze-record-be97bc7f.json
```

Result:

```text
3ddf60a6f24c204489a70c62465efed3ccd421baa7739bffa923d26821512b67  bundle
bbaaa973372cd95c3c99472a31664ab2add699cf1d844a5b2ab28a763dd04ffb  manifest
3fa59f57c4eee03949ecec750575a36ec69aaed3cda6fe6109a3033b2308c3b4  freeze record
36536084 bundle
5689 manifest
2130 freeze record
```

The exact reconstruction sequence was:

```text
git clone /workspace/cas-jlcv1-implementation-be97bc7f.bundle /workspace/cas-jlcv1-repo-be97bc7f
git -C /workspace/cas-jlcv1-repo-be97bc7f show-ref
git -C /workspace/cas-jlcv1-repo-be97bc7f switch --track origin/fix/jacobian-child-bytecode-guard-20260722
git -C /workspace/cas-jlcv1-repo-be97bc7f bundle verify /workspace/cas-jlcv1-implementation-be97bc7f.bundle
git -C /workspace/cas-jlcv1-repo-be97bc7f rev-parse HEAD
git -C /workspace/cas-jlcv1-repo-be97bc7f rev-parse HEAD^{tree}
git -C /workspace/cas-jlcv1-repo-be97bc7f status --porcelain=v1 --untracked-files=all
```

`git clone` warned that the bundle had no symbolic remote `HEAD` and therefore
did not initially check out files. `show-ref` returned exactly the expected
remote branch, which was then selected explicitly. Final result:

```text
The bundle records a complete history.
/workspace/cas-jlcv1-implementation-be97bc7f.bundle is okay
be97bc7f76d1e9f5e501702660678d4af3081f5e
4eb382528e8a4cee81a1c043f65bf0dcfa369ccf
fix/jacobian-child-bytecode-guard-20260722
0 dirty or untracked paths
```

## Remote implementation-manifest reconstruction

```text
/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python -I -B \
  /workspace/cas-jlcv1-repo-be97bc7f/noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/prepare_jacobian_lens_canary_v1.py \
  implementation-manifest \
  --repository-root /workspace/cas-jlcv1-repo-be97bc7f/noetic-compass-scaffold/noetic-compass \
  --code-commit be97bc7f76d1e9f5e501702660678d4af3081f5e \
  --output /workspace/cas-jlcv1-implementation-manifest-reconstructed-be97bc7f.json
cmp -s /workspace/cas-jlcv1-implementation-manifest-be97bc7f.json /workspace/cas-jlcv1-implementation-manifest-reconstructed-be97bc7f.json
```

Result: `{"byte_count":5689,"sha256":"bbaaa973...dd04ffb"}` and byte match.

## Dependency reconstruction and fail-closed line-ending finding

The initial command was:

```text
mkdir -m 0755 /workspace/cas-jlcv1-dependency-bundle-be97bc7f
git -C /workspace/cas-jlcv1-repo-be97bc7f archive HEAD:noetic-compass-scaffold/noetic-compass/live-trace-worker/research_environments/jacobian_lens_v1 | tar -xf - -C /workspace/cas-jlcv1-dependency-bundle-be97bc7f
```

The exact verifier rejected `LICENSE`. Comparison:

```text
cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  git-archive LICENSE (11,358 bytes)
3ddf9be5c28fe27dad143a5dc76eea25222ad1dd68934a047064e56ed2fa40c5  required LICENSE (11,560 bytes)
```

Recovery preserved the rejected bytes and did not weaken the verifier:

```text
mv /workspace/cas-jlcv1-dependency-bundle-be97bc7f /workspace/cas-jlcv1-dependency-bundle-rejected-git-archive-line-endings-be97bc7f
cp -a /workspace/cas-jlcv1-dependency-bundle-a8969eb7 /workspace/cas-jlcv1-dependency-bundle-be97bc7f
```

The corrected `-I -B` verification result was:

```json
{"bytecode_writes_disabled":true,"file_count":15,"file_manifest_sha256":"10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00","isolated_mode":true,"upstream_commit":"581d398613e5602a5af361e1c34d3a92ea82ba8e","uv_lock_sha256":"deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b"}
```

`diff -qr` returned no differences between the preserved Attempt 3 exact root
and the fresh Attempt 4 exact root. Both had 15 files and zero `__pycache__`.

## Linux bytecode guard

The negative checks ran each real script as its main program with `-I` and no
arguments. Both gates execute before argument parsing or ML imports:

```json
{"checks":[{"name":"wrapper","returncode":2,"stderr":"FAILED_CLOSED: Python bytecode writes must be disabled (-B)."},{"name":"bootstrap","returncode":2,"stderr":"FAILED_CLOSED: relaunch with Python bytecode writes disabled (-B)."}],"orchestrator_bytecode_disabled":true,"orchestrator_isolated":true}
```

The disposable ordinary-`-I` import used an in-memory Torch stub and actual
vendored `jlens` source. Result:

```json
{"bytecode_writes_disabled":false,"isolated_mode":true,"pyc_count":7,"pyc_files":["jlens/__pycache__/__init__.cpython-311.pyc","jlens/__pycache__/_logging.cpython-311.pyc","jlens/__pycache__/fitting.cpython-311.pyc","jlens/__pycache__/hf.cpython-311.pyc","jlens/__pycache__/hooks.cpython-311.pyc","jlens/__pycache__/lens.cpython-311.pyc","jlens/__pycache__/protocol.cpython-311.pyc"]}
```

The corrected positive payload ran with
`/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python -I -B -`.
It imported the wrapper and bootstrap without calling `main`, checked their
interpreter gates and the three frozen source hashes, installed only an
in-memory Torch stub, imported actual vendored `jlens`, `jlens.fitting`, and
`jlens.hf`, then reran the exact inventory verifier. Result:

```json
{"bytecode_writes_disabled":true,"dependency_file_count_after_import":15,"dependency_manifest_after_import":"10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00","isolated_mode":true,"official_dependency_pyc_count":0,"rejected_copy_error":"dependency bundle file set differs","source_sha256":{"bootstrap":"ae210bb41bce8dfad864f020a26c8d35298c56e0951df29862cf0a6b21e81cd6","runner":"0bd470f69df75d8254f20012f2292ea80c873d14cef50e4f75bfd82b3903f662","wrapper":"e1d5bbf228747a4c702035f11e1c3b9b5afcc55ff313b2713376f1aeaa655c95"}}
```

## Final stop boundary

```text
git status: clean, 0 dirty/untracked paths
Attempt 3 output file count: 0
Attempt 3 environment_post file count: 0
Attempt 3 runlog file count: 0
Active run_jacobian_lens_canary Python process count: 0
```

No Attempt 4 PRE, nonce, run ID, protocol, TSQ, TSR, launch config, CUDA state,
model result, producer receipt, POST capture, verdict, or claim was created.
