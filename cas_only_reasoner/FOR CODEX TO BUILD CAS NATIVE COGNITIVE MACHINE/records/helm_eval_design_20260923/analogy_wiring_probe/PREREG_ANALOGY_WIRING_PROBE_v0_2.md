# Analogy wiring probe v0.2: rules fixed before any reading

- **Owner:** Claude (independent checker).
- **Written:** 2026-09-23.
- **Supersedes:** `PREREG_ANALOGY_WIRING_PROBE.md` (v0.1). v0.1 produced **no reading**: attempt 1 stopped at
  its wall limit (`RUN_LOG.md`).
- **Why it was amended:** a read-only adversarial review (`records/helm_eval_design_20260923/REVIEW_20260923.md`,
  probe lens F1-F10, shortcut lens S4, stats lens F8/F9) showed that v0.1 would certify a repair that does no
  comparison. v0.1 is kept unchanged as the record of what was first written.

## The claim being checked

"Changing the arrangement Helm is asked to compare can now affect the relevant answer scores."

- **Relevant** means it can change **which candidate world wins**, or **whether any world beats NO_MATCH**.
- A uniform shift of every candidate's score is **not** relevant. A7's defect is an ordering defect: "a fixed
  relative ranking ... cannot select from both disjoint accepted sets".
- Correct answers are a later, separate test.

## Definitions (per analogy record r, frozen course `272c26e1...`, 70 records, 24 distinct focus worlds)

- **Scores.** `s_c` is the logit of candidate world c in the record's single `world_id` slot. `NO_MATCH` is
  pinned at 0 by the model.
- **X(r):** the cross-domain non-focus candidates. These are worlds whose declared domain string differs from
  the focus's. Only they can ever be answers.
- **Standardised scores:** `z_c = (s_c - mean_X s) / sd_X s`. These remove any shift and any scaling shared by
  all candidates.
- **Accepted set A(shape, domain):** the worlds in X whose contains-graph is isomorphic to `shape`.
- **Counterfactuals.** Every one is built at the **packet** level: the rewired or re-domained packet is fed
  through `pointer_inputs.read_packet` and `slots.compile_slots` again, exactly as the learner does. So every
  copy of the focus world in the reading (`worlds[...]`, `focus_world`, `node_flags`) is consistent. The
  analogy slot's symbol list must be unchanged, and that is asserted.
- **Graph alternatives, frozen here:**
  - For a 4-node focus: the other 4-node bank shapes, in canonical edge form:
    - `((0,1),(0,2),(0,3))`;
    - `((0,1),(0,2),(1,3),(2,3))`;
    - `((0,1),(1,2),(2,3))`;
    - `((0,1),(0,2),(3,1))`;
    - `((0,1),(0,2),(1,3))`.
  - For a 3-node focus: the 3-node DAGs other than the bank chain `((0,1),(1,2))`:
    - fork `((0,1),(0,2))`;
    - collider `((0,2),(1,2))`;
    - triangle `((0,1),(0,2),(1,2))`.
  - Design v0.2 no longer treats 3-4-node new shapes as secret test material (review S3/F5), so using them
    here leaks nothing sealed.
  - **Relabelling:** the alternative's canonical node 0 goes onto the declared whole; the remaining nodes
    follow in list order.
- **Domain alternatives:** the focus's `domain` declaration is replaced by each of the other three bank domain
  strings. The graph is unchanged.

## Measurements

| Id | What | Unit |
|---|---|---|
| M0 | **Noise gate.** Each base forward is run twice. `delta0 = max |s - s'|` over all records and candidates. Settings: `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `torch.use_deterministic_algorithms(True, warn_only=True)`, cudnn deterministic | logits |
| M1z | Witness pair (A7): `typed-input-092dc3b8...` vs `typed-input-0df25be3...`. Max `|z_A - z_B|` over their shared X. Kendall discordant-pair fraction between their X-rankings | z |
| M2z | Over all 70 records, grouped by focus DOMAIN (X depends only on the focus domain, so within a group X is the same set of worlds): for each (group, candidate), the spread of its z across the group's records; the maximum | z |
| M3z(f) | Per distinct focus f: max over graph alternatives of `max_{c in X} |Δz_c|` | z |
| K(f) | Per focus: max over graph alternatives of the Kendall discordant-pair fraction on X (**ranking change**) | fraction |
| RC(f) | Per focus: mean over the graph alternatives whose new accepted set is non-empty of `|mean_{A'} Δz - mean_{A} Δz|` (**does the favoured set move toward the new isomorphs**) | z |
| M4 L(f) | **Bystander control.** Apply the same graph alternatives to ONE non-focus world c' instead of the focus (the lexically first X world with the focus's node count). `L = max_{c in X \ {c'}} |Δz_c|`. A focus-to-candidate comparison leaves the other candidates unmoved. A global coupling across worlds moves them | z |
| M5 | NO_MATCH margin: the change in `max_{c in X} s_c` per graph alternative. Reported separately for alternatives with an empty and a non-empty new accepted set | logits |
| M6 RC_dom(f) | Domain counterfactual. The z-scores are standardised over ALL non-focus worlds, because the cross-domain set itself changes. For each domain alternative, compare: the focus-shape isomorphs in the NEW focus domain (which stop being answers) with the focus-shape isomorphs in the OLD focus domain (which start being answers). The measure is `|mean Δz(start) - mean Δz(stop)|`, averaged over the domain alternatives | z |

**Reported, not scored:**
- top-1 changes under the slot's decision: the argmax over the worlds, with NO_MATCH pinned at logit 0, and a tie with NO_MATCH counted as NO_MATCH;
- per-shape breakdowns;
- timings and GPU telemetry.

## Verdicts (per model), read by the program

- `tau = 1e-5` (z units). `effect_floor = max(1e-3, 100 * delta0)`.
- Every "share" is over the **24 distinct foci**, never over the 70 records.
- **The switch attribute.** A repaired container must expose a read-only boolean attribute, written
  `model.<switch>`. The probe records it and asserts it equals the requested state. For unchanged Helm 2.0 the
  attribute is absent, and that is recorded as `NOT_A_REPAIRED_CONTAINER`.

| Verdict | Condition |
|---|---|
| `INVALID_NONDETERMINISTIC` | `delta0 > 1e-6` |
| `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` | M1z <= tau AND M2z <= tau AND every M3z(f) <= tau AND every K(f) = 0 |
| `PRESENT_GRAPH` | K(f) > 0 on >= 22/24 foci AND M3z(f) >= effect_floor on >= 22/24 foci AND median RC(f) >= 1e-2 AND L(f) <= 0.1 * M3z(f) on >= 22/24 foci |
| `PRESENT_GRAPH_AND_DOMAIN` | PRESENT_GRAPH AND RC_dom(f) >= 1e-2 on >= 22/24 foci |
| `COUPLED_NOT_COMPARISON` | the PRESENT_GRAPH conditions hold except the bystander condition |
| `MIXED` | anything else |

**Preservation (a separate program, `preservation_digest.py`).** For all 564 registry records and **every**
slot, it writes the SHA-256 of the canonical JSON of each slot's float32 logits as IEEE-754 bit patterns, and
one overall digest.

## Acceptance for Codex's repair (`HELM-ANALOGY-REPAIR-1`, Part B of the design)

1. **Switch OFF.** For each of the 9 models (3 fresh seeds and 6 historical checkpoints), the preservation
   digest equals the unchanged source `20208c92`'s digest **bit for bit**. In addition:
   - the parameter count is 174,303;
   - the state_dict keys and shapes are identical;
   - historical checkpoints load `strict=True`;
   - the probe verdict is `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT`.
2. **Switch ON, trained.** `PRESENT_GRAPH_AND_DOMAIN` is required on **every** trained checkpoint whose
   analogy numbers are read.
3. **Switch ON, fresh.** If a new path is zero-initialised (a gate at 0), the fresh-container reading uses a
   recorded, seeded probe draw of those tensors. That reading is labelled `REACHABILITY`, not "wiring at init".
   A fresh reading alone never satisfies item 2.

## Before-reading on unchanged Helm 2.0 (source `20208c92`)

- **Models:** 3 fresh seeds, and `initial.pt` and `final.pt` of `receipt_2026091{7,8,9}`.
- **Predicted:** `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` on all 9, and `delta0 = 0`.
- **The preservation digests of these 9 models become the switch-OFF reference.**
- A failed prediction is reported as failed.

## Limits (current authorization `docs/OWNER_RUN_AUTHORIZATION_20260922.md`)

- **Device:** the local RTX 4070 laptop GPU. Every script exits `GPU_REQUIRED` if CUDA is absent. There is no
  CPU fallback.
- **Work:** forward passes only, under `no_grad`. No optimizer. No checkpoint is written.
- **Admission and stops:**
  - admission: at or below 75 C, and at least 2,048 MiB free;
  - stop at 80 C, checked every 10 records;
  - wall limit: **1,800 s per invocation**;
  - at most 3 models per invocation;
  - no automatic retries.
- **Scope:** no other CPU-heavy job runs at the same time. Only public packets are read: no sealed file, no
  eval split, no gold answer.
- **Cost:** no cloud and no spending.

## Amendment A1 (2026-09-23 04:50 PDT), made after two failed attempts and BEFORE any probe metric existed

Attempt log: `RUN_LOG.md`, attempts 2 and 3. No metric was written in either attempt; the probe crashed before
its first counterfactual score was stored.

1. **Where the slot plan comes from.** `slots.compile_slots` validates the whole source bank, and it rejects any
   world whose contains-list was altered (`TYPED_SOURCE_WORLD_RECONSTRUCTION`). So the slot plan is always
   taken from the **unmodified** packet.
   - Why this is safe: the analogy slot's symbols are the bank's world aliases, and no counterfactual changes
     them.
   - Where the counterfactual input comes from: its **reading** is built by `pointer_inputs.read_packet` (the
     learner's own reader). For focus changes, the probe asserts that `reading["focus_world"]["contains"]`
     equals `reading["worlds"][focus]["contains"]`.
   - This replaces "fed through `read_packet` and `slots.compile_slots` again" in the Definitions.
2. **Wall limit.** Raised to 3,600 s per invocation for both programs. Loading the course plus 564 forwards for
   each of 3 models exceeded 1,800 s.
3. **Partial results.** Both programs now write their output after each model, so a limit stop keeps the
   completed models.

The metrics, thresholds, verdict rules and the alternative list are **unchanged**.

## Amendment A2 (2026-09-23): device moves to AWS by owner order. Made before any further run.

**The order.** On 2026-09-23 the owner said "use aws", and then: "use aws as there is only 354 mb of 16 gbs
locally". The laptop ran out of memory during attempt 4 (`RUN_LOG.md`).

**The new device.** The remaining before-readings, the preservation reference and the self-test run on **one
AWS `g4dn.2xlarge`**: an NVIDIA T4 GPU, 8 vCPU, 32 GiB, us-west-2, on-demand at $0.752/hour (AWS pricing API,
2026-09-23). It is launched by `../aws_probe_job/launch.py`, with the limits written in that folder's
`JOB_LIMITS.md`.

**What changes.** Only the device, and running up to 4 invocations at the same time on that one machine. Every
metric, threshold, verdict rule, alternative list and per-invocation limit is **unchanged**: at most 3 models,
3,600 s, GPU admission at or below 75 C, a stop at 80 C, no CPU fallback, forward passes only.

**Preservation digests depend on the hardware.** Float32 kernels can differ in the last bits between GPU
models. So:
- all 9 reference models are fingerprinted on the T4;
- seed 20260919 was already fingerprinted on the RTX 4070 (`preservation_reference_20208c92_seed20260919.json`),
  so comparing the two measures bit-equality across GPUs;
- the switch-OFF acceptance check for Codex's repair must run on the **same GPU type** as the reference it is
  compared with.

## Amendment A3 (2026-09-23): acceptance item 1 is tightened. Made after the reference existed and BEFORE any repair existed.

**The measured fact.** Preservation digests differ between an RTX 4070 and a T4 for the same model: 0 of 7
compared are bit-identical (`BEFORE_READING_RESULT.md`, section 3).

**Item 1 (switch OFF) now requires, on a T4, in one job:**
- (a) the repaired container with its switch OFF;
- (b) unchanged `20208c92`, re-fingerprinted in the same job as a same-machine control.

**Pass:** (a) equals (b) bit for bit on all 9 models, AND (b) equals the T4 reference in `../aws_probe_job/results/`.

**If (b) differs from the reference:** the reading is `REFERENCE_NOT_REPRODUCIBLE_ON_T4`, never a pass. That settles
the reference question first.

Nothing else changes.
