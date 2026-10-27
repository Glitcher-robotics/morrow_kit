import unittest
from unittest import mock
from pathlib import Path
from test_kit import Sandbox
from fde.kit import _common as c, evaluate, promote


class PromotionEdgeTests(Sandbox):
    def test_imported_helper_change_invalidates_evidence(self):
        self.checks()
        (self.root / 'fde/helper.py').write_text('VALUE=1', encoding='utf-8')
        report = evaluate.run(self.root)
        (self.root / 'fde/helper.py').write_text('VALUE=99', encoding='utf-8')
        with self.assertRaises(ValueError):
            promote.promote(self.root, report['report_path'])

    def test_reserved_metadata_name_rejected_before_evaluation(self):
        self.checks()
        (self.root / 'fde/work/champion.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            evaluate.run(self.root)

    def test_rollback_failure_keeps_last_good_backup(self):
        self.checks()
        report = evaluate.run(self.root)
        promote.promote(self.root, report['report_path'])
        before = c.manifest(self.root / 'fde/champion')
        original = Path.rename

        def locked(path, target):
            if path.name.startswith(('.promote-', '.backup-')):
                raise PermissionError('simulated rename lock')
            return original(path, target)

        with mock.patch.object(Path, 'rename', locked), self.assertRaises(PermissionError):
            promote.promote(self.root, report['report_path'])
        backups = list((self.root / 'fde/artifacts').glob('.backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(before, c.manifest(backups[0]))

    def test_failed_history_write_restores_active_champion(self):
        self.checks()
        report = evaluate.run(self.root)
        promote.promote(self.root, report['report_path'])
        before = c.manifest(self.root / 'fde/champion')
        original = c.write_json

        def disk_error(path, value):
            if Path(path).name == 'promotion_history.json':
                raise OSError('simulated full disk')
            return original(path, value)

        with mock.patch.object(c, 'write_json', disk_error), self.assertRaises(OSError):
            promote.promote(self.root, report['report_path'])
        self.assertEqual(before, c.manifest(self.root / 'fde/champion'))

    def test_regression_failure_rejected(self):
        self.checks()
        cfg = c.read_json(self.root / 'fde/work/checks.json')
        cfg['regression'] = [['{python}', '-c', 'raise SystemExit(1)']]
        c.write_json(self.root / 'fde/work/checks.json', cfg)
        report = evaluate.run(self.root)
        self.assertTrue(report['p0_pass'])
        with self.assertRaises(ValueError):
            promote.promote(self.root, report['report_path'])

    def test_lower_optional_score_does_not_replace_champion(self):
        self.checks()
        path = self.root / 'fde/work/checks.json'
        cfg = c.read_json(path)
        cfg['requirements'].append({'id':'REQ-002','priority':'P1','acceptance':'optional',
                                    'command':['{python}','-c','print("ok")']})
        c.write_json(path, cfg)
        report = evaluate.run(self.root)
        promote.promote(self.root, report['report_path'])
        before = c.manifest(self.root / 'fde/champion')
        cfg['requirements'][1]['command'] = ['{python}','-c','raise SystemExit(1)']
        c.write_json(path, cfg)
        failed = evaluate.run(self.root)
        self.assertTrue(failed['p0_pass'])
        self.assertEqual(failed['score'], 50)
        with self.assertRaises(ValueError):
            promote.promote(self.root, failed['report_path'])
        self.assertEqual(before, c.manifest(self.root / 'fde/champion'))

class BundleMetadataPathTests(Sandbox):
    def test_nested_metadata_name_remains_a_normal_file(self):
        from fde.kit import bundle
        import zipfile
        self.checks()
        path = self.root / 'fde/work/config/champion.json'
        path.parent.mkdir()
        path.write_text('{"ordinary":true}', encoding='utf-8')
        report = evaluate.run(self.root)
        promote.promote(self.root, report['report_path'])
        result = bundle.make_bundle(self.root)
        with zipfile.ZipFile(result['path']) as archive:
            self.assertIn('config/champion.json', archive.namelist())
            self.assertEqual(archive.read('config/champion.json'), b'{"ordinary":true}')
