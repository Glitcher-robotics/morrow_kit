# GIT — 과제 폴더에서 쓰는 최소 명령

목적: 첫 commit을 **과제 원본**으로 남기고, 이후 REQ 단위로 쌓아 "무엇을 왜 바꿨나"를 diff·log로 보여 준다. 실수했을 때 되돌리는 보험이기도 하다.
모든 명령은 **과제 폴더 안**에서 실행한다. 전역 설정(`--global`)은 바꾸지 않는다. 원격 push·외부 전송은 과제 규칙이 허용할 때만 한다.

## 1. Git 루트 확인 (0~2분)
```sh
cd <과제 폴더>
git rev-parse --show-toplevel
```
| 출력 | 뜻 | 할 일 |
|---|---|---|
| `<과제 폴더>` 경로 | 과제 폴더가 Git 루트 | `git log --oneline`으로 이력만 확인 |
| `fatal: not a git repository` | Git 없음 | 2번으로 |
| **상위 폴더** 경로 | 상위 저장소에 묶임 | 그대로 commit하면 상위에 섞인다. 과제 폴더에서 `git init`으로 따로 만든다 |

## 2. 원본 그대로 첫 commit
키트 설치·코드 수정 **전에** 한다. 그래야 이후 diff가 내가 바꾼 것만 보여 준다.

**빠른 길:** `python3 /tmp/morrow_kit/install.py --target . --start` 한 줄이 아래 2·3번(.gitignore, init commit, 키트 설치 commit)을 모두 한다. 아래는 단계별로 할 때.

**과제 폴더가 홈(~)이면 먼저 .gitignore.** `ls -a`에 `.bashrc`·`.config`·`.codex`가 보이면 `git add -A`가 셸 설정과 Codex 로그인 정보까지 담는다.
```sh
python3 /tmp/morrow_kit/install.py --target . --gitignore-only   # 기존 줄은 두고 빠진 줄만 추가
git status --short --ignored | head   # 숨김 설정이 !! (무시)로, 과제 파일이 ?? 로 보여야 한다
```
키트를 받을 수 없으면 직접 쓴다: `printf '.codex/\n.config/\n.cache/\n.npm/\n.local/\n.bash*\n.profile\n.sudo_as_admin_successful\nnode_modules/\n__pycache__/\n' >> .gitignore`

```sh
git init
git add -A
git commit -m "init: 과제 원본"
```
`Author identity unknown`이 나오면 **이 저장소에만** 설정하고 commit을 다시 실행한다.
```sh
git config user.name "이름"
git config user.email "me@example.com"
```
이미 고친 뒤에 시작했다면 사실대로 남긴다: `git commit -m "init: 작업 중 스냅샷 (원본 아님)"`.

확인:
```sh
git log --oneline      # a1b2c3d init: 과제 원본
git status --short     # 비어 있으면 깨끗하다
```

## 3. 키트 설치 commit
```sh
python3 /tmp/morrow_kit/install.py --target .   # .gitignore 보강도 다시 확인한다
python3 fde/kit/init_work.py
git add -A
git commit -m "chore: morrow_kit 설치"
```

## 4. 작업 중 commit — 메시지 규칙
| 시점 | 메시지 예 |
|---|---|
| GATE1 합의 후 | `GATE1: problem/decisions/requirements 합의` |
| 첫 E2E 성공 | `REQ-001: E2E v0` |
| REQ 테스트 통과마다 | `REQ-005: METHOD ④ 조치 판정 (D1)` |
| 결정이 바뀌어 반영 | `REQ-015: METHOD ③ 중복 기준 meas_id (D9, D5 대체)` |
| 문서 | `docs: README_RUN 실행·한계` |
| fresh run 후 | `GATE3: fresh run passed` |

```sh
git status --short             # 무엇이 바뀌었나
git diff --stat                # 범위가 맡긴 REQ·단계 밖으로 넘었나
git add src/spc.js tests/spc.test.js fde/work/requirements.md
git commit -m "REQ-005: METHOD ④ 조치 판정 (D1)"
```
`git commit -am "..."`은 이미 추적 중인 파일만 담는다. 새 파일은 먼저 `git add <파일>`.
여러 REQ를 한 commit에 몰지 않는다. 마지막에 squash하거나 이력을 지우지 않는다.

## 5. 되돌리기 — 같은 REQ에서 2번 연속 나아지지 않을 때
```sh
git diff                        # 무엇을 버리게 되는지 먼저 본다
git restore src/spc.js          # 파일 하나를 마지막 commit 상태로
git restore .                   # commit 안 한 변경 전부 버리기 (되돌릴 수 없음)
git log --oneline               # 돌아갈 commit 확인
git revert <commit>             # 이미 commit한 변경을 새 commit으로 취소 (이력 보존)
```
`git reset --hard`·강제 push는 이력을 지우므로 쓰지 않는다.

## 6. 설명·서술형 준비
```sh
git log --oneline              # 내가 무엇을 어떤 순서로 정했나
git show --stat <commit>       # 그 commit에서 바뀐 파일
git diff <init commit> --stat  # 원본 대비 전체 변경 범위
```

## 7. 원격 저장소 (과제가 허용할 때만)
```sh
git remote -v                  # 이미 연결된 원격 확인
git push origin <브랜치>
```
시험 환경에서 push·외부 전송이 막혀 있으면 시도하지 않는다. 로컬 이력만으로 충분하다.
