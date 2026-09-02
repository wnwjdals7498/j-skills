# PMT v2 CLI 계약

`scripts/pmt.py`는 Python 3.8+ 표준 라이브러리만 사용한다. 전역 옵션은 `--docs-root`, `--session`, `--project`이며 환경 변수 `PMT_DOCS_ROOT`, `PMT_SESSION`을 같은 용도로 쓸 수 있다. 프로젝트 폴더 내부에서는 slug를 자동 감지한다.

## 저장 구조

```text
<docs-root>/
├── projects/projects.md
├── projects/<slug>/
│   ├── project.md
│   ├── RESUME.md  graph.md  graph.json  Doing.md  index.md
│   ├── facts.md  decisions.md  backlog.md
│   ├── archive/  .locks/  resources/{originals,derived,evidence}/
│   ├── _default/Work1.md  _default/Work1-1.md
│   └── <classification>/...
├── worklog/done/
└── times/YYYY-MM.md
```

Classification 기본값은 `_default`다. 활성 Work가 6개를 넘으면 `sync`가 분류를 제안하지만 자동 이동하지 않는다. Item `kind`는 `job`, `view`, `test`, `hotfix`; 깊이는 최대 3이고 `test` 자식은 금지한다.

## 생성·추가

| 명령 | 핵심 동작 |
|---|---|
| `new <slug> --goal <text> [--label <x>...]` | 프로젝트·목록·resources·`_default` 생성, `projects.md`와 생성물 갱신 |
| `resume <slug>` | `sync` 후 `RESUME.md` 출력 |
| `add work <title> [--class <name>] [--goal <text>]` | 다음 `WorkN` 발급 |
| `add item <parent-id> <title> [--kind <kind>] [--verify <command>]` | 부모 체인의 다음 순번 Item 발급 |
| `add fact <text> [--ref <id>]` | `F<n>` 행 발급 |
| `add decision <text> --from <a> --to <b> --why <reason> [--decider <name>]` | `D<n>` 행 발급 |
| `add backlog <text> --kind req|todo|plan|issue|bug` | `B<n>` 행 발급 |

## 실행 수명주기

`start <id> [--note <text>] [--delegate] [--worktree <path>]`는 원자 lock, 상태 승격, worklog 착수, `sync`, 실행 컨텍스트 출력을 묶는다. 중간 실패 시 문서 변경과 새 worklog를 되돌리고 lock을 해제한다.

`note <id> --did <text> --next <text> [--watch <text>] [--wait <text>] [--unverified <text>]`는 `## 재개`를 덮어쓰고 heartbeat와 worklog 체크포인트를 갱신한다.

`end` 모드:

- `--done --result <text> [--evidence <path>...]`: 결과·증거 기록, Done, 부모 자동 Done, worklog 완료 이동, lock 해제, sync, scoped doctor, times append.
- `--pause [--did <text> --next <text>]`: 재개 블록이 60분보다 낡거나 비었으면 보강 없이는 종료 코드 2. 상태는 In Progress 유지.
- `--fail --cause <text> --fix <text>`: 실패와 처방을 재개·worklog에 기록하고 lock 해제.
- `--skip --reason <text>`: 자식 없는 단위를 Canceled로 바꾸고 `canceled/`로 이동, 활성 관계를 해소한다. 자식이 있으면 먼저 자식을 완료하거나 skip해야 한다.
- `end --all --pause`: 현재 session이 가진 모든 Item에 pause 적용.

종료 코드: 성공 0, lock 또는 검색 실패 1, 필수 입력·위임 게이트 실패 2, 무결성 fail 1.

## 생성물과 조회

- `sync`: `graph.md`, `graph.json`, `Doing.md`, `RESUME.md`, `index.md`, `projects.md`를 다시 만든다. `__index` lock으로 직렬화하며 짧은 동시 실행은 제한 시간 안에서 대기한다.
- `graph roots|blocked|children|parents|ancestors|descendants|orphans [id]`: 원본 전체 대신 계보와 차단 관계를 조회한다.
- `find <ID-or-keyword>`: 활성 목록, `archive/`, Work·Item, worklog를 검색한다.
- `compact`: 활성 목록이 8000자를 넘으면 Done·Canceled 행을 같은 이름의 `archive/` 문서로 옮긴다. ID와 원문을 보존한다.

`RESUME.md`는 30초 요약, 점유 중, In Progress 재개 블록, 외부 대기, 착수 가능 최대 10개, 최근 결정·사실, 최근 worklog 결과, doctor 경고 순서다. 6000자를 넘으면 긴 항목 본문을 파일 링크로 줄인다.

## Lock

`lock acquire|beat|release|list|reap <id>`는 프로젝트 `.locks/`의 디렉터리 생성 원자성을 사용한다. stale 기준은 30분이다. `reap`은 마지막 `note` 위에 비정상 종료 추정 문구를 넣고 회수 이력을 남긴다.

저장소 병합 lock은 `--repo <absolute-or-resolved-path>`를 사용하며 `<docs-root>/.repo-locks/`에 분리한다. 저장소가 여러 개면 정규화 절대 경로 오름차순으로 획득한다.

## Doctor

Fail: 필수 frontmatter, id와 경로, parent 존재, 활성 관계 대상, 깊이·test 자식, 부모 순환, 목록 ID·`next_id`.

Warn: stale lock, 24시간 넘은 In Progress 재개 블록, `handoff-*.md`, resources·생성물·자체 완결성 부족.

## 원격 경계와 close

PMT 로컬 엔진은 특정 Linear 클라이언트나 자격 증명을 내장하지 않는다. 에이전트가 사용 가능한 공식 커넥터로 사용자 명시 요청 시 upsert하고 반환 ID를 frontmatter에 기록한다. `close <slug> --confirm [--remote-synced]`는 사용자 허가를 나타내는 `--confirm`이 필수다. 원격 대상이 구성됐는데 `--remote-synced`가 없으면 종료하지 않는다. push·배포는 수행하지 않는다.
