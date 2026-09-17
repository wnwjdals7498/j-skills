# V6 — GAMEPLAY MIGRATION (기존 기능 이식)

> LOAD WHEN: mode = `rebase` 이고 V5 = PASS. GREENFIELD 모드면 **이 스테이지를 건너뛴다.**

Golden Scene 이 합격한 **뒤에야** 기존 게임플레이를 끌어온다. 순서를 뒤집으면 새 디자인이 오염된다.

---

## ENTRY GATE
- mode = `rebase`
- V5 = `PASS` 또는 `PARTIAL`
- 기존 씬/프리팹이 존재

## INPUTS
- 기존 씬, 프리팹, 스크립트
- `ASSET_REPLACEMENT_MATRIX.md`

---

## STEPS

### 6-A. Gameplay / Presentation 분리 (선행 리팩터링)

현재 이렇게 얽혀 있으면 비주얼 변경이 위험하다:
```
Enemy
 ├ EnemyController
 ├ Animator
 ├ Mesh
 ├ Material
 ├ Collider
 └ Weapon
```

이렇게 바꾼다:
```
Enemy
 ├ Gameplay
 │   ├ EnemyController
 │   ├ Health
 │   └ Collider
 │
 └ PresentationRoot
     ├ Model
     ├ Animator
     ├ WeaponVisual
     └ VFX
```

**그러면 Visual Rebase 시 `PresentationRoot` 만 교체하면 된다. 게임 로직은 유지된다.**

리팩터링 범위는 사용자 승인 대상 (`ESCALATION` DECISION) — 게임플레이 회귀 위험이 있다.

### 6-B. 이식 순서

```
1. 새 씬(VisualRebuild.unity)을 기준으로 삼는다
2. 기존 씬에서 Gameplay 루트만 가져온다
3. 각 Gameplay 루트에 새 PresentationRoot 를 붙인다
4. 참조(레퍼런스) 끊김 확인 및 수정
5. 기능 회귀 테스트
6. VISUAL_DOD 실행
```

**기존 씬을 새 비주얼로 덮어쓰는 방향이 아니라, 새 씬으로 게임플레이를 옮겨오는 방향이다.**

### 6-C. 참조 무결성 검사

이식 후 반드시 확인:
```
[ ] Missing Prefab / Missing Script 없음
[ ] SerializedField 참조 끊김 없음
[ ] Animator Controller 연결 유지
[ ] Collider / Rigidbody 유지
[ ] Tag / Layer 유지
[ ] NavMesh / 물리 설정 유지
[ ] 이벤트 바인딩 (UnityEvent) 유지
```

### 6-D. 기능 회귀 테스트

가능하면 자동화:
```
Play Mode 진입 → 콘솔 에러 0 → 핵심 상호작용 N개 수행 → 정상 동작
```
자동화가 불가능하면 사용자에게 확인 요청 (MANUAL).

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| **리팩터링 범위** | DECISION | 게임플레이 회귀 위험. 승인 필요 |
| 기존 씬을 수정해야 함 | RISK | 백업 확인 후 승인 요청 |
| 참조 끊김이 대량 발생 | CONFLICT | 원인 + 복구 선택지 제시 |
| 수동 플레이 테스트 필요 | MANUAL | 테스트 항목 목록 제공 후 대기 |
| 게임플레이 코드가 비주얼에 강결합되어 분리 불가 | CONFLICT | 리팩터링 vs 우회 선택지 제시 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 모든 Enemy/NPC/Interactable 이 Gameplay + PresentationRoot 구조 |
| 2 | Missing Prefab / Missing Script 0 |
| 3 | Play Mode 콘솔 에러 0 |
| 4 | 기능 회귀 없음 (자동 테스트 또는 사용자 확인) |
| 5 | VisualLinter error 0 |
| 6 | 스코어카드 9항목 ≥4 유지 |

## OUTPUTS
- 이식 완료된 `VisualRebuild.unity`
- 회귀 테스트 결과

## STATE UPDATE
```yaml
stage: V6
status: PASS | PARTIAL | BLOCKED
migrated_objects: n
regression_test: passed | manual_pending
```
