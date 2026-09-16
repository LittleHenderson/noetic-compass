from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path(sys.argv[1]); root=Path(sys.argv[2]); oid=sys.argv[3]; size=int(sys.argv[4]); name=sys.argv[5]
cache=root/"github-lfs-cache"; destination=root/("github-"+name)
assert not destination.exists(), destination
assert not (cache/"objects"/oid[:2]/oid[2:4]/oid).exists(), "requested object already cached"
pointer=f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {size}\n".encode()
with destination.open("xb") as f:
    result=subprocess.run(["git","-C",str(repo),"-c","lfs.storage="+cache.as_posix(),"-c","lfs.url=https://github.com/LittleHenderson/noetic-compass.git/info/lfs","lfs","smudge","--",name],input=pointer,stdout=f,stderr=subprocess.PIPE)
if result.returncode:
    raise RuntimeError(result.stderr.decode(errors="replace"))
h=hashlib.sha256()
with destination.open("rb") as f:
    for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
assert destination.stat().st_size==size
assert h.hexdigest()==oid
receipt={"schema":"cas-publication-independent-lfs-download/v1","oid":oid,"size":size,"file":name,"sha256_verified":True,"independent_lfs_cache":str(cache),"requested_object_absent_before_download":True,"downloaded_file":str(destination),"command_exit":result.returncode}
(root/(name+".remote-verification.json")).write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt))
