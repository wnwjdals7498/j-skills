# proj-mgmt-tool v2 설계 지침서

작성 2026-09-02. 대상 독자: 다른 PC에서 새 프로젝트 관리 스킬을 처음부터 만드는 사람 또는 AI 에이전트. 이 문서만 읽고 v2를 설계·구현할 수 있도록 v1의 실측 진단, 유지할 것, 바꿀 것, 엔진 명령 규격, 수용 기준을 한 곳에 담았다. v1 원본 파일(`~/.claude/skills/proj-mgmt-tool/`)이 없는 환경을 전제한다.

용어. 스킬(skill) = AI 에이전트가 특정 작업을 할 때 읽는 절차 문서 묶음. frontmatter = Markdown 문서 맨 위 `---` 사이의 기계용 메타데이터. lock(점유) = 한 항목을 한 세션만 만지도록 잡는 표식. heartbeat(생존 신호) = 점유가 살아 있음을 주기적으로 갱신하는 시각. stale(만료) = 생존 신호가 오래돼 죽은 것으로 간주되는 점유. 콜드스타트(cold start) = 이전 맥락이 전혀 없는 새 세션이 작업을 이어받는 상황. upsert = 있으면 갱신, 없으면 생성.

---

## 0. 한 줄 요약

v1은 구조는 좋았고 실행이 지켜지지 않았다. 규칙 23개를 문서에 적고 사람·AI가 순서대로 지키게 했더니, 재개 정보는 9건 중 2건만 남았고 금지한 인계 문서가 4개 생겼다. v2는 **규칙을 줄이고 절차를 명령에 묶는다.** 단위 시작 `start`, 체크포인트 `note`, 단위 종료 `end` 세 명령이 lock·상태·기록·인계·검증을 한 번에 처리한다. 콜드스타트는 생성물 `RESUME.md` 하나만 읽고 투입된다.

---

## 1. v1 실측 진단 (2026-09-02, 프로젝트 13개·md 1,417개 기준)

### 1.1 유지할 강점 (실제로 작동한 것)

| 강점 | 근거 |
|---|---|
| 로컬 원천 (`~/docs/projects/<slug>/`) | 13개 프로젝트가 한 곳에 누적. Linear 없이도 조회 가능 |
| 그래프 생성물 (`graph.md`) | 차단 체인·착수 가능 루트·외부 대기를 1,845바이트로 요약. 원본 통독 없이 상태 파악 가능 |
| 원자적 lock + `Doing.md` | 병렬 세션 충돌 0건. stale 회수 이력도 남음 (2026-08-27 api/Work6 회수) |
| 사실·결정 목록 (`Information.md`·`histories.md`) | 각 34행·47행 누적. 재조사 방지 효과 실재 |
| 증거 기반 완료·부모 자동 Done | Work 완료가 증거 경로와 함께 남음. 보고서 원천으로 재사용됨 |
| `doctor` 무결성 검사 | 16 pass·1 warn·0 fail. 깨진 링크·고아 노드 조기 발견 |
| worklog 전역 append + 커밋 trailer `PMT:`/`PMT-Path:` | 커밋에서 Item, Item에서 과정 기록으로 역추적 가능 |
| Linear는 종료 시 upsert | 진행 중 원격 쓰기 없음. 중복 이슈 0건 |

### 1.2 실패한 규칙 (문서에는 있으나 지켜지지 않은 것)

| 규칙 | 실측 | 원인 진단 |
|---|---|---|
| In Progress 항목은 `## 진행 메모` 3줄로 인계 | In Progress Work·Item 9건 중 메모 있음 **2건** (22%) | 세션 종료 절차 5단계의 1번인데, 세션은 컨텍스트 소진·사용자 이탈로 절차 없이 끝남. 종료 시점에만 쓰는 규칙은 비정상 종료에 무력 |
| `handoff-*.md` 생성 금지 | `~/docs/handoff-*.md` 3개(10·11·18KB) + `~/docs/worklog/2026-08-25-Work10-handoff.md`(19KB) | 3줄 메모로는 부족한 인계 정보(먼저 알아야 할 위험·사용자가 할 일·현재 상태 표)가 실제로 존재. 금지하니 체계 밖으로 나감 |
| worklog 파일명 `<slug>__<class>__<item>.md` + frontmatter 필수 | 활성 23개 중 파일명 위반 7개, frontmatter 없음 **16개** (70%) | 사람이 손으로 만들면 규격을 안 지킴. `rg components:` 조회 전제가 무너짐 |
| 목록 문서 20000자 상한, 초과 시 두 행 병합 | `Information.md` 19,947자 · `histories.md` 19,997자 | 상한에 붙여 놓고 계속 수동 병합 중. 병합은 정보 손실 + AI 작업량. 상한이 부담이 됐음 |
| `times/` 서사 금지, ID 목록만 | 2026-09-01 행에 경위 서술 포함 | 규칙만 있고 생성해 주는 도구 없음 |
| `projects.md` 수기 색인 | 프로젝트 디렉터리 13개 중 색인 행 9개 (미등재 4) | 수기 색인은 어긋난다. 생성물로 전환 대상 |
| 위임 전 `verify` 필수 | null 필드 16건 경고 상시 | 등록 시점에 알 수 없는 값을 요구. 경고가 상시화되어 무시됨 |

### 1.3 진단 결론

1. **강제되지 않는 규칙은 지켜지지 않는다.** 지켜진 규칙(lock·graph·doctor)은 전부 `pmt.py`가 대신 실행하는 것이고, 깨진 규칙(진행 메모·worklog 규격·times·상한)은 전부 사람·AI가 손으로 하는 것이다.
2. **인계 정보는 종료 시점이 아니라 작업 중에 쌓여야 한다.** 세션은 예고 없이 끝난다.
3. **인계 문서 수요는 실재한다.** 금지가 아니라 생성물로 흡수해야 한다.
4. **규칙 밀도가 위반을 만든다.** SKILL.md 23,486바이트 + 참조 문서 6개 60,000바이트. 계약 23개, 태그 11종, 목록 문서 7개, 부모 규칙 표, 문서별 상한 2종. 읽는 비용이 지키는 비용을 넘었다.

---

## 2. v2 설계 원칙 (불변식 8개)

v1 계약 23개를 아래 8개로 압축한다. 이 밖의 것은 "기본값"이며 위반이 아니다.

1. **로컬이 원천.** 모든 상태·이력은 `~/docs/projects/<slug>/`. 원격(Linear·업무보고)은 종료 또는 명시 요청 시 upsert.
2. **절차는 명령에 산다.** 사람·AI가 순서를 외우는 절차를 두지 않는다. `start`·`note`·`end` 세 명령이 lock·상태·worklog·재개 블록·sync·검증을 묶어 실행한다.
3. **인계는 상시 갱신, 읽기는 한 파일.** 작업 중 `note`로 재개 블록을 덮어쓰고, 엔진이 `RESUME.md`를 생성한다. 콜드스타트는 `RESUME.md`만 읽는다.
4. **완료는 증거 기반 자동.** Item은 증거로 Done. 자식 전부 Done이면 부모 자동 Done. Project만 사용자 허가.
5. **점유는 원자적.** 착수 전 lock, 실패 시 착수 금지. 저장소 병합 구간은 repo lock.
6. **그래프가 탐색 경로.** 계보·차단은 `graph` 질의. 원본 통독 금지.
7. **정보는 버리지 않고 옮긴다.** 글자 상한 초과 시 병합 대신 Done 행을 `archive/`로 이동. ID 보존.
8. **자체 완결.** Project·Work·Item 본문은 링크 없이 읽어도 범위·결정·완료 조건·결과를 알 수 있어야 한다.

---

## 3. 계층·문서 구조 (축소판)

### 3.1 계층

`Project → Classification(선택) → Work → Item`. 4계층 유지하되 Classification은 **선택**이다. 없으면 `_default/` 폴더가 자동 분류다. Work가 6개를 넘거나 사용자가 요청할 때만 분류를 만든다. Linear 대응은 v1과 같다(Project → Milestone → Issue → Sub-issue).

### 3.2 Item 단일화

v1의 파일 태그 4종(V·J·TE·HF)과 부모 규칙 표를 폐지한다. Item은 한 종류이고 frontmatter `kind`로 성격만 표시한다.

| kind | 뜻 | 규칙 |
|---|---|---|
| `job` | 구현 작업 (기본값) | 자식 허용 |
| `view` | 화면 | 자식 허용 |
| `test` | 검증 | 자식 금지 |
| `hotfix` | 긴급 수정 | 자식 허용 |

남는 규칙은 두 개다. Work 아래 깊이 최대 3, `test`는 자식 없음. 파일명 체인(`Work1-J1.md` → `Work1-1.md`, `Work1-1-2.md`)은 순번만 쓴다. kind는 본문 제목 `# [job] 제목`에 표시한다.

### 3.3 목록 문서 7개 → 3개

| v2 문서 | 흡수한 v1 태그 | 행 형식 |
|---|---|---|
| `facts.md` | IF (확인된 사실) | `\| ID \| 상태 \| 생성 \| 내용 \|` 유지. 반증 시 Canceled + 사유 |
| `decisions.md` | H (결정 이력) | 상태 Done 고정. 전→후·사유·결정자 |
| `backlog.md` | R·T·P·I·B | `\| ID \| kind \| 상태 \| 생성 \| 내용 \|`. kind = req·todo·plan·issue·bug. 하단 `## 점검 특징` 절(v1 Bugs.md 자산) 유지 |

ID는 문서별 연번(`F1`, `D1`, `B1`), `next_id`는 frontmatter. 파일 항목에서 행 참조는 `list_refs: [backlog.md#B3]` 유지.

### 3.4 상한과 archive

글자 상한은 **활성 행 기준 8000자**로 두고, 초과 시 `pmt compact`가 Done·Canceled 행을 `archive/<문서명>.md`로 이동한다. 병합·요약·수동 편집 없음. 조회는 `pmt find <ID>`가 archive까지 찾는다. 이것으로 v1의 "두 행 병합 반복" 절차가 사라진다.

### 3.5 생성물

| 생성물 | 내용 | v1 대비 |
|---|---|---|
| `RESUME.md` | 콜드스타트 진입 문서 (4절) | **신설** |
| `graph.md` · `graph.json` | 차단 체인·루트·외부 대기·고립 | 유지 |
| `Doing.md` | lock 현황·회수 이력 | 유지 |
| `index.md` | Work·Item 트리 + 분류 요약 | `works.md`+`classifications.md` 통합 |

### 3.6 디렉터리

```text
~/docs/
├── projects/
│   ├── projects.md                # slug 색인 (생성물로 전환. pmt new/close 가 갱신)
│   └── <slug>/
│       ├── project.md
│       ├── RESUME.md              # 생성물
│       ├── graph.md  graph.json  Doing.md  index.md   # 생성물
│       ├── facts.md  decisions.md  backlog.md         # 수기 원본
│       ├── archive/               # compact 이동분
│       ├── .locks/
│       ├── resources/{originals,derived,evidence}/
│       ├── _default/              # 분류 없을 때
│       │   ├── Work1.md
│       │   └── Work1-1.md
│       └── <classification>/      # 선택
├── worklog/                       # 전역 과정 기록 (start 가 생성, 규격 자동)
│   └── done/
└── times/YYYY-MM.md               # end 가 자동 append
```

---

## 4. 재개(resume) 설계 — 핵심

### 4.1 재개 블록 (Item·Work 본문)

`## 진행 메모` 3줄을 폐지하고 `## 재개` 블록으로 바꾼다. 줄 수 제한 없음. **덮어쓰기** 방식이라 항상 최신 상태 하나만 남는다.

```markdown
## 재개
- 갱신: 2026-09-02T14:20 (session f8004d64)
- 한 것: <완료된 부분. 커밋 SHA·변경 파일 포함>
- 다음: <바로 실행할 첫 행동 1개 + 그 뒤 순서>
- 주의: <먼저 알아야 할 위험. 건드리면 안 되는 것. 틀렸던 전제>
- 대기: <사용자·외부가 해야 할 일. 없으면 "없음">
- 검증 못 한 것: <있으면>
```

v1 `handoff-*.md` 4개의 공통 구조(30초 요약 / 먼저 알 것 / 현재 상태 / 사용자가 할 일)를 그대로 키로 옮긴 것이다. 인계 문서 수요를 체계 안으로 흡수한다.

### 4.2 갱신 시점 (규칙 아닌 명령)

- `pmt note <id> --did "..." --next "..." [--watch "..."] [--wait "..."]` 가 재개 블록을 덮어쓰고 heartbeat 갱신, worklog에 체크포인트 한 줄 append.
- `pmt end <id> --pause` 는 재개 블록이 60분 이상 낡았으면 갱신을 요구한다(입력 없으면 종료 거부, 종료 코드 2).
- lock reap(만료 회수) 시 엔진이 재개 블록 맨 위에 `- 비정상 종료 추정: 마지막 체크포인트 HH:MM, 이후 작업 미기록` 한 줄을 자동 삽입한다. 비정상 종료라도 마지막 note까지는 살아남는다.

### 4.3 RESUME.md 생성 규격

`pmt sync`가 매번 재생성한다. 상한 6000자, 넘치면 항목별 링크로 대체. 섹션 순서 고정.

```markdown
# RESUME — <slug>            생성 YYYY-MM-DDTHH:MM

## 30초 요약
- Goal: <project.md Goal 1줄>
- 활성 Work N · In Progress Item N · 점유 중 N · 외부 대기 N · 미정 필드 N

## 지금 점유 중 (Doing)
| 세션 | 대상 | 경과 | 메모 |

## 이어받을 항목 (In Progress, 재개 블록 최신순)
### <id> — <제목>
<재개 블록 원문 그대로>

## 외부 대기
- <id>: <waiting_on 내용>

## 착수 가능 (선행 없음, 최대 10)
- <id> (<kind> <status>) — <제목>

## 최근 결정 5 / 최근 사실 5
- D47 2026-09-01: ...
- F34 2026-09-01: ...

## 최근 worklog 결과 3
- <id> HH:MM — 변경 파일 n · 테스트 통과/실패 · 후속 영향: ...

## 주의 (doctor warn/fail 요약)
```

### 4.4 콜드스타트 읽기 순서

1. `pmt resume <slug>` (sync 후 RESUME.md 출력).
2. 잡을 Item 파일 1개.
3. 끝. 필요할 때만 `facts.md`·`decisions.md`를 `pmt find`로 검색.

v1은 필독 7개 문서(project·Doing·graph·Information·todos·histories·분류 색인)였다. v2는 1개 + Item 1개다.

### 4.5 v1 대비 "재개 가능성" 판정

v1은 구조상 가능했으나 실측 22%만 남았다. v2는 재개 블록 갱신이 `note`·`end`에 묶이고 비정상 종료도 마지막 체크포인트가 남으므로, 갱신 누락은 "note를 한 번도 안 부른 경우"로 한정된다. 10절 수용 기준의 콜드스타트 테스트로 검증한다.

---

## 5. 단위 시작·종료 절차 (세션 종료 절차 대체)

v1 세션 종료 5단계(진행 메모·histories·lock 해제·sync·doctor·times)를 **단위(Work·Item) 단위의 start/end**로 바꾼다. 세션 개념은 사라지고, 열린 단위를 닫으면 세션 종료다.

### 5.1 `pmt start <id> [--note "..."]`

한 명령이 아래를 순서대로 수행한다. 실패하면 앞 단계를 되돌린다.

1. lock acquire. 실패 시 종료 코드 1, 아무것도 안 함.
2. Item `status: In Progress`, `updated` 갱신. 부모 Work·Classification이 Planned면 In Progress로 승격.
3. worklog 파일 생성 (`~/docs/worklog/<slug>__<class>__<item>.md`, frontmatter 자동: title·status·issues·components·created). 이미 있으면 append.
4. worklog에 `## 착수 HH:MM` 엔트리 append (위임 단위·작업 디렉터리는 옵션으로 받음).
5. sync (graph·Doing·RESUME·index).
6. **출력**: Item 본문 `## 기본 내용`·`## 범위`·`## 완료 기준`·`## 재개` + 같은 components의 과거 worklog "후속 영향" 항목(grep 결과). 이 출력이 v1 "실행 컨텍스트 수집"을 대체한다.

### 5.2 `pmt note <id> --did ... --next ... [--watch ...] [--wait ...]`

재개 블록 덮어쓰기 + heartbeat + worklog 체크포인트 1줄. 30분 이상 걸릴 작업 직전, 의미 있는 중간 결과마다, 종료 직전에 호출한다. 호출 비용이 명령 1개라 지켜진다.

### 5.3 `pmt end <id> --done | --pause | --fail | --skip`

| 모드 | 하는 일 |
|---|---|
| `--done --result "..." [--evidence path]` | 재개 블록을 `## 결과`로 이관·삭제, `status: Done`, worklog `## 결과` 엔트리 + `done/` 이동, 부모 자동 Done 전파, lock release, sync, scoped doctor(해당 분류만), `times/YYYY-MM.md`에 ID 1줄 append |
| `--pause` | 재개 블록 최신성 검사(4.2), worklog 체크포인트, lock release, sync. 상태는 In Progress 유지 |
| `--fail --cause "..." --fix "..."` | worklog `## 실패` 엔트리, 재개 블록 `주의`에 원인·처방 추가, lock release, 상태 유지 |
| `--skip --reason "..."` | `status: Canceled`, `canceled/`로 이동(v1 규칙 유지), 관계 제거, blocked_by 후속 해소, worklog `## 스킵` |

`--result` 없이 `--done`을 부르면 거부한다(종료 코드 2). 증거 없는 완료를 막는 지점이 여기다.

### 5.4 세션 종료

`pmt end --all --pause` 하나. 열린 lock 전부에 5.3 `--pause`를 적용한다. 재개 블록이 낡은 항목은 `--did/--next`를 요구한다. 별도 절차 문서 없음.

### 5.5 결정·사실 기록

`pmt add fact "..." [--ref <id>]`, `pmt add decision "..." --from "..." --to "..." --why "..."` 로 목록 행을 발급한다. `next_id`·`updated`·lock을 엔진이 처리하므로 "목록 문서 수정 전 lock acquire" 규칙이 사라진다.

---

## 6. 초기 진입 축소

### 6.1 목표

첫 코드 수정까지 명령 **3개**. v1은 projects.md 읽기 → 합류/신규 질문 → 구조 생성 → sync → 필독 7개 → lock → worklog 생성 → 착수 엔트리, 최소 8단계였다.

### 6.2 명령

| 단계 | 명령 | 하는 일 |
|---|---|---|
| 1 | `pmt new <slug> --goal "..." [--label ...]` 또는 `pmt resume <slug>` | 신규: project.md·`_default/`·목록 3개·resources·sync·projects.md 행 추가. 합류: sync + RESUME.md 출력 |
| 2 | `pmt add work "제목" [--class x] [--goal "..."]` → `pmt add item <work-id> "제목" [--kind job]` | 파일 생성·id·parent·파일명 체인 자동. 본문은 템플릿 골격 |
| 3 | `pmt start <id>` | 5.1 |

합류/신규 판단은 유지한다. 단 `pmt new`가 `projects.md`에서 라벨·이름 유사 후보를 찾아 "기존 프로젝트 후보: ..." 를 출력하고 사용자가 확정한다. 사용자가 slug를 처음부터 명시했으면 묻지 않는다(v1 동일).

### 6.3 frontmatter 최소화

필수 5개만 doctor fail 대상이다: `type`, `id`, `status`, `updated`, `parent`. 그 밖(`priority`·`assignee`·`due_date`·`labels`·`repo`·`branch`·`verify`·`executor`·`links`·`attachments`·`linear_id`)은 선택이며 없으면 키 자체를 쓰지 않는다. `null` 채우기 관행을 없앤다.

`verify`는 **위임 시점**에만 요구한다. `pmt start <id> --delegate` 가 `## 범위`·`## 완료 기준`·`verify` 부재를 검사해 거부한다. 등록 시점 미정 경고(v1 null 16건 상시 경고)를 없앤다.

### 6.4 SKILL.md 크기

SKILL.md 8000자 이내. 내용은 불변식 8개, 명령표, 진입 3단계, 완료 보고 형식만. 상세는 `references/`로 보내되 명령 출력이 필요한 내용을 인라인해 주므로 참조 문서를 읽을 일이 드물어야 한다.

---

## 7. 유지 규칙 (v1에서 변경 없이 가져오는 것)

| 항목 | 내용 |
|---|---|
| 증거 기반 완료 | Item Done에 결과 + 증거. 부모 자동 Done. Project만 사용자 허가 |
| lock 원자성 | `.locks/<id>.lock/` 디렉터리 생성(POSIX 원자적). stale 30분. 색인 재생성은 `__index` lock |
| repo merge-lock | 저장소당 병합~검증 1회. `pmt lock acquire --repo <r>`. cross-repo 고정 순서. `git reset --keep`만, `--hard` 금지, 자동 stash 금지 |
| worktree 규약 | 병렬 시에만. 경로 저장소 밖 `~/worktrees/<repo>/<key>/`. 브랜치 `pmt/<slug>/<key>` |
| 커밋 형식 | `<git user.name>: <한글 설명>` + 본문 `PMT: <id>` + 최하단 `PMT-Path: <절대 경로>`. push·배포는 사용자 몫 |
| 위임 게이트 | `## 범위`·`## 완료 기준`·`verify` 없으면 위임 금지 (요구 시점만 6.3으로 이동) |
| 서브에이전트 쓰기 범위 | worklog append + 자기 worktree 커밋만. pmt 문서·Linear·lock은 오케스트레이터 |
| worklog 4종 엔트리 | 착수·결과·실패·스킵. 실측·명령·결정만, AI 문답 금지. `components`는 통제 어휘 |
| resources 3계열 | `originals/`(변경 금지)·`derived/`·`evidence/<class>/`. 루트 파일 금지 |
| 자체 완결 | resource Markdown을 본문 대체로 참조 금지. 판독 결과는 본문에 직접 |
| Canceled 분리 | `canceled/` 분류로 이동, `canceled_from_id` 보존, 활성 관계 제거 |
| Linear 동기화 | 종료 또는 명시 요청 시만. `linear_id` upsert. 목록 문서는 문서당 이슈 1개. 로컬 참조 금지 |
| 관계 필드 4종 | `blocks`·`blocked_by`·`related_to`(실존 ID만) / `list_refs` / `waiting_on` / `resolved_blockers` |

---

## 8. 결정 필요 항목 (선택지 3개씩, 추천 표시)

### A. Classification 필수 여부

| 선택지 | 내용 | 장단 |
|---|---|---|
| A1 필수 (v1 유지) | 모든 Work는 분류 아래 | 구조 일관. 소규모 프로젝트에 빈 분류 강제 |
| A2 선택 (`_default`) | 없으면 `_default/`. 요청 시 생성 | 진입 빠름. 분류 없는 프로젝트가 Linear Milestone 1개로 뭉침 |
| **A3 선택 + 자동 제안 (추천)** | A2 + `_default/` 활성 Work 6개 초과 시 `sync`가 분류 제안 출력 | 진입 빠르고 커지면 구조화 유도. 자동 생성은 하지 않음 |

### B. 목록 문서 수

| 선택지 | 내용 | 장단 |
|---|---|---|
| B1 7개 유지 | R·T·I·B·P·H·IF 각 파일 | 태그별 조회 명확. 파일 7개 관리·lock·상한 부담 |
| B2 2개 | `facts.md` + `log.md`(나머지 전부 kind 열) | 최소. 결정(H)이 요구·버그와 섞여 검색성 저하 |
| **B3 3개 (추천)** | `facts.md`·`decisions.md`·`backlog.md`(kind 열) | 재조사 방지(사실)·근거 추적(결정)은 독립 유지, 할 일 성격은 통합 |

### C. Item 종류

| 선택지 | 내용 | 장단 |
|---|---|---|
| C1 태그 4종 + 부모 규칙 표 (v1) | V·J·TE·HF, 허용 부모·자식 표 | 구조 엄격. 규칙 표 학습·doctor 위반 잦음 |
| C2 종류 없음 | Item 하나 | 최소. 검증 Item과 구현 Item 구분 불가 → 병합 게이트 표현 어려움 |
| **C3 `kind` 필드 + 규칙 2개 (추천)** | job·view·test·hotfix, 깊이 3·test 자식 없음 | 성격은 남기고 표는 폐지 |

### D. 목록 상한 처리

| 선택지 | 내용 | 장단 |
|---|---|---|
| D1 수동 병합 (v1) | 초과 시 두 행 병합 반복 | 정보 손실·AI 작업량. 실측 20000자에 상시 밀착 |
| D2 상한 폐지 | 무제한 | 읽기 비용 증가. RESUME가 최근 N만 보여 주면 완화 가능 |
| **D3 archive 자동 (추천)** | 활성 8000자 초과 시 Done 행을 `archive/`로 이동, `find`로 조회 | 무손실·무노동. 활성 문서는 항상 작음 |

### E. worklog 위치

| 선택지 | 내용 | 장단 |
|---|---|---|
| E1 전역 단일 (v1) | `~/docs/worklog/` | 프로젝트 횡단 grep 가능. 파일명에 slug 필요 |
| E2 프로젝트 내부 | `<slug>/worklog/` | 프로젝트 이동·삭제 시 함께 움직임. 횡단 조회 불편 |
| **E3 전역 + 엔진 생성 (추천)** | E1 유지, 파일 생성은 `start`만 | 규격 위반(70%)의 원인이 수기 생성이었으므로 생성 주체를 엔진으로 고정 |

---

## 9. 엔진 요구사항 (`pmt` v2 CLI)

Python 3.8+, 외부 의존성 없음(v1 동일). 단일 파일 또는 패키지. 모든 명령은 `--project <slug>` 또는 프로젝트 폴더 안 자동 인식, `--session`/`PMT_SESSION`.

### 9.1 명령표

| 명령 | 종료 코드 | 비고 |
|---|---|---|
| `new <slug> --goal` / `resume <slug>` | 0 | 6.2 |
| `add work` / `add item` / `add fact` / `add decision` / `add backlog --kind` | 0 | ID·파일명·next_id 자동 |
| `start <id> [--delegate] [--worktree]` | 0 / 1 lock 실패 / 2 위임 게이트 실패 | 5.1 |
| `note <id> --did --next [--watch] [--wait]` | 0 | 5.2 |
| `end <id> --done\|--pause\|--fail\|--skip` / `end --all --pause` | 0 / 2 입력 부족 | 5.3 |
| `sync` | 0 | graph·Doing·RESUME·index. `__index` lock |
| `graph roots\|blocked\|children\|parents\|ancestors\|descendants\|orphans <id>` | 0 | v1 동일 |
| `lock acquire\|beat\|release\|list\|reap [<id> \| --repo <r>]` | 0 / 1 | v1 동일. `start`·`end`가 내부 호출 |
| `find <ID 또는 키워드>` | 0 / 1 없음 | 목록·archive·worklog frontmatter 검색 |
| `compact` | 0 | 3.4 |
| `doctor [--scope <class>]` | 0 / 1 fail 존재 | 9.3 |
| `close` | 0 | Project 종료: 사용자 확인 → Linear 동기화 → projects.md status Done |
| `migrate v1` | 0 | 11절 |

### 9.2 v1에서 재사용 가능한 코드 (v1 `pmt.py` 1,869줄 기준)

| v1 함수 | 재사용 |
|---|---|
| `parse_frontmatter` · `parse_scalar` · `as_list` | 그대로. flow list 한 줄 규격 유지 |
| `build_graph` · `render_graph_md` · `is_orphan` | 그대로. 노드 kind 필드만 추가 |
| `lock_acquire` · `lock_release` · `lock_beat` · `lock_scan` · `lock_reap` · `write_doing` | 그대로. reap 시 재개 블록 삽입(4.2) 추가 |
| `doctor` | 골격 재사용. 검사 항목은 9.3으로 교체 |
| `bootstrap_lists` · `insert_list_rows` · `bump_list_front` | 목록 3개 구조로 조정 |
| `write_works_index` · `shard_works` · `write_classifications_index` | `index.md` 하나로 통합. shard 폐지(활성만 담고 상한 넘으면 분류별 접기) |
| `cmd_repo_lock` | 그대로 |

### 9.3 doctor 검사 항목 (v1 16개 → 10개)

fail: ① 필수 frontmatter 5개 ② `id`=경로 일치 ③ `parent` 실존 ④ 관계 대상 실존·활성 ⑤ 깊이 3 초과 또는 `test` 자식 존재 ⑥ 순환 부모 ⑦ 목록 ID 중복·next_id 역행.
warn: ⑧ stale lock ⑨ 재개 블록 24시간 이상 미갱신인 In Progress 항목 ⑩ `~/docs/**/handoff-*.md` 존재(RESUME 부족 신호로 보고, 재개 블록 이관 권고).

resources 3계열·자체 완결·생성물 존재 검사는 유지하되 warn으로 내린다.

### 9.4 구현 순서

1. frontmatter·그래프·lock 코어 (v1 이식) + `sync`·`doctor`.
2. `new`·`add`·`start`·`note`·`end` (트랜잭션: 실패 시 되돌림).
3. `RESUME.md` 렌더러 + `resume`.
4. `compact`·`find`·`archive`.
5. `migrate v1`.
6. SKILL.md·templates·validate 스크립트.
7. 10절 수용 테스트.

---

## 10. 수용 기준 (완성 판정)

| 테스트 | 합격 조건 |
|---|---|
| 콜드스타트 | 새 세션에 `RESUME.md`만 주고 "다음 행동 1개와 주의점 1개"를 말하게 한다. Item 원본 없이 답할 수 있어야 함 |
| 진입 오버헤드 | 신규 프로젝트에서 첫 코드 수정까지 명령 3개 이하 |
| 비정상 종료 | `start` → `note` 1회 → 프로세스 강제 종료 → 다른 세션 `lock reap` → RESUME.md에 마지막 note 내용 + "비정상 종료 추정" 표시 |
| 세션 종료 | `end --all --pause` 1명령으로 lock 0·RESUME 최신·doctor fail 0 |
| 무손실 압축 | `compact` 전후 `find <ID>`가 같은 행을 반환 |
| 규칙 밀도 | SKILL.md 8000자 이내, 불변식 10개 이하, 사람이 외워야 하는 절차 0 |
| 병렬 안전 | 두 세션이 같은 Item `start` → 한쪽만 0, 다른 쪽 1. 같은 Work의 다른 Item은 둘 다 0 |
| 완료 게이트 | `end --done` 에 `--result` 없으면 거부. 자식 전부 Done 시 부모 Done 자동 |
| v1 이관 | 실 프로젝트 1개(권장: 규모가 큰 상시 유지보수 프로젝트) 이관 후 doctor fail 0, In Progress 항목의 `## 진행 메모`가 `## 재개`로 옮겨짐 |

---

## 11. v1 → v2 이관 (`pmt migrate v1`)

프로젝트를 다음에 열 때 그 프로젝트만 이관한다(지연 이관, v1 동일). 미리보기 기본, `--apply`로 기록.

1. Item 파일: 태그(V·J·TE·HF) → `kind`. 파일명 체인은 유지(역사적 체인, 새 Item만 순번 체인).
2. 목록 문서: `Information.md`→`facts.md`(IF→F), `histories.md`→`decisions.md`(H→D), `requirements.md`·`todos.md`·`plans.md`·`issues.md`·`Bugs.md`→`backlog.md`(kind 열, 원 ID를 내용 앞에 `[I3]` 로 보존, 새 ID 발급). `Bugs.md ## 점검 특징` 절은 그대로 이동. `list_refs` 재작성.
3. `## 진행 메모` → `## 재개` (한 것·다음·주의 매핑, 갱신 시각은 파일 `updated`).
4. `~/docs/handoff-*.md`·worklog 안의 `*-handoff.md`: 내용을 해당 Item 재개 블록으로 이관 후 `resources/derived/handoff-archive/`로 이동.
5. worklog: frontmatter 없는 파일에 frontmatter 생성(파일명·본문 첫 헤더에서 추정, 추정 불가 시 `issues: []` 로 두고 경고). 파일명 규격 위반은 rename.
6. `works.md`·`classifications.md` 삭제 → `index.md`. `null` 값 frontmatter 키 제거.
7. `sync` → `doctor` fail 0 확인.

---

## 부록 A. v1 실측 수치 (2026-09-02, 이 서버)

| 항목 | 값 |
|---|---|
| 프로젝트 디렉터리 / `projects.md` 색인 행 / 아카이브 | 13 / 9 (미등재 4) / 15 |
| md 파일 수 (`~/docs/projects/`, 생성물 포함, `_archive`·`resources` 제외) | 1,417 |
| SKILL.md / references 6개 / `pmt.py` | 23,486 B / 60,021 B / 71,096 B (1,869줄) |
| 계약 수 / 태그 종류 / 목록 문서 수 | 23 / 11 / 7 |
| In Progress Work·Item 수 / `## 진행 메모` 보유 | 9 / 2 |
| 체계 밖 인계 문서 | 4 (10.0 KB · 11.0 KB · 18.3 KB · 19.1 KB) |
| 활성 worklog 파일 / frontmatter 없음 / 파일명 규격 위반 | 23 / 16 / 7 |
| 최대 worklog 파일 | `iaas-maintenance__api__Work6.md` 63,500 B |
| `Information.md` / `histories.md` 글자 수 (상한 20,000) | 19,947 / 19,997 |
| doctor (iaas-maintenance) | 16 pass · 1 warn(null 필드 16건) · 0 fail |
| lock 회수 이력 | 1건 (2026-08-27 api/Work6, heartbeat 46분 경과) |

## 부록 B. 최소 템플릿

### project.md

```markdown
---
type: project
id: <slug>
status: Planned
updated: YYYY-MM-DD
labels: []
repositories: []
---
# <프로젝트명>
## Goal
- <검증 가능한 통합 목표 1개>
## Non-Goal
- 
## 결과
- <종료 시>
```

### Work (`_default/Work1.md`)

```markdown
---
type: work
id: <slug>/_default/Work1
parent: <slug>/_default
status: Planned
updated: YYYY-MM-DD
---
# Work1: <제목>
## Goal
- 
## 결과
- 
## 증거
- 
```

### Item (`_default/Work1-1.md`)

```markdown
---
type: item
kind: job
id: <slug>/_default/Work1-1
parent: <slug>/_default/Work1
status: Planned
updated: YYYY-MM-DD
---
# [job] <제목>
## 기본 내용
- 
## 범위
- [ ] 
## 완료 기준
- 
## 재개
<start 이후 note 가 채움>
## 결과
- 
## 증거
- 
```

### 목록 행

```markdown
| F12 | Done | 2026-09-02 | 개발 DB `admin_api_auth` 는 사용자별 override 행만 보유. 빈 테이블 = 현행 100% 보존. 검증: sandbox 실호출 11건 |
| D47 | Done | 2026-09-01 | 전→후: 그룹×메뉴×메서드 → 관리자 개인×엔드포인트. 사유: ERP 집계 전용 계정 요구. 결정자: 사용자 |
| B26 | issue | In Progress | 2026-08-31 | 규격서 21·25편 진단 정정 필요 — 8pt→12px 변화 원인은 padding·height |
```

### worklog 체크포인트 (note 가 append)

```markdown
## 체크포인트 2026-09-02 14:20
- 한 것: J2 저장 경로 철거 커밋 2850c1e 되돌림
- 다음: V1 팝업 개명
- 주의: ~/iaas-admin 미커밋 2파일(Events.php, check_commit_msg.sh) 사용자 것, 건드리지 말 것
```

---

## 부록 C. 이 문서를 쓰는 순서 (다른 PC 착수 절차)

1. 8절 결정 A~E를 확정한다. 추천을 그대로 받으면 질문 없이 진행 가능.
2. 9.4 순서로 엔진을 만든다. 각 단계마다 10절의 해당 테스트를 통과시킨다.
3. SKILL.md는 불변식 8개(2절)·명령표(9.1)·진입 3단계(6.2)·완료 보고 형식만 담는다. 8000자를 넘으면 참조로 보낸다.
4. 이 서버의 v1 프로젝트를 `~/docs`(git) 복제로 가져와 11절 이관을 1개 프로젝트에 실행하고 수용 기준을 확인한다.
