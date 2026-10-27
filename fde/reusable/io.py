"""Independent CSV/JSON reader. Decode UTF-8(BOM) first, then cp949."""
import csv
import io
import json
from pathlib import Path


def decode(data):
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError('supported encodings: utf-8 / cp949')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse_bytes(data, kind):
    text = decode(data)
    if kind.lower() == 'json':
        rows = json.loads(text, object_pairs_hook=unique_object,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))
        if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
            raise ValueError('JSON must be an array of objects')
        return rows
    if kind.lower() != 'csv':
        raise ValueError('supported kinds: csv / json')
    reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
    fields = reader.fieldnames
    if fields is None:
        return []
    if any(not field.strip() for field in fields) or len(fields) != len(set(fields)):
        raise ValueError('CSV headers must be nonempty and unique')
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError('invalid CSV: ' + str(exc)) from exc
    if any(None in row or None in row.values() for row in rows):
        raise ValueError('CSV row width differs from header width')
    return rows


def read_table(path):
    path = Path(path)
    return parse_bytes(path.read_bytes(), path.suffix.lstrip('.'))
