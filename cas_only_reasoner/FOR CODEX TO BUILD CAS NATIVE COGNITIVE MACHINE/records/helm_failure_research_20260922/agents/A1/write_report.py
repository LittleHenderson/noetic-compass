import json,pathlib
B=pathlib.Path(__file__).resolve().parent
R=[json.loads((B/f"seed_{i}.json").read_text()) for i in range(6)]
lines=["# A1 immutable first report","",
"Helm 2.0 failed the frozen label because seed 20260919 missed the paired improvement cutoff. That seed improved from 4/18 to 10/18, but seven gains and one loss give p=9/256=0.03515625, above 0.01. The other two Helm 2.0 seeds pass. Helm 1.0 passes all three seeds. These historical labels remain unchanged.","",
"## Scope and exposure","",
"A1 used codex/helm-failure-a1-20260922, starting at 59b1dd57e57648ab68c1cc26fbae95a957c20cd3. No peer reports or findings were read. The common directive line 59 claimed two of three Helm 2 runs failed because each lost a correct answer; line 60 mentioned past frozen-message-loop and single-head explanations. These were historical narrative exposure, not accepted causes. Frozen grader/contract comments discussed previous shortcut and expressibility findings; these are exposure to historical opinions, not established causes. No BRAIN_LINEAGE narrative was read. Current record-only boundaries supersede older broad execution instructions.","",
"## Exact original pass rule","",
"evaluate_gates.py has SHA256-LF d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d at both pinned source commits: Helm 1 af0970cfa6d54a85aeb16e5a99a84d791ace59c0 and Helm 2 20208c923d41c24614504d4ecc2b289ecb66eda8. It was read directly from those Git objects.","",
"- Lines 112–114 set alpha=1/100 and require at least two improved kinds and two improved worlds. Lines 283–321 count b wrong-to-right and c right-to-wrong question pairs; require b>c and P[Binomial(b+c,0.5)>=b] <= 0.01 plus the breadth requirements.",
"- Lines 296–298 require every presentation of a question correct. Presentations are not independent gate questions. Lines 355–380 choose the frozen relational population; lines 1142–1144 require all three seeds to pass.",
"- Lines 324–338 give precedence: failed integrity or missing seeds => VOID; otherwise all three primary tests pass => LEARNS_NEW_WORLDS; otherwise NO_TRANSFER_TO_NEW_WORLDS. Both committed historical readers record no void paths.",
"- Packaged pointer_contract.py lines 518–536 remove three parts flag-rule questions, two reach order-rule questions, one reach present-rule question, and five correspondence questions. Lines 539–553 freeze the counts and population digest.",
"- 50 held questions become 45 after five shortcut exclusions; 29 are relational; 11 further removals leave 18: edge_account 5, parts 2, reach 6, analogy 5, correspondence 0. Frozen ID-list digest: 4b1e3c1f0b8f8be339e281410dc830fac1834432e8d816d67dce58906e90036d. A1 checked this digest and source-bound removal subtraction. Shortcut discovery itself was not regenerated.",
"- MIN_PASSING_B=7 is the zero-loss minimum, not an unconditional seven-gain pass. Seven gains/no losses gives 1/128; seven gains/one loss gives 9/256.","",
"## Reconstructed results","",
"| Version | Seed | Initial /18 | Final /18 | Gains | Losses | Exact p | Pass |",
"|---|---:|---:|---:|---:|---:|---|---|"]
for r in R:
 p=r["primary_test"]; rr=[x for x in r["rows"] if x["in_label_population"]]
 lines += [f"| {r['version']} | {r['seed']} | {sum(x['initial'] for x in rr)} | {sum(x['final'] for x in rr)} | {p['wrong_to_right']} | {p['right_to_wrong']} | {p['p_one_sided']} | {p['passed']} |"]
lines += ["","All six seeds gain in edge_account, parts, and reach, across all five held worlds. Seed 20260919 fails the probability cutoff, not the gain direction or breadth requirements.",
"Correction to copied directive CODEX_HELM_FAILURE_RESEARCH_TEAM_20260922.md line 59: it says Helm 2 failed the rule in two of three runs because each lost a correct answer. Two seeds do each lose one answer, but only seed19 fails. Seed17 passes despite one loss: 11 gains/1 loss, p=13/4096=0.003173828125. The frozen rule does not require c=0. Historical per-seed G_LEARN_population fields and source lines 309–320 establish this correction.","",
"## Family results distinct from the label","",
"All 50 held questions, including those excluded from the label. Cells are initial→final/total. Raw endpoint answers were rechecked with the packaged checker.","",
"| Version/seed | Analogy | Context | Correspondence | Definition | Edges | Parts | Reach | Roles |",
"|---|---|---|---|---|---|---|---|---|"]
for r in R:
 f=r["family_totals"]["held_all"]
 lines += ["| "+r["version"]+" "+str(r["seed"])+" | "+" | ".join(f"{f[k]['initial']}→{f[k]['final']}/{f[k]['total']}" for k in ("analogy","context","correspondence","definition","edge_account","parts","reach","role_set"))+" |"]
lines += ["","Every final held analogy total is zero. Helm 2 correspondence improves from 0/5 to 5/5 in every seed, whereas Helm 1 stays at 0/5. Correspondence contributes zero questions to the label, so this real gain cannot repair its failing label. Analogy contributes five; its persistent failure occurs in both versions and cannot alone explain their label difference.","",
"## Exact failing-seed questions","",
"Seed17 also loses a reach answer but passes: typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005 changes from VIA through world-4090ec49174f1d031b16507663d875616c489382d0be1fdf7f4616aeb3dde9fc/n3 to DIRECT with via=null. Its full presentations are in seed_3.json.\n\nFor failing seed19, the only right-to-wrong query: typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f. Its world is world-28f61f2d7941a373f50285be7e57b1a9b8ec85bc0aff9e2d18c683e9f86b4547. All four saved presentations change from VIA through that world's n3 to VIA through n1. Only n3 is admissible. Exact record IDs and unabridged answers are in seed_5.json.",
"Final-wrong label questions:",""]
for x in R[5]["rows"]:
 if x["in_label_population"] and not x["final"]: lines += [f"- {x['query_id']} ({x['kind']}, {'right→wrong' if x['initial'] else 'wrong→wrong'})."]
lines += ["","The seven gains are five edge_account questions, parts query typed-query-c7ee82d21b69bf37a34cadf033ed59ddb829ceec26d3459ecca3b239c29f16ab, and reach query typed-query-f341afc7254139140ecbc5edaba9fd164bac26896c217e61e9c9c5b5ac8b5d82. QUESTION_TRANSITIONS.md lists all 300 question/run transitions. seed_0.json through seed_5.json preserve the complete raw answers, target sets, member hashes, original file hashes, and exact definition-line ranges.","",
"## Method and limits","",
"Each source.zip and public course was checked against the manifest. The probe reused only the exact historical source.py, answers.py, focal.py, checker.py modules, with stdlib-only import assertions. Prediction syntax was validated by answers.validate_answer; semantic truth was membership in the complete set returned by checker.derive_target, matching check_answer's decision. This handles multiple valid answers. It is checker reuse, not an independent implementation of semantics.",
"The primary arithmetic was also reused from the exact frozen grader: AST-selected binomial_upper_tail, paired, seed_test, and label_decision. It is an independent execution on recomputed outcomes, NOT an independently implemented paired-test algorithm. Results match the committed historical gate fields wrong_to_right, right_to_wrong, p_one_sided, and passed for all six seeds. Gate records were additionally compared against their integration Git objects.",
"No Torch, model initialization, neural checkpoint deserialization, inference, training, GPU, cloud, paid API, or installs ran. No full integrity-grader rerun occurred. The recorded no-VOID result is a historical fact, not a newly issued certificate.",
"Counts: one procedural probe; zero pytest/test_* functions; six completed run inputs; 50 unique held questions per run = 300 question/run cases; 127 presentations × two endpoints × six runs = 1,524 answer checks; 108 primary paired cases. The same 50 questions repeat across seeds/versions. Six successful executions, one partial failed execution, no successful reruns. All six completed in less than 13 seconds, sequentially; internal time guard 110 seconds. Zero saved-score disagreements.",
"The partial failure used initial_reload_predictions/final_reload_predictions, which do not contain the full population. It raised KeyError for typed-input-78a2cabeeee3db48a0ef1d63399d3c44c46cf13433dc7913c8d405d88f15cb7d. The completed probe uses the full course_p00/course_p10 answers, the endpoint phases used by the gate. Earlier text reads had truncated outputs; decisive checks parse files directly. See COMMANDS_AND_FAILURES.md.","",
"## Explanation and competing account","",
"Established: one seed's recorded gain/loss pattern fails the frozen statistical requirement. This explains the label; it does not explain the neural mechanism. The strongest measurement alternative was a mismatched checker or accidentally counting presentations/all-kind questions instead of the frozen 18. Source-bound target recomputation, zero disagreements in 1,524 checks, exact population digest, and exact paired fractions contradict that alternative within this scope.",
"Architecture limits and training instability remain competing mechanism explanations. Endpoint answers alone do not distinguish them. The smallest next record-only discriminating test is to inspect the saved intermediate heldback_p02/p04/p06/p08 answers for the three non-analogy failing queries in seed19 and compare those exact questions across seeds. Predicted outcome: earlier correctness followed by loss supports instability/forgetting; never-correct behavior across every stored checkpoint/seed is more consistent with a persistent limit, but does not prove impossibility. Register this test before execution. It is NOT RUN here.",
"Hypothetically preserving the one lost answer would give 7 gains/0 losses, p=1/128, and change the arithmetic. This is not a result, a proposed grader change, or evidence of fresh transfer. Do not tune historical failures and call them a fresh evaluation.","",
"Unknowns: full integrity gates not reexecuted; shortcut discovery not regenerated; outside-held predictions not rechecked; no fresh tasks, neural numeric-validity tests, weight inspections, alternative schedules, or Q4 experiments. No full-machine or production claim follows.","",
"FIRST_REPORT.md is immutable after submission. Corrections belong in a separate follow-up file."]
(B/"FIRST_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
tr=["# All held-question transitions","","Each query counts once; every presentation must be correct.",""]
for r in R:
 tr += [f"## {r['version']} seed {r['seed']}","","| Query ID | Kind | In label | Initial | Final |","|---|---|---|---|---|"]
 for x in r["rows"]: tr += [f"| {x['query_id']} | {x['kind']} | {x['in_label_population']} | {x['initial']} | {x['final']} |"]
(B/"QUESTION_TRANSITIONS.md").write_text("\n".join(tr)+"\n",encoding="utf-8")
print(sum(r["checker_cases"] for r in R))

