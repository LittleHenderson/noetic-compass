# CAS Harness matched-taxonomy Evidence Packet spec

**Date:** 2026-05-30
**Status:** Proposed integration spec for the pre-registered matched-taxonomy control
**Owner:** Agent D - Evidence Packet, FAQ, and claim-language integration
**Scope boundary:** This document only specifies packet fields, proof-chip wording, FAQ wording, Audit Console display guidance, pass/grey/fail claim language, and senior-researcher interpretation. It does not edit scripts, app UI, or run artifacts.

## Purpose

The matched-taxonomy control asks a narrower question than the general CAS Harness Evidence Packet:

> Did CAS beat same-size, coherent non-CAS semantic taxonomies under the same model, same activations, same split, same balanced-logistic probe family, same text baselines, same shuffled-label controls, and same flat-plus-nested lacunarity scoring?

The packet must make that comparison independently inspectable. It should let a reviewer see exactly what taxonomies were compared, whether the controls were fair, which pre-registered gates passed or failed, and what claim language is licensed by the result.

Reserved language from the Evidence Packet spec still applies: never call the result "irrefutable," "proven," or "guaranteed." Use "tamper-evident," "reproducible," "independently inspectable," and "pre-registered gate."

## Proposed Evidence Packet fields

This is a specialization of the existing Evidence Packet/WORM pattern. It should either be embedded under the packet's method-specific payload or emitted as a dedicated artifact referenced by the final packet.

```typescript
interface MatchedTaxonomyEvidencePacket {
  schema_version: 'cas_matched_taxonomy_packet.v0';
  packet_id: string;
  trace_id: string;
  generated_at: string; // RFC 3339 UTC

  preregistration: {
    prereg_doc_path: string; // docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md
    prereg_doc_sha256: string;
    prereg_date: '2026-05-30';
    status: 'pre_registered' | 'executed' | 'superseded';
  };

  run_identity: {
    method_label: string; // e.g. S9-40E-MATCHED-TAXONOMY-CONTROL
    model_subject: string; // e.g. GPT-NeoX-20B
    model_revision?: string;
    model_provenance: Record<string, unknown>;
    harness_build: {
      git_commit_sha: string;
      runtime_label?: string;
      package_lock_sha256?: string;
    };
    execution_environment?: {
      host_label?: string;
      device?: string;
      python_version?: string;
      sklearn_version?: string;
      torch_version?: string;
    };
  };

  data_and_split: {
    scenario_library_id: string;
    scenario_artifacts: Array<ArtifactDescriptor>;
    activation_artifacts: Array<ArtifactDescriptor>;
    split_manifest: ArtifactDescriptor;
    split_seed: number;
    train_count: number;
    test_count: number;
    group_overlap_count: number;
    class_balance_table_artifact?: ArtifactDescriptor;
  };

  taxonomies: Array<{
    taxonomy_id: string;
    taxonomy_family:
      | 'cas_40e'
      | 'cas_f28'
      | 'scrambled_cas'
      | 'coherent_non_cas_40'
      | 'coherent_non_cas_7x4'
      | 'text_only_adversary';
    class_count: 40 | 28;
    factorization?: '10x4' | '7x4' | 'flat_40' | 'flat_28';
    label_manifest: ArtifactDescriptor;
    human_description: string;
    construction_notes: string;
    construction_seed?: number;
    derived_from_cas_definitions: boolean;
    strawman_risk_note?: string;
  }>;

  probe_protocol: {
    hidden_readout: {
      estimator: 'sklearn.LogisticRegression';
      scaler: 'StandardScaler';
      class_weight: 'balanced';
      solver?: string;
      layers_scanned: number[];
      best_layer_rule: string;
      metrics: ['accuracy', 'macro_f1'];
    };
    text_baseline: {
      estimator: string; // e.g. CountVectorizer + LogisticRegression
      same_split: true;
      metrics: ['accuracy', 'macro_f1'];
    };
    shuffled_label_control: {
      seeds: number[];
      aggregation: ['mean', 'max'];
    };
    lacunarity: {
      formula: 'variance_over_mean_squared';
      flat_required: true;
      nested_required_for: ['cas_f28', 'coherent_non_cas_7x4'];
      nested_scores: ['parent_factor', 'child_factor', 'joint_class'];
    };
  };

  results: Array<{
    taxonomy_id: string;
    hidden_accuracy: number;
    hidden_macro_f1: number;
    text_accuracy: number;
    text_macro_f1: number;
    hidden_over_text_accuracy_lift_pp: number;
    hidden_over_text_macro_f1_lift_pp: number;
    shuffled_label_mean_accuracy?: number;
    shuffled_label_max_accuracy?: number;
    flat_lacunarity?: number;
    nested_lacunarity?: {
      parent_factor?: number;
      child_factor?: number;
      joint_class?: number;
    };
    best_layer?: number;
    neighboring_layer_stability?: Record<string, unknown>;
    report_artifact: ArtifactDescriptor;
  }>;

  gate_evaluation: {
    verdict: 'PASS' | 'GREY' | 'FAIL' | 'BLOCKED';
    gate_rows: Array<{
      gate_id: string;
      gate_text: string;
      threshold: string;
      observed: string;
      status: 'pass' | 'grey' | 'fail' | 'blocked';
      supporting_artifact_ids: string[];
    }>;
    blocking_reasons?: string[];
  };

  proof_chips: Array<{
    chip_id: string;
    label: string;
    short_text: string;
    status: 'pass' | 'grey' | 'fail' | 'blocked';
    packet_row_anchor: string;
    supporting_artifact_ids: string[];
  }>;

  claim_language: {
    allowed_short_claim: string;
    allowed_reviewer_claim: string;
    forbidden_claims: string[];
    replication_status:
      | '20b_only'
      | 'six_model_replication_pending'
      | 'six_model_replication_complete';
  };

  integrity: {
    packet_hash: string;
    canonicalization: 'canonical_json_sha256';
    artifact_manifest: ArtifactDescriptor;
    log_anchor?: {
      log_seq?: number;
      previous_log_hash?: string;
      merkle_root?: string;
      worm_storage_uri?: string;
      anchored_at?: string;
    };
  };

  caveats: string[];
}

interface ArtifactDescriptor {
  artifact_id: string;
  artifact_type: string;
  content_sha256: string;
  byte_count?: number;
  storage_uri?: string;
  redaction_class?: string;
  created_at?: string;
}
```

### Required artifact list

The packet is not packet-ready unless it references, by hash:

- Pre-registration document.
- CAS taxonomy report for 40E and/or F28.
- Matched taxonomy reports.
- Text baseline reports.
- Shuffled-label control reports, including fixed seed list.
- Flat lacunarity table.
- Nested lacunarity table for F28 and the coherent 7 x 4 control.
- Split manifest.
- Scenario library and label manifests.
- Activation capture metadata.
- Model provenance record.
- Harness build/runtime manifest.
- Final gate-evaluation report with explicit `PASS`, `GREY`, `FAIL`, or `BLOCKED`.

## Proof-chip wording

Proof chips should be short enough for a verdict table, but each chip must anchor to a packet row. The chip should not summarize more strongly than the row supports.

### PASS chips

Use only when the relevant gate passed.

- **CAS lift over text:** "CAS hidden readout cleared the pre-registered lift gate over the exact text baseline."
- **CAS beats matched taxonomies:** "CAS outperformed every coherent same-size taxonomy on hidden readout accuracy or macro-F1."
- **Cleaner flat geometry:** "CAS flat lacunarity was at least 2x cleaner than the best coherent matched taxonomy."
- **Nested factorization:** "F28 beat the coherent 7 x 4 control on at least 2 of 3 nested lacunarity scores."
- **Scramble sanity check:** "Scrambled CAS labels stayed near chance and did not recover clean nested structure."
- **Same split, same activations:** "All compared taxonomies used the same split, activation source, and probe family."
- **Packet integrity:** "Packet and artifact hashes verify against the recorded manifest."

### GREY chips

Use when the result is mixed or claim-limited.

- **Readout-lacunarity split:** "CAS won one evidence channel but not both; uniqueness remains open under this control."
- **Matched taxonomy close:** "A coherent matched taxonomy approached CAS on at least one pre-registered metric."
- **Lacunarity exception:** "CAS readout was strong, but flat or nested lacunarity did not clear the pre-registered margin."
- **Replication pending:** "20B result is available, but cross-model matched-taxonomy replication is still pending."
- **Packet caveat:** "One or more artifacts are present but carry a caveat that limits the external claim."

### FAIL chips

Use when a coherent non-CAS matched taxonomy matches or beats CAS on the load-bearing gates.

- **Matched taxonomy matched CAS:** "A coherent non-CAS taxonomy matched or beat CAS on hidden readout lift and lacunarity."
- **Text leakage:** "A text-only classifier explained too much of the result for a hidden-state uniqueness claim."
- **Scramble failure:** "Scrambled labels exceeded the sanity ceiling or showed clean structure."
- **Control unfairness:** "A required same-split, same-activation, or same-probe condition was not satisfied."
- **Packet blocked:** "The packet is blocked because required artifacts or hashes are missing."

### BLOCKED chip

Use when no scientific verdict should be rendered.

- **Packet incomplete:** "Matched-taxonomy verdict blocked: required artifacts are missing or unverifiable."

## FAQ wording

These entries are for a compact FAQ drawer or documentation page, not for always-visible console copy.

### What is the matched-taxonomy control?

It compares CAS labels against fair non-CAS opponents: same model, same activations, same train/test split, same class count, same probe family, same text baselines, and same lacunarity scoring. The point is to test whether CAS is cleaner than ordinary semantic partitions, not just better than random labels.

### Why is this control needed if CAS already beats text?

Beating text shows that the model contains a recoverable hidden-state signal beyond the surface wording of the prompt. It does not by itself show that CAS is uniquely recovering a natural structure. A coherent same-size semantic taxonomy might also be readable from hidden states. This control tests that stronger objection directly.

### What does PASS mean?

PASS means CAS cleared the pre-registered gates against same-size coherent semantic controls on hidden readout lift and flat-plus-nested lacunarity. On GPT-NeoX-20B alone, it supports a 20B-specific specificity claim. It does not yet license a cross-model claim unless the same control passes on the full validated model set.

### What does GREY mean?

GREY means the result is mixed. CAS may win readout but not lacunarity, or win lacunarity but not readout. The allowed conclusion is that CAS is a strong model-internal taxonomy, while uniqueness versus matched semantic controls remains open.

### What does FAIL mean?

FAIL means a coherent non-CAS matched taxonomy matched or beat CAS on both hidden readout lift over text and flat-plus-nested lacunarity. The required conclusion is that this experiment does not show CAS is uniquely privileged over matched semantic taxonomies.

### Does PASS prove CAS is the model's real cognitive architecture?

No. PASS would be strong evidence that CAS is a cleaner matched taxonomy under this protocol. It does not prove consciousness, intent, universal cognitive structure, safety, or causal mechanism. Causal and localization claims require their own ablation, cover, and bridge evidence.

### Why include text-only baselines?

A high hidden-state score can be misleading if the surface text already solves the classification problem. The exact-fixture text baseline tests whether the labels are recoverable from prompt wording alone.

### Why include scrambled labels?

Scrambled labels are a sanity check. If random label permutations become highly readable or geometrically clean, the probe or data split is suspect.

### What is lacunarity here?

Lacunarity is a geometry cleanliness score computed as variance divided by mean squared on the taxonomy readout space. Lower values mean the factorization is cleaner under this scoring rule. For F28-style taxonomies, the packet also checks parent factor, child factor, and joint-class nested lacunarity.

### What should I tell a reviewer?

Tell the reviewer what the packet actually tested: whether CAS beat same-size, coherent semantic alternatives under a pre-registered, same-data, same-probe protocol. Then show the packet rows for lift over text, matched taxonomy comparison, lacunarity, nested factorization, controls, seeds, split hash, and artifact hashes.

## Audit Console display guidance

The Audit Console should stay operator-focused. Do not turn the main result page into a methods memo.

### Primary result row

Show:

- Verdict: `PASS`, `GREY`, `FAIL`, or `BLOCKED`.
- Scope badge: `20B gate`, `replication pending`, or `cross-model replicated`.
- One-sentence allowed claim.
- Four compact metric columns: CAS lift over text, best matched-control gap, flat lacunarity ratio, nested score wins.
- Proof chips.
- Evidence Packet status: `hashes verified`, `verification pending`, `mismatch`, or `blocked`.

### Main-page copy

Use one of these, depending on verdict:

- PASS: "CAS cleared the matched-taxonomy gate for this model under the pre-registered protocol."
- GREY: "CAS produced a mixed matched-taxonomy result; uniqueness remains open."
- FAIL: "A coherent matched taxonomy matched or beat CAS on the load-bearing gates."
- BLOCKED: "No matched-taxonomy verdict: required evidence is missing or unverifiable."

### Drawer/detail content

Move these to a drawer, hover, or FAQ:

- Formal definitions of lacunarity.
- Full taxonomy construction notes.
- Full seed list.
- Package versions.
- Complete class-balance tables.
- Reviewer playbook.
- WORM/Merkle explanation.
- Caveats and forbidden claims.

### Required warning visibility

Do not hide these only in FAQ or hover:

- The result is 20B-only and replication is pending.
- Any coherent matched taxonomy came within the pre-registered margin.
- Text-only baseline exceeded the allowed ceiling.
- Scrambled labels behaved unexpectedly.
- Packet hash verification failed.
- Required artifacts are missing.

## Pass/grey/fail claim language

### PASS: 20B gate only

Allowed short claim:

> On GPT-NeoX-20B, CAS beat same-size coherent semantic taxonomies on the pre-registered matched-taxonomy control.

Allowed reviewer claim:

> Under the same model, activations, split, balanced-logistic probe family, text baselines, shuffled-label controls, and flat-plus-nested lacunarity scoring, CAS produced stronger hidden-state readout lift and cleaner factorization than the matched non-CAS semantic taxonomies tested. This supports a 20B-specific CAS specificity claim; cross-model generalization remains pending.

Forbidden:

- "CAS is proven unique."
- "CAS is the model's cognitive architecture."
- "CAS beats all semantic taxonomies."
- "CAS is validated across model families" unless the six-model replication has passed.

### PASS: replicated model set

Allowed short claim:

> CAS beat matched semantic taxonomies across the validated model set.

Allowed reviewer claim:

> Across the validated model set, CAS beat same-size coherent semantic taxonomies on pre-registered hidden-readout lift and flat-plus-nested factorization gates. This supports the claim that CAS is not merely relabeling an ordinary semantic partition under the tested protocols.

Still forbidden:

- "Universal."
- "Irrefutable."
- "Safety certified."
- "Explains all model cognition."

### GREY

Allowed short claim:

> CAS is a strong model-internal taxonomy, but uniqueness versus matched semantic controls remains open.

Allowed reviewer claim:

> The matched-taxonomy control produced mixed evidence. CAS remained readable from hidden states, but it did not clear all pre-registered readout and lacunarity margins against coherent same-size semantic controls. The result supports continued study of CAS as a useful taxonomy, not a uniqueness claim.

Required caveat:

> Do not use "CAS is unique" or "CAS beats matched semantic taxonomies" for this result.

### FAIL

Allowed short claim:

> This experiment does not show CAS is uniquely privileged over matched semantic taxonomies.

Allowed reviewer claim:

> A coherent non-CAS matched taxonomy matched or beat CAS on the load-bearing hidden-readout-lift and lacunarity gates. The evidence still may show that CAS labels recover a useful semantic structure, but this control does not support a CAS uniqueness claim.

Required caveat:

> Treat CAS as one readable taxonomy among the tested semantic partitions unless later pre-registered evidence reverses this result.

### BLOCKED

Allowed short claim:

> No scientific verdict: the matched-taxonomy packet is incomplete or unverifiable.

Allowed reviewer claim:

> The control cannot be interpreted because required artifacts, hashes, split manifests, taxonomy manifests, or gate rows are missing or failed integrity verification. Re-run or repair the packet before making a PASS, GREY, or FAIL claim.

## What a senior researcher should read from the result

### If PASS

A senior researcher should read PASS as evidence for CAS specificity under a fair matched-control design. The important signal is not one high accuracy number. It is the conjunction of:

- CAS hidden readout remains well above the exact text baseline.
- Coherent same-size semantic controls do not close the readout-lift gap.
- CAS flat lacunarity is materially cleaner than the best matched control.
- F28 nested factorization beats the coherent non-CAS 7 x 4 taxonomy on at least 2 of 3 nested scores.
- Scrambled labels stay near chance and geometrically unclean.
- All of the above are tied to the same split, activation source, seeds, model provenance, and artifact hashes.

This would make the "ordinary semantic partition" objection weaker. It still would not establish causal mechanism, sparse localization, safety, consciousness, or universal model-family validity unless those separate gates are passed.

### If GREY

A senior researcher should read GREY as a useful diagnostic result, not a failed run. It identifies which evidence channel is carrying CAS and which channel is not. The follow-up question becomes specific: did the matched taxonomy win because it is genuinely structurally comparable, because the CAS fixture has leakage or imbalance, because lacunarity is underpowered, or because the CAS uniqueness claim is too strong for this evidence tier?

### If FAIL

A senior researcher should treat FAIL as a falsification of the uniqueness claim at this tier. It does not erase prior evidence that CAS labels are readable. It does mean the correct interpretation shifts to: CAS is one useful semantic taxonomy among alternatives unless a later, pre-registered control with stronger design resolves the failure.

### If BLOCKED

A senior researcher should ignore the scientific result and inspect the audit trail. Missing hashes, absent split manifests, unverifiable artifacts, or incomplete gate rows are not minor formatting defects; they prevent the result from being used as evidence.

## Acceptance checklist for this packet layer

- Every proof chip has a stable packet row anchor.
- Every load-bearing metric has an artifact hash and rerun path.
- PASS/GREY/FAIL is computed from pre-registered gates, not hand-written summary copy.
- 20B-only PASS is visibly distinguished from cross-model replicated PASS.
- Text-only, shuffled-label, and coherent matched-control results are shown beside CAS, not in a separate appendix only.
- Missing, partial, redacted, or degraded evidence is explicit.
- Packet integrity status is visible before any claim language is shown.
- Forbidden claims are listed in the packet and available to the Audit Console.

