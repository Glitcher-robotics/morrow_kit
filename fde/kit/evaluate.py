import math
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fde.kit import _common as c


def validate_command(command):
    if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
        raise ValueError('command must be a nonempty argv array; use {python}, no shell operators')


def validate(config):
    requirements = config.get('requirements')
    regression = config.get('regression')
    if not isinstance(requirements, list) or not requirements:
        raise ValueError('at least one requirement is required')
    if not isinstance(regression, list) or not regression:
        raise ValueError('at least one regression command is required')
    seen = set()
    for req in requirements:
        if not isinstance(req, dict) or not re.fullmatch(r'REQ-[A-Za-z0-9_-]+', req.get('id', '')):
            raise ValueError('invalid REQ id')
        if req['id'] in seen or req.get('priority') not in {'P0', 'P1', 'P2'}:
            raise ValueError('duplicate id or invalid priority')
        if not isinstance(req.get('acceptance'), str) or not req['acceptance'].strip():
            raise ValueError('acceptance text required')
        seen.add(req['id'])
        validate_command(req.get('command'))
    if not any(x['priority'] == 'P0' for x in requirements):
        raise ValueError('at least one P0 requirement is required')
    for command in regression:
        validate_command(command)


def execute(command, root, timeout):
    command = [sys.executable if x == '{python}' else x for x in command]
    start = time.perf_counter()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    timed_out = False
    # File-backed capture bounds RAM even for a noisy test process.
    import tempfile
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.run(command, cwd=root, stdout=out, stderr=err,
                                  timeout=timeout, env=env, shell=False)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code, timed_out = None, True
        except OSError as exc:
            code = 127
            err.write(str(exc).encode('utf-8'))
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(32768).decode('utf-8', 'replace'), err.read(32768).decode('utf-8', 'replace')
    return {'command': command, 'pass': code == 0 and not timed_out, 'returncode': code,
            'timeout': timed_out, 'runtime': round(time.perf_counter() - start, 6),
            'stdout': stdout, 'stderr': stderr, 'log_limit_bytes': 32768}


def run(root, timeout=60):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be positive and finite')
    root = Path(root).resolve()
    work = root / 'fde/work'
    config = c.read_json(work / 'checks.json')
    validate(config)
    if (work / 'champion.json').exists():
        raise ValueError('champion.json is reserved for promotion metadata')
    before = c.manifest(work)
    inputs = c.task_manifest(root)
    start = time.perf_counter()
    results = [dict(execute(req['command'], root, timeout), id=req['id'],
                    priority=req['priority'], acceptance=req['acceptance'])
               for req in config['requirements']]
    regression = [execute(command, root, timeout) for command in config['regression']]
    stable = before == c.manifest(work) and inputs == c.task_manifest(root)
    passed = sum(x['pass'] for x in results)
    report = {'schema_version': 1, 'created_at': c.now(), 'requirements': results,
              'regression': regression, 'coverage': passed / len(results),
              'score': round(100 * passed / len(results), 6),
              'p0_pass': all(x['pass'] for x in results if x['priority'] == 'P0'),
              'regression_pass': all(x['pass'] for x in regression),
              'source_stable': stable, 'work_manifest': before, 'task_manifest': inputs,
              'runtime': round(time.perf_counter() - start, 6),
              'error_count': sum(not x['pass'] for x in results + regression)}
    report['pass'] = passed == len(results) and report['regression_pass'] and stable
    path = root / 'fde/artifacts' / ('eval_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ_') + uuid.uuid4().hex[:8] + '.json')
    report['report_path'] = str(path)
    c.write_json(path, report)
    return report


if __name__ == '__main__':
    p = c.parser('Run REQ and regression commands and save execution evidence.')
    p.add_argument('--timeout', type=float, default=60)
    a = p.parse_args()
    holder = {}
    code = c.cli(lambda: holder.setdefault('report', run(a.root, a.timeout)))
    sys.exit(code or (0 if holder['report']['pass'] else 1))
