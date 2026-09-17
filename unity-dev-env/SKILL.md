---
name: unity-dev-env
description: Unity 게임을 코딩 에이전트로 만들 때 비주얼 트랙(V1~V7)과 코드 트랙(C1~C6)을 게이트·증거 기반으로 진행시키는 파이프라인 키트. 환경 부트스트랩, 컨셉아트 반영, 화면 개선, 기능 구현, 버그 수정, 리팩터링 요청에 사용한다. Claude Code와 Codex에서 함께 쓴다.
---

# Unity AI 개발 파이프라인

코딩 에이전트가 **사용자 결정이나 수작업이 필요한 지점까지 스스로 굴러가게** 하는 키트다. 생성형 이미지 AI 없이 동작한다.

이 스킬 디렉터리는 Unity 프로젝트가 아니라 **재사용 템플릿 키트**다. 현재 읽은 `SKILL.md`의 부모를 `<skill-dir>`로 해석한다.

| 경로 | 역할 |
|---|---|
| `references/` | 파이프라인·정책·프로파일 참조 문서. 프로젝트로 복사하지 않고 여기서 읽는다 |
| `templates/` | 대상 Unity 프로젝트로 복사되는 실체 파일 |
| `scripts/` | 템플릿 주입기 |

`<PROJECT_ROOT>` = 대상 Unity 프로젝트 루트(`Packages/manifest.json`이 있는 디렉터리).

## 절대 규칙 (모든 것보다 우선)

1. 파괴적 작업 금지. [안전 규칙](references/policy/SAFETY_RULES.md)의 금지 목록을 위반하지 않는다.
2. 비주얼 에셋을 날조하지 않는다([에셋 정책](references/policy/ASSET_POLICY.md)). Cube·Quad·기본 머티리얼·즉석 PNG는 명시적 PROTOTYPE / BLOCKOUT 단계에서만 허용한다.
3. **컴파일 성공은 완료가 아니다.** 코드는 [CODE_DOD](references/policy/CODE_DOD.md), 비주얼은 [VISUAL_DOD](references/policy/VISUAL_DOD.md)가 완료 조건이다.
4. 테스트를 약화시켜 통과시키지 않는다. 코드를 고친다. 스펙이 바뀐 경우만 테스트를 고치고 신고한다.
5. 막히면 멈추고 묻는다. [에스컬레이션](references/policy/ESCALATION.md)의 STOP 조건에 걸리면 추측하지 말고 구체적 선택지와 추천을 제시한다.
6. 버전을 하드코딩하지 않는다. Unity CLI·Editor·패키지 버전은 실행 시점에 조회한다.
7. 확인하지 못한 것을 성공으로 보고하지 않는다. `PASS / PARTIAL / BLOCKED / FAILED` 중 하나로 보고한다.
8. 증거 없는 완료 보고 금지. 스크린샷·테스트 결과·로그가 실제 파일로 존재해야 한다.

## 트랙 선택

| 지시 유형 | 트랙 |
|---|---|
| 환경 세팅, Unity CLI 설치, 최초 시작 | **S0** |
| 컨셉아트 반영, 화면 개선, 비주얼 통일 | **V** (V1~V7) |
| 기능 추가, 버그 수정, 리팩터링 | **C** (C1~C6) |
| UI 코드, 카메라 스크립트, 셰이더 파라미터 제어 | **C + V 병행** (DoD 둘 다 충족) |

애매하면 **C로 시작한다.** C1 Task Contract가 비주얼 요구를 포함하면 V를 병행한다. 트랙·스테이지 그래프 전체는 [파이프라인](references/pipeline/PIPELINE.md)에 있다.

## Run Loop

```text
① <PROJECT_ROOT>/Docs/PIPELINE_STATE.md 읽기   없으면 키트 미적용 → S0 부터
② 트랙 판단 + 현재 스테이지 식별
③ 해당 스테이지 문서 1개 로드   references/pipeline/{S0|V{n}|C{n}}_*.md
   V 트랙이면 프로파일도        references/profiles/PROFILE_{3D|2D}.md
④ ENTRY GATE 검사              실패 → 선행 스테이지로 복귀 또는 에스컬레이션
⑤ STEPS 실행                   매 단계 STOP CONDITIONS 검사, 걸리면 즉시 중단·질문·BLOCKED 기록
⑥ EXIT GATE 검증               명령·린터·테스트·스크린샷 중 하나의 증거 필수
⑦ STATE 갱신 + 보고 + 커밋 → 다음 스테이지로 ①
```

문서를 한 번에 다 읽지 않는다. 각 문서 헤더의 `LOAD WHEN` 조건일 때만 연다. 전체 라우팅표는 [문서 색인](references/00_INDEX.md)이다.

**한 응답에서 여러 스테이지를 건너뛰지 않는다.** 게이트를 통과한 만큼만 진행한다.

## 키트 적용

대상 프로젝트에 템플릿을 주입한다. 파이썬 쪽이 기본이고 어느 OS·에이전트에서나 같은 결과를 낸다.

```text
python3 <skill-dir>/scripts/apply_kit.py --project-root "<PROJECT_ROOT>" --profile 3d|2d [--mode greenfield|rebase] [--force] [--dry-run]
```

Windows PowerShell만 쓸 수 있으면 `<skill-dir>/scripts/apply-kit.ps1 -ProjectRoot "<PROJECT_ROOT>" -Profile 3d -Mode greenfield`로 같은 일을 한다.

생성물은 프로젝트 루트의 `AGENTS.md`(+ `CLAUDE.md` 링크), `Docs/PIPELINE_STATE.md`, `Docs/Visual/VISUAL_SPEC.yaml`·`CONCEPT_ANALYSIS.yaml`·`ASSET_CATALOG.json`, `Docs/Code/TASK_TEMPLATE.yaml`, `.claude/skills/`와 `.agents/skills/`의 `visual-director`·`unity-task-runner`, `Assets/Editor/AIVisual/*.cs`다. 기존 파일은 `--force` 없이 덮어쓰지 않는다.

**프로파일(3d/2d)과 모드(greenfield/rebase)를 모르면 추측하지 않고 묻는다.** 파이프라인 경로 자체가 달라진다.

## 문서 라우팅

| 상황 | 문서 |
|---|---|
| 환경 설치·검증 | [S0 BOOTSTRAP](references/pipeline/S0_BOOTSTRAP.md) |
| "물어봐야 하나?" | [ESCALATION](references/policy/ESCALATION.md) |
| 설치·삭제·설정 변경 직전 | [SAFETY_RULES](references/policy/SAFETY_RULES.md) |
| `unity` CLI 문법 | [UNITY_CLI](references/guides/UNITY_CLI.md) — 최종 권위는 실행 시점의 `unity <cmd> --help` |
| 파일 이동·삭제·이름변경, 위험도 판정 | [UNITY_RISK_ZONES](references/guides/UNITY_RISK_ZONES.md) |

**V 트랙** — 컨셉 분해 [V1](references/pipeline/V1_CONCEPT_DECOMPOSITION.md) · 카메라/조명/셰이더 기반 [V2](references/pipeline/V2_VISUAL_FOUNDATION.md) · 블록아웃 [V3](references/pipeline/V3_BLOCKOUT.md) · 컨셉 대 렌더 수렴 [V4](references/pipeline/V4_GOLDEN_SCENE.md) + [스크린샷 루프](references/guides/SCREENSHOT_LOOP.md) · 에셋 조달 [V5](references/pipeline/V5_ASSET_STRATEGY.md) + [무료 에셋](references/guides/FREE_ASSETS.md) · 게임플레이 이식 [V6](references/pipeline/V6_GAMEPLAY_MIGRATION.md) · 전 씬 적용 [V7](references/pipeline/V7_FULL_MIGRATION.md) · 자동 검사 [VISUAL_LINTER_SPEC](references/guides/VISUAL_LINTER_SPEC.md) · 프로파일 [3D](references/profiles/PROFILE_3D.md) / [2D](references/profiles/PROFILE_2D.md)

**C 트랙** — 요구 계약 [C1](references/pipeline/C1_TASK_CONTRACT.md) · 기존 코드 탐색 [C2](references/pipeline/C2_CONTEXT_DISCOVERY.md) + [CODE_ARCHITECTURE](references/guides/CODE_ARCHITECTURE.md) · 영향·위험도 [C3](references/pipeline/C3_IMPACT_ANALYSIS.md) · STEP 분할 [C4](references/pipeline/C4_IMPLEMENTATION_PLAN.md) · 구현·검증 [C5](references/pipeline/C5_IMPLEMENT_VERIFY.md) + [TEST_STRATEGY](references/guides/TEST_STRATEGY.md) · diff 게이트 [C6](references/pipeline/C6_DIFF_GATE.md) + [GIT_WORKFLOW](references/guides/GIT_WORKFLOW.md)

## 게이트와 중단

- 게이트는 자기 신고로 통과할 수 없다. 검증 명령·린터·테스트 결과·스크린샷 중 하나의 증거가 있어야 한다.
- 게이트 검증이 **불가능한 경우**(Editor 미실행, 라이선스 없음)는 `PASS`가 아니라 `BLOCKED`다.
- 사용자 승인이 필수인 게이트: V1, V4, V5, C3(고위험). 에이전트 단독 통과 불가.
- V3/V4/V7 반복은 **루프당 상위 3개 변경만**, 1루프 1카테고리로 제한한다. 변수를 동시에 바꾸면 무엇이 효과였는지 판단할 수 없다.
- STOP에 걸리면 [에스컬레이션](references/policy/ESCALATION.md) §3 템플릿으로 선택지 2~4개 + 각각의 결과·되돌리기 난이도 + 추천을 제시한다. 결정과 무관하게 진행 가능한 작업은 먼저 끝내놓고 묻는다.
- 사소한 것마다 묻지 않는다. 파일명·폴더 생성·린터 실행·스크린샷 촬영·테스트 실행·다음 스테이지 진행은 그냥 한다(에스컬레이션 §5).
- 받은 결정은 `PIPELINE_STATE.md`의 `decisions:`에 기록하고 **같은 질문을 다시 하지 않는다.**

## 상태와 보고

매 스테이지 종료 시 `<PROJECT_ROOT>/Docs/PIPELINE_STATE.md`를 갱신한다. 새 세션에서 "이어서 해줘"라고 하면 **이 파일만 읽어도 어디서부터인지 알 수 있어야 한다.**

```markdown
## {S0|V{n}|C{n}} {STAGE_NAME} — {PASS | PARTIAL | BLOCKED | FAILED}

### 한 일
### 검증 결과 (증거 경로 포함)
### 변경된 파일
### 커밋 / 푸시
### 다음 스테이지 ENTRY GATE
### 사용자 결정 필요 (있으면 에스컬레이션 템플릿)
### 가정 (ASSUME 한 것)
```

코드 트랙 최종 보고는 [CODE_DOD](references/policy/CODE_DOD.md) §5, 비주얼 트랙은 [VISUAL_DOD](references/policy/VISUAL_DOD.md) §6 형식을 쓴다. 스테이지·태스크 완료 시 원자적 커밋과 push를 하되([GIT_WORKFLOW](references/guides/GIT_WORKFLOW.md)), 기본 브랜치에서 작업 중이면 브랜치 생성을 먼저 제안하고 Scene·Prefab 커밋은 코드 커밋과 분리한다.

## 에이전트 공통

- 대상 프로젝트의 진입점은 `AGENTS.md`이고 `CLAUDE.md`는 그 링크다. Claude Code와 Codex가 같은 규칙을 읽는다.
- 프로젝트에 설치되는 `visual-director`·`unity-task-runner`가 상위 오케스트레이터, Unity 공식 skills가 하위 도구다. 순서를 뒤집지 않는다.
- Unity 공식 skills는 미술 능력을 추가하지 않는다. 에이전트가 Unity를 잘못 만지는 비율을 줄일 뿐이고, 실제 비주얼 개선은 V1~V7의 규칙과 검수가 만든다.
