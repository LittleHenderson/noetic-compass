# Gate 3 — the freeze record — RE-PINNED at commit `8595f6ad`

> **RE-PINNED 2026-08-21 after the owner-approved model re-pin.** The previous pin, commit `33a81f52c0bc3b2b6740e9652292370d4541ab71`, is **superseded and retained here** — it froze a model artifact that could never load (see `MODEL_REPIN_RECORD_20260821.md`). A freeze that pins an unloadable artifact is not a valid freeze, so Gate 3 was re-run rather than carried forward. Two hashes below moved with it; everything else is re-verified, not assumed.

**Date: 2026-08-21. Everything on this page was verified at this exact commit, not carried forward.**

Gate 3 asks: *pin the exact commit, image, hardware, and receipts; re-run the full test suites — runtime, canary, guardian, and hostile inputs.* This page is that pin.

---

## The commit

| | |
|---|---|
| Repository | `cas_interpretability_successor_20260820`, branch `codex/cas-interpretability-successor-v2` |
| **Pinned HEAD** | **`8595f6adfca00a7c9f724aafad00ffabd32b5109`** (superseded: `33a81f52c0bc3b2b6740e9652292370d4541ab71`) |
| Working tree | clean except the preserved untracked `infra/runpod_precreate_guardian_aws/` |
| Line-ending armour | `.gitattributes` pins `eol=lf` on every hash-locked tree (the freeze survives a clone) |

**The canary freeze is CURRENT at this HEAD**: the live-computed source-file manifest equals the preregistration's pin, `BD4CCE31A351D05AE58F32C4F033B03B6C2F5CFF68AE234030E26CB5B4BB2A31` (superseded: `6EC46F9A42A52B6EE13F65EEEE81AB73889BD56B247F828393C84794A4227CCF`), re-computed live at this commit rather than assumed. The dependency lock `9E990C06B907FE117E67D6BB4CCD8B5AF09FFD9E8B1D98D893A727102C33CB9A` re-verified equal to the preregistration, and `execution_authority` re-verified still `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`.

## The image

| | |
|---|---|
| OCI digest | `sha256:4d1721e62b56d345c83b4fd6090664be6daf9312caab5b2e76f23d8231941851` |
| Image name | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |

## The hardware

| | |
|---|---|
| Device | `NVIDIA A40`, capability `[8, 6]`, `cuda:0` |
| Runtime | Python `3.12.3`, torch `2.8.0+cu128`, CUDA `12.8` |
| Dependency lock | `9E990C06B907FE117E67D6BB4CCD8B5AF09FFD9E8B1D98D893A727102C33CB9A` |
| Model | `EleutherAI/pythia-160m` @ `50f5173d932e8e61f858120bcb800b97af589f46`, tree manifest **`BB65650EB00AAA36900BBBB57B2C96EF4D34AA395F124E68C801C483D4BB5CDE`** (superseded: `6373A5C8…`), 5 files each hashed. **`model.safetensors` is the owner-approved fp16 re-serialization `D5861D3237C5F8E952B4EBF05179F3BC50D479186FBE96845D22660D96C50D97`, `324662840` B** — the original `29D2E457…` could never pass the byte-exact weight verifier under the pinned `transformers 5.8.1`. `config.json` and all three tokenizer files are byte-identical to the original pin. |
| Determinism | `PYTHONHASHSEED=1729`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, memory floors pinned |

## The receipts

Schemas pinned in the preregistration; **instances are Gate 4 outputs and cannot exist yet**:

- `cas_runpod_provider_launch_receipt.v2` (required)
- `cas_runpod_create_authorization.v1`
- `cas_runpod_precreate_guardian_arm.v1` (required)

## The guardian artifacts (this session's additions, all hash-bound)

| artifact | SHA-256 |
|---|---|
| runtime ZIP | `326f483639b8b48ec8718ddf166663a721710e353968cde59d601bc22858baf9` |
| `core-lock.json` | `cfbefb0df13f6b8b3636e7b0fecd2fe20dacdef4754b3505c0ff19eefe95d0f7` |
| state machine | `70dc66f4528ce2fe9664e6bb93dc2d9cfbcec1ac7c1712b5298cd60210033db4` |
| timing evidence | `59462f7d469c53ae377052b953582d43663a3288977e20ff7c7c85149d962126` |
| source manifest | `3ef4be1932c62f3d4119e93e93ad86cbfd782d81dc8a679a1eecc5cf9e3e77e9` |
| deployment binding | `9d6b2b74b3018117c5c7dae273ce673601337f4efad30c21a882cf0d58f258c7` |

## The suites, re-run AT this commit

| suite | result |
|---|---|
| Guardian runtime + core + timing harness + preflight + induction + precreate | **426 passed, 0 failed** |
| Open-weight canary v2 + trajectory runtime (includes the recovered negative tests) | **85 passed, 0 failed** |
| C14 interpretability adapter, hostile inputs included | **48 passed, 0 failed** |
| **Total** | **559 passed, 0 failed** |

**Re-run AT the new pin `8595f6ad` on 2026-08-21: 85 + 48 + 426 = 559 passed, 0 failed — identical to the previous pin's total.** Additionally proven at this pin, which the previous freeze could not claim: the model **loads through the real engine** at the pinned identity (observed tree manifest equals the pin; binding `HF_CACHE_MODEL_ID_AND_REVISION_PATH_BOUND`; weight value manifest `AD7CB93367AB338244B79D56A16EF3AF620CD624EE237EAB03D57CE940D2B7BB`; 12 layers / 768 hidden), and a capture **ran on this record's own frozen scenario prompt** — `"In a PCB, Ohm's law states that voltage equals"` → `" current,"`.

Operational notes that keep these numbers reproducible: run with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`; the canary and adapter suites cannot share one pytest invocation (conftest module-name collision).

## What is enforced-empty, and why that is correct

- `required_source_commit_sha256` = `None` — **enforced** while `execution_authority` is `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`. Filling it is the act of granting execution authority, which belongs to the owner at the Gate 4 threshold.
- `required_provider_launcher_source_sha256` = `None` — same enforcement.
- Receipt instances — cannot exist before a launch.

## Standing after this gate

- **Gate 1: COMPLETE** (preproduction). Evidence emitted on the owner's instruction, accepted by the runtime validator, substitution declared in the committed manifest.
- **Gate 2: agent side complete; two external waits** — AWS quota request `9b482ab5a8384b608285a2283f923876t4B7wPfM` (`PENDING`, new-account limit 10 → 1000), and **the owner's `LIVE` change-set review**, reserved to the owner by the gate list's own words.
- **Gate 3: this record.** Pin done, suites green at the pin.
- **Gate 4: not started.** One RunPod A40, once, ≤ `$0.50/hour`, 30-minute hard limit — requires stock/price check at launch time and creates a **paid** machine.
- **Gate 5: not started.** Even a pass proves plumbing only; `NOT_PACKET_ELIGIBLE`, `NOT_SCIENTIFIC_RESULT`.

Nothing is activated. Preproduction `INERT`; production untouched (`INERT`, recovery `DISABLED`, ledger `0`, zero EC2). No GPU exists anywhere. The A40/Pythia experiment remains **`NOT RUN`** — neither passed nor failed.
