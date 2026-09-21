# Codex 어댑터 — Layer B(Linear 큐) 편입

Layer A(인라인)는 별도 설정이 필요 없다. 아래는 큐 모드용.

## 1. Linear MCP 등록

`~/.codex/config.toml`에 추가 (원격 직결 — 2026-08-03 실측 구성):

```toml
[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
```

첫 사용 시 OAuth URL이 출력되면 로컬 브라우저에서 열어 인증한다.
확인: `codex mcp list`에서 linear가 `Status: enabled, Auth: OAuth`면 완료.

## 2. 프로젝트 준비

- 없음. 실행자 규약은 프로젝트에 설치하지 않고 **프롬프트에 내장**한다
  (`skills/codex-handoff/references/executor-protocol.md` 참조 — AGENTS.md 오염 방지).

## 3. 사용

- 수동 트리거(기본값):

  ```bash
  codex exec --dangerously-bypass-approvals-and-sandbox -C <프로젝트> \
    "다음 실행자 규약에 따라 내게 할당된 Todo 이슈 1건을 처리하라.
  <executor-protocol.md의 큐 모드 섹션 전문>"
  ```

- 반자동 배치(계획 품질 검증 후 승격): `scripts/codex-drain.sh <프로젝트> [필터문구]`
  — 이슈당 exec 1회, 기본 상한 5건(`MAX` 환경변수로 조정), `QUEUE_EMPTY` 시 즉시 종료.

## 보안 주의

큐 모드는 **이슈 본문을 지시문으로 실행**하며 샌드박스·승인을 우회한다.
따라서 이슈 작성 권한이 통제되는(팀 내부) 보드에서만 사용한다. 외부인이
이슈를 쓸 수 있는 보드에 돌리면 프롬프트 인젝션이 곧 코드 실행이 된다.
