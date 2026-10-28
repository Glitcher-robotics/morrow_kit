from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
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


PROBLEM_LABELS = ['사용자', '해결할 문제', '성공 기준', '만들 것', '만들지 않을 것', '제약', 'Unknown']
GATES = ['GATE1', 'GATE2', 'GATE3', 'GATE4']


def _read(path):
    return path.read_text(encoding='utf-8-sig') if path.exists() else ''


def _cells(line):
    return [x.strip() for x in line.strip().strip('|').split('|')]


def _field(text, label):
    for line in text.splitlines():
        if line.startswith(label) and ':' in line:
            return line.split(':', 1)[1].strip()
    return ''


def _git(root):
    try:
        out = subprocess.run(['git', '-C', str(root), 'log', '--reverse', '--format=%s'],
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    subjects = [x for x in out.stdout.splitlines() if x.strip()]
    return {'commits': len(subjects), 'req_commits': sum(bool(re.match(r'REQ-\d+', x)) for x in subjects),
            'first': subjects[0] if subjects else None}


def intent(root):
    """Count where the Q→D→REQ→commit chain is filled or broken; it is a self-check, not a score."""
    root = Path(root).resolve()
    work = root / 'fde/work'
    gaps = []
    git = _git(root)
    if git is None:
        gaps.append('Git 이력 없음: git init 후 init commit')
    else:
        if not git['first'] or not git['first'].lower().startswith('init'):
            gaps.append('첫 commit이 과제 원본(init)이 아님')
        if git['req_commits'] == 0:
            gaps.append('REQ-xxx commit 없음')
    problem = _read(work / 'problem.md')
    empty = [x for x in PROBLEM_LABELS if not _field(problem, x)]
    gaps += ['problem 빈칸: ' + x for x in empty]
    decisions, statuses = set(), {}
    for line in _read(work / 'decisions.md').splitlines():
        cells = _cells(line)
        if len(cells) >= 3 and re.fullmatch(r'D\d+', cells[0]) and cells[2]:
            decisions.add(cells[0])
            key = (cells[1] or '미기재').split('→')[0]
            statuses[key] = statuses.get(key, 0) + 1
    if not decisions:
        gaps.append('decisions에 값이 있는 D 없음')
    skeleton = 0
    for line in _read(work / 'skeleton.md').splitlines():
        cells = _cells(line)
        if len(cells) >= 5 and re.match(r'[1-6①-⑥]', cells[0]) and (cells[3] or cells[4]):
            skeleton += 1
    if skeleton < 6:
        gaps.append(f'skeleton D-ID·REQ 연결 {skeleton}/6')
    reqs, cited = 0, 0
    for line in _read(work / 'requirements.md').splitlines():
        cells = _cells(line)
        if cells and re.fullmatch(r'REQ-\d+', cells[0]) and '합의 후 작성' not in line:
            reqs += 1
            cited += bool(re.search(r'\bD\d+\b', line))
    if reqs and cited < reqs:
        gaps.append(f'D 근거 없는 REQ {reqs - cited}개')
    state = _read(work / 'state.md')
    gates = {g: bool(re.search(rf'(?m)^{g}[^:\n]*:[ \t]*\S', state)) for g in GATES}
    if not _field(state, '마지막 commit'):
        gaps.append('state 마지막 commit 비어 있음')
    return {'git': git, 'problem_filled': len(PROBLEM_LABELS) - len(empty), 'problem_total': len(PROBLEM_LABELS),
            'decisions': len(decisions), 'decision_status': statuses, 'skeleton_linked': skeleton,
            'requirements': reqs, 'requirements_citing_d': cited, 'gates': gates, 'gaps': gaps,
            'note': '기록의 연결 상태만 센다. 내용의 정확성·사람 승인·고객 수용은 SELFCHECK와 실제 근거로 확인한다.'}


if __name__ == '__main__':
    p = c.parser('Show STATE, time, champion and remaining P0 in one view.')
    p.add_argument('--intent', action='store_true', help='Q→D→REQ→commit 기록 연결 자가 점검')
    a = p.parse_args()
    sys.exit(c.cli(lambda: intent(a.root) if a.intent else snapshot(a.root)))
