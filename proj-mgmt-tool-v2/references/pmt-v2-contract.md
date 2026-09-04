# PMT v2 계약

`scripts/pmt.py`는 Python 3.8+ 표준 라이브러리만 쓴다. 전역 옵션은 `--docs-root`, `--session`, `--project`이고 환경 변수 `PMT_DOCS_ROOT`, `PMT_SESSION`도 지원한다.

## 저장 트리

```text
<docs-root>/
├── projects/projects.md
├── projects/<slug>/
│   ├── project.md
│   ├── RESUME.md
│   ├── facts.md  decisions.md  backlog.md
│   ├── decisions/D<n>.md
│   ├── archive/{facts,decisions,backlog}.md
│   ├── canceled/<class>__<stem>.md
│   ├── .locks/
│   ├── resources/{originals,derived,evidence}/
│   ├── _default/Work1.md  Work1-1.md
│   └── <classification>/...
├── worklog/<slug>__<class>__<item>.md
├── worklog/done/
├── times/YYYY-MM.md
└── .repo-locks/
```

생성물은 `RESUME.md`와 `projects.md`뿐이다. 나머지는 원본 또는 lock이다. v1 이관을 적용할 때만 프로젝트 안에 `.migration-v1-backup/`을 만든다.

## 문서 형식

Item frontmatter 핵심은 `type`, `kind`, `id`, `parent`, `status`, `updated`, `blocked_by`, `base_commit`, `verify`다. 본문 절은 기본 내용·범위·완료 기준·재개·검증·결과·증거 순이다.

`## 재개`는 `note`가 다음 여섯 키를 통째로 갱신한다.

```text
- 갱신: <시각> (session <id>)
- 한 것: <내용>
- 다음: <내용>
- 주의: <내용 또는 없음>
- 대기: <내용 또는 없음>
- 검증 못 한 것: <내용 또는 없음>
```

각 값은 400자 이하다. stale lock 회수 시 비정상 종료 추정 문구를 이 절에 추가한다.

`## 검증` 표:

```text
| at | commit | criteria | command | exit | limits |
|---|---|---|---|---|---|
| <시각> | <HEAD 또는 -> | <완료 기준 해시> | <명령> | <종료 코드> | <한계> |
```

`criteria`는 완료 기준 절의 SHA-1 앞 8자리다. Git 저장소 경로가 없으면 commit은 `-`다. `end --done --unverified`는 command·exit를 `-`, limits를 `미검증: <사유>`로 기록한다.

`decisions.md`는 `| ID | 상태 | 생성 | 제목 | 내용 | 대체 |` 6열이다. 상태는 `승인|대체|폐기`다. 내용 합계가 300자를 넘으면 행에는 첫 문장과 `decisions/D<n>.md` 경로만 두고, 상세 파일에 문맥·결정·대안·결과와 `supersedes`, `decider`를 기록한다.

`facts.md` 상태는 `Active|Closed`, `backlog.md` 상태는 `Active|Done|Dropped`다. 목록 행은 삭제하지 않고 `set --status`로 전이한다.

## 명령

| 명령 | 인자와 핵심 동작 |
|---|---|
| `new` | `<slug> --goal <text> [--label <x>]`; 프로젝트와 기본 트리 생성 |
| `resume` | `<slug>`; 목록 자동 압축 뒤 RESUME 재생성·출력 |
| `add` | `work|item|fact|backlog`; ID를 발급하며 RESUME는 즉시 갱신하지 않음 |
| `decide` | `<title> --context --decision [--alt --result --supersedes --decider]`; 승인 결정 기록 |
| `set` | `<ID> --status [--why]` 또는 `<item-id> --blocked-by|--unblock` |
| `start` | `<item-id> [--note] [--delegate] [--worktree]`; 점유·상태 승격·기준 commit 기록 |
| `note` | `<item-id> --did --next [--watch --wait --unverified]`; 재개·heartbeat 갱신 |
| `verify` | `<item-id> --cmd (--exit N|--run) [--cwd --limit]`; 검증 행·worklog 기록 |
| `end` | Item 완료·중지·실패·취소, `--all --pause`, 프로젝트 `--done --confirm` |
| `lock` | `acquire|beat|release|list|reap [id] [--repo <path>]...`; Item·저장소 lock 관리 |
| `find` | `[query] [--chain D<n>]`; 원본·archive·worklog 검색 또는 결정 계보 출력 |
| `doctor` | `[--scope <classification>]`; 무결성 fail·warn 출력 |
| `sync` | 숨김 명령. RESUME와 projects 색인을 재생성 |
| `compact` | 숨김 명령. 8,000자 초과 목록의 종료 상태 행을 archive로 이동 |

`start --delegate`는 범위·완료 기준·frontmatter `verify`가 모두 있어야 한다. `end --done`은 결과와 현재 HEAD·완료 기준에 맞는 성공 검증이 필요하며, 없으면 `--unverified <사유>`가 필요하다. 완료 기준이 비어 있어도 미검증 사유가 필요하다. 자식이 Planned 또는 In Progress면 완료할 수 없다.

## 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | 성공. `verify --run`의 대상 명령 실패도 기록 성공이면 0 |
| 1 | lock 실패 또는 doctor fail |
| 2 | 필수 입력·게이트·상태 전이 위반 |
| 3 | 처리하지 못한 예외 |

## RESUME 예산

전체는 4,500자 이하다. 요약은 Goal과 지표 2줄, 점유는 3행, 이어받을 In Progress Item은 3건·재개 블록 400자, 외부 대기는 3건, 착수 가능은 5건, 승인 결정과 Active 사실은 각각 최근 3건·행당 150자, 최근 결과는 2건·결과 첫 줄 120자, 주의는 fail 우선 3건이다.

4,500자를 넘으면 같은 데이터를 순서대로 다시 렌더한다.

1. 재개 블록 400자에서 200자로 축소
2. 결정·사실 3건에서 2건으로 축소
3. 착수 가능 5건에서 3건으로 축소

마지막 줄의 `축소 적용:` 값이 적용 단계를 나타낸다. 전체 문서를 임의 위치에서 자르지 않는다.

## 세션과 체크포인트

`--session`과 `PMT_SESSION`이 없으면 Linux `/proc/<ppid>/stat`에서 조부모 PID를 읽어 `pid-<gppid>`를 만든다. 실패하거나 조부모 PID가 0·1(sandbox 등 격리 실행기)이면 `session-<ppid>`를 쓰고 lock 존재만으로 소유를 완화하며 경고한다. 이런 환경(Codex sandbox 실측: 조부모 0)에서는 `PMT_SESSION`을 고정값으로 설정한다. 같은 실행기 아래 서브에이전트는 세션 ID가 같으므로 PMT 문서와 lock을 직접 다루지 않는다.

`add` 결과는 다음 `start`, `note`, `end`, `resume`의 sync에서 RESUME에 반영된다. 내 Item heartbeat가 20분을 넘으면 모든 명령이 stderr 첫 줄에 체크포인트 경고를 낸다. 다른 Item의 heartbeat가 30분을 넘으면 `start` 전이 게이트가 막는다. 대상 lock이 30분을 넘으면 `start`가 그 한 건을 회수하고 재개 절에 비정상 종료 추정 문구를 남긴다.

## doctor

Fail: 필수 frontmatter 누락, ID와 경로 불일치, parent 누락, 존재하지 않는 내부 `blocked_by`, Item 깊이 초과, test Item의 자식, 부모 순환, 목록 ID 중복, `next_id` 역행, facts·decisions·backlog의 허용 밖 상태.

Warn: 24시간 넘었거나 없는 In Progress Item 재개 블록, stale lock, `handoff-*.md`, `RESUME.md` 누락. 읽기 실패는 stderr에 경고한다. 출력 요약은 `doctor: fail N, warn N` 형식이다.

## 원격 경계

엔진에는 Linear·업무보고 같은 원격 클라이언트와 자격 증명이 없다. 원격 쓰기와 push·배포는 사용자 명시 요청을 받은 에이전트 커넥터의 책임이다.
