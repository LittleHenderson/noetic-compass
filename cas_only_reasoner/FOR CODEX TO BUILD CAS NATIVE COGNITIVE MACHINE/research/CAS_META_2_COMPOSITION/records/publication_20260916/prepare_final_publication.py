"""Prepare reversible LFS publication from the coordinator's exact final SHA.
No Git branch is pushed by this script.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
repo=Path(sys.argv[1]); output=Path(sys.argv[2]); source=sys.argv[3]
base="aaf969843c55bf681e3f2062377967b580f98d49"
migration_base="f8bcffe6e0504a05ccc85be29e7ffc052b1a8918"
branch="refs/heads/codex/cas-meta-2-composition"
archive_path="cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_ablation_v4_002/cloud_artifacts.zip"
prefix="cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/publication_20260916/"
def run(*args,input=None,env=None):
    result=subprocess.run(["git","-C",str(repo),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout
def text(*args,**kwargs):return run(*args,**kwargs).decode().strip()
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()
assert len(source)==40 and all(c in "0123456789abcdef" for c in source)
assert source!=base
run("fetch","source",source+":refs/publication/original-final")
assert text("rev-parse","refs/publication/original-final")==source
run("merge-base","--is-ancestor",base,source)
delta=output/"source-final-incremental.bundle"
assert not delta.exists()
run("bundle","create",str(delta),"refs/publication/original-final","^"+base)
run("bundle","verify",str(delta))
run("update-ref",branch,source,text("rev-parse",branch))
mapping=output/"commit-map.csv"
assert not mapping.exists()
run("lfs","migrate","import","--include-ref="+branch,"--exclude-ref="+migration_base,
    "--include="+archive_path,"--object-map="+str(mapping),"--yes")
migrated=text("rev-parse",branch)
subprocess.run([sys.executable,str(output/"verify_migration.py"),str(repo),str(mapping),str(output/"migration-verification.json")],check=True)
delta_sha=sha(delta);delta_size=delta.stat().st_size
lfs=repo/".git"/"lfs"/"objects"/delta_sha[:2]/delta_sha[2:4]/delta_sha
lfs.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(delta,lfs)
run("lfs","push","--object-id","origin",delta_sha)
subprocess.run([sys.executable,str(output/"verify_lfs_download.py"),str(repo),str(output),delta_sha,str(delta_size),delta.name],check=True)
restored=output/"restored-original.git"
assert restored.is_dir()
subprocess.run(["git","-C",str(restored),"fetch",str(output/("github-"+delta.name)),"refs/publication/original-final:refs/heads/original-final"],capture_output=True,check=True)
assert subprocess.check_output(["git","-C",str(restored),"rev-parse","refs/heads/original-final"],text=True).strip()==source
diagnostic_source="fb4bb4a297d6c5a9268bd96d98eb983d934ef4f5"
for original_commit in (base, diagnostic_source, source):
    assert subprocess.check_output(["git","-C",str(restored),"cat-file","-t",original_commit],text=True).strip()=="commit"
def pointer(oid,size):return f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {size}\n".encode()
receipt={"schema":"cas-publication-source-preservation/v1","original_source_sha":source,
         "migrated_source_sha":migrated,"mapping_sha256":sha(mapping),
         "full_original_bundle":{"filename":"source-aaf96984.bundle","sha256":"b23e58c7dfd21f897c92c499778136ff54214a4e13e13618dec901e78d031b2b","bytes":729531855,"tip":base},
         "incremental_original_bundle":{"filename":delta.name,"sha256":delta_sha,"bytes":delta_size,"prerequisite":base,"tip":source},
         "full_and_incremental_bundles_independently_downloaded_from_github":True,
         "original_final_sha_restored_in_separate_bare_repository":True,
         "restored_original_commits":[base,diagnostic_source,source],
         "original_worktree_rewritten":False,"original_worktree_upstream_changed":False}
receipt["continuation"]={
    "original_source_worktree":str(Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1")),
    "retained_isolated_publication_clone":str(repo),
    "source_history_remains_unmigrated":True,
    "ordinary_source_push_fast_forwards_remote":False,
    "supported_next_work":"Create a fresh clone of the migrated remote branch in a new directory inside the CNCM homebase; make future edits and commits there. Do not reset or relocate meta1.",
    "fresh_clone_command":"git clone --single-branch --branch codex/cas-meta-2-composition https://github.com/LittleHenderson/noetic-compass.git <NEW_DIRECTORY_INSIDE_CNCM_HOMEBASE>",
    "refresh_original_source_warning":"The one-shot prepare_final_publication.py is an audit record, not an idempotent refresh command. Later original-source changes require a new isolated migration, a new original-source backup and full mapping audit, and integration on top of the current published tip. Never force-push the unmigrated source branch."}
(output/"source-preservation.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
readme=f"""# Exact source preservation and LFS publication

The published source is **{migrated}**, mapped from original source **{source}**.
The migration only replaces the 136,120,962-byte historical cloud archive with
its LFS pointer and adds the tracking attribute. The old/new commit map and
migration audit cover every rewritten commit, including author, committer,
message, parent relationships, and unchanged source-file bytes.

The separate publication commit adds this restoration material. It is not a
new experiment result or a deployment. The original local source worktree and
its branch were not reset, rebased, or linked to the rewritten remote branch.

## Restore exact original SHA identities

Install Git LFS and obtain both bundle files from this directory. In a normal
clone, run git lfs pull if they still contain three-line pointer text.
Verify their SHA-256 hashes against source-preservation.json.

From this directory, using a new destination outside existing worktrees:

~~~text
git clone --bare source-aaf96984.bundle restored-original.git
git -C restored-original.git fetch <ABSOLUTE_PATH_TO_source-final-incremental.bundle> refs/publication/original-final:refs/heads/original-final
git -C restored-original.git rev-parse refs/heads/original-final
~~~

Replace the placeholder with the absolute incremental bundle path, quoted when
it contains spaces. The result must be {source}.
The base bundle contains complete original history through {base}; the
incremental bundle contains every subsequent original commit through the final
source SHA. Together they preserve the original raw archive and all source
identities named by historical research receipts.

The successful contrast diagnostic source commit
{diagnostic_source} is also preserved and was explicitly verified after restore.

Both bundles were uploaded to the existing GitHub LFS endpoint, downloaded
into a separate local cache, hash-checked, and used to restore the final
original source SHA in a separate bare repository. No paid plan was purchased.

The cloud archive SHA-256 is
c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708.
Its original Git blob SHA-1 is a61aca911fdd5a7ef1dc0e3db8d46d5e864b0a89.

Continue publishing from the rewritten branch, or repeat the isolated mapped
publication process for later original-source changes. Pushing the original
branch directly reintroduces the oversized blob. Do not force-push an
unmapped original branch over this publication.

## Continue future work

The original meta1 source branch deliberately remains on unmigrated history.
An ordinary push from meta1 will NOT fast-forward the published branch.
The retained publication repository is {repo}.
It is an isolated bare publication clone; its original objects currently use
the local source repository as an object alternate. Keep that dependency intact.

The supported ordinary continuation is a fresh clone of the migrated branch,
inside a NEW directory in the CNCM homebase:

~~~text
git clone --single-branch --branch codex/cas-meta-2-composition https://github.com/LittleHenderson/noetic-compass.git <NEW_DIRECTORY_INSIDE_CNCM_HOMEBASE>
~~~

Make future edits and commits in that clone, then use normal git push.
Do not reset, rebase, relocate, or set a misleading upstream on the original
meta1 worktree. Existing user changes remain there.

The one-shot prepare_final_publication.py script is an audit record, not an
idempotent refresh command. Publishing later work made on original history
requires a new isolated migration and original-source backup, a fresh full
mapping audit, and integration above the current published tip.
"""
assets={
    ".gitattributes":b"*.bundle filter=lfs diff=lfs merge=lfs -text\n",
    "source-aaf96984.bundle":pointer("b23e58c7dfd21f897c92c499778136ff54214a4e13e13618dec901e78d031b2b",729531855),
    delta.name:pointer(delta_sha,delta_size),"README.md":readme.encode(),
    "commit-map.csv":mapping.read_bytes(),
    "migration-verification.json":(output/"migration-verification.json").read_bytes(),
    "source-preservation.json":(output/"source-preservation.json").read_bytes(),
    "archive-remote-verification.json":(output/"cloud_artifacts.zip.remote-verification.json").read_bytes(),
    "base-bundle-remote-verification.json":(output/"source-aaf96984.bundle.remote-verification.json").read_bytes(),
    "incremental-bundle-remote-verification.json":(output/(delta.name+".remote-verification.json")).read_bytes(),
    "verify_migration.py":(output/"verify_migration.py").read_bytes(),
    "verify_lfs_download.py":(output/"verify_lfs_download.py").read_bytes(),
    "prepare_final_publication.py":Path(__file__).read_bytes(),
    "scan_large_git_objects.py":(output/"scan_large_git_objects.py").read_bytes(),
}
index=output/"publication.index";assert not index.exists()
env={**os.environ,"GIT_INDEX_FILE":str(index)}
run("read-tree",migrated,env=env)
for name,data in assets.items():
    oid=text("hash-object","-w","--stdin",input=data)
    run("update-index","--add","--cacheinfo","100644,"+oid+","+prefix+name,env=env)
tree=text("write-tree",env=env)
commit=text("commit-tree",tree,"-p",migrated,input=b"Preserve exact original source history alongside LFS publication\n")
run("update-ref",branch,commit,migrated)
state={**receipt,"publication_sha":commit,"branch":branch,"remote_git_push":"NOT_YET_PUSHED"}
(output/"publication-state.json").write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
print(json.dumps(state,indent=2))
