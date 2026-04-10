"""Pretty-print the CAS full demo execution log."""
import json
import os
import subprocess

here = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(here)

result = subprocess.run(
    ["python", "-m", "api.notation", "--mode", "run", "--file", "docs/CAS_FULL_DEMO_APP.cas"],
    cwd=project_root,
    capture_output=True,
    text=True,
)

data = json.loads(result.stdout)

print("=" * 65)
print("  CAS FULL LANGUAGE DEMO — COMPILATION SUCCESS")
print("=" * 65)
print()
print(f"  Engine:      {data['engine']}")
print(f"  Valid:       {data['valid']}")
print(f"  Tokens:      {len(data['tokens'])}")
print(f"  AST nodes:   {len(data['ast']['statements'])}")
print(f"  Bytecode:    {len(data['bytecode'])} instructions")
print(f"  Warnings:    {len(data['warnings'])}")
print(f"  Errors:      {data['error']}")
print()
print("-" * 65)
print("  PROGRAM EXECUTION LOG")
print("-" * 65)

for item in data['result']['results']:
    k = item['kind']
    if k == 'module':
        name = os.path.basename(item['path'])
        exports = ', '.join(item['exports'])
        print(f"  [MODULE]  {name}")
        print(f"            exports: {exports}")
    elif k == 'binding':
        name = item['name']
        v = item['value']
        if isinstance(v, str):
            print(f"  [LET]     {name:20s} -> string \"{v}\"")
            continue
        if not isinstance(v, dict):
            print(f"  [LET]     {name:20s} -> {type(v).__name__} {v}")
            continue
        if v.get('kind') == 'state':
            print(f"  [LET]     {name:20s} -> state {v['dominant_state']} ({v['dominant_operator']}, drive {v['dominant_drive']})")
        elif v.get('kind') == 'fractal':
            seq = v.get('sequence', [])
            print(f"  [LET]     {name:20s} -> fractal <{':'.join(str(x) for x in seq)}>")
        elif v.get('kind') == 'rpm':
            comp = v.get('completeness', 'n/a')
            drive = v.get('drive', 'n/a')
            print(f"  [LET]     {name:20s} -> rpm (drive {drive}, completeness {comp})")
        elif v.get('kind') == 'string':
            print(f"  [LET]     {name:20s} -> string \"{v.get('value', '')}\"")
        elif v.get('kind') == 'relation':
            src = v['source']['dominant_state']
            tgt = v['target']['dominant_state']
            print(f"  [LET]     {name:20s} -> relation {src} -> {tgt} (admissible: {v['admissible']})")
        else:
            print(f"  [LET]     {name:20s} -> {v.get('kind')}")
    elif k == 'function':
        print(f"  [FN]      {item.get('name', '?')}")
    elif k == 'relation':
        src = item['source']['dominant_state']
        tgt = item['target']['dominant_state']
        print(f"  [EXPR]    relation {src} -> {tgt} (admissible: {item['admissible']})")

print()
print("-" * 65)
print("  FINAL EXPRESSION RESULT")
print("-" * 65)
fr = data['result'].get('final_result', {})
if fr.get('kind') == 'relation':
    src = fr['source']
    tgt = fr['target']
    print(f"  Relation type:  {fr['relation']}")
    print(f"  Admissible:     {fr['admissible']}")
    print(f"  Descent valid:  {fr['domain_descent_ok']}")
    print(f"  Source state:   {src['dominant_state']} ({src['dominant_operator']} in {src['dominant_domain']} domain, {src['dominant_drive']})")
    print(f"  Target state:   {tgt['dominant_state']} ({tgt['dominant_operator']} in {tgt['dominant_domain']} domain, {tgt['dominant_drive']})")
print()
print("=" * 65)
