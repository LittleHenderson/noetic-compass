# CAS INtrpt — Design Brief, Part 3
Consolidating noeticcompass.com under one umbrella · brand system · route map
Read Parts 1 and 2 first.

---

## 14. The naming architecture — settle this before any pixel

There are three names in play and they are **not** competing. They occupy different levels. Getting this wrong makes the whole site feel confused; getting it right makes it feel inevitable.

| level | name | role |
|---|---|---|
| **Company / publisher** | **Noetic Compass** · *Noetic Compass Press* | who makes it, who publishes the book |
| **Domain** | **noeticcompass.com** | unchanged |
| **Product** | **CAS INtrpt** | the thing you use |
| **Framework** | **CAS** — Cognitive Architecture System | the science underneath |

**So: the name stays, the brand changes.** noeticcompass.com is the house. CAS INtrpt is what the house makes. The book, the papers, and the patent belong to Noetic Compass; the instrument is CAS INtrpt.

**Wordmark:** `CAS INtrpt` — `IN` in accent, the rest in foreground. Descriptor beneath in mono, letterspaced:
`BLACK BOX · WHITE BOX · AI INTERPRETABILITY`

Footer carries the company line: *Noetic Compass · Noetic Compass Press · USPTO #64/037,173 (patent pending)*.

**Never** write "Noetic Compass CAS INtrpt" as a compound. One or the other, per context.

---

## 15. Brand system — the palette

Taken from the Modernist direction and formalised. **One accent. No secondary accent. No gradients.**

```
accent-500   #ec3013     primary action, the measured-signal mark, "IN" in the wordmark
accent-600   #dd2b0f     hover / pressed
accent-100   (tint)      selection wash, focus ring at low alpha only
```

Grounds and type — both themes first-class, not inverted:

```
DARK                          LIGHT
bg        near-black          bg        near-white (warm, not blue-white)
surface   +4% lift            surface   -3% recede
border    +12% hairline       border    -12% hairline
fg        near-white          fg        near-black
fg-muted  ~60%                fg-muted  ~55%
```

**Status hues — the second and only other family, all muted:**
```
verified   desaturated green   REAL / VALIDATED
bounded    amber               BOUNDED / PARTIAL
withdrawn  desaturated red     WITHDRAWN / FALSIFIED
inert      grey outline        NOT RUN / NULL
```
Rendered as a `6px` left rule or a `6px` dot. **Never a filled pill.** Never traffic-light saturation — these sit *below* the accent in intensity, always.

**Type:** one grotesque for UI. One mono for every number, hash, path, model ID, and the descriptor lockup. Display sizes are large and tight-tracked (per the Modernist hero); body is generous. **Two faces total.**

**The accent is rationed.** One primary action per screen. The measured bar in a Floor component. `IN` in the wordmark. That is the whole budget. An orange that appears everywhere stops meaning "this is the signal."

---

## 16. One umbrella, two zones

Consolidation does **not** mean one flat layout. Marketing pages persuade; instrument pages measure. They share the design system and the shell — they do not share the layout logic.

- **Zone A — Public (no auth).** Wide measure, large display type, generous vertical rhythm, one idea per scroll.
- **Zone B — Product (auth).** Dense, monospace-forward, app chrome, the Explainer present.

**Shared:** wordmark, palette, type, the Floor component, status vocabulary, footer.
**The seam:** crossing from A to B is a real transition — the nav compresses, the Explainer appears. Design that moment; do not let it be accidental.

---

## 17. Route map — everything folded in

Thirteen existing routes consolidate to nine. Nothing is deleted; several merge.

```
/                    Home — the claim, the proof, the finding, the limits   (Part 2 §10)
/product             CAS INtrpt — what the instrument does
                       absorbs: /visualization, /tutorial
/framework           CAS — 10 Noetics · 4 Domains · 4 Registers · 7 Drives
/research            Book · papers · ADRs · methodology (CARP)
                       keeps: /research/book, /research/papers
/docs                Developer docs — compiler, API, integration, quickstart
/status              What is live vs roadmap — claim states, in public
/about               Framework, methodology, team
/legal               Copyright · USPTO #64/037,173 · terms · privacy
/app                 → Zone B. Dashboard, Connect, Profile, Detail, capabilities
```

**Merges, with reasons:**
- `/tutorial` → into `/product` as its opening section. A separate "Start Here" page is an admission the product page failed.
- `/visualization` → into `/product`. The Multi-Modal Cognitive Signature is a feature of the instrument, not a peer of it.
- `/contact` → into `/about` plus the footer. It does not need a page.

**`/status` is the sleeper.** A public page showing what is `REAL`, what is `BOUNDED`, what is `WITHDRAWN`, and what is `NOT RUN` — with real numbers. Almost nobody publishes this. Given the claim-state discipline already running through the product, it costs nothing and it is the most defensible page on the site. **Design it as a first-class page, not a changelog.**

---

## 18. Brand discipline that survives the rebrand

These constraints are load-bearing and pre-date the redesign. **The new colour scheme changes nothing about them.**

**Names — use verbatim:** Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect. Canonical, not subject to alternative naming.

**Never in any public surface:**
- Superseded operator names (Identity, Differentiation, Abstractification, Concretization, Integration, Empathy, Critique, Momentum, Expansion, Contraction)
- Aesthetic-heritage names (mandala, merkaba, esoteric labels) — internal documentation only
- Testimonials, case studies, customer counts, revenue figures — **none exist**
- Stock author photos or invented biography
- Publication dates beyond "2026" unless confirmed
- `certified`, `guaranteed`, `100%`, `world-first`, `court-admissible`

**Always:**
- Public feature names strictly technical: *Radial Architecture Display*, *Temporal Cognitive Score*, *Multi-Modal Cognitive Signature*
- `|f` lowercase preserved wherever registers appear
- Author byline **Little Henderson**
- USPTO notice in footer and `/legal`
- The Radial Architecture Display ships with a **text alternative** — accessibility is a launch requirement, not a follow-up

---

## 19. Component inheritance

The public site borrows from the product, not the reverse. This is what makes the umbrella feel like one thing:

- **The Floor** appears on `/` and `/status` with real numbers — same component, same rules, no marketing variant
- **Status rules** appear on `/status` and in the product identically
- **Matched-sentence treatment** (differing words highlighted, everything else identical) appears on `/` and in Relation detail — same type treatment both places
- **Mono numerals** everywhere, both zones, no exceptions

**No marketing-only versions of data components.** The instant a Floor on the landing page uses invented numbers, the whole product's credibility argument collapses. Landing-page figures come from real runs or the component is not used.

---

## 20. Additional deliverables

18. Wordmark lockup — dark and light, full and compact (favicon/app icon)
19. Colour token sheet — both themes, with the accent-rationing rule written into it
20. `/` home, full scroll, in the new palette
21. `/status` — the claim-state page, populated with real statuses
22. `/product` with `/tutorial` and `/visualization` folded in
23. `/framework` — the four axes without ornament
24. The Zone A → Zone B transition
25. Nav: public state, authed state, mobile
26. Footer with company line and USPTO notice

**Test of success for Part 3:** a visitor cannot tell where the marketing ends and the instrument begins — because the same components, the same restraint, and the same honesty run through both. And the orange means one thing everywhere: *this is the measured signal.*
