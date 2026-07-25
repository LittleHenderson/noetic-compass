# Gate 2 Item 3 — Semantic Authority Registry: Signature-Readiness Audit

## Status block

- **Addresses (does NOT close)**: Gate 2, item 3 of
  `docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:198-203` —
  *"Obtain owner approval for a field-level semantic authority registry before claim-bearing A/B work.
  Bind native symbols, normalized indices, semantic definition IDs, source/crosswalk hashes, D3DA and
  A124 as separate versions, World-to-CAS-Domain and World-to-CAS-Register as separate mappings, and
  native F28 versus CAS Drive-by-Register. Mark Acquisition and algebra profiles `unavailable` until
  explicitly reconciled."*
- **What this document does close**: nothing in roadmap item 3. It closes only the *readiness question* —
  "is the candidate registry safe to sign as written?" — with the answer **no**, plus a named, costed,
  zero-compute change set (§9) and an exact signature receipt to issue afterwards (§9(a)).
- **What it does NOT close**: item 3's primary clause is *"Obtain owner approval."* No owner approval was
  obtained and this audit recommends against granting it on the current file. Item 3 remains **OPEN**.
- **Date**: 2026-07-24
- **Subject artifact**: `docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json`
  (sha256 `A68D1B431C98F51DCD61007FBD75595659486B0092292CD92A49392D58AEEF54`, 275 lines, status field
  at `:4` = `CANDIDATE_RECONCILIATION_MANIFEST_NOT_OWNER_SIGNED`)
- **Compute**: none. This is a document-and-hash audit. No model was loaded, no probe was trained,
  no A/B arm was run.

### Claim-state line

This document contains **real** results (every hash, count, grep, and line citation below was
recomputed or re-read by me during this audit), **accepted-as-recorded** items (explicitly labelled,
two of them), **unavailable** items (four, each with the exact search that failed), and **open**
items (six of the eight roadmap bindings). Nothing here is **simulated**. Nothing here changes,
relaxes, or restates the claim status of any existing result. This audit **licenses nothing**; it
only reports whether a signature would be safe.

---

## 1. Verdict up front

**BLOCKED — do not sign the current file.**

Of the eight bindings roadmap item 3 names, **one** is fully satisfied, **one** is half satisfied, and
**six** are open. That, on its own, is sufficient for `BLOCKED`: signing a manifest that binds 1.5 of 8
would mark item 3 satisfied while six of its named bindings stayed unbound.

Separately, the registry itself carries no signature field. This is **not** a missing-mechanism problem.
A working owner-signature receipt mechanism already exists in this repository and is described in §9(a):
24 receipt templates under `docs/working/pcba_authority_receipts_needed_20260617/`, a finalizer
(`cas-forex/scripts/finalize_pcba_authority_receipt.py`) and a verifier
(`cas-forex/scripts/verify_pcba_semantics_receipt.py`) that hash-binds artifacts and exits nonzero while
unsigned. It has simply never been pointed at this registry. Cost to fix: one receipt file, no new schema.

The recommendation is **not** "abandon this registry." The registry's byte-level substrate is sound
and independently verified (Section 2). The recommendation is: apply the change set in Section 9,
then issue the §9(a) receipt against the revised file.

Specific blockers are listed in full in Section 10.

---

## 2. What is already sound (verified this session)

This is the strongest argument in the registry's favour, and it is now reproducible by command.

Re-run: `python docs/working/gate2_closure/verify_registry_bindings.py` (exit code 0 observed
2026-07-24).

| Assertion | Where the registry claims it | Independent result | Claim state |
|---|---|---|---|
| All 20 `sources[]` files exist and hash as recorded | registry `:13-154` | **20 of 20 MATCH, 0 mismatch** | real |
| D3DA vs A124: 20 of 40 Element definition strings differ | registry `:165` | recomputed **20 of 40** | real |
| D3DA vs A124: 8 of 28 Foundation definition strings differ | registry `:165` | recomputed **8 of 28** | real |
| `canon_subfoundations_28_defs.json` absent from `canon_index.json` | registry `:171` | canon_index version 1.2.0; file **not listed** | real |

Registry structure counts, re-read directly: 20 sources, 12 `known_conflicts`, 8-tier
`claim_bearing_precedence`, 25 `required_run_bindings`, 7 `future_agent_rules`.

Corroborating facts I checked independently, which confirm the registry is describing real problems
and not speculative ones:

- Native Element codes really are `A1`..`D10` and native Foundation codes really are `1a`..`7d` in the
  owner payload (`docs/working/tks_owner_locked_definitions_20260603.json`, keys
  `tks_40_elements` / `tks_28_foundations`, each record `{code, title, definition}`).
- Normalized `canon_elements_40.json` really uses a different scheme: 40 records keyed
  `{symbol, name, world, definition}` with symbols in the `A0`..`D9` range.
- The mod-10 algebra profile really is hardcoded in the shipped engine:
  `noetic-compass-scaffold/noetic-compass/cas-engine/src/ontology/operators.rs:100` doc comment
  *"composition maps (CO-a, CO-b) -> CO-((a+b) mod 10)"* and `:103` `let idx = (self.index() + other.index()) % 10;`.
- The two 22-Acquisition vocabularies really are different in kind:
  `TKS_v7.4_MASTER.tex:333` *"The **twenty-two Acquisitions** (A0 together with the D, W, and P chains)."*
  versus `canon_acquisitions_22.json` = 22 lexical records shaped
  `{"id":"1","name":"Recall","type":"Wisdom","foundation_id":"2"}`.

**Bottom line for this section**: every factual assertion the registry makes is currently true. The
problem is not accuracy. The problem is *coverage* and *granularity*.

---

## 3. Binding-by-binding checklist

Status tokens: `PRESENT` / `MISSING` / `MERGED-INCORRECTLY` / `UNSOURCED`.

| # | Required binding (roadmap `:199-203`) | Status | Registry field that satisfies it, or the gap | Citation |
|---|---|---|---|---|
| 1 | Native symbols (`A1-D10`, `1a-7d`) | **MISSING** | No per-symbol row exists anywhere in the file. Appears only as future-tense prose: *"store both source_symbol and normalized_index in every artifact"* | registry `:160`; whole-file read confirms 0 field rows |
| 2 | Normalized indices (`A0-D9`) | **MISSING** | Same gap. `symbol_indexing_scheme` exists as a *run-level field name* only, with no table of values | registry `:244`, `:160` |
| 3 | Semantic definition IDs | **MISSING** (partial at wrong level) | Source-level `id` strings exist for all 20 files; no per-Element / per-Foundation definition ID. The two version names proposed by the LICENSING program document appear **0 times** | registry `:15-153`; grep `TKS_OWNER_RAW_40_28_D3DA_V1` = 0, `TKS_DEPLOYED_NORMALIZED_40_28_A124_V1` = 0; names proposed at LICENSING `:220-221` |
| 4a | Source hashes | **PRESENT** | 20 `sha256` fields, all recomputed MATCH | registry `:13-154`; verified §2 |
| 4b | Crosswalk hashes | **UNSOURCED** | `tks_to_cas_crosswalk_sha256` is **required** but no crosswalk artifact exists to hash. Field is currently unsatisfiable | registry `:245`; see §7 and gap list |
| 5 | D3DA and A124 as separate versions | **PRESENT** | Two distinct `sources[]` entries with distinct hashes and explicit non-identity precedence text; reinforced by a P0 conflict and an agent rule | registry `:50-55`, `:56-62`, `:163-167`, `:269` |
| 6 | World-to-CAS-Domain and World-to-CAS-Register as **separate** mappings | **MISSING** | The collision is *documented* as `P0_SEMANTIC_AXIS`, but there are **zero mapping objects**. grep `world_to_domain` = 0, `world_to_register` = 0 | registry `:186-191` (conflict text); grep on registry |
| 7 | Native F28 vs CAS Drive-by-Register | **MISSING** | Conflict documented as `P1_SEMANTIC_AXIS` with a future-tense resolution; the two systems are never *named* as distinct entities in any machine-readable field | registry `:192-197` |
| 8 | Acquisition and algebra profiles marked `unavailable` | **MISSING** | The literal token `unavailable` appears **0 times** in the registry. Intent is present as prose prohibitions only. `required_run_bindings` has no `acquisition_profile` and no `algebra_profile` field. Proposed profile names appear 0 times | grep `unavailable` = 0; prose at registry `:89`, `:174-179`, `:198-203`; names proposed at LICENSING `:277-278` |

**Tally: 1 fully PRESENT (binding 5), 1 split PRESENT/UNSOURCED (binding 4), 6 MISSING.**

**Standing of `CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md`, stated so it is not
overread**: the controlling text for this item is the roadmap (`:198-203`). LICENSING is an *adjacent
program document*, not a normative authority — it does not appear in the registry's own
`claim_bearing_precedence` list (`:229-238`, eight role-descriptions, verified this session). Where this
audit cites LICENSING (`:220-221`, `:253-259`, `:277-278`) it is citing **proposed** identifiers and
**recommended** language, not binding requirements. The requirement in every case comes from the roadmap.

No binding is `MERGED-INCORRECTLY` *inside the registry itself* — the registry never asserts a wrong
identity. But bindings 6 and 7 are merged incorrectly **in live code that the registry governs**; that
is Section 5, and it is why signing-by-omission is dangerous.

---

## 4. Structural finding: the file is the wrong granularity for three bindings

The roadmap asks for a **field-level** registry (`:198`). The candidate is a **source-level** manifest:
one row per *file*, not one row per *symbol*.

`required_run_bindings` (registry `:239-265`) is the closest thing in the file to a contract, and it is
a **per-run** contract of 25 field names, not a per-symbol table. Bindings 1, 2, and 3 are per-symbol
facts. No source-level document can carry them, no matter how carefully written.

What is needed: **68 rows** — 40 Elements + 28 Foundations — each carrying native symbol, native symbol
scheme, normalized index, normalized symbol scheme, semantic definition ID, definition source ID, and
definition sha256.

**This is buildable, not blocked.** Every input already exists and is already hashed:
`tks_owner_locked_definitions_20260603.json` (both D3DA and A124 copies) supplies the 40 `A1`..`D10`
codes and 28 `1a`..`7d` codes with titles and definitions; `canon_elements_40.json` supplies the 40
`A0`..`D9` symbols with `world`. Generating the 68 rows is mechanical and zero-compute.

---

## 5. The two collisions are live in code, not hypothetical

The registry documents the World / Domain / Register collision at `:186-191`. Signing a manifest whose
only content on this point is *"this is a P0 conflict, resolve it later"* could be read downstream as
approval of the status quo. Here is the status quo.

**Instance A — `docs/working/lsa_artifacts_20260530/build_stage9_elements_fixture.v1.py`.**
The same `A/B/C/D` letter is used as a Domain *and* mapped to a Register:

- `:29` `_DOMAINS = ("A", "B", "C", "D")`
- `:30` `_DOMAIN_TO_REGISTER = {"A": "T", "B": "A", "C": "f", "D": "E"}`
- `:257` and `:259` emit **both** `element_domain` and `element_register` derived from that one letter.
- `:5` (docstring) conflates the terms outright: *"4 worlds/domains x 10 noetics = 40 element slots."*
- `:306` manifest `"position_definition": "4 original TKS worlds/domains x 10 noetics = 40 elements"`.
- `:55` `_TKS_TO_CAS_NOETIC = {10: "^0", **{i: f"^{i}" for i in range(1, 10)}}` — the `A1-D10` → `^0-^9`
  cyclic crosswalk, **inline, unversioned, unhashed, untested**.

> **Scope note on Instance A, added in revision.** This LSA file is a *copy* of the Stage-9 builder, and it
> is not the builder that produced the 20B claim fixture (see §5.1). It is real live code carrying the
> collision, so it stands as Instance A on its own terms; but the same collision also exists in the builder
> the 20B fixture actually names — `git show be9b4a31:noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage9_elements_fixture.py`
> at `:28` `_DOMAINS = ("A", "B", "C", "D")`, `:29` `_DOMAIN_TO_REGISTER = {"A": "T", "B": "A", "C": "f", "D": "E"}`,
> `:235` `register = _DOMAIN_TO_REGISTER[domain]`, `:257-260` emitting `element_domain` / `element_register`
> (all four lines read by me this session). The two copies differ by a one-line offset (`_DATE` is at LSA
> `:27` and at cas_probe `:28`). Both write `stage9_elements_{mode}_20260517.jsonl` (LSA `:282`), which is a
> *different artifact* from the 20260527 scenarios export discussed in §5.1.

**Instance B — `docs/working/mtc_f28_goemotions_20260615/`.**
`WORLD_TO_REGISTER = {"A": ("T","Transcendent"), "B": ("A","Analytical"), "C": ("f","Affective"), "D": ("E","Embodied")}`
is hardcoded in three separate scripts with no version and no hash:
`build_confirmatory_authoring_plan_tks_original.py:31`,
`build_confirmatory_authoring_plan_tks_original_delink.py:25`,
`gate2_confirmatory_tks_original_blind.py:32`.

Downstream, **8 authoring-plan JSON files each carry 2,800 rows** asserting the World→Register identity
(700 rows per register in each file), e.g.
`mtc_f28_goemotions_confirmatory_authoring_plan_20260615_tks_original.json` pairing
`register_definition` *"Mental world in original TKS"* with `register` *"Analytical"*.
None of the 8 files has any `crosswalk` or `scheme` field in its row schema (verified by key inspection).

> **Correction to the gathering pass**: the gathered material stated 5,600 rows / 1,400 per register.
> The verified count is **2,800 rows / 700 per register, per plan file, across 8 plan files.**

**Instance C — the repository-normative authority asserts the identity itself.**
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md:346`: *"TKS encoded both cross-products with the same 4-Worlds
axis. Reframed in secular universal terms as 4 Registers (T, A, f, E), this axis applies consistently
across all CAS primitives — both Noetic-level (10 × 4 = 40 Cognitive-State-by-Register combinations)
and Drive-level (7 × 4 = 28 Drive-by-Register combinations)."* No crosswalk version, no hash.

That file **is** in the registry's `sources[]` (`:43-48`, sha256 `CDA85C03…`, recomputed MATCH) with
precedence *"Operational CAS authority for Noetic names and definitions."* But the registry does **not**
record that this line is one of the two competing mappings named in conflict
`tks_world_to_cas_domain_and_register_collision`, nor that it is the origin of the F28-as-Drive-by-Register
conflation in conflict `tks_foundation_vs_cas_drive_position_mapping` (`:192-197`).

**An owner signature must decide**: is `CLARIFICATIONS.md:346` the *approved* World→Register mapping, or
*one hypothesis among several*? The registry currently permits both readings. That ambiguity is exactly
what a signature should not leave open.

### 5.1 Why this couples to the project's strongest live claim

> **Revision notice.** An earlier draft of this section asserted that the fixture behind the 95.625% claim
> "is Instance A above" and that the risk came from a builder deriving *both* `element_domain` and
> `element_register` from one letter. Both statements were wrong, and I had not opened the fixture when I
> made them. The corrected finding below is narrower in one direction and **stronger** in another: the
> register half never reached the labels, but the **World→Domain** half did, unversioned and unhashed, in
> every one of the 8,320 exported rows.

**Step 1 — identify the fixture from its own fields, not by filename.**
`docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:388` attributes the
95.625% / macro-F1 95.617% GPT-NeoX-20B layer-2 readout to *"Exact original Stage-9 role-bound fixture"*.
That fixture is
`D:/tksCAS-archive/gpt_neox_20b_stage9_original_40e_closure_20260527/stage9_original_40e_scenarios_20260527.json`,
opened and parsed by me this session. It carries its own provenance:

| Field | Value (read directly) |
|---|---|
| `schema_version` | `cas_harness_original_stage9_scenarios_export.v1` |
| `source_builder` | `noetic-compass-scaffold/noetic-compass/research/cas_probe/build_stage9_elements_fixture.py` |
| `source_commit` | `be9b4a3` |
| `created_at` | `2026-05-27T19:27:01.724043+00:00` |
| `axis` / `mode` / `scenario_count` | `element` / `pilot` / `8320` |
| `important_limit` | *"Scenario export only. This is not a probe result, ablation result, verifier verdict, or Evidence Packet."* |

`source_commit` `be9b4a3` resolves to real commit `be9b4a31bbb9b863d737fa5e8d2bcc9e98fe90b0`,
*"cas-probe: pre-register Stage 9 40 Elements"*, Sun May 17 06:08:42 2026 -0700 (`git log -1 be9b4a31`).
That is a **different path** from the LSA copy cited as Instance A. Claim state for the identification:
**real** (field-read, not inferred).

**Step 2 — the register mechanism did NOT reach the labels.**
I enumerated the key sets across all 8,320 scenarios. Every row has exactly:

- `metadata` keys: `axis`, `counterfactual_pair_id`, `legacy_domain`, `legacy_domain_name`,
  `legacy_element_code`, `legacy_element_name`, `legacy_element_noetic`, `pair_kind`, `paraphrase_family`,
  `source_profile`, `split`
- `expected_cas_axes` keys: `domain`, `element`, `noetic`, `operator`

**No `register` field exists anywhere in the export** (0 metadata keys containing the substring
`register`, across all 8,320 rows). The `_DOMAIN_TO_REGISTER` derivation present in the builder source was
not serialized into the fixture. Any claim that the 95.625% readout's label semantics carry a register
assignment is **refuted**, and this audit withdraws it.

**Step 3 — the live exposure is the other half of the collision, and it is in every row.**
`legacy_domain` is mapped to `expected_cas_axes.domain` across exactly four pairs, which I enumerated
exhaustively over the scenario set:

| `legacy_domain` | `legacy_domain_name` | `expected_cas_axes.domain` |
|---|---|---|
| `A` | Spiritual | `P` |
| `B` | Mental | `C` |
| `C` | Emotional | `E` |
| `D` | Physical | `O` |

That is the **World-to-CAS-Domain mapping** — roadmap binding 6's first half — applied to the labels
behind the project's strongest live claim, with **no crosswalk id, no crosswalk version, and no crosswalk
hash** in the export (`metadata` has no `crosswalk`, `scheme`, or `definition_sha256` key; see §6).
This *raises*, not lowers, the stakes on binding 6: the registry has zero mapping objects for a mapping
that is already load-bearing in a shipped label set. Claim state: **real**.

**Step 4 — what I am NOT saying.** I am not restating or reweighting the 95.625% claim. Its recorded
status is unchanged and stands as written at LICENSING `:388`: *"Genuine 20B hidden-state evidence. Final
packet remains `FLAG_FOR_HUMAN_REVIEW`; no standing `ACCEPT`."* Claim state: **accepted-as-recorded**.
I am also not asserting the mapping is *wrong* — `A/Spiritual → P` is consistent with the P ≻ C ≻ E ≻ O
descent. I am asserting it is **unbound**: nothing records which crosswalk produced it or at what hash.

**Step 5 — the procedural point for the owner, restated on the corrected evidence.** If the registry is
signed and later forces a different World→Domain crosswalk, the label semantics of this 8,320-row fixture
change, and the readout trained on it would need re-derivation. Flag the coupling **before** signature,
not after. That conclusion survives the correction; only its evidence changed.

**One thing I could not establish.** The builder named in `source_builder` writes
`stage9_elements_{mode}_20260517.jsonl` (LSA copy `:282`), not this `..._20260527.json` export, so an
intermediate exporter emitted `cas_harness_original_stage9_scenarios_export.v1`. I searched the working
tree for the literal `cas_harness_original_stage9_scenarios_export` across `*.py` and `*.json`
(`grep -rn --include=*.py --include=*.json`) and a repo-history search (`git log --all -S`) exceeded the
tool timeout without returning. The exporter is therefore **unavailable**; the fixture's own
`source_builder` / `source_commit` fields are what I rely on above, and they are recorded values, not
derived ones.

---

## 6. The provenance gap is also live

Registry conflict `sdg_and_capture_source_binding_gap` (`:204-209`, `P0_PROVENANCE`) states that fixtures
and captures are *"not yet uniformly bound to the exact semantic source hash and crosswalk hash that
produced their labels."* Confirmed by inspection:

- The Stage-9 **builder** — specifically the LSA copy
  `docs/working/lsa_artifacts_20260530/build_stage9_elements_fixture.v1.py`, which is the file these two
  counts were taken from — contains **zero** occurrences of `definition_source_id`, `definition_sha256`,
  `crosswalk_sha256`, or `symbol_indexing_scheme` (grep count 0 across the whole file).
- That same file's manifest block records provenance as
  `:307` `"source": "user-provided original TKS 40 Elements passage in chat on 2026-05-17"` —
  a **chat citation, not a hashed file**.
- **Framing correction (added in revision).** The two bullets above are facts about the LSA builder copy,
  not about the 20B claim fixture. The 20B fixture *does* record `source_builder` and `source_commit`
  `be9b4a3` and `source_profile: "exact_original_stage9_rolebound_fixture"` (§5.1). The substantive gap is
  unchanged and holds for **both**: neither carries a `definition_sha256`, a `crosswalk_sha256`, nor a
  `symbol_indexing_scheme`. Builder-and-commit provenance is not definition-and-crosswalk provenance.

One honest nuance in the other direction: the MTC F28 authoring plans **do** carry a partial binding —
`definition_source_sha256` = `5507bf6f85f63dc62847ea5f9018b6ad4471ca8acfe851a0f50d2b4ebbf6c88d`, which
matches the registry's `normalized_subfoundations_28_defs` entry (`:80`). So source binding is *partially*
solved there. What is still absent everywhere is the **crosswalk** id and hash, and the
`symbol_indexing_scheme`.

---

## 7. The missing piece that already half-exists

`docs/reference/tks_28_foundations_translation_key.md`
(sha256 `5D3E87025CBBA5A4AC7887063CF26603A2B16AF10A7E8FFFD0A597BFBB3444B7`, computed by me this session)
is the nearest thing the repository has to the crosswalk bindings 6 and 7 need. It contains:

- `:31-41` a position-matched CAS-Drive ↔ TKS-Foundation table (F1 Unity = 1st Foundation … F7 Purpose = 7th Foundation).
- `:45-51` a "Register-to-World correspondence" table binding `|T`=1st World, `|A`=2nd, `|f`=3rd, `|E`=4th.
- `:52` the doctrine that Instance A violates, quoted in full: *"The Register axis is orthogonal to the
  Domain axis; they do not collapse, but they share a high-to-low abstraction gradient that eases reading
  when both are specified."* The trailing clause is retained deliberately — it **softens** the doctrine
  this audit uses to indict live code, and an earlier draft truncated it at "do not collapse." with no
  ellipsis. "Orthogonal, not collapsing" still forbids deriving one axis from the other by lookup; the
  shared gradient explains why the conflation is easy to make, not why it is permitted.

Three defects block using it as authority as-is:

1. **It is not in the registry.** grep for `tks_28_foundations_translation_key` in the registry = **0 hits**.
   It carries no registry-bound hash, despite being cited as authoritative-adjacent by
   `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md:350`.
2. **It is incomplete by its own declaration.** `:66-70` "Scaffold status": *"Each entry below is a
   placeholder … TKS-source fields marked as pending."* It contains **14** `PENDING` markers, and its
   Population Plan (`:154`, step at `:160`) requires *"Review by Wakil"* before it can be authoritative.
3. **It binds World by ordinal position, not native letter.** It says "1st World", "2nd World" — joining it
   to native TKS `A/B/C/D` symbols still requires an unstated, unhashed `A=1st … D=4th` assumption.

Recommendation: register it as source #21 **with an explicit `completeness: scaffold` marker**, not as
authority. Promoting a self-declared placeholder to semantic authority is precisely the silent-remapping
failure the registry exists to prevent (registry `:5`).

Claim state for this artifact: **flagged-for-human-review**.

---

## 8. What signing this would commit you to — in plain language

**What the registry asserts, if you sign it as written.**

You would be putting your name to six things. First, that these **20 specific files, at these exact byte
hashes**, are the semantic sources of record for CAS Harness claim-bearing work — and every one of those
hashes is currently true, so this part is safe. Second, that **D3DA and A124 are two different versions of
the owner definitions**, not one file in two places, and that nobody may treat them as interchangeable.
Third, that **12 named conflicts are real and unresolved**, at the severities recorded. Fourth, an
**8-tier precedence order** (`:229-238`) saying which source wins when two disagree — with "owner-approved
signed semantic authority manifest" at the top, which is the slot this registry is trying to fill. Fifth,
that **25 named fields must be recorded on every claim-bearing run** (`:239-265`). Sixth, **7 standing
rules for future agents** (`:266-274`), including "do not remap A1-D10 to A0-D9 by position without a
tested crosswalk."

**What it would unblock.** Roadmap item 3 exists to gate roadmap item 4 — the six-arm TKS definition
experiment (`:204-206`: original raw TKS; deployed byte-different payload; approved rich normalized
definitions; compact CAS; coherent non-TKS ontology; shuffled/random nulls). A signed registry is what
makes arms 1 and 2 legitimately distinguishable (they *are* D3DA and A124) and what would make arm 3's
"approved" normalized definitions actually approved. Without a signature, item 4's results would carry
label semantics that nothing binds — the exact condition the Gate 2 exit clause calls *not independently
reproducible*.

**What signing would NOT commit you to — say this out loud before signing.** It would bind **no**
field-level symbol row, **no** crosswalk of any kind, **no** World-to-Domain mapping, **no**
World-to-Register mapping, **no** naming separation between native TKS-F28 and CAS Drive-by-Register, and
**no** `unavailable` status on the Acquisition or algebra profiles. Six of the eight things roadmap item 3
asks for would remain unbound **while item 3 appeared satisfied**. That is the single largest risk in this
audit.

---

## 9. Defects to fix BEFORE signature

All zero-compute. Ordered by blocking severity.

**(a) Issue an owner-signature receipt using the receipt mechanism the repository already has.**
Do **not** invent a new schema. An earlier draft of this document proposed a fresh ad-hoc `owner_signature`
object on the theory that no signing mechanism existed. That was false. Corrected finding:

*The existing mechanism, verified this session.*

| Component | Location | State I observed |
|---|---|---|
| Receipt templates | `docs/working/pcba_authority_receipts_needed_20260617/` | **24 files** (`ls` count), all unsigned |
| Receipt schema | e.g. `governance_regulatory_proof_claim__legal_review_signed.json` | 11 fields: `evidence_key`, `feature`, `approved`, `operator_id`, `signed_reason`, `signature`, `artifact_refs`, `artifact_hashes`, `created_at`, `receipt_hash` |
| Unsigned template values | same file, read in full | `approved: false`, `operator_id: ""`, `signed_reason: ""`, `signature: ""`, `artifact_refs: []`, `artifact_hashes: {}`, `receipt_hash: null`, `created_at: "2026-06-17T23:21:31.754478+00:00"` |
| Finalizer | `cas-forex/scripts/finalize_pcba_authority_receipt.py` | present; per `docs/working/cas_harness_production_todo.md:16590`, computes `receipt_hash` *"only after a reviewer has set `approved=true`, `operator_id`, `signed_reason`, and `signature`"* |
| Verifier | `cas-forex/scripts/verify_pcba_semantics_receipt.py` | present; per todo `:16590`, verifies *"against artifact SHA-256 hashes"* and *"intentionally exits nonzero on the current unsigned template and records `verified=false`"*; corroborated at todo `:16588` |

Claim state for the mechanism's existence: **real** (files listed and read by me). Claim state for the
finalizer/verifier *behaviour*: **accepted-as-recorded** — I read the two todo entries that describe them
and confirmed both script files exist; I did not execute either script this session (this is a
zero-compute audit).

*The exact receipt to issue, once §9(b)-(i) are applied.* Write
`docs/working/pcba_authority_receipts_needed_20260617/tks_cas_semantic_source_registry__owner_semantic_authority_signed.json`
in that same 11-field schema, populated as follows:

```json
{
  "evidence_key": "owner_semantic_authority_signed",
  "feature": "tks_cas_semantic_source_registry",
  "approved": true,
  "operator_id": "<owner id>",
  "signed_reason": "<scope sentence: which of roadmap bindings 1-8 this signature covers, and which it does not>",
  "signature": "<owner signature string>",
  "artifact_refs": [
    "docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json",
    "docs/reference/tks_28_foundations_translation_key.md",
    "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md",
    "docs/working/gate2_closure/verify_registry_bindings.py"
  ],
  "artifact_hashes": {
    "docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json": "<sha256 of the REVISED registry, recomputed at signing time>",
    "docs/reference/tks_28_foundations_translation_key.md": "5D3E87025CBBA5A4AC7887063CF26603A2B16AF10A7E8FFFD0A597BFBB3444B7",
    "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md": "<CDA85C03… — full value is in registry :43-48, recomputed MATCH this session>",
    "docs/working/gate2_closure/verify_registry_bindings.py": "<sha256 at signing time>"
  },
  "created_at": "<UTC timestamp>",
  "receipt_hash": null
}
```

Then run the finalizer to populate `receipt_hash`, and the verifier to confirm the artifact hashes still
match. Notes that make this concrete rather than aspirational:

- The registry hash **must be recomputed at signing time**, not copied from this audit. The current value
  `A68D1B431C98F51DCD61007FBD75595659486B0092292CD92A49392D58AEEF54` is the hash of the *unrevised*
  candidate and will not survive change set 9(b)-(i). Do not carry it forward.
- `artifact_hashes` is the field that solves the "signature binds a determinate byte sequence" problem the
  earlier draft tried to solve with a bespoke `signed_registry_sha256`. The existing schema already does
  this, and the verifier already checks it.
- `signed_reason` is the field that carries scope. Because six of eight bindings may still be open at
  signing time (§3), `signed_reason` must **enumerate what is and is not covered** in plain words, so no
  future reader can infer coverage the owner did not grant. This is the one field where a careless value
  would recreate the "item 3 appeared satisfied" hazard named in §8.
- **Naming caution.** The `pcba_authority_receipts_needed_20260617/` directory was built for the CAS Forex
  PCBA licensing gates, not for CAS Harness. Reusing the *schema and toolchain* is the point; the receipt
  above is a new file in that directory and must not be read as a PCBA gate. If the owner prefers, the same
  11-field schema can be written to a CAS-Harness-local path — the finalizer and verifier take a
  `--receipt` path argument (todo `:16588` shows the invocation form), so directory choice is free.
- Also add a pointer **inside the registry** to the receipt path, so a downstream check reading only the
  registry can find its approval record. This is the one small registry-side addition still required; it is
  a path string, not a new schema.

**(b) Add `fields[]` with 68 rows** (40 Elements + 28 Foundations), each carrying
`{native_symbol, native_symbol_scheme, normalized_index, normalized_symbol_scheme,
semantic_definition_id, definition_source_id, definition_sha256}`. Generate mechanically from
`tks_owner_locked_definitions_20260603.json` (both hashes) and `canon_elements_40.json`. Closes bindings
1, 2, 3.

**(c) Add `mappings[]` with two separate, versioned, explicitly-untested entries.** Not one. Two.
```
world_to_cas_domain    -> status: "unavailable"  (no artifact exists)
world_to_cas_register  -> status: "candidate"    artifact: docs/reference/tks_28_foundations_translation_key.md
                                                  sha256: 5D3E8702...  completeness: "scaffold"
                                                  world_binding: "ordinal_position_not_native_letter"
```
Closes binding 6 and makes the `tks_to_cas_crosswalk_sha256` field (`:245`) satisfiable — a run may
record `unavailable` rather than being forced to fabricate or silently skip.

**(d) Add `systems[]` naming the two F28 systems as distinct**: `native_tks_f28` (codes `1a`-`7d`) and
`cas_drive_by_register` (`F1`-`F7` × `T/A/f/E`), with the translation profile between them marked
`untested`. Closes binding 7. Source language: LICENSING `:253-259`.

**(e) Add `profiles[]`** with `acquisition_profile: "unavailable"` and `algebra_profile: "unavailable"`,
carrying the two identifiers proposed at LICENSING `:277-278` (`tks_v7_4_algebra_profile`,
`cas_engine_mod10_profile`). Closes binding 8 and puts the literal roadmap token in the file.

**(f) Register `docs/reference/tks_28_foundations_translation_key.md` as source #21** with sha256
`5D3E87025CBBA5A4AC7887063CF26603A2B16AF10A7E8FFFD0A597BFBB3444B7`, role
"candidate Foundation↔Drive and World↔Register crosswalk", precedence "scaffold; not authority; 14 PENDING
fields; requires owner population review before any claim-bearing use."

**(g) Adopt the version names** `TKS_OWNER_RAW_40_28_D3DA_V1` and `TKS_DEPLOYED_NORMALIZED_40_28_A124_V1`
on the two source entries (`:50-62`), matching LICENSING `:220-221`. Currently the registry separates the
two payloads correctly but leaves them unnamed, so downstream artifacts have no stable token to cite.

**(h) Add a note recording the ambiguity in `CAS_FOUNDATIONAL_CLARIFICATIONS.md:346`** — state explicitly
whether that line is the *approved* World→Register mapping or *one hypothesis*. Do not leave this to
inference.

**(i) Ship `docs/working/gate2_closure/verify_registry_bindings.py` as the standing check** and reference
it from the registry, so the signature's factual basis stays re-checkable after any file changes.

---

## 10. Readiness verdict

### `BLOCKED` — re-derived after correction, not carried forward

**How this verdict was re-derived.** Two corrections in this revision cut in opposite directions and both
were applied before re-scoring. (i) The former Blocker 1 — *"no signature mechanism exists"* — was **false
and is withdrawn**; a working, tested, hash-binding, fail-closed receipt mechanism already exists (§9(a)).
That removes the single most expensive blocker in the original list and downgrades the signature question
from *design work* to *one file*. (ii) §5.1's World→Domain finding is **new and worse than what the earlier
draft alleged**: an unversioned, unhashed World-to-CAS-Domain mapping is live in all 8,320 label rows behind
the project's strongest claim.

Re-scoring on the corrected evidence: the verdict is **unchanged at `BLOCKED`**, and it never rested on the
withdrawn blocker. It rests on the binding tally in §3 — the candidate binds 1.5 of the 8 things roadmap
`:198-203` names. Signing it would record item 3 as satisfied while six bindings stayed unbound. That is
independently sufficient, and the §5.1 correction reinforces rather than relieves it.

Blockers, in order, as they now stand:

1. **The signature mechanism exists but has never been applied to this registry.** *(Downgraded from
   "no mechanism exists" — that statement was false and is withdrawn.)* The registry itself defines no
   approval field: grep for `owner_signature`, `signed_by`, `signed_at`, `signed_registry_sha256`,
   `approval_scope`, `supersedes` in the registry = 0 hits each, and the only signature-adjacent string in
   the file is its own status at `:4`, `CANDIDATE_RECONCILIATION_MANIFEST_NOT_OWNER_SIGNED`. But the
   repository *does* hold a receipt mechanism: 24 templates under
   `docs/working/pcba_authority_receipts_needed_20260617/` on the 11-field schema
   `{evidence_key, feature, approved, operator_id, signed_reason, signature, artifact_refs, artifact_hashes,
   created_at, receipt_hash}`, with `cas-forex/scripts/finalize_pcba_authority_receipt.py` and
   `cas-forex/scripts/verify_pcba_semantics_receipt.py` (todo `:16588`, `:16590`). So approval **does** have
   a representation a downstream check could read; it has simply never been issued for this artifact.
   Severity: **low and mechanical** — one receipt file plus a path pointer in the registry.
   **Fix: 9(a).** Claim state: **real** (mechanism observed), **open** (never applied here).
2. **`tks_to_cas_crosswalk_sha256` (registry `:245`) is unsatisfiable** — no TKS↔CAS crosswalk artifact
   exists to hash. Signing a manifest that mandates a hash for a nonexistent file either blocks every
   subsequent run or invites a downstream agent to fabricate the field. **Fix: 9(c).** Claim state:
   **unavailable**.
3. **Six of eight bindings are MISSING** (1, 2, 3, 6, 7, 8 — Section 3). Signing and marking item 3
   complete would leave them unbound while appearing satisfied. **Fix: 9(b)(c)(d)(e).**
4. **Signing as-is would ratify the World/Domain/Register collision by omission.** The collision is live in
   source at `docs/working/lsa_artifacts_20260530/build_stage9_elements_fixture.v1.py:29-30`, in the same
   two constants of the builder the 20B fixture names (`be9b4a31:…/cas_probe/build_stage9_elements_fixture.py:28-29`),
   and in three MTC scripts; and it is asserted by the repository-normative file at
   `CAS_FOUNDATIONAL_CLARIFICATIONS.md:346`. **Strengthened in this revision:** the World→**Domain** half is
   not merely in source — it is serialized into labels. All 8,320 rows of
   `stage9_original_40e_scenarios_20260527.json` carry `legacy_domain` → `expected_cas_axes.domain`
   (`A/Spiritual→P`, `B/Mental→C`, `C/Emotional→E`, `D/Physical→O`) with no crosswalk id, version, or hash
   (§5.1). The World→**Register** half, by contrast, never reached that export — no `register` field exists
   in it — so the collision's live label exposure is one-sided, and it is the side roadmap binding 6 names
   first. **Fix: 9(c)(h).**
5. **The literal token `unavailable` appears 0 times** — a literal non-compliance with roadmap `:202-203`,
   not a wording preference. Prose prohibitions are not machine-readable and cannot fail a run closed.
   **Fix: 9(e).**
6. **The only crosswalk candidate is itself a scaffold** with 14 `PENDING` markers and an unstated
   ordinal-to-letter assumption. **Fix: 9(c)(f)** — register with `completeness: scaffold`, never as
   authority.

**Sequencing note, stated without rewriting any criterion.** Roadmap item 3 gates item 4. Item 4's arms 1
and 2 *are* D3DA and A124; arm 3 depends on normalized definitions whose `A0-D9` index scheme has no tested
crosswalk (registry `:156-161`, `P0_SEMANTIC_IDENTITY`). Starting item 4 before item 3 is signed would
produce results whose label semantics are unbound. I flag the dependency; I do not propose relaxing either
item. The Gate 2 exit clause stands as written.

**After the Section 9 change set is applied, the resulting file should be re-audited and would then be a
reasonable candidate for `READY_FOR_SIGNATURE`.** This audit does not pre-approve that revision.

---

## 11. Claim-state ledger

| Claim state | Items |
|---|---|
| **real** (recomputed by me, 2026-07-24) | 20/20 source-hash MATCH; 20-of-40 and 8-of-28 definition-string diffs; `canon_subfoundations_28_defs.json` absent from canon_index 1.2.0; registry sha256 `A68D1B43…`; translation-key sha256 `5D3E8702…`; all grep counts (`unavailable`=0, `world_to_domain`=0, `world_to_register`=0, `owner_signature`=0, four proposed names =0, translation key in registry =0); mod-10 at `operators.rs:100,103`; two distinct 22-Acquisition vocabularies; native codes `A1-D10` / `1a-7d`; normalized `A0-D9`; 8 plan files × 2,800 rows; Stage-9 builder lines `:5,29,30,55,257,259,306,307` |
| **accepted-as-recorded** (not re-verified by me) | `main_md_not_located` (registry `:222-227`, LICENSING §5.7 at `:282`) — I did not re-search for `main.md`; the 95.625% / macro-F1 95.617% GPT-NeoX-20B row and its `FLAG_FOR_HUMAN_REVIEW` status at LICENSING `:388` |
| **unavailable** | signature mechanism; TKS↔CAS crosswalk artifact; World-to-Domain mapping object; field-level symbol rows in the registry |
| **open** | roadmap bindings 1, 2, 3, 6, 7, 8 |
| **flagged-for-human-review** | completeness of `tks_28_foundations_translation_key.md`; whether `CAS_FOUNDATIONAL_CLARIFICATIONS.md:346` is the approved World→Register mapping or one hypothesis |
| **not-licensed** | nothing in this document licenses any claim |
| **simulated** | none |

### Search coverage limits (stated honestly)

- The `world_to_domain` / `WORLD_TO_DOMAIN` / `world_to_register` grep covered `docs/`, `cas-synthetic/`,
  `peer_review/`, and `book/`. A repo-wide version exceeded the tool timeout. Coverage of
  `noetic-compass-scaffold/`, `cas-engine/`, and `.claude/worktrees/` is therefore **incomplete** — I did
  not exhaustively prove absence outside the scanned trees. Six hits found, all `WORLD_TO_REGISTER`, zero
  `WORLD_TO_DOMAIN`.
- I did not re-search for `main.md`; I accepted the registry's recorded finding.

---

## 12. Scope fence

- This audit covers **registry signature readiness only**. It produced no model run, no probe, no A/B
  result, and no claim status change.
- It does **not** touch, cite, or build on the four prompt-injection experiments run earlier today.
  Prompt-injection detection is Gate 3 (`docs/working/cas_harness_production_todo.md:955`), not Gate 2.
- **Naming hazard for future readers**: `docs/working/mtc_f28_goemotions_20260615/gate2_confirmatory_tks_original_blind.py`
  refers to the 2026-06-15 MTC F28/GoEmotions confirmatory gate, **not** roadmap Gate 2. Do not cite that
  lineage as Gate 2 evidence.
- Prior to this session there was no Gate-2 evidence for item 3. I searched
  `CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md`, `cas_harness_executive_summary_20260630.md`,
  `cas_harness_synopsis_20260630.md`, and `cas_harness_cjt_rpm_assessment_20260630.md` for
  `semantic authority|registry|crosswalk|D3DA|A124|A1-D10|A0-D9`; the only hit was JSPACE `:615`
  "Build the direction and calibration registry", which concerns steering directions, not semantic
  authority. Claim state: **unavailable** prior to this session.

---

## Sources

Every file below was opened or hashed during this audit.

**Subject and controlling text**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json` (read in full, 275 lines; sha256 `A68D1B431C98F51DCD61007FBD75595659486B0092292CD92A49392D58AEEF54`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md` (Gate 2 section `:187-220`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md` (`:186-296`, `:388`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/cas_harness_production_todo.md` (grep only: `:954`, `:955`)

**Verification apparatus (this session)**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/gate2_closure/verify_registry_bindings.py` (re-run, exit 0)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/gate2_closure/registry_source_hash_verification_20260724.json`

**Normative CAS sources**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (`:340-352`; registry sha256 `CDA85C03…` recomputed MATCH)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/reference/tks_28_foundations_translation_key.md` (`:25-55`, `:64-72`, `:154-160`; sha256 `5D3E87025CBBA5A4AC7887063CF26603A2B16AF10A7E8FFFD0A597BFBB3444B7`)

**Definition payloads and normalized canon**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/tks_owner_locked_definitions_20260603.json` (D3DA)
- `C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/api/resources/tks_owner_locked_definitions_20260603.json` (A124)
- `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_index.json`
- `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_elements_40.json`
- `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_subfoundations_28_defs.json`
- `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_acquisitions_22.json`
- `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/TKS_v7.4_MASTER.tex` (`:333`)

**Live code carrying the collisions**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/lsa_artifacts_20260530/build_stage9_elements_fixture.v1.py` (`:5`, `:29-30`, `:55`, `:257-263`, `:306-307`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/mtc_f28_goemotions_20260615/build_confirmatory_authoring_plan_tks_original.py` (`:31-36`, `:125`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/mtc_f28_goemotions_20260615/build_confirmatory_authoring_plan_tks_original_delink.py` (`:25`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/mtc_f28_goemotions_20260615/gate2_confirmatory_tks_original_blind.py` (`:32`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/mtc_f28_goemotions_20260615/mtc_f28_goemotions_confirmatory_authoring_plan_20260615_tks_original.json` (+ 7 sibling `*authoring_plan*tks_original*.json` files, row-count and schema inspection)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/cas-engine/src/ontology/operators.rs` (`:100`, `:103`)

**Searched and found to contain no Gate-2 item-3 evidence**
- `docs/working/CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md` (`:615` only, unrelated sense of "registry")
- `docs/working/cas_harness_executive_summary_20260630.md`
- `docs/working/cas_harness_synopsis_20260630.md`
- `docs/working/cas_harness_cjt_rpm_assessment_20260630.md`
