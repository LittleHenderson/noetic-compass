"""Independent bounded parse/check exercise; generated review evidence only."""
from pathlib import Path
import hashlib
import json
import random
import sys
import time
import traceback

ROOT = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\codex-helm-data")
LAB = ROOT / "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab"
sys.dont_write_bytecode = True
sys.path.insert(0, str(LAB))
from pcba_check import check_pcba_document
from pcba_reader import MAX_SOURCE_BYTES

BASE = """circuit bounded_example {
 input: prompt; output: response;
 node cause: ^8^C_{F2}|A; node bias: ^5^P_{F4}|f; node effect: ^9^C_{F6}|A;
 cjt stage1: CJT< cause | bias => effect > [beta=0.5];
 feedback effect -> cause [beta=0.2]; probe result: effect;
}"""

results = {"seed": 214521, "cases": 0, "crashes": [], "unexpected_passes": [], "inconsistent_reports": [], "targeted": []}
results["loaded_source_hashes"] = {name: hashlib.sha256((LAB / name).read_bytes()).hexdigest() for name in ["pcba_check.py", "pcba_reader.py", "pcba_component_adapter.py"]}


def check(label, source, reject=False, record=False):
    results["cases"] += 1
    try:
        report = check_pcba_document(source)
        json.dumps(report, allow_nan=False)
        if report["valid"] and (report["parse_status"] != "PASS" or report["structural_status"] != "PASS" or any(d["severity"] != "warning" for d in report["diagnostics"])):
            results["inconsistent_reports"].append({"label": label, "source": repr(source), "report": report})
        if reject and report["valid"]:
            results["unexpected_passes"].append({"label": label, "source": repr(source), "report": report})
        if record:
            results["targeted"].append({"label": label, "source_length": len(source), "valid": report["valid"], "parse_status": report["parse_status"], "structural_status": report["structural_status"], "codes": sorted(set(d["code"] for d in report["diagnostics"]))})
    except Exception:
        results["crashes"].append({"label": label, "source": repr(source), "traceback": traceback.format_exc()})


started = time.perf_counter()
check("baseline", BASE, record=True)
states = ["^10", "^", "^A", "^8^X", "^8^CC", "^8^C_{F0}", "^8^C_{F8}", "^8^C_{F2x}", "^8^C|Q", "^8^C|Ω", "^8^C|Aevil", "^8^C|⟨⟩", "^8^C|⟨A,T,⟩", "^8^C|⟨A T⟩", "^8 ^C", "^8", "^C", "^8^C + ^9^C", "^8^C|A + ^8^C|f", "^8^C|⟨A,⟨T,f⟩⟩", "^8^C_{F2}|A[0]", "^8^C_{F2}|A.foo", "^8^C|<A,T>"]
for state in states:
    check("state:" + state, BASE.replace("^8^C_{F2}|A", state), reject=state != "^8^C|⟨A,⟨T,f⟩⟩", record=True)
terminals = ["missing", "cause.foo", "cause[0]", "cause[-1]", "cause[.5]", "^P", "^8", "^8^C|Q", "^8^C|⟨⟩", "probe", "stage1", "result", "prompt", "a::b", "null", '"cause"', "cause extra", "cause + effect", "cause()", "cause; node hidden: ^2^C; cause"]
for value in terminals:
    check("terminal:" + value, BASE.replace("CJT< cause |", "CJT< " + value + " |"), reject=True, record=True)
numbers = ["NaN", "nan", "inf", "Infinity", "1e309", "+1", "1_000", "0x10", "-0.1", "1s", "true", "null", "[1]", '"1"', ".", "1.", "9" * 512, "1" * 513, "0." + "0" * 509 + "1", "0." + "0" * 510 + "1"]
for value in numbers:
    for old in ["beta=0.5", "beta=0.2"]:
        check("number:" + old + ":" + value[:30] + ":len=" + str(len(value)), BASE.replace(old, "beta=" + value), reject=value != "0." + "0" * 509 + "1", record=True)
unsupported = ["rail F7=1;", "monitor x: cause > 1;", "assert cause.foo == 1;", "assert cause < effect;", "gate x: AND< cause,effect >;", "xnor x: XNOR<cause,effect>;", "let x = Resistor<cause,R=1>;", 'alert "safe // }";', "series stage1 -> cause;", "sequence x: F7 -> F2;", "transition t: effect -> missing;", "probe tp: prompt;"]
for statement in unsupported:
    check("unsupported:" + statement, BASE[:-1] + statement + "}", reject=True, record=True)
for value in ["beta=1,β=2", "β=1,b=2", "beta=1,beta=2"]:
    check("alias:" + value, BASE.replace("beta=0.2", value), reject=True, record=True)
for statement in ["node n: ^2^C;" * 513, "node n: ^2^C;" * 512, "node n: ^2^C|" + "⟨" * 33 + "A" + "⟩" * 33 + ";", "feedback cause -> effect [beta=" + "[" * 33 + "1" + "]" * 33 + "];"]:
    check("size:statements/nesting", "board limits {" + statement + "}", reject=True, record=True)
for length in [65535, 65536, 65537, MAX_SOURCE_BYTES, MAX_SOURCE_BYTES + 1]:
    prefix = "board limits {} //"
    source = prefix + "x" * max(0, length - len(prefix))
    check("byte-bound:" + str(length), source, reject=length > MAX_SOURCE_BYTES, record=True)
for value in [b"\xff", "\ud800", b"board x {}\x00", "board x {\x00}"]:
    check("encoding:" + repr(value), value, reject=True, record=True)
for at in range(len(BASE)):
    check("truncated:" + str(at), BASE[:at], reject=True)
randomizer = random.Random(results["seed"])
alphabet = list("{}[]()<>,:;=.|^abc0123_ \n\t\"/+-") + ["β", "⟨", "⟩", "Ω", "\x00", "\ufeff"]
for index in range(1800):
    source = BASE
    for _ in range(randomizer.randint(1, 5)):
        start = randomizer.randrange(len(source) + 1)
        end = min(len(source), start + randomizer.randrange(4))
        insertion = "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(4)))
        source = source[:start] + insertion + source[end:]
    check("mutation:" + str(index), source)
for index in range(600):
    body = "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(250)))
    check("random:" + str(index), "board x {" + body + "}")
results["elapsed_seconds"] = time.perf_counter() - started
results["reader_max_source_bytes"] = MAX_SOURCE_BYTES
results["final_source_hashes"] = {name: hashlib.sha256((LAB / name).read_bytes()).hexdigest() for name in results["loaded_source_hashes"]}
output = Path(__file__).with_name("review_result.json")
output.write_text(json.dumps(results, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps({key: results[key] for key in ["cases", "elapsed_seconds", "reader_max_source_bytes"]}))
print(json.dumps({key: len(results[key]) for key in ["crashes", "unexpected_passes", "inconsistent_reports"]}))
for category in ["crashes", "unexpected_passes", "inconsistent_reports"]:
    for item in results[category][:10]:
        print(category, json.dumps(item))
print(output)
