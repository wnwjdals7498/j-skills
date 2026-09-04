---
name: proj-mgmt-tool-v2
description: 로컬 문서를 원천으로 프로젝트를 재개·점유하고 결정 이력과 검증 기록을 관리하는 스킬. Codex와 Claude Code에서 장기 작업을 안전하게 이어갈 때 사용한다.
---

# proj-mgmt-tool v2

프로젝트 상태는 `~/docs/projects/<slug>/`에 두며, 엔진은 형제 `scripts/pmt.py` 하나다.

## 엔진 호출

현재 읽은 `SKILL.md`의 부모를 `<skill-dir>`로 해석해 실행한다.

```text
python3 <skill-dir>/scripts/pmt.py [--docs-root <path>] [--session <stable-id>] [--project <slug>] <command>
```

기본 데이터 루트는 `~/docs`이며 격리는 `--docs-root` 또는 `PMT_DOCS_ROOT`를 쓴다. `--session`을 생략하면 조부모 프로세스 기준으로 자동 파생한다. 서브에이전트는 같은 세션이므로 PMT 문서와 lock을 만지지 않는다.

## 불변식

1. 로컬 문서가 원천이다. 원격 쓰기는 사용자 명시 요청이 있을 때만 에이전트 커넥터로 수행한다.
2. 점유·상태·기록·검증 절차는 `start`, `note`, `verify`, `end` 명령에 맡긴다.
3. 인계는 `note`로 상시 갱신. 콜드스타트·컨텍스트 압축 후 재개는 `pmt resume <slug>` 하나에서 시작.
4. 완료는 `--result`가 필수다. 현재 HEAD·완료 기준과 일치하는 `verify` 기록이 없으면 `--unverified <사유>`도 필수다. 자식이 모두 Done이면 부모는 자동 Done, 프로젝트 종료는 `end <slug> --done --confirm`이다.
5. `start` 성공 전 문서를 수정하지 않는다. stale lock은 `start`가 자동 회수하며, 다른 Item의 heartbeat가 30분을 넘으면 새 `start`를 거부한다.
6. 착수 가능·차단·계보는 `RESUME.md`와 `find`로 본다. 원본 통독 금지.
7. 목록 행은 `set --status`로 전이하고 엔진이 8,000자 초과 시 자동 archive. 결정은 삭제하지 않고 `대체`·`폐기`로만 남긴다.
8. Project·Work·Item은 링크 없이도 범위·결정·완료 기준·결과를 이해할 수 있게 자체 완결로 유지한다.

## 진입

신규는 네 명령으로 착수한다.

```text
pmt new <slug> --goal "검증 가능한 목표"
pmt add work "작업 묶음"
pmt add item <work-id> "첫 작업" --kind job
pmt start <item-id>
```

`pmt`는 위 Python 호출의 줄임말이다. 기존 프로젝트는 `pmt resume <slug>` 출력과 작업할 Item 하나만 읽는다.

## 작업 루프

- `start <id>`: 출력의 체크포인트와 재검증 판정 줄을 읽은 뒤 수정한다.
- `note <id> --did "..." --next "..."`: 각 필드는 400자 이하. 30분 이상 작업 전, 의미 있는 중간 결과, 종료 직전에 갱신한다.
- `verify <id> --cmd "..." (--exit N | --run) [--limit "..."]`: 완료 기준 해시·HEAD·종료 코드를 `## 검증`과 worklog에 남긴다.
- `end <id> --done --result "..." [--unverified "..."]`, `--pause`, `--fail --cause "..." --fix "..."`, `--skip --reason "..."` 중 하나로 끝낸다.
- 세션 정리는 `end --all --pause`다. 모든 명령의 stderr 첫 줄에 "체크포인트 N분 경과"가 나오면 즉시 `note`한다.

## 결정·사실·백로그

- 결정: 사용자 합의 뒤 `decide "<제목>" --context "..." --decision "..." [--alt "..." --result "..." --supersedes D<n>]`.
- 사실: `add fact "<내용>" [--ref "<출처>"]`. 출처 기록을 권장한다.
- 백로그: `add backlog "<내용>" --kind req|todo|plan|issue|bug`.
- 상태: `set F3|B5|D2 --status <상태> [--why "..."]`.
- 계보: `find --chain D<n>`.

## 명령 지도

| 명령 | 목적 |
|---|---|
| `new` | 프로젝트 생성 |
| `resume` | 제한된 재개 요약 생성·출력 |
| `add` | Work·Item·fact·backlog 추가 |
| `decide` | 승인 결정과 대체 이력 기록 |
| `set` | 목록 상태·Item 차단 변경 |
| `start` | Item 점유와 착수 |
| `note` | 재개 정보와 heartbeat 갱신 |
| `verify` | 검증 행과 worklog 기록 |
| `end` | 완료·중지·실패·취소·프로젝트 종료 |
| `lock` | Item·저장소 lock 관리 |
| `find` | 원본·archive·worklog 검색과 결정 계보 |
| `doctor` | 문서·관계·목록 무결성 검사 |

## 병렬·위임

- Work 아래 Item 깊이는 최대 3이며 `kind: test`는 자식을 만들지 않는다.
- `start --delegate`는 범위·완료 기준·`verify`가 모두 있어야 한다.
- 서브에이전트는 자기 작업 파일만 다루고 PMT 문서·lock·원격 동기화는 오케스트레이터가 맡는다.
- 여러 저장소는 `lock acquire --repo A --repo B`로 정렬 획득해 병합부터 검증까지 직렬화한다.
- 자동 stash와 `git reset --hard`는 금지하며 push·배포는 사용자 명시 요청 때만 수행한다.

## 완료 보고

```text
대상: <id>
결과: <한 줄>
증거: <경로 또는 없음>
검증: <Item의 ## 검증 마지막 행>
부모 상태: <자동 전파 결과>
남은 차단/대기: <없음 또는 목록>
```

참조: 인자·종료 코드가 필요하면 [계약서](references/pmt-v2-contract.md), v1 이관은 [이관 안내](references/migration-v1.md)를 읽는다.
