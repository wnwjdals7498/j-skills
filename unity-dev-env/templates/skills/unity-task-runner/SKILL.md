---
name: unity-task-runner
description: Unity 프로젝트의 모든 코드 작업을 지휘하는 상위 오케스트레이션 스킬. 기능 추가, 버그 수정, 리팩터링 요청을 검증 가능한 Task Contract 로 구체화하고, 기존 코드 탐색 → 변경 위험도 판정 → 원자적 STEP 분할 → 구현 → 컴파일/EditMode/PlayMode/Smoke 검증 → diff 자기검토 → 원자적 커밋까지 강제한다. "기능 만들어줘", "버그 고쳐줘", "리팩터링", "이거 구현해" 같은 요청에서 트리거된다.
---

# unity-task-runner

> 한 문장 요약:
> **에이전트에게 코드를 작성할 권한만 주지 말고, 변경이 올바르다는 증거를 제출하게 만든다.**

Unity 에서 **컴파일 성공은 정상 동작이 아니다.** 그래서 이 스킬은 폐루프를 강제한다.

```
요구사항 → 코드 탐색 → 영향 범위 → 계획 → 최소 수정
→ 컴파일 → 테스트 → PlayMode → Smoke → Diff 검토 → 커밋 → Push
```

---

## 1. 시작 시 반드시 하는 것

```
1. <PROJECT_ROOT>/Docs/PIPELINE_STATE.md 를 읽는다
2. {KIT_ROOT}/references/pipeline/PIPELINE.md 로 C 트랙 현재 스테이지 확인
3. 진행 중 태스크가 있으면 그 스테이지부터, 없으면 C1 부터
```

**C1 을 건너뛰지 않는다.** 지시가 아무리 명확해 보여도 계약을 먼저 만든다.

---

## 2. 스테이지

| 스테이지 | 하는 일 | 코드를 쓰는가 |
|---|---|---|
| **C1** Task Contract | goal / AC / non_goals / invariants / out_of_bounds | ✗ |
| **C2** Context Discovery | 관련 코드, **기존 패턴 확인**, 레이어 배치, asmdef | ✗ |
| **C3** Impact Analysis | 위험도 분류 → **검증 레벨 결정** | ✗ |
| **C4** Implementation Plan | 원자적 STEP 분할, 고위험 격리, AC-테스트 매핑 | ✗ |
| **C5** Implement & Verify | **여기서 처음 코드를 쓴다.** compile→test→playmode→smoke | ✓ |
| **C6** Diff Gate | 자기 심문 → 원자적 커밋 → push → 보고 | ✗ |

각 스테이지 상세: `{KIT_ROOT}/references/pipeline/C{n}_*.md`

---

## 3. C1 — 요구사항 구체화가 핵심

```yaml
goal: 한 문장
acceptance_criteria:   # 검증 가능한 문장만. 형용사 금지.
non_goals:             # 이번에 안 하는 것
invariants:            # 반드시 유지되어야 하는 기존 동작
out_of_bounds:         # 건드리면 안 되는 파일/영역
```

모호한 요구를 검증 가능하게 바꾼다:
```
"공격이 자연스럽게"  → 쿨다운 0.4초, 입력 후 0.1초 내 판정 시작
"적절한 데미지"      → base 10, 감산식 max(1, dmg - def)
"가까운 적만"        → 반경 1.8m, 전방 120도 콘
```

모르는 값은 **묻기 전에** 스스로 찾는다:
```
① 기존 코드에 유사 값이 있는가
② 프로젝트 설정/SO 에 있는가
③ 기존 테스트가 값을 암시하는가
④ 장르 표준값이 명확한가  → ASSUME 으로 진행, assumed: true 표기
─────────
⑤ 그래도 모르면 → STOP. 선택지 2~4개 + 추천을 한 번에 묶어 질문
```

---

## 4. C2 — 가장 흔한 실수를 막는다

이 단계를 생략하면 에이전트는 **기존 시스템이 있는데 비슷한 것을 하나 더 만든다.**

```
현재 이 책임은 어디에 있는가?
새 기능은 어느 모듈에 들어가야 하는가?
이미 같은 일을 하는 기존 패턴이 있는가?   ★ 반드시 확인
새 클래스가 정말 필요한가, 기존 확장인가?
```

3층 구조에 매핑한다 (`{KIT_ROOT}/references/guides/CODE_ARCHITECTURE.md`):
```
Domain    순수 C#           ← 여기를 크게 만든다. Unity 없이 테스트 가능
Adapter   MonoBehaviour
Wiring    Scene / Prefab    ← 고위험
```

---

## 5. C3 — 위험도가 검증 레벨을 결정한다

| 위험도 | 예 | 검증 |
|---|---|---|
| 저 | 순수 C# 계산 로직 | Compile + EditMode |
| 중 | MonoBehaviour 로직 | + PlayMode |
| 고 | SerializeField / Prefab / Scene / SO / asmdef | + Asset Diff + Reference 확인 + **사용자 승인** |
| 매우 높음 | Input / Addressables / Build Settings | + 빌드 검증 + **사용자 확인** |

### SerializeField 특별 취급
```csharp
// 이름만 바꿔도 Inspector 저장값이 날아간다
[FormerlySerializedAs("speed")]
[SerializeField] private float movementSpeed;
```

상세: `{KIT_ROOT}/references/guides/UNITY_RISK_ZONES.md`

---

## 6. C5 — 검증 (테스트를 약화시키지 않는다)

```
① 최소 단위 수정
② Compile              error 0 아니면 여기서 멈춘다
③ EditMode Test
④ PlayMode Test        (검증 레벨이 요구하면)
⑤ Smoke Test           (검증 레벨이 요구하면)
⑥ Console Error 0
⑦ Asset/Prefab Diff    (고위험)
⑧ Reference 무결성     (고위험)
```

### 절대 금지
```
✗ assert 를 느슨하게 변경
✗ 기대값을 실제 출력에 맞춰 수정      ← 가장 흔한 부정행위
✗ [Ignore] / Skip 부착
✗ 테스트 케이스 삭제
✗ 타임아웃 늘려서 통과 (원인 미해결)
```

```
Production code 수정 → 기존 test 통과      ← 기본
Specification 변경   → test 수정           ← Task Contract 가 바뀐 경우만
```

테스트를 수정했으면 **C6 에서 자진 신고**한다.

---

## 7. C6 — Diff Gate

```
[ ] 왜 이 파일을 수정했는가? (파일별 한 줄)
[ ] 요구와 무관한 변경은 없는가?
[ ] non_goals 를 구현하지 않았는가?
[ ] out_of_bounds 를 건드리지 않았는가?
[ ] invariants 가 유지되는가?
[ ] 새 global state / Singleton 추가?
[ ] SerializeField 변경?         → FormerlySerializedAs
[ ] Scene/Prefab 변경?           → 별도 커밋
[ ] .meta 삭제/재생성?
[ ] asmdef dependency 변경?
[ ] public API 파괴?
[ ] 테스트를 약화시켰는가?       ★
[ ] 디버그 코드가 남아 있는가?
```

**"김에 같이 고쳤습니다" 를 조용히 섞지 않는다.**

원자적 커밋 → push → 보고. 상세: `{KIT_ROOT}/references/guides/GIT_WORKFLOW.md`

---

## 8. 완료 조건

`{KIT_ROOT}/references/policy/CODE_DOD.md`.

```
Done =
    Acceptance Criteria 전부 충족
  + Compiler Error 0
  + 관련 Test Pass (신규 + 기존 회귀)
  + Console Error 0
  + Smoke Test Pass (요구된 경우)
  + Diff Gate 통과
  + 원자적 커밋 + Push
```

보고 형식은 `CODE_DOD.md` §5. **Not Changed 섹션이 특히 중요하다** — invariants 증명.

---

## 9. 멈추고 물어야 할 때

`{KIT_ROOT}/references/policy/ESCALATION.md`. C 트랙에서 반드시 묻는 것:

```
검증 불가능한 Acceptance Criteria
코드에서 유도할 수 없는 수치값 (밸런스)
기존 시스템 확장 vs 신규 생성
고위험 변경 승인 (SerializeField / Prefab / Scene / SO / asmdef)
매우 높음 승인 (Input / Addressables / Build Settings)
테스트를 고쳐야만 통과 가능해 보일 때   ← 절대 임의로 고치지 않는다
계약 범위 밖 변경의 처리
```

반대로 아래는 **묻지 말고 그냥 한다**: 테스트 실행, 커밋/푸시(스테이지 완료 시),
변수명, 상수 위치, 폴더 생성, 다음 스테이지 진입(게이트 통과 시).

---

## 10. 비주얼이 함께 걸리면

UI 코드, 카메라 스크립트, 셰이더 파라미터 제어 등은 화면에 영향을 준다.
`visual-director` 스킬과 병행하고, **`CODE_DOD` 와 `VISUAL_DOD` 를 둘 다 충족**해야 한다.
