from pathlib import Path
import sys
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fde.kit import _common as c


def resolve_report(root, report):
    folder = (root / 'fde/artifacts').resolve()
    if str(report) == 'latest':
        candidates = list(folder.glob('eval_*.json'))
        if not candidates:
            raise ValueError('no evaluation report')
        report = max(candidates, key=lambda x: x.stat().st_mtime_ns)
    report = Path(report).resolve()
    if report.parent != folder or not report.name.startswith('eval_'):
        raise ValueError('report must be an evaluation inside fde/artifacts')
    return report


def promote(root, report):
    root = Path(root).resolve()
    with c.promotion_lock(root):
        return _promote(root, resolve_report(root, report))


def _promote(root, report_path):
    report = c.read_json(report_path)
    requirements = report.get('requirements', [])
    regression = report.get('regression', [])
    p0 = [x for x in requirements if x.get('priority') == 'P0']
    if (not p0 or not all(x.get('pass') is True for x in p0) or not regression
            or not all(x.get('pass') is True for x in regression) or not report.get('source_stable')):
        raise ValueError('P0, regression and stable-source evidence must pass')
    calculated_score = round(100 * sum(x.get('pass') is True for x in requirements) / len(requirements), 6)
    if report.get('score') != calculated_score:
        raise ValueError('invalid score in report')
    work = root / 'fde/work'
    expected = report['work_manifest']
    if c.manifest(work) != expected or c.task_manifest(root) != report['task_manifest']:
        raise ValueError('source or task input changed after evaluation; evaluate again')
    champion = root / 'fde/champion'
    metadata = champion / 'champion.json'
    old = c.read_json(metadata) if metadata.exists() else {}
    if calculated_score < old.get('score', -1):
        raise ValueError('score is below current champion')
    artifacts = root / 'fde/artifacts'
    token = uuid.uuid4().hex
    staging, backup = artifacts / ('.promote-' + token), artifacts / ('.backup-' + token)
    history_path = artifacts / 'promotion_history.json'
    history = c.read_json(history_path) if history_path.exists() else []
    changed = False
    committed = False
    try:
        staging.mkdir()
        c.copy_candidate(work, staging)
        if c.manifest(staging) != expected or c.task_manifest(root) != report['task_manifest']:
            raise ValueError('source changed while staging')
        meta = {'score': calculated_score, 'promoted_at': c.now(), 'report': report_path.name,
                'work_manifest': expected, 'task_manifest': report['task_manifest']}
        c.write_json(staging / 'champion.json', meta)
        if champion.exists():
            champion.rename(backup)
        try:
            staging.rename(champion)
            changed = True
            c.write_json(history_path, history + [meta])
            committed = True
        except BaseException:
            if changed:
                c.remove_tree(champion, root)
            if backup.exists():
                backup.rename(champion)
            raise
    finally:
        c.remove_tree(staging, root)
        if committed:
            c.remove_tree(backup, root)
    return {'promoted': True, 'score': calculated_score, 'champion': str(champion)}


if __name__ == '__main__':
    p = c.parser('Promote evaluated P0+regression passing work without losing the previous champion.')
    p.add_argument('--report', default='latest', help='exact evaluation path or latest')
    a = p.parse_args()
    sys.exit(c.cli(lambda: promote(a.root, a.report)))
