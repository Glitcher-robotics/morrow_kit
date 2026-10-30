# RUNBOOK — 설치·검증·정상본·번들

Python 3.10 이상, 표준 라이브러리만 사용한다. Git·Node는 preflight가 확인하는 선택 도구다. `python` 명령이 다른 인터프리터를 가리키면 설치된 Python 실행 파일 경로를 사용한다.

## 1. 설치와 초기화

기존 프로젝트 폴더를 대상으로 실행한다.

```sh
python morrow_kit/install.py --target ./my-project
cd my-project
python fde/kit/init_work.py
python fde/kit/preflight.py --port 3000
```

- 설치는 대상 README·기존 work/champion/artifacts를 보존한다. 정적 도구·템플릿·fde/docs는 갱신한다.
- AGENTS 관리 블록은 한 번만 추가한다. 기존 블록을 갱신하려면 `--refresh-agents`를 사용한다. 원본은 fde/artifacts에 백업되고 블록 밖 내용은 보존된다.
- init_work는 없는 양식·session.json·빈 checks.json만 만든다. 사람이 작성한 내용은 덮어쓰지 않는다.
- session.json의 started_at은 첫 초기화 시각이다. 실제 작업 시작과 다르면 실제 시작 시각을 시간대 포함 ISO 8601로 기록한다. 허위 시각을 만들지 않는다.
- preflight는 사용 가능한 포트를 확인하며 서버를 계속 켜 두지는 않는다. 실제 앱의 호스트·포트·경로로 별도 실행한다.
- 설치 전 기존 fde가 이 도구와 무관한 폴더라면 충돌을 검토한다. 도구를 억지로 설치하지 않아도 된다.
- 대상 `.gitignore`는 자동 생성·갱신하지 않는다. 실제 데이터·비밀값·세션/평가 로그·중복 보관본의 추적 여부를 별도로 검토한다. 구현 소스·테스트·필수 기록까지 무조건 제외하지 않고, 이미 추적한 파일이 ignore 규칙만으로 추적 해제된다고 가정하지 않는다.

interview의 질문/답, problem의 문제/범위, requirements의 합격 기준을 실제 사람과 확인하고 skeleton의 처리 계약에 연결한다. 상태 프롬프트는 STAGE_PROMPTS의 현재 항목만 선택한다.

## 2. checks.json — 실행 명령 목록

아래 경로는 실제 프로젝트 검사로 바꾼다. 두 파일을 먼저 작성하지 않고 이 설정만 복사하면 실패한다.

```json
{
  "requirements": [
    {
      "id": "REQ-001",
      "priority": "P0",
      "acceptance": "고정 입력에서 사람이 정한 기대 결과와 일치",
      "command": ["{python}", "-m", "unittest", "discover", "-s", "fde/work/tests", "-p", "test_requirement.py", "-v"]
    }
  ],
  "regression": [
    ["{python}", "-m", "unittest", "discover", "-s", "fde/work/tests", "-p", "test_existing.py", "-v"]
  ]
}
```

명령은 **프로젝트 루트**에서 argv 배열로 실행한다. `{python}`은 현재 인터프리터로 치환된다. 셸 연산자·리디렉션을 넣지 않는다. 빈 requirements·P0 없음·회귀 없음은 거절한다. 빈 테스트 모음이나 단순 exit 0가 실제 합격 검사를 대신하지 않도록 사람이 내용과 기대값을 확인한다.

## 3. 검사와 정상본 보관

```sh
python fde/kit/evaluate.py
python fde/kit/promote.py --report latest
python fde/kit/status.py
python fde/kit/status.py --intent   # Q→D→REQ→commit 기록 빈칸
```

evaluate는 REQ별 명령·출력·exit code·timeout·소요 시간·work/프로젝트 파일 해시를 fde/artifacts에 기록한다. 기본 timeout은 명령당 60초이며 `--timeout 120`으로 조정할 수 있다.

promote는 P0·회귀 통과, 안정된 최신 소스, 기존 정상본 이상의 REQ 통과 비율을 확인하고 work를 champion으로 보관한다. P1/P2 실패는 보고서에서 사라지지 않는다. 이후 source나 입력이 달라지면 재검사한다. 정확한 보고서를 선택하려면 `--report`에 출력된 평가 파일의 실제 경로를 준다.

coverage/score는 등록한 REQ의 통과 비율이다. 검사 품질·고객 수용·프로덕션 안전을 자동 판단하지 않는다. 상태 전환과 GATE는 사람이 기록한다. status는 180분 예시 예산과 최신 증거 여부를 보여 주는 참고 도구다.

## 4. 번들과 fresh run

```sh
python fde/kit/bundle.py
```

ZIP에는 champion 안의 실행 파일·테스트·필요 데이터만 담긴다. session.json·champion.json·캐시·비밀 형태 파일은 제외한다. 파일명 정렬·고정 시각·무압축으로 같은 입력 바이트의 SHA256을 재현한다.

work 밖의 src·설정·데이터·fde/reusable은 자동 포함되지 않는다. 독립 후보는 실행에 필요한 부품을 work에 함께 준비하고 검사해야 한다. 기존 앱은 원래 프로젝트 구조로 실행·전달한다.

새 폴더에 번들을 풀고 새 프로세스에서 실제 입력과 테스트를 실행한다. 동작 중인 서버는 종료 코드를 기다리지 않고 준비 상태·HTTP 응답을 확인한다. 문서와 요구가 다르면 원인을 확인해 최소 수정·관련 재검사를 한다.

## 5. 재개와 전달 확인

handoff에 목표·현재 STATE/METHOD·완료 근거·실패/Unknown·명령·다음 3행동을 짧게 남긴다. 실제 전달 대상·경로·필수 파일·실행법·사용자 확인으로 완료를 판단한다. Git이 깨끗하거나 ZIP이 존재한다는 사실만으로 전달 완료를 기록하지 않는다.

## 6. 범용 부품의 제한

- io.py는 CSV/JSON 파싱, validate.py는 지정 스키마 검증이다. validate의 errors는 필드 오류 목록이라 같은 행에 오류가 여러 개일 수 있다. errors 길이를 곧바로 격리 레코드 수로 쓰지 않는다.
- aggregate.py의 합계·정렬은 명시한 키로만 수행한다. 중복·분모·중요도 같은 업무 정책은 따로 합의한다.
- export.py는 결정론적 저장 부품이며 CSV 수식 방어를 자동 적용하지 않는다. 스프레드시트로 열 입력이면 프로젝트에서 적절한 출력 방어를 추가한다.
- webui.py는 로컬 업로드/표/상세의 출발점이다. 인증·접근 통제·운영 보안이 없으며 네트워크에 공개할 완성 서비스가 아니다. 기본 호스트는 127.0.0.1이다. 0.0.0.0은 프로젝트가 다른 인터페이스 연결을 요구할 때만 선택한다.

도구 자체 검사는 저장소 루트에서 `python -m unittest discover -s tests -v`로 실행한다. 임시 파일·로컬 소켓 사용이 제한된 환경에서는 오류 원인을 구분해 기록한다.
