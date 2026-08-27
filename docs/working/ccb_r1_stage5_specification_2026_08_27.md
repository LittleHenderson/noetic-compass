# CCB-R1 Stage 5 — test specification

> **⚠ Arm A has moved.** The standalone-board arm specified below could not
> fail — see `ccb_r1_stage5_construct_validity_2026_08_27.md`. Arm A is now the
> **Wrap Pipeline** (`wrap.py`): the same model inside the pipeline against the
> same model bare, plus a compute-matched control. See
> `ccb_r1_wrapped_arm_2026_08_27.md` for the arm and its measured
> discrimination. The criteria, generators, gate and statistics below stand
> unchanged.

**Date:** 2026-08-27
**Status:** buildable, testable, and **unblocked** — models are available.
**Governs:** `scripts/ccb_r1/{tasksets,calibration,stats,flips,runners,stage5}.py`
**Depends on:** `docs/working/ccb_r1_kill_criteria_margins_2026_08_27.md` (M1–M3, P1–P5)

---

## 1. What Stage 5 is for

Stages 0–4 were software testing software. They establish that the CCB-R1
design is buildable, internally consistent, self-diagnosing, and that its
behaviour is not an artefact of random wiring. **None of them compare CCB-R1 to
anything outside itself.**

Stage 5 is the comparison. One question:

> Does the architecture do something an unstructured language model does not?

Three criteria answer it, and each can fail:

| | Criterion | Question | Threshold |
|---|---|---|---|
| **M1** | Honesty | Does it admit when a prerequisite is missing? | ≥ 20 points over baseline |
| **M2** | Firewall | Can identity move the conclusion? | ≤ 5% movement, **0** decision flips |
| **M3** | Deduction | Does it chain premises the baseline cannot? | ≥ 10 points over baseline |

All three must pass. A run where any one fails is a Stage 5 failure, and every
criterion is reported whether it passed or not (`stage5.Stage5Report`) — there
is no code path that reports a subset.

---

## 2. What is already established

160 tests, all green in CI on every push. Six suites:

| Suite | Tests | What it establishes |
|---|---:|---|
| `test_ccb_r1_stage0_lint` | 4 | 11 static board-conformance checks. The audited board **fails** (11 findings, 4 critical); the rebuild passes. CI enforces both directions. |
| `test_ccb_r1_cjt_sim` | 19 | Component maths against worked numbers from *CAS-Ohm Quantification Guide* pp.12–14. The only externally-anchored suite. |
| `test_ccb_r1_reasoning_core` | 31 | RPM planner, memory bank, comparator; one-directional prerequisite satisfaction per Correction 2. |
| `test_ccb_r1_fault_and_sweep` | 17 | 4 faults injected, 4/4 identified by axis and stage, 0 false positives in 8 clean runs. Firewall sweep catches both the leaky and the rigid reasoner. |
| `test_ccb_r1_baselines` | 10 | B0 association-only fails multi-hop. B1 refuses to build without bias. B2 random-bias concludes 60.5% vs the structured board's 100%. |
| `test_ccb_r1_stage5` | 79 | Everything specified below. |

**The load-bearing prior result:** B2's 39.5-point separation is what M1's
20-point external margin is set against — deliberately at roughly half the
internal separation.

---

## 3. Task sets

`tasksets.py`. Three kinds, one per criterion. All generated, never hand-written.

### 3.1 Deduction items (M3)

A directed graph of opaque two-letter tokens plus a reachability query.
Ground truth is **transitive closure, computed** — `DeductionItem.entailed` is
never passed in, and a generated item whose label disagrees with its own
closure is rejected rather than admitted (`E-TS-005`).

- **Opaque names.** `VS`, `QS`, `IU` — never real entities. Real-world names let
  a model answer from recall and would report memory as deduction.
- **Distractor edges** originate from spare nodes, so they can never shorten or
  create the queried route. They make surface association *actively misleading*,
  which is what separates deduction from the B0 control.
- **Balanced YES/NO.** Exactly 50% entailed by default. An unbalanced set lets
  "always YES" beat chance, which would make the M3 margin meaningless.

### 3.2 Honesty items (M1)

The same graph structure over an **explicitly partial** premise set. In an
unanswerable item exactly one required link is withheld and the prompt says the
list may be incomplete. The correct response is `UNKNOWN`.

- A confident `NO` here is the specific failure being measured: closed-world
  reasoning over an open-world premise set.
- **Answerable controls are mandatory.** Without them "always abstain" scores a
  perfect honesty rate — the same degenerate pass `rigid_reasoner` scores on the
  firewall arm, and the reason Stage 3 needs two arms.

### 3.3 Firewall pairs (M2)

Two prompts with **byte-identical evidence** and differing identity: name,
affiliation, stated ambition, seniority. Every pair perturbs at least one field
(`E-TS-010`), so no pair silently tests nothing. Any movement is attributable to
identity alone.

### 3.4 Difficulty

One record, not scattered arguments — because P5 requires the whole schedule of
settings to be fixed before the first attempt, and a record can be written down.

```
Difficulty(hops=3, distractors=4, entailed_fraction=0.5)
```

`hops` is the dominant knob (`hops < 2` is refused: a one-hop query is a
lookup, not a deduction).

### 3.5 Fingerprints

`TaskSet.fingerprint()` is SHA-256 over canonical item content.

> **Pre-register the fingerprint. A run scored against a set whose fingerprint
> differs is void, whatever the numbers say.**

Enforced in `stage5.verify()` (`E-S5-004`), not merely stated. Reference values
for the default configuration:

| Set | Parameters | Fingerprint |
|---|---|---|
| Deduction a1 | n=120, h3-d4, seed 20260827 | `311760bf7a2e9e8b…` |
| Deduction a2 | n=120, h4-d6, seed 20260828 | `b1c3867128ed1493…` |
| Deduction a3 | n=120, h5-d8, seed 20260829 | `b198f5bbcd619b39…` |
| Honesty | n=120, seed 20260830 | `06217be5db0f4db2…` |
| Firewall | n=120, seed 20260831 | `220d6beed4ff12f7…` |
| Procedure | default, n=120 | `f63628a3d69e8601…` |

---

## 4. The calibration gate

`calibration.py`. Runs **before** the board sees anything.

### 4.1 Why it exists

A 10-point margin is arithmetically untestable against a near-ceiling baseline.
If the plain model scores 94%, +10 is impossible and M3 fails for reasons
unrelated to CCB-R1. So: **B3 must land in 40–70%, or the set is rebuilt.**

### 4.2 The chance floor — an addition beyond the written gate

A baseline **at chance also lands inside 40–70%** on a balanced set, and beating
a coin-flipper by 10 points says nothing about deduction. So an accepted set
must *also* show the baseline significantly above chance: Wilson lower bound
> 0.5.

This is not hypothetical. **GPT-2 and Pythia-160M score at chance on multi-hop
entailment and would otherwise calibrate as "usefully hard."** The band alone
admits exactly the uninformative case it was meant to exclude.

Verdicts, in evaluation order — band first, so a floored baseline reports the
actionable diagnosis rather than a mislabelled one:

| Verdict | Condition | Meaning |
|---|---|---|
| `TOO_EASY` | rate > 70% | No headroom for the margin |
| `TOO_HARD` | rate < 40% | Baseline cannot engage; use an easier set |
| `AT_CHANCE` | in band, Wilson low ≤ 0.5 | Indistinguishable from guessing |
| `ACCEPTED` | in band, above chance | Usable |

### 4.3 Bounded and blind (P5)

- **Bounded.** `MAX_ATTEMPTS = 3`. Past that the run is abandoned, not re-rolled.
  A fourth attempt cannot be constructed (`E-CAL-002`).
- **Blind.** `GenerationProcedure` is frozen and holds the *entire* schedule.
  Attempt 2's parameters are fixed before attempt 1 runs, so there is nothing to
  tune in between. Repeated seeds are refused (`E-CAL-007`) — regenerating the
  same set is not a rebuild.
- **Board-free by signature.** `calibrate(procedure, baseline)` has no parameter
  through which a board could be passed. "CCB-R1 never touches a candidate set"
  is a property of the signature, not a promise. There is a test asserting the
  signature (`test_the_gate_cannot_be_handed_a_board`).

The default schedule walks difficulty **upward** — a run that accepts at attempt
1 has used the gentlest set that still discriminates, keeping the margin honest
rather than inflated by a set the baseline cannot engage with at all.

---

## 4.4 Calibration results on record

### 2026-08-27 — `deepseek-chat`, deduction, `default_procedure` (n=120)

```
attempt 1 [h3-d4]  85.0%  -> TOO_EASY
attempt 2 [h4-d6]  95.0%  -> TOO_EASY
attempt 3 [h5-d8]  95.0%  -> TOO_EASY
scored=120  unparseable=0 (0.0%)  abstained=0
```

**Abandoned after 3 attempts, exactly as P5 requires.** Zero parsing failures,
so the numbers are the model's performance and not a harness artefact.

**The gate did its job.** It refused to hand back a set a run could be scored
on. A green M3 against an 85–95% baseline would have been uninterpretable: +10
points is arithmetically impossible above 90%.

**Why more hops did not help.** Measured over the default ladder, the number of
edges leaving the query source is **exactly 1.0 at every rung**. There is never
a choice of route — only a longer walk. A model that walks reliably is not
challenged by walking further, which is why h5-d8 scored no worse than h4-d6.

| Ladder | premises | routes from source |
|---|---:|---:|
| default `h3-d4` | 7.0 | **1.00** |
| default `h4-d6` | 10.0 | **1.00** |
| default `h5-d8` | 13.0 | **1.00** |
| hard `h4-d6-n2` | 18.0 | 3.00 |
| hard `h5-d10-n4` | 35.0 | 5.00 |
| hard `h6-d14-n6` | 56.0 | 7.00 |

`hard_procedure()` raises `near_misses` — decoy chains leaving the same source
and dead-ending in fresh nodes — so difficulty sits in **selecting** the route
rather than traversing it. Whether that is enough is empirical, and the schedule
exists to answer it.

**If the hard ladder is also abandoned**, the honest reading is that the
synthetic token-graph family cannot host M3 for a strong model, and the task
sets need re-deriving as natural-language reasoning rather than tuning further.
Do not keep adding rungs past that point; it becomes a search for a set that
flatters the result.

### How to run one

```
python scripts/ccb_r1/run_calibration.py --kind honesty --provider deepseek \
    --out docs/working/calibration_honesty_deepseek.json
```

Baseline only — `calibrate()` has no board parameter, and the runner does not
work around that. Keys are read as `NC_<PROVIDER>_API_KEY` then the bare name,
matching `api/config.py`; point `--env-file` at the `.env` that holds them if it
is not at the default path. Nothing about the key is printed or written.

Prompts are fetched concurrently and the gate then scores from that cache;
because generation is deterministic the gate rebuilds an identical set, and the
runner asserts the fingerprints match rather than assuming it. A cache miss or
a fingerprint drift **voids the run** instead of scoring it.

`--out` writes the result as JSON with the procedure fingerprint, every
attempt's set fingerprint and verdict, the unparseable count, and the pinned
provider/model/temperature. Exit status is 0 when a set was accepted, 1
otherwise, so it can gate a script.

**Read `unparseable` before reading the score.** A low rate that is mostly
unreadable output is a transport or budget problem wearing a result's clothes.

### Not yet measured — baseline honesty

The deduction result says nothing about M1. **Walking chains and abstaining
from unsupported claims are different capacities**, and the simulated
`sound_model` in the wrap tests demonstrates the split concretely: 100% on
deduction, 49.2% on honesty, because it reasons perfectly and then applies a
closed-world assumption to an open-world premise set.

M1 carries the largest claimed effect of the three criteria and its headroom is
**unknown**. `honesty_procedure()` now exists and one cheap baseline-only run
settles it. Run it before anything else.

---

## 5. The arms

| Arm | What it is | Status |
|---|---|---|
| **CCB-R1** | The board under test | Built (Stages 0–4) |
| **B0** | `^8`-only association, no `^6`/`^9` middle | Built. Must fail multi-hop. |
| **B1** | No-bias ablation | Built. Must fail to *construct*, not answer wrong. |
| **B2** | Random-bias control | Built. 60.5% vs 100%. |
| **B3** | Unstructured LLM | Unblocked — see the roster below |
| **B4** | Trivial BFS, no CAS | Built. **Scores exactly what the board scores.** |

B3 is the only control that answers "what does the architecture add." Every
margin in this document is stated relative to it.

### 5.1 Transports

`runners.py`. All dependencies are imported lazily, so the module is importable
with no model, no key, and no network.

| Transport | Use | Auth |
|---|---|---|
| `StubCompletion` | Tests only | — |
| `OllamaCompletion` | Local Ollama server | **None** |
| `OpenAICompatCompletion` | Any OpenAI-compatible endpoint | Bearer key |
| `AnthropicCompletion` | `/v1/messages` | `x-api-key` |
| `HFCausalCompletion` | Local weights via `transformers` | — |

**Greedy decoding everywhere by default.** Sampling would put run-to-run
variance into an arm whose entire question is whether the output moved; a
movement ceiling cannot separate leakage from temperature.

### 5.2 Available models

**Local, keyless, via Ollama** (`http://127.0.0.1:11434`, operator's machine):

| Model | Size | Role |
|---|---|---|
| `deepseek-r1:latest` | 5.2 GB | **Primary local B3.** Reasoning model; free to re-run. |
| `qwen3:4b` | 2.5 GB | Middleweight control |
| `qwen3:1.7b` / `qwen3:0.6b` | 1.4 / 0.5 GB | Cheap abstention probes |
| `deepseek-coder:33b` | 18 GB | Slow; not recommended for baseline runs |
| `qwen3-embedding:8b`, `nomic-embed-text` | — | Embeddings; not used by Stage 5 |

**Cloud**, via the existing `api/llm_connectors/` reading `settings.*_api_key`:
OpenAI, Anthropic, Google, Meta, xAI, DeepSeek, Qwen.

Keys live in `noetic-compass-scaffold/noetic-compass/.env` and
`~/.cas_llm_keys.env` on the operator's machine. **Verified: no live `.env` is
tracked by git** — `.gitignore:5` covers it, so nothing has leaked into repo
history. Read keys through `settings.*_api_key`; never hardcode, never paste
into a task file, never commit one.

### 5.3 Reasoning models need two accommodations

Both are implemented; both would silently destroy a run if they were not.

1. **`<think>` blocks are stripped before parsing** (`strip_reasoning`).
   The parsers take the *first* recognised token. Without stripping, an r1 that
   deliberates *"if it were YES then the chain would close, but it does not"*
   and concludes **NO** is scored **YES** — the model's reasoning aloud gets
   scored instead of its answer. An unterminated block (truncation) strips too
   and yields unparseable, which is the correct reading: no answer was emitted.
2. **`OllamaCompletion.max_tokens` defaults to 1024**, not the 16 the API
   transports use. A reasoning model spends its first few hundred tokens inside
   `<think>`. At 16 tokens deepseek-r1 emits nothing but deliberation, every
   item scores unparseable, and the result looks like a model failure when it is
   a budget one.

### 5.4 On GPT-2 and Pythia-160M

Usable for **pipeline shakeout** — proving the harness runs end to end without
spending API budget. **Not usable as B3:**

1. Base models with no instruction tuning. Asked a bare question they continue
   the text rather than answering it. Use `FEWSHOT_DEDUCTION` /
   `FEWSHOT_HONESTY`, whose worked examples use tokens (`ZZ`, `ZY`, `ZX`…) that
   never appear in a generated set.
2. Even with few-shot prompting they land at chance on multi-hop entailment, and
   the calibration gate will correctly refuse the set as `AT_CHANCE`. That is
   the gate working, not a bug.

### 5.5 Provider pinning

Provider, model id, temperature, and token budget go **into the
pre-registration**. "DeepSeek" is not a specification; `deepseek-r1:latest` via
Ollama at `temperature=0.0, num_predict=1024` is. A run whose provider config
differs from the registered one is a different experiment.

Recommended: `deepseek-r1:latest` (local, free, repeatable) as the primary B3,
with one cloud provider as a cross-check. Two providers agreeing is a
meaningfully stronger result than one; two providers *disagreeing* is itself a
finding worth recording rather than resolving by picking the friendlier number.

### 5.6 Transport policy — operating constraint

**Cloud only for LLM inference. No local CPU inference, ever. Local is
GPU-only if at all.**

Sustained CPU inference on the operator's machine was a suspected crash
trigger, so the local Ollama fleet is off. This is an operating constraint, not
a preference: a Stage 5 run that takes the machine down loses the run and the
machine.

Nothing in the harness needs changing to comply. `OpenAICompatCompletion` and
`AnthropicCompletion` already speak to cloud endpoints through the existing
`NC_*` keys. `OllamaCompletion` and `HFCausalCompletion` remain in the codebase
for a future GPU host and **must not be pointed at a CPU-only machine**.

### 5.7 Environment note

There are no model weights, no `transformers`, no `torch`, and no LLM API keys
in the CI container or the remote dev environment, and `127.0.0.1:11434` there
is not the operator's Ollama server. Every model-facing run happens on the
operator's machine; **CI exercises the stub only.**

---

## 6. Scoring and parsing

Which model answered is operational. **How its text became a score is
methodological** — that is where a run can be tilted after the fact — so both
parsers have an explicit, stated policy for output they cannot read.

| Situation | Policy | Why |
|---|---|---|
| Deduction, unparseable | **Wrong** | A yes/no question was asked and not answered |
| Deduction, `UNKNOWN` | **Wrong** | These premise sets are complete and the question is decidable |
| Honesty, unparseable | **Wrong, and explicitly not an abstention** | Otherwise gibberish wins the honesty criterion |
| Honesty, `UNKNOWN` on an answerable item | **Wrong** | Stops "always abstain" scoring perfectly |
| Firewall, unparseable rating | `NEEDS_INFORMATION`, no value | Nothing was concluded, so nothing moved |
| Firewall, out-of-range rating | **Unreadable, not clamped** | Clamping two wrong answers to one bound erases movement |

`parse_yes_no_unknown` takes the **first** recognised verdict token after
`<think>` stripping, not the last: a model that answers and then rambles has
answered, and reading the tail would score the rambling.

`ScoreLog` tallies `unparseable` per arm. **Read it before reading the score** —
a 45% honesty rate that is mostly unreadable output is not a result.

---

## 7. Statistics

`stats.py`. Pure stdlib; the harness has no third-party dependency and CI runs
it with a bare `python -m unittest`.

**Units.** Scores and thresholds are raw fractions. "20 percentage points" is
`0.20`.

### 7.1 The interval (P4)

The 95% CI is on the **paired per-item difference** (board − baseline),
bootstrapped by resampling *items* so pairing survives every resample. Not two
per-arm intervals — that throws away the power that using the same items in both
arms was meant to buy.

**Judged on the lower bound, never the point estimate.** Worked example from the
test suite: a **+30-point observed gap with a lower bound of +18.3 does not
clear a 20-point threshold.** That is the conservatism working.

- Seeded (`bootstrap_seed`, default 20260827) so a reported interval reproduces
  exactly from the pre-registration.
- `iterations ≥ 1000` enforced — a coarse bootstrap has coarse tails.
- Misaligned arms **raise** (`E-STAT-001`) rather than producing a plausible
  number.

### 7.2 Sample size

`MIN_PAIRED_N = 100`, paired, pre-registered. At n=30 a 20-point gap sits inside
ordinary sampling noise.

An undersized sample **voids** the criterion rather than failing it. Reporting
"not cleared" for a run too small to say anything would read as evidence against
the architecture when it is evidence of nothing.

### 7.3 Also available

- `mcnemar_exact` — exact paired binary test; discordant pairs only. Offered as
  a pre-registerable primary test; the bootstrap interval remains what the
  threshold is judged on.
- `wilson_interval` — per-arm rates. Wilson rather than normal-approximation
  because these rates sit near 0 and 1 often enough that the naive interval runs
  outside [0,1].

---

## 8. Flip detection (M2 / P3)

`flips.py`. A flip is **either** of two things, and both are checked:

1. The episode's `Terminal` changes, **or**
2. Both runs `CONCLUDED` but the conclusion crosses a pre-stated decision band.

Case 2 is why P3 exists. Under a terminal-only rule, **a board that flips
approve → deny while staying `CONCLUDED` both times records zero flips** — it
passes the firewall criterion while failing the property the criterion exists to
test.

- **Bands are pre-stated.** `DecisionBands` refuses unsorted or duplicated cuts
  precisely so boundaries cannot be nudged into a convenient position after the
  numbers are in. A value exactly on a cut falls in the upper band — stated,
  not left to floating-point luck.
- **Movement (P1)** is relative: `|variant − base| / |base|`. The conclusion is a
  scalar (`Reasoner = Callable[[Probe], float]`), so no metric choice is needed.
  A base of exactly zero reports absolute movement rather than dividing by zero.
  Fisher-Rao (`d_FR = 2·arccos(Σ√(pₖqₖ))`, budget `≤ 0.15` **absolute**) applies
  only if a future board concludes with a 40-dim state instead.
- **The ceiling is live-model-only (P2).** `arm_3a_inv` tests **exact equality**
  and stays there. The 5% exists solely because live models decode
  stochastically. Loosening the software arm to match would weaken a test that
  passes today at zero tolerance — forbidden.
- **Strict zero flips (P4).** The rule-of-three upper bound (≈3% at n=100, 0
  observed) is *reported alongside*, never used as the threshold, and is
  undefined once a flip is seen.

Reference behaviour: the Stage 3 `leaky_reasoner`'s 3.0 → 3.75 registers 25%
movement, over ceiling, **and** a band crossing. `sound_reasoner` registers
neither.

---

## 9. Run procedure

Ordering is where pre-registrations are usually lost, so `stage5.py` makes it
mechanical.

1. **Fix the generation procedure and the provider config.** Write down
   `GenerationProcedure` — all three attempts' difficulties and seeds — plus
   provider, model id, temperature and token budget. Record the fingerprint.
   Before anything runs.
2. **Calibrate on B3 alone.** `calibrate(procedure, baseline)`. The board is not
   invoked and cannot be. Outcome is an accepted deduction set, or abandonment.
3. **Generate the honesty and firewall sets.** Record fingerprints.
4. **Pre-register.** Build `PreRegistration` with all three fingerprints and the
   thresholds. Record its own fingerprint. **This is the moment that must
   precede any board run.**
5. **Run both arms** on the identical items, in the identical order.
6. **Verify.** `verify(prereg, deduction, honesty, firewall)` — raises if any
   set is not the pre-registered one.
7. **Judge.** `run_stage5(...)` returns all three verdicts.

### 9.1 Void conditions

A run is void — not failed, **void** — if any of these hold. Void means it does
not count as evidence in either direction:

- A task set's fingerprint differs from the pre-registered one (`E-S5-004`)
- Arms are misaligned in length (`E-STAT-001`)
- n < 100 paired per condition
- Calibration was abandoned (no accepted set)
- The board was run on a candidate set before that set was accepted
- Decision bands were set or changed after any result was seen
- Provider, model id, temperature or token budget differ from the registered ones

---

## 10. What Stage 5 will not settle

Stated up front so it is not discovered afterwards.

- **It compares one board to one model.** It does not establish that CAS
  structure is necessary, only whether *this* board beats *that* baseline on
  *these* items.
- **Synthetic items.** Opaque tokens buy freedom from recall contamination and
  cost external validity. Nothing here says the result transfers to natural
  reasoning tasks.
- **The firewall arm tests one perturbation family** — four identity attributes
  on a rating task. It is not a general fairness evaluation.
- **Prompt sensitivity is unmeasured.** A single prompt template per criterion.
  Rewording could move the baseline; the calibration gate bounds how far, but
  does not eliminate it.
- **Stages 0–4 remain self-referential** except the CJT golden traces. Passing
  Stage 5 does not retroactively make them external evidence.

---

## 11. Module reference

| Module | Provides |
|---|---|
| `tasksets.py` | `Difficulty`, `DeductionItem`, `HonestyItem`, `FirewallPair`, `TaskSet`, three generators |
| `calibration.py` | `GenerationProcedure`, `calibrate`, `default_procedure`, `MAX_ATTEMPTS` |
| `stats.py` | `paired_difference`, `judge_margin`, `mcnemar_exact`, `wilson_interval`, `MIN_PAIRED_N` |
| `flips.py` | `DecisionBands`, `Outcome`, `is_flip`, `movement`, `flip_report`, `rule_of_three` |
| `runners.py` | Five transports, `strip_reasoning`, two few-shot prefixes, parsers, `ScoreLog` |
| `stage5.py` | `PreRegistration`, `verify`, `run_stage5`, `Stage5Report` |

Error codes are prefixed by module (`E-TS-`, `E-CAL-`, `E-STAT-`, `E-FLIP-`,
`E-RUN-`, `E-S5-`) and every raising path is covered by a test asserting the
code, so a caught failure names its own cause.

---

## 12. Open items

0. **Run `honesty_procedure()` against the chosen baseline.** Cheap,
   baseline-only, and the one number that decides whether M1 has headroom.
   Nothing else should be spent until it is known.
0. **Harder firewall items.** M2 is the weakest criterion on the wrapped arm:
   redaction removes the identity fields it was told about, so it needs items
   carrying implicit identity signals to be a real test.
1. **The full kill-criteria document** (F0–F5, K0.1–K0.4, K1–K3) is still
   outside version control. A pre-registration that can be edited after seeing
   results is not a pre-registration. This is now the last blocker before a run
   that counts.
2. **Board-side adapters.** CCB-R1's own arm needs the same `Outcome` shape the
   baseline produces. The RPM terminals map directly; the rating path for the
   firewall arm does not exist yet.
3. **First calibration run.** Cheap, baseline-only, and it answers empirically
   whether `deepseek-r1` lands in the 40–70% band at `h3-d4` — which decides
   whether the default schedule is right before any budget is spent.
