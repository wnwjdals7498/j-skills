# C4 — IMPLEMENTATION PLAN (구현 계획)

> LOAD WHEN: C3 = PASS. **아직 코드를 쓰지 않는다.** 마지막 비구현 단계.

가장 위험한 형태는 `47 files changed / +3,842 / -1,931` 이후 "구현 완료했습니다" 다.
그것을 막기 위해 **미리 최소 단위로 쪼갠다.**

---

## ENTRY GATE
- C3 = `PASS` (검증 레벨 확정, 고위험이면 승인 완료)

## INPUTS
- Task Contract / Context / Impact 문서

---

## STEPS

### 4-A. 원자적 단위로 분할

각 단위는 **독립적으로 컴파일되고 커밋 가능**해야 한다.

```
STEP 1  feat: add combat cooldown model
        - CombatModel.cs (신규, 순수 C#)
        - CombatModelTests.cs (신규, EditMode)
        위험도: 낮음   검증: Compile + EditMode

STEP 2  feat: integrate combat with player controller
        - PlayerCombat.cs (신규, MonoBehaviour)
        - PlayerController.cs (수정: 입력 라우팅 1줄)
        위험도: 중간   검증: Compile + EditMode + PlayMode

STEP 3  test: add combat playmode smoke test
        - Assets/Tests/Scenes/CombatSmokeTest.unity (신규)
        - CombatSmokeTests.cs (신규, PlayMode)
        위험도: 낮음   검증: Compile + PlayMode
```

분할 기준:
```
[ ] 각 STEP 이 단독으로 컴파일되는가
[ ] 각 STEP 이 단독으로 되돌릴 수 있는가 (revert)
[ ] 각 STEP 의 diff 가 사람이 검토 가능한 크기인가 (대략 300줄 이내 권장)
[ ] 고위험 변경이 별도 STEP 으로 격리되었는가   ★
```

**고위험 변경(SerializeField/Prefab/Scene/asmdef)은 반드시 단독 STEP 으로 격리한다.**
저위험 변경과 섞이면 문제 발생 시 원인 분리가 불가능하다.

### 4-B. STEP 별 검증 계획 명시

C3 에서 정한 검증 레벨을 STEP 단위로 배분한다.

| STEP | Compile | EditMode | PlayMode | Smoke | Asset Diff | Ref Check |
|---|---|---|---|---|---|---|
| 1 | ✓ | ✓ | | | | |
| 2 | ✓ | ✓ | ✓ | | | |
| 3 | ✓ | | ✓ | ✓ | | |

### 4-C. 테스트 계획

**Acceptance Criteria 1개당 최소 1개 테스트.** 매핑을 명시한다.

```
AC1 쿨다운 0.4초                → CombatModelTests.Cooldown_BlocksWithin04s   (EditMode)
AC2 범위 내 Enemy 만 데미지      → CombatModelTests.OnlyEnemiesInCone         (EditMode)
AC3 죽은 Enemy 제외             → CombatModelTests.DeadEnemyExcluded         (EditMode)
AC4 연타 무시                    → CombatSmokeTests.RapidInput_SingleHit      (PlayMode)
```

테스트 종류 선택은 `references/guides/TEST_STRATEGY.md`.

### 4-D. 롤백 계획

```
각 STEP 은 git revert 로 단독 원복 가능한가?
Prefab/Scene 변경이 있으면 원복 절차는?
직렬화 데이터 변경이 있으면 원복 시 값이 복구되는가?
```

### 4-E. 계획 저장 및 진행

계획을 파일로 남긴다. **승인을 기다리지 않는다** — 게이트를 통과했으면 실행한다.
`ESCALATION.md` §5 참조: "계획이 괜찮은가요?" 는 묻지 않는다.

```
Docs/Code/Tasks/TASK-{nnnn}.plan.md
```

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 원자적 분할이 불가능 (강결합) | CONFLICT | 선행 리팩터링 vs 단일 대형 커밋 선택지 |
| STEP 수가 과도 (10개 초과) | DECISION | 태스크 분리 제안 |
| Acceptance Criteria 를 검증할 테스트를 설계할 수 없음 | CONFLICT | AC 재정의 요청 (C1 롤백) |
| 롤백 불가능한 STEP 존재 | RISK | 백업/브랜치 확인 후 승인 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 모든 변경이 STEP 으로 분할됨 |
| 2 | 각 STEP 이 단독 컴파일·단독 revert 가능 |
| 3 | 고위험 변경이 단독 STEP 으로 격리됨 |
| 4 | STEP 별 검증 계획이 표로 존재 |
| 5 | **모든 Acceptance Criteria 에 대응 테스트가 매핑**됨 |
| 6 | 롤백 절차가 명시됨 |

## OUTPUTS
- `Docs/Code/Tasks/TASK-{nnnn}.plan.md`

## STATE UPDATE
```yaml
stage: C4
status: PASS | BLOCKED
steps: 3
ac_test_mapping: complete
```
