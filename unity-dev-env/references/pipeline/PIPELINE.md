# PIPELINE — 트랙, 스테이지 그래프, 게이트

> LOAD WHEN: 어느 트랙/스테이지인지 판단이 필요할 때. 상태 파일이 없거나 모순될 때.

---

## 1. 전체 구조

```
                         S0 BOOTSTRAP
                     (환경 표준화 — 공유)
                              │
              ┌───────────────┴───────────────┐
              │                               │
       V 트랙 (비주얼)                   C 트랙 (코드)
   "원하는 모습을 재현하는가"     "변경→검증→영향확인→안전통합이 도는가"
              │                               │
   V1 Concept Decomposition        C1 Task Contract
   V2 Visual Foundation            C2 Context Discovery
   V3 Blockout                     C3 Impact Analysis
   V4 Golden Scene                 C4 Implementation Plan
   V5 Asset Strategy               C5 Implement & Verify
   V6 Gameplay Migration           C6 Diff Gate
   V7 Full Migration
              │                               │
              └───────────────┬───────────────┘
                              │
                            Game
```

대응 관계:
```
Visual:  Reference     → Generation → Import → Integration  → Visual QA
Code:    Specification → Context    → Impl   → Verification → Integration QA
```

---

## 2. 트랙 선택

| 지시 유형 | 트랙 |
|---|---|
| 환경 세팅, Unity CLI 설치, 최초 시작 | S0 |
| 컨셉아트 반영, 화면 개선, 비주얼 통일 | V |
| 기능 추가, 버그 수정, 리팩터링 | C |
| UI 코드 / 카메라 스크립트 / 셰이더 파라미터 제어 | C + V 병행 |

애매하면 **C 로 시작**한다. C1 Task Contract 가 비주얼 요구를 포함하면 V 를 병행한다.

---

## 3. V 트랙 — 왜 순서가 중요한가

비주얼이 나쁜 상태에서 나무 하나부터 고치면, 그 새 나무는
**옛 카메라 + 옛 조명 + 옛 머티리얼 + 옛 지형** 속에 들어간다. 그래서 새 나무마저 이상해 보인다.

항상 **화면 점유 영향이 큰 것부터** 고정한다.

```
Camera            30%
Lighting          25%
Environment mass  20%
Palette           15%
Small props        5%
etc.               5%
```

작은 prop 이나 버튼을 먼저 만지는 것은 거의 항상 낭비다.

### V 스테이지 그래프

```
V1 CONCEPT DECOMPOSITION   컨셉아트 → 측정치/규칙
    GATE: CONCEPT_ANALYSIS + VISUAL_SPEC 확정 (사용자 승인 필수)
V2 VISUAL FOUNDATION       카메라 / 월드스케일 / 조명 / Volume / 마스터 셰이더
    GATE: 캘리브레이션 큐브만으로 컨셉의 톤이 보임
V3 BLOCKOUT                큰 형태와 실루엣만
    GATE: 오버레이 대비 실루엣 일치, Camera/Scale/Composition ≥4
V4 GOLDEN SCENE            컨셉 vs 렌더 수렴 루프
    GATE: 9항목 전부 ≥4, 린터 0 error, 사용자 합격 승인 필수
V5 ASSET STRATEGY          블록아웃을 무엇으로 대체할지
    GATE: ASSET_CATALOG 채워짐, 미해결은 전부 VISUAL_MISSING (사용자 승인 필수)
V6 GAMEPLAY MIGRATION      기존 게임플레이 이식 (rebase 모드만)
    GATE: 기능 회귀 없음 + 린터 PASS
V7 FULL MIGRATION          나머지 씬 전수
    GATE: 전 씬 린터 PASS + 스코어카드 ≥4
```

### V 트랙 진입 모드

| 모드 | 경로 | 설명 |
|---|---|---|
| **GREENFIELD** | V1→V2→V3→V4→V5→V7 | 신규 프로젝트. V6 생략 |
| **VISUAL REBASE** | V1→V2→V3→V4→V5→V6→V7 | 기존 프로젝트 전면 개선 |

**REBASE 에서 기존 씬을 직접 고치지 않는다.**
`VisualRebuild.unity` 라는 새 씬을 처음부터 만들고, V4 를 통과한 뒤에야 기존 게임플레이를 끌어온다.
기존 비주얼의 잘못된 전제가 새 디자인을 오염시키는 것을 막기 위해서다.

모드는 `PIPELINE_STATE.md` 의 `mode:` 에 기록한다.

---

## 4. C 트랙 — 왜 순서가 중요한가

```
요구사항 → 코드 탐색 → 영향 범위 → 계획 → 최소 수정
→ 컴파일 → 테스트 → Unity 통합 → PlayMode → Diff 검토 → 커밋
```

`"기능 구현해"` 를 그대로 주는 것과 위를 강제하는 것의 품질 차이가 크다.

각 단계를 생략했을 때 실제로 일어나는 일:

| 생략 | 결과 |
|---|---|
| C1 Task Contract | 에이전트가 추측으로 스펙을 만든다. 재작업 |
| C2 Context Discovery | **기존 시스템이 있는데 비슷한 것을 하나 더 만든다** |
| C3 Impact Analysis | SerializeField 리네임으로 Inspector 값이 날아간다 |
| C4 Implementation Plan | `47 files changed` 후 "완료했습니다" |
| C5 Verify | 컴파일만 되고 런타임에 터진다 |
| C6 Diff Gate | 요구와 무관한 변경이 조용히 섞인다 |

### C 스테이지 그래프

```
C1 TASK CONTRACT          Goal / AC / non_goals / invariants / out_of_bounds
    GATE: AC 가 전부 검증 가능한 문장, 남은 DECISION 0
C2 CONTEXT DISCOVERY      관련 코드·기존 패턴·레이어·asmdef
    GATE: "같은 일을 하는 기존 시스템" 유무를 명시적으로 확인
C3 IMPACT ANALYSIS        위험도 분류 → 검증 레벨 결정
    GATE: 검증 레벨 확정, 고위험이면 사용자 승인
C4 IMPLEMENTATION PLAN    원자적 STEP 분할, 고위험 격리, AC-테스트 매핑
    GATE: 모든 AC 에 테스트가 매핑됨
C5 IMPLEMENT & VERIFY     compile → EditMode → PlayMode → Smoke → Console 0
    GATE: Compiler Error 0, 테스트 PASS, 회귀 없음, 테스트 약화 없음
C6 DIFF GATE              자기 심문 → 원자적 커밋 → push → 보고
    GATE: 계약 범위 밖 변경 0, 커밋 분리, 보고서 작성
```

### C 트랙 위험도별 검증 레벨 (C3 산출)

| 위험도 | 검증 |
|---|---|
| 저 — 순수 계산 로직 | Compile + Unit/EditMode |
| 중 — MonoBehaviour | Compile + Test + PlayMode |
| 고 — SerializeField / Prefab / Scene / SO / asmdef | + Asset/Prefab Diff + Reference 확인 |
| 매우 높음 — Input / Addressables / Build Settings | + 빌드 검증 + 사용자 확인 |

---

## 5. 게이트 규칙 (양 트랙 공통)

1. **게이트는 자기 신고로 통과할 수 없다.** 검증 명령 / 린터 / 테스트 결과 / 스크린샷 중 하나의 증거 필수.
2. 게이트 실패 시 **다음 스테이지로 진행하지 않는다.** 원인을 상태 파일에 기록하고 보고한다.
3. 게이트 검증이 **불가능한 경우**(Editor 미실행, 라이선스 없음 등)는 `PASS` 가 아니라 `BLOCKED`.
4. **사용자 승인이 필수인 게이트:** V1, V4, V5, C3(고위험 시). 에이전트 단독 통과 불가.

---

## 6. 반복(iteration) 규칙 — V3/V4/V7

- **한 번에 전체를 고치지 않는다.** 루프당 상위 우선순위 **3개 변경만.**
- 1개 루프 = 1개 카테고리 (Iteration 01 Camera → 02 Lighting → 03 Terrain → …).
- 변수를 동시에 많이 바꾸면 무엇 때문에 좋아졌는지 판단 불가.
- 각 루프는 스크린샷 증거를 남긴다: `Assets/VisualTests/Screenshots/iter_{nn}_{category}.png`

상세: `references/guides/SCREENSHOT_LOOP.md`

---

## 7. 스테이지 문서의 고정 섹션

모든 `S0_*.md` / `V{n}_*.md` / `C{n}_*.md` 는 아래 섹션을 가진다.

| 섹션 | 의미 |
|---|---|
| `LOAD WHEN` | 이 문서를 읽어야 하는 조건 |
| `ENTRY GATE` | 시작 전 만족해야 할 조건 (실패 시 진행 금지) |
| `INPUTS` | 필요한 파일/정보 |
| `STEPS` | 실행 절차 |
| `STOP CONDITIONS` | 걸리면 즉시 중단하고 사용자에게 질문 |
| `EXIT GATE` | 통과 판정 기준 + 검증 방법 |
| `OUTPUTS` | 산출물 경로 |
| `STATE UPDATE` | 상태 파일에 기록할 내용 |

---

## 8. 두 트랙이 만나는 지점

| 지점 | 내용 |
|---|---|
| **S0** | 환경은 공유. Unity CLI / Pipeline / MCP 는 양쪽 모두가 쓴다 |
| **Scene/Prefab** | V 트랙의 배선이자 C 트랙의 고위험 영역. `UNITY_RISK_ZONES.md` 를 양쪽이 참조 |
| **UI 작업** | 코드 구조(C)와 디자인 토큰(V)이 동시에 걸림 → DoD 둘 다 충족 |
| **V6 Gameplay Migration** | Gameplay/Presentation 분리는 C 트랙의 리팩터링 규칙을 따름 |
| **완료 보고** | 화면에 영향 있는 코드 변경은 `CODE_DOD` + `VISUAL_DOD` 둘 다 |
