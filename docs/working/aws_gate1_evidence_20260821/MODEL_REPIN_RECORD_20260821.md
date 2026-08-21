# Model re-pin record — owner-approved 2026-08-21

**Authorization, verbatim: "re-pin approved proceed".** This page is the full account of what moved, why, and what was proven afterwards.

## Why the re-pin was necessary

The canary's byte-exact weight verifier and the pinned model file were **mutually unsatisfiable**. Not a judgement call — proven byte-for-byte:

- pinned `model.safetensors` `29D2E457A664E41C12C735F20A36DC0956A665F614A54CE5DB21A32E75965270` carries **184** tensors, including **36** legacy GPT-NeoX buffers;
- under the canary's own pinned `transformers==5.8.1` the loaded `state_dict()` carries **148** keys;
- `verify_loaded_weight_values` requires **exact set equality**.

The canary would therefore have raised inside `load_open_weight_runtime` **on the pod, after the one authorized create attempt was spent, before any capture**. Two ways out existed. The verifier was **not** touched — weakening a check to make a run pass is exactly what the owner's gate rule forbids. The model artifact moved instead.

## Method — and the step that makes it trustworthy

**The method was proven against the old pin before it was used to make a new one.** The attestation code was run over the untouched original snapshot and reproduced the preregistration's existing `tree_manifest_sha256` `6373A5C8367B1D33B96921791D28AD29E7851D3B9BC78C6D3C25E94EF342C571` **exactly**. Only then was the same code trusted to compute the replacement hash.

The new weights are a re-serialization of the pinned originals — `from_pretrained(dtype=float16)` → `save_pretrained(safe_serialization=True)` under `transformers 5.8.1` — not a re-download and not a different model. The 148 functional tensors were already confirmed byte-identical (`changed=[]` in the original failure report). `config.json` and all three tokenizer files are **byte-identical to the pinned originals** — carried across, never regenerated.

## Exactly what moved — five hashes, nothing else

| pin | from | to |
|---|---|---|
| `model.safetensors` sha256 | `29D2E457…5270` | `D5861D3237C5F8E952B4EBF05179F3BC50D479186FBE96845D22660D96C50D97` |
| `model.safetensors` byte count | `374998696` | `324662840` |
| model `tree_manifest_sha256` | `6373A5C8…C571` | `BB65650EB00AAA36900BBBB57B2C96EF4D34AA395F124E68C801C483D4BB5CDE` |
| `FROZEN_EXPERIMENT_SHA256` | `B5D00239…C6C8` | `0B037433A556A9626C0B5D71D191F29586829A9B6E15F189924FC756E76167D9` |
| `required_source_file_manifest_sha256` | `6EC46F9A…7CCF` | `BD4CCE31A351D05AE58F32C4F033B03B6C2F5CFF68AE234030E26CB5B4BB2A31` |

Plus the preregistration self-hash, recomputed twice as required: `30798FA6…` → `C7B50F16…` → `5EAEE8559B0B39440B41DF8B8346082D5799A2D550FDE24125F521636502CEE8`.

**Unchanged:** `model_id`, `revision` `50f5173d932e8e61f858120bcb800b97af589f46`, the scenario, the prompt, layers, seeds, dtype policy, memory floors, dependency lock, image digest, and every NO-GO latch. `execution_authority` remains `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`.

## The freeze caught the incomplete edit — twice

The first edit changed only the preregistration. The suite failed **10 tests** with `preregistration experiment bytes differ from frozen design` — a second guard, `FROZEN_EXPERIMENT_SHA256`, compiled into the source so a re-hashed document cannot smuggle a changed experiment past. Updating that surfaced a third guard: editing the source file broke `required_source_file_manifest_sha256` (**8** failures). Both were completed rather than bypassed. **This is the freeze working as designed, on its author.**

## Proof after the change

| check | result |
|---|---|
| Canary v2 + trajectory runtime | **85 passed, 0 failed** |
| C14 interpretability adapter (hostile inputs included) | **48 passed, 0 failed** |
| Guardian runtime + canary tooling | **426 passed, 0 failed** |
| **Total** | **559 passed, 0 failed** |
| Tamper guard `test_rehashed_preregistration_cannot_change_frozen_experiment` | **still passes** — a re-hashed document with an altered prompt is still rejected |
| Live load at the pinned identity | **PASSED** — observed tree `BB65650E…` equals the pin; binding `HF_CACHE_MODEL_ID_AND_REVISION_PATH_BOUND`; weight value manifest `AD7CB93367AB338244B79D56A16EF3AF620CD624EE237EAB03D57CE940D2B7BB`; 12 layers / hidden 768 |
| Capture on the canary's **own frozen prompt** | **RAN** — `"In a PCB, Ohm's law states that voltage equals"` → `" current,"` |

The `559` total matches the Gate 3 freeze record exactly.

## Standing after the re-pin

Gate 3's freeze record is superseded on five hashes only; its commit pin advances with this change. **Gate 2 still open** (Lambda quota `9b482ab5…`, `CASE_OPENED`). Gate 4 remains authorized but not started. Nothing launched, no pod touched, no AWS resource changed, production `INERT`. The A40/Pythia experiment is still **`NOT RUN`** — but it would now die at model-load **no longer**.
