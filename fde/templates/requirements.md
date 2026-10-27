# 요구사항 — requirements가 기준, checks.json은 실행용 사본
| REQ-ID | 내용 | 우선순위 | acceptance criteria (조건·대상·기대 결과) | 처리단계 / D-ID | AI가 할 일 / 내가 확인할 일 | 검증 명령 | 상태/증거 |
|---|---|---|---|---|---|---|---|
| REQ-001 | 합의 후 작성 | P0 | 고정 입력·시점에서 측정 가능한 기대 결과 | | | 미정 | TODO |
P0: 완주 필수 / P1: 유용 / P2: 여유가 있을 때.
checks.json에 같은 ID·우선순위·검증 명령(argv 배열)을 등록한다.
regression 배열에 기존 동작 검증을 최소 1개 넣는다.
증거: artifacts/eval_*.json의 해당 REQ, exit code, source_stable.
합격 문장의 원본은 이 파일이다. skeleton.md·결정표는 REQ-ID를 참조한다. AI가 테스트 통과용으로 기준을 약화하지 않는다.
정책 변경·기준 오류는 사람 확인→새 D-ID·대체 관계→관련 REQ/checks/테스트/handoff 갱신 순서로 반영한다.
지정 src/ 과제는 해당 프로젝트 검증 명령·실제 로그를 기록한다. 이 표의 추가 열은 기록용이며 checks.json의 실행 스키마는 바꾸지 않는다.
