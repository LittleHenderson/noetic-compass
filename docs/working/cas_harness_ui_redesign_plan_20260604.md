# CAS Harness Audit Console — Redesign Plan: "The Audit Bench"

**One synthesized direction.** All three inputs converge, so this plan locks the strongest concrete decision from each: the **3-zone app frame** (rail / center workspace / right evidence rail), a **horizontal stage ladder + plain-English transcript** as the progress surface, the **`isAuditResultCustomerSafe()`-gated verdict chip**, the enterprise/distributed/fleet machinery **moved off the first screen**, and the **10-dot Tree-of-Life mark as the cross-app brand anchor**. No API contract changes; every field name (`audit_id`, `status`, `verdict`, `confidence`, `evidence_packet_trace_id`, `provenance_chips[]`, `verifier_decision`, `audit_scope`, `lifecycle[]`) and claim word (`ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, `SUPPRESS`, `LICENSED`, `NOT LICENSED`, `OPEN`, `unavailable`, `present`, `verified`, `missing`, `failed`) is preserved verbatim.

> **BUILDER PREREQUISITE — read before editing.** The live `AuditConsolePage.tsx` and its full audit component set **do not exist on the current branch `wave5.5/harness-launch-declutter` (HEAD 8fa3cf8)**. They live on `launch/paid-security-sessions`, `launch/scoped-beta`, `codex/audit-console-declutter-hover`, and `codex/audit-console-visual-command-center`. The most complete tree (with `EnterpriseScalePlanCard`, `DistributedAuditRunPanel`, `FleetExecutorPanel`, `EvidencePacketVerificationPanel`, `AuditPopover`) is the one matching the inspected-surface brief — verify with `git ls-files "*AuditConsolePage.tsx"` and confirm the component set with `git ls-tree -r --name-only <branch> | grep atlas-viewer/src/components/audit` **before** branching. Land this redesign on the branch that is the actual launch-integration target. The verified honesty-gate logic below was confirmed against the live `casHarnessAudit.ts` and `AuditVerdictCard.tsx` in the `cas-audit-declutter` worktree.

---

## 1. CHOSEN SHELL + LAYOUT

Replace `PageShell`'s centered single-column card flow (used only for `/audit-console`) with a **full-width 3-zone CSS-grid app frame**. Login / License / Model-config keep `PageShell` and its 5-step flow nav untouched.

```
┌──────────────┬───────────────────────────────────────────┬─────────────────────┐
│  LEFT RAIL   │            CENTER — Audit Workspace        │  RIGHT — Evidence    │
│  (240px)     │            (fluid, min ~560px)             │  Rail (360px, sticky)│
│              │                                            │                     │
│ ◇ 10-dot mark│  ┌─ Run header: model · mode · status ──┐  │ ┌ VERDICT chip ───┐ │
│   CAS HARNESS│  └────────────────────────────────────────┘ │ │ ACCEPT / FLAG /  │ │
│              │  ┌─ Composer (target·mode·modules·[Run])─┐  │ │ SUPPRESS / NO    │ │
│ [+ New Audit]│  └────────────────────────────────────────┘ │ │ VERDICT YET      │ │
│              │  ── Stage ladder (horizontal) ─────────────  │ │ + confidence     │ │
│ RECENT RUNS  │  queued · running · verifying · anchoring·✓  │ └──────────────────┘ │
│  ▸ audit_1a2b│  ── Run transcript (plain-English log) ────  │ ┌ SCOPE ribbon ───┐ │
│  ▸ audit_9f0c│   • 12:04 validating model access…           │ └──────────────────┘ │
│  ▸ …         │   • 12:04 real Pythia weights ✓             │ ┌ Proof chips (6) ┐ │
│              │   • 12:05 running CAS modules…   ← active    │ │ rows · status   │ │
│ ── divider ──│   • 12:06 building evidence packet…          │ └──────────────────┘ │
│ ◐ scope chip │                                            │ ┌ Evidence Packet ┐ │
│ ⬡ license    │  ▸ Scale & fleet (advanced)  [link → tab]   │ │ open·verify     │ │
│ ? help ⚙ set │                                            │ │ [Inspect Atlas] │ │
└──────────────┴───────────────────────────────────────────┴─────────────────────┘
```

**Why this synthesis.** The left rail fixes the **split-identity problem** (the mark + `CAS HARNESS` wordmark now self-identify the product on every screen) and finally surfaces the already-called-but-never-listed `GET /sessions` history. The center column makes **one run the protagonist** — composer → ladder → transcript — directly killing the kitchen-sink vertical stack. The right rail isolates the **decision surface** (verdict + scope + proof + packet) so honesty rules have one consolidated home. The enterprise/distributed/fleet machinery leaves the customer's first screen entirely.

**Responsive collapse** (`max-width: 1100px`): left rail → hamburger drawer; right rail drops **below** the transcript but the **verdict + scope ribbon stay pinned directly under the stage ladder** so the result is never below the fold on mobile.

**Dark mode only** — the atlas-viewer app is dark-native (`bgDeep #020617`, slate ramp). No light-mode work in this pass.

---

## 2. COMPONENT PLAN — CREATE vs MODIFY

All paths under `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/` (apply on the launch-integration branch).

### CREATE

| File | Role |
|---|---|
| `components/shell/AuditAppFrame.tsx` | 3-zone CSS-grid frame (rail / center / right) + responsive collapse. Reuses `PageShell` backdrop + grid graticule. |
| `components/shell/AuditRail.tsx` | Left rail: brand mark, `+ New Audit`, Recent Runs (via existing `listCasHarnessAuditSessions`), scope chip, license chip, help/settings. |
| `components/shell/EvidenceRail.tsx` | Right rail orchestrator: verdict chip → scope ribbon → proof chips → packet actions → Inspect-in-Atlas. |
| `components/brand/TreeOfLifeMark.tsx` | Ported 10-dot SVG + `tks-breathe` animation (from `CompilerPage.tsx:3379-3407`). `size` + `animated` props. |
| `components/audit/AuditComposer.tsx` | Composer: target/mode/modules/run. **Absorbs** `ModelConnectionCard` + the command-bar button soup + BYOK field. |
| `components/audit/AuditRunHeader.tsx` | Calm one-row status header (folds in `AuditSessionSummaryCard` data: audit_id/model/mode/status). Replaces the giant animated H1. |
| `components/audit/AuditStageLadder.tsx` | Horizontal 6-node progress indicator. Consumes existing `progressSteps` + `lifecycleStatusFor()`. |
| `components/audit/AuditRunTranscript.tsx` | Plain-English append-only event log from `session.lifecycle[]`. **No `JSON.stringify`.** |
| `components/audit/ProofChipRail.tsx` | The 6 chips as a vertical status-row stack + "N/6 ready" counter. Lifts the grid out of `AuditVerdictExplainer`. |
| `components/audit/ScopeRibbon.tsx` | Persistent validation-vs-production + scoped-ACCEPT ribbon (promotes the buried `verifierBoundary()` string). |
| `components/audit/LicenseChip.tsx` | `LICENSED` / `NOT LICENSED` / `LICENSE UNKNOWN`. |
| `components/audit/MethodologyDrawer.tsx` | `?`-Help / "Why this verdict" drawer. Absorbs `AuditVerdictExplainer` prose + `EvidencePacketFlightRecorderFaq` + honesty legend. |
| `components/audit/AuditScaleFleetTab.tsx` | Off-screen home for `EnterpriseScalePlanCard` + `DistributedAuditRunPanel` + `FleetExecutorPanel` + the 6-button fleet row. |
| `components/ui/Disclosure.tsx` | Shared collapse primitive — **promote the inline Disclosure already landed in the dashboard declutter** (commits `47d71d4` / `9204a25`). Used by MethodologyDrawer + ScaleFleetTab. |

### MODIFY

| File | Change |
|---|---|
| `pages/AuditConsolePage.tsx` | Becomes a **thin orchestrator**: keep ALL state + handlers + API calls + the live-worker `useEffect` probe; replace the 8-section render body with `<AuditAppFrame>` wiring handlers into the new zones. **No API signature touched.** |
| `components/audit/AuditSessionProgress.tsx` | **Refactor + export** its `progressSteps`, `statusCopy`, `statusOrder`, `stepState`, and tone-style helpers so `AuditStageLadder` + `AuditRunTranscript` consume them. Keep the component + its test green for back-compat. |
| `components/audit/AuditVerdictCard.tsx` | Shrink headline `clamp(30px, 7vw, 64px)` → `clamp(20px, 3vw, 30px)` for the 360px rail. Keep `verdictTone`, `verdictLabels`, confidence meter, `'NO VERDICT YET'` fallback. **Add the `isAuditResultCustomerSafe`-gated ACCEPT chrome** (§5). Relocate action buttons into the packet block. |
| `components/audit/AuditVerdictExplainer.tsx` | Extract the 6-chip grid → `ProofChipRail`. Remaining prose (incl. Stage-19/20/21, `accepted_accuracy`, `Generation Readiness` strings) renders **only inside `MethodologyDrawer`**. Keep all logic functions. |
| `components/audit/ProvenanceChips.tsx` | Add a vertical status-row variant for the rail (chip ids/order/status unchanged). |
| `components/audit/EvidencePacketVerificationPanel.tsx` | Restyle compact (single pill + Disclosure). **Same derive logic** — WORM/S3 only from the `merged_packet_external_anchor` check; keep `statusLabel` wording incl. `unavailable`. |
| `components/cockpit/EvidenceDrawer.tsx` | Add a **human-readable summary tab as the default**; demote the raw `<pre>` JSON (`:967-1018`) to a secondary "Raw packet (JSON)" tab. |
| `lib/casHarnessAudit.ts` | Add two pure helpers: `lifecycleToTranscript(session)` (lifecycle entry → sentence) and `licenseStateFor(...)`. No change to `isAuditResultCustomerSafe`. |
| `lib/designTokens.ts` | Add `VERDICT_TONE`, `STAGE_*`, and `BRAND_DOT_TEAL = ['#5ce0d6','#38b2ac','#2a9d8f']` tokens; lift the duplicated inline rgba teal/amber/rose into shared tokens (fixes the inline-style drift). |
| `styles/global.css` | Add `@keyframes tks-breathe` (ported from `dashboard/src/index.css:184-187`) + a single `@keyframes cas-step-breathe` + `prefers-reduced-motion` guard. |
| `App.tsx` | Optional: gate `Run audit` enablement on license state. Route unchanged; `AuthGate` stays a no-op (license honesty handled at the UI chip, not by inventing a guard). |

### REUSED UNCHANGED (no contract edits)
`ModelConnectionCard.tsx` (inside composer), `EvidencePacketFlightRecorderFaq.tsx`, `AuditPopover.tsx`/`LiquidGlassTooltip.tsx`, `GlassPanel.tsx`, `PageShell.tsx` (kept for the flow pages), all cockpit panels, and the entire `casHarnessAuditApi.ts` / `atlasLiveApi.ts` / `evidencePacketVerification.ts` surface.

### Small adapters (the only new glue)
1. **`lifecycleToTranscript(session)`** — maps each `lifecycle[]` entry (`{message}`) + status transition to a plain sentence; falls back to `progressSteps[].description` when a message is absent. Antidote to the raw-JSON dump.
2. **Stage-label map** in `AuditStageLadder` — public node labels over the unchanged backend states (table in §4). No new backend states.
3. **`licenseStateFor(...)`** — derives `LICENSED` / `NOT LICENSED` / `LICENSE UNKNOWN` from the real entitlement signal the launch branches added (account model / invite redemption / Bearer token). Returns `UNKNOWN` (muted) when unresolvable — **never speculatively `LICENSED`**.

---

## 3. 10-DOT ANIMATED LOGO INTEGRATION

**Recreate, don't import** — the two apps share no component library, so port the markup rather than cross-app import.

- **Source:** `dashboard/src/pages/CompilerPage.tsx:3379-3407` — inline `<svg viewBox="0 0 800 1100">`, ten `<circle r="90">` at the canonical Tree-of-Life coords (400,55 / 110,190 / 690,190 / 400,400 / 110,545 / 690,545 / 400,690 / 110,870 / 690,870 / 400,1020), the `dotGrad` radial (`#5ce0d6 → #38b2ac → #2a9d8f`), the `dotShadow` filter, and the **staggered `tks-breathe 2.5s ease-in-out <delay> infinite alternate`** with per-dot delays `0s, 0.25s, … 2.25s` so the brighten wave ripples **top→bottom** through the formation. Pure CSS/SVG, no framer-motion.
- **Port the keyframe:** add `@keyframes tks-breathe` (currently only in `dashboard/src/index.css:184-187`) to `atlas-viewer/src/styles/global.css` — atlas-viewer has no 10-dot mark today (only single pulsing dots, `App.tsx:41-63`).
- **Placement (three sizes, one heartbeat):**
  1. **Left-rail header (~32px)** beside the `CAS HARNESS` wordmark — the always-visible primary brand anchor. This is the **only always-animating instance**. Doubles as the `+ New Audit` reset affordance (click the mark → reset workspace).
  2. **Empty-state (~96px, centered)** in the center workspace when no audit exists yet ("Start an audit") — echoes the `CompilerPage` empty-terminal behavior and bridges compiler ↔ harness identity.
  3. **Stage-ladder active node** reuses the **same `tks-breathe` heartbeat** (the breathing, not the SVG) so "currently happening" and the brand pulse are visibly one motion language.
- **Restraint guardrail** (matches the user's documented preference): breathing only — opacity `0.65 → 1` + soft drop-shadow. No comet sweep, no entrance flash (`tks-flash` stays unused here), no per-dot color cycling. The mark **breathes, it does not perform.** Gate behind `prefers-reduced-motion` (static dots when reduced).

---

## 4. PROGRESS-TIMELINE DESIGN + CALM MOTION

Two coordinated pieces; `AuditSessionProgress`'s `progressSteps` + `lifecycleStatusFor()` (`AuditConsolePage.tsx:244-270`) stay the **source of truth** — only layout and labels change.

### Horizontal stage ladder (`AuditStageLadder`)
Six nodes on a hairline track, mapped over the **unchanged** lifecycle union (`DRAFT|VALIDATING|RUNNING|EVIDENCE_PENDING|EVIDENCE_READY|COMPLETE|FAILED|SCAFFOLD_PENDING_RUNNER`):

| Public node | Backed by internal state | Tone |
|---|---|---|
| **Queued** | `draft` | muted |
| **Validating** | `validating` | amber (active) |
| **Running** | `running` | amber (active) |
| **Verifying** | `evidence_pending` (verdict awaiting trail) | amber (active) |
| **Anchoring** | `evidence_pending` + WORM/packet step | amber (active) |
| **Completed** | `complete` **AND** verdict present | teal |

Terminal overrides:
- **`runner_pending` (`SCAFFOLD_PENDING_RUNNER`)** → does **not** read as a normal stage; render an **amber interrupt pill on the Running node** ("Runner not connected"), preserving the honest "session exists but the real runner isn't connected" meaning.
- **`FLAG_FOR_HUMAN_REVIEW`** → terminal node is **`Needs human review` (amber)**, never the calm teal `Completed`.
- **`failed`** → reached node turns **rose**, ladder stops, transcript shows the terminal reason (reuse `failedStep`).

Reuse the existing `statusOrder` + `markerStyle`/`stepStyle` tone logic so teal/amber/rose semantics stay byte-identical.

### Run transcript (`AuditRunTranscript`)
Append-only, newest at bottom, derived from `session.lifecycle[]` via `lifecycleToTranscript`. Each row: `time · plain sentence · status glyph`. Example (all copy sourced from existing `progressSteps`/live-worker health):
```
●  12:04  Validating model access and runtime proof…
●  12:04  Real Pythia weights loaded ✓
◐  12:05  Running CAS modules against model output…   ← active row, subtle pulse
○   —     Building evidence packet (audit trail + anchor)…
```

### Calm motion
One keyframe, one rule: **only the single active node/row pulses** (2.5s, the logo's tempo) via `cas-step-breathe` (opacity `.72 ↔ 1`). Done nodes are solid teal; pending are muted; failed is rose. No spinners, no bounce. The hairline track fills left→right with `EASE_OUT_CUBIC`. Respect `prefers-reduced-motion` (the page already gates the heading wave on it) — under reduced motion the active node is solid with a static ring.

**Covers all 7 required UX beats:** (1) start = Run button; (2) begun = ladder leaves `Queued` + first transcript row; (3) moving through = ladder advances + transcript appends; (4) what's happening now = the single active node + active row text; (5) completion/failure/review = terminal node + verdict chip; (6) open packet = right-rail actions; (7) verdict without JSON = verdict chip + proof chips, never `<pre>`.

---

## 5. HONESTY-ENFORCEMENT POINTS

Every rule wires to logic that **already exists** — nothing fabricated, nothing softened.

| Rule | Now | After | Mechanism |
|---|---|---|---|
| **No raw ACCEPT without the product gate** | card shows ACCEPT regardless | Right-rail verdict chip | Clean teal ACCEPT renders **only if `isAuditResultCustomerSafe(summary) === true`** (`casHarnessAudit.ts:229-267` — requires `confidence > 0`, `model_proof === 'verified'`, real-weights runtime proof not fake, and for ACCEPT all 6 chips usable). Else: render the word `ACCEPT` with a **persistent amber "scoped — not a customer-production ACCEPT" band**, and the ladder terminal shows **`Needs human review`**. Mirrors the MEMORY Stage 9 40E rule. |
| **ACCEPT ≠ FLAG_FOR_HUMAN_REVIEW** | same chrome, equal weight (`AuditVerdictCard.tsx:206`, `clamp(...64px)`) | Distinct rail chrome | ACCEPT-safe = clean teal ring; ACCEPT-scoped = amber caveat band; FLAG = amber ring + explicit "HUMAN REVIEW REQUIRED" eyebrow; SUPPRESS = rose. Labels verbatim from `verdictLabels` (`FLAG_FOR_HUMAN_REVIEW → 'FLAG FOR HUMAN REVIEW'`). Color is never the only signal — always a status word. |
| **Validation vs production scope** | buried tooltip `!` chip + thin low-contrast banner | **Persistent left-rail scope chip + right-rail ScopeRibbon** under the verdict | Promote `verifierBoundary()` / `verifierScopeLabel()` strings ("Scope: Stage 9 40E validation packet" / "Boundary: this is a validation-packet verdict, not a live customer-production row") to always-visible. Driven by `verifier_decision` / `audit_scope`. Wording preserved exactly. |
| **LICENSED vs NOT LICENSED** | not surfaced; `AuthGate` is a no-op (`App.tsx:16-18`) | **Persistent left-rail license chip** | New `LicenseChip` via `licenseStateFor(...)`. Exact words `LICENSED` / `NOT LICENSED` (+ muted `LICENSE UNKNOWN` when unresolvable). When `NOT LICENSED`: `Run audit` disabled with inline reason; demo presets may still load read-only. |
| **Missing/OPEN controls must not imply pass** | grid present but easy to skim | Right-rail proof-row stack + "N/6 ready" counter | `control_proof` (and any chip) with status `missing`/`unavailable`/`failed`/`OPEN` renders muted/amber with the **literal status word** — never teal/green. Reuse `chipState`/`chipStatusLabel` (only `verified`/`present` → pass). |
| **Evidence Packet must not overclaim** | panel exists | Restyled, **same logic** | Before Verify: "Not checked" — does not assert tamper-evidence. After Verify: only `WORM retained` / `S3 verified` / `Hashes match` / `Mismatch` / `Unable to verify` from `EvidencePacketVerificationPanel`'s honest `statusLabel`; WORM/S3 only when `merged_packet_external_anchor` passes. Keep the "Final ACCEPT/SUPPRESS requires S3 re-read + Object Lock/WORM" line. |
| **Raw JSON not primary** | cockpit `EvidenceDrawer` JSON `<pre>` is the view | Human summary default; JSON secondary tab | Console surface shows verdict word + proof chips + human packet status only. Raw JSON stays a cockpit expert escape hatch via "Inspect in Atlas". |
| **UI never fabricates a verdict** | enforced server-side (`casHarnessAuditApi.ts:1023-1030`, `:1245-1254`) | Unchanged | Composer `Verify` and the Scale/fleet tab show connection/status only, never a verdict; distributed/fleet merge stays always `FLAG_FOR_HUMAN_REVIEW`. |

**Plain-language relabel map** (customer surface only; internal strings stay inside MethodologyDrawer/tooltips): `cas_readout` → "CAS readout (model-internal signal)" · `causal_proof` → "causal check (ablation)" · `control_proof` → "matched control" · `output_proof` → "output match" · `packet_proof` → "evidence packet" · live-worker chip → "live trace". The Stage-19/20/21 / `accepted_accuracy` / `Generation Readiness` vocabulary stays **only** in the drawer.

---

## 6. TIGHTLY-SCOPED FIRST PASS

Smallest change set that delivers a **branded shell + clean left rail + central workspace + visible progress timeline + verdict/proof panel + the animated mark**. Each step ships independently and keeps existing tests green.

**BUILD FIRST (the redesign-defining slice):**
1. **`TreeOfLifeMark.tsx` + `Disclosure.tsx` + token additions** (`BRAND_DOT_TEAL`, `VERDICT_TONE`, `STAGE_*`) + port `@keyframes tks-breathe`/`cas-step-breathe` to `global.css`. (Pure additive; risk-free.)
2. **`AuditAppFrame` + `AuditRail`** wrapping the **current page body unchanged** — instantly delivers CAS-Harness identity, the mark, Recent Runs (via existing `/sessions`), and the scope + license chips. (Biggest perceived win, lowest risk.)
3. **Split progress** → `AuditStageLadder` + `AuditRunTranscript` consuming the exported `AuditSessionProgress` constants. (The visible beginning→middle→end.)
4. **`EvidenceRail`** = verdict chip (with the `isAuditResultCustomerSafe` ACCEPT gate) + `ScopeRibbon` + `ProofChipRail` + compact packet panel. (The honest decision surface.)

**DEFER to a second pass:**
5. **`AuditComposer`** consolidation (absorb `ModelConnectionCard` + button soup) and **`AuditRunHeader`** — the current command center can keep working inside the frame until then.
6. **Move enterprise/distributed/fleet** into `AuditScaleFleetTab` (off the default view).
7. **`MethodologyDrawer`** + the full relabel pass + the `EvidenceDrawer` human-summary default tab.

Rationale: steps 1–4 produce a screenshot that already reads as "CAS Harness, clean, ChatGPT/Codex-clarity, honest verdict" without touching the API surface or the composer's connect/run logic. Steps 5–7 are decluttering polish.

---

## 7. TEST / TYPECHECK / PREVIEW PLAN

Run from `noetic-compass-scaffold/noetic-compass/atlas-viewer/` on the launch-integration branch.

- **Typecheck:** `npm run typecheck` (or `tsc --noEmit`) — the redesign must keep every preserved field name typed against `CasHarnessAuditSession`; a rename surfaces as a type error.
- **Unit tests (Vitest):** `npm test`. Keep green: `AuditSessionProgress.test.tsx` (exporting its constants must not break it), `AuditVerdictCard.test.tsx`, `AuditVerdictExplainer.test.tsx`, `ProvenanceChips.test.tsx`, `casHarnessAudit.test.ts` (the `isAuditResultCustomerSafe` gate). **Add** tests: `AuditStageLadder` state→label mapping (incl. `runner_pending` interrupt + FLAG→`Needs human review`), `AuditRunTranscript` lifecycle→sentence with **no `JSON.stringify`**, `ScopeRibbon` shows the boundary string when scope is a validation packet, `LicenseChip` returns `LICENSE UNKNOWN` when entitlement is unresolvable, and a verdict-chip test asserting ACCEPT renders the amber scoped band when `isAuditResultCustomerSafe === false`.
- **Lint:** `npm run lint`.
- **Local preview:** `npm run dev` (Vite), open `/audit-console`. Drive it via the two demo presets (20B validation packet / 20B review packet) to exercise the full ladder → transcript → verdict → proof → packet path with no live model. To preview the live-worker teal path, point `VITE_ATLAS_API_BASE_URL` at a reachable worker; otherwise the live-trace chip correctly shows amber/muted.
- **Visual check:** confirm the mark breathes top→bottom in the rail, the active ladder node pulses on the same heartbeat, and `prefers-reduced-motion` (DevTools → Rendering → Emulate CSS) freezes both.

---

## 8. ACCEPTANCE CRITERIA

- [ ] **User immediately knows they are in CAS Harness** — the 10-dot Tree-of-Life mark + `CAS HARNESS` wordmark sit in the left rail on every audit-console view (no longer dashboard-only).
- [ ] **Can start/view an audit without research clutter** — composer (target → mode → Run) is the only setup surface; enterprise/distributed/fleet machinery is off the first screen behind a `Scale & fleet` link; Recent Runs lists real `/sessions`.
- [ ] **Progress has a visible beginning / middle / end** — horizontal ladder `Queued → Validating → Running → Verifying → Anchoring → Completed` (+ `Needs human review` / failure terminals), with a plain-English transcript narrating the active step.
- [ ] **Clear verdict/status chip** — exact `verdictLabels` words with tone-differentiated chrome; ACCEPT-safe (teal) vs ACCEPT-scoped (amber band) vs FLAG (amber + review eyebrow) vs SUPPRESS (rose) are visually distinct; `'NO VERDICT YET'` before completion.
- [ ] **Obvious Evidence Packet access** — Open / Verify / Inspect-in-Atlas in the right rail; verify status uses honest `statusLabel` only, never claims WORM/S3 unanchored.
- [ ] **No raw JSON as the primary result** — console shows verdict + chips + human packet summary; raw `<pre>` JSON is demoted to a secondary cockpit tab.
- [ ] **The 10-dot animated mark appears in the shell** — breathing (opacity 0.65→1) top→bottom, restrained, `prefers-reduced-motion`-safe; the stage-ladder active node shares the same heartbeat.
- [ ] **Honesty gates hold** — clean ACCEPT only when `isAuditResultCustomerSafe()` is true; LICENSED vs NOT LICENSED is a persistent chip; missing/OPEN controls render the literal status word and never teal; scope boundary is always visible, not tooltip-only.
- [ ] **Feels closer to ChatGPT/Codex/Claude Code in clarity** — rails/rows/chips/timeline over cards, one spacious workspace, no marketing hero, deep methodology behind disclosures — while preserving CAS teal `#2dd4bf` / cyan `#22d3ee` / amber `#fbbf24` on slate, the glass surfaces, and Noetic Compass identity.
- [ ] **No API contract drift** — typecheck passes; all preserved field names and claim words intact; all existing audit tests green.

---

### Key file references (absolute paths, live copies in the `cas-audit-declutter` worktree; integration target is the launch branch)
- Audit page composition + all handlers + command center + fleet row + scope banner: `C:\tmp\cas-audit-declutter\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\pages\AuditConsolePage.tsx`
- Honesty gate (verified): `...\atlas-viewer\src\lib\casHarnessAudit.ts` — `isAuditResultCustomerSafe` L229-267 (confidence>0 + `model_proof==='verified'` + real-weights-not-fake + all-6-chips-for-ACCEPT); verdict/chip/status type unions L3-26.
- Verdict card (verified): `...\atlas-viewer\src\components\audit\AuditVerdictCard.tsx` — `verdictLabels` L29-32 (`FLAG_FOR_HUMAN_REVIEW → 'FLAG FOR HUMAN REVIEW'`), `verdictTone` L35, giant `verdictStyle` `clamp(30px,7vw,64px)` L80-85, `'NO VERDICT YET'` fallback L207.
- Verdict explainer (methodology surface): `...\atlas-viewer\src\components\audit\AuditVerdictExplainer.tsx` (Stage-19/20/21 + `verifierBoundary` strings → MethodologyDrawer).
- Lifecycle ladder source: `...\atlas-viewer\src\components\audit\AuditSessionProgress.tsx` (`progressSteps`, `statusCopy`, `statusOrder`, `failedStep` — export these).
- Proof chips: `...\atlas-viewer\src\components\audit\ProvenanceChips.tsx`; chip model + `CHIP_SPECS` in `casHarnessAudit.ts`.
- Evidence verify panel: `...\atlas-viewer\src\components\audit\EvidencePacketVerificationPanel.tsx` (honest `statusLabel`, WORM/S3 from `merged_packet_external_anchor`).
- Reused composer card: `...\atlas-viewer\src\components\audit\ModelConnectionCard.tsx`.
- Tokens (restyle home): `...\atlas-viewer\src\lib\designTokens.ts` (teal `#2dd4bf`, cyan `#22d3ee`, amber `#fbbf24`).
- Shell to keep for flow pages: `...\atlas-viewer\src\components\ui\PageShell.tsx`; base surface `...\GlassPanel.tsx`.
- Router + no-op `AuthGate`: `...\atlas-viewer\src\App.tsx` (`/audit-console` route; `AuthGate` L16-18).
- 10-dot logo source to port: `C:\tmp\cas-audit-declutter\noetic-compass-scaffold\noetic-compass\dashboard\src\pages\CompilerPage.tsx` L3379-3407; `@keyframes tks-breathe` at `dashboard\src\index.css:184-187`.