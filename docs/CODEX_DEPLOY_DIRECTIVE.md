# Codex Deploy Directive — noeticcompass.com Full Feature Surface

**Generated:** 2026-04-25
**Repository:** `LittleHenderson/noetic-compass` at commit `37be0ac` (or latest master)
**Target:** noeticcompass.com production site
**Companion document:** `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md` — site architecture and copy

---

## Honest scope statement (read first)

This directive deploys **everything that exists in the repository**. One feature in the original session brief — the **Temporal Cognitive Score** (audio sonification) — exists ONLY as specification (`docs/design/cas_v7_5_multimodal_display_specification.md` Phase B+) with **zero implementation files** in the repo. Codex must NOT fabricate it. Treat it as roadmap with a "coming soon" placeholder. If user wants it built, that's a separate directive.

Everything else IS implemented and deployable.

---

## What's deployable (the real list)

### 1. Frontend dashboard (the main app)

**Location:** `noetic-compass-scaffold/noetic-compass/dashboard/`
**Stack:** Vite + React + TypeScript, with existing `vercel.json` and `package.json`
**14 pages already built:**

| Page | File | Description |
|---|---|---|
| Home / How it works | `HowItWorksPage.tsx` | Framework overview, marketing surface |
| Assessment | `AssessmentPage.tsx` | Run a new CAS assessment |
| Forecast | `ForecastPage.tsx` | **NEW — lacunarity forecast feature Codex just shipped (parity-fixed)** |
| Compiler | `CompilerPage.tsx` | Interactive CAS notation compiler |
| Configuration | `ConfigPage.tsx` | Dial settings, wrap pipeline config |
| Details | `DetailsPage.tsx` | Drill-down into a specific assessment |
| History | `HistoryPage.tsx` | Past assessments timeline |
| Cohort | `CohortPage.tsx` | Multi-subject comparative view |
| Validation | `ValidationPage.tsx` | Cross-validation against human raters |
| Validation Leaderboard | `ValidationLeaderboardPage.tsx` | Public LLM scoring leaderboard |
| Reproducibility | `ReproducibilityPage.tsx` | Reproducibility audit and replay |
| AI Challenges | `AiChallengesPage.tsx` | Adversarial scenario library |
| Scenario Browser | `ScenarioBrowserPage.tsx` | Browse 500+ test scenarios |
| FAQ | `FaqPage.tsx` | Common questions |
| Login | `LoginPage.tsx` | Authentication entry |

**Components of note:**

- `RadialArchitectureDisplay.tsx` — the visual "mandala" component (Phase A static SVG, 19 passing tests). Deployable today, mountable on any page that wants the visualization.

### 2. Backend API (FastAPI)

**Location:** `noetic-compass-scaffold/noetic-compass/api/`
**Routes implemented:**

- `/assess` — single assessment
- `/auth` — authentication
- `/batch` — batch assessment
- `/benchmark` — performance benchmarking
- `/cohort` — cohort analytics
- `/config` — dial / pipeline configuration
- `/export` — export results
- `/forecast` — **NEW — lacunarity forecast endpoint Codex just shipped**

### 3. Static documentation surface

- Book PDF at `book/publishing/Thinking_in_Cognitive_Architecture_v1.pdf` (742 pages, 1.79 MB)
- Book Markdown source at `book/manuscript/FULL_MANUSCRIPT_v2.md`
- All ADRs at `docs/architecture/cas_native_v2_adrs.md`
- Foundational Clarifications at `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
- Memory Substrate PDR at `docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md`
- Site spec at `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md`

These serve `/research`, `/research/book`, `/research/papers`, `/docs` pages on the marketing site.

---

## What is NOT deployable (be honest in user-facing copy)

### Temporal Cognitive Score (audio sonification)

- **Specification only:** `docs/design/cas_v7_5_multimodal_display_specification.md` Phases B-E
- **Implementation:** ZERO files. No audio engine, no Web Audio code, no sonification mappings translated from CAS algebra to actual sound.
- **What to ship instead:** A "Coming Soon" panel on the `/visualization` page. Suggested copy:

> ### The Temporal Cognitive Score (in development)
>
> A coming auditory companion to the Radial Architecture Display. Every pitch, dynamic, tempo, and rhythm mapping will derive directly from CAS algebra — turning a cognitive profile into a listenable signature. Currently in design specification; implementation roadmap published in our research notes.

DO NOT fabricate audio playback. DO NOT use stock music. DO NOT promise a launch date.

### CAS-Native v2 neural architecture

- **Implemented:** Yes (Python + Rust, 473+ tests passing)
- **Deployable as a website feature:** No — it's a research-grade neural architecture, not a consumer service
- **What to ship:** Brief mention on `/research` linking to ADRs and the relevant book chapters

### CAS Memory Substrate (ADR-09)

- **Specification only** (deferred to v7.8/v8.0)
- **What to ship:** Brief roadmap mention on `/research` or `/status`

---

## Deployment plan for Codex

### Phase 1 — Deploy the dashboard (do this first)

```bash
# Verify dashboard builds locally
cd noetic-compass-scaffold/noetic-compass/dashboard
npm install
npm run build

# Deploy to Vercel preview
vercel deploy

# After preview QA passes, promote to production
vercel deploy --prod
```

**`vercel.json` already exists** — review it before deploy. If it needs updating to reflect Vite + React App Router conventions or Node.js 24 LTS defaults, update it. Per current Vercel knowledge: prefer `vercel.ts` over `vercel.json` for new configs (TypeScript-typed config, environment variable access).

**Domain wiring:** point `noeticcompass.com` (apex) and `www.noeticcompass.com` to the Vercel project. Ensure SSL cert provisions cleanly.

### Phase 2 — Deploy the API

The `api/` directory is FastAPI. Deploy to Vercel Functions (Python runtime — Vercel supports Python 3.13/3.14 via Fluid Compute).

```bash
cd noetic-compass-scaffold/noetic-compass/api
# Ensure requirements.txt is current
# Vercel auto-detects FastAPI; no special config needed
vercel deploy
```

If the API needs to live at `api.noeticcompass.com` as a separate subdomain, configure DNS and Vercel project routing accordingly. If it goes under `noeticcompass.com/api/*`, set rewrites in `vercel.ts` to route `/api/*` to the API project.

### Phase 3 — Mount the Radial Architecture Display visually

`RadialArchitectureDisplay.tsx` exists as a component but is NOT wired into any page yet (per Wave 4 Agent 16 follow-up notes). Mount it:

1. On `HowItWorksPage.tsx` as a hero visual with sample data fixture
2. On a new dedicated `/visualization` page if the marketing site is a separate Next.js app
3. Provide demo controls (load different cognitive profiles to see visualization change)

### Phase 4 — Add "Coming Soon" placeholder for Temporal Cognitive Score

On `/visualization` (or wherever the Radial Display lives), add a sibling section explicitly labeled "Coming Soon" for the audio companion. Use the suggested copy above.

### Phase 5 — Wire static documentation pages

- `/research/book` — book purchase / sample chapter / TOC. Link to KDP/IngramSpark when those listings go live.
- `/research/papers` — placeholder for Paper 1 (Categorical Hutchinson Theory) status
- `/docs` — render relevant docs from the repo (compiler reference, API reference, framework primer)
- `/about` — methodology section including CARP

Use the existing `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md` as the source of truth for copy and structure on these pages.

### Phase 6 — Production verification

- [ ] All 14 dashboard pages render without errors
- [ ] Forecast endpoint returns expected shape (post-parity-patch)
- [ ] Radial Architecture Display renders on intended pages
- [ ] No fabricated content (no stock photos, no fake testimonials, no aesthetic-heritage names)
- [ ] No superseded operator names anywhere on site (Identity / Differentiation / Abstractification / Concretization / Integration / Empathy / Critique / Momentum / Expansion / Contraction)
- [ ] Lowercase `|f` preserved everywhere registers appear
- [ ] USPTO #64/037,173 patent-pending notice in footer / legal page
- [ ] Author byline "Little Henderson" / publisher "Noetic Compass Press"
- [ ] Accessibility: Radial Display text-alternative view available
- [ ] Mobile responsive
- [ ] Lighthouse score >90 (use Vercel Speed Insights to measure post-deploy)

---

## Vercel platform integrations to consider

Per repository's Vercel platform context:

- **AI Gateway** — if/when assessment-running needs LLM calls server-side, route through Vercel AI Gateway with `provider/model` strings. Don't pin to provider-specific packages.
- **Vercel Functions (Fluid Compute)** — current default. Python 3.13/3.14 supported for the FastAPI backend.
- **Marketplace integrations** — Clerk for user auth (when needed), Neon Postgres or Upstash Redis for assessment-history persistence.
- **Vercel Blob** — for any future user-uploaded files (e.g., scenario sets, assessment exports).
- **Rolling Releases** — when shipping platform updates beyond the marketing site, use Rolling Releases for gradual canary rollout.
- **BotID** — if/when the assessment endpoint needs bot protection.

---

## What to do if Codex hits blockers

1. **Build fails:** report the specific error. Do NOT silently disable failing tests or skip type checks to get a build through.
2. **Page renders but data missing:** verify backend API is deployed and reachable. Likely a CORS or routing issue.
3. **Radial Architecture Display doesn't render:** check that the SVG library / dependencies installed. Component has 19 passing tests in dev — should be solid.
4. **Domain doesn't resolve:** verify DNS records, especially A/AAAA for apex and CNAME for www. Vercel docs cover both.
5. **SSL doesn't provision:** wait 24h for DNS propagation; if still failing, check that the domain isn't held by a previous Vercel project.

If a blocker takes more than 30 minutes to resolve: stop, report status, await user direction. Do NOT push half-broken state to production.

---

## Anti-patterns to avoid

- ❌ Deploying with placeholder "Lorem ipsum" copy. Use the real copy from the site feature spec.
- ❌ Adding analytics/tracking without explicit user authorization (privacy concern; user hasn't approved any specific provider).
- ❌ Hardcoding API keys or credentials into source. Use Vercel environment variables.
- ❌ Promising audio sonification "launching this month" — it isn't built.
- ❌ Adding `noindex` to legitimate marketing pages (would tank SEO).
- ❌ Deploying without HTTPS / redirecting HTTP → HTTPS.
- ❌ Skipping the production verification checklist above.

---

## Reporting back

When deployment lands, Codex should report:

- Vercel project name(s) created
- Production URL(s) — confirm `noeticcompass.com` resolves
- Build time and bundle size
- Lighthouse score (Performance, Accessibility, Best Practices, SEO)
- Any pages that didn't deploy and why
- Any feature spec items that needed clarification
- Confirmation that "Coming Soon" placeholder is in place for Temporal Cognitive Score (NOT a fabricated audio player)

---

## If user wants the Temporal Cognitive Score built

This requires a separate "build, then deploy" directive. Scope estimate: 4-8 hours of focused work to:

1. Read the multi-modal display spec (`docs/design/cas_v7_5_multimodal_display_specification.md` Phases B-E)
2. Implement Web Audio API mappings translating CAS algebra to pitch / dynamic / tempo / rhythm
3. Build playback UI component pairing with Radial Architecture Display
4. Add tests
5. Deploy to dashboard
6. Update the "Coming Soon" placeholder to a live demo

Recommend doing this AFTER Phase 1-6 above lands, so the rest of the site is live first.

---

## Source of truth

- This document: `docs/CODEX_DEPLOY_DIRECTIVE.md`
- Site copy and architecture: `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md`
- Repository state: commit `37be0ac` or later
- Key constraints: `CLAUDE.md` (naming discipline, what NOT to fabricate)

If anything in this directive contradicts the repo state (because Codex commits new work after this is written), the repo wins. Re-read CLAUDE.md and the site feature spec, then proceed.
