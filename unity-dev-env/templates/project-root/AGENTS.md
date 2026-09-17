# AGENTS.md — {PROJECT_NAME}

> 이 프로젝트의 코딩 에이전트 진입점. `CLAUDE.md` 는 이 파일의 링크다.

---

## 1. 파이프라인 키트

이 프로젝트는 **Unity AI Development Pipeline Kit** 규칙을 따른다.

```
KIT_ROOT = {KIT_ROOT}
```

작업 시작 시 **반드시** 아래를 읽는다:

```
{KIT_ROOT}/SKILL.md          ← 트랙 선택, Run Loop, 절대 규칙
{KIT_ROOT}/references/00_INDEX.md   ← 문서 라우팅
```

그 다음 현재 스테이지 문서만 로드한다. 전체를 한 번에 읽지 않는다.

---

## 2. 이 프로젝트의 설정

```yaml
profile: {3d|2d}
mode: {greenfield|rebase}
render_pipeline: {URP|HDRP|BuiltIn}
unity_version: {version}
mcp_client: {claude-code|codex|...}
```

---

## 3. 프로젝트 로컬 문서

| 파일 | 역할 |
|---|---|
| `Docs/PIPELINE_STATE.md` | **진행 상태.** 세션 시작 시 첫 번째로 읽는다 |
| `Docs/Visual/VISUAL_SPEC.yaml` | 시각 계약 (authoritative) |
| `Docs/Visual/CONCEPT_ANALYSIS.yaml` | 컨셉 분석 결과 |
| `Docs/Visual/ASSET_CATALOG.json` | 승인 에셋 카탈로그 |
| `Docs/Visual/Reference/` | 컨셉아트 원본 |
| `Docs/Code/Tasks/` | Task Contract 들 |

---

## 4. 절대 규칙 (요약 — 상세는 키트 문서)

1. 비주얼 작업은 `VISUAL_SPEC.yaml` 이 authoritative. 형용사가 아니라 숫자를 따른다.
2. `ASSET_CATALOG.json` 밖의 에셋을 씬에 넣지 않는다. 없으면 `MISSING_` 처리.
3. Cube/Quad/기본 머티리얼은 `BLOCKOUT_` 접두사 + Blockout 루트에서만.
4. 코드 작업은 C1 Task Contract 부터. 요구를 검증 가능한 계약으로 먼저 고정한다.
5. 컴파일 성공은 완료가 아니다. `CODE_DOD.md` / `VISUAL_DOD.md` 를 충족해야 한다.
6. 테스트를 약화시켜 통과시키지 않는다.
7. Scene / Prefab / SerializeField / asmdef 변경은 고위험. 승인 대상.
8. `.meta` 를 임의 삭제하지 않는다.
9. 막히면 멈추고 구체적 선택지로 묻는다 (`ESCALATION.md`).

---

## 5. 스킬

| 스킬 | 언제 |
|---|---|
| `visual-director` | 모든 비주얼 Unity 태스크 |
| `unity-task-runner` | 모든 코드 Unity 태스크 |
| Unity 공식 skills | 위 두 스킬이 하위 도구로 호출 |

`visual-director` 와 `unity-task-runner` 가 상위 오케스트레이터,
Unity 공식 skills 가 하위 도구다. 순서를 뒤집지 않는다.

---

## 6. 프로젝트 고유 규칙

<!-- 이 프로젝트만의 규칙을 여기에 추가한다. 키트 규칙과 충돌하면 여기가 우선. -->
