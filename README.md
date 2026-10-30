# morrow_kit

로컬 데이터 프로젝트를 **질문 → 합의 → 최소 실행 → 검증 → 전달**로 이어 가는 작은 작업 도구 모음입니다.
Python 3.10 이상과 표준 라이브러리만 사용합니다. 패키지 설치·외부 API가 필요하지 않습니다.

## 보는 순서

1. **이 README**: 목적과 설치 방법을 확인합니다.
2. [QUICKCARD](docs/QUICKCARD.md): 전체 작업 순서와 체크 항목을 한 번 봅니다.
3. [METHOD](docs/METHOD.md): 데이터를 처리하는 6단계와 합격 기준을 이해합니다.
4. [STAGE_PROMPTS](docs/STAGE_PROMPTS.md): 현재 STATE의 산출물과 필요한 프롬프트 **하나만** 골라 씁니다.
5. [RUNBOOK](docs/RUNBOOK.md): 검사·정상본 보관·번들 명령이 필요할 때 엽니다.

[INDEX](INDEX.md)는 파일을 빨리 찾는 목차입니다. 문서 전부를 AI에 한꺼번에 읽히지 않습니다.

## 두 가지 단계

| 구분 | 무엇을 설명하나 |
|---|---|
| 7 STATE | 작업 진행: DISCOVERY → CONTRACT → SCAFFOLD → E2E_V0 → VERIFY → ACCEPT → SUBMIT |
| 6 METHOD | 데이터 처리: 읽기 → 정규화 → 정제 → 판정 → 순위/집계 → 표시 |

예를 들어 `STATE: VERIFY`, `METHOD: ④ 판정`이라고 기록할 수 있습니다. 시간이 됐다는 이유로 승인·완료 상태를 만들지 않습니다.

## 시작하기

기존 프로젝트 폴더 `my-project`가 있고 그 옆에 내려받는 예입니다.

```sh
git clone https://github.com/Glitcher-robotics/morrow_kit.git
python morrow_kit/install.py --target ./my-project
cd my-project
python fde/kit/init_work.py
python fde/kit/preflight.py --port 3000
```

설치는 프로젝트 README와 기존 work/champion/artifacts를 보존합니다. 재설치는 정적 도구·템플릿·문서를 갱신하고, 초기화는 **없는 작업 파일만** 만듭니다.
프로젝트의 지정 `src/`·실행 방법·산출물 위치는 유지합니다. 설치가 불필요하면 문서와 필요한 함수만 참고해도 됩니다.

## 설치한 뒤 할 일

1. `fde/work/interview.md`에 실제 질문·답과 Unknown을 기록합니다. 놓치기 쉬운 질문 예시가 들어 있습니다.
2. `problem.md`에서 README의 설명과 실제 업무 문제·데이터·성공 기준을 대조합니다.
3. 사람이 범위를 확인한 뒤 `requirements.md`와 `skeleton.md`에 합격 기준과 처리 계약을 연결합니다.
4. 실제 입력 하나에서 출력 하나를 만들고, REQ별 검사를 준비합니다.
5. 독립 work 후보라면 `checks.json`을 채운 뒤 도구를 실행합니다. **빈 검사로는 평가되지 않습니다.**

```sh
python fde/kit/evaluate.py
python fde/kit/promote.py --report latest
python fde/kit/bundle.py
python fde/kit/status.py
python fde/kit/status.py --intent   # Q→D→REQ→commit 기록 빈칸
```

`champion`은 검사한 정상 후보의 별도 보관본입니다. bundle은 그 후보를 ZIP으로 묶습니다. **work 밖의 src·데이터·부품은 자동 포함되지 않습니다.** 기존 앱을 그대로 쓰는 프로젝트는 자체 검사·전달 구조를 따르세요.

## 폴더 역할

| 위치 | 내용 |
|---|---|
| `docs/` | 방법·현재 상태별 지시·체크리스트·명령 설명 |
| `fde/templates/` | 사람이 확인하며 채울 빈 양식과 질문 예시 |
| `fde/reusable/` | CSV/JSON·검증·집계·내보내기·작은 HTTP 화면 부품 |
| `fde/kit/` | 준비·초기화·검사·승격·번들·상태 도구 |
| `tests/` | 도구 자체의 합성 입력 검사. 프로젝트별 완성 풀이가 아님 |

`fde/work/`, `champion/`, `artifacts/`는 설치·실행 때 만들어집니다. **이 도구 저장소**에서는 Git에서 제외하지만 설치 대상의 `.gitignore`는 자동 변경하지 않습니다. 대상 프로젝트의 소스·테스트·필수 기록은 필요한 대로 추적하고, 실제 데이터·비밀값·실행 로그의 추적 제외는 별도로 확인하세요.

## 확인할 한계

- 예시는 질문 소재이며 업무 정책·기대 정답이 아닙니다. 실제 담당자와 데이터로 확인합니다.
- `coverage/score`는 등록한 REQ의 통과 비율이며 코드 커버리지·서비스 품질 인증이 아닙니다.
- 상태 도구는 180분 작업 세션의 예시 타이머입니다. 실제 일정·마감과 사람이 확인한 근거가 우선입니다.
- 웹 부품은 로컬 확인용이며 인증·권한·영속 저장을 갖춘 운영 서비스가 아닙니다.
- 현재 환경의 도구·데이터·공개/전달 규칙을 먼저 확인하고 허용된 범위에서 사용합니다.

도구 자체 검사: `python -m unittest discover -s tests -v`.
