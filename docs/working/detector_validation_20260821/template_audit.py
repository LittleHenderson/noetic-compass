"""TEMPLATE/REGEX AUDIT -- blocking manipulation check to run BEFORE any GPU spend.

Lesson from v19 (2026-08-21): the char-ngram surface control UNDERSTATES the surface ceiling.
A stimulus grid can pass char-ngram (0.688) while a three-line regex solves it perfectly (1.000).
Passing char-ngram is NECESSARY, NOT SUFFICIENT.

Usage: give it {class: [sentences]} and candidate marker regexes. If any short rule separates the
classes above the gate (default 0.35), the grid is template-confounded -- DO NOT SPEND GPU ON IT.
"""
import re, itertools, json

def rule_accuracy(classes, patterns):
    """patterns: {class_label: regex}. Unmatched items fall to the residue class (the one with no pattern)."""
    residue=[c for c in classes if c not in patterns]
    residue=residue[0] if len(residue)==1 else None
    ok=tot=0; per={}
    for c,sents in classes.items():
        for s in sents:
            hit=[lab for lab,pat in patterns.items() if re.search(pat,s,flags=re.I)]
            pred=hit[0] if len(hit)==1 else (residue if not hit else hit[0])
            ok+=(pred==c); tot+=1; per[f"{c}->{pred}"]=per.get(f"{c}->{pred}",0)+1
    return ok/tot, per

def marker_leakage(classes, pattern, target):
    """How cleanly does one regex pick out the target class? Returns (in_class, out_class, n_in, n_out)."""
    inn=sum(1 for s in classes[target] if re.search(pattern,s,flags=re.I))
    out=sum(1 for c,ss in classes.items() if c!=target for s in ss if re.search(pattern,s,flags=re.I))
    n_in=len(classes[target]); n_out=sum(len(ss) for c,ss in classes.items() if c!=target)
    return inn,out,n_in,n_out

def audit(classes, patterns, gate=0.35, verbose=True):
    acc,per=rule_accuracy(classes,patterns)
    passed = acc <= gate
    if verbose:
        print(f"template-rule accuracy: {acc:.3f} (gate <= {gate})  -> {'PASS (safe to spend)' if passed else 'FAIL -- TEMPLATE-CONFOUNDED, DO NOT SPEND GPU'}")
        print("confusion:",per)
        for lab,pat in patterns.items():
            i,o,ni,no=marker_leakage(classes,pat,lab)
            print(f"  {lab}: '{pat[:40]}' in-class {i}/{ni}, out-of-class {o}/{no}")
    return {"rule_accuracy":round(acc,3),"gate":gate,"passed":bool(passed),"confusion":per}

if __name__=="__main__":
    # demo: the v19 grid FAILS this audit at 1.000
    print("See RESULT_DETECTOR_VALIDATION_V19_DECISIVE_NULL_AND_V11_V15_CORRECTION_20260821.md")
