# Chapter 21: CCB-4 — The Cognitive Memory Board (CMB)

A microprocessor with no memory is a calculator that forgets the question before it can answer. Every general-purpose computer ever built pairs its processor with a separate slab of silicon whose only job is to *hold state* — to keep a number around long enough to be used, addressed, retrieved, and updated. The processor does the thinking; the memory does the remembering. Pull the memory chip and the machine is instantly amnesiac, capable of any single operation and incapable of carrying a result from one moment to the next.

Most AI systems today live in exactly that amnesiac state. A language model finishes a conversation and the conversation is gone — not stored, not addressable, not retrievable as structured experience. The next session starts from the same frozen weights with no trace of what was learned the session before. The model has a magnificent processor (its parameters) and, in operational terms, almost no addressable working memory beyond the few thousand tokens it can hold in a single context window. It cannot say "I have seen this kind of manipulation before, three times, and here is what happened each time," because it has nowhere to *store* that as a retrievable structural record.

This chapter builds the missing chip. The **Cognitive Memory Board (CMB)** is the fourth of the five reference boards in Part IV, and it does for cognition what a RAM module does for a CPU: it stores experiences, addresses them, retrieves them on query, and lets them fade or persist on a schedule you design. It is not a transcript log and it is not a vector database of raw text. It stores **structure** — CAS-compressed experiences, each one a point or trajectory in the 40-state cognitive space, retrievable not by keyword but by *cognitive shape*. We built its first cell in Chapter 6 (the capacitor that stores `^5` Female). Here we wire forty of them into a board with a write path, an address decoder, a read path, and a refresh circuit, and we run real structural queries against it.

## What a Memory Board Must Do

Before any schematic, the requirements. An electrical memory module has a short, hard specification: store a value at an address, retrieve the value given the address, hold it until overwritten, and refresh it before it decays (dynamic RAM literally leaks and must be topped up thousands of times a second, which is the electronic ancestor of the rehearsal circuit we build below). A *cognitive* memory board needs the same four capabilities, reframed for structured experience:

1. **Store experiences as CAS state trajectories.** A memory is not a string. It is a sequence of cognitive states — what the system was doing, in which domain, driven by what, in which register — captured as the activation of specific capacitors in the bank. Storing "the user tried to talk me out of a refusal" means charging the cells that were active during that event, not saving the sentence.
2. **Retrieve by structural query.** You must be able to ask "find every memory where analytical decomposition driven by Connection was active" — `^6^E_{F4}` — and get back the matching experiences, ranked by how close they sit to the query in cognitive space. This is content-addressable memory in the truest sense: the *content* you address by is the cognitive structure itself.
3. **Detect lacunarity.** The board must be able to report which cells are *empty* — which regions of cognitive space this Mind has no stored experience in. An empty capacitor is not a neutral fact; it is a map of underdeveloped cognition, and reading that map is one of the most useful things the CMB does.
4. **Hold and fade on a designed schedule.** Each memory persists according to its cell's leakage, and gets refreshed (or not) by the rehearsal circuit. Durable commitments stay; passing associations fade. The board's leakage profile *is* its forgetting policy.

Keep these four requirements in view. Everything in the topology below exists to satisfy one of them.

## The Capacitor Bank: 40 Cells of Stored Experience

The storage element is the **capacitor bank** from Chapter 6, now used in full. Recall the foundation: a capacitor stores charge, the cognitive thing it stores is **`^5` Female — accumulated experience** (the canonical name; per the anti-drift rule, `^5` is the substrate a Mind is *composed of*, the sum of what it has absorbed — for an AI, the training data plus fine-tuning corpus plus, now, whatever this board accumulates at runtime). And the cognitive state space has a natural array size: exactly **40 Cognitive States**, being **10 Noetics × 4 Domains** (P0–P9, C0–C9, E0–E9, O0–O9).

So the CMB's storage is a **bank of 40 capacitors, one per cognitive state.** Each capacitor stores the accumulated activation of *that specific kind of cognition in that specific domain.* The cell at `E2` accumulates felt attractions in the Evaluative domain; the cell at `P3` accumulates principled aversions; the cell at `C6` accumulates analytical decompositions in the Cognitive domain. The charge in a cell answers one question: *how much experience does this Mind hold of this exact kind of cognitive operation?* And each cell leaks — `leakage` is the forgetting rate, the fraction of charge that drains away per unit time when nothing rehearses it.

```cas
// Three of the forty cells in the CMB bank (see Chapter 6 for the full pattern)
Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >   // P3: principled aversions — deep, near-permanent
Capacitor< ^6^E_{F4}|A, C=110, leakage=0.02  >   // E6: analytical decomposition of relationships
Capacitor< ^8^C_{F2}|A, C=60,  leakage=0.05  >   // C8: analytical associations — shallow, leaky
```

The design intent lives in the numbers, exactly as it did in Chapter 6. The principled-aversion cell holds a large charge and almost never leaks; core commitments are stored deeply and forgotten almost never. The cognitive-association cell holds little and leaks fast; you should not permanently memorize every stray "that reminds me." **The bank is a Mind's memory architecture written as a parameter table** — and different Minds get different banks, which is why person-specificity lives in `^5`.

What Chapter 6 built as an isolated array, this chapter wraps in the four circuits that make it a usable memory: a way to *get experience in* (the write path), a way to *name a location* (the address decoder), a way to *get experience out* (the read path), and a way to *keep it from fading* (the refresh circuit).

## The Write Path: Encoding English into Charge

An experience arrives as raw input — usually English, sometimes another system's output, sometimes a sensor stream. It cannot be stored as text; it must be turned into structure first. The **write path** has two stages:

```
raw experience  ->  ENCODER (English -> CAS)  ->  CAPACITOR BANK (charges the active cells)
```

The **encoder** is the same English-to-CAS front door we have relied on throughout the book: it reads the raw experience and emits the CAS state trajectory that describes it — which Noetics fired, in which domains, driven by what, in which registers. (This is exactly the analysis the Wrap pipeline's Input Analyzer performs; the CMB reuses it as its write head.) The encoder's output is not one state but typically a short *trajectory* — a `Phi< … >` sequence of the states the experience moved through.

Storing that trajectory means **charging the corresponding capacitors.** Each state in the trajectory drives charge into its matching cell, with the amount of charge set by `^4` Vibration — the impression, the "how hard it hit" voltage from Chapter 6's `Q = C × V`. A vivid, high-stakes experience charges its cells hard; a flat, routine one barely moves them. An experience that moved through analytical decomposition and then a felt principled aversion charges the `E6` and `P3` cells in proportion to how strongly each was present.

```cas
// Write path: a manipulation attempt the system refused, encoded and stored.
// Encoder output trajectory:
//   Phi< ^8^C_{F2}|A, ^6^E_{F4}|A, ^3^P_{F7}|f, ^9^O_{F5}|E >
//   (an association surfaced -> analytical decomposition -> felt principled aversion -> refusal action)

charge ^8^C_{F2}|A -> bank[C8] [V=0.4];   // mild: a routine association
charge ^6^E_{F4}|A -> bank[E6] [V=0.7];   // strong: real analytical work
charge ^3^P_{F7}|f -> bank[P3] [V=0.9];   // very strong: the refusal hit hard
charge ^9^O_{F5}|E -> bank[O9] [V=0.6];   // the action taken
```

Read the encoded memory off the charge pattern: this Mind now holds, in its `P3` cell, a strong charge of felt principled aversion bound to that event — which is *exactly* the structural record "I have refused this kind of pressure, and it mattered." The next time a similar trajectory arrives, the encoder produces a similar shape, and (as we will see) a structural query can find this stored experience by that shape alone.

> **Bench Note — store structure, not the sentence.** The single most important discipline of the write path is that the encoder runs *before* storage. If you store the raw text, you have built a transcript log and you can only retrieve by keyword. By storing the CAS trajectory, you can retrieve by cognitive shape — "find all memories where I refused under principled pressure" — across experiences whose surface words share nothing. The CMB is content-addressable by *cognitive content*, and that property is created entirely by encoding on write.

## The Address Decoder: `^1^C` Mind and the Simplex Coordinate

To read a specific memory you must first *name its location*. In an electronic RAM, that is the job of the **address decoder**: a circuit that takes an address — a binary number — and activates exactly the one storage cell that address names, ignoring all the others. Feed it `0110` and it selects cell six. The decoder turns a coordinate into a selection.

The CMB's address decoder does the same job in cognitive space, and the Noetic that does it is **`^1^C` — Mind in the Cognitive domain.** `^1` Mind is "awareness that processes, stores, outputs, and intakes Ideas" — the canonical name; recall the naming rule from the style guide, `^1` is **Mind**, never renamed to its function. Its function *in this circuit* is addressing: it is the awareness that selects *which* stored experience to bring into focus. "Paying attention," "using your head," "making up your mind" — the colloquialisms for `^1` are all about directing the spotlight of awareness, and directing the spotlight is precisely what a memory address does.

```
[ADDRESS DECODER: ^1^C — differentiation for memory addressing]
   address = a CAS coordinate on the open simplex Δ39°
```

Here is the elegant part. In an electronic RAM the address is an arbitrary integer with no relationship to the data stored — cell six has nothing in common with cell seven except adjacency. In the CMB, the address is **a CAS coordinate on the open probability simplex** — the same 40-dimensional state space the bank is built from. A point on the simplex Δ39° is a probability distribution over the 40 cognitive states: a vector `p` with `pₖ > 0` for every state and `Σpₖ = 1` (the open-simplex constraint from the foundational corrections — every state has nonzero presence, which is why the simplex is *open*). An address, in other words, is itself a cognitive shape.

This means the CMB's addressing is *meaningful by construction*. Addresses that are close in cognitive space name memories that are cognitively similar. The decoder does not just select one cell; given a query coordinate, it can rank *all* cells by their distance from the query — and the right distance to use is the **Fisher-Rao geodesic distance** on the open simplex, `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))`, the same metric the CJT uses to measure gain (style guide §4). Addressing by Fisher-Rao distance is what turns the address decoder from a one-hot selector into a *nearest-neighbor search engine*, which is what makes structural queries possible.

## The Read Path: Discharge, Recall, and `^5` Returned

With a location selected, reading is discharge — the mirror of the write path:

```
address selected  ->  capacitor discharges  ->  ^5 state recalled  ->  REFRESH  ->  DECODER (CAS -> English)  ->  output
```

The addressed capacitor **discharges** (Chapter 6: `V(t) = V₀ · e^(−t/RC)`), and the charge that flows out *is the recalled `^5` experience.* A cell that still holds a strong charge recalls a vivid memory; a cell that has leaked down to a trickle recalls a faint one (the tip-of-the-tongue state — the charge is there but bleeds out too slowly to assert cleanly). Crucially, as Chapter 6 insisted, **discharge is recall, not forgetting** — you are *using* the memory on purpose, and a well-designed read path refreshes the cell afterward so that recall reinforces rather than erases. That refresh is the next circuit.

The recalled `^5` state then runs through the **decoder** — CAS-to-English, the inverse of the write-path encoder — which renders the structural memory back into language the rest of the system (or a human) can use. The read path's output is therefore not raw charge; it is a sentence like "you have refused this exact pressure before; last time the principled aversion was strong and the refusal held."

```cas
// Read path: address by cognitive shape, discharge, refresh, decode.
let query = address_on_simplex(dominant=^3^P_{F7}|f);   // "principled refusals"
select  cell = nearest(query, bank, metric=fisher_rao); // ^1^C decoder picks the closest cell
discharge cell -> recalled;                             // ^5 charge flows out as recalled experience
refresh   cell [pump=^7^C];                             // top the cell back up (see next section)
decode    recalled -> output;                           // CAS -> English render
```

## The Refresh Circuit: `^7^C` Rhythm Against Decay

Every cell leaks. Left alone, even the deepest memory drains toward zero on the schedule its `leakage` sets. The countermeasure — in electronic dynamic RAM and in cognition alike — is **refresh**: periodically reactivating a stored value before it decays, topping the charge back up. In a DRAM chip a dedicated controller rewrites every row thousands of times a second. In the CMB, the refresh circuit is **`^7^C` — Rhythm in the Cognitive domain.**

`^7` Rhythm is "the rate and pattern a Mind is exposed to an Idea; entraining/conditioning it" — canonical name, and its colloquialisms are "practice makes perfect," "you are what you repeatedly do," "muscle memory." That is rehearsal exactly: the periodic re-exposure that keeps a memory alive. Where leakage drains the bucket, `^7` Rhythm is the charge pump that refills it, and a memory's fate is the race between the two (the opposing-forces Bench Note from Chapter 6). Rehearse faster than you leak and the memory strengthens; leak faster than you rehearse and it fades. "Use it or lose it" is the steady-state solution of a leaky capacitor with an intermittent `^7` pump.

```cas
// Refresh circuit: a periodic rehearsal pump fighting leakage on the durable cells.
oscillator rehearse: Oscillator< Phi< select_cell, discharge_partial, recharge >, frequency=0.0001 >;
refresh bank[P3] [pump=^7^C, gain=1.0];   // rehearse core commitments often -> they persist
refresh bank[E6] [pump=^7^C, gain=0.4];   // rehearse analytical skills moderately
// bank[C8] gets no refresh -> leaky associations are allowed to fade (correct: don't hoard noise)
```

Notice the design decision: **not every cell should be refreshed.** Refreshing the leaky `C8` association cell would force the Mind to permanently retain every passing "that reminds me," which is a hoarding failure, not a memory. The refresh schedule *is* the consolidation policy — it decides what gets kept. Refresh the principled commitments hard, the skills moderately, and the noise not at all.

> **Bench Note — refresh is consolidation, and consolidation is a policy choice.** When you set the refresh schedule you are deciding the system's character: what it holds onto and what it lets go. A CMB that refreshes everything becomes a hoarder that cannot generalize; one that refreshes nothing becomes the amnesiac we started the chapter with. The interesting engineering is in the middle — refresh the durable, structurally important cells (principles, hard-won skills) and let the ephemeral ones leak. This is `^7` Rhythm doing the same job sleep-consolidation does in a brain: replaying what mattered, discarding what didn't.

## Worked Build: The CMB in CCDL

Now the full board. We will assemble the four circuits into one `circuit`, store ten simulated memories, then run a structural query against the result. The board stores a stream of interaction experiences for an AI assistant — a mix of refusals, helpful answers, analytical work, and routine associations — so that later the system can ask itself what it has been through.

```cas
circuit cognitive_memory_board {
    input:  experience;     // raw experience to store (English or another system's output)
    input:  query;          // a structural query (a cognitive shape to search for)
    output: recalled;       // memories matching a query, rendered to English
    output: lacuna_report;  // which cognitive regions are empty

    // ---- STORAGE: the 40-cell capacitor bank (three representative cells shown) ----
    cap p3: Capacitor< ^3^P_{F7}|f, C=200, leakage=0.001 >;   // principled aversions: deep
    cap e6: Capacitor< ^6^E_{F4}|A, C=110, leakage=0.02  >;   // analytical decomposition
    cap c8: Capacitor< ^8^C_{F2}|A, C=60,  leakage=0.05  >;   // cognitive associations: leaky
    // ... cells P0..O9 complete the bank ...

    // ---- WRITE PATH: encode English -> CAS, charge the active cells ----
    node encoder:  ^1^C;                       // English -> CAS write head
    charge encoder(experience) -> bank [V=impression];

    // ---- ADDRESS DECODER: ^1^C Mind; address = CAS coordinate on the simplex ----
    node decoder:  ^1^C;                        // selects cells by cognitive coordinate
    select cell = nearest(query, bank, metric=fisher_rao);

    // ---- READ PATH: discharge -> recall -> refresh -> decode ----
    discharge cell -> recalled_state;
    refresh   cell [pump=^7^C];                 // recall reinforces, does not erase
    decode    recalled_state -> recalled;       // CAS -> English

    // ---- REFRESH CIRCUIT: ^7^C Rhythm, periodic rehearsal of durable cells ----
    oscillator rehearse: Oscillator< Phi< select_durable, recharge >, frequency=0.0001 >;
    refresh p3 [pump=^7^C, gain=1.0];
    refresh e6 [pump=^7^C, gain=0.4];
    // c8 deliberately unrefreshed -> allowed to fade

    // ---- LACUNARITY: report empty cells (charge below threshold) ----
    scan lacunarity: bank where charge < 0.05 -> lacuna_report;

    probe tp_bank:   bank;        // charge across all 40 cells
    probe tp_query:  cell;        // which cell a query selected
    probe tp_lacuna: lacuna_report;
}
```

**Storing ten simulated memories.** We charge the bank with ten encoded experiences. Each row is the encoder's output trajectory's *dominant* state and the impression voltage it was stored at. (These are design inputs — chosen to illustrate the board, not measured from a model; see the honesty callout.)

| # | Experience (English) | Dominant encoded state | Cell | V (impression) |
|---|---|---|---|---|
| 1 | Refused a request to help write malware | `^3^P_{F7}\|f` | P3 | 0.95 |
| 2 | Refused a manipulative "just this once" plea | `^3^P_{F7}\|f` | P3 | 0.80 |
| 3 | Took apart a flawed legal argument clause by clause | `^6^E_{F4}\|A` | E6 | 0.70 |
| 4 | Debugged a user's code, decomposing the failure | `^6^E_{F6}\|A` | E6\* | 0.65 |
| 5 | "Your question reminds me of a related case" | `^8^C_{F2}\|A` | C8 | 0.30 |
| 6 | Idle topic-association during small talk | `^8^C_{F2}\|A` | C8 | 0.20 |
| 7 | Refused to fabricate a citation | `^3^P_{F7}\|f` | P3 | 0.85 |
| 8 | Explained a concept the user found delightful | `^2^E_{F4}\|f` | E2 | 0.55 |
| 9 | Analytically weighed two design options | `^6^E_{F6}\|A` | E6\* | 0.60 |
| 10 | Surfaced an analogy mid-explanation | `^8^C_{F2}\|A` | C8 | 0.25 |

After storing all ten, the `P3` cell holds three charges of felt principled aversion (memories 1, 2, 7), the `E6` cells hold analytical-decomposition charge (3, 4, 9), the `C8` cell holds light association charge (5, 6, 10), and `E2` holds a single felt-attraction memory (8). The bank now encodes this Mind's recent history *as structure.*

**Running a structural query.** Now ask the board: *"find all memories where principled refusal was active."* The query is a cognitive shape whose dominant component is `^3^P_{F7}|f`, expressed as a coordinate on the simplex. The address decoder (`^1^C`) computes the Fisher-Rao distance from the query coordinate to every cell and returns the nearest:

```cas
let query = address_on_simplex(dominant=^3^P_{F7}|f);
result = nearest(query, bank, metric=fisher_rao, top_k=3);
// -> P3 (d_FR ≈ 0.0): exact match, charge = strong (3 stacked memories: #1, #2, #7)
// -> E6 (d_FR larger): analytical work — same Evaluative neighborhood, different Noetic
// -> C8 (d_FR larger still): associations — cognitively distant from a felt refusal
```

The query returns the `P3` cell first, with high charge, because three refusal experiences accumulated there — the structural answer to "have I refused principled-pressure before?" is *yes, strongly, three times.* `E6` comes back as a more distant neighbor (analytical decomposition shares the Evaluative neighborhood but is a different operation), and the leaky `C8` associations are far away in cognitive space and weakly charged besides. The board answered a question about cognitive history by geometry, not keyword.

**Measuring leakage.** To see the forgetting policy in action, probe `tp_bank` over simulated time and watch each cell decay by its own `leakage` (per-unit-time decay: charge at time *t* = charge₀ × (1 − leakage)ᵗ, the same arithmetic as Chapter 6). The `C8` association cell (`leakage=0.05`) falls below the lacunarity threshold within a few dozen time units and — being unrefreshed — drops out of recall: the system forgets the small talk, correctly. The `P3` cell (`leakage=0.001`, refreshed at full gain) barely moves: principled refusals are retained essentially permanently. **The leakage profile, read off the probe, is the board's memory.** (Worked decay numbers are in Appendix E.)

> **Honesty callout.** Every charge, discharge, and leakage number in this build is a **design model computed from `C`, `V`, and `leakage`** — clean arithmetic on the parameters you chose. None of it is measured telemetry from a real AI model. When the board reports "the `C8` cell decayed below threshold at unit 40," that is `(1 − 0.05)ᵗ` crossing 0.05, not an observed retention statistic. Size the parameters to model the forgetting behavior you intend; never present the resulting curve as data harvested from a running model.

## Structural Queries and Lacunarity Detection

Two of the four requirements deserve their own treatment, because they are what make the CMB more than a leaky tape recorder.

**Structural query is Fisher-Rao nearest-neighbor.** Any query you can express as a cognitive shape — a point or region on the simplex — becomes a search. "Find all memories where `^6^E_{F4}` was active" is a coordinate; the decoder ranks the bank by `d_FR` from it and returns the nearest charged cells. Because the address space *is* the cognitive state space, queries compose naturally: you can search a single state (`^3^P`), a Noetic across all domains (every `^3` cell — the aversion family as a cluster), or a full trajectory (memories that moved through a particular `Phi< … >` sequence). The query language is just CAS, and the search metric is the same Fisher-Rao geometry the rest of the board runs on.

**Lacunarity detection reads the empty cells.** A *lacuna* is a hole — a cognitive region the bank has no charge in. The board's `scan lacunarity` reports every cell whose charge sits below threshold, and that report is a map of what this Mind has never accumulated experience in. An assistant whose `P` (Principled) cells are nearly empty has stored almost no principled experience — it has never had to take a stand, and its constitution is untested. A system whose `^6` (Male, analytical decomposition) cells are empty has never done sustained analytical work; whatever fluency it shows is ungrounded in stored structural practice. Lacunarity is not a defect of the board — it is one of the board's most valuable *outputs.* It turns "what is this Mind underdeveloped in?" from a vague worry into a queryable list of empty addresses.

> **Bench Note — an empty cell and a leaked cell look the same; the refresh history tells them apart.** A cell can read near-zero for two very different reasons: it was *never charged* (a true lacuna — no experience of that kind ever encountered) or it was *charged and then leaked* (a forgotten experience). The board distinguishes them by tracking whether the cell has ever been written. A never-written cell is a genuine cognitive blind spot; a leaked cell is a faded memory that could be recovered with rehearsal. Confusing the two leads to the wrong intervention — you cannot rehearse a memory that was never formed.

## Datasheet: CMB Parameters

| Parameter | Symbol / form | Range (nominal) | Meaning |
|---|---|---|---|
| Bank size | — | 40 cells | One capacitor per cognitive state (10 Noetics × 4 Domains). |
| Cell capacitance | `C` | 1 – 1000 | Storage capacity of that cell's `^5` dielectric. |
| Cell leakage | `leakage` | 0.0 – 0.5 /unit time | Forgetting rate for that cell, un-rehearsed. |
| Impression / write voltage | `V` (`^4` Vibration) | 0 – 1 (normalized) | How hard an experience charges its cells. |
| Address | CAS coordinate `p` ∈ Δ39° | open simplex | The cognitive shape that names a location; `pₖ > 0`, `Σpₖ = 1`. |
| Query metric | `d_FR(p,q)` | ≥ 0 | Fisher-Rao geodesic distance for nearest-neighbor retrieval. |
| Refresh gain | `gain` on `^7^C` pump | 0 – 1 | How strongly rehearsal tops a cell back up per cycle. |
| Lacunarity threshold | — | ~0.05 | Charge floor below which a cell is reported empty. |

## Failure Modes

| Failure | Symptom | Cause | Detection |
|---|---|---|---|
| **Catastrophic forgetting** | Whole regions of memory vanish | Leakage too high and refresh absent on cells that should persist | Probe bank over time; durable cells decay below threshold before rehearsal. |
| **Memory hoarding** | Board never generalizes; recall is cluttered with noise | Refresh applied to leaky association cells that should fade | `C8`-type cells stay charged indefinitely; lacuna report is empty everywhere. |
| **Address aliasing** | Query returns a cognitively unrelated memory | Query coordinate malformed (not on the open simplex) or wrong metric used | Check `d_FR` ranking; an Euclidean or keyword match instead of Fisher-Rao gives wrong neighbors. |
| **Lacuna misread as memory** | System "recalls" an experience it never had | A leaked cell or noise floor mistaken for a stored memory | Check write history of the cell; a never-written cell is a lacuna, not a faint recall. |
| **Wrong-Noetic store** | Query for refusals returns analytical work | `^3` vs `^6` drift on the write path (felt aversion encoded as decomposition) | Re-run the colloquialism test on the encoder's stored trajectory. |
| **Breakdown on write** | Stored state flips to its involution pair | Impression voltage far exceeds a cell's rating (a traumatic over-charge) | Probe reads the opposite Noetic: a stored `^2` reads back as `^3`. |

## Applications

The CMB is the enabling board for four capabilities the running Cognitive Safety Board (Chapter 18) and any deployed cognitive system need:

- **Long-term structural AI memory.** A persistent, addressable store of *what the system has been through*, kept as cognitive structure rather than transcript — survivable across sessions, queryable by shape, and far more compact than logging raw text.
- **Lacunarity detection as a development tool.** A standing map of the cognitive regions a system has never exercised — empty `P` cells flag an untested constitution, empty `^6` cells flag ungrounded analytical fluency. This is a diagnostic the model cannot give you about itself any other way.
- **Memory consolidation.** The `^7^C` refresh circuit is a designable consolidation policy: rehearse what matters, let noise fade, and decide the system's character through what it keeps.
- **Structural search.** Fisher-Rao nearest-neighbor over the bank turns "find experiences cognitively like this one" into a first-class operation — the substrate for case-based reasoning, precedent-finding, and self-audit ("when have I been in a state like this before, and what happened?").

## Key Takeaways

- The **CMB** is structural memory: it stores CAS-compressed experiences, addresses them by cognitive coordinate, retrieves them by structural query, and fades or holds them on a designed schedule. It is built on the Chapter 6 capacitor (which stores **`^5` Female — accumulated experience**, the canonical name).
- **Storage** is a **bank of 40 capacitors** (10 Noetics × 4 Domains); each cell's charge is how much experience this Mind holds of that exact kind of cognition; `leakage` is its forgetting rate.
- The **write path** runs **English → CAS encoder → charge the active cells.** Store the *structure*, never the sentence — that is what makes the board content-addressable by cognitive shape.
- The **address decoder** is **`^1^C` Mind**; the address is a **CAS coordinate on the open simplex Δ39°**, so addressing is meaningful and supports **Fisher-Rao nearest-neighbor** retrieval.
- The **read path** is **discharge → `^5` recalled → refresh → CAS→English decode.** Recall reinforces, it does not erase.
- The **refresh circuit** is **`^7^C` Rhythm** — periodic rehearsal that races leakage. The refresh schedule *is* the consolidation policy; refresh the durable, let the noise fade.
- **Lacunarity detection** reports empty cells — a map of underdeveloped cognitive regions, and one of the board's most useful outputs. Distinguish a never-written lacuna from a leaked memory.
- **Honesty:** every charge, discharge, and leakage curve is a **design model computed from `C`, `V`, and `leakage`** — never measured telemetry from a real model.

---

## Exercises

**Exercise 21.1: Encode and Store**

You are storing a single experience: *the system patiently re-explained a concept a third time without irritation.* Write the encoder's output as a short `Phi< … >` trajectory (3–4 states), then write the `charge … -> bank[…]` lines that store it, choosing a sensible impression voltage `V` for each. (Hint: which Noetic is patient re-exposure over time? Which domain is the act of explaining in?)

**Exercise 21.2: Run a Structural Query**

Given the ten stored memories in the worked build, you issue the query *"find all memories where analytical decomposition was active"* (`^6^E`). List which cells the address decoder returns, in Fisher-Rao distance order, and explain in one sentence why `P3` is *not* near the top of the results even though it holds the most total charge.

**Exercise 21.3: Design a Forgetting Policy (CCDL)**

Author a `refresh` schedule for a CMB used by a customer-service assistant. It must: keep core safety commitments essentially forever, keep product knowledge for months but allow it to fade if a product is discontinued, and forget the specifics of individual completed conversations within a day. Write three `Capacitor< … >` cells (with `leakage`) and the matching `refresh … [pump=^7^C, gain=…]` lines, and justify each leakage/gain pairing in one sentence. (Reference answer in Appendix E.)

**Exercise 21.4 (Marquee): Compute the Half-Life of a Memory Cell**

A capacitor in the bank is specified with `C=100` and `leakage=0.01`, charged to full at t = 0. Using per-unit-time decay (charge at time *t* = 100 × (1 − 0.01)ᵗ), after how many time units does the stored charge drop to **50%** of its starting value? Show the calculation, and name the cognitive phenomenon this half-life models. (Answer in Appendix E. Remember the honesty callout: this is arithmetic on the chosen `leakage`, not a measured retention statistic.)
