---
name: proj-mgmt-tool-v2
description: 로컬 문서를 원천으로 Project→Work→Item 작업을 생성·재개·점유·기록·완료하는 프로젝트 관리 스킬. 긴 작업의 콜드스타트 재개, 병렬 세션 충돌 방지, 증거 기반 완료, v1 이관이 필요할 때 사용한다. 원격 이슈만 단순 편집하거나 일회성 할 일을 적는 요청에는 사용하지 않는다.
---

# proj-mgmt-tool v2

프로젝트 상태는 로컬 `~/docs/projects/<slug>/`에 둔다. Codex와 Claude Code 모두 이 폴더의 같은 `SKILL.md`와 형제 `scripts/pmt.py`를 사용한다. 특정 에이전트 전용 도구나 홈 경로를 가정하지 않는다.

## 엔진 호출

현재 읽은 `SKILL.md`의 부모를 `<skill-dir>`로 해석하고 다음 형태로 실행한다.

```text
python <skill-dir>/scripts/pmt.py [--docs-root <path>] [--session <stable-id>] [--project <slug>] <command>
```

한 작업 단위 동안 같은 `--session` 값을 유지한다. 기본 데이터 루트는 `~/docs`; 격리 실행은 `--docs-root` 또는 `PMT_DOCS_ROOT`를 사용한다. `pmt`가 PATH에 있다고 가정하지 않는다.

## 불변식

1. 로컬 문서가 원천이다. Linear·업무보고 같은 원격 쓰기는 종료 또는 사용자 명시 요청 때만 upsert한다.
2. lock·상태·worklog·재개·sync·검증 순서는 사람이 재구현하지 않는다. `start`, `note`, `end`를 호출한다.
3. 인계 정보는 작업 중 `note`로 덮어쓴다. 콜드스타트는 생성물 `RESUME.md` 하나에서 시작한다.
4. Item 완료에는 `--result`가 필수이고 가능하면 `--evidence`를 붙인다. 자식이 모두 Done이면 부모는 자동 Done; Project 종료는 사용자 허가가 필요하다.
5. `start` 성공 전 파일을 수정하지 않는다. 같은 Item lock 실패 시 착수하지 않는다. 병합·검증 구간은 repo lock을 별도로 잡는다.
6. 계보·차단·착수 가능 항목은 `graph`로 찾는다. 상태 파악을 위해 원본 전체를 통독하지 않는다.
7. 목록이 커지면 `compact`로 Done·Canceled 행을 `archive/`로 옮긴다. 병합·요약으로 정보를 버리지 않는다.
8. Project·Work·Item은 링크 없이도 범위·결정·완료 조건·결과를 이해할 수 있게 유지한다.

## 진입

신규는 세 명령 그룹 이내에 착수한다.

```text
pmt new <slug> --goal "검증 가능한 목표"
pmt add work "작업 묶음"
pmt add item <work-id> "첫 작업" --kind job
pmt start <item-id>
```

여기서 `pmt`는 위의 Python 호출을 줄여 쓴 표기다. 기존 프로젝트는 `pmt resume <slug>` 출력만 먼저 읽고, 잡을 Item 파일 하나를 읽는다. 추가 사실이나 결정이 필요할 때만 `pmt find <ID-or-keyword>`를 쓴다.

## 작업 루프

- 착수: `start <id> [--delegate] [--worktree <path>]`. lock 실패는 종료 코드 1, 위임 필드 부족은 2다.
- 체크포인트: `note <id> --did "..." --next "..." [--watch "..."] [--wait "..."]`. 30분 이상 작업 전, 의미 있는 중간 결과, 종료 직전에 호출한다.
- 종료: `end <id> --done --result "..." [--evidence <path>]`, `--pause`, `--fail --cause "..." --fix "..."`, 또는 `--skip --reason "..."` 중 하나만 사용한다.
- 세션 정리: `end --all --pause`. 낡거나 비어 있는 재개 블록이 있으면 `--did`와 `--next`를 보강한 뒤 다시 실행한다.

명령을 수동 파일 편집으로 흉내 내지 않는다. 명령 실패 시 출력과 종료 코드를 보존하고, 원인을 고친 뒤 같은 명령을 재시도한다.

## 명령 지도

| 목적 | 명령 |
|---|---|
| 생성·합류 | `new`, `resume` |
| 구조·목록 추가 | `add work`, `add item`, `add fact`, `add decision`, `add backlog` |
| 실행 수명주기 | `start`, `note`, `end` |
| 생성물 재작성 | `sync` |
| 계보·차단 조회 | `graph roots|blocked|children|parents|ancestors|descendants|orphans` |
| 점유·병합 점유 | `lock acquire|beat|release|list|reap [<id>|--repo <path>]` |
| 검색·보관 | `find`, `compact` |
| 무결성·종료·이관 | `doctor`, `close`, `migrate v1` |

세부 인자·종료 코드는 [references/pmt-v2-contract.md](references/pmt-v2-contract.md)를 해당 명령이 필요할 때만 읽는다. v1을 옮길 때만 [references/migration-v1.md](references/migration-v1.md)를 읽는다. 구현이나 변경을 검증할 때만 [references/acceptance-tests.md](references/acceptance-tests.md)를 읽는다.

## 병렬·위임

- Work 아래 Item 깊이는 최대 3. `kind: test`는 자식을 만들지 않는다.
- `start --delegate`는 Item의 `## 범위`, `## 완료 기준`, `verify`가 모두 있어야 한다.
- 서브에이전트는 자기 worktree와 worklog만 쓴다. PMT 문서·lock·원격 동기화는 오케스트레이터가 맡는다.
- 병렬 저장소 작업에서 merge부터 검증까지 `lock acquire --repo <repo>`로 직렬화한다. 자동 stash와 `git reset --hard`는 금지한다.
- push·배포는 사용자가 수행하거나 명시적으로 요청한 경우만 실행한다.

## 완료 보고

`end --done` 뒤 다음만 보고한다.

```text
대상: <id>
결과: <한 줄>
증거: <경로 또는 없음>
검증: <명령과 pass/fail>
부모 상태: <자동 전파 결과>
남은 차단/대기: <없음 또는 목록>
```

완료 주장 전 `doctor --scope <classification>` 또는 전체 `doctor` 결과를 읽는다. Project `close`는 사용자 허가와 원격 동기화 결과가 확보된 뒤 실행한다.
