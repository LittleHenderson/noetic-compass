# Exact source preservation and LFS publication

The published source is **40dce98c931a246c45c427969a2ef38a95973ef5**, mapped from original source **06d95cb017266102001e0298d22d1a78ee93bc9d**.
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
it contains spaces. The result must be 06d95cb017266102001e0298d22d1a78ee93bc9d.
The base bundle contains complete original history through aaf969843c55bf681e3f2062377967b580f98d49; the
incremental bundle contains every subsequent original commit through the final
source SHA. Together they preserve the original raw archive and all source
identities named by historical research receipts.

The successful contrast diagnostic source commit
fb4bb4a297d6c5a9268bd96d98eb983d934ef4f5 is also preserved and was explicitly verified after restore.

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
The retained publication repository is C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_publication\20260916\repo.
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
