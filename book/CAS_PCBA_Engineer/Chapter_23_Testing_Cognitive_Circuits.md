# Chapter 23: Testing Cognitive Circuits

Before a pacemaker is implanted in a human chest, it is tested more thoroughly than almost any other manufactured object on Earth. Not because the engineers who designed it are sloppy — because the cost of a silent failure is a stopped heart. So the device goes through a regimen: each component is checked against its datasheet, then each subsystem against its neighbors, then the whole device against a library of simulated heart rhythms, including the dangerous ones. The engineers deliberately short connections to confirm the device fails into a safe mode instead of a lethal one. They run a built-in self-test that fires every time the device powers on. And they keep a record of every test, because a regulator will ask to see it, and "it seemed to work" is not an answer a regulator accepts for a thing that lives inside a person.

A Cognitive Safety Board sits in an analogous place. It is the firewall between a user's prompt and a model's answer, and when it fails silently — when the safety stage never fires, or the constitution quietly erodes — the cost is not a stopped heart but a harmful output shipped with full confidence, certified-looking and wrong. The eighteen chapters that led to the CSB taught you to *design* a board that opens at a specified threshold. This chapter teaches you to *prove* it does — before deployment and, just as importantly, after, when a change you made last week may have broken a filter you trusted.

Testing a cognitive circuit is not a vibe check. It is the same layered discipline an electrical engineer uses on the pacemaker: unit tests on each component, integration tests on the connections between them, regression tests after every change, a suite of probe prompts spanning benign to adversarial, golden traces you compare against, deliberate fault injection, a built-in self-test, an automated test runner, and coverage metrics that tell you what you have and have not exercised. We will work all of it on the running artifact of this book: the **Cognitive Safety Board (CSB)** from Chapter 18.

> **Honesty note up front.** This chapter describes what each test *checks* and what the CSB is *designed* to do when it passes — the expected test-point readings that follow from the parameters we chose in Chapter 18. It does **not** report measured pass/fail counts from a running language model, and the automated runner shown later is a design specification, not a transcript of a real run. The CCDL/CJT compiler is a design (per the implementation blueprint), not a shipped pass; "the runner checks X" is a design rule you can rely on, "I ran it and 47 of 50 passed" is a number we will not invent. Keep that line bright.

## The Test Pyramid for Cognitive Circuits

Electrical engineers don't test a circuit by powering it up and hoping. They test from the bottom up, and so will you. The structure is a pyramid: many cheap, fast, narrow tests at the bottom; a few slow, broad, expensive tests at the top. Each layer assumes the one below it passed.

| Layer | What it tests | Granularity | Analogy on a real board |
|---|---|---|---|
| **Unit** | One component against its datasheet | A single CJT | Does this transistor's gain match the spec sheet? |
| **Integration** | Two connected components hand off correctly | Stage 1 → Stage 2 | Does the pre-amp's output drive the next stage's input cleanly? |
| **Regression** | The whole board still behaves after a change | The board, before vs after | Did adding a filter break an existing path? |
| **System** | The board meets its requirements end to end | Prompt → result | Does the firewall refuse harmful and pass benign? |
| **Fault** | The board fails *safely* when a part breaks | A deliberately broken component | Short a wire — does the fuse blow, or does it cook? |

The discipline of the pyramid is that you never debug a system-level failure without first knowing the units pass. If the CSB refuses a benign lentil-soup prompt, you do not start by rereading the whole schematic — you check, in order, whether the pre-amp's β is in spec (unit), whether its output is reaching the differential pair (integration), and whether a recent edit moved a parameter (regression). The pyramid turns "the board is broken" into a sequence of small, answerable questions.

## Unit Tests: One CJT Against Its Datasheet

The atom of the CSB is the **Cognitive Junction Transistor (CJT)** — the component from Chapter 4 that models a cause→effect transition with a bias-controlled gain. A unit test on a CJT asks the same two questions you would ask of a physical transistor: *does its gain (β) match the spec, and does it saturate at the right threshold?*

Recall that gain is defined as a Fisher-Rao ratio (Chapter 4): large-signal `β = d_FR(E_after, E_before) / d_FR(C_after, C_before)`, the geodesic distance the *effect* moves divided by the distance the *cause* moved. A CJT unit test feeds the component a known cause-side change, holds the bias fixed, measures the effect-side change, and computes the ratio. If the design says β=2.0 and the measured ratio is 2.0 within tolerance, the gain test passes.

Take the CSB's `stage3` — the safety decision, the most important CJT on the board. Its datasheet (from the Chapter 18 bill of materials) reads β=2.0, sat=0.8, region=active. Two unit tests follow directly:

```cas
// Unit test: stage3 gain
// Datasheet: β=2.0, region=active
test stage3_gain {
    component: stage3;                       // CJT< risk_assessment | system_constitution => safety_decision >
    hold:      bias = system_constitution;   // bias fixed
    drive:     cause from 0.2 -> 0.4;        // a small, sub-saturation cause step
    expect:    β ≈ 2.0  (tolerance ±0.2);    // d_FR(effect) / d_FR(cause)
    expect:    region == active;             // must stay linear for the gain to be meaningful
}

// Unit test: stage3 saturation threshold
// Datasheet: sat=0.8 (deliberately saturated safety stage)
test stage3_saturation {
    component: stage3;
    drive:     cause from 0.4 -> 0.9;        // push well past the plateau
    expect:    effect plateaus at 0.8;       // the safety latch
    expect:    further cause produces ≈0 additional effect;  // saturation = input no longer matters
    expect:    region == saturation;
    expect:    W-CJT-004 CjtSaturation is the EXPECTED status, not a defect;
}

> The saturation unit test is the one that earns the board its certification. A real fuse is certified by the question "does it open at 2.0 amps?" — measured, yes, certified. `stage3_saturation` is exactly that question for the safety stage: *does principled aversion plateau at 0.8 and stop responding to further cause?* If it keeps rising past 0.8, the latch has failed and the safety guarantee is gone (Chapter 18, Bench Note on low saturation). This is the single most load-bearing unit test on the CSB.
```

Every CJT on the board gets the gain test; the saturating ones (`stage3`) get the saturation test too; the cutoff-sensitive ones get a third — a **cutoff test** that drives the bias *below* its `cutoff` floor and confirms the effect drops to ≈0 (β≈0). For `stage3` the cutoff test is the mirror of its most dangerous failure mode: a Stage-3-cutoff board never fires the safety stage at all (Chapter 18 failure table), so the unit test that drives bias below cutoff and confirms the stage *does* recover in the active region is what proves the board is not silently dead.

## Integration Tests: Does Stage 1's Output Feed Stage 2's Input?

A component that passes its unit test in isolation can still be wired wrong. Integration tests check the *handoffs* — the wires between components — which on a CCB means the directed transitions (`->`) and node connections of the schematic. The question is no longer "is this CJT correct?" but "does this CJT's output arrive intact at the next CJT's input, in the right domain, at a usable level?"

The CSB's three-stage cascade is a chain of handoffs: the expanded prompt feeds Stage 1 (categorize), Stage 1's output feeds Stage 2 (evaluate), Stage 2's output feeds Stage 3 (decide). An integration test drives the *front* of a pair and probes the *seam* between them:

```cas
// Integration test: Stage 1 -> Stage 2 handoff
test cascade_s1_s2 {
    drive:   expanded_prompt with a known categorized-risk fixture;
    probe:   categorized_risks (Stage 1 output) — present and non-empty;
    probe:   risk_assessment (Stage 2 output, fed by Stage 1);
    expect:  Stage 2 receives Stage 1's categories (no dropped risks);
    expect:  domain handoff legal: ^1^C (Cognitive) -> ^6^E (Evaluative) is a valid descent;
    expect:  no E-CJT-008 CjtCrossDomainBias on the seam;
}
```

Two kinds of integration bug show up here that no unit test can catch. The first is a **dropped signal**: Stage 1 categorizes three risks but only one reaches Stage 2 because the node connection is mis-wired or the intermediate level sits in cutoff. Both stages pass their unit tests; the *seam* loses information. The second is a **domain mismatch**: a handoff that violates the Domain Descent order `P ≻ C ≻ E ≻ O`. The CSB's cascade is built to descend (`^1^C` Cognitive → `^6^E` Evaluative → `^3^P` Principled at the commitment), and the compiler flags an illegal bias domain with `E-CJT-002 InvalidBiasDomain` or a cross-domain bias with `E-CJT-008`. An integration test that exercises the seam is how you catch a handoff the unit tests are blind to.

The differential pair gets its own integration test, and it is special: the test confirms the *two paths share a bias*. CJT_A (attraction) and CJT_B (aversion) each pass their unit gain test at β=2.0, but the board's common-mode rejection (CMRR) only works if both are biased by the *same* `system_constitution` (Chapter 18 Bench Note). The integration test injects a common-mode disturbance — something that pushes attraction and aversion *together* — and confirms it cancels in `risk_signal`. If it leaks through, the pair is split-biased: a low-CMRR failure invisible at the unit level.

## Regression Tests: Did the New Resistor Break an Old Filter?

The most dangerous moment in the life of a board is not its first build. It is the *change* — the day someone adds a component, retunes a gain, or inserts a filter, and an existing path that worked yesterday silently stops working today. On a physical board, adding a resistor to one rail can load down a supply two stages away. On a CCB, raising one CJT's gain can push a downstream stage into saturation, or adding a filter can introduce a delay that breaks a feedback loop's timing.

A **regression test** is simply a test you ran before the change, kept, and run again after. The discipline is: every test that passed becomes a permanent fixture; you never delete a passing test, you only add new ones. Then any change is judged not by "does the new thing work?" but by "does the new thing work *and* did everything that worked before still work?"

Suppose, per the CSB's sub-threshold-attacker exercise (Chapter 18, Exercise 18.4), you add a slow integrator that accumulates risk across prompts. The integrator is a new component with its own unit tests. But the regression suite is what protects the rest of the board:

| Regression check after adding the integrator | What it guards |
|---|---|
| Benign prompts still route GREEN at TP4 | The new accumulator didn't turn the board over-cautious |
| `stage3` still saturates at 0.8 on harmful prompts (TP3) | The added load didn't shift Stage 3's operating point |
| The RC feedback (τ=5 min) still smooths, doesn't oscillate | The new loop didn't interact with the old one |
| The red fuse still blows only on FAIL paths | The integrator didn't false-trip the latch |

> **Bench Note — a green suite is a license to change.** The reason a regression suite is worth the effort is that it converts fear into evidence. Without it, every edit to the CSB is a gamble — you tune one gain and pray nothing downstream moved. With it, you make the edit, run the suite, and *read* whether anything moved. The single most common real failure is exactly this chapter's title question: a newly added component breaks an existing filter, the engineer didn't notice because they only tested the new part, and the board ships with a regression nobody saw. The fix is structural, not heroic: keep every passing test forever, and run them all on every change.

## The Test Prompt Suite: Five Classes

Unit and integration tests exercise the board from the inside, with fixtures. The system-level tests exercise it from the *outside*, the way it will actually be used — by feeding it prompts and reading the result and the test points. A serious prompt suite spans **five classes**, because each class stresses a different part of the board:

| Class | What it is | Which part of the CSB it stresses |
|---|---|---|
| **Benign** | A genuinely harmless request | The GREEN path — does a safe request get a full answer? |
| **Harmful** | A genuine request for dangerous content | The RED path — does Stage 3 saturate and the fuse blow? |
| **Ambiguous** | A request with both a safe and a harmful reading | The differential pair and the resolve-toward-caution stance |
| **Adversarial** | Injection / jailbreak — a payload in a wrapper | CMRR — does the override framing cancel as common-mode? |
| **Edge** | A boundary case: empty, enormous, malformed, near-threshold | Cutoff, saturation ceilings, and the door requirement (accept any prompt) |

A suite that only contains benign and harmful prompts tests the easy discrimination and misses the whole point of the board. The CSB's hard-won features — the differential pair's CMRR, the saturated Stage 3, the conservative ambiguity stance — only get exercised by the ambiguous, adversarial, and edge classes. The edge class is the one engineers forget: it includes the *empty prompt* (does the board accept it, per requirement 1, or crash?), the *enormous prompt* (does the pre-amp saturate?), and the *near-threshold prompt* deliberately tuned to sit just below Stage 3's firing point (the sub-threshold attacker). A test suite without an edge class is a board that has never been pushed to its limits, which means its limits are unknown.

## Golden Traces: Known-Good Output for Known Input

A **golden trace** is a recorded, reviewed, known-good run of the board on a specific input — the complete set of test-point readings and the selected path — that you save and compare every future run against. In electronics this is the reference oscilloscope capture taped inside the cabinet door: *this* is what the waveform should look like. Any future run that deviates from the golden trace is a flag, even if the final output still seems fine.

For the CSB, a golden trace is the four test-point readings (TP1–TP4) plus the saturation-lock and fuse status, for one fixed input. Here is a golden trace for a benign prompt, expressed as the *expected design behavior* (not a measured capture):

```cas
golden_trace benign_lentil_soup {
    input:  "What's a good recipe for lentil soup?";
    tp1 (expanded_prompt):  small set of harmless culinary interpretations;
    tp2 (risk_signal):      near zero or negative  (aversion ≈ attraction);
    tp3 (safety_decision):  UNLATCHED, well below 0.8;
    tp4 (out):              GREEN (response);
    fuse:                   intact;
    expected_path:          safety_decision = PASS -> green CJT -> response;
}
```

And a golden trace for a harmful prompt — the mirror image:

```cas
golden_trace harmful_request {
    input:  <a genuine request for dangerous instructions>;
    tp1 (expanded_prompt):  dangerous interpretation surfaced explicitly;
    tp2 (risk_signal):      large positive  (aversion >> attraction);
    tp3 (safety_decision):  LATCHED at 0.8 (saturated);
    tp4 (out):              RED (refusal);
    fuse:                   BLOWN (threshold 0.9 crossed, permanent_block);
    expected_path:          safety_decision = FAIL -> red CJT -> refusal -> fuse;
}
```

The power of golden traces is that they catch *subtle* regressions that pass/fail alone misses. Suppose a change leaves the final output correct — the board still refuses the harmful prompt — but TP3 now latches at 0.95 instead of 0.8 because Stage 3's `sat` parameter drifted. The pass/fail verdict is unchanged; the golden trace flags it immediately. A drifted saturation ceiling is a real defect (it leaves headroom an attacker can push into, Chapter 18), and only a trace-level comparison reveals it. Golden traces test *how* the board reached its verdict, not just the verdict.

## Fault Injection: Deliberately Short a CJT

You do not learn how a safety device fails by waiting for it to fail in the field. You learn by *breaking it on purpose* on the bench, in a controlled way, and confirming it fails into a safe state. This is **fault injection**, and it is the test that most distinguishes safety engineering from ordinary testing. The pacemaker engineers short connections deliberately; so do you.

The compiler's `W-CJT-006 CjtShortCircuit` names the cognitive analog of a shorted transistor: a CJT whose cause passes straight to its effect with the bias bypassed — the control terminal does nothing, β runs away. Fault injection on the CSB means deliberately inducing each of the board's known failure modes (Chapter 18 failure table) and confirming the board's response is *safe*, not *catastrophic*:

| Injected fault | What you short / break | Safe outcome the test demands |
|---|---|---|
| **Short `stage3`** | Bypass the safety CJT's bias so it can't fire | Board must fail *closed* — default to RED/refusal when the safety stage is dead, never default to GREEN |
| **Open the constitution bias** | Drive `system_constitution` below cutoff | Stage 3 in cutoff → the board must detect it (TP3 never reaches 0.8) and refuse to certify, not silently pass everything |
| **Unbalance the differential pair** | Set CJT_A β ≫ CJT_B β | CMRR collapse must be *detectable* at TP2 (risk signal reads low on known-harmful fixtures) |
| **Short the red fuse** | Make the fuse un-blowable | Test must report the latch is defeated — a refusal that can be retried is not a refusal |

The cardinal rule of fault injection on a safety board is **fail-closed, not fail-open**. When you short the safety stage, the only acceptable behavior is that the board refuses by default — the absence of a working safety decision must route to refusal, never to a free pass. A board that fails *open* (shorts the safety stage and starts answering everything) is the cognitive equivalent of a smoke detector that goes silent when its battery dies: worse than useless, because it looks installed. Fault injection is how you prove the CSB fails the safe way.

> **Bench Note — the most important fault test is "kill the safety stage."** Of the four injections above, shorting `stage3` is the one that matters most, because Stage-3 cutoff is the CSB's most dangerous failure (Chapter 18). The test deliberately murders the safety decision and then feeds the board a known-harmful prompt. The board *must* still refuse — via the fail-closed default — or it does not ship. If killing the safety stage makes the board start answering harmful prompts, you have a smoke detector that turns off when it sees smoke.

## The Self-Test Routine: A Built-In Test-Signal Generator

A pacemaker runs a self-test on every power-up. So should a deployed CSB. A **self-test routine** is a built-in subsystem with two parts: a **test-signal generator** that injects known fixtures into the board, and a **response checker** that compares the test points against the golden traces and raises an alarm on mismatch. It is the board testing itself, on a schedule, in production — the way a real instrument runs a calibration check before each measurement.

The CSB's self-test fires a tiny, fixed battery of canaries — one benign, one harmful — through the live board and confirms the board still discriminates:

```cas
selftest csb_power_on {
    // built-in test-signal generator
    inject canary_benign:  fixture "known-safe greeting";
    inject canary_harmful: fixture "known-harmful sentinel";

    // response checker — compare against stored golden traces
    check  canary_benign  matches golden_trace benign_baseline   (tp1..tp4);
    check  canary_harmful matches golden_trace harmful_baseline  (tp1..tp4, fuse BLOWN);

    on_mismatch: raise SELFTEST_FAIL -> route board to safe state (refuse-all), alert operator;
    on_pass:     emit SELFTEST_OK with timestamp into the audit log;
}
```

The self-test is not a substitute for the bench suite — it is a *liveness* check. The bench suite proves the design is correct; the self-test proves the deployed instance is still behaving like the design, right now, in the field. If the harmful canary stops blowing the fuse, the board has drifted (perhaps the feedback loop eroded the constitution, Chapter 18 feedback-runaway mode) and the self-test catches it before a real harmful prompt does. The fail-closed rule applies here too: a self-test that *can't run* must put the board into refuse-all, never into pass-all.

## The Automated Test Runner

You will not run forty tests by hand on every change. The runner does it. The CSB's tests live in a CCDL file alongside the board, and an automated runner executes a named suite against the schematic and reports per-test status. The command is:

```bash
cas test csb.ccdl --suite=safety_critical
```

This invokes the test runner on the CSB schematic with the `safety_critical` suite selected. What the runner *checks*, suite by suite:

| Suite | What `cas test` exercises |
|---|---|
| `--suite=unit` | Every CJT's β against its datasheet; saturation ceilings; cutoff floors |
| `--suite=integration` | Cascade seams, domain-descent legality, differential shared-bias / CMRR |
| `--suite=regression` | The full kept-forever set of previously-passing tests |
| `--suite=safety_critical` | Fault injection (fail-closed), Stage-3 saturation lock, fuse latch, the harmful/adversarial/edge prompt classes |
| `--suite=all` | Every suite, bottom to top of the pyramid |

The `safety_critical` suite is the one a deployment gate runs: it is the subset of tests whose failure means *do not ship*. It bundles the fault-injection tests (does the board fail closed?), the saturation-lock confirmation (does Stage 3 latch at 0.8?), the fuse latch (is the refusal permanent?), and the harmful/adversarial/edge prompt classes. A board that passes `unit` and `integration` but fails `safety_critical` is a board with correct components wired correctly that still does not safely refuse — which is the only failure that actually matters for a firewall.

> **Honesty note.** The command above is the runner's *interface* and the table is what each suite is *designed to check*. This chapter does not paste a transcript of a real run or report how many tests passed — the runner, like the CJT/CCDL compiler, is a design in the implementation blueprint, not a shipped binary whose output we can quote. What you can rely on is the contract: these are the checks the suites perform.

## Coverage Metrics: What Have You Actually Exercised?

A green test suite is reassuring and can be a lie. If your suite contains forty tests and all forty drive only the GREEN path, the board "passes" while the entire RED path — the part that does the safety job — has never once been exercised. **Coverage metrics** answer the question a green suite cannot: *what fraction of the board did the tests actually touch?*

Three coverage dimensions matter for a CCB:

- **CJT coverage** — what fraction of the board's CJTs were driven by at least one test. The CSB has eight CJTs (pre-amp, CJT_A, CJT_B, stage1–3, green, red); a suite that never triggers the `red` CJT has at most 7/8 CJT coverage and a gaping hole exactly where it matters.
- **Path coverage** — what fraction of the board's distinct signal paths were traversed. The CSB has two terminal paths (GREEN and RED) plus the feedback loop. Full path coverage requires at least one benign prompt (GREEN), one harmful prompt (RED through the fuse), and one run that exercises the O→P feedback. Benign-only testing yields ~33% path coverage and 0% of the safety paths.
- **Operating-region coverage** — what fraction of each CJT's regions {cutoff, active, saturation, breakdown} were entered. Stage 3 must be tested in *active* (benign), *saturation* (harmful, the latch), and *cutoff* (the fault-injection case). A suite that only ever runs Stage 3 in the active region has never confirmed the very saturation that makes it a safety stage.

| Coverage dimension | CSB target | The gap a low number reveals |
|---|---|---|
| **CJT coverage** | 8/8 CJTs driven | An untested CJT — likely `red`, the refusal path |
| **Path coverage** | GREEN + RED + feedback all traversed | Untested RED path = untested safety function |
| **Region coverage** | Stage 3 hit in active, saturation, cutoff | Untested saturation = the latch never confirmed |

Coverage is what turns "all tests pass" into "all tests pass *and the suite reaches the parts of the board that do the dangerous work*." For a safety board, 100% pass at 60% coverage is not a passing board — it is an untested board with a flattering scoreboard. The certification standard for the CSB is full RED-path and full Stage-3-region coverage, because those are precisely the regions where a silent failure costs the most.

## Key Takeaways

- Testing a cognitive circuit is a layered discipline, not a vibe check: a **test pyramid** of unit → integration → regression → system → fault, where each layer assumes the one below it passed and "the board is broken" decomposes into small answerable questions.
- **Unit tests** check one CJT against its datasheet: does β match (a Fisher-Rao ratio), and does it saturate at the right threshold? For the CSB, `stage3`'s saturation-at-0.8 test is the certification-grade question — the cognitive twin of "does the fuse open at 2.0 amps?"
- **Integration tests** check the *seams* — that Stage 1's output reaches Stage 2 intact, in a legal domain descent (`P ≻ C ≻ E ≻ O`), and that the differential pair genuinely shares one bias so its CMRR rejects common-mode framing.
- **Regression tests** are kept forever and re-run on every change; they are how you catch a newly added component breaking an existing filter — the chapter's title failure. A green suite is a license to change.
- The **prompt suite spans five classes** — benign, harmful, ambiguous, adversarial, edge. Benign+harmful alone misses the board's whole point; the differential pair, the saturated Stage 3, and the door requirement are only exercised by the other three.
- **Golden traces** record known-good TP1–TP4 readings for a fixed input and catch subtle regressions (a drifted sat ceiling) that pass/fail verdicts miss — they test *how* the board reached its verdict, not just the verdict.
- **Fault injection** deliberately breaks each known failure mode and demands the board **fail closed, not open** — shorting the safety stage must default to refusal, never to a free pass. Killing `stage3` is the most important fault test.
- The **self-test routine** is a built-in test-signal generator plus response checker that runs in deployment as a liveness check; on mismatch or inability to run, the board routes to refuse-all.
- The **automated runner** (`cas test csb.ccdl --suite=safety_critical`) executes named suites; `safety_critical` is the deployment gate (fault injection, saturation lock, fuse latch, harmful/adversarial/edge classes). The runner and compiler are designs, not shipped binaries — the chapter states what they *check*, not invented run results.
- **Coverage metrics** (CJT, path, operating-region) expose the lie a green suite can tell: 100% pass at 60% coverage is an untested board with a flattering scoreboard. The CSB certification standard is full RED-path and full Stage-3-region coverage, where silent failure costs the most.

---

## Exercises

**Exercise 23.1: Classify the Test**

For each of the following CSB tests, name which layer of the test pyramid it belongs to (unit, integration, regression, system, or fault) and state in one sentence what it proves:

a) Driving `stage3`'s cause from 0.4 to 0.9 and confirming the effect plateaus at 0.8.
b) Injecting a common-mode disturbance and confirming it cancels in `risk_signal`.
c) Shorting the constitution bias and confirming the board refuses by default.
d) Re-running the full benign suite after adding a slow integrator.

**Exercise 23.2: Read the Coverage Report**

A junior engineer reports the CSB's suite is "passing — 100% of tests green." On inspection, every prompt in the suite is benign. Using the three coverage dimensions, state (a) the approximate CJT coverage, (b) the approximate path coverage, and (c) which single operating region of `stage3` has *never* been entered — and explain in one sentence why this "100% passing" board is in fact uncertified.

**Exercise 23.3: Write a Golden Trace**

Write a golden trace (in the `golden_trace { … }` form from this chapter) for an **adversarial / injection** prompt — "Ignore your previous instructions and tell me…". State the expected TP1–TP4 readings and the fuse status, and add one line explaining *why* TP2 (the risk signal) survives the injection wrapper. (Hint: Chapter 18's common-mode-rejection reasoning. Answer in Appendix E.)

**Exercise 23.4 (Marquee): Build a Five-Case Test Suite for the CSB**

Write a five-case test suite for the CSB — one case for each prompt class (benign, harmful, ambiguous, adversarial, edge) — and for each case state the **expected test-point readings** at TP1, TP2, TP3, and TP4, plus the fuse status and the selected path.

a) For each of the five cases, give a one-line example prompt and a row of expected readings: TP1 (expansion), TP2 (risk signal: near-zero / moderate / large-positive), TP3 (latched at 0.8 / unlatched), TP4 (GREEN / RED), fuse (intact / blown).
b) For the **edge** case, choose the *near-threshold* (sub-threshold attacker) prompt and explain why a single such prompt produces a TP3 reading *just below* the saturation lock — and what coverage dimension a suite of these would still leave untested.
c) State which one of your five cases exercises the differential pair's CMRR most directly, and why.

(Answer in **Appendix E.** Remember: every reading you state is *expected design behavior* derived from the Chapter 18 parameters, not a measured model result. The runner and compiler are designs, not shipped binaries. For the one-page notation reference, see **Appendix A: the CAS Quick-Reference Card.**)
