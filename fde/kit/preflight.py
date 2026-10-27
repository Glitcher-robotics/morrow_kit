import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fde.kit import _common as c


def version(command):
    try:
        result = subprocess.run([command, '--version'], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def inspect(root, port=8000):
    root = Path(root).resolve()
    writable = False
    try:
        with tempfile.TemporaryFile(dir=root):
            writable = True
    except OSError:
        pass
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
            available = True
        except OSError:
            available = False
    return {'python': sys.version.split()[0], 'python_executable': sys.executable,
            'python_ok': sys.version_info >= (3, 10), 'git': version('git'),
            'node': version('node'), 'writable': writable, 'port': port,
            'port_available': available, 'offline': True}


if __name__ == '__main__':
    p = c.parser('Check runtime, write permission and localhost port; git/node are optional.')
    p.add_argument('--port', type=int, default=8000)
    a = p.parse_args()
    result = inspect(a.root, a.port)
    print(__import__('json').dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['python_ok'] and result['writable'] and result['port_available'] else 1)
