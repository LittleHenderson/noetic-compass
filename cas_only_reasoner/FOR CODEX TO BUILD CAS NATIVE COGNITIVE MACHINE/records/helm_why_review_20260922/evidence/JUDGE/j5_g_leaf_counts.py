# JUDGE: leaf-field frequencies on VISIBLE G train/dev inputs (observation strings only). Pure Python regex.
# Leaf grammar as seen in the data: ^<noetic>^<domain>[_{F<k>}][|<register>]
import json, re, collections, os
D = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/data/q3_v0_7"
LEAF = re.compile(r"\^(\d)\^([PCEO])(?:_\{F(\d)\})?(?:\|([TAfE]))?")
used = json.load(open(r"C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review/R5/used_rows.json", encoding="utf-8"))
used_ids = set(used if isinstance(used, list) else used.get("record_ids", used.get("rows", [])))
for split in ("train", "dev"):
    rows = [json.loads(l) for l in open(os.path.join(D, "visible_G_%s.jsonl" % split), encoding="utf-8") if l.strip()]
    for label, subset in (("all", rows), ("seen128", [r for r in rows if r["record_id"] in used_ids])):
        if not subset:
            continue
        drive = collections.Counter(); reg = collections.Counter(); noe = collections.Counter(); dom = collections.Counter(); n = 0
        for r in subset:
            for m in LEAF.finditer(r["observation"]):
                n += 1
                noe[m.group(1)] += 1; dom[m.group(2)] += 1
                drive["F" + m.group(3) if m.group(3) else "F_NONE"] += 1
                reg[m.group(4) or "REG_ABSENT"] += 1
        print(split, label, "rows", len(subset), "leaves", n,
              "| F_NONE", drive["F_NONE"], "(%.4f)" % (drive["F_NONE"] / n),
              "| REG_ABSENT", reg["REG_ABSENT"], "(%.4f)" % (reg["REG_ABSENT"] / n),
              "| top noetic", noe.most_common(3), "| domains", dom.most_common())
print("used_ids loaded", len(used_ids))
