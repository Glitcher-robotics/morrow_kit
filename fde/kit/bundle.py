import hashlib
import io
from pathlib import Path
import sys
import zipfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fde.kit import _common as c


def make_bundle(root):
    root = Path(root).resolve()
    champion = root / 'fde/champion'
    metadata = c.read_json(champion / 'champion.json')
    actual = c.manifest(champion, exclude={'champion.json'})
    if actual != metadata['work_manifest']:
        raise ValueError('champion was edited after promotion')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(actual):
            if name == 'session.json':
                continue
            content = (champion / name).read_bytes()
            if hashlib.sha256(content).hexdigest() != actual[name]:
                raise ValueError('champion changed during bundling')
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, content)
    raw = buffer.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    output = root / 'fde/artifacts' / ('submission_' + digest[:16] + '.zip')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n', encoding='ascii')
    return {'path': str(output), 'sha256': digest, 'files': len(actual) - int('session.json' in actual)}


if __name__ == '__main__':
    p = c.parser('Create deterministic ZIP_STORED submission and SHA256 from champion.')
    a = p.parse_args()
    sys.exit(c.cli(lambda: make_bundle(a.root)))
