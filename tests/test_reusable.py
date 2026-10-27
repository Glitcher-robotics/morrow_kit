import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fde.reusable import io, validate, aggregate, export, webui


class IOTests(unittest.TestCase):
    def test_csv_encodings_and_quoted_cells(self):
        raw = '이름,값\r\n장비A,"1,2"\r\n'.encode('cp949')
        self.assertEqual(io.parse_bytes(raw, 'csv'), [{'이름': '장비A', '값': '1,2'}])
        self.assertEqual(io.parse_bytes(b'\xef\xbb\xbf[{"x":1}]', 'json'), [{'x': 1}])

    def test_empty_and_malformed(self):
        self.assertEqual(io.parse_bytes(b'', 'csv'), [])
        for raw, kind in [(b'{}', 'json'), (b'[1]', 'json'), (b'a,a\n1,2', 'csv'),
                          (b'a,b\n1,2,3', 'csv'), (b'[{"x":1,"x":2}]', 'json')]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                io.parse_bytes(raw, kind)


class ValidateTests(unittest.TestCase):
    def test_invalid_values_do_not_pollute_dedup(self):
        schema = {'id': {'type': 'str'}, 'value': {'type': 'float', 'min': 0, 'max': 10}}
        result = validate.validate_rows(
            [{'id': 'a', 'value': 'NaN'}, {'id': 'a', 'value': '10'},
             {'id': 'a', 'value': '1'}, {'id': '', 'value': '-1'},
             {'id': 'b', 'value': True}], schema, unique='id')
        self.assertEqual(result['valid'], [{'id': 'a', 'value': 10.0}])
        self.assertEqual([x['code'] for x in result['errors']],
                         ['TYPE', 'DUPLICATE', 'REQUIRED', 'RANGE', 'TYPE'])

    def test_choices_and_missing(self):
        result = validate.validate_rows([{'mode': 'BAD'}, {}],
                                      {'mode': {'type': 'str', 'choices': ['OK']}})
        self.assertEqual([x['code'] for x in result['errors']], ['CHOICE', 'REQUIRED'])


class AggregateExportTests(unittest.TestCase):
    def test_sort_group_and_roundtrip(self):
        rows = [{'group': 'b', 'value': 2.0}, {'group': 'a', 'value': 3.0},
                {'group': 'b', 'value': 4.0}]
        self.assertEqual(aggregate.summarize(rows, 'group', ['value']),
                         [{'group': 'a', 'count': 1, 'value': 3.0},
                          {'group': 'b', 'count': 2, 'value': 6.0}])
        self.assertEqual(aggregate.filter_rows(rows, lambda x: x['value'] > 3), [rows[2]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            export.write_json(rows, path / 'rows.json')
            self.assertEqual(io.read_table(path / 'rows.json'), rows)
            export.write_csv(rows, path / 'rows.csv', ['group', 'value'])
            self.assertEqual(len(io.read_table(path / 'rows.csv')), 3)
            first = (path / 'rows.json').read_bytes()
            export.write_json(rows, path / 'rows.json')
            self.assertEqual(first, (path / 'rows.json').read_bytes())


class WebUITests(unittest.TestCase):
    def test_upload_table_errors_and_no_file_serving(self):
        server = webui.create_server(port=0, host='0.0.0.0')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        try:
            with urlopen(base) as response:
                self.assertIn(b'type="file"', response.read())
            req = Request(base + '/api/analyze', b'[{"x":"<script>"}]',
                          {'Content-Type': 'application/json'})
            with urlopen(req) as response:
                self.assertEqual(json.load(response)['rows'][0]['x'], '<script>')
            for endpoint, body, expected in [('/api/analyze', b'not json', 400),
                                              ('/../../README.md', None, 404)]:
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(base + endpoint, body, {'Content-Type': 'application/json'}))
                self.assertEqual(caught.exception.code, expected)
                caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
