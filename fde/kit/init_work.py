from pathlib import Path
import shutil
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fde.kit import _common as c


def initialize(root):
    root = Path(root).resolve()
    work = root / 'fde/work'
    work.mkdir(parents=True, exist_ok=True)
    created = []
    templates = root / 'fde/templates'
    if not templates.exists():
        templates = Path(__file__).resolve().parents[1] / 'templates'
    for source in sorted(templates.glob('*.md')):
        target = work / source.name
        if not target.exists():
            shutil.copyfile(source, target)
            created.append(target.name)
    for name, value in [
        ('session.json', {'started_at': c.now()}),
        ('checks.json', {'requirements': [], 'regression': []}),
    ]:
        if not (work / name).exists():
            c.write_json(work / name, value)
            created.append(name)
    for directory in ['champion', 'artifacts']:
        (root / 'fde' / directory).mkdir(exist_ok=True)
    return {'created': created, 'work': str(work)}


if __name__ == '__main__':
    p = c.parser('Create missing work templates; never overwrite an existing file.')
    a = p.parse_args()
    sys.exit(c.cli(lambda: initialize(a.root)))
