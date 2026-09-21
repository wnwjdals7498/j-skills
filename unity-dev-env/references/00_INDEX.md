# 00_INDEX — 문서 라우팅 테이블

> 에이전트용. **전부 읽지 마라.** 지금 상황에 맞는 것만 로드한다.
> 각 문서 헤더의 `LOAD WHEN:` 조건이 아니면 열지 않는다.

## 읽기 순서 (최초 1회)

1. `<skill-dir>/SKILL.md` — 진입점, 트랙 선택, Run Loop, 절대 규칙
2. `references/pipeline/PIPELINE.md` — 트랙/스테이지 그래프와 게이트 전체 그림
3. 현재 트랙의 현재 스테이지 문서 1개
4. (V 트랙이면) 프로파일 1개

---

## references/pipeline/ — 무엇을 어떤 순서로

### 공유
| 문서 | LOAD WHEN | 산출물 |
|---|---|---|
| `references/pipeline/PIPELINE.md` | 트랙/스테이지 판단이 필요할 때 | — |
| `references/pipeline/S0_BOOTSTRAP.md` | CLI/Editor/Skills/Pipeline/MCP 미검증 | 환경 PASS, `PIPELINE_STATE.md` 초기화 |

### V 트랙 (비주얼)
| 문서 | LOAD WHEN | 산출물 |
|---|---|---|
| `references/pipeline/V1_CONCEPT_DECOMPOSITION.md` | 컨셉아트 있고 미분석 | `CONCEPT_ANALYSIS.yaml`, `VISUAL_SPEC.yaml` |
| `references/pipeline/V2_VISUAL_FOUNDATION.md` | SPEC 확정, 씬 기반 미제작 | `VisualRebuild.unity`, CameraRig, LightingRig, VP_Global, MasterShader |
| `references/pipeline/V3_BLOCKOUT.md` | Foundation 완료, 형태 미확정 | Blockout 지오메트리 |
| `references/pipeline/V4_GOLDEN_SCENE.md` | Blockout 완료 | Golden Scene PASS, 스코어카드 ≥4 |
| `references/pipeline/V5_ASSET_STRATEGY.md` | Golden Scene PASS 후 실제 에셋 필요 | `ASSET_CATALOG.json`, Replacement Matrix |
| `references/pipeline/V6_GAMEPLAY_MIGRATION.md` | rebase 모드, 기존 게임플레이 이식 | Gameplay/Presentation 분리 |
| `references/pipeline/V7_FULL_MIGRATION.md` | 나머지 씬 확대 | 전 씬 린터 PASS |

### C 트랙 (코드)
| 문서 | LOAD WHEN | 산출물 |
|---|---|---|
| `references/pipeline/C1_TASK_CONTRACT.md` | 코드 작업 지시를 받았을 때 (**항상 첫 단계**) | `TASK-{nnnn}.yaml` |
| `references/pipeline/C2_CONTEXT_DISCOVERY.md` | C1 PASS | `TASK-{nnnn}.context.md` |
| `references/pipeline/C3_IMPACT_ANALYSIS.md` | C2 PASS | `TASK-{nnnn}.impact.md`, 검증 레벨 |
| `references/pipeline/C4_IMPLEMENTATION_PLAN.md` | C3 PASS | `TASK-{nnnn}.plan.md`, STEP 분할 |
| `references/pipeline/C5_IMPLEMENT_VERIFY.md` | C4 PASS (**여기서 처음 코드를 쓴다**) | 코드 + 검증 결과 |
| `references/pipeline/C6_DIFF_GATE.md` | C5 PASS | 원자적 커밋, 최종 보고 |

---

## references/policy/ — 무엇을 하면 안 되는가 / 언제 멈추는가

| 문서 | LOAD WHEN |
|---|---|
| `references/policy/ESCALATION.md` | **상시.** 판단이 갈리거나 정보가 없을 때 |
| `references/policy/SAFETY_RULES.md` | 설치·삭제·설정 변경 직전 (**S0 필수**) |
| `references/policy/ASSET_POLICY.md` | 씬에 보이는 오브젝트를 만들기 직전 (**V2~V7 상시**) |
| `references/policy/VISUAL_DOD.md` | 비주얼 작업을 완료 보고하기 직전 |
| `references/policy/CODE_DOD.md` | 코드 작업을 완료 보고하기 직전 |

---

## references/guides/ — 어떻게 하는가

### 공유
| 문서 | LOAD WHEN |
|---|---|
| `references/guides/UNITY_CLI.md` | `unity` 명령을 쓰기 직전 (문법은 항상 `--help` 재확인) |
| `references/guides/UNITY_RISK_ZONES.md` | 위험도 판정 / 파일 이동·삭제·이름변경 직전 (**양 트랙**) |

### V 트랙
| 문서 | LOAD WHEN |
|---|---|
| `references/guides/SCREENSHOT_LOOP.md` | V3/V4/V7 에서 렌더를 컨셉과 비교할 때 |
| `references/guides/VISUAL_LINTER_SPEC.md` | 자동 검사 스크립트를 구현/수정할 때 |
| `references/guides/FREE_ASSETS.md` | V5 에서 외부 에셋 도입 검토 |

### C 트랙
| 문서 | LOAD WHEN |
|---|---|
| `references/guides/CODE_ARCHITECTURE.md` | C2 레이어 배치 결정, 새 모듈/asmdef 생성 |
| `references/guides/TEST_STRATEGY.md` | C4 테스트 설계, C5 테스트 실행 |
| `references/guides/GIT_WORKFLOW.md` | C6 커밋, 브랜치/푸시 전략 |

---

## references/profiles/ — 3D 인가 2D 인가 (V 트랙)

| 문서 | LOAD WHEN |
|---|---|
| `references/profiles/PROFILE_3D.md` | 3D (URP/HDRP, 메시 기반) |
| `references/profiles/PROFILE_2D.md` | 2D (스프라이트/타일맵 기반) |

프로파일은 **공통 파이프라인을 덮어쓰지 않고 채운다.** 스테이지 문서가 뼈대, 프로파일이 수치/규칙.

---

## templates/ — 프로젝트로 복사되는 것

| 경로 | 설명 |
|---|---|
| `templates/project-root/AGENTS.md` | 대상 프로젝트 루트의 얇은 진입점 (이 키트를 가리킴) |
| `templates/project-root/Docs/PIPELINE_STATE.md` | 진행 상태 체크포인트 |
| `templates/project-root/Docs/Visual/VISUAL_SPEC.3d.yaml` | 3D 시각 계약 |
| `templates/project-root/Docs/Visual/VISUAL_SPEC.2d.yaml` | 2D 시각 계약 |
| `templates/project-root/Docs/Visual/CONCEPT_ANALYSIS.yaml` | V1 산출물 |
| `templates/project-root/Docs/Visual/ASSET_CATALOG.json` | 승인 에셋 카탈로그 |
| `templates/project-root/Docs/Code/TASK_TEMPLATE.yaml` | C1 Task Contract |
| `templates/skills/visual-director/SKILL.md` | 비주얼 오케스트레이션 스킬 |
| `templates/skills/unity-task-runner/SKILL.md` | 코드 트랙 오케스트레이션 스킬 |
| `templates/unity/Editor/*.cs` | GameViewCapture / ConceptOverlay / VisualLinter |

주입은 `scripts/apply_kit.py`(모든 OS) 또는 `scripts/apply-kit.ps1`(Windows PowerShell)로 한다.

---

## references/source/ — 원본 (수정 금지)

| 파일 | 내용 |
|---|---|
| `references/source/UNITY_AI_ENVIRONMENT_BOOTSTRAP_PROMPT.md` | S0 원본 마스터 프롬프트. 부트스트랩 보고서 형식(§12)과 CLI 명령 문법의 원본 |

스테이지 문서와 충돌하면 **스테이지 문서가 우선**한다.
단 S0 의 CLI 명령 문법이 의심스러우면 원본을 확인해도 된다. 그보다 우선하는 권위는 `unity <cmd> --help`.
