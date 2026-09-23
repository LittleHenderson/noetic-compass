"""RT6 M1: for every VISIBLE train/dev Q3 v0.7 record, compute the answer with the project's own
registered program, reading ONLY the model-visible packet. No sealed file, no eval file, no torch."""
import collections, hashlib, json, pathlib, sys
ROOT = pathlib.Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
D = LAB / "data/q3_v0_7"
sys.path.insert(0, str(LAB))
assert "torch" not in sys.modules
import reference_ops as ref
import q3_behaviour_records as q3
from historical_compiler import load_historical_compiler, source_receipt
compile_expression = load_historical_compiler().compile_expression
print("compiler receipt:", source_receipt()["sha256"])
manifest = json.loads((D / "manifest.json").read_text(encoding="utf-8"))

def rows(fam, split):
    name = "visible_%s_%s.jsonl" % (fam, split)
    assert name.startswith("visible_") and split in ("train", "dev")
    p = D / name
    raw = p.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["files"][name]["sha256"], name
    return [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]

REFUSE = "INVALID_INPUT"
def answer_A(obs):   # registered 'exact_symbolic_reference' rule, q3_behaviour_records.py:653
    if not q3._valid_fields(obs):
        return REFUSE
    return ref.is_admissible(obs["operator"], tuple(obs["source"]), tuple(obs["target"]))

def parse_compose(s):  # my own recursive parser; applies ref.compose in the WRITTEN grouping
    s = s.strip()
    if s.startswith("compose(") and s.endswith(")"):
        inner, depth = s[len("compose("):-1], 0
        for i, ch in enumerate(inner):
            if ch == "(": depth += 1
            elif ch == ")": depth -= 1
            elif ch == "," and depth == 0:
                return ref.compose(parse_compose(inner[:i]), parse_compose(inner[i+1:]))
        raise ValueError(s)
    return int(s)
def modsum(s):       # registered 'modular_sum_ignoring_grouping', q3_behaviour_records.py:691
    return sum(int(x) for x in s.replace("compose(", " ").replace(")", " ").replace(",", " ").split()) % 10
def answer_RG(obs):  # registered 'compiler_reference', q3_behaviour_records.py:698
    art = compile_expression(obs).to_dict()
    return q3.canonical(q3.to_lab_spelling(art["ast"])) if art["valid"] and art["ast"] is not None else None

def digest(xs):
    return hashlib.sha256(json.dumps(xs, sort_keys=True, default=str).encode()).hexdigest()[:16]

vis_fields = {"A": {"record_id", "family", "mode", "operation_id", "observation"},
              "C": {"record_id", "family", "mode", "operation_id", "observation"},
              "G": {"record_id", "family", "mode", "observation"},
              "R": {"record_id", "family", "mode", "observation"}}
for fam in ("A", "C", "G", "R"):
    for split in ("train", "dev"):
        rs = rows(fam, split)
        keysets = collections.Counter(tuple(sorted(r.keys())) for r in rs)
        extra = [k for k in keysets if set(k) != vis_fields[fam]]
        if fam == "A":
            ans = [answer_A(r["observation"]) for r in rs]
            ans2 = [answer_A(r["observation"]) for r in rs]
            dist = collections.Counter(str(a) for a in ans)
            ok = sum(1 for a in ans if a is not None)
            extra_info = "answers %s" % dict(sorted(dist.items()))
        elif fam == "C":
            ans = [parse_compose(r["observation"]) for r in rs]
            ans2 = [parse_compose(r["observation"]) for r in rs]
            ms = [modsum(r["observation"]) for r in rs]
            ok = sum(1 for a in ans if a is not None)
            extra_info = "grouped-compose == modular-sum on %d/%d" % (sum(a == m for a, m in zip(ans, ms)), len(rs))
        else:
            ans = [answer_RG(r["observation"]) for r in rs]
            ans2 = [answer_RG(r["observation"]) for r in rs]
            ok = sum(1 for a in ans if a is not None)
            extra_info = "compiler returned a valid AST"
        print("%s %-5s n=%d  visible keysets=%s  non-visible keys=%s  answer defined=%d/%d  deterministic(2 runs)=%s  digest=%s  %s"
              % (fam, split, len(rs), len(keysets), extra, ok, len(rs), ans == ans2, digest(ans), extra_info))

# Direct check against reference targets that a RUN RECORD already carries (dev split, family G).
insp = json.loads((ROOT / "records/q4_authorized_20260922/inspected_predictions.json").read_text(encoding="utf-8"))
hit = 0
for c in insp["cases"]:
    mine = answer_RG(c["input"])
    hit += int(mine == q3.canonical(c["checker_reference_ast"]))
print("G dev, first 16 (records/q4_authorized_20260922/inspected_predictions.json): compiler(visible input) == frozen dev reference AST on %d/%d" % (hit, len(insp["cases"])))
print("torch imported:", "torch" in sys.modules)
