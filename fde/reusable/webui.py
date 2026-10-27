"""Independent localhost upload -> table -> detail UI, using http.server only."""
import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE = r'''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>FDE 데이터 확인</title><style>
body{font:16px system-ui;max-width:960px;margin:40px auto;padding:0 20px;color:#173047}
button,input{font:inherit;padding:10px}table{border-collapse:collapse;width:100%;margin-top:20px}
td,th{border-bottom:1px solid #d4dfe6;padding:10px;text-align:left}tr{cursor:pointer}
pre{white-space:pre-wrap;padding:16px;background:#f2f6f9}#error{color:#a02121}
</style><h1>데이터 확인</h1><p>CSV 또는 JSON을 올려 결과와 상세 내용을 확인합니다.</p>
<form id="form"><input id="file" type="file" accept=".csv,.json" required><button>확인</button></form>
<p id="error" role="alert"></p><p id="summary"></p><table id="table"></table>
<h2>상세</h2><pre id="detail">표의 행을 선택하세요.</pre><script>
const $=id=>document.getElementById(id);
$('form').onsubmit=async e=>{e.preventDefault();$('error').textContent='';$('table').replaceChildren();
try{const file=$('file').files[0],res=await fetch('/api/analyze',{method:'POST',
headers:{'Content-Type':file.name.toLowerCase().endsWith('.csv')?'text/csv':'application/json'},body:file});
const data=await res.json();if(!res.ok)throw Error(data.error||'입력 처리 실패');
const rows=data.details||data.rows||[data],keys=[...new Set(rows.flatMap(Object.keys))];
$('summary').textContent=rows.length+'행 · 처리 완료';$('detail').textContent=JSON.stringify(data,null,2);
let header=$('table').insertRow();for(const key of keys){let cell=document.createElement('th');cell.textContent=key;header.append(cell)}
for(const row of rows){let tr=$('table').insertRow();for(const key of keys){let td=tr.insertCell();
td.textContent=typeof row[key]==='object'?JSON.stringify(row[key]):String(row[key]??'')}
tr.onclick=()=>$('detail').textContent=JSON.stringify(row,null,2)}
}catch(err){$('error').textContent=err.message;$('summary').textContent='';$('detail').textContent='';}};
</script></html>'''


def parse_body(raw, content_type):
    text = None
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise ValueError('UTF-8 / cp949 인코딩만 지원합니다.')
    if content_type == 'text/csv':
        reader = csv.DictReader(io.StringIO(text), strict=True)
        fields = reader.fieldnames
        if fields and (len(set(fields)) != len(fields) or any(not x for x in fields)):
            raise ValueError('CSV 헤더가 비어 있거나 중복되었습니다.')
        rows = list(reader)
        if any(None in row or None in row.values() for row in rows):
            raise ValueError('CSV 열 수가 맞지 않습니다.')
    elif content_type == 'application/json':
        rows = json.loads(text)
    else:
        raise ValueError('text/csv 또는 application/json이 필요합니다.')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('객체 배열이 필요합니다.')
    return rows


def create_server(port=8000, analyzer=None, host='127.0.0.1'):
    analyze = analyzer or (lambda rows: {'rows': rows, 'total': len(rows)})

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, code, value, kind='application/json; charset=utf-8'):
            raw = value.encode('utf-8') if isinstance(value, str) else json.dumps(
                value, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == '/':
                self.respond(200, PAGE, 'text/html; charset=utf-8')
            else:
                self.respond(404, {'error': '경로가 없습니다.'})

        def do_POST(self):
            if self.path != '/api/analyze':
                self.respond(404, {'error': '경로가 없습니다.'})
                return
            try:
                length = int(self.headers.get('Content-Length', '-1'))
                if length < 0 or length > 2 * 1024 * 1024:
                    self.respond(413, {'error': '최대 2MiB 파일이 필요합니다.'})
                    return
                self.connection.settimeout(10)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('파일 전송이 중단되었습니다.')
                rows = parse_body(raw, self.headers.get('Content-Type', '').split(';')[0])
                result = analyze(rows)
                self.respond(200, result)
            except (ValueError, TypeError, csv.Error, TimeoutError) as exc:
                self.respond(400, {'error': str(exc)})

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--host', default='127.0.0.1', help='Use 0.0.0.0 only when the project requires connections through another interface.')
    a = p.parse_args()
    with create_server(a.port, host=a.host) as server:
        print('http://' + a.host + ':' + str(server.server_port), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
