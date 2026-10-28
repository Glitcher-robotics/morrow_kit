# live_params — 화면에서 값 조절 → 즉시 재계산

담당자 앞에서 "기준 시각을 어제로, 연속 개수를 5로 바꾸면?"을 바로 보여 주는 패턴이다. 합성 예시 데이터·예시 규칙이며 업무 기준이 아니다.

```sh
python fde/examples/live_params/app.py --port 8000
```
브라우저에서 `http://127.0.0.1:8000` → 기준 시각·구간·연속 개수·상한/하한·보기를 바꿔 본다.
예: 상한 105 → 101.5면 EX-A가 조치로 바뀐다. 기준 시각을 `2026-01-02T12:00`으로 당기면 EX-B 이탈이 구간 밖으로 빠진다.

## 구조 — 값이 사는 곳은 세 층

| 층 | 역할 | 이 예시 |
|---|---|---|
| config.json | **기본값** (담당자와 합의한 값, D-ID 근거) | `config.json` |
| URL 쿼리 | **이번 화면에서만** 바꾼 값. 새로고침·링크 공유해도 유지 | `?trend_points=5&base_time=…` |
| 서버 허용 목록 | 바꿀 수 있는 키·형식·범위·교차 조건 검사 | `PARAMS`, `parse_params()` |

1. `GET /api/params` → 허용 목록과 기본값. 화면은 이것으로 입력칸을 만든다.
2. 입력이 바뀌면 300ms debounce → `GET /api/result?…` → 서버가 검사 후 **순수 함수 `compute()`로 재계산**.
3. 응답의 `applied`에 실제 적용 값을 돌려준다. 화면은 적용 값·D-ID·"기본값과 다름" 표시를 보여 준다.
4. 잘못된 값은 400 + 필드별 메시지. 이전 결과를 남겨 두지 않아 틀린 값의 결과로 오해하지 않게 한다.

지켜야 할 것: 화면 조절은 config 파일을 **쓰지 않는다**(저장은 별도 합의). 모르는 키는 거절한다. 출력은 `textContent`. 판정 로직은 서버 한 곳에만 둔다(화면에서 다시 계산하지 않는다).

## 기존 Node 프로젝트에 붙이기 (예: `src/server.js` + `src/view.js`)

판정 함수가 이미 `buildSummary({ config: 덮어쓸 값, base_time })`처럼 덮어쓰기를 받으면 서버 몇 줄로 된다.

**① 서버: 쿼리 → 검사 → 덮어쓰기** ([node_params.js](node_params.js))
```js
const { parseParams } = require('./node_params');
const SCHEMA = {
  base_time: { type: 'datetime', label: '판정 기준 시각', default: '' },
  trend_points: { type: 'int', label: '연속 개수', min: 3, max: 12, default: 6 },
  baseline_wafers: { type: 'int', label: '기준선 장수', min: 6, max: 50, default: 20 },
  window_hours: { type: 'int', label: '최근 구간(시간)', min: 1, max: 72, default: 24 },
};
const url = new URL(req.url, 'http://localhost');
const { values, errors } = parseParams(url.searchParams, SCHEMA);
if (Object.keys(errors).length) return reply(400, 'application/json; charset=utf-8', JSON.stringify({ errors }));
const { base_time, ...config } = values;
const summary = buildSummary({ config, base_time: base_time ? base_time.replace('T', ' ') + ':00' : undefined });
```
기본값은 config.json에서 읽어 SCHEMA default에 넣으면 한 곳에서 관리된다. `datetime-local` 값(`2026-01-03T06:00`)과 프로젝트 시각 형식이 다르면 여기서 변환한다.

**② 화면: 두 가지 방법**

| 방법 | 동작 | 바꿀 것 |
|---|---|---|
| A. JS 없이 GET 폼 | 값 입력 → 적용 버튼 → 같은 주소에 쿼리로 다시 렌더 | `view.js`에 `<form method="get">` + 현재 값을 `value="${E(v)}"`로 채운 입력칸. CSP 변경 불필요 |
| B. 즉시 갱신 | 입력 즉시 `/api/summary?…`를 fetch해 표만 교체 | `live.js` 같은 외부 스크립트 파일 + CSP에 `script-src 'self'; connect-src 'self'` 추가. 인라인 스크립트 금지 유지 |

CSP가 `default-src 'none'`이면 스크립트가 막혀 있으므로, 가장 빠른 길은 A로 먼저 동작시키고 시간이 되면 B로 바꾸는 것이다.

## 검사할 것 (REQ 예)
- 쿼리 없음 = config 기본값 결과와 동일
- 범위 밖·형식 오류·모르는 키 → 400, 필드 메시지
- 하한 ≥ 상한 → 400
- 같은 쿼리 두 번 → 같은 결과(결정론)
- 값 하나를 바꾸면 예상한 대상의 등급만 바뀐다(실행 전 내 예상을 먼저 적는다)

검사 예시: `tests/test_examples.py` (morrow_kit 저장소).
