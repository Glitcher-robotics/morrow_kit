"""Independent, explicit filtering/grouping/sorting; no domain decisions."""
import math


def filter_rows(rows, predicate):
    return [row for row in rows if predicate(row)]


def sort_rows(rows, keys):
    return sorted(rows, key=lambda row: tuple(row[key] for key in keys))


def summarize(rows, group_by, sum_fields=()):
    groups = {}
    for row in rows:
        key = row[group_by]
        groups.setdefault(key, []).append(row)
    result = []
    for key in sorted(groups):
        members = groups[key]
        summary = {group_by: key, 'count': len(members)}
        for field in sum_fields:
            values = [float(row[field]) for row in members]
            if not all(math.isfinite(value) for value in values):
                raise ValueError('nonfinite aggregation value')
            summary[field] = math.fsum(values)
        result.append(summary)
    return result
