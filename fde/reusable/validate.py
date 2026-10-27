"""Independent validation returning typed valid rows and row/field/code errors."""
import math


def convert(value, kind):
    if isinstance(value, bool):
        raise ValueError('boolean is not a number/string field')
    if kind == 'str':
        if not isinstance(value, str):
            raise ValueError('expected string')
        return value.strip()
    if kind == 'int':
        if isinstance(value, float) and not value.is_integer():
            raise ValueError('expected integer')
        return int(value)
    if kind == 'float':
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('expected finite number')
        return number
    raise ValueError('unknown schema type: ' + str(kind))


def validate_rows(rows, schema, unique=None):
    valid, errors, seen = [], [], set()
    for index, row in enumerate(rows, start=1):
        clean, current = {}, []
        for name, rule in schema.items():
            value = row.get(name)
            code = None
            if value is None or (isinstance(value, str) and not value.strip()):
                if rule.get('required', True):
                    code = 'REQUIRED'
                else:
                    clean[name] = None
            else:
                try:
                    value = convert(value, rule.get('type', 'str'))
                    clean[name] = value
                    if ('min' in rule and value < rule['min']) or ('max' in rule and value > rule['max']):
                        code = 'RANGE'
                    elif 'choices' in rule and value not in rule['choices']:
                        code = 'CHOICE'
                except (ValueError, TypeError, OverflowError):
                    code = 'TYPE'
            if code:
                current.append({'row': index, 'field': name, 'code': code})
        if not current and unique is not None:
            key = clean[unique]
            if key in seen:
                current.append({'row': index, 'field': unique, 'code': 'DUPLICATE'})
            else:
                seen.add(key)
        if current:
            errors.extend(current)
        else:
            valid.append(clean)
    return {'valid': valid, 'errors': errors}
