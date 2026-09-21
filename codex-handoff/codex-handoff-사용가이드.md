> 원본: `~/ai-integrate` (하이브리드 워크플로우 본부 저장소). 이 사본은 스킬 파악용이며,
> 본문 속 `scripts/`·`docs/` 상대경로는 원본 저장소 기준이다. adapters/는 이 디렉토리에 동봉.

# ai-integrate — Claude(계획) + Codex(실행) 하이브리드 워크플로우

계획·검증은 Claude Code가, 코드 생성은 실행자(Codex)가 맡아 토큰 비용을
최적화한다. 오케스트레이터는 없다 — 계약 문서 2개와 얇은 스킬 1개가 전부다.

## 언제 무엇을 쓰나

| 상황 | 레이어 | 사용법 |
|---|---|---|
| 일상 작업 (단일 세션, 순차) | **A. 인라인** | Claude Code에서 `/codex-handoff` — 계획 파일의 태스크를 실행자에게 넘기고 검증 |
| 대형 작업, 병렬, 비동기 | **B. Linear 큐** | `linear-register`로 이슈 등록 → 실행자가 클레임 프로토콜로 소비 |

## 다른 프로젝트에 적용하기

0. (최초 1회) 스킬 전역 설치 — 모든 프로젝트에서 `/codex-handoff` 사용 가능
   (이 저장소에서는 `~/.claude/skills`가 `skills/`를 가리키는 심볼릭 링크라
   별도 설치가 없다 — `skills/` 하위를 지우면 설치본이 같이 사라진다):

   ```bash
   ln -sfn ~/ai-integrate/skills/codex-handoff ~/.claude/skills/codex-handoff
   ```

1. 계획 작성: `<프로젝트>/docs/superpowers/plans/YYYY-MM-DD-<주제>.md` —
   `skills/codex-handoff/references/plan-format.md` 형식 (superpowers writing-plans와 동일 위치).
   **태스크마다 실행 가능한 `검증:` 커맨드 필수.**

2. Claude Code(해당 프로젝트)에서 실행: `/codex-handoff` 로 계획을 지정하면
   태스크별 핸드오프 → 검증 → 체크박스 → 커밋 루프가 돈다.

3. (선택) 대형·병렬 작업은 Layer B로 승격: `linear-register`로 이슈 등록 후
   `adapters/codex.md`(Linear MCP 등록·수동 트리거·`codex-drain.sh`) 절차를 따른다.

대상 프로젝트에 설치할 파일은 **없다** — 실행자 규약은 핸드오프 프롬프트에
전문이 내장되므로 프로젝트의 AGENTS.md를 건드리지 않는다
(`skills/codex-handoff/references/executor-protocol.md` 참조).

## 구성

- `skills/codex-handoff/references/plan-format.md` — 계획 파일 형식. **검증 커맨드 없는 태스크는 넘기지 않는다.**
- `skills/codex-handoff/references/executor-protocol.md` — 실행자 규약(센티널 TASK_DONE/TASK_FAIL/QUEUE_EMPTY). 핸드오프 프롬프트에 전문 내장.
- `skills/codex-handoff/` — Layer A 스킬. 핸드오프 → 판정 → 분기 루프.
- `scripts/codex-drain.sh` — Layer B 반자동 배치 (이슈당 exec 1회, 상한, QUEUE_EMPTY 종료)
- `adapters/codex.md` — Codex 편입 절차(Linear MCP 등록, 큐 모드 트리거, 보안 주의)
- `docs/` — 설계 스펙, 구현 계획, 평가 보고(2026-08-03 todo-app 실험)

## 실측 요약 (2026-08-03 todo-app 실험)

- 비용 구조 검증: 코드 생성 토큰 전량이 실행자 요금제로 이동, Claude는 계획+검증만.
  Codex 소모의 85%는 프롬프트 캐시로 흡수되어 주간 한도 영향 미미.
- Codex: 규약 위반 0회.
- 상세: `docs/evaluations/2026-08-03-todo-app-eval.md`

## 설계 문서

- 스펙: `docs/superpowers/specs/2026-08-03-claude-codex-hybrid-design.md`
- 구현 계획: `docs/superpowers/plans/2026-08-03-claude-codex-hybrid.md`
