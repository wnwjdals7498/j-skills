# 워크플로 계약

토큰 우선 균형형의 데이터 계약이다. `codex-handoff`가 있으면 계획 위치, `대상`·`검증`, 실행자 센티널만 호환한다. 실행 방식과 검증·커밋 규칙은 이 계약을 따른다.

## 실행 예산

```yaml
profile:
  mode: token-first-balanced
  max_parallel: 2
  initial_planner_calls: 1
  replan_per_block_signature: 1
  implementation_retry: 1
  final_independent_reviews: 1
```

동일 파일과 문맥을 사용하는 작은 작업은 계획 단계에서 하나의 태스크로 합친다. 병렬화는 총 토큰보다 대기 시간 절감이 중요한 경우에만 2개까지 사용한다.

## 환경 스냅샷

계획 전에 직접 확인해 계획 상단에 기록한다.

```yaml
environment:
  environment_id: <짧은 실행 식별자>
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

비밀 값, 토큰, 개인 경로의 자격 증명 파일 내용은 넣지 않는다. 전문은 한 번만 저장하고 모델 프롬프트에는 `environment_id`, 기준 커밋, 태스크에 필요한 항목만 전달한다. worktree를 사용하면 각 작업 경로와 기준 커밋이 같은지 별도로 확인한다.

## 계획 형식

기본 위치는 `docs/superpowers/plans/YYYY-MM-DD-<주제>.md`다.

```markdown
# <주제> 실행 계획

## 목표와 제외 범위
- 목표: ...
- 제외: ...

## 환경
- environment_id: <ID>
- base_commit: <SHA>

## 태스크
- [ ] T1: <검증 가능한 목표>
  - wave: 1
  - depends_on: []
  - model: gpt-5.6-sol
  - risk: low
  - verification_tier: V1
  - write_set: [src/a.ts, tests/a.test.ts]
  - resource_set: []
  - context: [src/contracts.ts]
  - acceptance: <관찰 가능한 완료 조건>
  - verify: `<실행 가능한 명령>` -> <기대 결과>

## 개정 기록
- R0: 최초 계획
```

`write_set`은 glob이 아닌 파일 또는 충분히 좁은 디렉토리로 적는다. `resource_set`에는 DB, 포트, 테스트 서버, 빌드 캐시, 생성물 디렉토리 같은 파일 외 공유 자원을 적는다. 같은 웨이브의 두 집합이 겹치면 안 된다. lockfile, 공용 설정, 생성기 입력, 마이그레이션, 배럴 export는 독립 순차 태스크로 둔다.

`wave`, `depends_on`, `model`, `risk`, `verification_tier`, `write_set`, `resource_set`, `acceptance`, `verify`가 없는 태스크는 실행하지 않는다. `codex-handoff` 형식의 `대상`은 `write_set`, `검증`은 `verify`로 인정하되 나머지 필드는 보강한다. 계획 작성 후 다음을 실행한다.

```text
python <스킬경로>/scripts/validate_plan.py <계획파일>
```

## Fable 계획 패킷

Fable에는 사용자 목표, 제외 범위, `environment_id`, 관련 파일·심볼, 적용 지침, 알려진 테스트 명령만 제공한다. 저장소 전체 파일 목록, 전체 대화, 성공 로그는 포함하지 않는다. 관련 파일을 로컬 검색으로 결정할 수 없을 때만 Fable이 추가 탐색한다.

## Fable 계획 프롬프트

```text
너는 계획자다. 구현하거나 파일을 수정하지 마라.
제공된 목표와 간결한 계획 패킷만 사용해 실행 계획을 작성하라. 필요한 증거가 없을 때만 추가 파일을 읽어라.
외부 정보성 사실이 필요하면 공식 문서만 근거로 사용하라.
장문 설명 없이 태스크 표와 미확인 사항만 반환하라.
각 태스크에 depends_on, wave, model, risk, verification_tier, 정확한 write_set과 resource_set,
acceptance, 실행 가능한 verify와 기대 결과를 지정하라.
Sol을 기본으로 하고 Terra는 고위험 조건에만 지정하라. 같은 문맥의 작은 작업은 하나의 태스크로 합쳐라.
같은 wave의 write_set과 resource_set은 겹치면 안 된다.
불명확한 사항은 사실로 만들지 말고 계획의 차단 조건으로 표시하라.
```

## Codex 작업자 패킷

전체 계획과 대화 이력을 전달하지 않는다. 다음만 포함한다.

```yaml
task_packet:
  environment_id: <ID>
  repo_root: <절대 경로>
  base_commit: <SHA>
  task: <T번호와 목표>
  write_set: [<허용 경로>]
  resource_set: [<공유 자원>]
  context: [<읽을 파일>]
  acceptance: <완료 조건>
  verify: <명령과 기대 결과>
```

## Codex 작업자 프롬프트

```text
너는 실행자다. 제공된 task_packet만 수행하라.
write_set 밖의 파일, 계획 파일, 다른 태스크, 커밋은 건드리지 마라.
완료 후 V0 범위 검사와 지정된 verify만 한 번 실행하라.
계획 또는 환경 문제로 안전하게 완료할 수 없으면 수정 범위를 넓히지 말고 차단 보고서를 작성하라.
장문 설명과 전체 로그를 출력하지 마라. 다음 필드만 보고하라:
task, status, changed, verify, exit_code, note.
성공 마지막 줄: TASK_DONE <T번호>
차단 마지막 줄: TASK_FAIL <T번호>: BLOCKED <한 줄 요약>
실패 마지막 줄: TASK_FAIL <T번호>: <한 줄 원인>
```

네이티브 에이전트에는 가능한 최소 대화 이력과 작업자 패킷만 전달한다. CLI를 사용할 때는 대상 저장소 또는 전용 worktree를 `-C`로 명시하고 모델을 생략하지 않는다. 일반 실행에서는 승인과 sandbox를 유지한다. 외부에서 격리된 환경과 명시적 권한 없이 `--dangerously-bypass-approvals-and-sandbox`를 사용하지 않는다.

## 차단 보고서

```yaml
block:
  task: T<N>
  type: requirement | plan | scope | collision | environment | dependency | permission | verification
  observed: <직접 관찰한 사실>
  evidence: [<명령, 파일, 짧은 결과>]
  log_excerpt: <오류 핵심 줄만>
  modified_files: [<현재 부분 변경>]
  safe_state: <부분 변경을 유지해도 되는지>
  planner_question: <Fable이 결정해야 할 한 가지>
  options: [<근거가 있는 선택지만>]
```

차단 전에 범위 밖 파일을 수정하지 않는다. 이미 부분 변경이 있으면 자동 삭제·되돌리기하지 말고 정확히 공개한다.

권한·인증·비밀·목표 변경은 Fable에 보내지 않고 사용자에게 요청한다. 구현 오류는 관련 diff와 오류 핵심 줄만 Codex에 한 번 재전달한다. 계획·범위·충돌 문제만 Fable 재계획 대상이다.

## Fable 재계획 프롬프트

```text
너는 계획 수정자다. 코드를 작성하거나 파일을 수정하지 마라.
사용자 목표와 environment_id는 유지하라. 차단 태스크, 관련 diff, 오류 핵심 줄만 검토해
차단 원인을 해소하는 최소 plan_delta만 반환하라. 전체 계획을 다시 출력하지 마라.
변경한 태스크의 의존성, wave, model, risk, verification_tier, write_set, resource_set, verify,
부분 변경 처리 방식만 명시하라.
사용자 목표·공개 인터페이스·의존성·데이터·보안 경계를 바꿔야 하면 계획을 확정하지 말고
필요한 사용자 결정을 한 문장으로 표시하라.
```

오케스트레이터만 `plan_delta`를 적용하고 계획 파일과 체크박스를 갱신한다. 변경 태스크의 하위 의존 태스크는 다시 검증한다. 같은 차단 서명에 대한 Fable 호출은 1회가 상한이다.

## 검증 단계

- **V0 범위 검사:** 태스크마다 로컬 `git diff`와 `git status --short -uall`; 모델 없음
- **V1 태스크 검증:** 작업자가 태스크의 최소 테스트 1회
- **V2 영향 검증:** 공용 인터페이스·공유 자원 변경 때만 통합 후 실행
- **V3 최종 검증:** 전체 검증과 독립 Sol 검토를 커밋 직전 각각 1회
- **V4 고위험 검증:** 보안·인증·데이터 마이그레이션·파괴 가능 변경 또는 Sol 검증 실패 때 Terra 1회

성공 로그 전문은 모델에 전달하지 않는다. 실패 로그도 원인 판단에 필요한 부분만 전달하고 전체 로그는 파일로 보존한다.

## 독립 검증 보고

검증자는 파일을 수정하지 않고 다음을 반환한다.

```yaml
verification:
  reviewer_model: <모델>
  base_commit: <SHA>
  diff_hash: <검토한 diff 식별값>
  reviewed_diff: <범위 요약>
  commands:
    - command: <실행 명령>
      exit_code: <정수>
      result: <핵심 결과>
  scope_ok: true | false
  findings: [<심각도, 파일, 근거>]
  verdict: PASS | FAIL | BLOCKED
```

독립 검증자는 최종 diff, 사용자 목표, 완료 조건만 받는다. 구현 대화와 전체 로그는 받지 않는다. `PASS`라도 staged diff가 `diff_hash`와 같은지 확인해야 하며 전체 검증을 대신하지 않는다.
