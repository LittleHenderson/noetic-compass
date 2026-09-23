import sys, os, json, io, contextlib, importlib.util
R=sys.argv[1]
spec=importlib.util.spec_from_file_location('gp',os.path.join(os.path.dirname(__file__),'g_parse.py'))
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    gp=importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
d=json.load(open(os.path.join(R,'records','q4_authorized_20260922','inspected_predictions.json'),encoding='utf-8'))['cases']
dv={r['record_id']:p for r,p in zip(*gp.out['dev'])}
ok=0
for c in d:
    rid=c.get('record_id'); ref=c['checker_reference_ast']
    ok+= dv[rid]==ref
print('cases',len(d),'my parser == checker_reference_ast',ok, 'pred == ref', sum(c.get('checker_canonical_exact') for c in d))
