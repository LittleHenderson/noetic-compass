import zipfile, hashlib, re, sys
REC = ("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE "
       "MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001")
for r in ["receipt_helm1_certified_20260917","receipt_helm1_certified_20260918","receipt_helm1_certified_20260919",
          "receipt_20260917","receipt_20260918","receipt_20260919"]:
    z = zipfile.ZipFile(REC + "/" + r + "/source.zip")
    names = [n for n in z.namelist() if n.endswith("pointer_learner.py")]
    for n in names:
        src = z.read(n).decode("utf-8")
        print("==", r, n, "sha256", hashlib.sha256(z.read(n)).hexdigest())
        for i, line in enumerate(src.splitlines(), 1):
            if re.search(r"PER_ROUND_UPDATE_CAP|round_rate|torch\.optim\.|weight_decay|LEARNING_RATE\s*=|\bblock = ", line):
                print("  %d: %s" % (i, line.strip()[:150]))
