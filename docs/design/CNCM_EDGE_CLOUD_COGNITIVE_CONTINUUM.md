# CNCM Edge-Cloud Cognitive Continuum — deployment architecture (R&D record)

**Status: RECORDED FOR FUTURE R&D. Not authorized, not scheduled, not started.**
Owner instruction, 2026-09-01: *"This should be recorded as a deployment architecture, not
allowed to derail the current memory validation work."*

**Owner:** Little Henderson (Prof. Hermes M. Thoth). **Recorded by:** Claude, verbatim where
the wording is load-bearing. **Cost to date:** $0 — no build, no spend, no lane opened.

---

## 0. The correction that defines the design

> **Do not cut one transformer arbitrarily in half, with half its layers on the phone and
> half in the cloud.** That would make every thought depend on a network round trip. A weak
> connection would turn the mind into a buffering icon.

Divide by **responsibility**, not by layer:

```
ON-DEVICE:   a complete minimum brain
IN THE CLOUD: extended memory, larger specialists, consolidation, and heavy compute
```

**Name:** *CNCM Edge-Cloud Cognitive Continuum.* Explicitly **not** "split brain" — in
distributed systems that phrase describes two copies losing agreement. This is **one mind
with a local core and an optional extended cortex.**

The existing CNCM already suits this: a deterministic runtime kernel with typed state,
atomic commits, branch isolation, rollback, RPM recursion and sealed replay; and a semantic
CMB with entities, relations, truth, provenance and memory queries. Those separations make
it natural to keep **authority local** while placing larger memory and compute in the cloud.

## 1. What stays on the device

The part of the mind that must never disappear when the internet goes down.

| Local component | Purpose |
|---|---|
| Small CNCM language model | Basic conversation, comprehension, offline operation |
| CAS runtime kernel | State, branches, commitments, RPM, authority |
| Current Bias state | Who the machine currently is, what it is doing, recent history |
| Working memory | Information needed for the present task |
| Hot CMB cache | Recent, important, frequent, and private memories |
| Local verifier | Decides whether cloud results may influence answer or memory |
| Owner keys and permissions | The cloud cannot silently rewrite the machine's identity |
| Offline skills | Basic reasoning, tools, safety, routine actions |

The local system must always be able to say:

```
The internet is unavailable.
I have incomplete information.
I can continue locally or wait for extended memory.
```

> It should never become cognitively unconscious merely because Wi-Fi drops.

## 2. What lives in the cloud

| Cloud component | Purpose |
|---|---|
| Full long-term CMB | The larger lifetime memory graph |
| CMB-R1 propagation system | Finds related memories beyond direct semantic matches |
| Large specialist models | Hard language, coding, mathematics, vision, research |
| Cloud CJT experts | Rare or expensive experts, called only when needed |
| Memory consolidation service | Deduplicate, summarize, cross-link, organize |
| Replay selector | Choose old memories relevant to new learning |
| Model adaptation service | Train small adapters / controlled updates |
| Cross-device synchronization | Keep laptop, phone and other devices consistent |
| Cold archive | Old raw records that need not stay locally active |

The cloud may be much larger, but it remains **an assistant to the local sovereign core, not
the owner of the mind.**

## 3. How one thought moves

1. **A new Idea appears.** The device builds an Idea packet: semantic meaning, CAS geometric
   profile, ordered CAS trajectory, entities and relations, current Mind state, source and
   provenance, time and context, verification status.
2. **Local memory searches first** — semantic matches, structural matches, similar
   trajectories, recent relevant experience. If the answer is local, nothing leaves the
   device.
3. **RPM decides whether cloud help is necessary**, with a *typed* reason:
   `WISDOM BLOCK` (lack required information) · `POWER BLOCK` (local model lacks capacity) ·
   `MEMORY LACUNA` (no relevant local memory) · `NO_READY_CJT` (no local expert can perform
   the operation). This matches the existing CJT design, where RPM distinguishes relevance,
   knowledge and capacity rather than collapsing them into one vague confidence score.
4. **The device sends a compact query capsule** — not the whole conversation by default:
   the query, the required operation, a semantic vector, a CAS trajectory, authorized
   context, privacy level, maximum cost, memory types requested.
5. **The cloud returns candidates, not authority**: candidate memories, candidate Effects,
   source records, provenance roots, confidence and uncertainty, content hashes, and the
   reason each result was retrieved. **The cloud does not rewrite local state.**
6. **The local verifier decides.** Does this memory apply? Is it current? Is its source
   trustworthy? Does it contradict local evidence? Is it one independent source or twenty
   copies of one source? Does the returned Effect satisfy the current Cause?

> **The central authority rule: cloud components may PROPOSE. The local kernel COMMITS.**

## 4. Memory lifecycle and sync

Do not permanently store every passing sentence or accidental model output. Staged
lifecycle:

```
1. WORKING MEMORY            active for the present task
2. EPISODIC BUFFER           recent events awaiting evaluation
3. CANDIDATE LONG-TERM       potentially important, not yet consolidated
4. VERIFIED LONG-TERM        source, context and usefulness checked
5. CONSOLIDATED              deduplicated, summarized, cross-linked, indexed
6. QUARANTINED OR DELETED    false, unsafe, obsolete, or owner-removed
```

Sync when the device is **charging, on trusted Wi-Fi, idle, inside its cost limit, and
explicitly permitted.** This functions somewhat like sleep: the device accumulates
experience during the day, the cloud consolidates and cross-references, and the device later
receives a smaller organized update — compact summaries, updated cross-reference links, new
indexes, frequently needed memories, revised confidence records, small trained adapters.

**Three memory temperatures:**

```
HOT   on device, immediately accessible
WARM  cloud indexed, retrieved on demand
COLD  cloud archive, restored only when needed
```

The device streams **memory capsules** on demand rather than downloading the database. The
hot cache keeps recently used memories, high-importance autobiographical memories, active
project material, recurring procedures, memories that must be available offline, and
especially private records that never leave the device.

## 5. Where CMB-R1 fits

```
LOCAL STATIC CMB   find direct candidates (semantic + static CAS trajectory)
CLOUD CMB-R1       expand through related memory geometry (bounded graph propagation,
                   cross-domain analogy, pattern completion, large-memory traversal,
                   provenance clustering)
LOCAL STATIC CMB   re-score against the original question
LOCAL VERIFIER     decide what is admitted
```

Creativity without surrendering control.

> **AUDIT NOTE (Claude, 2026-09-01, commit `68fdf570`).** The independent audit of CMB-R1 /
> RGM-0 at `95cedfe5` returned **PARTIAL_PASS**. Reproduction was exact and no answer
> leakage was found, but `RESONANCE_SPECIFIC_VALUE` was **not established** — ordinary
> bounded best-first expansion beat the resonance engine on three of five families and tied
> it exactly on pattern completion — and the echo defence proved to be the
> trajectory-coherence quarantine, **not** provenance (root-dedup alone failed 17/23;
> coherence alone was sufficient 0/23). So the "CLOUD CMB-R1" box above should be read as
> **bounded graph propagation with a coherence verifier**, which is a real and useful
> mechanism, until the six registered repairs are done and the status is re-emitted. This
> note does not weaken the architecture — the box is still needed — it names honestly what
> currently goes inside it.

## 6. Conditional cloud compute (dynamic allocation)

```
simple question      local model only
memory-heavy         cloud CMB
hard mathematics     cloud math expert
large coding task    cloud programming expert
private routine      local only
offline              local degraded mode
```

A CJT route decides: local expert ready → execute locally; local Wisdom missing → query
cloud memory; local Power insufficient → invoke cloud specialist; privacy policy blocks
upload → remain local or abstain; cost ceiling reached → remain local or defer.

## 7. Three ways to divide the brain

1. **Functional split — RECOMMENDED FIRST.** Complete small brain locally; large memory and
   specialists remotely. Most robust.
2. **Cloud CJT expert offloading — PROMISING LATER.** Device holds base model, router,
   working memory, governance; cloud holds selected expensive experts. Maps naturally onto a
   future CJT mixture-of-experts architecture.
3. **Literal layer split — AVOID INITIALLY.** Activations cross the network repeatedly;
   every token may need another round trip; hidden activations can leak private information;
   a network failure interrupts the forward pass; versions must stay perfectly synchronized.
   *"This makes the cloud part of the machine's spinal cord. I would rather make it an
   optional organ."*

## 8. The real dangers

- **Privacy.** Memories may contain health, financial, emotional, location, relationship or
  work information. Each memory needs an upload policy: `LOCAL_ONLY`, `CLOUD_ENCRYPTED`,
  `CLOUD_SEARCHABLE`, `TEMPORARY_REMOTE`, `OWNER_APPROVAL_REQUIRED`. **Master identity and
  encryption keys stay on the user's device.**
- **Memory poisoning.** Every returned memory carries origin, version, content digest,
  verification status, independent provenance roots, last confirmation date.
- **State divergence.** Append-only event journal; never silently overwrite one side with
  "the latest file."
- **Cloud dependence.** The user must be able to export memory records, indexes, CAS
  profiles, trajectories, adapters and audit history. *The mind should not cease to be
  itself because one cloud account disappears.*

## 9. Inference flow vs learning flow

```
INFERENCE   device asks -> cloud retrieves or computes -> device verifies -> device answers
            (nothing permanent changes)

LEARNING    device uploads verified experience -> cloud consolidates or trains ->
            cloud returns a PROPOSED memory/update -> device tests it ->
            local authority commits or rejects
```

The cloud may help create an update. It cannot quietly install one.

## 10. Prototype ladder (registered, not scheduled)

**EC-CNCM-0: Edge-Cloud Continuity and Memory Sync Simulator.** Before any real phone, test:

```
device works while offline
memories queue locally
sync resumes without duplicates
network drops during retrieval
cloud returns stale memory
cloud returns corrupted memory
two devices create conflicting records
owner deletes a cloud memory
local verifier refuses poisoned updates
hot-cache selection stays inside storage limits
```

Then: **EC-CNCM-1** laptop core + cloud CMB · **EC-CNCM-2** smartphone core + cloud CMB ·
**EC-CNCM-3** local base model + conditional cloud CJT experts.

## 11. Falsifiers (what would show this is the wrong shape)

Recorded so the idea can fail honestly rather than be defended:

- EC-CNCM-0 shows the local verifier cannot reject poisoned or stale cloud memories without
  also rejecting good ones at an unacceptable rate.
- Offline degraded mode is not usable in practice — the local minimum brain is too small to
  be a *complete* mind, so the "continuing self" claim fails.
- Sync cannot converge without duplicates or divergence under realistic disconnection.
- The cost or latency of the query capsule exceeds simply running a larger local model.
- Privacy policy enforcement proves unimplementable at memory granularity.

## 12. Boundary

This is a **deployment architecture record**, not a research claim and not a lane. It does
not modify, block, or reprioritize: CJT-EX1 (awaiting the owner's E1S ruling), the CMB-R1
repairs, or any Tier C record. No claim word is asserted; no status is emitted; nothing here
is `EMPIRICALLY_SUPPORTED`.

**Bottom line, owner's words:**

> A complete minimum mind on the device, with its identity, authority, working memory and
> essential skills intact, connected to a cloud-based long-term memory and specialist cortex
> whenever additional knowledge or power is needed.
>
> The device is the continuing self. The cloud is the extended library, workshop and
> long-distance memory. The internet connection is the corpus callosum, but the local mind
> must remain alive when that bridge goes dark.
