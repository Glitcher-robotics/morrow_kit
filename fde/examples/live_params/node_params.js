'use strict';
// Node 프로젝트(예: node:http 서버)에 붙이는 같은 패턴. app.py의 parse_params와 규칙이 같다.
// 사용: const { parseParams } = require('./node_params');
//       const { values, errors } = parseParams(new URL(req.url, 'http://localhost').searchParams, SCHEMA);
//       if (Object.keys(errors).length) return reply(400, ...JSON.stringify({ errors }));
//       const summary = buildSummary({ config: values, base_time: values.base_time });
const DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

function parseParams(searchParams, schema) {
  const values = {}, errors = {};
  const unknown = [...new Set(searchParams.keys())].filter(k => !(k in schema));
  if (unknown.length) errors._ = '알 수 없는 값: ' + unknown.sort().join(', ');
  for (const [key, spec] of Object.entries(schema)) {
    const raw = searchParams.get(key);
    if (raw === null || raw === '') { values[key] = spec.default; continue; }
    let ok = true, value = raw;
    if (spec.type === 'datetime') ok = DATETIME.test(raw) && !Number.isNaN(Date.parse(raw));
    else if (spec.type === 'choice') ok = spec.choices.includes(raw);
    else {
      value = Number(raw);
      ok = raw.trim() !== '' && Number.isFinite(value) && (spec.type !== 'int' || Number.isInteger(value))
        && value >= spec.min && value <= spec.max;
    }
    if (ok) values[key] = value;
    else errors[key] = `${spec.label}: 형식 또는 범위${'min' in spec ? ` ${spec.min}~${spec.max}` : ''} 확인`;
  }
  if (!('lsl' in errors) && !('usl' in errors) && 'lsl' in schema && 'usl' in schema && values.lsl >= values.usl) {
    errors.usl = '상한은 하한보다 커야 합니다.';
  }
  return { values, errors };
}

module.exports = { parseParams };
