from datetime import datetime, timezone
from pathlib import Path
import re
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fde.kit import _common as c


def snapshot(root, elapsed=None):
    root = Path(root).resolve()
    work = root / 'fde/work'
    text = (work / 'state.md').read_text(encoding='utf-8') if (work / 'state.md').exists() else ''
    match = re.search(r'(?m)^STATE:\s*(' + '|'.join(c.STAGES) + r')\b', text)
    stage = match.group(1) if match else 'DISCOVERY'
    if elapsed is None:
        start = datetime.fromisoformat(c.read_json(work / 'session.json')['started_at'])
        if start.tzinfo is None:
            raise ValueError('session.started_at must include timezone')
        elapsed = max(0, (datetime.now(timezone.utc) - start).total_seconds() / 60)
    warnings = []
    for minute, message in [(80, '구조 변경 금지'), (140, '새 기능 금지'),
                            (170, '저장·제출 확인만'), (180, '180분 작업 시간 초과')]:
        if elapsed >= minute:
            warnings.append(message)
    reports = list((root / 'fde/artifacts').glob('eval_*.json'))
    report = c.read_json(max(reports, key=lambda x: x.stat().st_mtime_ns)) if reports else {}
    config_path = work / 'checks.json'
    config = c.read_json(config_path) if config_path.exists() else {'requirements': []}
    fresh = (report.get('work_manifest') == c.manifest(work) and
             report.get('task_manifest') == c.task_manifest(root)) if report else False
    passed = {x['id'] for x in report.get('requirements', []) if x.get('pass')} if fresh else set()
    remaining = [x['id'] for x in config['requirements'] if x['priority'] == 'P0' and x['id'] not in passed]
    meta = root / 'fde/champion/champion.json'
    score = c.read_json(meta)['score'] if meta.exists() else None
    return {'stage': stage, 'elapsed_minutes': round(elapsed, 2), 'champion_score': score,
            'task_limit_minutes': 180, 'remaining_task_minutes': round(max(0, 180 - elapsed), 2),
            'remaining_p0': remaining, 'evidence_fresh': fresh, 'warnings': warnings,
            'note': '로컬 180분 작업 예산의 참고 타이머다. 프로젝트의 실제 마감이 우선하며 단계·GATE는 사람이 실제 근거로 기록한다.'}


if __name__ == '__main__':
    p = c.parser('Show STATE, time, champion and remaining P0 in one view.')
    a = p.parse_args()
    sys.exit(c.cli(lambda: snapshot(a.root)))
