# CODE_DOD — 코드 작업 완료 정의

> LOAD WHEN: 코드 작업을 "완료" 로 보고하기 직전. **예외 없음.**

---

## 1. 완료가 아닌 것

```
코드 작성 완료
컴파일 성공
내가 보기에 로직이 맞음
기능이 동작하는 것 같음
```

Unity 에서 **컴파일 성공 = 정상 동작이 아니다.**

---

## 2. 완료 정의

```
Done =
    요구사항(Acceptance Criteria) 전부 충족
  + Compiler Error 0
  + 관련 Test Pass (신규 + 기존 회귀)
  + Console Error 0
  + Smoke Test Pass (요구된 경우)
  + Diff Gate 통과
  + 원자적 커밋 + Push
```

하나라도 빠지면 `PARTIAL` 또는 `BLOCKED` 다. `PASS` 가 아니다.

---

## 3. 등급

| 등급 | 기준 |
|---|---|
| PASS | 위 7항목 전부 충족, 증거 존재 |
| PARTIAL | 핵심은 동작하나 일부 AC 미충족 또는 수동 확인 대기 |
| BLOCKED | Editor/권한/결정 대기로 검증 자체가 불가 |
| FAILED | 컴파일 에러 또는 테스트 실패가 남아 있음 |

**확인하지 못한 항목을 성공으로 추정하지 않는다.**

---

## 4. 증거 요구

각 항목은 증거가 있어야 한다. **"돌렸습니다" 는 증거가 아니다.**

| 항목 | 증거 |
|---|---|
| Compile | 컴파일 로그 / exit code |
| EditMode | 테스트 결과 XML, n/n PASS |
| PlayMode | 테스트 결과 XML, n/n PASS |
| Smoke | 테스트 결과 + 콘솔 로그 |
| Console Error 0 | 콘솔 출력 |
| Asset Diff (고위험) | git diff 결과 |
| Reference 무결성 (고위험) | 체크리스트 결과 |

---

## 5. 최종 보고 형식 (필수)

```markdown
## TASK-{nnnn} {제목} — {PASS | PARTIAL | BLOCKED | FAILED}

### Changed
- path (신규/수정, 한 줄 사유)

### Verification
- Compilation:  PASS
- EditMode:     18/18 PASS
- PlayMode:      4/4 PASS
- Smoke Test:   PASS
- Console:      Error 0

### Acceptance Criteria
| AC | 테스트 | 결과 |
|---|---|---|

### Not Changed
- (명시적으로 건드리지 않은 것 — invariants 증명)

### Commits
- {hash} {message}
(pushed to {remote}/{branch})

### Risk / 수동 확인 필요
- ...

### Assumptions
- {가정} — 조정 필요 시 {파일:줄}
```

"구현했습니다" 대비 정보 밀도가 압도적으로 높다.
**Not Changed 섹션이 특히 중요하다** — invariants 가 지켜졌다는 증명이다.

---

## 6. 비주얼이 걸린 코드 작업

코드 변경이 화면에 영향을 주면 **VISUAL_DOD.md 도 함께 만족해야 한다.**

```
CODE_DOD  +  VISUAL_DOD
```

예: UI 코드 수정, 카메라 스크립트, 셰이더 파라미터 제어, VFX 트리거.
