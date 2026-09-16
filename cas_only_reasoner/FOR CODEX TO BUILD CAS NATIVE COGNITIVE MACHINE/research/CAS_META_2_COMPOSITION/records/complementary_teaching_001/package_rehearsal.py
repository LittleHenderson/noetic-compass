"""Pure extraction/import/real worker dispatch rehearsal; neural imports denied."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

package = Path(sys.argv[1]).resolve()
process_cwd = Path(__file__).resolve().parents[2]
archive_path = package / 'source.zip'
scratch = package / '_scratch'
(package/'.gitignore').write_bytes(b'_scratch/\n')
scratch.mkdir(exist_ok=True)
with ZipFile(archive_path) as archive:
    for item in archive.infolist():
        target = (scratch / item.filename).resolve()
        assert target.is_relative_to(scratch)
    archive.extractall(scratch)
manifest = json.loads((scratch / 'graph6_curriculum_source_manifest.json').read_bytes())
verified = []
for relative, expected in manifest['files_sha256'].items():
    raw = (scratch / relative).read_bytes()
    assert sha256(raw).hexdigest() == expected, relative
    verified.append(relative)
worker = (scratch / 'complementary_teaching_worker.py').read_text(encoding='utf-8')
tree = ast.parse(worker)
inner = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'INNER_RUNNER' for target in node.targets):
        assert isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='join'
        inner = ast.literal_eval(node.value.args[0])
assert inner and 'from cas_meta2.complementary_teaching import runner' in inner
denial = '''
import sys, importlib.abc
class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','cas_cjt','casformer','boto3','botocore'}:
            raise RuntimeError('PURE_REHEARSAL_FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,NoNeural())
'''
config = manifest['candidate_design']['worker_config']
assert config['execution_enabled'] is False
(scratch / 'config.json').write_text(json.dumps(config),encoding='utf-8')
dispatch = subprocess.run([sys.executable,'-I','-c',denial+'\n'+'\n'.join(inner),str(scratch)],
                          cwd=process_cwd,capture_output=True,text=True,timeout=60)
assert dispatch.returncode != 0 and 'COMPLEMENTARY_EXECUTION_DISABLED' in dispatch.stderr, dispatch.stderr
assert 'PURE_REHEARSAL_FORBIDDEN_IMPORT' not in dispatch.stderr
code = denial + '''
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'research/CAS_META_2_COMPOSITION'))
from cas_meta2.complementary_teaching import course,data,runner
document=data.validate_manifest(json.loads((root/'research/CAS_META_2_COMPOSITION'/runner.DATA_PATH).read_bytes()))
counts=[]
for seed in course.SEEDS:
    for condition in course.CONDITIONS:
        value=course.compile_complementary_course(seed,condition)
        assert value['counts']['decisions']==1152 and value['counts']['optimizer_updates']==160
        assert value['counts']['sample_core_passes_planned']==4320
        counts.append({'seed':seed,'condition':condition,'schedule_sha256':value['schedule_sha256'],'counts':value['counts']})
assert 'torch' not in sys.modules
print(json.dumps({'courses':counts,'data_sha256':document['data_sha256'],'imported_module':runner.__file__}))
'''
compiled = subprocess.run([sys.executable,'-I','-c',code,str(scratch)],cwd=process_cwd,
                          capture_output=True,text=True,timeout=120)
assert compiled.returncode == 0, compiled.stderr
body = json.loads(compiled.stdout)
report = {'schema':'cas.complementary-packaged-rehearsal/0.1','status':'PASS',
    'source_sha':manifest['source_sha'],'archive_sha256':sha256(archive_path.read_bytes()).hexdigest(),
    'verified_package_members':len(verified),'real_worker_dispatch':'COMPLEMENTARY_EXECUTION_DISABLED before torch/model/provider import',
    'actual_course_compilation':body,'actual_neural_presentations':0,'actual_optimizer_updates':0,
    'actual_provider_calls':0,'boundary':'Validates package imports/bytes/compiler and guarded dispatch only; no neural or provider outcome.'}
(package/'REHEARSAL.json').write_bytes((json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
(package/'.gitignore').write_bytes(b'_scratch/\n')
print(json.dumps({'status':'PASS','archive_sha256':report['archive_sha256'],'members':len(verified),'courses':len(body['courses'])}))
