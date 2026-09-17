# CODE_ARCHITECTURE — 에이전트 친화적 Unity 구조

> LOAD WHEN: C2 에서 레이어 배치를 결정할 때. 새 모듈/asmdef 를 만들 때.

---

## 1. 왜 구조가 파이프라인보다 중요한가

코딩 에이전트를 쓰면 Unity 프로젝트 설계 기준이 바뀐다.

```
기존:  사람이 이해하기 좋은 코드

이제:  사람이 이해하기 좋은 코드
     + 에이전트가 탐색하기 좋은 구조
     + 에이전트가 검증하기 좋은 구조
     + 잘못 건드리기 어려운 구조
```

마지막 항목이 특히 중요하다. **문서로 금지하는 것보다 물리적으로 불가능하게 만드는 것이 강하다.**

---

## 2. 3층 구조

```
┌─────────────────────────────┐
│      Game / Domain Logic    │   순수 C#            ← 여기를 크게 만든다
│  Unity 참조 없음. Unity 없이 테스트 가능            │
├─────────────────────────────┤
│       Unity Adapter         │   MonoBehaviour / Component
│  입력·수명주기·렌더를 Domain 에 연결               │
├─────────────────────────────┤
│       Content Wiring        │   Scene / Prefab / Inspector
│  데이터 배선. 코드가 아님. 고위험 영역             │
└─────────────────────────────┘
```

### 나쁜 구조
```
PlayerController.cs
 ├ Input
 ├ Movement
 ├ Attack
 ├ Damage Calculation
 ├ Animation
 ├ Sound
 ├ Enemy Detection
 ├ Cooldown
 └ VFX
```
전부 한 MonoBehaviour 안. 에이전트가 어디를 고쳐도 다른 것이 깨진다. 테스트가 불가능하다.

### 좋은 구조
```
CombatModel.cs          Domain    순수 C#. 쿨다운·데미지·판정 로직
    ↓
CombatController.cs     Adapter   MonoBehaviour. 입력 → Model
    ↓
PlayerCombatView.cs     Adapter   애니메이션·VFX·사운드
    ↓
Player.prefab           Wiring    Inspector 배선
```

### 순수 C# 영역을 크게 만드는 이유

| 효과 | 설명 |
|---|---|
| **Unity 없이 테스트** | Editor 를 띄우지 않고 검증 가능 → 루프가 빨라짐 |
| **위험도 하락** | 순수 계산 로직은 C3 기준 "낮음". 검증 비용 최소 |
| **에이전트 정확도 상승** | 직렬화·수명주기 함정이 없음 |
| **회귀 탐지** | 테스트로 즉시 잡힘 |

**Domain 에 넣을 수 있는 것을 MonoBehaviour 에 넣지 않는다.**

Domain 후보:
```
데미지 계산 / 상태 전환 / 인벤토리 계산 / 경험치 / 스킬 쿨다운
AI 판단 / 세이브 데이터 변환 / 밸런스 공식 / 아이템 조합 / 퀘스트 조건
```

---

## 3. 폴더 구조 (권장)

```
Assets/
├─ Scripts/
│  ├─ Core/            Game.Core.asmdef          공용 타입, 유틸, 이벤트
│  ├─ Combat/          Game.Combat.asmdef
│  │  ├─ Domain/          순수 C#
│  │  └─ Unity/           MonoBehaviour
│  ├─ Inventory/       Game.Inventory.asmdef
│  ├─ AI/              Game.AI.asmdef
│  └─ UI/              Game.UI.asmdef
├─ Editor/             Game.Editor.asmdef
│  └─ AIVisual/           GameViewCapture / ConceptOverlay / VisualLinter
├─ Tests/
│  ├─ EditMode/        Game.Tests.EditMode.asmdef
│  ├─ PlayMode/        Game.Tests.PlayMode.asmdef
│  └─ Scenes/             *SmokeTest.unity
├─ Art/
│  ├─ Approved/
│  ├─ Experimental/
│  └─ Missing/
├─ VisualRebuild/
└─ VisualTests/
```

각 기능 모듈 안에서 `Domain/` 과 `Unity/` 를 분리하면 에이전트가 레이어를 헷갈리지 않는다.

---

## 4. asmdef 경계

Assembly Definition 은 컴파일 시간만을 위한 것이 아니다.
**에이전트에게 물리적 아키텍처 경계를 준다.**

```
Game.Core
Game.Combat
Game.Inventory
Game.AI
Game.UI

Game.Editor

Game.Tests.EditMode
Game.Tests.PlayMode
```

참조 규칙 예:
```
Combat → Core     허용
Combat → UI       금지     ← asmdef 로 참조 자체를 불가능하게
UI     → Combat   허용
```

```
문서에 "Combat 이 UI 를 참조하면 안 돼" 라고 적어두는 것보다
asmdef 로 실제로 참조가 불가능하게 만드는 편이 훨씬 강력하다.
```

### 규칙
- Runtime / Editor / Test 어셈블리를 분리한다.
- 참조는 명시적으로 구성한다. `Auto Referenced` 남용 금지.
- **asmdef 변경은 고위험**(C3). 신설·참조 변경은 사용자 승인 대상.
- 순환 참조가 생기면 설계가 틀린 것이다. 이벤트/인터페이스로 방향을 뒤집는다.

---

## 5. 에이전트가 탐색하기 좋은 규칙

```
[ ] 폴더 이름 = 도메인 이름 (기술 이름 아님)
[ ] 클래스 1개 = 파일 1개, 파일명 = 클래스명
[ ] 한 클래스의 책임은 한 문장으로 설명 가능
[ ] 이름에서 레이어가 드러남 (Model / Controller / View / Service)
[ ] 매직넘버 금지 — 상수 또는 ScriptableObject
[ ] 전역 상태 최소화, Singleton 신규 도입은 신고 대상 (C6)
[ ] public API 는 최소화. 필요 없으면 internal/private
```

---

## 6. 새 코드를 어디에 넣을지 결정 순서

```
① 순수 계산인가?                  → Domain (순수 C#)
② Unity 수명주기가 필요한가?       → Adapter (MonoBehaviour)
③ 데이터 배선인가?                → Wiring (Prefab/Scene) — 고위험, 승인 필요
④ 에디터 전용인가?                → Editor asmdef
⑤ 이미 같은 일을 하는 곳이 있는가? → 거기를 확장 (신규 생성 금지)  ★
```

⑤ 를 건너뛰면 같은 책임의 시스템이 둘씩 생긴다. C2 의 핵심 점검 항목이다.
