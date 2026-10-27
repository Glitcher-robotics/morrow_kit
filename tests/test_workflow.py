"""Project-independent install, preservation and fresh-process workflow checks."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def call(self, project, script, *args, expected=0):
        result = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=project,
                                capture_output=True, text=True, encoding='utf-8', timeout=30,
                                env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def setup_project(self, base):
        project = Path(base) / 'project'
        project.mkdir()
        (project / 'README.md').write_bytes(b'project instructions\r\n')
        (project / 'AGENTS.md').write_bytes(b'project rules\n')
        (project / 'src').mkdir()
        (project / 'src/keep.py').write_bytes(b'VALUE = 42\n')
        self.call(project, ROOT / 'install.py', '--target', project)
        self.call(project, project / 'fde/kit/init_work.py')
        return project

    def test_install_reinstall_preserves_original_and_filled_templates(self):
        with tempfile.TemporaryDirectory() as base:
            project = self.setup_project(base)
            work = project / 'fde/work'
            for name in ['interview', 'problem', 'requirements', 'skeleton', 'decisions', 'state', 'handoff']:
                self.assertTrue((work / (name + '.md')).is_file(), name)
            (work / 'interview.md').write_bytes('실제 받은 답\r\n'.encode())
            (work / 'problem.md').write_bytes('사람이 합의한 범위\r\n'.encode())
            before = {name: (work / name).read_bytes() for name in ['interview.md', 'problem.md']}
            self.call(project, ROOT / 'install.py', '--target', project, '--refresh-agents')
            self.call(project, project / 'fde/kit/init_work.py')
            for name, content in before.items():
                self.assertEqual((work / name).read_bytes(), content)
            self.assertEqual((project / 'README.md').read_bytes(), b'project instructions\r\n')
            self.assertEqual((project / 'src/keep.py').read_bytes(), b'VALUE = 42\n')
            rules = (project / 'AGENTS.md').read_text(encoding='utf-8')
            self.assertTrue(rules.startswith('project rules\n'))
            self.assertEqual(rules.count('<!-- FDE:BEGIN -->'), 1)
            for doc in (ROOT / 'docs').glob('*.md'):
                self.assertEqual((project / 'fde/docs' / doc.name).read_bytes(), doc.read_bytes())

    def test_cli_evaluate_bundle_fresh_run_and_failed_promotion(self):
        with tempfile.TemporaryDirectory() as base:
            project = self.setup_project(base)
            work = project / 'fde/work'
            (work / 'component.py').write_text('def total(values):\n    return sum(values)\n', encoding='utf-8')
            tests = work / 'tests'
            tests.mkdir()
            (tests / 'test_component.py').write_text(
                'from pathlib import Path\nimport sys,unittest\n'
                'sys.path.insert(0,str(Path(__file__).resolve().parents[1]))\n'
                'from component import total\n'
                'class ContractTests(unittest.TestCase):\n'
                '    def test_positive(self): self.assertEqual(total([1,2]),3)\n'
                '    def test_empty(self): self.assertEqual(total([]),0)\n'
                'if __name__=="__main__": unittest.main()\n', encoding='utf-8')
            command = ['{python}', 'fde/work/tests/test_component.py']
            checks = {'requirements': [{'id': 'REQ-001', 'priority': 'P0',
                                       'acceptance': 'fixed values total equals three',
                                       'command': command + ['ContractTests.test_positive', '-v']}],
                      'regression': [command + ['ContractTests.test_empty', '-v']]}
            (work / 'checks.json').write_text(json.dumps(checks), encoding='utf-8')
            report = json.loads(self.call(project, project / 'fde/kit/evaluate.py').stdout)
            self.assertTrue(report['pass'])
            self.call(project, project / 'fde/kit/promote.py', '--report', 'latest')
            first = json.loads(self.call(project, project / 'fde/kit/bundle.py').stdout)
            second = json.loads(self.call(project, project / 'fde/kit/bundle.py').stdout)
            self.assertEqual(first['sha256'], second['sha256'])
            fresh = Path(base) / 'fresh'
            fresh.mkdir()
            with zipfile.ZipFile(first['path']) as archive:
                archive.extractall(fresh)
            # The extracted candidate must run without the toolkit or original project.
            self.call(fresh, fresh / 'tests/test_component.py', '-v')
            champion = project / 'fde/champion/component.py'
            before = hashlib.sha256(champion.read_bytes()).hexdigest()
            (work / 'component.py').write_text('def total(values):\n    return 0\n', encoding='utf-8')
            failed = json.loads(self.call(project, project / 'fde/kit/evaluate.py', expected=1).stdout)
            self.assertFalse(failed['pass'])
            self.call(project, project / 'fde/kit/promote.py', '--report', 'latest', expected=2)
            self.assertEqual(hashlib.sha256(champion.read_bytes()).hexdigest(), before)

    def test_local_markdown_links_stay_in_package_and_exist(self):
        documents = [*ROOT.glob('*.md'), *(ROOT / 'docs').glob('*.md')]
        for document in documents:
            for link in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):
                    continue
                target = (document.parent / link.split('#')[0]).resolve()
                self.assertTrue(target.is_relative_to(ROOT), (document.name, link))
                self.assertTrue(target.exists(), (document.name, link))


if __name__ == '__main__':
    unittest.main()
