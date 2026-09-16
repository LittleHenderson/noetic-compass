from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path(sys.argv[1]); mapping_file=Path(sys.argv[2]); out=Path(sys.argv[3])
pairs=[line.strip().split(",") for line in mapping_file.read_text().splitlines() if line.strip()]
mapping=dict(pairs); cache={}
proc=subprocess.Popen(["git","-C",str(repo),"cat-file","--batch"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
def obj(oid):
    if oid not in cache:
        proc.stdin.write((oid+"\n").encode());proc.stdin.flush()
        h=proc.stdout.readline().decode().strip().split()
        assert len(h)==3 and h[0]==oid,h
        data=proc.stdout.read(int(h[2]));assert proc.stdout.read(1)==b"\n"
        cache[oid]=(h[1],data)
    return cache[oid]
def tree(oid):
    typ,data=obj(oid);assert typ=="tree"
    result={};i=0
    while i<len(data):
        a=data.index(b" ",i);b=data.index(b"\0",a)
        mode=data[i:a].decode();name=data[a+1:b].decode()
        result[name]=(mode,data[b+1:b+21].hex());i=b+21
    return result
allowed={".gitattributes","cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_ablation_v4_002/cloud_artifacts.zip"}
memo={}
def changes(old,new):
    if old==new:return ()
    key=(old,new)
    if key in memo:return memo[key]
    left,right=tree(old),tree(new);result=[]
    for name in sorted(left.keys()|right.keys()):
        a,b=left.get(name),right.get(name)
        if a==b:continue
        if a and b and a[0]==b[0]=="40000":
            result += [name+"/"+x for x in changes(a[1],b[1])]
        else:result.append(name)
    memo[key]=tuple(result);return memo[key]
for old,new in pairs:
    oldtyp,oldraw=obj(old);newtyp,newraw=obj(new)
    assert oldtyp==newtyp=="commit"
    oldlines=oldraw.split(b"\n");newlines=newraw.split(b"\n")
    oldtree=oldlines[0].split()[1].decode();newtree=newlines[0].split()[1].decode()
    oldparents=[];newparents=[]
    for raw,parents in [(oldlines,oldparents),(newlines,newparents)]:
        for line in raw[1:]:
            if line.startswith(b"parent "):parents.append(line.split()[1].decode())
            else:break
    assert newparents==[mapping.get(parent,parent) for parent in oldparents],old
    assert oldlines[1+len(oldparents):]==newlines[1+len(newparents):],("metadata_changed",old)
    changed=set(changes(oldtree,newtree))
    assert changed <= allowed,(old,changed-allowed)
proc.stdin.close();proc.wait()
receipt={"schema":"cas-publication-migration-audit/v1","mapped_commits":len(pairs),"mapping_sha256":hashlib.sha256(mapping_file.read_bytes()).hexdigest(),"all_commit_metadata_preserved_except_tree_and_mapped_parents":True,"all_source_tree_changes_limited_to":sorted(allowed),"original_head":pairs[-1][0],"migrated_head":pairs[-1][1]}
out.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt))
