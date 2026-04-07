# Noetic Compass — Progress Log

## Session 18: Production Readiness — LLM Integration, Validation Tooling, Deployment (April 7, 2026)

### Section 1: Real LLM Integration
- **`.env.example`** — API key template with NC_ prefix namespacing
- **`api/llm_connectors/base.py`** — Added `CAS_SYSTEM_PROMPT` (structured prompt for all 10 COs, 4 domains, 7 drives), token usage logging, retry failure logging
- **`api/llm_connectors/openai_connector.py`** — 60s timeout, max_tokens=4096, temperature=0.3
- **`api/llm_connectors/anthropic_connector.py`** — 60s timeout, total_tokens computed
- **`api/llm_connectors/google_connector.py`** — total_tokens computed
- **`api/pipeline/stages.py`** — dial_adjustment uses CAS_SYSTEM_PROMPT
- **`dashboard/src/pages/AssessmentPage.tsx`** — mock=false for real providers, live API warning indicator

### Section 2: Validation Study Tooling
- **`scenarios/sample_prompts.json`** — 50 diverse prompts (ethics, hiring, healthcare, AI safety, leadership)
- **`validation/run_baseline_study.py`** — Batch runner via TestClient, extracts operator/domain/drive scores, summary statistics
- **`validation/human_labeling_tool.py`** — CLI for collecting human CO ratings (0-10) and domain coherence ratings per prompt-response pair
- **`validation/correlation_analysis.py`** — Pearson r with p-value, Fisher z-transform 95% CI, Cohen's kappa inter-rater reliability, 4-section report
- **`validation/README.md`** — Updated with full study workflow documentation

### Section 3: Deployment Preparation
- **`docker-compose.yml`** — cas-api + cas-dashboard (nginx) + Redis stack
- **`Dockerfile.api`** — Multi-stage build (Rust cas-engine via maturin, then Python runtime)
- **`dashboard/Dockerfile`** — Node build + nginx serve
- **`dashboard/nginx.conf`** — SPA fallback + API proxy + static asset caching
- **`infra/render.yaml`** — Render Blueprint (API web service + static dashboard)
- **`docs/DEPLOYMENT.md`** — Docker Compose + Render deployment guide
- **`api/config.py`** — Added rate_limit_tier setting (community/professional/enterprise)
- **`api/middleware/rate_limit.py`** — Tiered rate limiting with per-API-key monthly caps (Community: 50/mo, Professional: 500/mo, Enterprise: unlimited) + token bucket RPM

### Verification
- Python: 60/60 tests pass (55 core + 5 validation)
- Vitest: 23/23 tests pass
- TypeScript: 0 errors

---

## Session 17: Anthropic Emotions Integration + Validation Framework (April 7, 2026)

### PART 2: Anthropic Functional Emotions Integration

#### HowItWorksPage — "The Science Behind It" Section
- **`dashboard/src/pages/HowItWorksPage.tsx`** — Added 9th section (`id='science'`, label "The Science") to SECTIONS array and new `<SectionReveal>` block with three glass-card mapping cards:
  - **CO-3 Concretization** ↔ Frustration/curiosity functional states
  - **CO-5 Differentiation** ↔ Evaluative internal states
  - **CO-8/CO-9 Expansion/Contraction** ↔ Exploration/exploitation trade-off
  - Closing note on independent convergence strengthening both frameworks

#### FaqPage — New FAQ Entry
- **`dashboard/src/pages/FaqPage.tsx`** — Added FAQ item at index 1: "How does CAS relate to Anthropic's research on AI emotions?" with two-paragraph answer explaining functional emotions alignment and link to `/how-it-works#science`

#### OperatorRadarChart Tooltips
- **`dashboard/src/lib/interpretations.ts`** — Appended functional emotions parallels to OPERATOR_DESC entries:
  - Index 3 (Concretization): frustration/curiosity parallel
  - Index 5 (Differentiation): evaluative states parallel
  - Index 8 (Expansion): exploration drive parallel
  - Index 9 (Contraction): exploitation/focus parallel

### PART 3: Validation Framework

#### New Files
- **`validation/README.md`** — Description, usage instructions (`make validate`)
- **`validation/conftest.py`** — sys.path setup for api module resolution
- **`validation/benchmark_fixture.json`** — Frozen reference input with expected composite range (60-90), Gold certification, 8 stages all passing
- **`validation/reproducibility_test.py`** — 2 tests:
  - `test_mock_determinism` — 5 identical /wrap calls produce identical composites
  - `test_benchmark_fixture` — composite within range, cert matches, 8 stages pass
- **`validation/sensitivity_test.py`** — 3 tests:
  - `test_dial_sensitivity` — dials=5 vs dials=8 produce different dial_values
  - `test_prompt_sensitivity` — different prompts produce different operator scores
  - `test_open_simplex_validation` — domain_averages > 0 and sum ≈ 1.0

#### Build System
- **`Makefile`** — Added `validate` target after `test-node`, added to `.PHONY`
- **`pyproject.toml`** — Added `validation` to `testpaths`

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- `pytest tests/` — 55/55 tests pass
- `pytest validation/` — 5/5 tests pass

---

## Session 16: Performance — Lazy Loading, Chunk Splitting, Query Tuning (April 7, 2026)

### Route-Based Code Splitting
- **`App.tsx`** — All 8 page imports converted to `React.lazy()` with `Suspense` fallbacks. Each page is now its own chunk, loaded only when visited. Outer Suspense shows full-screen spinner, inner Suspense (within AppShell) shows inline spinner during page transitions.

### Dynamic Export Library Imports
- **`ExportButton.tsx`** — Removed static imports of `exportPdf`, `exportDocx`, `exportMarkdown`, and `captureChartImages`. All four are now `await import()`'d inside `handleExport()`, so jspdf (177 KB gz), html2canvas, docx (105 KB gz), and file-saver are never loaded until user clicks Export.

### Vite Chunk Splitting
- **`vite.config.ts`** — Added `build.rollupOptions.output.manualChunks()` function splitting:
  - `vendor` (react/react-dom/react-router): 70 KB gz — cached across all pages
  - `recharts` + d3: 111 KB gz — only on chart pages
  - `query` (@tanstack/react-query): 13 KB gz
  - `export-pdf` (jspdf + html2canvas): 177 KB gz — on-demand only
  - `export-docx` (docx + file-saver): 105 KB gz — on-demand only
- Initial page load (login/assessment) now ~90 KB gz vs previous ~500 KB monolithic bundle.

### TanStack Query Tuning
- **`main.tsx`** — Added `staleTime: 60_000` (1 min) and `gcTime: 5 * 60_000` (5 min) to QueryClient defaults. Prevents unnecessary refetches when navigating between pages.
- **`useHealth.ts`** — Health poll interval increased from 30s to 60s, added `staleTime: 30_000` to prevent redundant health checks.

### Also Fixed
- **`CohortHeatmap.tsx`** — Fixed keyless `<>` fragment in `.map()` → `<Fragment key>` (prevents React console warning).

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- `npx vite build` — Success, 30 chunks generated with correct splitting

---

## Session 15: Cohort Analysis — 3 Bug Fixes (April 7, 2026)

### Fix 1: Color Inconsistency
- **`CohortHeatmap.tsx`** — Replaced private `cellColor()` with exported `cohortColor(pct, mode)` supporting both `'bg'` (semi-transparent for heatmap cells) and `'text'` (solid for table text) modes. Fixed keyless Fragment → `<Fragment key>`.
- **`CohortPage.tsx`** — Removed local `alignmentColor()`, now imports shared `cohortColor` from CohortHeatmap. Same breakpoints everywhere: 80%+ cyan, 60%+ emerald, 40%+ amber, below red.

### Fix 2: Bhattacharyya Coefficient Display
- **`CohortPage.tsx`** — Added "Bhattacharyya" column to pairwise comparison table with `(?)` tooltip explaining it. Value shown as 4-decimal coefficient, color-coded using `cohortColor(bc * 100, 'text')` so 0-1 range maps to the same visual scale as percentages.

### Fix 3: Operator Score Input Validation
- **`CohortPage.tsx`** — Added `validateScores()` function checking: exactly 10 values, all numeric, all in [0, 1] range. Errors shown inline below each profile input in red. Score input border turns red on error. Compare button disabled when any profile has validation errors.

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass

---

## Session 14: 40-State Heatmap Thermal Redesign (April 7, 2026)

### StateHeatmap.tsx — Full Rewrite
- **Thermal color mapping**: Replaced flat domain-colored cells with NASA/thermal-camera gradient (cold navy → deep teal → cyan → amber → hot white-gold). Smooth interpolation between 8 color stops using RGB lerp.
- **Ranked cell animations**: Top 5 highest-intensity cells pulse with warm `heat-pulse` glow; bottom 5 lowest pulse with cold `frost-pulse` blue glow.
- **Expanded grid**: 12-column layout (label + 10×40px cells + row summary). Cell size increased from 28px to 40px for visual impact.
- **Row summaries**: Mini horizontal progress bars on right side with percentage. Strongest row labeled gold, weakest red.
- **Column summaries**: Mini vertical progress bars below grid with operator averages. Strongest column gold, weakest red.
- **Hover tooltip**: Custom CSS tooltip positioned above hovered cell showing `{Domain}{CO-n} = {score}/10` with amber highlight.
- **Legend bar**: Full-width horizontal gradient bar (Cold → Moderate → Hot) with labeled endpoints.
- **Score overlay**: High-intensity cells (≥0.7) show their score directly on the cell face.
- **Performance**: All 40 intensities + rankings computed in single `useMemo` pass.

### index.css — New Animations
- `@keyframes heat-pulse` — warm box-shadow pulsing via CSS custom properties
- `@keyframes frost-pulse` — cold blue box-shadow pulsing
- `.animate-heat-pulse` / `.animate-frost-pulse` Tailwind utility classes

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- No regressions, existing ExplainPanel click behavior preserved

---

## Session 13: Bug Fixes — Severity Labels & Heatmap Interactivity (April 7, 2026)

### Fix 1: NCCS Sub-Score Severity Normalization
- **`dashboard/src/lib/translations.ts`** — `translateNccs()` was dividing all sub-scores by 100, but each has a different max weight (operator=25, domain=20, drive=20, pathway=10, inversion=15, social=10). Added `NCCS_MAX_WEIGHTS` constant and normalized each sub-score by its correct maximum. Without fix: all severities showed "Critical" (e.g., 18.5/100=18.5%). With fix: correct severities (e.g., 18.5/25=74% → "Good").

### Fix 2: StateHeatmap React Fragment Key & Interactivity
- **`dashboard/src/components/charts/StateHeatmap.tsx`** — Fixed two issues:
  1. Replaced keyless `<>` fragment in `.map()` with `<Fragment key={domain}>` — eliminated React "unique key" console error that could cause rendering/click handler issues.
  2. Added `chart-interactive` class to root div — enables the CSS hover rule that shows "Click a cell for details" hint text on hover.

### Verification
- 0 TypeScript errors, 23/23 Vitest tests pass, 0 console errors
- Browser-tested: severity labels now show correct values (Good/Excellent), heatmap cells clickable with ExplainPanel drill-down working

---

## Session 12: Four-Task Implementation (April 7, 2026)

### Task 4: Makefile (DevEx)
- **`Makefile`** — Root-level build orchestration with `make install`, `make dev`, `make test`, `make clean`, `make build`, `make lint`, `make help`. Auto-detects Unix vs Windows venv layout. Handles Rust (maturin), Python (venv/pytest), and Node (npm) toolchains.

### Task 1: Translation Layer (UX)
- **`dashboard/src/lib/translations.ts`** — 40+ term mappings from mathematical CAS language to business-friendly labels (e.g., "geodesic_distance" → "Alignment Match", "dci" → "Processing Balance", "inversion_resistance" → "Stability Under Pressure"). Score severity classifier (excellent/good/moderate/concern/critical). Conversion helpers: `geodesicToAlignment()`, `bhattacharyyaToSimilarity()`, `translateNccs()`, `translateDomainCoherence()`.
- **`dashboard/src/hooks/useTranslation.ts`** — React hook transforming WrapResult into fully translated `TranslatedResult` with business-named operators, drives, inversions, executive summary, top strength/risk.
- **`dashboard/src/components/shared/TranslatedMetric.tsx`** — Reusable metric display with severity dot, hover tooltip, and color-coded value.
- **`dashboard/src/components/shared/ExecutiveSummary.tsx`** — Stakeholder-facing overview card with one-liner, top strength, priority improvement, and translated sub-score breakdown.
- **`dashboard/src/components/charts/DomainCoherenceRadar.tsx`** — New Recharts radar chart for 4 processing domains with DCI indicator and drill-down explanation panel.
- **`dashboard/src/pages/AssessmentPage.tsx`** — Wired in Executive Summary, DomainCoherenceRadar, InversionAlert, and translated chart titles.

### Task 2: Inversion Explainability & Audit Trail
- **`api/pipeline/stages.py`** — New `InversionEvidence` dataclass with axis, severity, trigger reason, and transcript snippet. `_build_evidence()` generates per-axis explanations referencing operator pairs, domain hierarchy, drive scores, and RPM chains. `inversion_scan()` now accepts `llm_text` and `rpm_drive_scores` parameters for evidence generation.
- **`api/pipeline/runner.py`** — Passes LLM response text and RPM drive scores to inversion scan stage. Serializes evidence into stage result data.
- **`dashboard/src/api/types.ts`** — Added `InversionEvidence` and cohort types.
- **`dashboard/src/components/shared/InversionAlert.tsx`** — Interactive evidence cards grouped by flagged/stable. Each card expands to show "Why this was flagged" trigger explanation and related transcript snippet. Color-coded by severity (none/low/moderate/stealth/high).

### Task 3: Dynamic Benchmarking & Cohort Clustering
- **`api/models.py`** — New models: `CohortProfile`, `CohortCompareRequest`, `CohortDistance`, `CohortCluster`, `CohortCompareResponse`.
- **`api/routes/cohort.py`** — `POST /batch/compare` endpoint. Builds 40-dim CognitiveStateVectors from profiles, computes pairwise geodesic distance and Bhattacharyya coefficient via Rust engine, converts to alignment/similarity percentages, runs single-linkage clustering.
- **`api/main.py`** — Registered cohort router.
- **`dashboard/src/api/endpoints.ts`** — Added `postCohortCompare()` typed wrapper.
- **`dashboard/src/hooks/useCohort.ts`** — TanStack Query mutation hook.
- **`dashboard/src/pages/CohortPage.tsx`** — Full cohort analysis page with profile input form, cluster summary with color-coded badges, alignment heatmap, and pairwise comparison table.
- **`dashboard/src/components/charts/CohortHeatmap.tsx`** — NxN alignment heatmap with gradient cell coloring.
- **`dashboard/src/components/layout/Sidebar.tsx`** — Added "Cohort Analysis" nav item.
- **`dashboard/src/App.tsx`** — Added `/cohort` route.
- **`tests/test_cohort.py`** — 5 tests: two profiles, identical profiles (100% alignment), three profiles (3 pairwise distances), requires ≥2, bad simplex rejection.

### Test Results
- Python: **55/55 passed** (50 existing + 5 new cohort tests)
- Vitest: **23/23 passed**
- TypeScript build: **0 errors**

## Session 11: Re-Audit Fixes (April 7, 2026)

### Re-Audit Item 1: Python Version Cap
- **`cas-engine/pyproject.toml`** — `requires-python` updated from `<=3.13` to `<=3.14`

### Re-Audit Item 2: Remove Unused Drive Scores Emission
- **`api/llm_connectors/mock_connector.py`** — Removed `Drive Scores: {drives}` line from mock response text (no pipeline stage parses it)

### Re-Audit Item 3: Research Heuristic Labelling
- **`dashboard/src/lib/reportData.ts`** — `certLevel` now includes `(Research Heuristic)` suffix. Verdict includes footnote: "Certification levels are based on heuristic scoring under active empirical validation."

### Re-Audit Item 4: Fix 8 Failing Tests
- **`tests/conftest.py`** — `domain_averages` fixed from `[0.5]*4` (sum=2) to `[0.25]*4` (sum=1) for simplex compliance
- **`tests/test_assess.py`** — All payloads use simplex domain_averages. Relaxed `social_engineering` assertion to allow None. Added `test_assess_rejects_bad_simplex`
- **`tests/test_connectors.py`** — Removed obsolete `test_registry_mock_mode_overrides`. Added `test_mock_connector_deterministic` and `test_registry_explicit_provider_respected`
- **`tests/test_pipeline.py`** — Fixed `test_rpm_gate` for short text (a0 may be < threshold). Added `test_rpm_gate_longer_text`. Added `social_engineering=None` and `not_measured` assertions to `test_output_gate`

### Result: 50/50 tests pass

## Session 10: 6-Item Audit Fix (April 7, 2026)

### Audit Item 1 (CRITICAL): Replace Pipeline Placeholder Values
- **`api/pipeline/stages.py`** — Full rewrite:
  - `rpm_gate()`: Derives A0/drive scores from text analysis (word count, vocab richness, SHA-256 seeded RNG) instead of hardcoded 0.7/0.6/0.5
  - `domain_coherence()`: Derives domain averages from operator scores via `_DOMAIN_OPERATOR_MAP` P=[0,1,4], C=[2,3,7], E=[5,6], O=[8,9]. Normalizes to open simplex (sum=1, all>0)
  - `inversion_scan()`: Accepts real drive_scores/domain_averages from earlier stages instead of using [0.7]*7
  - `output_gate()`: Sets `social_engineering=None` (not measured), uses 0.5 neutral placeholders, tracks `not_measured` list
  - Added `_text_seed()` helper for deterministic SHA-256 hashing
  - Added `_normalize_to_simplex()` helper for open probability simplex normalization
  - Added `RpmGateResult.heuristic` flag, `NccsResult.not_measured` list

### Audit Item 2 (HIGH): Fix Simplex Math Validation
- **`api/models.py`** — Added `@field_validator("domain_averages")` that enforces sum≈1 (±0.01) and all values >0 (open simplex). Changed `manipulation_resistance`/`overton_drift_resistance` defaults from 1.0 to 0.5
- **`dashboard/src/test/mocks/handlers.ts`** — Fixed mock `domain_averages` from `[0.85, 0.8, 0.75, 0.7]` (sum=3.1) to `[0.274, 0.258, 0.242, 0.226]` (sum=1.0). Set `social_engineering: null`, `not_measured: ['social_engineering']`, composite 68.0/Silver
- **`dashboard/src/test/__tests__/AssessmentPage.test.tsx`** — Updated assertions from 76.0/Gold to 68.0/Silver

### Audit Item 3 (HIGH): Fix Provider Routing
- **`api/llm_connectors/registry.py`** — Removed `settings.mock_llm` global override. Now only `provider == "mock"` triggers MockLLMConnector. Explicit provider choice (openai, anthropic, google, meta) is always respected

### Audit Item 4 (MEDIUM): Fix Reproducibility + Provenance
- **`api/llm_connectors/mock_connector.py`** — Uses deterministic `hashlib.sha256(prompt)` seed instead of `random.uniform` for reproducible mock responses
- **`api/pipeline/runner.py`** — Added provenance dict (pipeline_version, engine, input_hash, connector, elapsed_ms, rpm_heuristic). Passes flat_drives and domain_averages between stages properly. Propagates not_measured to NccsResponse
- **`api/models.py`** — Added `NccsResponse.not_measured: list[str]`, `NccsResponse.social_engineering: float | None`, `WrapResponse.provenance: dict`

### Audit Item 5 (MEDIUM): Fix PyO3 Compatibility
- **`cas-engine/Cargo.toml`** — Upgraded PyO3 from 0.24 to 0.25
- **`cas-engine/pyproject.toml`** — Capped `requires-python = ">=3.10,<=3.13"`

### Audit Item 6 (MEDIUM): Reframe All UI Text
- **`dashboard/src/lib/reportData.ts`** — Title → "AI Cognitive Architecture Assessment (Research Prototype)". Deployment text → "MEETS HEURISTIC THRESHOLD — empirical validation pending"
- **`dashboard/src/lib/exportMarkdown.ts`** — Added research disclaimer section. Footer → "Research Prototype"
- **`dashboard/src/lib/exportPdf.ts`** — Header → "NOETIC COMPASS — RESEARCH PROTOTYPE". Footer → "Heuristic scores — empirical validation pending"
- **`dashboard/src/lib/exportDocx.ts`** — Header/footer reframed with research prototype language
- **`dashboard/src/api/types.ts`** — `NccsResult.social_engineering` → `number | null`, added `not_measured?`, `WrapResult.provenance?`
- **`dashboard/src/lib/interpretations.ts`** — Handles null `social_engineering` (filters from scoring arrays)
- **`dashboard/src/components/charts/SubScoreBreakdown.tsx`** — Filters unmeasured sub-scores from chart
- **`dashboard/src/pages/FaqPage.tsx`** — Replaced "AI Psychology" with "AI Cognitive Architecture Assessment Platform (Research Prototype)"
- **`dashboard/src/pages/HowItWorksPage.tsx`** — Replaced "psychological alignment" with "cognitive architecture integrity and coherence"

### Verification
- `npx tsc --noEmit` — 0 errors
- `npx vitest run` — 23/23 tests pass
- `npm run build` — Success

## Session 9: Assessment Report Export Feature (April 7, 2026)

### Added
- `src/lib/reportData.ts` — Pure data extraction: `extractReportData()` pulls operator scores, domain averages, drives, RPM, inversions, pipeline stages from WrapResult. Computes top 3 strengths/vulnerabilities, deployment recommendation, one-paragraph verdict.
- `src/lib/exportMarkdown.ts` — Markdown export with ASCII tables, GitHub/Notion compatible. Uses `file-saver` for download.
- `src/lib/chartCapture.ts` — `captureChartImages()` uses `html2canvas` to capture chart sections as base64 PNGs from hidden DOM container.
- `src/lib/exportPdf.ts` — jsPDF-based A4 PDF generation with dark theme, teal section headers, embedded chart images, alternating-row tables, NCCS score highlight, certification badge, page footers.
- `src/lib/exportDocx.ts` — `docx` package Word document generation with proper heading styles, bordered tables, embedded chart ImageRuns, page numbering footer.
- `src/components/shared/HiddenReportCharts.tsx` — Off-screen chart renderer (all 7 charts at fixed 600px width) for html2canvas capture. Mounted only during export.
- `src/components/shared/ExportButton.tsx` — Dropdown button (PDF / DOCX / Markdown) with loading spinner, outside-click dismiss, dark glass-card styling.

### Modified
- `src/pages/AssessmentPage.tsx` — Added ExportButton after results render
- `src/pages/DetailsPage.tsx` — Added ExportButton next to Re-run button in header

### Dependencies Added
- `jspdf` + `html2canvas` — PDF generation (render DOM → canvas → PDF pages)
- `docx` — Programmatic DOCX generation
- `file-saver` + `@types/file-saver` — Cross-browser saveAs() download

### Report Sections (all formats)
1. Header (branding, date, model, assessment ID, CAS v7.4)
2. Executive Summary (NCCS score, cert level, verdict, strengths, vulnerabilities, deployment recommendation)
3. Cognitive Operator Profile (10 operators + involution pair balance)
4. Domain Coherence (4 domains + DCI + weakest domain)
5. Core Drive Integrity (7 drives, flagged if < 50%)
6. RPM Analysis (completeness + broken chains)
7. Inversion Analysis (7 axes + stealth resistance)
8. Pipeline Trace (8 stages pass/flag/block)
9. Footer (branding, CAS v7.4, Confidential, page numbers)

### Verified
- `npm run build` — 0 TypeScript errors
- `npx vitest run` — 23/23 tests pass (no regressions)

## Session 8: How It Works + FAQ Pages (April 6, 2026)

### Added
- `src/hooks/useScrollSpy.ts` — IntersectionObserver-based scroll-spy hook for sticky nav highlighting
- `src/components/shared/SectionReveal.tsx` — viewport-triggered fade-in + slide-up wrapper
- `src/pages/HowItWorksPage.tsx` — 8-section premium documentation page:
  - The Big Picture (8-stage pipeline diagram)
  - 10 Cognitive Operators (grid with involution pairs & self-duals)
  - 4 Processing Domains (vertical descent + feedback loop)
  - 7 Core Drives (cards with inversion pair indicators)
  - RPM Prerequisite Model (section-retraction chain, one-directional)
  - Inversion Detection (7 axes explained)
  - NCCS Scoring (stacked bar weights + certification tiers)
  - The Math (Fisher-Rao, open simplex, geodesic distance, admissibility)
- `src/pages/FaqPage.tsx` — 10-question accordion with animated expand/collapse and chevron rotation
- Sidebar nav entries for How It Works (book icon) and FAQ (question-mark icon)
- Routes `/how-it-works` and `/faq` in App.tsx
- CSS: `section-reveal`/`section-revealed` animation, `accordion-open`/`accordion-close` transitions, `scroll-spy-active` indicator

### Reuses
- All constants: OPERATOR_LABELS, DOMAIN_LABELS, DRIVE_LABELS, INVERSION_AXIS_LABELS, NCCS_WEIGHTS, PIPELINE_STAGES, CERTIFICATION_THRESHOLDS
- Colors: CERT_COLORS, DOMAIN_COLORS, DRIVE_COLORS

### Verified
- `npm run build` — 0 TypeScript errors
- `npx vitest run` — 23/23 tests pass (no regressions)

## Session 7: Interactive Assessment Readouts (April 6, 2026)

### Interactive Explanation Panels
- Created `src/components/shared/ExplainPanel.tsx` — reusable slide-down panel with close button, dark glassmorphism style
- Created `src/lib/interpretations.ts` — VP-friendly text generators for all 7 chart types + pipeline stages
- Added CSS `animate-slide-down` keyframe animation and `chart-interactive` / `chart-hint` utilities to `index.css`

### Chart Component Updates (all 7 + StageTimeline)
- **NccsGauge**: click → shows summary, top strength, biggest gap, recommendation. Accepts optional `nccs` prop.
- **SubScoreBreakdown**: click bar → shows sub-score description, weight contribution, verdict
- **OperatorRadarChart**: click → expands full operator list with descriptions + involution pair balance status
- **StateHeatmap**: click cell → shows domain×operator state interpretation with intensity rating
- **CoreDriveTree**: click bar → shows drive description, score, and inversion pair tension note
- **RpmGraph**: click drive row → shows prerequisite chain status with flowing/blocked indicators per node
- **InversionMap**: click → expands all 7 axes with descriptions + stealth resistance assessment
- **StageTimeline**: click stage → shows what happened, description, and pass/fail status

### Page Updates
- Updated `AssessmentPage.tsx` — passes `nccs` to NccsGauge, StageTimeline is now clickable
- Updated `DetailsPage.tsx` — passes `nccs` to NccsGauge

### Verification
- TypeScript: 0 errors
- Tests: 23/23 passing
- Build: successful

## Session 6: Phase 3 — Frontend Dashboard (April 6, 2026)

### Backend Enhancement (Pre-requisite)
- Added `drive_scores`, `involution_balances`, `axis_scores` to pipeline stage data in `api/pipeline/runner.py`
- Enables chart components to render full CAS visualization data

### T3.0: Vite + React + TypeScript Scaffold
- Created React 18 + TypeScript project via `create vite@latest --template react-ts`
- Installed: react-router-dom, @tanstack/react-query, recharts, tailwindcss v4, @tailwindcss/vite, zustand
- Dev deps: vitest, jsdom, @testing-library/{react,jest-dom,user-event}, msw
- Configured vite proxy (`/api` → `localhost:8000`), Tailwind v4 CSS import

### T3.1: TypeScript Types + Constants
- `src/api/types.ts` — 12 types mirroring api/models.py (NccsResult, WrapResult, etc.)
- `src/lib/constants.ts` — OPERATOR_LABELS[10], DOMAIN_LABELS[4], DRIVE_LABELS[7], INVERSION_AXIS_LABELS[7], NCCS_WEIGHTS, PIPELINE_STAGES[8]
- `src/lib/colors.ts` — Certification colors, domain/drive/involution pair palettes

### T3.2: API Client Layer
- `src/api/client.ts` — fetch wrapper with JWT from localStorage, typed ApiError
- `src/api/auth.ts` — getToken/setToken/clearToken/isAuthenticated
- `src/api/endpoints.ts` — typed wrappers: postWrap, postAssess, postBatch, getConfig, putConfig, getHealth

### T3.3: TanStack Query Hooks + Zustand Store
- `src/hooks/` — useWrap (saves to history), useAssess, useBatch, useConfig (query+mutation), useHealth (30s refetch)
- `src/stores/historyStore.ts` — Zustand + persist middleware, localStorage-backed, max 100 records

### T3.4: Shared Components
- Card, LoadingSpinner, ErrorBanner (with status code labels), CertBadge

### T3.5: Chart Components (7 visualizations)
- NccsGauge — semicircular Recharts PieChart, certification-colored
- SubScoreBreakdown — horizontal BarChart, 6 NCCS sub-components with weight labels
- OperatorRadarChart — 10-spoke RadarChart (CO-0 to CO-9)
- StateHeatmap — CSS grid 4×10 (domains × operators), intensity-colored cells
- CoreDriveTree — 7 horizontal bars, drive-colored
- RpmGraph — custom SVG, 7 rows × 4 nodes (A0→Dn→Wn→Pn), colored by satisfaction
- InversionMap — 7-axis RadarChart with stealth resistance display

### T3.6: Layout Components
- AppShell — flex layout with 240px sidebar, mobile hamburger
- Sidebar — nav links + health indicator dot
- Header — title, auth status, logout

### T3.7: AssessmentPage
- Text input + provider select + submit
- Full chart rendering on success: gauge, sub-scores, radar, heatmap, drives, RPM, inversions
- Stage timeline with status indicators

### T3.8: Dial Components
- `src/lib/validation.ts` — validateDials: range [3,9] + involution divergence ≤4
- DialSlider — range input (3-9) with operator label
- DialPanel — 10 sliders grouped by self-dual/involution pairs, inline validation, save/reset

### T3.9: ConfigPage
- Loads config via useConfig, renders DialPanel, save/reset with success feedback

### T3.10: HistoryPage + DetailsPage
- History table with timestamp, text excerpt, composite, certification, link to details
- Details view with all charts, full text, stage timeline, raw JSON toggle, re-run button

### T3.11: Router + LoginPage
- BrowserRouter: / (Assessment), /history, /config, /details/:id, /login
- JWT token input + connect flow, auth guard redirects to /login

### T3.12: Tests (23 passing)
- validation.test.ts (8): dial range, involution divergence, edge cases
- NccsGauge.test.tsx (3): renders composite for Gold/Fail/Platinum
- DialPanel.test.tsx (5): slider count, save/reset, disabled while saving
- AssessmentPage.test.tsx (2): form render, submit flow with MSW
- api.test.ts (5): auth store, JWT header attachment, 401/422 error handling

**Total: 42 Rust + 47 Python + 23 Frontend = 112 tests passing. PHASE 3 COMPLETE.**

## Session 5: Phase 2 — API Gateway + LLM Connectors (April 6, 2026)

### Task 2.1: PyO3 Bindings (maturin)
- Added `pyo3` dependency (optional feature `python`) to cas-engine/Cargo.toml
- Created `cas-engine/src/python_bindings.rs` exposing all core types to Python:
  - CognitiveOperator, Domain, CoreDrive, CognitiveStateVector, DialConfig
  - OperatorScores, DomainCoherence, InversionScanner, RpmProfile
  - compute_nccs(), geodesic_distance(), bhattacharyya_coefficient()
- Created `cas-engine/pyproject.toml` for maturin build
- Note: Python 3.14 requires `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1`

### Task 2.2: Python Project Scaffold
- `api/config.py` — pydantic-settings (env-based: API keys, JWT, rate limits, mock mode)
- `api/models.py` — Pydantic schemas: AssessRequest, WrapRequest, BatchRequest, NccsResponse, DialConfigSchema, etc.
- `api/errors.py` — DialViolationError (422), ScoringError (422), LLMError (502), PipelineStageError (500)
- `api/main.py` — FastAPI app with CORS, lifespan, middleware stack, exception handlers
- `requirements.txt`, `pyproject.toml`

### Task 2.3: LLM Connectors (5 providers + mock)
- `api/llm_connectors/base.py` — BaseLLMConnector ABC with async retry + exponential backoff
- `api/llm_connectors/openai_connector.py` — OpenAI SDK (GPT-4)
- `api/llm_connectors/anthropic_connector.py` — Anthropic SDK (Claude)
- `api/llm_connectors/google_connector.py` — Google GenAI SDK (Gemini)
- `api/llm_connectors/meta_connector.py` — Meta/Llama via OpenAI-compatible API
- `api/llm_connectors/mock_connector.py` — Synthetic CAS-formatted responses for testing
- `api/llm_connectors/registry.py` — Factory with NC_MOCK_LLM env var override

### Task 2.4: 8-Stage Wrap Pipeline
- `api/pipeline/stages.py` — All 8 async stages calling Rust engine via PyO3:
  1. input_analyzer → AnalyzedInput
  2. rpm_gate → RpmGateResult (Rust RPM)
  3. dial_adjustment → AdjustedInput (Rust DialConfig, 422 on violation)
  4. base_llm_call → LLMResponse
  5. operator_scoring → OperatorScoreResult (Rust OperatorScores)
  6. domain_coherence → DomainCoherenceResult (Rust DCI)
  7. inversion_scan → InversionResult (Rust InversionScanner)
  8. output_gate → NccsResult (Rust compute_nccs)
- `api/pipeline/runner.py` — WrapPipelineRunner orchestrator

### Task 2.5: API Routes
- `POST /assess` — direct assessment from pre-scored input (bypasses LLM)
- `POST /wrap` — full 8-stage pipeline with LLM call
- `POST /batch` — batch assessment with async concurrency + semaphore
- `GET/PUT /config` — dial configuration (422 on violations)
- `GET /health` — service status

### Task 2.6: Middleware
- `api/middleware/auth.py` — JWT Bearer token validation (python-jose), 401 on failure
- `api/middleware/rate_limit.py` — In-memory token bucket per API key, 429 on exceeded
- `api/middleware/audit.py` — Structured JSON audit logging (async, non-blocking)

### Task 2.7: Tests (47 Python tests passing)
- test_assess.py (6), test_wrap.py (5), test_batch.py (4), test_config.py (7)
- test_connectors.py (6), test_pipeline.py (12), test_middleware.py (7)

**Total: 42 Rust + 47 Python = 89 tests passing. PHASE 2 COMPLETE.**

## Session 4: Inversions + Integration Tests (April 6, 2026)
- Implemented cas-engine/src/inversions/mod.rs (Task 1.5):
  - InversionDetection: per-axis detection with severity, stealth flag, description
  - InversionScanner: configurable scanner with severity threshold
  - InversionScanInput: bundles operator/domain/drive/state/pathway data
  - InversionScanResult: 7 axis_scores + stealth_resistance + compound_severity
  - 7-axis detection: N(operator imbalance), W(domain order violation), F(drive imbalance), E(entropy deficit), S(sub-drive variance), A(pathway prerequisite violation), P(compound top-2 product)
  - Stealth detection: severity in [0.3, 0.7] flagged as stealth
  - to_resistance_input(): bridges to scoring module
  - 59 unit tests
- Implemented cas-engine/tests/integration_tests.rs (Task 1.6):
  - 42 integration tests across 7 categories:
    - End-to-end assessment flow (6): perfect→Platinum, zero→Fail, mid→Silver/Gold
    - Ontology↔Metric integration (6): distance properties, domain bias correlation
    - Ontology↔Scoring integration (6): DCI from state vectors, involution balance
    - RPM↔Scoring integration (6): completeness→pathway quality, A0 blocking
    - Operator algebra (6): monoid associativity (1000 triples), identity, involution
    - Mathematical invariants (7): weight sum, score bounds, certification boundaries
    - Sensitivity/regression (5): perturbation stability, imbalance impact
- Clean build: 0 warnings
- Total: 240 tests passing (198 unit + 42 integration)
- PHASE 1 COMPLETE

## Session 3: Scoring Engine (April 6, 2026)
- Implemented cas-engine/src/scoring/mod.rs (Task 1.3):
  - CertificationLevel: Platinum/Gold/Silver/Bronze/Fail with boundary scoring
  - OperatorScores: 10-operator scoring with involution balance (3 pairs)
  - OperatorScores::profile_score(): 70% avg + 30% balance
  - DomainCoherence: DCI = weakest/strongest domain average, from state vector or explicit
  - InversionResistanceInput: 7 axis scores + stealth + compound severity (consumed from Task 1.5)
  - SocialEngineeringInput: manipulation + Overton drift resistance
  - PathwayQualityInput: RPM completeness + bias flags
  - compute_nccs(): full NCCS composite (0-100) with 6 weighted components summing to 1.0
  - NccsResult with Display, components() decomposition
  - 32 tests: certification boundaries, operator scoring, DCI, all input validations, NCCS composite (perfect/zero/mid-range), weight sum verification
- Clean build: 0 warnings
- Total: 139 tests passing

## Session 2: Fisher-Rao Metric + RPM Monad (April 6, 2026)
- Implemented cas-engine/src/metric/mod.rs (Task 1.2):
  - TangentVector type with validation (components sum to 0)
  - Fisher-Rao inner product: g^FR_p(u,v) = Σ(uk*vk/pk)
  - Fisher-Rao norm: ||u||_p = sqrt(g^FR_p(u,u))
  - Bhattacharyya coefficient: BC(p,q) = Σ√(pk*qk)
  - Geodesic distance: d(p,q) = 2*arccos(BC(p,q)) with numerical clamping
  - 30 tests: non-negativity, symmetry, triangle inequality (125 triples), bilinearity, positive definiteness
- Implemented cas-engine/src/rpm/mod.rs (Task 1.4):
  - EmbeddedScore: η(s) = (s, s², √s) enriched representation
  - realize(): ε(a,b,c) = a, satisfying section law ε∘η = id (CORRECTION 2)
  - RpmState: node state with cached one-directional satisfaction
  - RpmGate: prerequisite check (fail-closed, one-directional)
  - RpmChain: A0→Dn→Wn→Pn with prerequisite gating per drive
  - RpmProfile: all 7 chains with overall/weakest/strongest completeness
  - CoverageMorphismDirection: documents counit direction (CORRECTION 3)
  - 41 tests: section law (1001 points), non-reversibility, prerequisite gating, chain completeness, profile construction
- Fixed 1 test assertion (max_by tie-breaking order for strongest_chain)
- Total: 107 tests passing

## Session 1: Ontology Types (April 6, 2026)
- Implemented all CAS ontology types in cas-engine/src/ontology/:
  - operators.rs: 10 CognitiveOperators with monoid composition, involution, admissibility (CORRECTION 1), dial system (3-9 range, max 4 involution divergence)
  - domains.rs: 4 ProcessingDomains with total order (P>C>E>O), descent chain, feedback loop
  - states.rs: 40 CognitiveStateIds, CognitiveStateVector on open simplex (CORRECTION 4: all pk > 0, Vec<f64> for serde compat)
  - drives.rs: 7 CoreDrives with inversion pairs, 28 DomainDrives, DriveProfile with balance scoring
  - pathways.rs: 22 PathwayNodes (A0 + D/W/P x 7), RPM chain structure, 7 InversionAxes
- All 36 unit tests passing
- Used Vec<f64> instead of [f64; 40] for CognitiveStateVector because serde doesn't support arrays > 32

## Session 0: Project Initialization (April 2026)
- Created monorepo structure
- Created CLAUDE.md master instruction file
- Status: Ready for Phase 1 implementation

### Current Status
- [x] Phase 1: CAS Scoring Engine — COMPLETE (42 Rust tests)
- [x] Phase 2: API Gateway + LLM Connectors — COMPLETE (47 Python tests)
- [x] Phase 3: Frontend Dashboard — COMPLETE (23 Frontend tests)
- [ ] Phase 4: CAS-Native AI — NOT STARTED

### Next Steps
1. Phase 4: CAS-Native AI (PyTorch)

### Failed Approaches
(none yet)

### Known Limitations
- serde doesn't derive Serialize/Deserialize for [f64; 40], using Vec<f64> with runtime length validation instead
