"""Install fde/ and a managed AGENTS block; optionally back up and refresh it. Preserve task README."""
import argparse
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parent
BEGIN, END = b'<!-- FDE:BEGIN -->', b'<!-- FDE:END -->'
# 과제 폴더가 홈(~)일 때 git add -A가 셸 설정·Codex 로그인 정보까지 담지 않게 막는다.
IGNORE = ['.codex/', '.config/', '.cache/', '.npm/', '.local/', '.ssh/', '.gnupg/', '.vscode-server/',
          '.bash_history', '.bash_logout', '.bashrc', '.profile', '.sudo_as_admin_successful',
          '.python_history', '.lesshst', '.viminfo', '.wget-hsts', '.git-credentials', '.netrc',
          '.env', 'node_modules/', '__pycache__/', '*.pyc']


def ensure_gitignore(target):
    """Append missing IGNORE lines to target/.gitignore; never remove existing lines."""
    path = Path(target).resolve() / '.gitignore'
    if path.is_symlink():
        raise ValueError('.gitignore must not be a symbolic link')
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    present = {line.strip() for line in text.splitlines()}
    missing = [line for line in IGNORE if line not in present]
    if missing:
        head = '' if not text or text.endswith('\n') else '\n'
        path.write_text(text + head + '# morrow_kit: 홈 폴더 설정·비밀 제외\n' + '\n'.join(missing) + '\n',
                        encoding='utf-8')
    return missing


def install(target, refresh_agents=False):
    target = Path(target).resolve()
    if not target.is_dir() or target == SOURCE:
        raise ValueError('target must be an existing task folder different from this source repo')
    agents = target / 'AGENTS.md'
    if agents.is_symlink():
        raise ValueError('AGENTS.md must not be a symbolic link')
    original = agents.read_bytes() if agents.exists() else b''
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('malformed/duplicate FDE markers; review AGENTS.md manually')
    if BEGIN in original and original.index(BEGIN) > original.index(END):
        raise ValueError('reversed FDE markers; review AGENTS.md manually')
    destination = target / 'fde'
    if destination.is_symlink():
        raise ValueError('fde must not be a symbolic link')
    if destination.exists():
        for path in destination.rglob('*'):
            if path.is_symlink():
                raise ValueError('existing fde tree contains symbolic link: ' + str(path))
    copied = 0
    for source in sorted((SOURCE / 'fde').rglob('*')):
        rel = source.relative_to(SOURCE / 'fde')
        if any(part in {'work', 'champion', 'artifacts', '__pycache__'} for part in rel.parts):
            continue
        if source.is_symlink():
            raise ValueError('source contains symbolic link')
        if source.is_file() and source.suffix not in {'.pyc', '.pyo'}:
            output = destination / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
            copied += 1
    for source in sorted((SOURCE / 'docs').glob('*.md')):
        output = destination / 'docs' / source.name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        copied += 1
    for folder in ['work', 'champion', 'artifacts']:
        (destination / folder).mkdir(parents=True, exist_ok=True)
    block = (SOURCE / 'fde/AGENTS_BLOCK.md').read_bytes().rstrip()
    managed = BEGIN + b'\n' + block + b'\n' + END
    agents_updated = False
    if BEGIN in original and refresh_agents:
        start, end = original.index(BEGIN), original.index(END) + len(END)
        updated = original[:start] + managed + original[end:]
        if updated != original:
            import hashlib
            backup = destination / 'artifacts' / ('AGENTS-before-refresh-' + hashlib.sha256(original).hexdigest() + '.md')
            if backup.exists() and backup.read_bytes() != original:
                raise ValueError('AGENTS backup conflict')
            backup.write_bytes(original)
            agents.write_bytes(updated)
            agents_updated = True
    elif BEGIN not in original:
        agents.write_bytes(original + (b'\n' if original and not original.endswith(b'\n') else b'')
                           + BEGIN + b'\n' + block + b'\n' + END + b'\n')
    ignored = ensure_gitignore(target)
    return {'agents_refreshed': agents_updated, 'target': str(target), 'copied': copied, 'readme_modified': False,
            'gitignore_added': len(ignored),
            'note': 'work/champion/artifacts preserved; static tools/docs refreshed; existing work templates unchanged; use --refresh-agents to back up and update the managed block'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, type=Path)
    parser.add_argument('--refresh-agents', action='store_true', help='Back up AGENTS.md and replace only its marked FDE block; preserve work files.')
    parser.add_argument('--gitignore-only', action='store_true',
                        help='Only add home/secret ignore lines to .gitignore (run before the init commit).')
    args = parser.parse_args()
    try:
        import json
        if args.gitignore_only:
            if not Path(args.target).is_dir():
                raise ValueError('target must be an existing folder')
            print(json.dumps({'gitignore_added': ensure_gitignore(args.target)}, ensure_ascii=False, indent=2))
            sys.exit(0)
        print(json.dumps(install(args.target, refresh_agents=args.refresh_agents), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
