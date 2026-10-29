# QUICKCARD — 현재 단계만 보기

**묻기 → 정하기 → 준비 → 한 번 실행 → 검사 → 사용자 확인 → 전달.**

## 시작 0~5분 — 이 순서로

0. 키트는 과제 폴더 **밖**에 받는다: `git clone <키트 주소> /tmp/morrow_kit`. 과제 폴더 안에 받으면 제출물·commit·Codex 검색에 섞인다.
   `pwd; ls -a; date` — 과제 폴더가 홈(`.bashrc`·`.config`가 보임)인지, 서버 시각이 UTC인지 확인한다.
1. **한 번에:** `python3 /tmp/morrow_kit/install.py --target . --start`
   .gitignore(`.codex/` 로그인 정보·셸 설정 제외) → `git init`(없을 때만) → `init: 과제 원본` commit → 키트 설치 → work 양식 → `chore: morrow_kit 설치` commit.
   - 상위 폴더가 이미 Git이면 멈춘다. 과제 폴더를 다시 확인한다.
   - 모르는 숨김 파일이 보이면 commit 전에 멈춘다. 비밀이면 .gitignore에 넣고, 과제 파일이면 `--allow-hidden`.
   - 이미 commit이 있으면 원본 commit은 건너뛰고 키트 파일만 commit한다.
   - 단계별로 하려면 [GIT](GIT.md)의 `--gitignore-only` → init commit → install 순서.
2. Codex 업데이트 안내가 뜨면 건너뛴다. `npm install -g`·`sudo` 설치를 하지 않는다.
3. **과제 폴더에서** Codex를 연다. 상위 폴더에서 열면 AGENTS.md가 로드되지 않는다.
4. "지금 적용 중인 AGENTS.md 규칙 3개만 말해 줘"로 로드를 확인한다. 못 말하면 다시 연다.
5. state.md에 작업 폴더·Git 루트·AGENTS 로드 확인을 적는다.

**새 세션을 열 때마다 첫 메시지:** "handoff 요약만 읽고 STATE와 다음 3행동을 한 줄로 말해. 이 세션은 [범위]만 맡는다. 기록 파일은 고치지 마(기록 담당 세션이면 이어받기 시험 칸에 남겨)."
여러 세션을 돌리면 기록 파일(decisions·requirements·state·handoff)을 고치는 세션은 하나만 정한다.

매 프롬프트 전 30초·체크포인트마다 2분은 [SELFCHECK](SELFCHECK.md)로 기술·의도·인지 빈칸을 확인한다.

| STATE | 남길 최소 근거 | 선택 지시 |
|---|---|---|
| DISCOVERY | 제약·공개 입력·질문/답 원문·Unknown | STAGE_PROMPTS의 DIS |
| CONTRACT | 사람 확인 범위·REQ 합격 문장·단계 계약 | CON |
| SCAFFOLD | 기존 파일/함수↔실행 명령, 작은 입력·기대값 | SCA |
| E2E_V0 | 실제 입력→출력·작은 기대값 검사·첫 피드백 요청 | E2E |
| VERIFY | P0·경계/회귀·실제 로그·남은 위험 | VER |
| ACCEPT | 사용자 피드백/미응답·최종 회귀·필수 문서·한계 | ACC |
| SUBMIT | 전달 위치 fresh run·필수 파일·실제 인도 확인 | SUB |

## 네 가지를 연결하기

질문/답 **Q-ID** → 선택/이유 **D-ID** → 합격 기준 **REQ-ID** → 실제 명령·결과·근거.
정책 승인 / 구현 검사 / 사용자 결과 수용의 O/X를 따로 쓴다. 파일이 있다는 사실을 승인·실행 성공으로 바꾸지 않는다.

데이터는 **읽기→정규화→정제→판정→순위/집계→표시**로 흐른다. 7 STATE와 별개이고 파일 6개를 강제하지 않는다.
정상 대표·격리 원본·중복 원본이 배타적일 때만 같은 파일의 원본 레코드 보존식을 쓴다. 경고를 정상 건수에 다시 더하지 않는다.

## 독립 work 후보 도구

```sh
python fde/kit/preflight.py --port 8000
python fde/kit/init_work.py
python fde/kit/evaluate.py
python fde/kit/promote.py --report latest
python fde/kit/bundle.py
python fde/kit/status.py
python fde/kit/status.py --intent   # Q→D→REQ→commit 기록 빈칸
```

빈 checks는 거절된다. 지정 src/가 있는 앱에는 자체 검사·전달 구조를 유지한다. work 밖 파일은 ZIP에 자동 포함되지 않는다.

## 180분 집중 세션 예시 — 실제 일정이 우선

0~15 입력·질문 / 15~30 합의·검사 계획 / 30~45 최소 실행 / 45~115 P0 / 115~140 사용자 흐름·위험 / 140~155 회귀·설명 / 155~170 fresh run·인계 / 170~180 전달 확인.
80분 구조 동결·140분 새 기능 동결·170분 최종 전달 준비는 참고 경계다. 안전·핵심 오류·확인된 필수 수정은 이유를 남기고 최소 변경·재검증한다. 선택 기능·장식부터 줄인다.
같은 실패 3회면 원인·작은 재현·대안 2개를 확인한다. 긴 작업은 handoff의 다음 3행동으로 재개한다. 전달 규칙·허용 도구·네트워크·승인 절차는 실제 프로젝트를 따른다.
