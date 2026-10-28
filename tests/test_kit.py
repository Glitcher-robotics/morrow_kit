import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from fde.kit import _common as c
from fde.kit import bundle, evaluate, init_work, preflight, promote, status


def installer():
    spec = importlib.util.spec_from_file_location('installer', REPO / 'install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'fde/work').mkdir(parents=True)
        (self.root / 'README.md').write_bytes(b'task README\r\n')

    def tearDown(self):
        self.tmp.cleanup()

    def checks(self, fail=False):
        work = self.root / 'fde/work'
        (work / 'solution.py').write_text('print("hello")\n', encoding='utf-8')
        script = 'import sys; sys.exit(1)' if fail else 'print("ok")'
        config = {'requirements': [{'id': 'REQ-001', 'priority': 'P0',
                   'acceptance': 'smoke', 'command': ['{python}', '-c', script]}],
                  'regression': [['{python}', '-c', 'print("regression")']]}
        c.write_json(work / 'checks.json', config)


class InstallTests(Sandbox):
    def test_reinstall_preserves_readme_work_and_single_block(self):
        before = (self.root / 'README.md').read_bytes()
        (self.root / 'AGENTS.md').write_text('existing\n', encoding='utf-8')
        installer().install(self.root)
        init_work.initialize(self.root)
        task = self.root / 'fde/work/problem.md'
        task.write_text('keep my work', encoding='utf-8')
        installer().install(self.root)
        self.assertEqual(before, (self.root / 'README.md').read_bytes())
        self.assertEqual(task.read_text(encoding='utf-8'), 'keep my work')
        agents = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertEqual(agents.count('<!-- FDE:BEGIN -->'), 1)
        self.assertTrue(agents.startswith('existing\n'))
        self.assertTrue((self.root / 'fde/docs/QUICKCARD.md').is_file())


    def test_refresh_agents_preserves_user_text_and_backs_up_old_block(self):
        old = b'prefix\r\n<!-- FDE:BEGIN -->\nold rules\n<!-- FDE:END -->\r\nsuffix\n'
        agents = self.root / 'AGENTS.md'
        agents.write_bytes(old)
        installer().install(self.root)
        self.assertEqual(agents.read_bytes(), old)
        result = installer().install(self.root, refresh_agents=True)
        self.assertTrue(result['agents_refreshed'])
        updated = agents.read_bytes()
        self.assertTrue(updated.startswith(b'prefix\r\n'))
        self.assertTrue(updated.endswith(b'\r\nsuffix\n'))
        self.assertNotIn(b'old rules', updated)
        backups = list((self.root / 'fde/artifacts').glob('AGENTS-before-refresh-*.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), old)
        self.assertFalse(installer().install(self.root, refresh_agents=True)['agents_refreshed'])

    def test_malformed_markers_rejected_without_modifying_agents(self):
        for old in [b'<!-- FDE:END --><!-- FDE:BEGIN -->', b'<!-- FDE:BEGIN -->']:
            agents = self.root / 'AGENTS.md'
            agents.write_bytes(old)
            with self.assertRaises(ValueError):
                installer().install(self.root, refresh_agents=True)
            self.assertEqual(agents.read_bytes(), old)


class EvaluationTests(Sandbox):
    def test_empty_requirements_rejected(self):
        c.write_json(self.root / 'fde/work/checks.json', {'requirements': [], 'regression': []})
        with self.assertRaises(ValueError):
            evaluate.run(self.root)

    def test_evidence_pass_fail_and_source_manifest(self):
        self.checks()
        report = evaluate.run(self.root)
        self.assertTrue(report['pass'])
        self.assertEqual(report['coverage'], 1.0)
        self.assertEqual(report['score'], 100.0)
        self.assertIn('work_manifest', report)
        self.checks(fail=True)
        report = evaluate.run(self.root)
        self.assertFalse(report['pass'])
        self.assertEqual(report['error_count'], 1)

    def test_timeout_records_failure(self):
        self.checks()
        cfg = c.read_json(self.root / 'fde/work/checks.json')
        cfg['requirements'][0]['command'] = ['{python}', '-c', 'import time; time.sleep(5)']
        c.write_json(self.root / 'fde/work/checks.json', cfg)
        report = evaluate.run(self.root, timeout=0.1)
        self.assertFalse(report['pass'])
        self.assertTrue(report['requirements'][0]['timeout'])

    def test_invalid_priority_or_missing_regression_rejected(self):
        self.checks()
        cfg = c.read_json(self.root / 'fde/work/checks.json')
        cfg['requirements'][0]['priority'] = 'P9'
        c.write_json(self.root / 'fde/work/checks.json', cfg)
        with self.assertRaises(ValueError):
            evaluate.run(self.root)
        self.checks()
        cfg = c.read_json(self.root / 'fde/work/checks.json')
        cfg['regression'] = []
        c.write_json(self.root / 'fde/work/checks.json', cfg)
        with self.assertRaises(ValueError):
            evaluate.run(self.root)


class PromotionTests(Sandbox):
    def test_pass_then_failed_promotion_preserves_champion(self):
        self.checks()
        report = evaluate.run(self.root)
        promote.promote(self.root, Path(report['report_path']))
        before = c.manifest(self.root / 'fde/champion')
        self.checks(fail=True)
        failed = evaluate.run(self.root)
        with self.assertRaises(ValueError):
            promote.promote(self.root, Path(failed['report_path']))
        self.assertEqual(before, c.manifest(self.root / 'fde/champion'))

    def test_changed_source_or_task_invalidates_evidence(self):
        self.checks()
        report = evaluate.run(self.root)
        (self.root / 'fde/work/solution.py').write_text('print("changed")', encoding='utf-8')
        with self.assertRaises(ValueError):
            promote.promote(self.root, Path(report['report_path']))
        self.checks()
        report = evaluate.run(self.root)
        (self.root / 'README.md').write_text('changed input contract', encoding='utf-8')
        with self.assertRaises(ValueError):
            promote.promote(self.root, Path(report['report_path']))


class BundleTests(Sandbox):
    def test_same_bytes_same_hash(self):
        self.checks()
        report = evaluate.run(self.root)
        promote.promote(self.root, Path(report['report_path']))
        first = bundle.make_bundle(self.root)
        second = bundle.make_bundle(self.root)
        self.assertEqual(first['sha256'], second['sha256'])
        import zipfile
        with zipfile.ZipFile(first['path']) as archive:
            self.assertIn('solution.py', archive.namelist())
            self.assertNotIn('champion.json', archive.namelist())

    def test_secret_in_candidate_rejected(self):
        self.checks()
        (self.root / 'fde/work/.env').write_text('SECRET=demo', encoding='utf-8')
        with self.assertRaises(ValueError):
            evaluate.run(self.root)


class UtilityTests(Sandbox):
    def test_init_never_overwrites(self):
        shutil.copytree(REPO / 'fde/templates', self.root / 'fde/templates')
        init_work.initialize(self.root)
        p = self.root / 'fde/work/state.md'
        p.write_text('mine', encoding='utf-8')
        init_work.initialize(self.root)
        self.assertEqual(p.read_text(encoding='utf-8'), 'mine')

    def test_status_time_policy(self):
        c.write_json(self.root / 'fde/work/session.json', {'started_at': '2026-01-01T00:00:00+00:00'})
        result = status.snapshot(self.root, elapsed=180)
        self.assertIn('새 기능 금지', ' '.join(result['warnings']))
        self.assertIn('구조 변경 금지', ' '.join(result['warnings']))
        self.assertEqual(result['stage'], 'DISCOVERY')

    def test_intent_reports_gaps_on_empty_templates(self):
        init_work.initialize(self.root)
        result = status.intent(self.root)
        self.assertEqual(result['decisions'], 0)
        self.assertEqual(result['problem_filled'], 0)
        self.assertFalse(any(result['gates'].values()))
        self.assertIn('decisions에 값이 있는 D 없음', result['gaps'])

    def test_intent_counts_linked_records(self):
        if shutil.which('git') is None:
            self.skipTest('git not installed')
        init_work.initialize(self.root)
        work = self.root / 'fde/work'
        (work / 'problem.md').write_text('\n'.join(f'{x}: 값' for x in status.PROBLEM_LABELS), encoding='utf-8')
        (work / 'decisions.md').write_text(
            '| D-ID | 상태 | 결정 | 근거 | REQ | 위치 |\n|---|---|---|---|---|---|\n'
            '| D1 | 확인 | 6회 연속 → 주의 | Q-001 | REQ-001 | config.trend |\n'
            '| D2 | 대체됨→D3 | 전 필드 동일 | Q-002 | REQ-002 | |\n'
            '| D3 | 확인 | 같은 meas_id | Q-003 | REQ-002 | dedupe |\n| D4 | | | | | |\n', encoding='utf-8')
        (work / 'requirements.md').write_text('| REQ-001 | 추세 (D1) | P0 |\n| REQ-002 | 중복 | P0 |\n', encoding='utf-8')
        (work / 'state.md').write_text('STATE: VERIFY\n마지막 commit: REQ-001\nGATE1 합의: 10:20 승인\nGATE2 E2E v0:\n',
                                       encoding='utf-8')
        git = ['git', '-C', str(self.root), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
        subprocess.run(git[:3] + ['init', '-q'], check=True)
        for message in ['init: 과제 원본', 'REQ-001: METHOD ④ 추세 (D1)']:
            subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', message], check=True)
        result = status.intent(self.root)
        self.assertEqual(result['git'], {'commits': 2, 'req_commits': 1, 'first': 'init: 과제 원본'})
        self.assertEqual(result['problem_filled'], 7)
        self.assertEqual(result['decisions'], 3)
        self.assertEqual(result['decision_status'], {'확인': 2, '대체됨': 1})
        self.assertEqual((result['requirements'], result['requirements_citing_d']), (2, 1))
        self.assertEqual(result['gates'], {'GATE1': True, 'GATE2': False, 'GATE3': False, 'GATE4': False})
        self.assertIn('D 근거 없는 REQ 1개', result['gaps'])

    def test_example_session_warning_boundaries(self):
        for minute, token in [(80, '구조 변경 금지'), (140, '새 기능 금지'), (170, '저장·제출 확인만'), (180, '180분 작업 시간 초과')]:
            before = status.snapshot(self.root, elapsed=minute - 0.01)
            after = status.snapshot(self.root, elapsed=minute)
            self.assertNotIn(token, before['warnings'])
            self.assertIn(token, after['warnings'])
        self.assertEqual(status.snapshot(self.root, elapsed=181)['remaining_task_minutes'], 0)
        self.assertEqual(status.snapshot(self.root, elapsed=0)['task_limit_minutes'], 180)

    def test_preflight_port_bind(self):
        before = sorted(x.name for x in self.root.iterdir())
        result = preflight.inspect(self.root, port=0)
        self.assertTrue(result['python_ok'])
        self.assertTrue(result['writable'])
        self.assertTrue(result['port_available'])
        self.assertEqual(before, sorted(x.name for x in self.root.iterdir()))


if __name__ == '__main__':
    unittest.main()
