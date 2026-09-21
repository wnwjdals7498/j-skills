# C6 — DIFF GATE (변경 자기검토와 원자적 커밋)

> LOAD WHEN: C5 = PASS. **완료 보고 직전. 건너뛰지 않는다.**

Git 은 백업이 아니라 파이프라인의 일부다.
가장 위험한 형태: `47 files changed / +3,842 / -1,931` 뒤에 "구현 완료했습니다".

---

## ENTRY GATE
- C5 = `PASS` (컴파일 0 / 테스트 통과 / 콘솔 0)

## INPUTS
- `git diff` / `git status`
- Task Contract (`out_of_bounds`, `invariants`, `non_goals`)

---

## STEPS

### 6-A. Diff 자기 심문 (전부 답해야 한다)

```
[ ] 왜 이 파일을 수정했는가?                      (파일별로 한 줄)
[ ] 요구사항과 관계없는 변경은 없는가?
[ ] non_goals 에 있는 것을 구현하지 않았는가?
[ ] out_of_bounds 영역을 건드리지 않았는가?
[ ] invariants 가 유지되는가?
[ ] 새로운 global state 를 추가했는가?
[ ] 새 Singleton 을 추가했는가?
[ ] SerializeField 를 변경했는가?                  → FormerlySerializedAs 확인
[ ] Scene/Prefab 을 건드렸는가?                    → 별도 diff 검토
[ ] .meta 파일을 삭제·재생성했는가?
[ ] asmdef dependency 를 변경했는가?
[ ] 기존 public API 를 깨뜨렸는가?
[ ] 테스트를 약하게 만들어 통과시킨 것은 아닌가?   ★
[ ] 디버그 코드/주석/로그가 남아 있지 않은가?
[ ] TODO 를 남겼다면 이유가 명확한가?
```

하나라도 "예" 인데 계약에 없던 것이면 → **되돌리거나 사용자에게 신고한다.**

### 6-B. 범위 이탈 처리

요구사항과 무관한 변경을 발견하면:
```
① 되돌린다 (기본)
② 되돌릴 수 없다면(부수적으로 필요했다면) 보고서에 사유와 함께 명시
③ 별도 태스크로 분리 제안
```

**"김에 같이 고쳤습니다" 를 조용히 섞지 않는다.**

### 6-C. 원자적 커밋

C4 의 STEP 단위로 커밋한다. 한 커밋 = 한 논리 변경.

```
feat: add combat cooldown model
feat: integrate combat with player controller
test: add combat playmode smoke test
```

커밋 메시지 규칙 (Conventional Commits):
```
<type>: <subject>          # subject 는 50자 이내, 명령형

body (왜가 자명하지 않을 때만)
- 무엇을 왜 바꿨는지
- 되돌릴 때 알아야 할 것
```

type: `feat` `fix` `refactor` `test` `docs` `chore` `perf` `build`

상세: `references/guides/GIT_WORKFLOW.md`

### 6-D. Scene/Prefab 커밋 분리

Scene/Prefab 변경은 **코드 커밋과 분리한다.** 되돌릴 때 코드만/에셋만 원복할 수 있어야 한다.

### 6-E. Push

커밋 후 원격에 push 한다. 사용자가 다른 환경에서 확인할 수 있어야 한다.
```bash
git push <remote> <branch>
```
기본 브랜치에 직접 작업 중이면 브랜치를 먼저 만드는 것을 제안한다.

### 6-F. 최종 보고

```markdown
## TASK-0007 근접 공격 — PASS

### Changed
- Assets/Scripts/Combat/CombatModel.cs        (신규, 순수 C#)
- Assets/Scripts/Player/PlayerCombat.cs       (신규, MonoBehaviour)
- Assets/Scripts/Player/PlayerController.cs   (수정 1줄, 입력 라우팅)
- Assets/Tests/EditMode/CombatModelTests.cs   (신규, 6 케이스)

### Verification
- Compilation:  PASS
- EditMode:     18/18 PASS
- PlayMode:      4/4 PASS
- Smoke Test:   PASS
- Console:      Error 0

### Acceptance Criteria
| AC | 테스트 | 결과 |
|---|---|---|
| 쿨다운 0.4초 | Cooldown_BlocksWithin04s | PASS |
| 범위 내 Enemy 만 | OnlyEnemiesInCone | PASS |
| 죽은 Enemy 제외 | DeadEnemyExcluded | PASS |
| 연타 무시 | RapidInput_SingleHit | PASS |

### Not Changed
- Player movement
- Enemy AI
- Prefabs / Scenes

### Commits
- a1b2c3d feat: add combat cooldown model
- e4f5g6h feat: integrate combat with player controller
- i7j8k9l test: add combat playmode smoke test
(pushed to github/master)

### Risk / 수동 확인 필요
- 공격 애니메이션 이벤트 타이밍은 수동 확인 필요 (non_goal 로 애니메이션 미연동)

### Assumptions
- 쿨다운 0.4초는 기존 DashAbility.cooldown=0.5 기준 추정. 조정 필요 시 CombatModel.cs:12
```

`"구현했습니다"` 보다 정보 밀도가 압도적으로 높다.

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 계약 범위를 벗어난 변경 발견 | DECISION | 되돌릴지 유지할지 질문 |
| 테스트를 약화시킨 것을 발견 | DECISION | **자진 신고 후** 원복 여부 질문 |
| Scene/Prefab diff 가 예상 밖으로 큼 | RISK | 내용 제시 후 승인 요청 |
| 기본 브랜치에 직접 커밋해야 함 | DECISION | 브랜치 생성 제안 |
| push 권한/인증 실패 | MANUAL | 에러 원문 + 해결 절차 안내 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | Diff 자기 심문 체크리스트 전부 응답 |
| 2 | 계약 범위 밖 변경 0 (또는 신고 완료) |
| 3 | 커밋이 STEP 단위로 분리됨 |
| 4 | Scene/Prefab 커밋이 코드 커밋과 분리됨 |
| 5 | push 완료 (또는 실패 사유 보고) |
| 6 | 최종 보고서 작성 (Changed / Verification / Not Changed / Risk / Assumptions) |

## OUTPUTS
- 원자적 커밋들
- 최종 보고서

## STATE UPDATE
```yaml
stage: C6
status: PASS
commits: [a1b2c3d, e4f5g6h, i7j8k9l]
pushed: true
scope_violations: 0
manual_followups: ["공격 애니메이션 타이밍 확인"]
```
