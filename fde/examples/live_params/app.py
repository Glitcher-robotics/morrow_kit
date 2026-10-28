"""Live parameter UI example: config gives defaults, URL query overrides them per view, server validates.

합성 예시 데이터와 예시 규칙이다. 업무 기준·정답이 아니다. 표준 라이브러리만 사용한다.
"""
import argparse
from datetime import datetime, timedelta
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
FORMAT = '%Y-%m-%dT%H:%M'

# 화면에서 바꿀 수 있는 값만 허용 목록으로 둔다. default는 config에서 오고, d는 근거 결정 ID 자리다.
PARAMS = {
    'base_time': {'type': 'datetime', 'label': '판정 기준 시각', 'default': '2026-01-03T06:00', 'd': 'D-예시'},
    'window_hours': {'type': 'int', 'label': '최근 구간(시간)', 'min': 1, 'max': 72, 'default': 24, 'd': 'D-예시'},
    'trend_points': {'type': 'int', 'label': '연속 상승 개수', 'min': 3, 'max': 12, 'default': 6, 'd': 'D-예시'},
    'lsl': {'type': 'float', 'label': '하한(nm)', 'min': 0, 'max': 1000, 'step': 0.5, 'default': 95.0, 'd': 'D-예시'},
    'usl': {'type': 'float', 'label': '상한(nm)', 'min': 0, 'max': 1000, 'step': 0.5, 'default': 105.0, 'd': 'D-예시'},
    'level': {'type': 'choice', 'label': '보기', 'choices': ['전체', '조치', '주의', '정상'], 'default': '전체', 'd': None},
}
LEVELS = ['조치', '주의', '정상']


def load_defaults(path=HERE / 'config.json'):
    """config.json은 기본값만 정한다. 화면 조절은 파일을 바꾸지 않는다."""
    schema = json.loads(json.dumps(PARAMS))
    if path.exists():
        for key, value in json.loads(path.read_text(encoding='utf-8-sig')).items():
            if key in schema:
                schema[key]['default'] = value
    return schema


def parse_params(query, schema):
    """허용 목록·형식·범위·교차 조건을 검사한다. 모르는 키는 거절해 오타가 조용히 무시되지 않게 한다."""
    values, errors = {}, {}
    unknown = sorted(set(query) - set(schema))
    if unknown:
        errors['_'] = '알 수 없는 값: ' + ', '.join(unknown)
    for key, spec in schema.items():
        raw = query.get(key, [None])[-1]
        if raw is None or raw == '':
            values[key] = spec['default']
            continue
        try:
            if spec['type'] == 'datetime':
                values[key] = datetime.strptime(raw, FORMAT).strftime(FORMAT)
            elif spec['type'] == 'choice':
                if raw not in spec['choices']:
                    raise ValueError
                values[key] = raw
            else:
                number = int(raw) if spec['type'] == 'int' else float(raw)
                if number != number or not spec['min'] <= number <= spec['max']:
                    raise ValueError
                values[key] = number
        except ValueError:
            bounds = f" {spec['min']}~{spec['max']}" if 'min' in spec else ''
            errors[key] = f"{spec['label']}: 형식 또는 범위{bounds} 확인"
    if 'lsl' not in errors and 'usl' not in errors and values['lsl'] >= values['usl']:
        errors['usl'] = '상한은 하한보다 커야 합니다.'
    return values, errors


def sample_data():
    """설비 3개 × 1시간 간격 60개 합성 측정. A는 상승 추세, B는 한 번 이탈, C는 안정."""
    start = datetime(2026, 1, 1, 0, 0)
    rows = []
    for i in range(60):
        at = (start + timedelta(hours=i)).strftime(FORMAT)
        rows.append({'tool': 'EX-A', 'at': at, 'nm': 100 + (0.3 * (i - 48) if i >= 48 else (i % 3) * 0.2)})
        rows.append({'tool': 'EX-B', 'at': at, 'nm': 106.2 if i == 40 else 100 + (i % 4) * 0.3})
        rows.append({'tool': 'EX-C', 'at': at, 'nm': 100 + (i % 2) * 0.4})
    return rows


def compute(rows, p):
    """판정은 순수 함수로 둔다. 같은 입력·값이면 같은 결과."""
    end = datetime.strptime(p['base_time'], FORMAT)
    begin = end - timedelta(hours=p['window_hours'])
    result = []
    for tool in sorted({r['tool'] for r in rows}):
        series = [r for r in rows if r['tool'] == tool and begin <= datetime.strptime(r['at'], FORMAT) <= end]
        out = [r for r in series if not p['lsl'] <= r['nm'] <= p['usl']]
        run, best, best_at = 1, 1, None
        for prev, cur in zip(series, series[1:]):
            run = run + 1 if cur['nm'] > prev['nm'] else 1
            if run > best:
                best, best_at = run, cur['at']
        if out:
            level, reason = '조치', f"{out[-1]['at']} {out[-1]['nm']:.2f} nm, 스펙 {p['lsl']}~{p['usl']} 밖 ({len(out)}건)"
        elif best >= p['trend_points']:
            level, reason = '주의', f"{best_at}까지 {best}회 연속 상승 (기준 {p['trend_points']})"
        else:
            level, reason = '정상', f"최대 연속 상승 {best}회"
        result.append({'tool': tool, 'level': level, 'reason': reason, 'points': len(series),
                       'latest': round(series[-1]['nm'], 2) if series else None})
    result.sort(key=lambda r: (LEVELS.index(r['level']), r['tool']))
    shown = [r for r in result if p['level'] in ('전체', r['level'])]
    return {'applied': p, 'window': {'start': begin.strftime(FORMAT), 'end': p['base_time']},
            'counts': {lv: sum(r['level'] == lv for r in result) for lv in LEVELS}, 'rows': shown}


def create_server(port=8000, host='127.0.0.1', rows=None, schema=None):
    rows = rows if rows is not None else sample_data()
    schema = schema or load_defaults()
    files = {'/': ('index.html', 'text/html; charset=utf-8'), '/live.js': ('live.js', 'text/javascript; charset=utf-8')}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, code, body, kind='application/json; charset=utf-8'):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path in files:
                name, kind = files[url.path]
                self.respond(200, (HERE / name).read_bytes(), kind)
            elif url.path == '/api/params':
                self.respond(200, schema)
            elif url.path == '/api/result':
                values, errors = parse_params(parse_qs(url.query, keep_blank_values=True), schema)
                self.respond(400, {'errors': errors}) if errors else self.respond(200, compute(rows, values))
            else:
                self.respond(404, {'error': '경로가 없습니다.'})

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--port', type=int, default=8000)
    a.add_argument('--host', default='127.0.0.1', help='과제가 요구할 때만 0.0.0.0')
    args = a.parse_args()
    with create_server(args.port, args.host) as server:
        print(f'http://{args.host}:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
