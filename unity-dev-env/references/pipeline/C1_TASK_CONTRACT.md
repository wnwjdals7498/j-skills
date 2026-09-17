# C1 — TASK CONTRACT (요구사항 구체화)

> LOAD WHEN: 코드 작업 지시를 받았을 때. **모든 코드 트랙의 첫 스테이지. 건너뛰지 않는다.**
>
> 여기서 코드를 쓰지 않는다. **무엇을 만들고 무엇을 건드리지 않을지**를 계약으로 고정한다.

---

## 왜 이 스테이지가 있는가

`"근접 공격 만들어줘"` 를 그대로 받으면 에이전트가 결정해야 하는 공간이 너무 넓다.
쿨다운, 판정 방식, 데미지 계산 위치, 애니메이션 연동, 기존 코드 수정 범위 — 전부 추측이 된다.

**Task Contract 는 그 추측 공간을 좁히는 스펙 레이어다.**
비주얼 트랙의 `VISUAL_SPEC.yaml` 에 대응한다.

---

## ENTRY GATE
- S0 = `PASS` 또는 `PARTIAL` (Unity CLI 로 컴파일/테스트를 돌릴 수 있어야 함)

## INPUTS
- 사용자의 원문 지시
- 기존 프로젝트 코드 (있으면)

---

## STEPS

### 1-A. 원문 지시를 5개 슬롯으로 분해

```yaml
task_id: TASK-0007
title: 플레이어 근접 공격

goal: |
  플레이어가 공격 버튼을 누르면 근접 공격을 수행한다.

acceptance_criteria:          # 검증 가능한 문장만. 형용사 금지.
  - 공격 쿨다운 0.4초
  - 공격 범위(반경 1.8m, 전방 120도) 내 Enemy 만 데미지를 받는다
  - 죽은 Enemy(Health<=0)는 공격 대상에서 제외된다
  - 동일 입력 연타 시 쿨다운 중에는 무시된다

non_goals:                    # 이번에 하지 않는 것
  - 원거리 공격
  - 콤보 시스템
  - 공격 VFX

invariants:                   # 반드시 유지되어야 하는 기존 동작
  - 기존 이동 코드는 변경하지 않는다
  - 데미지 계산은 PlayerController 내부에 넣지 않는다
  - 기존 EditMode 테스트 18개는 전부 통과 상태를 유지한다

out_of_bounds:                # 건드리면 안 되는 파일/영역
  - Assets/Scenes/**            # 명시 요청 없이 Scene 수정 금지
  - Assets/**/*.prefab
  - Assets/**/*.asmdef
```

### 1-B. Acceptance Criteria 작성 규칙

**검증 가능해야 한다.** 아래 변환을 적용한다.

| 모호한 요구 | 검증 가능한 형태 |
|---|---|
| "공격이 자연스럽게" | 쿨다운 0.4초, 입력 후 0.1초 내 판정 시작 |
| "적절한 데미지" | base_damage 10, 방어력 감산식 `max(1, dmg - def)` |
| "가까운 적만" | 반경 1.8m, 전방 120도 콘 |
| "부드러운 이동" | 가속 12 m/s², 최대 속도 5 m/s |
| "빠르게" | 프레임당 할당 0, 60fps 유지 |

**숫자·조건·불변식이 아닌 항목은 Acceptance Criteria 가 아니다.** `notes:` 로 밀어낸다.

### 1-C. 모르는 값 처리 (요구사항 구체화의 핵심)

값이 없을 때 **묻기 전에** 아래 순서로 스스로 찾는다.

```
① 기존 코드에 유사 값이 있는가?        (다른 스킬의 쿨다운, 기존 상수)
② 프로젝트 설정/ScriptableObject 에 있는가?
③ 기존 테스트가 값을 암시하는가?
④ 장르 표준값이 명확한가?              → ASSUME 으로 진행, 계약에 assumed: true 표기
─────────────────────────────────
⑤ 그래도 모르면                        → STOP (DECISION), 선택지 2~4개 제시
```

`ASSUME` 한 값은 계약에 반드시 표기한다:
```yaml
acceptance_criteria:
  - value: 공격 쿨다운 0.4초
    assumed: true
    basis: "기존 DashAbility.cooldown=0.5 와 동급 스케일"
```
사용자가 나중에 뒤집어도 어디를 고칠지 즉시 알 수 있다.

### 1-D. 질문은 한 번에 묶어서

여러 값이 불명확하면 **하나씩 순차로 묻지 않는다.** 한 번에 모아서 묻는다.
형식은 `references/policy/ESCALATION.md` §3.

```markdown
### 결정 항목: 근접 공격 파라미터 3개

| # | 항목 | 선택지 | 추천 |
|---|---|---|---|
| 1 | 판정 방식 | (a) OverlapSphere+각도 (b) 히트박스 콜라이더 (c) 레이캐스트 | (a) — 기존 EnemyDetector 와 동일 패턴 |
| 2 | 데미지 계산 위치 | (a) 신규 CombatModel (순수 C#) (b) 기존 DamageSystem 확장 | (a) — invariant "PlayerController 에 넣지 않음" 충족 + 테스트 용이 |
| 3 | 애니메이션 연동 | (a) 이번 범위 제외 (b) Animator Trigger 만 (c) 애니메이션 이벤트 기반 판정 | (a) — non_goal 로 두고 별도 태스크 |

**전부 추천대로 진행할까?**
```

### 1-E. 위험도 사전 태깅

계약 시점에 이미 알 수 있는 위험 신호를 표기한다. C3 에서 정밀 분석한다.

```yaml
risk_signals:
  - serialize_field_change: false
  - prefab_touch: false
  - scene_touch: false
  - asmdef_touch: false
  - public_api_break: false
```

### 1-F. 계약 저장

```
<PROJECT_ROOT>/Docs/Code/Tasks/TASK-0007.yaml
```

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| Acceptance Criteria 를 검증 가능한 형태로 못 만듦 | DECISION | 선택지 제시 |
| 요구가 기존 아키텍처와 충돌 | CONFLICT | 아키텍처 변경 vs 우회 선택지 |
| 요구 범위가 너무 커서 원자적 커밋이 불가 | DECISION | 태스크 분할안 제시 |
| `out_of_bounds` 영역을 반드시 건드려야 함 | RISK | 승인 요청 |
| 요구가 서로 모순 | CONFLICT | 모순 지점 명시 후 질문 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | `goal` 이 한 문장으로 존재 |
| 2 | `acceptance_criteria` 가 전부 **검증 가능한 문장** (숫자/조건/불변식) |
| 3 | `non_goals` 가 비어 있지 않음 |
| 4 | `invariants` 가 비어 있지 않음 |
| 5 | `out_of_bounds` 명시 |
| 6 | `ASSUME` 항목이 전부 `assumed: true` + `basis` 로 표기됨 |
| 7 | 남은 `DECISION` 항목이 없음 (있으면 BLOCKED) |

## OUTPUTS
- `Docs/Code/Tasks/TASK-{nnnn}.yaml`

## STATE UPDATE
```yaml
track: code
stage: C1
status: PASS | BLOCKED
task_id: TASK-0007
assumptions: [...]
```
