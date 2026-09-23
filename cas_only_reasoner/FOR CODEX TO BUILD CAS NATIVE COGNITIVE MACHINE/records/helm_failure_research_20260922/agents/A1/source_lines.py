import pathlib,json,subprocess,zipfile,ast,hashlib
B=pathlib.Path(__file__).resolve().parent
m=json.loads((B.parents[1]/"SOURCE_AND_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8-sig"))
lines=[]
for i in (0,3):
 s=m["subjects"][i]; gs=m["grading_sources"][0 if i==0 else 1]
 b=subprocess.run(["git","show",gs["commit"]+":"+gs["repository_path"]],check=True,capture_output=True).stdout
 lines += [f"GRADER {gs['commit']} {gs['repository_path']} SHA256-LF {gs['sha256_lf']}"]
 ll=b.decode().splitlines()
 for a,z in ((112,114),(283,338),(355,380),(1142,1144)):
  lines.extend(f"{j}: {ll[j-1]}" for j in range(a,z+1))
 p=next(a["path"] for a in s["artifacts"] if pathlib.Path(a["path"]).name=="source.zip")
 with zipfile.ZipFile(p) as f:
  member="research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py"
  b=f.read(member); ll=b.decode().splitlines(); tree=ast.parse(b)
  lines += [f"CONTRACT {s['version']} {member} SHA256 {hashlib.sha256(b).hexdigest()}"]
  for n in tree.body:
   if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ("REMOVALS","VERIFIED_POPULATION_DIGEST","VERIFIED_POPULATION_BY_KIND") for t in n.targets):
    lines.extend(f"{j}: {ll[j-1]}" for j in range(n.lineno,n.end_lineno+1))
(B/"PINNED_SOURCE_LINES.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(x for x in lines if "REMOVALS =" in x))

