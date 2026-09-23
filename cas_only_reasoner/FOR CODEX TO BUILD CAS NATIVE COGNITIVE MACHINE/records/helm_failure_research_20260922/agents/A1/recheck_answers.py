"""A1 bounded stdlib-only saved-answer recheck. No neural modules or checkpoint loads."""
import ast, collections, fractions, hashlib, json, math, pathlib, subprocess, sys, time, types, zipfile
BASE=pathlib.Path(__file__).resolve().parent
MAN=BASE.parents[1]/"SOURCE_AND_EVIDENCE_MANIFEST.json"
m=json.loads(MAN.read_text(encoding="utf-8-sig"))
idx=int(sys.argv[1]); s=m["subjects"][idx]; start=time.monotonic()
fingerprints=[]
def raw(path, expected=None):
    p=pathlib.Path(path); b=p.read_bytes(); h=hashlib.sha256(b).hexdigest()
    if expected: assert h==expected,(str(p),h,expected)
    fingerprints.append({"path":str(p),"bytes":len(b),"sha256":h})
    return b
def load(path,expected=None): return json.loads(raw(path,expected))
def art(name):
    a=next(a for a in s["artifacts"] if pathlib.Path(a["path"]).name==name)
    return load(a["path"],a["sha256_raw"])
root=pathlib.Path(m["immutable_source_workspace"])/m["cncm_relative_path"]
gpath=root/"records/typed_pointer_001"/("admission_helm1_certified" if idx<3 else "admission_001")/"gate_reading.json"
# Additional historical record, bound here to its committed integration object.
gr=raw(gpath)
gitpath=str(gpath.relative_to(pathlib.Path(m["immutable_source_workspace"]))).replace("\\","/")
gb=subprocess.run(["git","show",m["integration_commit"]+":"+gitpath],capture_output=True,check=True).stdout
assert gr.replace(b"\r\n",b"\n")==gb.replace(b"\r\n",b"\n")
gate=json.loads(gr)
course_a=m["additional_required_sources"][0]
course=load(course_a["path"],course_a["sha256_raw"])
z_a=next(a for a in s["artifacts"] if pathlib.Path(a["path"]).name=="source.zip")
raw(z_a["path"],z_a["sha256_raw"])
z=zipfile.ZipFile(z_a["path"])
prefix="research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
pkg=types.ModuleType("a1checker"); pkg.__path__=[]; sys.modules[pkg.__name__]=pkg
sources=[]
for name in ("source","answers","focal","checker"):
    member=prefix+name+".py"; code=z.read(member)
    module=types.ModuleType("a1checker."+name); module.__file__=str(BASE/"tmp"/name/(name+".py")); module.__package__="a1checker"
    sys.modules[module.__name__]=module; setattr(pkg,name,module)
    tree=ast.parse(code)
    assert all(not isinstance(n,ast.Import) or all(x.name.split(".")[0] in sys.stdlib_module_names for x in n.names) for n in ast.walk(tree))
    assert all(not isinstance(n,ast.ImportFrom) or n.level or n.module.split(".")[0] in sys.stdlib_module_names for n in ast.walk(tree))
    exec(compile(tree,member,"exec"),module.__dict__)
    sources.append({"member":member,"sha256":hashlib.sha256(code).hexdigest(),"definitions":[{"name":n.name,"line":n.lineno,"end_line":n.end_lineno} for n in tree.body if isinstance(n,ast.FunctionDef)]})
# Frozen gate source from own pinned commit; compile only four pure functions.
gs=m["grading_sources"][0 if idx<3 else 1]
gbytes=subprocess.run(["git","show",gs["commit"]+":"+gs["repository_path"]],capture_output=True,check=True).stdout
assert hashlib.sha256(gbytes.replace(b"\r\n",b"\n")).hexdigest()==gs["sha256_lf"]
tree=ast.parse(gbytes); fnames={"binomial_upper_tail","paired","seed_test","label_decision"}
ns={"Fraction":fractions.Fraction,"comb":math.comb,"ALPHA":fractions.Fraction(1,100),"MIN_IMPROVED_KINDS":2,"MIN_IMPROVED_WORLDS":2}
for n in tree.body:
    if isinstance(n,ast.FunctionDef) and n.name in fnames: exec(compile(ast.Module(body=[n],type_ignores=[]),gs["repository_path"],"exec"),ns)
pc=z.read(prefix+"pointer_contract.py"); pct=ast.parse(pc)
constants={}
for n in pct.body:
    if isinstance(n,ast.Assign):
        for t in n.targets:
            if isinstance(t,ast.Name) and t.id in ("REMOVALS","VERIFIED_POPULATION_DIGEST","VERIFIED_POPULATION","RELATIONAL"):
                constants[t.id]=ast.literal_eval(n.value)
pop=gate["label_key_population"]
assert hashlib.sha256(json.dumps(pop,sort_keys=True,separators=(",",":")).encode()).hexdigest()==constants["VERIFIED_POPULATION_DIGEST"]
removed={q for kinds in constants["REMOVALS"].values() for qs in kinds.values() for q in qs}
assert sorted(set(gate["population"]["eligible_questions"])-removed)==pop
mat=art("protocol_material.json")
held=set(mat["held_back_record_ids"])
registry={r["record_id"]:r for r in course["registry"]}
questions=collections.defaultdict(list)
for rid in held: questions[registry[rid]["query"]["query_id"]].append(rid)
pred=[{p["record_id"]:p for p in art(n)["predictions"]} for n in ("course_p00_predictions.json","course_p10_predictions.json")]
saved=[{r["record_id"]:r for r in art(n)["rows"]} for n in ("course_p00_scoring.json","course_p10_scoring.json")]
targets={}; rows=[]; correct=[{},{}]; mismatches=[]
for q, rids in sorted(questions.items()):
    if time.monotonic()-start>110: raise TimeoutError("110 second internal bound")
    row=registry[rids[0]]; bank=course["bank"]
    public={"focus_world_id":row["source_world_id"],"worlds":bank["worlds"],"bank":bank["bank"]}
    target=pkg.checker.derive_target(public,row["query"]); targets[q]=target
    rr=[]
    for rid in sorted(rids):
        vals=[]
        for phase in range(2):
            answer=pred[phase][rid]["answer"]
            validated=pkg.answers.validate_answer(public,row["query"],answer)
            ok=validated in target["admissible_answers"]
            correct[phase][rid]=ok
            if ok!=saved[phase][rid]["correct"]: mismatches.append([phase,rid])
            vals.append({"answer":answer,"correct":ok,"saved_correct":saved[phase][rid]["correct"],"prediction_id":pred[phase][rid]["prediction_id"]})
        rr.append({"record_id":rid,"initial":vals[0],"final":vals[1]})
    rows.append({"query_id":q,"kind":row["query"]["kind"],"world":row["source_world_id"],"in_label_population":q in pop,
                 "initial":all(correct[0][r] for r in rids),"final":all(correct[1][r] for r in rids),
                 "admissible_answers":target["admissible_answers"],"records":rr})
qbefore={r["query_id"]:r["initial"] for r in rows}; qafter={r["query_id"]:r["final"] for r in rows}
kinds={r["query_id"]:r["kind"] for r in rows}; worlds={r["query_id"]:r["world"] for r in rows}
test=ns["seed_test"](qbefore,qafter,pop,kinds,worlds)
expected=gate["seeds"][str(s["seed"])]["G_LEARN_population"]
assert all(test[k]==expected[k] for k in ("wrong_to_right","right_to_wrong","p_one_sided","passed"))
families={}
for scope,qs in (("held_all",list(questions)),("label",pop),("eligible",sorted(set(questions)-set(gate["population"]["shortcut_question_ids"])))):
    families[scope]={}
    for kind in sorted(set(kinds[q] for q in qs)):
        kr=[q for q in qs if kinds[q]==kind]
        families[scope][kind]={"total":len(kr),"initial":sum(qbefore[q] for q in kr),"final":sum(qafter[q] for q in kr)}
result={"version":s["version"],"seed":s["seed"],"historical_label":gate["label"],"historical_void_paths":gate["void_paths_taken"],
        "primary_test":test,"family_totals":families,"rows":rows,"mismatches":mismatches,"sources":sources,
        "fingerprints":fingerprints,"subject_source":s["source_commit"],"checker_cases":sum(map(len,questions.values()))*2,
        "unique_questions":len(questions),"gate_source":gs,"contract_sha256":hashlib.sha256(pc).hexdigest(),
        "elapsed_seconds":time.monotonic()-start,"scope_note":"Independent answer validation + admissible-set membership; not full integrity grader re-execution. Population recovered from committed saved reader and crosschecked against source removal constants and frozen digest."}
out=BASE/f"seed_{idx}.json"; out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({k:result[k] for k in ("version","seed","primary_test","family_totals","mismatches","checker_cases","unique_questions","elapsed_seconds")}))

