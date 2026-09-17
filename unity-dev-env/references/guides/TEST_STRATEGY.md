# TEST_STRATEGY — 3단 검증

> LOAD WHEN: C4 에서 테스트를 설계할 때. C5 에서 테스트를 실행할 때.

---

## 1. 3단 구성

```
Pure C# Unit Test  ┐
                   ├─ 빠른 검증 (Unity 불필요 / 에디터만)
EditMode Test      ┘
        ↓
PlayMode Test        Unity 통합 검증
        ↓
Smoke Test           상태·순서 검증
```

Unity Test Framework 가 EditMode / PlayMode 를 공식 지원한다.

---

## 2. 어디에 무엇을 넣는가

### Pure C# Unit / EditMode — 빠름, 대부분 여기

```
데미지 계산
상태 전환
인벤토리 계산
경험치
스킬 쿨다운
AI 판단 로직
세이브 데이터 변환
밸런스 공식
```

`CODE_ARCHITECTURE.md` 의 Domain 층이 크면 이 영역이 커진다. **의도적으로 크게 만든다.**

### PlayMode — Unity 통합

```
GameObject 생성
  ↓ Component 연결
  ↓ 몇 프레임 실행
  ↓ 결과 검증
```

물리, 코루틴, Animator, 프레임 기반 로직, 컴포넌트 간 상호작용.

### Smoke — 상태와 순서

Unit/Integration 으로는 못 잡는 **초기화 순서 버그**를 잡는다.

```
Player Spawn → Awake → OnEnable → Start → Input 활성화
→ Animator 초기화 → Enemy Spawn → Physics Update
```

전용 씬:
```
Assets/Tests/Scenes/CombatSmokeTest.unity

Scene Load
  ↓ Player Spawn 확인
  ↓ Enemy Spawn 확인
  ↓ 공격 실행
  ↓ Enemy HP 감소 확인
  ↓ Console Error 0
```

**게임 전체가 "그냥 뜨는지" 만 확인해도 가치가 크다.**

---

## 3. 위험도별 필요 검증 (C3 와 연동)

| 위험도 | Compile | Unit/EditMode | PlayMode | Smoke | Asset Diff | Ref Check | Build |
|---|---|---|---|---|---|---|---|
| 저 (순수 로직) | ✓ | ✓ | | | | | |
| 중 (MonoBehaviour) | ✓ | ✓ | ✓ | | | | |
| 고 (SerializeField/Prefab/Scene/SO/asmdef) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| 매우 높음 (Input/Addressables/Build) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 4. Acceptance Criteria 매핑 (필수)

**AC 1개당 최소 1개 테스트.** C4 에서 표로 매핑하고 C5 에서 전부 통과시킨다.

```
AC1 쿨다운 0.4초           → CombatModelTests.Cooldown_BlocksWithin04s    EditMode
AC2 범위 내 Enemy 만        → CombatModelTests.OnlyEnemiesInCone          EditMode
AC3 죽은 Enemy 제외         → CombatModelTests.DeadEnemyExcluded          EditMode
AC4 연타 무시               → CombatSmokeTests.RapidInput_SingleHit       PlayMode
```

매핑되지 않은 AC 가 있으면 C4 EXIT GATE 실패다.

---

## 5. CLI 실행

```
-runTests -testPlatform EditMode -testResults <path>
-runTests -testPlatform PlayMode -testResults <path>
-batchmode -quit -projectPath <path> -buildTarget <target> -logFile -
```

정확한 문법은 실행 시점에 `unity --help` / 공식 문서로 확인한다.
`unity command --project-path ... --format json` 으로 catalog 에 test/compile command 가 있는지도 확인.

결과 XML 을 파싱해 통과/실패 수를 보고한다. **"돌렸습니다" 는 증거가 아니다.**

---

## 6. 테스트를 약화시키지 않는다 (중대)

에이전트가 "테스트를 통과시켜" 를 받으면 **코드 대신 테스트를 고치는** 경로로 갈 수 있다.

```
Production code 수정  →  기존 test 통과      ← 기본
Specification 변경    →  test 수정           ← Task Contract 가 바뀐 경우만
```

금지 패턴:
```
✗ assert 를 느슨하게 변경
✗ 기대값을 실제 출력에 맞춰 수정        ← 가장 흔한 부정행위
✗ [Ignore] / Skip 부착
✗ 테스트 케이스 삭제
✗ try-catch 로 실패를 삼킴
✗ 타임아웃을 늘려서 통과시키기 (원인 미해결)
```

테스트를 수정했다면 **C6 Diff Gate 에서 자진 신고**한다. 숨기면 안 된다.

---

## 7. 테스트가 없는 프로젝트에서 시작할 때

기존 테스트가 하나도 없으면 회귀를 잡을 수 없다. C2/C3 에서 STOP (DECISION) 대상이다.

권장 최소 세트:
```
1. Smoke Test 1개          — 게임이 뜨고 콘솔 에러 0
2. 이번 태스크의 AC 테스트  — Domain 층 우선
3. 이후 태스크마다 AC 테스트를 누적
```

전체 커버리지를 먼저 만들려 하지 않는다. **태스크마다 조금씩 쌓는다.**
