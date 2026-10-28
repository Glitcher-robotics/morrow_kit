import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

EXAMPLE = Path(__file__).resolve().parents[1] / 'fde/examples/live_params'


def load_app():
    spec = importlib.util.spec_from_file_location('live_params_app', EXAMPLE / 'app.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveParamsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app()
        cls.schema = cls.app.load_defaults()
        cls.rows = cls.app.sample_data()

    def result(self, **query):
        values, errors = self.app.parse_params({k: [str(v)] for k, v in query.items()}, self.schema)
        self.assertEqual(errors, {})
        return {r['tool']: r['level'] for r in self.app.compute(self.rows, values)['rows']}

    def test_defaults_come_from_config(self):
        config = json.loads((EXAMPLE / 'config.json').read_text(encoding='utf-8'))
        values, errors = self.app.parse_params({}, self.schema)
        self.assertEqual(errors, {})
        for key, value in config.items():
            self.assertEqual(values[key], value)

    def test_changing_one_value_changes_expected_target(self):
        self.assertEqual(self.result(), {'EX-B': '조치', 'EX-A': '주의', 'EX-C': '정상'})
        self.assertEqual(self.result(usl=101.5)['EX-A'], '조치')
        self.assertEqual(self.result(base_time='2026-01-02T12:00')['EX-B'], '정상')
        self.assertEqual(self.result(trend_points=8)['EX-A'], '정상')

    def test_rejects_bad_values(self):
        cases = [{'trend_points': ['99']}, {'window_hours': ['abc']}, {'base_time': ['2026-13-01T00:00']},
                 {'level': ['<script>']}, {'lsl': ['110']}, {'lsl': ['nan']}, {'typo': ['1']}]
        for query in cases:
            _, errors = self.app.parse_params(query, self.schema)
            self.assertTrue(errors, query)

    def test_http_roundtrip_and_headers(self):
        server = self.app.create_server(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/result?usl=101.5&level=%EC%A1%B0%EC%B9%98') as res:
                data = json.loads(res.read())
                self.assertIn("script-src 'self'", res.headers['Content-Security-Policy'])
            self.assertEqual({r['tool'] for r in data['rows']}, {'EX-A', 'EX-B'})
            self.assertEqual(data['applied']['usl'], 101.5)
            with self.assertRaises(HTTPError) as caught:
                urlopen(base + '/api/result?trend_points=1')
            self.assertEqual(caught.exception.code, 400)
            for path in ['/', '/live.js', '/api/params']:
                with urlopen(base + path) as res:
                    self.assertEqual(res.status, 200)
        finally:
            server.shutdown()
            server.server_close()

    @unittest.skipIf(shutil.which('node') is None, 'node not installed')
    def test_node_params_matches_python_rules(self):
        script = ("const {parseParams}=require(process.argv[1]);"
                  "const s={trend_points:{type:'int',label:'t',min:3,max:12,default:6},"
                  "lsl:{type:'float',label:'l',min:0,max:1000,default:95},usl:{type:'float',label:'u',min:0,max:1000,default:105}};"
                  "const r=[['trend_points=5'],['trend_points=99'],['lsl=110'],['x=1']].map(q=>parseParams(new URLSearchParams(q[0]),s));"
                  "console.log(JSON.stringify(r.map(x=>Object.keys(x.errors))))")
        out = subprocess.run(['node', '-e', script, str(EXAMPLE / 'node_params.js')],
                             capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout), [[], ['trend_points'], ['usl'], ['_']])


if __name__ == '__main__':
    unittest.main()
