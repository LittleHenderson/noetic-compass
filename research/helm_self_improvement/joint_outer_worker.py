"""AWS-only public CPU delivery for the new joint worker; no model execution."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import zipfile


def run(bucket, region):
    base = Path(__file__).resolve().parent
    cfg = json.loads((base / 'job.json').read_bytes())
    out = base / 'outer-output'; out.mkdir(exist_ok=False)
    began = time.monotonic()
    result = {'status': 'FAILED', 'source_commit': cfg['source_commit'], 'commands': []}
    try:
        for row in cfg['inputs']:
            path = base / row['path']
            if not path.resolve().is_relative_to(base.resolve()) or sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('INPUT_HASH:' + row['path'])
        repo = base / 'source'; repo.mkdir()
        with zipfile.ZipFile(base / 'source.zip') as z:
            for row in z.infolist():
                if not (repo / row.filename).resolve().is_relative_to(repo): raise ValueError('ARCHIVE_PATH')
            z.extractall(repo)
        env = os.environ.copy()
        env.update({'PYTHONDONTWRITEBYTECODE':'1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
                    'PYTHONPATH':str(base / 'pip.whl'), 'PIP_DISABLE_PIP_VERSION_CHECK':'1'})
        deps = base / 'deps'
        def command(name, argv, cwd=base):
            remaining = 900 - (time.monotonic() - began)
            if remaining <= 0: raise TimeoutError('JOINT_OUTER_DEADLINE')
            p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=remaining)
            (out / (name + '.stdout')).write_bytes(p.stdout); (out / (name + '.stderr')).write_bytes(p.stderr)
            result['commands'].append({'name':name, 'argv':argv, 'returncode':p.returncode})
            if p.returncode: raise RuntimeError('COMMAND_FAILED:' + name)
        command('pinned_dependencies', [sys.executable, '-m', 'pip', 'install', '--retries', '0',
            '--target', str(deps), 'pytest==9.0.2', 'pydantic==2.12.5', 'boto3==1.43.87'])
        env['PYTHONPATH'] = str(deps) + ':' + str(repo)
        env['HELM_JOINT_JOB_ADMITTED'] = '1'
        sys.path.insert(0, str(deps))
        command('joint_worker', [sys.executable, '-B', '-m', 'research.helm_self_improvement.joint_worker',
            '--out', str(base / 'joint-output'), '--implementation-commit', cfg['source_commit']], cwd=repo)
        record = json.loads((base / 'joint-output/joint_worker_receipt.json').read_bytes())
        result.update(status=record['status'], tests=record['junit'],
            reload_status=record['reload']['status'],
            witness_disposition=json.loads((base/'joint-output/episode/episode.json').read_bytes())['receipt']['disposition'])
    except BaseException as error:
        result['error_type'], result['error'] = type(error).__name__, str(error)
    finally:
        result['elapsed_seconds'] = time.monotonic() - began
        (out/'outer_receipt.json').write_text(json.dumps(result,indent=2))
        archive = base/'outputs.tar.gz'
        with tarfile.open(archive,'w:gz') as stream:
            stream.add(out,arcname='outer')
            if (base/'joint-output').exists(): stream.add(base/'joint-output',arcname='joint')
        raw=archive.read_bytes()
        if len(raw)>32*1024*1024: raise ValueError('JOINT_EVIDENCE_BOUND')
        import boto3
        from botocore.config import Config
        client=boto3.client('s3',region_name=region,endpoint_url='https://s3.'+region+'.amazonaws.com',
            config=Config(signature_version='s3v4',s3={'addressing_style':'path'},retries={'total_max_attempts':1},connect_timeout=5,read_timeout=30))
        for path,key in [(out/'outer_receipt.json','outputs/outer_receipt.json'),
                         (base/'joint-output/joint_worker_receipt.json','outputs/joint_worker_receipt.json'),
                         (base/'joint-output/joint-junit.xml','outputs/joint-junit.xml')]:
            if path.exists(): client.put_object(Bucket=bucket,Key=key,Body=path.read_bytes())
        client.put_object(Bucket=bucket,Key='outputs/outputs.tar.gz',Body=raw)
        client.put_object(Bucket=bucket,Key='outputs/terminal.json',Body=json.dumps({**result,'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}).encode())
    return 0 if result['status']=='JOINT_ENGINEERING_CHECKS_COMPLETED' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bucket',required=True);p.add_argument('--region',required=True)
    a=p.parse_args();raise SystemExit(run(a.bucket,a.region))
