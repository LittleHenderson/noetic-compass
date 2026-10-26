"""AWS-only PRE-CHECK supervisor for Option B job b1 (operator decision D7): four stages, each run once, CPU only.

1. opt_pytorch_inventory  what the image's /opt/pytorch environment really contains
2. overlay_install        the package's own venv + pinned pip overlay commands
3. import_smoke           can the overlay see the image torch; are the nine pins exact
4. selftest               'runner_b1.py selftest --mode precheck', once (tokenizer only)

No model B weights are in the payload. No model call, no experiment, no training,
no promotion, no retry. A failing stage never stops later independent evidence
collection. Exit 0 means "evidence collected" (the status says SELFTEST_PASS or
WITH_FINDINGS); exit 1 only when this supervisor itself stopped. A self-test pass
is a software result. It is not a finding about roles.

Derived from cas_probe_supervisor.py (the CPU software probe that ran on 2026-10-04).
Stages 1 to 3 are unchanged. Stage 4 and the 35 minute window are new and have never
run. The four values between double at-signs are filled by derive_precheck_job.py:
the job id, the kind of job, and the two package hashes.

Review round 1 (plan section 19.1): each pre-check job has its own job id. The kind
is SEALED_PACKAGE, REHEARSAL or DEVELOPMENT_TEST. Only a SEALED_PACKAGE job returns
values for seal step 7. The receipt also carries the plain facts that say which of
the plan's cases a failed pre-check is.

Every child process gets an explicitly built environment. Nothing from the
systemd unit's environment (PYTHONPATH, guard names, proxies) is passed on.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback

JOB = '@@JOB@@'
PRECHECK_KIND = '@@PRECHECK_KIND@@'
SOURCE_ARCHIVE_SHA256 = '@@SOURCE_ARCHIVE_SHA256@@'
BUNDLE_MANIFEST_SHA256 = '@@BUNDLE_MANIFEST_SHA256@@'
# The work window the controller grants: 35 minutes after launch (host limit 45 minutes, forced stop at 40).
MAXIMUM_WORKLOAD_SECONDS = 2100
# Where the six small model B files sit under the job root (PLAN_CONSTANTS.json, model_b.snapshot_path_in_payload).
MODEL_SNAPSHOT = 'models/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775'
# The one command of this job (FILE_FORMATS.md section 16). {PACKAGE}, {MODEL} and {OUTPUT} are absolute folders.
# The names of the three folder flags are not fixed by FILE_FORMATS.md. derive_precheck_job.py refuses to build
# unless every word here that starts with '--' also occurs in job/runner_b1.py of the sealed source.zip.
SELFTEST_ARGV = ('selftest', '--mode', 'precheck', '--package-dir', '{PACKAGE}', '--model-dir', '{MODEL}',
                 '--output-dir', '{OUTPUT}')
SELFTEST_PASS = 'SELFTEST_PASS'
RECEIPT_RESERVE_SECONDS = 30
IMAGE_PYTHON = '/opt/pytorch/bin/python'
IMAGE_SITE_PACKAGES = '/opt/pytorch/lib/python3.12/site-packages'
VENV_SITE_PACKAGES = ('lib', 'python3.12', 'site-packages')
BRIDGE_NAME = '_image_pytorch_bridge.pth'
EXPECTED_TORCH = '2.9.1+cu130'
INDEX_URL = 'https://pypi.org/simple'
OFFICIAL_WHEEL_PREFIX = 'https://files.pythonhosted.org/packages/'
RAW_REPORT_KEEP_BYTES = 2 * 1024 * 1024
RAW_REPORT_PARSE_BYTES = 64 * 1024 * 1024
CHILD_PATH = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
STAGES = ('opt_pytorch_inventory', 'overlay_install', 'import_smoke', 'selftest')
# Each stage also stops at what is left of the work window. Measured on 2026-10-04 (probe c02): the first three
# stages together took about 200 seconds. The self-test time is not measured; 900 seconds is an allowance.
LIMITS = {'opt_pytorch_inventory': 60, 'overlay_install': 600, 'import_smoke': 180, 'selftest': 900}
TORCH_PROBE_CAP_SECONDS = 60
# (distribution name, import name), in the order of contracts/requirements.small-linux.txt
PIN_MODULES = (('numpy', 'numpy'), ('scipy', 'scipy'), ('scikit-learn', 'sklearn'), ('joblib', 'joblib'),
               ('threadpoolctl', 'threadpoolctl'), ('transformers', 'transformers'), ('tokenizers', 'tokenizers'),
               ('safetensors', 'safetensors'), ('huggingface-hub', 'huggingface_hub'))
SMOKE_MODULES = (('torch', 'torch'),) + PIN_MODULES + (('jsonschema', 'jsonschema'), ('referencing', 'referencing'))
REQUIRED_FOR_TESTS = ('transformers', 'tokenizers', 'numpy', 'torch')
# Exactly the exports of the package's FUTURE_COMMANDS "Environment and software stage" block,
# plus CUDA_VISIBLE_DEVICES='' because this is a CPU-only probe.
PACKAGE_ENV = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
               'TOKENIZERS_PARALLELISM': 'false', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8', 'CUDA_VISIBLE_DEVICES': ''}

INVENTORY_CODE = '''
import importlib.metadata as metadata
import importlib.util
import json
import sys
from pathlib import Path


def spec_origin(module):
    try:
        spec = importlib.util.find_spec(module)
    except Exception as error:
        return {'found': False, 'origin': None, 'error': type(error).__name__ + ':' + str(error)[:300]}
    if spec is None:
        return {'found': False, 'origin': None}
    return {'found': True, 'origin': spec.origin}


def dist_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None
    except Exception as error:
        return 'ERROR:' + type(error).__name__


def small_text(path):
    try:
        target = Path(path)
        if not target.is_file():
            return None
        return target.read_text(encoding='utf-8', errors='replace')[:4000]
    except Exception as error:
        return 'ERROR:' + type(error).__name__


out = {'schema': 'cas.probe.opt-pytorch-inventory/1', 'sys_prefix': sys.prefix,
       'sys_base_prefix': sys.base_prefix, 'sys_executable': sys.executable,
       'sys_executable_resolved': str(Path(sys.executable).resolve()), 'sys_version': sys.version,
       'sys_path': list(sys.path)}
config = Path('/opt/pytorch/pyvenv.cfg')
out['pyvenv_cfg_present'] = config.is_file()
out['pyvenv_cfg'] = config.read_text(encoding='utf-8', errors='replace') if config.is_file() else None
rows = []
site_dirs = {}
unreadable = 0
for dist in metadata.distributions():
    try:
        name = dist.metadata['Name']
        version = dist.version
    except Exception:
        unreadable += 1
        continue
    rows.append([str(name), str(version)])
    try:
        location = str(dist.locate_file(''))
    except Exception:
        location = 'UNKNOWN'
    site_dirs[location] = site_dirs.get(location, 0) + 1
out['distributions'] = sorted(rows)
out['distribution_count'] = len(rows)
out['distribution_metadata_unreadable'] = unreadable
out['distribution_site_dirs'] = site_dirs
named = {}
for name, module in json.loads(sys.argv[2]):
    version = dist_version(name)
    named[name] = {'present': version is not None, 'version': version, 'module': module,
                   'find_spec': spec_origin(module)}
out['named_packages'] = named
out['venv_prerequisites'] = {'venv': spec_origin('venv'), 'ensurepip': spec_origin('ensurepip'),
                             'pip': spec_origin('pip'), 'pip_version': dist_version('pip')}
out['os_release'] = small_text('/etc/os-release')
out['pip_config_files'] = {path: small_text(path) for path in (
    '/etc/pip.conf', '/opt/pytorch/pip.conf', '/root/.config/pip/pip.conf', '/root/.pip/pip.conf')}
with open(sys.argv[1], 'x', encoding='utf-8') as stream:
    json.dump(out, stream, indent=1, sort_keys=True)
'''

TORCH_PROBE_CODE = '''
import importlib.util
import json
import sys

out = {'sys_path': list(sys.path), 'sys_prefix': sys.prefix, 'sys_base_prefix': sys.base_prefix,
       'sys_executable': sys.executable, 'sys_version': sys.version, 'torch_spec_found': False,
       'torch_spec_origin': None, 'torch_import_attempted': False, 'torch_imported': False}
try:
    spec = importlib.util.find_spec('torch')
    if spec is not None:
        out['torch_spec_found'] = True
        out['torch_spec_origin'] = spec.origin
except Exception as error:
    out['find_spec_error'] = type(error).__name__ + ':' + str(error)[:500]
with open(sys.argv[1], 'x', encoding='utf-8') as stream:
    json.dump(out, stream, indent=1, sort_keys=True)
out['torch_import_attempted'] = True
try:
    import torch
    out['torch_imported'] = True
    out['torch_version'] = str(torch.__version__)
    out['torch_file'] = str(torch.__file__)
except BaseException as error:
    out['import_error'] = type(error).__name__ + ':' + str(error)[:1500]
with open(sys.argv[2], 'x', encoding='utf-8') as stream:
    json.dump(out, stream, indent=1, sort_keys=True)
'''

IMPORT_CODE = '''
import importlib
import importlib.metadata as metadata
import json
import sys

out = {'sys_path': list(sys.path), 'sys_prefix': sys.prefix, 'sys_base_prefix': sys.base_prefix,
       'sys_executable': sys.executable, 'sys_version': sys.version, 'modules': {}}
loaded = {}
for dist_name, module_name in json.loads(sys.argv[2]):
    row = {'distribution': dist_name, 'imported': False, 'metadata_version': None, 'file': None}
    try:
        row['metadata_version'] = str(metadata.version(dist_name))
    except Exception as error:
        row['metadata_error'] = type(error).__name__ + ':' + str(error)[:300]
    try:
        module = importlib.import_module(module_name)
        loaded[module_name] = module
        row['imported'] = True
        row['file'] = str(getattr(module, '__file__', None))
        row['module_version'] = str(getattr(module, '__version__', None))
    except BaseException as error:
        row['import_error'] = type(error).__name__ + ':' + str(error)[:1500]
    out['modules'][module_name] = row
basics = {}
if 'torch' in loaded:
    torch = loaded['torch']
    try:
        basics['torch_version'] = str(torch.__version__)
        basics['torch_version_cuda'] = None if torch.version.cuda is None else str(torch.version.cuda)
        basics['torch_cuda_is_available'] = bool(torch.cuda.is_available())
    except BaseException as error:
        basics['torch_basics_error'] = type(error).__name__ + ':' + str(error)[:1500]
    if 'numpy' in loaded:
        try:
            basics['torch_from_numpy_roundtrip'] = torch.from_numpy(loaded['numpy'].arange(3)).numpy().tolist()
        except BaseException as error:
            basics['torch_from_numpy_error'] = type(error).__name__ + ':' + str(error)[:1500]
out['basics'] = basics
with open(sys.argv[1], 'x', encoding='utf-8') as stream:
    json.dump(out, stream, indent=1, sort_keys=True)
'''


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def atomic(path, document):
    # default=str: an unexpected value type must never cost the whole receipt.
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(document, stream, sort_keys=True, indent=2, default=str)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        # A half-written temporary file must not block the next write.
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def read_json(path):
    """A child's JSON file, or None when it is absent or unreadable. Never raises."""
    try:
        if not path.is_file() or path.is_symlink():
            return None
        return json.loads(path.read_bytes())
    except Exception:
        return None


def display(argv):
    """Receipt form of a command line: inline child programs are named by hash, not repeated."""
    return [('<inline python sha256=' + sha_bytes(item.encode('utf-8')) + '>') if '\n' in item else item
            for item in argv]


def run_step(step, argv, *, env, cwd, end, stdout, stderr, tick, cap=None, mark_stdout=True):
    """One child, once, in its own session. At the limit the whole process group is killed."""
    argv = [str(item) for item in argv]
    limit = end - time.monotonic()
    if cap is not None:
        limit = min(limit, cap)
    row = {'step': step, 'argv': display(argv), 'cwd': str(cwd), 'env': dict(env),
           'timeout_seconds': limit, 'exit_code': None, 'timed_out': False, 'seconds': None}
    if limit <= 0:
        row['status'] = 'NOT_RUN_DEADLINE'
        return row
    header = ('===== step ' + step + ' ' + utc() + ' =====\n').encode('utf-8')
    for handle in ([stdout, stderr] if mark_stdout else [stderr]):
        handle.write(header)
        handle.flush()
    started = time.monotonic()
    row['started_utc'] = utc()
    try:
        child = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=stdout,
                                 stderr=stderr, start_new_session=True)
    except OSError as error:
        row.update(status='SPAWN_FAILED', error=type(error).__name__ + ':' + str(error),
                   seconds=time.monotonic() - started)
        return row
    row['pid'] = child.pid
    cutoff = started + limit
    try:
        while child.poll() is None:
            left = cutoff - time.monotonic()
            if left <= 0:
                row['timed_out'] = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                break
            try:
                child.wait(timeout=min(15, left))
            except subprocess.TimeoutExpired:
                tick()
    finally:
        # The step is over (or this supervisor faulted): nothing in the step's own
        # process group may keep running.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    row.update(exit_code=child.returncode, seconds=time.monotonic() - started)
    row['status'] = 'TIMEOUT' if row['timed_out'] else ('EXIT_0' if child.returncode == 0 else 'EXIT_NONZERO')
    return row


def parse_pins(path):
    """name==version lines of the package's requirements file. Text only."""
    pins, problems = [], []
    for line in path.read_text(encoding='utf-8').splitlines():
        text = line.split('#', 1)[0].strip()
        if not text:
            continue
        parts = text.split('==')
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            problems.append(text)
            continue
        pins.append((parts[0].strip(), parts[1].strip()))
    return pins, problems


def trim_pip_report(path):
    """Name, version, download URL and sha256 of every item pip resolved. Never raises."""
    info = {'present': path.is_file() and not path.is_symlink()}
    if not info['present']:
        return info, None
    info.update(bytes=path.stat().st_size, sha256=sha(path))
    if info['bytes'] > RAW_REPORT_PARSE_BYTES:
        info['parse_error'] = 'RAW_REPORT_TOO_LARGE_TO_PARSE'
        return info, None
    try:
        report = json.loads(path.read_bytes())
        items = []
        for item in report.get('install', []):
            download = item.get('download_info') or {}
            archive = download.get('archive_info') or {}
            digest = (archive.get('hashes') or {}).get('sha256')
            if digest is None and isinstance(archive.get('hash'), str) and archive['hash'].startswith('sha256='):
                digest = archive['hash'][len('sha256='):]
            metadata = item.get('metadata') or {}
            url = download.get('url')
            items.append({'name': metadata.get('name'), 'version': metadata.get('version'), 'url': url,
                          'sha256': digest, 'requested': item.get('requested'),
                          'is_direct': item.get('is_direct'), 'is_yanked': item.get('is_yanked'),
                          'official_pypi_wheel': isinstance(url, str) and url.startswith(OFFICIAL_WHEEL_PREFIX)
                          and url.endswith('.whl')})
        environment = report.get('environment') or {}
        trimmed = {'schema': 'cas.probe.resolved-wheels/1', 'job': JOB,
                   'pip_report_version': report.get('version'), 'pip_version': report.get('pip_version'),
                   'raw_report_sha256': info['sha256'], 'raw_report_bytes': info['bytes'],
                   'environment': {key: environment.get(key) for key in (
                       'implementation_name', 'python_full_version', 'platform_machine', 'sys_platform')},
                   'item_count': len(items),
                   'all_official_pypi_wheels': bool(items) and all(row['official_pypi_wheel'] for row in items),
                   'all_have_sha256': bool(items) and all(isinstance(row['sha256'], str) and len(row['sha256']) == 64
                                                          for row in items),
                   'items': sorted(items, key=lambda row: str(row['name']).lower())}
    except Exception as error:
        info['parse_error'] = type(error).__name__ + ':' + str(error)[:500]
        return info, None
    return info, trimmed


def list_leftovers(folder):
    """What a stage left in its scratch folder: names and sizes only, links never followed."""
    entries, total, links = [], 0, 0
    for base, directories, files in os.walk(folder, followlinks=False):
        for entry in directories + files:
            path = os.path.join(base, entry)
            is_link = os.path.islink(path)
            size = 0
            if not is_link and os.path.isfile(path):
                size = os.path.getsize(path)
            total += size
            links += int(is_link)
            if len(entries) < 100:
                entries.append({'path': os.path.relpath(path, folder), 'bytes': size, 'symlink': is_link})
    return {'entries': entries, 'bytes': total, 'symlinks': links}


def sweep_symlinks(output):
    """worker.sh refuses to package any symlink under results/. Record and remove any that appear."""
    removed = []
    for base, directories, files in os.walk(output, followlinks=False):
        for entry in list(directories) + files:
            path = os.path.join(base, entry)
            if os.path.islink(path):
                removed.append({'path': os.path.relpath(path, output), 'target': os.readlink(path)})
                os.unlink(path)
                if entry in directories:
                    directories.remove(entry)
    return {'symlinks_removed_count': len(removed), 'symlinks_removed': removed[:50]}


def post_run_source_check(root):
    """Sources must still equal the pinned payload bytes after every stage ran."""
    inventory = json.loads((root / 'payload_inventory.json').read_bytes())
    members = {name: pin for name, pin in inventory['members'].items() if name.startswith('sources/')}
    changed = []
    for name, pin in members.items():
        path = root / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size != pin['bytes'] or sha(path) != pin['sha256']:
            changed.append(name)
    extra = sorted(path.relative_to(root).as_posix() for path in (root / 'sources').rglob('*')
                   if (path.is_file() or path.is_symlink()) and path.relative_to(root).as_posix() not in members)
    pycache = sorted(path.relative_to(root).as_posix() for path in (root / 'sources').rglob('__pycache__'))
    return {'members_checked': len(members), 'changed_or_missing': sorted(changed)[:50],
            'changed_or_missing_count': len(changed), 'extra_files_count': len(extra), 'extra_files': extra[:50],
            'pycache_directories_count': len(pycache), 'pycache_directories': pycache[:50]}


class Probe:
    def __init__(self, root, output, deadline_epoch, progress):
        self.root = root
        self.output = output
        self.deadline_epoch = deadline_epoch
        self.progress = progress
        self.overlay = root / 'overlay'
        self.venv = self.overlay / 'venv'
        self.venv_python = self.venv / 'bin' / 'python'
        self.source = root / 'sources' / 'cas'
        self.state = {}

    def seconds_left(self):
        return self.deadline_epoch - time.time() - RECEIPT_RESERVE_SECONDS

    def env(self, extra=None):
        """Explicit child environment. Nothing is inherited from the unit."""
        environment = {'PATH': CHILD_PATH, 'LANG': 'C.UTF-8', 'HOME': str(self.overlay / 'home'),
                       'TMPDIR': str(self.overlay / 'tmp'), 'PYTHONDONTWRITEBYTECODE': '1',
                       'PYTHONNOUSERSITE': '1'}
        environment.update(extra or {})
        return environment

    def stage(self, name, body):
        """Run one stage once. A fault inside a stage is recorded and the next stage still runs."""
        row = {'name': name, 'stage': 'probe', 'status': 'RUNNING', 'limit_seconds': LIMITS[name],
               'commands': [], 'started_utc': utc()}
        started = time.monotonic()
        self.progress(row)
        try:
            folder = self.output / name
            folder.mkdir(exist_ok=False)
            budget = min(LIMITS[name], self.seconds_left())
            if budget <= 0:
                row['status'] = 'NOT_RUN_DEADLINE'
            else:
                body(row, folder, time.monotonic() + budget)
        except Exception as error:
            row.update(status='SUPERVISOR_STAGE_ERROR_RECORDED', error_type=type(error).__name__,
                       reason=str(error)[:1000], traceback=traceback.format_exc()[-3000:])
        if row['status'] == 'RUNNING':
            row['status'] = 'SUPERVISOR_STAGE_LEFT_RUNNING_STATUS'
        row.update(seconds=time.monotonic() - started, finished_utc=utc())
        self.progress(row)
        return row

    # ---------------- 1. what /opt/pytorch contains ----------------
    def inventory(self, row, folder, end):
        target = self.output / 'opt_pytorch_inventory.json'
        named = [list(pair) for pair in (('torch', 'torch'),) + PIN_MODULES]
        with (folder / 'stdout.log').open('ab') as out, (folder / 'stderr.log').open('ab') as err:
            step = run_step('inventory', [IMAGE_PYTHON, '-B', '-c', INVENTORY_CODE, target, json.dumps(named)],
                            env=self.env(), cwd=folder, end=end, stdout=out, stderr=err,
                            tick=lambda: self.progress(row))
        row['commands'].append(step)
        document = read_json(target)
        if step['exit_code'] == 0 and isinstance(document, dict):
            packages = document.get('named_packages') or {}
            row.update(status='COMPLETE', output='results/opt_pytorch_inventory.json', output_sha256=sha(target),
                       distribution_count=document.get('distribution_count'),
                       sys_prefix=document.get('sys_prefix'), sys_base_prefix=document.get('sys_base_prefix'),
                       sys_executable_resolved=document.get('sys_executable_resolved'),
                       pyvenv_cfg_present=document.get('pyvenv_cfg_present'),
                       venv_prerequisites=document.get('venv_prerequisites'),
                       named_packages={name: {'present': (packages.get(name) or {}).get('present'),
                                              'version': (packages.get(name) or {}).get('version')}
                                       for name, unused in named})
        else:
            row['status'] = 'TIMEOUT' if step['timed_out'] else 'FAILED_RECORDED'

    # ---------------- 2. the package's own overlay commands ----------------
    def overlay_install(self, row, folder, end):
        report = folder / 'pip-report.json'
        requirements = self.source / 'contracts' / 'requirements.small-linux.txt'
        environment = self.env({'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_INPUT': '1'})
        tick = lambda: self.progress(row)
        row['requirements_sha256'] = sha(requirements)
        with (folder / 'stdout.log').open('ab') as out, (folder / 'stderr.log').open('ab') as err:
            row['detail'] = 'venv_create'
            step = run_step('venv_create', [IMAGE_PYTHON, '-m', 'venv', '--system-site-packages', self.venv],
                            env=environment, cwd=folder, end=end, stdout=out, stderr=err, tick=tick)
            row['commands'].append(step)
            self.progress(row)
            installed = None
            if step['exit_code'] == 0:
                row['detail'] = 'pip_install'
                installed = run_step('pip_install', [
                    self.venv_python, '-m', 'pip', 'install', '--only-binary=:all:', '--no-cache-dir',
                    '--index-url', INDEX_URL, '--report', report, '-r', requirements],
                    env=environment, cwd=folder, end=end, stdout=out, stderr=err, tick=tick)
                row['commands'].append(installed)
                self.progress(row)
            if installed is not None and os.path.exists(self.venv_python):
                # Run even after a failed install: what the overlay then holds is evidence.
                row['detail'] = 'pip_freeze'
                with (folder / 'installed-versions.txt').open('xb') as frozen:
                    step = run_step('pip_freeze', [self.venv_python, '-m', 'pip', 'freeze', '--all'],
                                    env=environment, cwd=folder, end=end, stdout=frozen, stderr=err, tick=tick,
                                    mark_stdout=False)
                step['evidence_only_after_failed_install'] = installed['exit_code'] != 0
                row['commands'].append(step)
        info, trimmed = trim_pip_report(report)
        if trimmed is not None:
            atomic(folder / 'resolved-wheels.json', trimmed)
            row.update(resolved_item_count=trimmed['item_count'],
                       all_official_pypi_wheels=trimmed['all_official_pypi_wheels'],
                       all_have_sha256=trimmed['all_have_sha256'], pip_version=trimmed['pip_version'])
        info['kept_in_results'] = bool(info['present'])
        if info['present'] and info['bytes'] >= RAW_REPORT_KEEP_BYTES:
            # Too large for the result archive: the trimmed file plus this hash and size stand in for it.
            os.replace(report, self.overlay / 'pip-report.raw.json')
            info['kept_in_results'] = False
        row['pip_report'] = info
        codes = [step['exit_code'] for step in row['commands']]
        row['exit_codes'] = codes
        row['detail'] = 'done'
        row['status'] = 'PASS' if len(codes) == 3 and all(code == 0 for code in codes) else 'FAIL'
        self.state['overlay_install_pass'] = row['status'] == 'PASS'

    # ---------------- 3. is the image torch visible; are the nine pins exact ----------------
    def torch_probe(self, row, folder, end, label, out, err, environment):
        first, final = folder / ('torch_probe_' + label + '.spec.json'), folder / ('torch_probe_' + label + '.json')
        step = run_step('torch_probe_' + label, [self.venv_python, '-B', '-c', TORCH_PROBE_CODE, first, final],
                        env=environment, cwd=folder, end=end, stdout=out, stderr=err,
                        tick=lambda: self.progress(row), cap=TORCH_PROBE_CAP_SECONDS)
        row['commands'].append(step)
        result = read_json(final)
        if not isinstance(result, dict):
            result = read_json(first)
        return result if isinstance(result, dict) else None

    def import_smoke(self, row, folder, end):
        target = self.output / 'import_smoke.json'
        document = {'schema': 'cas.probe.import-smoke/1', 'job': JOB, 'venv': str(self.venv),
                    'expected_torch': EXPECTED_TORCH, 'torch_visible_literal_venv': None, 'bridge_applied': False,
                    'all_pins_exact': False, 'required_for_tests': list(REQUIRED_FOR_TESTS),
                    'required_for_tests_importable': False}
        try:
            self.import_smoke_body(row, folder, end, document)
        finally:
            atomic(target, document)
            row.update(output='results/import_smoke.json', output_sha256=sha(target))
            for key in ('torch_visible_literal_venv', 'bridge_applied', 'torch_visible_after_bridge',
                        'all_pins_exact', 'torch_version', 'torch_version_exact', 'torch_importable',
                        'required_for_tests_importable'):
                if key in document:
                    row[key] = document[key]
            self.state.update(torch_visible_literal_venv=document.get('torch_visible_literal_venv'),
                              bridge_applied=document.get('bridge_applied'),
                              all_pins_exact=document.get('all_pins_exact') is True,
                              torch_ok=document.get('torch_importable') is True
                              and document.get('torch_version_exact') is True,
                              required_importable=document.get('required_for_tests_importable') is True)

    def import_smoke_body(self, row, folder, end, document):
        if not os.path.exists(self.venv_python):
            row['status'] = 'NOT_RUN_NO_OVERLAY_PYTHON'
            document['not_run_reason'] = 'NO_OVERLAY_PYTHON'
            return
        environment = self.env(PACKAGE_ENV)
        config = self.venv / 'pyvenv.cfg'
        document['venv_pyvenv_cfg'] = config.read_text(encoding='utf-8', errors='replace') if config.is_file() else None
        with (folder / 'stdout.log').open('ab') as out, (folder / 'stderr.log').open('ab') as err:
            row['detail'] = 'torch_probe_literal'
            literal = self.torch_probe(row, folder, end, 'literal', out, err, environment)
            document['torch_probe_literal_venv'] = literal
            if literal is not None:
                document['torch_visible_literal_venv'] = literal.get('torch_spec_found') is True
                document['torch_import_ok_literal_venv'] = literal.get('torch_imported') is True
                document['sys_path_literal_venv'] = literal.get('sys_path')
            self.progress(row)
            if document['torch_visible_literal_venv'] is False:
                site = self.venv.joinpath(*VENV_SITE_PACKAGES)
                bridge = site / BRIDGE_NAME
                content = IMAGE_SITE_PACKAGES + '\n'
                if site.is_dir() and Path(IMAGE_SITE_PACKAGES).is_dir() and not os.path.lexists(bridge):
                    with bridge.open('x', encoding='utf-8', newline='\n') as stream:
                        stream.write(content)
                    document.update(bridge_applied=True, bridge_file=str(bridge), bridge_content=content,
                                    bridge_bytes=bridge.stat().st_size, bridge_sha256=sha(bridge),
                                    bridge_note='One .pth line adds the image site-packages AFTER the overlay '
                                                'site-packages. This is not part of the package instructions.')
                    row['detail'] = 'torch_probe_bridged'
                    bridged = self.torch_probe(row, folder, end, 'bridged', out, err, environment)
                    document['torch_probe_after_bridge'] = bridged
                    if bridged is not None:
                        document['torch_visible_after_bridge'] = bridged.get('torch_spec_found') is True
                        document['sys_path_after_bridge'] = bridged.get('sys_path')
                else:
                    document['bridge_skipped_reason'] = 'OVERLAY_OR_IMAGE_SITE_PACKAGES_MISSING_OR_BRIDGE_EXISTS'
            elif document['torch_visible_literal_venv'] is None:
                document['bridge_skipped_reason'] = 'LITERAL_PROBE_PRODUCED_NO_RESULT'
            self.progress(row)
            row['detail'] = 'imports'
            imports_path = folder / 'imports.json'
            step = run_step('imports', [self.venv_python, '-B', '-c', IMPORT_CODE, imports_path,
                                        json.dumps([list(pair) for pair in SMOKE_MODULES])],
                            env=environment, cwd=folder, end=end, stdout=out, stderr=err,
                            tick=lambda: self.progress(row))
            row['commands'].append(step)
        imports = read_json(imports_path)
        if not isinstance(imports, dict) or not isinstance(imports.get('modules'), dict):
            row['status'] = 'TIMEOUT' if step['timed_out'] else 'FAILED_RECORDED'
            document['imports'] = None
            return
        modules = imports['modules']
        document.update(imports=modules, basics=imports.get('basics'), sys_path_final=imports.get('sys_path'))
        pins, problems = parse_pins(self.source / 'contracts' / 'requirements.small-linux.txt')
        expected_names = [name for name, unused in PIN_MODULES]
        pins_file_ok = not problems and [name for name, unused in pins] == expected_names
        import_names = dict(PIN_MODULES)
        overlay_prefix = str(self.venv) + os.sep
        table = []
        for name, pinned in pins:
            module = modules.get(import_names.get(name, name)) or {}
            table.append({'distribution': name, 'module': import_names.get(name), 'pinned': pinned,
                          'installed': module.get('metadata_version'),
                          'exact': module.get('metadata_version') == pinned,
                          'imported': module.get('imported') is True, 'file': module.get('file'),
                          'file_in_overlay': isinstance(module.get('file'), str)
                          and module['file'].startswith(overlay_prefix)})
        torch_row = modules.get('torch') or {}
        basics = imports.get('basics') or {}
        torch_version = basics.get('torch_version') or torch_row.get('module_version')
        document.update(
            pins_file_ok=pins_file_ok, pins_file_problems=problems, pins_parsed_count=len(pins), pin_table=table,
            all_pins_exact=pins_file_ok and len(table) == len(PIN_MODULES) and all(item['exact'] for item in table),
            all_pinned_imports_ok=bool(table) and all(item['imported'] for item in table),
            torch_importable=torch_row.get('imported') is True, torch_version=torch_version,
            torch_version_exact=torch_version == EXPECTED_TORCH, torch_file=torch_row.get('file'),
            torch_cuda_is_available=basics.get('torch_cuda_is_available'),
            required_for_tests_importable=all((modules.get(name) or {}).get('imported') is True
                                              for name in REQUIRED_FOR_TESTS),
            import_failures=sorted(name for name, item in modules.items() if item.get('imported') is not True))
        passed = (document['all_pins_exact'] and document['torch_importable'] and document['torch_version_exact']
                  and document['required_for_tests_importable'])
        row['detail'] = 'done'
        row['status'] = 'PASS' if passed else 'FINDINGS'

    # ---------------- 4. the runner's self-test, once, tokenizer only ----------------
    def selftest(self, row, folder, end):
        row.update(selftest_status=None, selftest_mode=None, selftest_json_present=False, selftest_json_sha256=None,
                   prompt_list_sha256=None, padding_plan_sha256=None, bound_hashes_match_files=False,
                   selftest_started=False)
        if not self.state.get('required_importable'):
            row.update(status='NOT_RUN_DEPENDENCIES_UNAVAILABLE',
                       reason='import smoke did not show transformers, tokenizers, numpy and torch importable')
            return
        model = self.root.joinpath(*MODEL_SNAPSHOT.split('/'))
        row['model_files_present'] = sorted(path.name for path in model.iterdir()) if model.is_dir() else None
        # No weights may be on this host: the pre-check must not be able to call model B.
        row['model_weights_absent'] = not (model / 'model.safetensors').exists()
        if not model.is_dir() or not row['model_weights_absent']:
            row.update(status='FAIL', reason='TOKENIZER_FOLDER_MISSING_OR_WEIGHTS_PRESENT')
            return
        temporary, out_dir = folder / 'tmp', folder / 'run_b1'
        temporary.mkdir()
        # The runner creates its one new output folder itself (file rule 1). It is inside results/, so it is returned.
        places = {'{PACKAGE}': str(self.source), '{MODEL}': str(model), '{OUTPUT}': str(out_dir)}
        argv = [self.venv_python, '-B', self.source / 'job' / 'runner_b1.py'] + [places.get(item, item)
                                                                                for item in SELFTEST_ARGV]
        environment = self.env(dict(PACKAGE_ENV, TMPDIR=str(temporary)))
        with (folder / 'stdout.log').open('ab') as out, (folder / 'stderr.log').open('ab') as err:
            step = run_step('selftest', argv, env=environment, cwd=folder, end=end, stdout=out, stderr=err,
                            tick=lambda: self.progress(row))
        row['commands'].append(step)
        row['exit_code'] = step['exit_code']
        # True once the runner process was really started. Plan section 19.1 asks whether the self-test ever started.
        row['selftest_started'] = 'pid' in step
        result_path = out_dir / 'selftest.json'
        document = read_json(result_path)
        row['selftest_json_present'] = isinstance(document, dict)
        files = {}
        for name in ('prompt_hashes.jsonl', 'padding_plan.json'):
            path = out_dir / name
            files[name] = sha(path) if path.is_file() and not path.is_symlink() else None
        row['output_file_sha256'] = files
        if isinstance(document, dict):
            checks = document.get('checks') if isinstance(document.get('checks'), list) else []
            row.update(selftest_status=document.get('status'), selftest_mode=document.get('mode'),
                       selftest_json_sha256=sha(result_path), selftest_json_bytes=result_path.stat().st_size,
                       prompt_list_sha256=document.get('prompt_list_sha256'),
                       padding_plan_sha256=document.get('padding_plan_sha256'),
                       planned_calls=document.get('planned_calls'),
                       score_time_limit_seconds=document.get('score_time_limit_seconds'),
                       slowest_analysis_seconds_text=document.get('slowest_analysis_seconds_text'),
                       checks=[{'name': item.get('name'), 'passed': item.get('passed')} for item in checks
                               if isinstance(item, dict)],
                       made_up_sets=document.get('made_up_sets'))
            # FILE_FORMATS.md 17.1: the two bound values are the sha256 of the bytes of these two files.
            row['bound_hashes_match_files'] = (
                isinstance(files['prompt_hashes.jsonl'], str) and isinstance(files['padding_plan.json'], str)
                and document.get('prompt_list_sha256') == files['prompt_hashes.jsonl']
                and document.get('padding_plan_sha256') == files['padding_plan.json'])
        passed = (step['exit_code'] == 0 and isinstance(document, dict) and document.get('status') == SELFTEST_PASS
                  and document.get('mode') == 'precheck' and row['bound_hashes_match_files'] is True)
        if step['status'] in ('NOT_RUN_DEADLINE', 'SPAWN_FAILED'):
            row['status'] = step['status']
        elif step['timed_out']:
            row['status'] = 'TIMEOUT'
        elif passed:
            row['status'] = 'PASS'
        else:
            # A stop such as GATE_STOP_SELFTEST or GATE_STOP_PADDING lands here. It is a failure of the pre-check.
            row['status'] = 'FAIL'
        # Scratch is not evidence. List what was left, then remove it so packaging cannot trip on it.
        row['tmp_leftovers'] = list_leftovers(temporary)
        shutil.rmtree(temporary, ignore_errors=True)
        row['tmp_removed'] = not os.path.lexists(temporary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--instance', required=True)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    if os.name != 'posix' or os.environ.get('CAS_HELM_R2_SHARED_ADMITTED') != '1':
        raise RuntimeError('EXTERNAL_AUTHORIZED_AWS_CONTROLLER_REQUIRED')
    if not 0 < args.deadline_epoch - time.time() <= MAXIMUM_WORKLOAD_SECONDS:
        raise RuntimeError('INVALID_LAUNCH_DERIVED_THIRTY_FIVE_MINUTE_DEADLINE')
    root = args.root.resolve()
    output = root / 'results'
    output.mkdir(exist_ok=False)
    receipt = {'job': JOB, 'precheck_kind': PRECHECK_KIND, 'instance': args.instance, 'status': 'RUNNING',
               'deadline_epoch': args.deadline_epoch,
               'scope': 'OPTION_B_PRECHECK_SELFTEST_ONLY_CPU_TOKENIZER_ONLY_NO_MODEL_CALL', 'suites': [],
               'scientific_success_claimed': False, 'global_promotion': False, 'no_automatic_retry': True,
               'receipt_reserve_seconds': RECEIPT_RESERVE_SECONDS,
               'source_archive_sha256': SOURCE_ARCHIVE_SHA256, 'bundle_manifest_sha256': BUNDLE_MANIFEST_SHA256,
               # The same value under the name tools/ob_seal.py reads when a failed pre-check is recorded in a repair line.
               'source_zip_sha256': SOURCE_ARCHIVE_SHA256,
               'stage_limits_seconds': dict(LIMITS), 'supervisor_python': sys.version,
               'supervisor_executable': sys.executable}
    rows = {}

    def progress(row=None):
        if row is not None:
            rows[row['name']] = row
        receipt['suites'] = [rows[name] for name in STAGES if name in rows]
        atomic(output / 'supervisor_receipt.json', receipt)
        atomic(output / 'progress.json', {
            'job': JOB, 'instance': args.instance, 'status': receipt['status'], 'utc': utc(),
            'stages': [{'name': item['name'], 'status': item['status'], 'detail': item.get('detail'),
                        'tests_run': item.get('tests_run'), 'failures': item.get('failures'),
                        'errors': item.get('errors'), 'skipped': item.get('skipped')}
                       for item in receipt['suites']]})

    code = 1
    try:
        progress()
        probe = Probe(root, output, args.deadline_epoch, progress)
        probe.overlay.mkdir(exist_ok=False)
        (probe.overlay / 'home').mkdir()
        (probe.overlay / 'tmp').mkdir()
        probe.stage('opt_pytorch_inventory', probe.inventory)
        probe.stage('overlay_install', probe.overlay_install)
        probe.stage('import_smoke', probe.import_smoke)
        probe.stage('selftest', probe.selftest)
        check = post_run_source_check(root)
        receipt['post_run_source_check'] = check
        conditions = {
            'overlay_install_all_commands_exit_0': rows['overlay_install']['status'] == 'PASS',
            'all_nine_pins_exact': probe.state.get('all_pins_exact') is True,
            'torch_2_9_1_cu130_importable': probe.state.get('torch_ok') is True,
            'selftest_pass_and_bound_hashes_match_files': rows['selftest']['status'] == 'PASS',
            'source_check_clean': check['changed_or_missing_count'] == 0 and check['extra_files_count'] == 0,
        }
        receipt.update(pass_conditions=conditions,
                       torch_visible_literal_venv=probe.state.get('torch_visible_literal_venv'),
                       bridge_applied=probe.state.get('bridge_applied'),
                       all_pins_exact=probe.state.get('all_pins_exact') is True)
        # The five values seal step 7_PRECHECK needs (FILE_FORMATS.md section 15). Only a job on the sealed package
        # returns them under that name. A rehearsal or a test on made-up data is never written to a seal file.
        five = {'source_zip_sha256': SOURCE_ARCHIVE_SHA256,
                'selftest_status': rows['selftest'].get('selftest_status'),
                'prompt_list_sha256': rows['selftest'].get('prompt_list_sha256'),
                'padding_plan_sha256': rows['selftest'].get('padding_plan_sha256'),
                'selftest_json_sha256': rows['selftest'].get('selftest_json_sha256')}
        receipt['seal_step_7_values' if PRECHECK_KIND == 'SEALED_PACKAGE' else 'values_never_for_a_seal_file'] = five
        receipt['status'] = ('PRECHECK_COMPLETE_SELFTEST_PASS' if all(conditions.values())
                             else 'PRECHECK_COMPLETE_WITH_FINDINGS')
        code = 0
    except BaseException as error:
        receipt.update(status='STOPPED_NO_RETRY', error_type=type(error).__name__, reason=str(error)[:2000])
    finally:
        # Plain facts for plan section 19.1 (what may follow a pre-check that does not pass). The supervisor names
        # no case; the run sheet maps these facts to the plan's cases.
        selftest_row = rows.get('selftest') or {}
        package_check = [item.get('passed') for item in (selftest_row.get('checks') or [])
                         if item.get('name') == 'package_matches_seal']
        receipt['after_a_failure_facts'] = {
            'selftest_started': selftest_row.get('selftest_started') is True,
            'selftest_json_present': selftest_row.get('selftest_json_present') is True,
            'selftest_status': selftest_row.get('selftest_status'),
            'check_package_matches_seal': package_check[0] if len(package_check) == 1 else None}
        try:
            receipt['results_symlink_sweep'] = sweep_symlinks(output)
        except Exception as error:
            receipt['results_symlink_sweep'] = {'error': type(error).__name__ + ':' + str(error)[:500]}
        receipt.update(exit_code=code, finished_utc=utc())
        progress()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
