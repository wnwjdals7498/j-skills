# C5 — IMPLEMENT & VERIFY (구현과 검증)

> LOAD WHEN: C4 = PASS. **여기서 처음으로 코드를 쓴다.**

핵심 원칙 한 문장:
> **에이전트에게 코드를 작성할 권한만 주지 말고, 변경이 올바르다는 증거를 제출하게 만든다.**

---

## ENTRY GATE
- C4 = `PASS` (STEP 분할 + 검증 계획 + AC-테스트 매핑 완료)

## INPUTS
- `TASK-{nnnn}.yaml` / `.context.md` / `.impact.md` / `.plan.md`

---

## STEPS

STEP 1개당 아래 사이클을 **끝까지** 돈다. 다음 STEP 으로 넘어가기 전에 완결한다.

```
① 최소 단위 코드 수정
        ↓
② Compile           ← 실패하면 여기서 멈추고 고친다
        ↓
③ EditMode Test
        ↓
④ PlayMode Test      (C3 검증 레벨이 요구하면)
        ↓
⑤ Smoke Test         (C3 검증 레벨이 요구하면)
        ↓
⑥ Console Error 0 확인
        ↓
⑦ Asset/Prefab Diff  (고위험이면)
        ↓
⑧ Reference 무결성   (고위험이면)
        ↓
⑨ 증거 수집 → C6 Diff Gate
```

---

### 5-A. 컴파일 검증 (자동화 필수)

**"수정하고 끝" 을 허용하지 않는다.** 최소한 아래까지가 하나의 작업이다.

```
코드 수정 → Unity compile → compiler error 0
```

Unity CLI / batchmode 로 자동화한다:
```bash
unity command --project-path "<PROJECT_ROOT>" --format json      # catalog 에서 compile command 확인
```
또는 batchmode:
```
-batchmode -quit -projectPath "<PROJECT_ROOT>" -executeMethod <CompileCheck> -logFile -
```

**정확한 command 이름/문법은 추측하지 않는다.** catalog 조회 또는 `--help` 로 확인 (`references/guides/UNITY_CLI.md`).

컴파일 실패 시:
- 에러 원문을 그대로 기록
- 다음 검증 단계로 넘어가지 않는다
- 3회 시도해도 못 고치면 STOP (CONFLICT)

### 5-B. 테스트 실행 (3단)

`references/guides/TEST_STRATEGY.md` 상세. 요약:

| 종류 | 무엇을 검증 | 속도 | Unity 필요 |
|---|---|---|---|
| **Pure C# Unit** | 데미지 계산, 상태 전환, 인벤토리, 쿨다운, AI 판단, 세이브 변환 | 빠름 | ✗ |
| **EditMode** | 에디터 컨텍스트의 로직 | 빠름 | 에디터만 |
| **PlayMode** | GameObject 생성 → Component 연결 → 몇 프레임 실행 → 결과 검증 | 느림 | ✓ |
| **Smoke** | Scene Load → Spawn 확인 → 상호작용 → 상태 변화 → Console Error 0 | 느림 | ✓ |

CLI 실행:
```
-runTests -testPlatform EditMode -testResults <path>
-runTests -testPlatform PlayMode -testResults <path>
```
문법은 실행 시점 `--help`/공식 문서로 확인.

### 5-C. Smoke Test 가 왜 별도로 필요한가

게임은 상태 기반 시스템이라 **순서에서 오는 버그**가 많다.
```
Player Spawn → Awake → OnEnable → Start → Input 활성화
→ Animator 초기화 → Enemy Spawn → Physics Update
```
Unit/Integration 테스트로는 이 순서 문제를 잡지 못한다.

전용 테스트 씬을 둔다:
```
Assets/Tests/Scenes/CombatSmokeTest.unity

Scene Load
  ↓ Player Spawn 확인
  ↓ Enemy Spawn 확인
  ↓ 공격 실행
  ↓ Enemy HP 감소 확인
  ↓ Console Error 0
```

### 5-D. 테스트를 약화시켜 통과시키지 않는다 (중대)

에이전트에게 "테스트를 통과시켜" 라고 하면, **코드 대신 테스트를 고쳐서** 통과시키는 경로로 갈 수 있다.

구분 규칙:
```
Production code 수정  →  기존 test 통과        ← 기본. 테스트를 건드리지 않는다
Specification 변경    →  test 수정             ← Task Contract 가 바뀐 경우만
```

테스트를 수정했다면 **C6 Diff Gate 에서 반드시 사유를 신고한다.**
```
[ ] assert 를 느슨하게 바꾸지 않았는가
[ ] 테스트를 Skip/Ignore 하지 않았는가
[ ] 기대값을 실제 출력에 맞춰 바꾸지 않았는가   ★ 가장 흔한 부정행위
[ ] 테스트 케이스를 삭제하지 않았는가
```

### 5-E. Console Error 0

컴파일 에러가 없어도 런타임 콘솔 에러/예외가 남을 수 있다.
PlayMode/Smoke 실행 후 콘솔을 확인한다. `NullReferenceException`, `MissingReferenceException` 등이 0 이어야 한다.

### 5-F. 고위험 추가 검증

C3 가 고위험으로 판정했으면:

```
[ ] Asset/Prefab Diff 검토      (Force Text 직렬화 전제)
[ ] Missing Prefab / Missing Script 0
[ ] SerializedField 참조 끊김 0
[ ] Inspector 저장값이 보존되었는가 (FormerlySerializedAs 동작 확인)
[ ] Animator Controller / Collider / Tag / Layer 유지
[ ] UnityEvent 바인딩 유지
[ ] asmdef 참조 방향이 의도대로인가
```

### 5-G. 자기 수정 루프

```
Agent
 ↓ Code Change
Unity CLI
 ├ Compile
 ├ EditMode Tests
 ├ PlayMode Tests
 └ Build (필요시)
 ↓ Result
Agent Fix
 ↺
```

실패 → 원인 분석 → 수정 → 재실행. **실패를 숨기지 않는다.**
동일 실패가 3회 반복되면 STOP (CONFLICT).

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 컴파일 에러 3회 시도 후에도 미해결 | CONFLICT | 에러 원문 + 원인 가설 + 선택지 제시 |
| 동일 테스트 실패 3회 반복 | CONFLICT | AC 자체가 틀렸을 가능성 제시 |
| Unity Editor 실행 불가 (PlayMode 필요) | MANUAL | Editor 실행 요청 |
| 테스트를 고쳐야만 통과 가능해 보임 | DECISION | **절대 임의로 고치지 않는다.** 스펙 변경인지 질문 |
| Prefab/Scene 수정이 불가피 | RISK | 승인 요청 |
| 참조 끊김 발생 | CONFLICT | 복구 선택지 제시 |
| 수동 플레이 확인이 필요 (애니메이션 타이밍 등) | MANUAL | 확인 항목 목록 제공 |

---

## EXIT GATE

| # | 조건 | 증거 |
|---|---|---|
| 1 | Compiler Error **0** | 컴파일 로그 |
| 2 | 모든 Acceptance Criteria 충족 | AC-테스트 매핑 전부 PASS |
| 3 | 기존 테스트 전부 PASS (회귀 없음) | 테스트 결과 |
| 4 | Console Error **0** | 콘솔 로그 |
| 5 | C3 검증 레벨의 항목 전부 수행 | 각 항목 결과 |
| 6 | 테스트를 약화시키지 않았음 | §5-D 체크리스트 |
| 7 | Smoke Test PASS (요구된 경우) | 테스트 결과 |

**"돌렸다고 말하기" 는 증거가 아니다.** 테스트 결과 파일/로그가 실제로 있어야 한다.

## OUTPUTS
- 구현된 코드
- `Docs/Code/Tasks/TASK-{nnnn}.verify.md` (검증 결과)
- 테스트 결과 XML/로그

## STATE UPDATE
```yaml
stage: C5
status: PASS | PARTIAL | BLOCKED | FAILED
compile: PASS
editmode: 18/18
playmode: 4/4
smoke: PASS
console_errors: 0
tests_modified: false
```
