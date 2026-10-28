'use strict';
// 흐름: /api/params로 허용 목록·기본값을 받는다 → 입력칸 생성 → 값이 바뀌면 debounce 후 /api/result?쿼리 → 화면 갱신.
// 주소창 쿼리도 같이 바꿔서 새로고침·공유해도 같은 화면이 나온다. 모든 출력은 textContent로 넣는다(XSS 방지).
const $ = id => document.getElementById(id);
let schema = {}, timer = null, seq = 0;

function el(tag, props = {}, text) {
  const node = Object.assign(document.createElement(tag), props);
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function buildControls() {
  const query = new URLSearchParams(location.search);
  for (const [key, spec] of Object.entries(schema)) {
    const label = el('label', { id: 'f-' + key });
    label.append(el('span', {}, spec.label));
    let input;
    if (spec.type === 'choice') {
      input = el('select', { name: key });
      for (const c of spec.choices) input.append(el('option', { value: c }, c));
    } else {
      input = el('input', { name: key, type: spec.type === 'datetime' ? 'datetime-local' : 'number' });
      if ('min' in spec) Object.assign(input, { min: spec.min, max: spec.max, step: spec.step || 1 });
    }
    input.value = query.get(key) ?? spec.default;
    input.addEventListener('input', schedule);
    label.append(input, el('small', { className: 'err', id: 'e-' + key }));
    $('controls').append(label);
  }
}

function currentQuery() {
  const q = new URLSearchParams();
  for (const [key, spec] of Object.entries(schema)) {
    const value = $('controls').elements[key].value;
    $('f-' + key).classList.toggle('changed', value !== '' && value !== String(spec.default));
    if (value !== '' && value !== String(spec.default)) q.set(key, value);  // 기본값은 주소에 안 남긴다
  }
  return q;
}

function schedule() { clearTimeout(timer); timer = setTimeout(refresh, 300); }

async function refresh() {
  const q = currentQuery(), mine = ++seq;
  history.replaceState(null, '', q.toString() ? '?' + q : location.pathname);
  $('status').textContent = '계산 중…';
  for (const key in schema) $('e-' + key).textContent = '';
  $('globalErr').textContent = '';
  try {
    const res = await fetch('/api/result?' + q);
    const data = await res.json();
    if (mine !== seq) return;  // 늦게 도착한 이전 응답은 버린다
    if (!res.ok) {
      for (const [key, msg] of Object.entries(data.errors || {})) ($('e-' + key) || $('globalErr')).textContent = msg;
      $('status').textContent = '입력 확인 필요 · 이전 결과는 지웠습니다';
      $('rows').replaceChildren(); $('cards').replaceChildren(); $('applied').textContent = '';
      return;
    }
    render(data);
    $('status').textContent = '갱신 ' + new Date().toLocaleTimeString();
  } catch (err) {
    $('globalErr').textContent = '서버 응답 실패: ' + err.message;
  }
}

function render(data) {
  $('cards').replaceChildren(...Object.entries(data.counts).map(([lv, n]) => {
    const card = el('div', { className: 'card ' + lv }, lv); card.append(el('b', {}, n)); return card;
  }));
  $('window').textContent = `판정 구간 ${data.window.start} → ${data.window.end}`;
  $('rows').replaceChildren(...data.rows.map(r => {
    const tr = el('tr');
    tr.append(el('td', {}, r.tool), el('td', { className: r.level }, r.level), el('td', {}, r.reason),
      el('td', {}, r.points), el('td', {}, r.latest ?? '측정 없음'));
    return tr;
  }));
  if (!data.rows.length) {
    const tr = el('tr'); tr.append(el('td', { colSpan: 5 }, '해당 대상 없음')); $('rows').append(tr);
  }
  const applied = Object.fromEntries(Object.entries(data.applied).map(([k, v]) => [k, schema[k].d ? `${v}  (${schema[k].d})` : v]));
  $('applied').textContent = JSON.stringify(applied, null, 2);
}

$('reset').addEventListener('click', () => {
  for (const [key, spec] of Object.entries(schema)) $('controls').elements[key].value = spec.default;
  refresh();
});

fetch('/api/params').then(r => r.json()).then(s => { schema = s; buildControls(); refresh(); })
  .catch(err => { $('globalErr').textContent = '설정을 불러오지 못했습니다: ' + err.message; });
