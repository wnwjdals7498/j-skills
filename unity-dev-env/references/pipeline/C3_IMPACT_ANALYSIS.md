# C3 — IMPACT ANALYSIS (변경 영향/위험도 판정)

> LOAD WHEN: C2 = PASS. **여기서 검증 레벨이 결정된다.**

Unity 에서 코드 변경의 위험도는 전부 같지 않다.
C# 관점에서 완벽한 리팩터링이 Unity 에서는 **데이터 마이그레이션 사고**가 될 수 있다.

---

## ENTRY GATE
- C2 = `PASS`

## INPUTS
- Task Contract + Context 문서

---

## STEPS

### 3-A. 변경 항목별 위험도 분류

| 변경 종류 | 위험도 |
|---|---|
| 순수 C# 계산 로직 | 낮음 |
| 일반 클래스 추가 | 낮음 |
| MonoBehaviour 로직 | 중간 |
| Inspector 공개 필드 변경 | 중간~높음 |
| **SerializeField 변경** | **높음** |
| **ScriptableObject 구조 변경** | **높음** |
| **Prefab 변경** | **높음** |
| **Scene 변경** | **높음** |
| **asmdef 변경** | **높음** |
| **Input / Addressables / Build Settings** | **매우 높음** |

태스크의 최고 위험도가 **전체 태스크의 위험도**다.

### 3-B. SerializeField 변경 특별 취급

```csharp
[SerializeField] private float speed;
        ↓  단순 리네임처럼 보이지만
[SerializeField] private float movementSpeed;
```

C# 관점에서는 완벽하지만, **Inspector 에 저장된 기존 직렬화 값이 유실될 수 있다.**

필수 처리:
```csharp
[FormerlySerializedAs("speed")]
[SerializeField] private float movementSpeed;
```
`using UnityEngine.Serialization;` 필요.

체크리스트:
```
[ ] 필드 이름 변경 → FormerlySerializedAs 부착
[ ] 타입 변경 → 마이그레이션 코드 또는 새 필드 + 이관 로직
[ ] 필드 삭제 → 해당 값을 쓰던 Prefab/Scene 영향 조사
[ ] private → public / [SerializeField] 추가·제거 → 직렬화 대상 변화 확인
[ ] 변경 후 관련 Prefab/Scene 의 Inspector 값을 실제로 확인
```

### 3-C. .meta / GUID 위험

Unity 의 오브젝트 참조는 `.meta` 의 GUID 로 연결된다.
파일을 Move / Rename / Delete / Recreate 할 때 `.meta` 를 잘못 다루면 **참조가 끊긴다.**

```
✗ .meta 파일을 임의 삭제
✗ OS 레벨 delete + recreate 로 에셋 이동
✗ 파일만 옮기고 .meta 를 두고 감
✓ Unity Editor 내에서 이동/이름변경 (또는 파일+.meta 를 함께 이동)
```

### 3-D. Scene / Prefab 정책

```
Scene / Prefab 수정은 명시적으로 요청받은 경우에만 수행한다.
수정했다면 반드시 diff 를 별도로 검토한다.
```

Force Text 직렬화가 켜져 있어야 diff 검토가 가능하다. 아니면 먼저 확인/보고.

### 3-E. 검증 레벨 결정 (이 스테이지의 산출물)

위험도에 따라 C5 에서 수행할 검증을 확정한다.

| 위험도 | 필요 검증 |
|---|---|
| **저위험**<br>순수 계산 로직 | Compile + Unit/EditMode Test |
| **중위험**<br>MonoBehaviour 수정 | Compile + Test + **PlayMode** |
| **고위험**<br>SerializeField / Prefab / Scene / SO / asmdef | Compile + Test + PlayMode + **Asset/Prefab Diff** + **Reference 무결성 확인** |
| **매우 높음**<br>Input / Addressables / Build Settings | 위 전부 + **빌드 검증** + 사용자 확인 |

### 3-F. 영향 받는 테스트 식별

```
[ ] 이 변경으로 깨질 가능성이 있는 기존 테스트
[ ] 새로 필요한 테스트 (Acceptance Criteria 1개당 최소 1개)
[ ] 회귀 방지용 Smoke Test 필요 여부
```

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 고위험 변경이 필요 (SerializeField/Prefab/Scene/SO/asmdef) | RISK | **승인 요청.** 영향 범위와 롤백 방법 명시 |
| 매우 높음 (Input/Addressables/Build Settings) | RISK | **승인 필수** + 백업 확인 |
| Force Text 직렬화가 꺼져 있음 | DECISION | 켤지 질문 (기존 diff 이력 영향) |
| 기존 테스트가 없어 회귀를 잡을 수 없음 | DECISION | 테스트 선작성 여부 질문 |
| 영향 범위가 Task Contract 의 `out_of_bounds` 를 넘음 | RISK | 계약 수정 승인 요청 |

### 고위험 승인 요청 템플릿

```markdown
## ⏸ 고위험 변경 승인 요청

**변경:** `PlayerController.speed` → `movementSpeed` (SerializeField)
**위험도:** 높음
**영향:** Player.prefab, MainScene.unity 의 Inspector 저장값
**완화책:** `[FormerlySerializedAs("speed")]` 부착 → 기존 값 보존
**롤백:** git revert 로 원복 가능. Prefab 미수정.

| # | 선택지 | 결과 |
|---|---|---|
| 1 | FormerlySerializedAs 부착 후 리네임 (추천) | 값 보존, 코드 가독성 개선 |
| 2 | 리네임하지 않음 | 위험 0, 이름 유지 |
| 3 | 리네임 + Prefab 값 수동 재설정 | 수작업 필요 |
```

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 모든 변경 항목에 위험도가 부여됨 |
| 2 | 태스크 전체 위험도 확정 |
| 3 | **검증 레벨 확정** (C5 가 무엇을 돌릴지) |
| 4 | SerializeField 변경이 있으면 마이그레이션 방안 명시 |
| 5 | 고위험 이상이면 **사용자 승인 기록 존재** |
| 6 | 영향 받는 기존 테스트 목록 확보 |

## OUTPUTS
- `Docs/Code/Tasks/TASK-{nnnn}.impact.md`

## STATE UPDATE
```yaml
stage: C3
status: PASS | BLOCKED
risk_level: low | medium | high | critical
verification_level: [compile, editmode, playmode, asset_diff, reference_check]
approvals: [{item: serializefield_rename, approved_at: <iso8601>}]
```
