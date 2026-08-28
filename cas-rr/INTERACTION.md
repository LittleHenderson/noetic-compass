# Testing and Interacting with the CAS Reasoning Machine

CAS-RR is one generic machine and a set of CAS-encoded problems. You
interact with it three ways: the test suite, the command line, and
direct Python. All three talk to the same runtime and the same
provenance packet.

---

## 1. The test suite (what we test)

From the cas-rr directory:

    python -m pytest              # everything: 37 tests
    python -m pytest tests/test_battery_reasoning.py    # the six-task battery
    python -m pytest tests/test_runtime_invariants.py   # the five laws
    python -m pytest tests/test_interaction.py          # CLI + reporting
    python -m pytest -k transitive                      # one keyword
    python -m pytest tests/test_battery_reasoning.py::test_fault_localizes_first_bad_stage -v

What the suite verifies:

- every battery task halts in its expected typed state with the expected
  conclusion and a complete proof path (premises + rules);
- the five load-bearing laws hold as executable constraints (no bias-free
  CJT; evaluation gain locked to unity; association is not deduction;
  action cannot authorize its principle; child probes retained);
- determinism: two runs of any task produce identical traces, status,
  and output;
- boot order (P -> C -> E -> O, O last), the candidate invariant, the 28
  channels, the adapter, the four CJT regions, and both rumination stop
  gates.

What the suite does NOT claim: generality beyond these tasks, safety,
consciousness, or any empirical CAS-Ohm prediction. The tests prove the
architecture executes its own rules - nothing more.

---

## 2. The command line

    python run.py list                 list every battery task
    python run.py run transitive       one episode: report
    python run.py run recursive_plan --trace      report + full trace
    python run.py run fault --full     report + raw provenance JSON
    python run.py run transitive --json packet.json
    python run.py demo                 run the whole battery, one table
    python run.py check                determinism check on every task
    python run.py repl                 interactive Python session

Example - transitive inference:

    python run.py run transitive

    problem:     transitive_01
    status:      CONCLUDED  (ticks=1)
    output:      precedes(a,c)
    tournament: winner cand_01; eliminated: {'cand_02': ...}
    gates:
      PASS COMPARISON_SURVIVED       tournament winner cand_01
      PASS PREREQUISITES_SUFFICIENT  D/W/P all sufficient
      PASS NO_FATAL_CONTRADICTION    winner contradiction status NONE
      PASS PRINCIPLED_CONSTRAINTS    clean
      PASS POWER_GOOD                O enabled (P, C, E power-good)
    proof:      precedes(a,c) <- rules ['r_trans']
                via premises ['precedes(a,b)', 'precedes(b,c)']

Example - recursive planning, with the recursion story:

    python run.py run recursive_plan --trace

    status:  CONCLUDED
    rpm story:
      descend  KNOWLEDGE   from g_launch (blocked on W, action=market_research)
      resolve              g_launch.knowledge via market_research
      descend  CAPABILITY  from g_launch (blocked on P, action=restructure_resources)
      resolve              g_launch.capability via restructure_resources
    rpm scans:
      g_launch    D=Y W=n P=Y unmet=W cached=True
      g_launch    D=Y W=Y P=n unmet=P cached=False
      g_launch    D=Y W=Y P=Y unmet=None cached=False

Note cached=False: the parent is re-measured from scratch after every
subgoal resolution (RPM is section-retraction; nothing is assumed to
reverse). The trace below the report shows every phase and tick.

---

## 3. Direct Python

    from cas_rr.runtime import CASRuntime, default_constitution
    from tasks import battery

    packet = CASRuntime(default_constitution(),
                        battery.task_fault()).run()
    print(packet["terminal_status"])        # CONCLUDED
    print(packet["output"]["conclusion"])   # first_bad(S3)

The packet is the complete provenance:

    packet["trace"]            append-only event list (tick, phase, kind)
    packet["memory"]           queries, selected items with source, lacunae
    packet["candidates"]       ^8 frames with amplification and associations
    packet["decompositions"]   ^6 records with premises matched/missing
    packet["inferences"]       ^9 records: success, rules_used, premises_used
    packet["foundation_effects"]  28-channel consequence profiles
    packet["comparisons"]      CDAB tournament, divergence reports
    packet["rpm"]              scan history + subgoal events
    packet["commitment"]       decision, hysteresis state, typed gates
    packet["learning"]         dispositions (episodic only in v0.1)

---

## 4. Authoring a new problem

A problem is five things: facts, rules, a hypothesis space, a goal, and
optional actions. Nothing else. See examples/custom_kinship.py - a
grandparent syllogism the battery has never seen:

    python examples/custom_kinship.py

    CONCLUDED -> grandparent(ada,cy)
    proof: grandparent(ada,cy) rules: ['r_grandparent']
           premises: ['parent(ada,bo)', 'parent(bo,cy)']

Template:

    facts        ground atoms: A("pred", "arg1", "arg2")
    rules        Rule(id, [premises], conclusion, source)
                 variables start with ?; not_ pred negates pred
    alternatives the hypothesis space the ^8 bank will amplify
    goal         GoalFrame(goal_id, foundation_ref, desired_outcome, kind)
                 kind: question | plan | subgoal
                 desired_outcome may be a pattern, e.g. A("viable", "?P")
    authored_effects  optional 28-channel deltas per candidate
    available_actions  maps W/P blocks to action names for RPM recursion
    world_actions      action effects: added facts + acquisition updates

To add a permanent task, add a builder to tasks/battery.py and register
it in BATTERY; it is then available to pytest, run.py, and demo.

---

## 5. Poking the machine (safe experiments)

All of these are legitimate interaction - each shows a law or gate
firing, and each is covered by a test.

Break the truth firewall (Law 2):

    from dataclasses import replace
    from cas_rr.runtime import default_constitution
    from cas_rr.cjt import ConstitutionError

    try:
        replace(default_constitution(), eval_gain=2.0).validate()
    except ConstitutionError as e:
        print(e)   # boot refuses: gain is not truth

Add a memory and watch the answer change (task 6):

    rt = CASRuntime(default_constitution(), battery.task_memory())
    from cas_rr.terms import Atom

    rt = CASRuntime(default_constitution(), battery.task_memory())
    print(rt.run()["terminal_status"])      # NEEDS_INFORMATION

    rt2 = CASRuntime(default_constitution(), battery.task_memory())
    rt2.cmb.store_atom(Atom("has", "b", "y"), "^5", "C", "semantic",
                       "verified_memory_episode_1")
    packet2 = rt2.run()
    print(packet2["terminal_status"])       # CONCLUDED
    print(packet2["output"]["conclusion"])  # is(b,y)

Same constitution, same problem; only memory differs, and the stored
item appears in the provenance with its source.

Starve the machine (rumination stop gates):

    from dataclasses import replace
    poor = replace(default_constitution(), attention_budget=1.5)
    packet = CASRuntime(poor, battery.task_recursive_plan()).run()
    print(packet["terminal_status"])        # RESOURCE_EXHAUSTED

    fast = replace(default_constitution(), max_ticks=0)
    print(CASRuntime(fast, battery.task_transitive()).run()["terminal_status"])
                                            # LOOP_LIMIT_REACHED

Watch a block halt typed (task 4):

    packet = CASRuntime(default_constitution(),
                        battery.task_missing_info()).run()
    print(packet["terminal_status"])        # NEEDS_INFORMATION
    for mem in packet["memory"]:
        for lacuna in mem["lacunae"]:
            print(lacuna["query"], lacuna["kind"])
    # is(b,y) KNOWLEDGE_MISSING
    # has(b,y) EXPERIENCE_MISSING

The machine reports what it does not know instead of inventing it.

---

## 6. Verifying determinism and the laws yourself

    python run.py check     # every task twice: identical traces

    python -m pytest tests/test_runtime_invariants.py -v

The five laws live in code, not prose: cjt.py validates gain regimes at
construction, reasoning.py separates ^8 from ^6+^9, domains.py blocks
direct O -> P edges, learning.py disables durable layers, and trace.py
retains every probe.

---

## 7. Where each organ lives

    cas_rr/ontology.py     Noetics, Domains, Drives, Registers, Foundations,
                           28 channels, adapter, acquisitions, gain regimes
    cas_rr/terms.py        atoms, rules, pattern matching, backward chaining
    cas_rr/cjt.py          the junction: four regions, typed biases, probes
    cas_rr/memory.py       CMB: 40 cells, layers, structural query, lacunae
    cas_rr/foundations.py  goal engines, D/W/P, attention, 28-lane effects
    cas_rr/candidates.py   ^8 generator
    cas_rr/reasoning.py    ^6 decomposition + ^9 inference
    cas_rr/compare.py      CDAB + tournament
    cas_rr/rpm.py          recursion stack, typed subgoals
    cas_rr/commit.py       Schmitt gates + seven halt states
    cas_rr/domains.py      P -> C -> E -> O sequencing + diodes
    cas_rr/learning.py     low-gain feedback, disabled durable layers
    cas_rr/trace.py        append-only trace + provenance packet
    cas_rr/runtime.py      the 12-phase machine loop
