"""Shared stdlib plumbing; no shell evaluation and no network calls."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}
SECRET_NAMES = {'.env', 'id_rsa', 'id_ed25519', 'credentials.json'}
STAGES = ['DISCOVERY', 'CONTRACT', 'SCAFFOLD', 'E2E_V0', 'VERIFY', 'ACCEPT', 'SUBMIT']


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                     dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def is_secret(path):
    return path.name in SECRET_NAMES or path.name.startswith('.env.') or path.suffix.lower() in {'.pem', '.key'}


def files_under(base, strict=True):
    base = Path(base)
    if not base.exists():
        return []
    result = []
    for path in sorted(base.rglob('*')):
        rel = path.relative_to(base)
        if any(part in SKIP_DIRS for part in rel.parts) or path.name == '.gitkeep':
            continue
        if path.is_symlink():
            raise ValueError('symbolic links are not supported: ' + str(rel))
        if not path.is_file() or path.suffix in {'.pyc', '.pyo'}:
            continue
        if is_secret(path):
            if strict:
                raise ValueError('secret-like filename in candidate: ' + str(rel))
            continue
        result.append(path)
    return result


def manifest(base, exclude=()):
    base = Path(base)
    return {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files_under(base) if p.relative_to(base).as_posix() not in exclude}


def task_manifest(root):
    root = Path(root)
    result = {}
    for path in files_under(root, strict=False):
        rel = path.relative_to(root)
        if len(rel.parts) > 1 and rel.parts[0] == 'fde' and rel.parts[1] in {'work', 'champion', 'artifacts'}:
            continue
        result[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def copy_candidate(source, destination):
    source, destination = Path(source), Path(destination)
    for path in files_under(source):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def remove_tree(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError('refusing to remove path outside task root')
    if path.exists():
        shutil.rmtree(path)


@contextlib.contextmanager
def promotion_lock(root):
    path = Path(root) / 'fde/artifacts/.promotion.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError('promotion already running; inspect .promotion.lock if a crash occurred') from exc
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    return p


def cli(action):
    try:
        value = action()
        print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2
