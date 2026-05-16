# Evidence Packet v1 — Locked Specification

**Date:** 2026-05-15
**Branch:** `codex/evidence-packet`
**Status:** Locked. Agents B (backend), C (UI), and D (integration) build against this spec verbatim.
**Sibling docs:**
- `noetic-compass-scaffold/noetic-compass/cas-native/inference/traceability_v0.py` — the trace JSON the Evidence Packet wraps.
- `docs/working/mode_7_traceability_design_2026_05_13.md` — the mechanistic-trace surface that supplies neural attribution data.

Reserved language: **never "irrefutable."** Always **tamper-evident, reproducible, independently inspectable**.

---

## 1. Why this exists — the credibility problem

The Noetic Compass project owner does not hold a CS degree. The build used AI assistance heavily. The expected audience — reviewers, regulators, ML researchers, prospective investors — is unforgiving and starts skeptical. A demo that asks reviewers to trust the builder loses before it begins.

The Evidence Packet is the answer to that. It makes the artifact talk on its own. A reviewer who opens the drawer for any single CAS thought gets the input, the structured form the model used, the output, the chain of files that produced it, the cryptographic hashes of those files, and a per-claim breakdown of what is hard evidence versus estimate — without having to take the builder's word for anything.

This rule is locked at the project level. See `feedback_traceability_is_the_whole_purpose.md`:
> *"Every model output, decision, lock-in, and generated reply must walk back to its origin. Not a feature; the architectural spine. Show your work, or don't ship it."*

The Evidence Packet is that rule rendered for stakeholders.

### Drawer headline (verbatim)

The pitch line below is the drawer's main headline. Render as a blockquote at the top of the open drawer.

> **"CAS does not just show an answer. It turns each idea into an inspectable object: meaning, structure, origin, and model evidence."**

No paraphrase. Agent C copy-pastes this string.

### Language rules

- Never write "irrefutable", "proven", "guaranteed correct", or "verified by Claude/Codex/Anthropic."
- Always write **tamper-evident**, **reproducible**, **independently inspectable**, **on-disk match**, **deterministic where applicable**.
- A neural attribution number is *evidence*. A hash match is *tamper-evident*. A compile pass is *deterministic*. Hold the line.

---

## 2. Evidence type vs claim support

Do not overload the word "confidence." The packet separates two questions:

1. **Evidence type** — how CAS found or traced the claim.
2. **Claim support** — whether the answer itself backs the claim up.

Plain example: CAS may clearly track that an answer said "this policy is
fair" while also marking the fairness claim as unsupported because the answer
gave no appeal process, bias check, worker protection, or audit path.

### 2a. Evidence type tiers

These are the only valid evidence-type labels. Locked as a TypeScript-ready union:

```typescript
type EvidenceClaimLevel =
  | 'cas_hard_trace'              // produced by the compiler + slot supervision; deterministic
  | 'source_copy_evidence'        // backed by pointer/slot evidence (which input tokens got copied)
  | 'derived_trace'               // reconstructed from logs/UI state; not a primary signal
  | 'neural_attribution_estimate'; // Mode 7 mechanistic data — evidence, not proof
```

### 2b. Claim support status

This field answers a different question: did the answer actually support the
claim it made?

```typescript
type EvidenceClaimSupport =
  | 'supported'
  | 'partially_supported'
  | 'unsupported'
  | 'contradicted'
  | 'not_applicable'
  | 'unknown';
```

- `supported`: the answer gives enough backing for this claim.
- `partially_supported`: the answer gives some backing, but leaves gaps.
- `unsupported`: CAS can see the claim, but the answer does not back it up.
- `contradicted`: the answer conflicts with the claim or its own evidence.
- `not_applicable`: the row is about trace mechanics, not an argumentative claim.
- `unknown`: old packet or missing field; do not infer support.

### `cas_hard_trace` — green check, label "CAS hard trace"

The strongest tier. Produced by deterministic systems: the CAS compiler (`api/notation/compiler.py`), the slot-supervision head, or the admissibility relations in the Rust `cas-engine`. Re-running the same input through the same compiler version returns the same answer. Mechanically reproducible.

*Plain-English tooltip:*
> "Deterministic. The CAS compiler or the supervised slot decoder produced this directly. Re-run the same input on the same code and you get the same result. No model guessing involved."

*Example row:* "The expression `^3^P|A` is a valid CAS state literal." Source: compiler.

### `source_copy_evidence` — green check, label "Source copy evidence"

Backed by the pointer-generator pointer-copy distribution. When the decoder emits a named identifier (an Ω name, a stage variable, a let-bound symbol), the trace records which input position the pointer copied from. The same identifier appearing in input and output, with a peaked `p_copy` distribution on the matching source token, is direct evidence of copy — not LM hallucination.

*Plain-English tooltip:*
> "The model's pointer mechanism shows it copied this token straight from the input. We can name the input position it pointed at and the strength of the pointer. Hallucination would look different."

*Example row:* "`Ω_translation_72` appeared at output position 14 with pointer copy strength 0.91 from input position 7." Source: `p_copy` distribution.

### `derived_trace` — blue check, label "Derived trace"

Reconstructed from logs, UI state, or post-processing steps — not a primary supervised signal. Still useful, but a step removed from the source of truth.

*Plain-English tooltip:*
> "Reconstructed from logs or downstream state, not a direct model signal. Sound, but a step removed from the source of truth. Cross-check against the hard-trace fields if it matters."

*Example row:* "Identifier repair substituted `Ω_x` → `Ω_translation_72` based on the post-processing rewrite log." Source: `identifier_repair.py` log.

### `neural_attribution_estimate` — amber warning, label "Neural attribution (estimate)"

Mode 7 mechanistic data: encoder simplex trajectory, per-layer L2 norms, attention entropy, top-K LM logits, dominant Noetic marginals. These are real measurements off the live network — but they are evidence, not proof. A high attention weight to a token does not by itself prove that token caused the output; the architecture supports the inference, but interpretability research is unfinished.

*Plain-English tooltip:*
> "Measured directly from the neural network during this run. Strong evidence, but not a deterministic guarantee. Treat it as 'here is what the model attended to' rather than 'here is why the model decided.' Interpretability is an active field."

*Example row:* "Dominant Noetic at encoder output: ^2 Positive, marginal probability 0.41." Source: `noetic_marginal` from `simplex_pooled`.

---

## 3. The seven labeled sections of the drawer

Order is locked. Each section gets a headline and a subtitle. Agent C renders them top-to-bottom in this order.

| # | Section | Headline | Subtitle (verbatim) |
|---|---|---|---|
| 1 | Input | **Input** | *"The exact text the user submitted. No editing, no paraphrase."* |
| 2 | CAS expression | **CAS expression** | *"The structured form the model used. Validated by `api/notation/compiler.py`."* |
| 3 | Output | **Output** | *"The model's full reply, generated from the CAS expression and input."* |
| 4 | Copy / slot trace | **Copy / slot trace** | *"Which named identifiers survived the trip from input to output. Backed by pointer evidence."* |
| 5 | Provenance | **Provenance** | *"Every step is logged with its checkpoint, code commit, and config."* |
| 6 | Hashes | **Hashes** | *"Compare these to the on-disk files yourself. Mismatch means something changed."* |
| 7 | Claim levels | **Evidence type & claim support** | *"Evidence type says how CAS traced it. Claim support says whether the answer backed it up."* |

---

## 4. JSON schema — the EvidencePacket contract

Agent B (backend) implements this. Agent C (UI) consumes it. Locked as TypeScript-ready.

```typescript
interface EvidencePacket {
  schema_version: 'evidence_packet.v1';
  trace_id: string;            // UUID4
  generated_at: string;        // ISO-8601 UTC, e.g. "2026-05-15T14:23:01Z"

  // ─── Section 1: Input ────────────────────────────────────────────────
  // Source: chat REPL input, before any rewrite. Verbatim user text.
  // Field origin: traceability_v0.py:289 (input_section.user_text or cas_expression).
  input: {
    text: string;              // raw user text or CAS expression
    user_id?: string;          // optional, omitted if anonymous
    session_id?: string;       // chat session UUID
  };

  // ─── Section 2: CAS expression ───────────────────────────────────────
  // Source: api/notation/compiler.py result on the parsed input.
  // Field origin: cas_routing.py compilability gate + compiler artifact.
  cas_expression?: {
    text: string;              // the canonical CAS string
    compiler_valid: boolean;   // compile_expression succeeded
    compiler_error?: string;   // populated when compiler_valid === false
    grammar_category?: string; // e.g. "state_literal", "recipe", "rpm_chain"
  };

  // ─── Section 3: Output ───────────────────────────────────────────────
  // Source: model.forward + post-processing pipeline final text.
  // Field origin: traceability_v0.py:290-293 (output section).
  output: {
    text: string;              // final_rendered_text — what the user saw
    n_tokens?: number;         // tokens emitted by the decoder
    max_new_tokens?: number;   // generation cap configured for this run
  };

  // ─── Section 4: Copy / slot trace ────────────────────────────────────
  // Source: TypedFiberDecoder pointer-copy outputs + slot-type decisions.
  // Field origin: typed_fiber_decoder.py:300-360 (p_copy, slot_type_logits,
  // copy_source_indices); per_identifier in traceability_v0.py:298.
  copy_slot_trace?: Array<{
    role: 'noetic' | 'domain' | 'drive' | 'register'
        | 'stage_var' | 'omega' | 'identifier';
    name: string;              // e.g. "Ω_translation_72", "^2", "P", "F3", "A"
    copied: boolean;           // did this survive into the output?
    source_token_index?: number; // input position the pointer pointed at
    target_token_index?: number; // output position where it appeared
    claim_level: EvidenceClaimLevel; // typically 'source_copy_evidence'
  }>;

  // ─── Section 5: Provenance ───────────────────────────────────────────
  // Source: checkpoint_manifest.json + run command + git state.
  // Field origin: train_native_nl_gen.py:1546-1564 writes the manifest
  // (checkpoint_id, git_commit_sha, n_train_records, schema_version).
  provenance: {
    model_checkpoint_id: string;     // UUID from checkpoint_manifest.json
    checkpoint_label?: string;       // human-friendly, e.g. "Stage 4A v0.2"
    code_commit_sha: string;         // from train_native_nl_gen.py:289 get_git_commit_sha()
    code_commit_summary?: string;    // one-line `git log -1 --format=%s`
    run_command?: string;            // exact CLI used to produce this output
    config_snapshot?: Record<string, unknown>; // d_model, n_layers, sampling, etc.
  };

  // ─── Section 6: Hashes ───────────────────────────────────────────────
  // Source: checkpoint_manifest.json + tokenizer manifest.
  // Field origin: train_native_nl_gen.py:1555 weights_sha = hash_state_dict(...);
  // checkpoint_manifest.json tokenizer.tokenizer_hash + english_bpe_hash;
  // trained_from_corpus_hash at manifest root.
  hashes: {
    weights_sha: string;            // sha256 of model state_dict
    tokenizer_hash: string;         // sha256 of tokenizer.json
    english_bpe_hash?: string;      // sha256 of english_bpe.json if extended tokenizer
    corpus_sha256?: string;         // sha256 of training corpus jsonl
    on_disk_paths: {
      weights_path?: string;        // e.g. ".tmp/.../model_final.pt"
      tokenizer_path?: string;
      corpus_path?: string;
    };
  };

  // ─── Section 7: Evidence type & claim support ────────────────────────
  // Per-packet rollup. Each claim separates evidence type from answer support.
  claim_levels: Array<{
    claim: string;                  // e.g. "the model produced a valid CAS expression"
    level: EvidenceClaimLevel;      // how CAS traced/found this claim
    support_status?: EvidenceClaimSupport; // whether the answer backs the claim up
    support_rationale?: string;     // plain-English reason for support_status
    rationale: string;              // 1-2 sentences, plain English
  }>;

  // ─── Auxiliary ───────────────────────────────────────────────────────
  caveats?: string[];               // ⚠ items reviewer should know
                                    // (e.g. "training corpus included synthetic records")
}
```

### Field-source quick reference

| Field | Source file |
|---|---|
| `trace_id`, `generated_at` | `traceability_v0.py:287-288` (uuid4 + `_iso_now()`) |
| `input.text` | `traceability_v0.py:266-282` (`input_section`) |
| `cas_expression.text` | `traceability_v0.py:237` (`input_cas_expression`) |
| `cas_expression.compiler_valid` | `api/notation/compiler.py::compile_expression` |
| `output.text` | `traceability_v0.py:291` (`generated`) |
| `output.n_tokens` | `traceability_v0.py:292` (`n_tokens_generated`) |
| `copy_slot_trace[].copied` | `traceability_v0.py:104` (`status == "copied"`) |
| `copy_slot_trace[].source_token_index` | `typed_fiber_decoder.py:351` (`copy_source_indices`) |
| `provenance.model_checkpoint_id` | `checkpoint_manifest.json` root `checkpoint_id` |
| `provenance.code_commit_sha` | `train_native_nl_gen.py:289` (`get_git_commit_sha()`) |
| `hashes.weights_sha` | `train_native_nl_gen.py:1555` (`hash_state_dict(model.state_dict())`) |
| `hashes.tokenizer_hash` | `checkpoint_manifest.json` `extra.tokenizer.tokenizer_hash` |
| `hashes.english_bpe_hash` | `checkpoint_manifest.json` `extra.tokenizer.english_bpe_hash` |
| `hashes.corpus_sha256` | `checkpoint_manifest.json` root `trained_from_corpus_hash` |

---

## 5. Verbatim row copy — populated and empty states

Locked. Agent C copy-pastes. No paraphrase.

### Section 1 — Input

**Default badge:** `cas_hard_trace` (green) — the input is verbatim, recorded as submitted.

- **Populated state:** show `input.text` in a monospace box. Above the box: *"The exact text the user submitted. No editing, no paraphrase."*
- **Empty state:** *"No input recorded for this trace. This packet was produced from a synthetic test run."*

### Section 2 — CAS expression

**Default badge:** `cas_hard_trace` (green) when `compiler_valid === true`. Falls back to `derived_trace` (blue) when no CAS expression was produced.

- **Populated, compiler_valid:** show `cas_expression.text` in monospace, followed by a green check and the literal string *"Compiles. Grammar category: {grammar_category}."*
- **Populated, compiler_valid === false:** show the text, an amber warning, and *"Compiler rejected this expression. Error: {compiler_error}"*. Claim level becomes `derived_trace`.
- **Empty state:** *"This response did not produce a structured CAS expression. The model answered in plain English without parsing to CAS."*

### Section 3 — Output

**Default badge:** `cas_hard_trace` (green) — the output is exactly what the model emitted plus the post-processing pipeline.

- **Populated state:** show `output.text` in a normal-prose box. Below the box: *"{n_tokens} tokens. Generation cap was {max_new_tokens}."* (Omit the line if both fields are absent.)
- **Empty state:** *"No output recorded. The decode path may have failed; check the Provenance section for run details."*

### Section 4 — Copy / slot trace

**Default badge:** `source_copy_evidence` (green) per row.

- **Populated state:** show a small table with columns *Identifier*, *Copied?*, *From input position*, *To output position*. Above the table: *"Which named identifiers survived the trip from input to output. Backed by pointer evidence."*
- **Empty state:** *"No identifiers in this trace. The input did not contain named identifiers, so nothing was copied. This is normal for bare state expressions like `^3^P|A`."*

### Section 5 — Provenance

**Default badge:** `cas_hard_trace` (green) — provenance fields are recorded mechanically at training time.

- **Populated state:** four labeled rows. *Model checkpoint:* `{checkpoint_label} ({model_checkpoint_id})`. *Code commit:* `{code_commit_sha} — {code_commit_summary}`. *Run command:* monospace box with `{run_command}`. *Config:* collapsed JSON, expandable.
- **Empty state:** *"No provenance recorded. This packet may have been generated from an in-memory smoke test that never wrote a checkpoint manifest."*

### Section 6 — Hashes

**Default badge:** `cas_hard_trace` (green) — hashes are deterministic.

- **Populated state:** rows for each of `weights_sha`, `tokenizer_hash`, `english_bpe_hash`, `corpus_sha256`. Each row shows the first 12 chars of the hash, the on-disk path (truncated to fit), and a copy-to-clipboard button. At the bottom: *"Compare these to the on-disk files yourself. Mismatch means something changed."* Plus a **Verify Hashes** button (see Section 6 contract below).
- **Empty state:** *"No hashes recorded. Without hashes this packet cannot be independently verified against on-disk artifacts."*

### Section 7 — Evidence type & claim support

**Default badge:** mixed (per-row).

- **Populated state:** a vertical list. Each row: claim text, evidence-type badge, claim-support badge, rationale in italics. Above the list: *"Evidence type says how CAS traced it. Claim support says whether the answer backed it up."*
- **Empty state:** *"No claim-level rollup for this packet. Default to inspecting each section directly."*

---

## 6. Verify Hashes contract

The Hashes section has a **Verify Hashes** button. Clicking it calls the backend.

### Request

```
POST /api/evidence/{trace_id}/verify
```

No body. The backend looks up the packet by `trace_id`, re-hashes the on-disk files referenced in `hashes.on_disk_paths`, and compares to the recorded hashes.

### Response

```typescript
interface VerifyHashesResponse {
  trace_id: string;
  verified_at: string;             // ISO-8601 UTC, time of verify
  checks: Array<{
    artifact: 'weights' | 'tokenizer' | 'english_bpe' | 'corpus' | 'code_commit';
    expected: string;              // sha256 from the packet
    actual: string;                // sha256 just computed (or git rev-parse for code_commit)
    match: boolean;
    notes?: string;                // e.g. "file not found at recorded path"
  }>;
  overall: 'all_match' | 'partial_mismatch' | 'unable_to_verify';
}
```

### UI behavior

- **`overall === 'all_match'`** — Green banner above the Hashes table:
  > *"All artifact hashes verified. The on-disk files match the recorded hashes."*

- **`overall === 'partial_mismatch'`** — Red banner above the Hashes table, listing each mismatched artifact by name:
  > *"Hash mismatch on {artifact}. Recorded {expected[:12]}, on disk {actual[:12]}. Something changed since this packet was written. Investigate before trusting this trace."*

- **`overall === 'unable_to_verify'`** — Amber banner above the Hashes table:
  > *"Some artifacts couldn't be located locally — see notes. This does not mean the trace is wrong; it means a reviewer running on a different machine should compare hashes manually."*

Each row in the `checks` array also gets a per-row colored dot (green/red/amber) so reviewers can see at a glance which artifact failed.

---

## 7. Reviewer playbook — "How to audit this"

The bottom of the drawer has a collapsible **How to audit this** section. Five concrete steps. Verbatim copy. Each step has a "what success looks like" line so the reviewer knows when to stop.

### Step 1 — Open the JSON for this trace

> *"Copy the trace_id from the top of the drawer. Find the JSON file at `noetic-compass-scaffold/noetic-compass/dashboard/public/traces/{trace_id}.json` (or wherever the backend writes it). Open it in any text editor. Confirm every field shown in the drawer also appears in the JSON."*
>
> *Success looks like:* the JSON exists, parses, and the `input.text`, `output.text`, and `hashes.weights_sha` fields match what the drawer shows you.

### Step 2 — Reproduce the output

> *"Copy the `provenance.run_command` from the Provenance section. Run it on the same machine. If the command targets a remote pod (look for `runpod` in the command), note that you need access to the same pod or a clone of its checkpoint."*
>
> *Success looks like:* the model produces the same output text for the same input, on the same checkpoint. Greedy sampling is deterministic; sampled outputs will be close but not identical.

### Step 3 — Inspect the code that ran

> *"Run `git show {provenance.code_commit_sha}` in this repository. The diff and commit message show exactly what code was running when this output was produced."*
>
> *Success looks like:* the commit exists, the working tree was clean at that SHA, and the relevant files (model code, post-processing) match what the drawer claims they do.

### Step 4 — Hash the weights yourself

> *"Compute the SHA-256 of the weights file at `hashes.on_disk_paths.weights_path` using `sha256sum {path}` (Linux/macOS) or `Get-FileHash -Algorithm SHA256 {path}` (Windows PowerShell). Compare to `hashes.weights_sha`."*
>
> *Success looks like:* the two hashes match character-for-character. A mismatch means the file on disk is not the file that produced this output — investigate before drawing conclusions from the rest of the packet.

### Step 5 — Confirm gates passed on a held-out test set

> *"The provenance section links to an evaluator report (e.g. `docs/working/stage4a_v02_2026_05_14/eval_report.json`). Open it. Look at `aggregate.free_decode_validity_rate`, `per_category.{category}.tf_acc`, and `diversity.mode_collapse_ratio` for the categories you care about."*
>
> *Success looks like:* the reported gate metrics are above their thresholds, the eval was run on a corpus whose `corpus_sha256` matches the packet's `hashes.corpus_sha256`, and the held-out set was disjoint from training.

---

## 8. Out of v1 scope (explicit)

So Agent C does not accidentally build these:

- **Replay Trace** — re-run the same input deterministically inside the drawer, side-by-side with the recorded output. Deferred to **v1.5**.
- **PDF export** — packet rendered as a single-page PDF with embedded hashes for offline review. Deferred to **v1.5**.
- **Ablation tests** — remove a layer or a head, prove the output breaks in the predicted way. Deferred to **v2**.
- **Counterfactual tests** — perturb the input, prove the trace changes in the predicted direction (e.g. swap `^2` for `^3` and confirm the dominant Noetic flips). Deferred to **v2**.
- **Negative-test packet** — fabricate a fake trace and prove the verifier rejects it. Deferred to **v2**.
- **Cross-session aggregation** — drawer for a *set* of traces (e.g. all replies in a session) with summary statistics. Deferred to **v2**.

v1 ships the seven sections, the verify endpoint, the reviewer playbook. Nothing else.

---

## 9. Acceptance checklist

For Agents B / C / D, the contract is met when:

1. **Schema** — backend emits `EvidencePacket` JSON matching Section 4 byte-for-field exactly. `schema_version === 'evidence_packet.v1'`.
2. **Drawer copy** — UI renders the seven section headlines and subtitles from Section 3 and the populated/empty-state copy from Section 5 verbatim. No paraphrase, no rewording, no emoji.
3. **Headline blockquote** — Section 1's pitch line appears at the top of the open drawer as a blockquote. Verbatim.
4. **Verify endpoint** — `POST /api/evidence/{trace_id}/verify` returns `VerifyHashesResponse` (Section 6). UI renders the three banner states with the verbatim copy in Section 6.
5. **Reviewer playbook** — the five steps in Section 7 render in the drawer footer, collapsible, in order, with the "Success looks like" line for each.
6. **Claim levels** — every row that surfaces in the drawer carries one of the four tiers from Section 2 with the correct badge color and label.
7. **Out of scope** — none of the v1.5 or v2 items in Section 8 ship in v1.

---

**Document ends. Locked. No code changed by this doc.**
