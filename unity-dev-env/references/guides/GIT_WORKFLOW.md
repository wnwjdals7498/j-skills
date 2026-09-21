# GIT_WORKFLOW — 원자적 커밋과 Diff Gate

> LOAD WHEN: C6 에서 커밋할 때. 브랜치/푸시 전략이 필요할 때.

Git 은 백업이 아니라 **파이프라인의 일부**다.

---

## 1. 단위

```
Task
 ↓ Agent implementation
 ↓ Tests
 ↓ Diff review
Atomic commit
```

한 커밋 = 한 논리 변경. C4 의 STEP 단위와 일치시킨다.

```
feat: add combat cooldown model
feat: integrate combat with player controller
test: add combat playmode smoke test
```

### 가장 위험한 형태

```
47 files changed
+3,842
-1,931
```

뒤에 "구현 완료했습니다". 문제가 생겨도 **어느 변경 때문인지 분리할 수 없다.**

---

## 2. 커밋 메시지

Conventional Commits.

```
<type>: <subject>

<body — 왜가 자명하지 않을 때만>
```

| type | 용도 |
|---|---|
| feat | 기능 추가 |
| fix | 버그 수정 |
| refactor | 동작 변화 없는 구조 개선 |
| test | 테스트 추가/수정 |
| docs | 문서 |
| chore | 빌드/설정/잡무 |
| perf | 성능 |
| build | 빌드 시스템/의존성 |

규칙:
```
subject 50자 이내, 명령형, 마침표 없음
body 는 무엇을 이 아니라 왜 를 쓴다 (무엇은 diff 가 말해준다)
되돌릴 때 알아야 할 것을 body 에 남긴다
```

---

## 3. 커밋 분리 규칙

| 분리 대상 | 이유 |
|---|---|
| 코드 ↔ Scene/Prefab | 되돌릴 때 한쪽만 원복 가능해야 함 |
| 고위험 ↔ 저위험 | 문제 발생 시 원인 격리 |
| 기능 ↔ 리팩터링 | 리뷰 가능성 |
| 기능 ↔ 포맷팅 | diff 노이즈 제거 |
| 프로덕션 코드 ↔ 테스트 수정 | 테스트 약화를 눈에 띄게 |

---

## 4. 브랜치

기본 브랜치에 직접 작업 중이면 **브랜치 생성을 먼저 제안한다.**

```
feat/TASK-0007-melee-attack
fix/TASK-0012-enemy-hp-underflow
refactor/TASK-0015-split-player-controller
```

---

## 5. Push

각 스테이지/태스크 완료 시 원격에 push 한다. 사용자가 다른 환경에서 확인할 수 있어야 한다.

```bash
git push <remote> <branch>
```

push 실패(권한/인증)는 MANUAL 로 승격. 에러 원문과 해결 절차를 준다.
**강제 푸시는 사용자가 명시적으로 요청하지 않는 한 하지 않는다.**

---

## 6. Diff Gate 체크리스트 (C6 본체)

커밋 전에 전부 답한다.

```
[ ] 왜 이 파일을 수정했는가?                      (파일별 한 줄)
[ ] 요구사항과 관계없는 변경은 없는가?
[ ] non_goals 를 구현하지 않았는가?
[ ] out_of_bounds 를 건드리지 않았는가?
[ ] invariants 가 유지되는가?
[ ] 새 global state / Singleton 을 추가했는가?
[ ] SerializeField 를 변경했는가?                 → FormerlySerializedAs
[ ] Scene/Prefab 을 건드렸는가?                   → 별도 커밋 + diff 검토
[ ] .meta 를 삭제/재생성했는가?
[ ] asmdef dependency 를 변경했는가?
[ ] 기존 public API 를 깨뜨렸는가?
[ ] 테스트를 약하게 만들어 통과시킨 것은 아닌가?  ★
[ ] 디버그 로그/주석/임시 코드가 남아 있지 않은가?
```

범위 밖 변경 발견 시:
```
1. 되돌린다 (기본)
2. 되돌릴 수 없으면 보고서에 사유 명시
3. 별도 태스크로 분리 제안
```

**"김에 같이 고쳤습니다" 를 조용히 섞지 않는다.**

---

## 7. Unity 프로젝트의 .gitignore

Unity 표준 gitignore 를 쓴다. 핵심:

```
Library/
Temp/
Obj/
Build/
Builds/
Logs/
UserSettings/
*.csproj
*.sln
```

**`.meta` 파일은 절대 무시하지 않는다.** GUID 참조가 깨진다.

---

## 8. 커밋하지 않는 것

```
사용자가 요청하지 않은 커밋
자격증명 / 라이선스 키 / 토큰
Library/ 등 생성물
대용량 바이너리 (LFS 검토)
검증(C5)을 통과하지 않은 코드
```
