from pathlib import Path
import json,subprocess,sys
repo=Path(sys.argv[1]); ref=sys.argv[2]; out=Path(sys.argv[3])
objects=subprocess.check_output(["git","-C",str(repo),"rev-list","--objects",ref]).splitlines()
names={}
for line in objects:
    parts=line.decode().split(" ",1);names[parts[0]]=parts[1] if len(parts)>1 else None
result=subprocess.check_output(["git","-C",str(repo),"cat-file","--batch-check=%(objectname) %(objecttype) %(objectsize)"],input=b"\n".join(x.encode() for x in names)+b"\n")
oversized=[];largest=[]
for line in result.decode().splitlines():
    oid,kind,size=line.split();size=int(size)
    if kind=="blob":
        row={"oid":oid,"bytes":size,"path":names[oid]}
        largest.append(row)
        if size>100*1024*1024:oversized.append(row)
receipt={"ref":ref,"head":subprocess.check_output(["git","-C",str(repo),"rev-parse",ref],text=True).strip(),"reachable_objects":len(names),"oversized_git_blobs":oversized,"largest_blobs":sorted(largest,key=lambda x:x["bytes"],reverse=True)[:5]}
out.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt,indent=2))
assert not oversized
