# 워크플로 계약

`codex-handoff`가 없을 때 사용하는 자체 계약이다. 있으면 그 스킬의 계획 형식과 실행자 규약을 우선 재사용하고, 아래 환경·병렬·차단·검증 필드를 보강한다.

## 환경 스냅샷

계획 전에 직접 확인해 계획 상단에 기록한다.

```yaml
environment:
  repo_root: <절대 경로>
  base_commit: <SHA>
  branch: <이름 또는 detached>
  baseline_status: <git status --short -uall 결과 요약>
  os_shell: <운영체제와 셸>
  planner: claude/fable
  worker_models: [gpt-5.6-sol, gpt-5.6-terra]
  instructions: [<적용되는 AGENTS.md/CLAUDE.md/기타 규칙 파일>]
  package_lock: <lockfile과 패키지 관리자, 없으면 없음>
  verification: [<전체 검증 명령>]
  env_names: [<필요한 환경 변수 이름만>]
```

비밀 값, 토큰, 개인 경로의 자격 증명 파일 내용은 넣지 않는다. worktree를 사용하면 각 작업 경로와 기준 커밋이 같은지 별도로 확인한다.

## 계획 형식

기본 위치는 `docs/superpowers/plans/YYYY-MM-DD-<주제>.md`다.

```markdown
# <주제> 실행 계획

## 목표와 제외 범위
- 목표: ...
- 제외: ...

## 환경
<환경 스냅샷>

## 태스크
- [ ] T1: <검증 가능한 목표>
  - wave: 1
  - depends_on: []
  - model: gpt-5.6-sol
  - write_set: [src/a.ts, tests/a.test.ts]
  - context: [src/contracts.ts]
  - acceptance: <관찰 가능한 완료 조건>
  - verify: `<실행 가능한 명령>` -> <기대 결과>

## 개정 기록
- R0: 최초 계획
```

`write_set`은 파일 또는 충분히 좁은 디렉토리로 적는다. lockfile, 공용 설정, 생성기 입력, 마이그레이션, 배럴 export처럼 충돌 가능성이 큰 대상은 독립 순차 태스크로 둔다. `verify`가 없는 태스크는 실행하지 않는다.

## Fable 계획 프롬프트

```text
너는 계획자다. 구현하거나 파일을 수정하지 마라.
제공된 사용자 목표, 환경 스냅샷, 저장소의 직접 증거를 바탕으로 실행 계획만 작성하라.
외부 정보성 사실이 필요하면 공식 문서만 근거로 사용하라.
각 태스크에 depends_on, wave, 정확한 write_set, acceptance, 실행 가능한 verify와 기대 결과,
gpt-5.6-sol 또는 gpt-5.6-terra 중 담당 모델을 지정하라.
같은 wave의 write_set은 겹치면 안 된다. 공용 파일은 순차 통합 태스크로 분리하라.
불명확한 사항은 사실로 만들지 말고 계획의 차단 조건으로 표시하라.
```

## Codex 작업자 프롬프트

```text
너는 실행자다. 계획 파일 <절대 경로>의 <T번호>만 수행하라.
저장소=<절대 경로>, 기준 커밋=<SHA>, 작업 경로=<절대 경로>다.
write_set 밖의 파일, 계획 체크박스, 다른 태스크, 커밋은 건드리지 마라.
완료 후 태스크의 verify를 직접 실행하고 실제 명령·결과·변경 파일을 보고하라.
계획 또는 환경 문제로 안전하게 완료할 수 없으면 수정 범위를 넓히지 말고 차단 보고서를 작성하라.
성공 마지막 줄: TASK_DONE <T번호>
차단 마지막 줄: TASK_FAIL <T번호>: BLOCKED <한 줄 요약>
실패 마지막 줄: TASK_FAIL <T번호>: <한 줄 원인>
```

CLI를 사용할 때는 대상 저장소 또는 전용 worktree를 `-C`로 명시하고 모델을 생략하지 않는다. 일반 실행에서는 승인과 sandbox를 유지한다. 외부에서 격리된 환경과 명시적 권한 없이 `--dangerously-bypass-approvals-and-sandbox`를 사용하지 않는다.

## 차단 보고서

```yaml
block:
  task: T<N>
  type: requirement | plan | scope | collision | environment | dependency | permission | verification
  observed: <직접 관찰한 사실>
  evidence: [<명령, 파일, 짧은 결과>]
  modified_files: [<현재 부분 변경>]
  safe_state: <부분 변경을 유지해도 되는지>
  planner_question: <Fable이 결정해야 할 한 가지>
  options: [<근거가 있는 선택지만>]
```

차단 전에 범위 밖 파일을 수정하지 않는다. 이미 부분 변경이 있으면 자동 삭제·되돌리기하지 말고 정확히 공개한다.

## Fable 재계획 프롬프트

```text
너는 계획 수정자다. 코드를 작성하거나 파일을 수정하지 마라.
사용자 목표와 환경 스냅샷은 유지하라. 현재 계획, 차단 보고서, 관련 diff와 검증 로그를 검토해
차단 원인을 해소하는 최소 수정 계획을 반환하라.
변경한 태스크, 의존성, wave, write_set, verify, 부분 변경 처리 방식을 명시하고 개정 사유를 남겨라.
사용자 목표·공개 인터페이스·의존성·데이터·보안 경계를 바꿔야 하면 계획을 확정하지 말고
필요한 사용자 결정을 한 문장으로 표시하라.
```

오케스트레이터만 계획 파일과 체크박스를 갱신한다. 완료된 태스크는 수정 계획의 직접 영향을 받는 경우에만 재개한다.

## 독립 검증 보고

검증자는 파일을 수정하지 않고 다음을 반환한다.

```yaml
verification:
  reviewer_model: <모델>
  base_commit: <SHA>
  reviewed_diff: <범위 요약>
  commands:
    - command: <실행 명령>
      exit_code: <정수>
      result: <핵심 결과>
  scope_ok: true | false
  findings: [<심각도, 파일, 근거>]
  verdict: PASS | FAIL | BLOCKED
```

`PASS`라도 오케스트레이터의 staged diff 확인과 전체 검증을 대신하지 않는다.
