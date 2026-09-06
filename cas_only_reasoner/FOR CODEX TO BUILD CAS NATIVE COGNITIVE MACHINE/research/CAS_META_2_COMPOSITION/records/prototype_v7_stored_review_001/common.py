"""Pure v7 packet utilities. External source and packet identities are required."""
from contextlib import contextmanager
from hashlib import sha256
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = None  # Supplied externally for each actual review.
OLD_SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
OLD_PACKET = 'db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def'
ADMISSION = 'd479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420'
RUNTIME = '897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37'
BASELINE = '0917267b1354e5d036263eaa6ba9a7197eafb776'
OLD_JOB = 'cas-meta2-20260906064703-c0d74ffa'
PILOT = 'research/CAS_META_2_COMPOSITION'
BASE = 'cloud_job/campaign/'
NATIVE = BASE+'native/'
ARMS = ('cas_untrained','cas_trained','generic_untrained','generic_trained','rule')
FIELDS = ('task_correct','procedure_correct','binding_correct','dependency_correct','actual_output_correct','trace_valid')
FAILURE = 'POST_ADMISSION_RUNTIME_FAILURE'
MESSAGE = 'repair cannot open without a durable distinct ^6 round trip'
HEX = re.compile(r'[0-9a-f]{64}\Z')
FORBIDDEN = {'torch','casformer','cas_cjt','cas_meta','tensorflow','jax','cupy','boto3','botocore'}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def decode(raw):
    require(len(raw) <= 64*1024**2,'REVIEW_JSON_BOUND')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'REVIEW_DUPLICATE_JSON_KEY')
            result[key]=value
        return result
    result=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('REVIEW_NONFINITE_JSON')))
    canonical(result)
    return result


def regular(path):
    path=Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
            for p in (path,*path.parents)),'REVIEW_FILE_MISSING_OR_LINK')
    return path


def file_hash(path):
    result=sha256()
    with regular(path).open('rb') as stream:
        for raw in iter(lambda:stream.read(1024**2),b''):result.update(raw)
    return result.hexdigest()


def pin(path,expected):
    require(type(expected) is str and HEX.fullmatch(expected) and file_hash(path)==expected,'REVIEW_EXTERNAL_PIN_MISMATCH')


def safe_name(name):
    require(type(name) is str and name and '\\' not in name and ':' not in name and not name.startswith('/')
            and all(part not in ('','.','..') for part in name.split('/')),'REVIEW_UNSAFE_MEMBER')
    return name


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        require(fullname.split('.')[0] not in FORBIDDEN,'REVIEW_NEURAL_PROVIDER_IMPORT_REFUSED')


@contextmanager
def pure_guard():
    require(not any(name in sys.modules for name in FORBIDDEN),'REVIEW_PROCESS_ALREADY_IMPORTED_NEURAL_PROVIDER')
    hooks,paths=list(sys.meta_path),list(sys.path)
    sys.meta_path.insert(0,Guard());sys.path.insert(0,str(ROOT))
    try:yield
    finally:sys.meta_path[:],sys.path[:]=hooks,paths


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Packet:
    """Every extracted byte is matched to a pinned ZIP before semantic reads."""
    def __init__(self,path,expected,extracted,*,create=False):
        pin(path,expected)
        require(regular(path).stat().st_size <= 1024**3,'REVIEW_COMPRESSED_BOUND')
        self.archive_path,self.archive_sha256,self.root=Path(path),expected,Path(extracted).absolute()
        require(not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (self.root,*self.root.parents)),
                'REVIEW_EXTRACTION_LINK')
        if create:
            require(not self.root.exists() and self.root.resolve().is_relative_to(HERE.resolve()),'REVIEW_NEW_EXTRACTION_REQUIRED')
        else:require(self.root.is_dir(),'REVIEW_EXTRACTION_MISSING')
        self.inventory={}
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist();spellings={}
            require(0 < len(infos) <= 65536 and sum(i.file_size for i in infos) <= 2*1024**3,'REVIEW_EXPANDED_BOUND')
            for info in infos:
                name=safe_name(info.filename)
                require(not info.is_dir() and not info.flag_bits & 1 and name not in self.inventory
                        and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG),'REVIEW_MEMBER_TYPE_OR_DUPLICATE')
                for i in range(1,len(name.split('/'))+1):
                    part='/'.join(name.split('/')[:i]);key=part.casefold()
                    require(key not in spellings or spellings[key]==part,'REVIEW_CASE_ALIAS')
                    spellings[key]=part
                self.inventory[name]={'path':name,'bytes':info.file_size,'sha256':None}
            require(not any('/'.join(name.split('/')[:i]) in self.inventory
                    for name in self.inventory for i in range(1,len(name.split('/')))),'REVIEW_FILE_DIRECTORY_ALIAS')
            if create:self.root.mkdir(parents=True,exist_ok=False)
            for info in infos:
                name=info.filename;h=sha256();count=0
                destination=self.root.joinpath(*name.split('/'))
                if create:destination.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(info) as stream:
                    target=destination.open('xb') if create else None
                    try:
                        for raw in iter(lambda:stream.read(1024**2),b''):
                            count+=len(raw);require(count<=info.file_size,'REVIEW_MEMBER_SIZE')
                            h.update(raw)
                            if target:target.write(raw)
                    finally:
                        if target:target.close()
                require(count==info.file_size,'REVIEW_MEMBER_SIZE')
                self.inventory[name]['sha256']=h.hexdigest()
        self.verify_all()

    def path(self,name):
        require(safe_name(name) in self.inventory,'REVIEW_UNINDEXED_MEMBER:'+name)
        path=regular(self.root.joinpath(*name.split('/')))
        row=self.inventory[name]
        require(path.resolve().is_relative_to(self.root.resolve()) and path.stat().st_size==row['bytes']
                and file_hash(path)==row['sha256'],'REVIEW_EXTRACTED_BYTES_CHANGED:'+name)
        return path

    def raw(self,name,limit=64*1024**2):
        require(type(limit) is int and 0<limit<=64*1024**2 and self.inventory[name]['bytes']<=limit,'REVIEW_JSON_BOUND')
        return self.path(name).read_bytes()

    def json(self,name):return decode(self.raw(name))
    def same_hash(self,name,expected):
        require(name in self.inventory and self.inventory[name]['sha256']==expected,'REVIEW_MEMBER_BINDING:'+name)

    def verify_all(self):
        actual=set()
        for directory,dirs,files in os.walk(self.root,followlinks=False):
            for name in dirs:
                p=Path(directory)/name
                require(not p.is_symlink() and not getattr(p,'is_junction',lambda:False)(),'REVIEW_EXTRACTION_LINK')
            for name in files:
                member=(Path(directory)/name).relative_to(self.root).as_posix()
                self.path(member);actual.add(member)
        require(actual==set(self.inventory),'REVIEW_EXTRACTION_COVERAGE')
        pin(self.archive_path,self.archive_sha256)



PRIOR_REVIEW = '5396e0ab263fa435eefd2b8925382ce802b7af7c8d1c4dae5702d51435349ac3'
PRIOR_REVIEW_PATH = 'research/CAS_META_2_COMPOSITION/records/contrast_recovery_v6_review_001/run_001/recovery_stored_review.json'


def source_preflight(archive, expected, source):
    require(type(source) is str and re.fullmatch('[0-9a-f]{40}',source),'V7_EXTERNAL_SOURCE_SHA_REQUIRED')
    pin(archive,expected)
    repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip())
    require(subprocess.check_output(['git','rev-parse',source+'^{commit}'],cwd=repo,text=True).strip()==source,
            'V7_FROZEN_COMMIT_MISSING')
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist()
        require(len(infos)==604 and sum(i.file_size for i in infos)<=128*1024**2
            and all(not i.is_dir() and not i.flag_bits&1 and stat.S_IFMT(i.external_attr>>16) in (0,stat.S_IFREG)
                    for i in infos),'V7_SOURCE_ARCHIVE_BOUND_OR_TYPE')
        names=z.namelist()
        require(len(names)==len(set(names))==len({x.casefold() for x in names}),'V7_SOURCE_DUPLICATE')
        for name in names:safe_name(name)
        m=decode(z.read('launch_manifest.json'));mapping=m['files_sha256']
        require(m['source_sha']==source and m['baseline_sha']==BASELINE and m['protected_baseline_files']==316
            and m['original_source_files']==538 and m['prototype_additional_files']==65 and len(mapping)==603
            and set(names)==set(mapping)|{'launch_manifest.json'},'V7_SOURCE_CLOSURE')
        require(m['prototype']['prerequisite_review_path']==PRIOR_REVIEW_PATH
            and m['prototype']['prerequisite_review_sha256']==PRIOR_REVIEW
            and mapping[PRIOR_REVIEW_PATH]==PRIOR_REVIEW
            and m['prototype']['recovery_manifest_sha256']==RUNTIME,'V7_PREREQUISITE_PIN')
        files={name:z.read(name) for name in mapping};requests=[]
        for name,raw in files.items():
            path=ROOT.parents[1]/safe_name(name)
            require(name.startswith('research/') and sha256(raw).hexdigest()==mapping[name]
                and file_hash(path)==mapping[name],'V7_LOCAL_SOURCE_CHANGED:'+name)
            requests.append(source+':'+path.relative_to(repo).as_posix())
        response=subprocess.run(['git','cat-file','--batch'],input=('\n'.join(requests)+'\n').encode(),
            cwd=repo,check=True,capture_output=True).stdout
        offset=0
        for name,raw in files.items():
            end=response.index(b'\n',offset);header=response[offset:end].split()
            require(len(header)==3 and header[1]==b'blob','V7_GIT_BLOB_REQUIRED')
            length=int(header[2]);offset=end+1
            require(response[offset:offset+length]==raw,'V7_SOURCE_DIFFERS_FROM_GIT:'+name)
            offset+=length;require(response[offset:offset+1]==b'\n','V7_GIT_BATCH_FORMAT');offset+=1
        require(offset==len(response),'V7_GIT_BATCH_EXTRA_DATA')
        prior=decode(files[PRIOR_REVIEW_PATH])
        require(prior['completed'] is True and prior['status']=='RECOVERY_STORED_REVIEW_PASSED'
            and prior['errors']==[] and prior['outcomes']['references_checked']==72
            and prior['outcomes']['arms_checked']==360,'V7_PRIOR_REVIEW_INCOMPLETE')
        baseline_raw=files['research/CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json']
        require(sha256(baseline_raw).hexdigest()=='476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0',
            'V7_PROTECTED_MANIFEST_CHANGED')
        baseline=decode(baseline_raw)
        require(baseline['baseline_sha']==BASELINE and len(baseline['files'])==316,'V7_BASELINE_IDENTITY')
        for item in baseline['files']:
            require(mapping['research/'+item['path']]==item['sha256'],'V7_PROTECTED_BYTES_CHANGED')
    # Import only after every closed local source byte has matched the archive and Git.
    profile=load('_v7_bound_source_profile',ROOT/'tools/experiment_profiles_prototype_v7.py')
    require(profile.validate_launch_manifest(m,files.__getitem__)==m['experiment'],'V7_PROFILE_CHANGED')
    profile.require_execution_ready(profile.validate_prototype_spec(files[profile.SPEC_PATH]))
    return m,prior


def prior_helpers(prior):
    directory=ROOT/'records/contrast_recovery_v6_review_001'
    result={}
    for name in ('evidence','outcomes','partial','report'):
        path=directory/(name+'.py')
        pin(path,prior['reviewer_files_sha256'][name+'.py'])
        result[name]=load('_v7_pinned_prior_'+name,path)
    path=ROOT/'records/first_transition_review_v5_001/run.py'
    pin(path,prior['frozen_first_difference_sha256'])
    result['differences']=load('_v7_bound_first_differences',path)
    require(result['differences'].self_checks()==11,'V7_DIFFERENCE_SELF_CHECK')
    return result


def check_source_again(manifest):
    for name,pin_value in manifest['files_sha256'].items():
        require(file_hash(ROOT.parents[1]/name)==pin_value,'REVIEW_SOURCE_CHANGED_DURING_AUDIT')


def remote_member(path):
    prefix='/opt/cas-meta2/package/'+PILOT+'/runs/'
    require(type(path) is str and path.startswith(prefix),'REVIEW_UNEXPECTED_REMOTE_PATH')
    return safe_name(path[len(prefix):])
