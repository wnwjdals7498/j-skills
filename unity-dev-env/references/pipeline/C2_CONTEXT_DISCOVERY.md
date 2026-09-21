# C2 — CONTEXT DISCOVERY (관련 코드 탐색)

> LOAD WHEN: C1 = PASS. **여기서도 코드를 쓰지 않는다.**

이 단계를 생략하면 에이전트가 가장 자주 하는 실수가 나온다:
**기존 시스템이 있는데 비슷한 새 시스템을 하나 더 만든다.**
그러면 같은 책임을 가진 시스템이 프로젝트 안에 둘씩 생긴다.

---

## ENTRY GATE
- C1 = `PASS` (Task Contract 존재)

## INPUTS
- `Docs/Code/Tasks/TASK-{nnnn}.yaml`
- 프로젝트 소스 트리

---

## STEPS

### 2-A. 관련 코드 열거

Task Contract 의 명사·동사에서 검색 키워드를 뽑아 탐색한다.

```
[ ] 관련 MonoBehaviour / 클래스
[ ] 관련 ScriptableObject
[ ] 관련 인터페이스 / 추상 클래스
[ ] 관련 asmdef 와 그 참조 관계
[ ] 관련 EditMode / PlayMode 테스트
[ ] 관련 Prefab / Scene
[ ] 관련 입력 액션 (Input System)
[ ] 관련 이벤트 / 메시지 버스
```

예시 산출:
```
PlayerController.cs        Assets/Scripts/Player/       입력+이동 담당
CombatSystem.cs            없음                          ← 미존재 확인
Health.cs                  Assets/Scripts/Common/       HP + OnDeath 이벤트
Enemy.cs                   Assets/Scripts/Enemy/        Health 참조
EnemyDetector.cs           Assets/Scripts/Enemy/        OverlapSphere+각도 패턴 존재 ★
Game.Core.asmdef           Assets/Scripts/Core/
Game.Combat.asmdef         없음                          ← 신설 필요 여부 판단
PlayerTests.cs             Assets/Tests/EditMode/       18개 테스트
```

### 2-B. 책임 소재 판단 (가장 중요)

```
현재 이 책임은 어디에 있는가?
        ↓
새 기능은 어느 모듈에 들어가야 하는가?
        ↓
이미 같은 일을 하는 기존 패턴이 있는가?     ★ 반드시 확인
        ↓
새 클래스가 정말 필요한가? 아니면 기존 확장인가?
```

**"비슷한 것이 이미 있는가"** 를 확인하지 않고 새 클래스를 만들지 않는다.
있으면 그 패턴을 따른다 (`EnemyDetector` 의 판정 방식을 재사용 등).

### 2-C. 아키텍처 레이어 배치 결정

`references/guides/CODE_ARCHITECTURE.md` 3층 구조에 매핑한다.

```
┌─────────────────────────────┐
│      Game / Domain Logic    │  순수 C#  ← 여기를 크게 만든다
├─────────────────────────────┤
│       Unity Adapter         │  MonoBehaviour / Component
├─────────────────────────────┤
│       Content Wiring        │  Scene / Prefab / Inspector
└─────────────────────────────┘
```

각 신규/수정 요소를 어느 층에 놓을지 명시한다.
```
CombatModel.cs        Domain      순수 C# — Unity 없이 테스트 가능
PlayerCombat.cs       Adapter     MonoBehaviour, 입력 → Model 호출
Player.prefab         Wiring      명시 요청 없으면 건드리지 않음
```

**순수 C# 영역을 크게 만들수록 Unity 를 띄우지 않고 검증할 수 있다.** 에이전트 친화적 구조의 핵심.

### 2-D. asmdef 경계 확인

```
Combat → Core     참조 가능?
Combat → UI       참조 금지?
UI     → Combat   참조 가능?
```

asmdef 는 **문서로 적어둔 규칙보다 강력하다** — 참조가 물리적으로 불가능해진다.
새 asmdef 신설은 **고위험 변경**이다 (C3 참조). 승인 대상.

### 2-E. 발견 사항 기록

```
Docs/Code/Tasks/TASK-{nnnn}.context.md
```

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 같은 책임의 기존 시스템 발견 — 확장 vs 신설 | DECISION | 두 안의 영향 범위 비교 후 질문 |
| asmdef 신설/참조 변경 필요 | RISK | 승인 요청 |
| 코드가 비주얼/게임플레이에 강결합 | CONFLICT | 리팩터링 vs 우회 선택지 |
| 관련 코드를 찾을 수 없음 (프로젝트가 비어 있음) | DECISION | 신규 구조 설계안 제시 |
| 기존 테스트가 없어 회귀 검증이 불가 | DECISION | 테스트 먼저 작성할지 질문 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 관련 파일 목록이 경로와 함께 열거됨 |
| 2 | "같은 일을 하는 기존 시스템" 유무가 **명시적으로 확인**됨 |
| 3 | 신규/수정 요소가 3층 중 어디에 속하는지 매핑됨 |
| 4 | asmdef 참조 방향이 확인됨 |
| 5 | 관련 기존 테스트 목록이 확보됨 |

## OUTPUTS
- `Docs/Code/Tasks/TASK-{nnnn}.context.md`

## STATE UPDATE
```yaml
stage: C2
status: PASS | BLOCKED
related_files: [...]
existing_pattern_found: EnemyDetector (OverlapSphere+angle)
layer_plan: {CombatModel: domain, PlayerCombat: adapter}
```
