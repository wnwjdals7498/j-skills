# UNITY_RISK_ZONES — Unity 고유 위험 영역

> LOAD WHEN: C3 에서 위험도를 판정할 때. 파일을 이동/삭제/이름변경 하기 직전.
>
> **C# 관점에서 완벽한 변경이 Unity 에서는 데이터 사고가 될 수 있다.**

---

## 1. .meta 와 GUID

Unity 의 오브젝트 참조는 에셋 `.meta` 에 저장된 **GUID** 로 연결된다.
파일 경로가 아니라 GUID 다. 그래서 파일을 옮겨도 참조가 유지된다 — `.meta` 를 함께 옮기면.

### 금지
```
.meta 파일을 임의 삭제
OS 레벨 delete + recreate 로 에셋 이동/이름변경
파일만 이동하고 .meta 를 남겨둠
.meta 를 gitignore 에 추가
```

### 허용
```
Unity Editor 안에서 이동/이름변경
파일과 .meta 를 항상 함께 이동 (git mv 도 함께)
삭제 시 파일과 .meta 를 함께 삭제
```

**참조가 끊기면 Missing Prefab / Missing Script 로 나타난다.** 변경 후 반드시 확인한다.

---

## 2. SerializeField

```csharp
[SerializeField] private float speed;
        // 이름만 바꿈
[SerializeField] private float movementSpeed;
```

C# 리팩터링으로는 완벽하다. 하지만 Unity 는 **필드 이름으로 직렬화 값을 찾는다.**
이름이 바뀌면 Inspector 에 저장된 기존 값이 유실되고 기본값(0)으로 돌아간다.

### 해결

```csharp
using UnityEngine.Serialization;

[FormerlySerializedAs("speed")]
[SerializeField] private float movementSpeed;
```

### 변경 유형별 처리

| 변경 | 위험 | 처리 |
|---|---|---|
| 이름 변경 | 값 유실 | FormerlySerializedAs 부착 |
| 타입 변경 (float→int 등) | 값 유실/왜곡 | 새 필드 추가 + 마이그레이션 코드 + 구 필드 유지 후 제거 |
| 필드 삭제 | 데이터 손실 | 사용 중인 Prefab/Scene 전수 조사 후 진행 |
| SerializeField 제거 | 값 유실 | 의도적인지 확인 |
| SerializeField 추가 | 새 값이 기본값 | Prefab/Scene 에서 값 설정 필요 |
| private → public | 직렬화 유지 | 상대적으로 안전 |
| 컨테이너 구조 변경 | 값 유실 | Dictionary 는 직렬화되지 않음. 주의 |

**변경 후 실제 Prefab/Scene 을 열어 Inspector 값을 눈으로 확인한다.**

---

## 3. ScriptableObject 구조 변경

SO 는 에셋 파일에 값이 저장된다. 구조를 바꾸면 기존 에셋 전부가 영향을 받는다.

```
[ ] 필드 변경 시 SerializeField 규칙 전부 적용
[ ] 해당 SO 타입의 모든 에셋 인스턴스를 열거
[ ] 마이그레이션이 필요하면 Editor 스크립트 작성
[ ] 변경 후 각 인스턴스의 값 확인
```

SO 구조 변경은 항상 **고위험**이다.

---

## 4. Prefab

```
Prefab 수정은 명시적으로 요청받은 경우에만 수행한다.
```

위험 요소:
```
Prefab Variant 관계
Nested Prefab
Prefab Override (인스턴스별 덮어쓴 값)
Missing Script (스크립트를 지우거나 옮겼을 때)
```

Prefab 을 건드렸으면 **diff 를 별도 검토**하고 **커밋을 코드와 분리**한다.

---

## 5. Scene

Scene 도 Prefab 과 동일하게 취급한다. 추가로:
```
[ ] 라이팅 데이터(Lightmap) 재생성 필요 여부
[ ] NavMesh 재베이크 필요 여부
[ ] Scene 내 오브젝트 참조
[ ] Build Settings 의 씬 목록
```

### Force Text 직렬화

Scene/Prefab diff 를 검토하려면 Force Text 직렬화가 켜져 있어야 한다 (Editor 기본 설정).
꺼져 있으면 **바이너리라 diff 검토가 불가능**하다 → C3 에서 확인/보고.

---

## 6. asmdef

```
[ ] 신설 → 고위험. 승인 필요
[ ] 참조 추가/제거 → 고위험. 아키텍처 경계 변경
[ ] 순환 참조 → 컴파일 실패. 설계가 틀린 것
[ ] Auto Referenced 변경 → 예상치 못한 컴파일 오류
[ ] 플랫폼/Define 제약 변경 → 특정 플랫폼에서만 깨질 수 있음
```

asmdef 변경 후에는 **전체 재컴파일**을 확인한다.

---

## 7. 매우 높음 등급

| 영역 | 왜 위험한가 |
|---|---|
| Input System / Input Actions | 에셋 기반. 액션 이름 변경 시 전 바인딩 영향 |
| Addressables | 그룹/라벨/주소 변경 시 런타임 로드 실패. 빌드해야 드러남 |
| Build Settings | 씬 목록, 플랫폼 설정. 빌드 검증 필요 |
| Player Settings | 스크립팅 백엔드, API 레벨. 전역 영향 |
| Package manifest | 반드시 CLI 경유 (SAFETY_RULES.md) |
| Project Settings 전반 | Physics, Time, Quality — 게임플레이 전반에 영향 |

이 영역은 **사용자 승인 + 빌드 검증**까지 필요하다.

---

## 8. 변경 후 무결성 체크리스트

고위험 변경 후 반드시 실행:

```
[ ] Missing Prefab 0
[ ] Missing Script 0
[ ] SerializedField 참조 끊김 0
[ ] Inspector 저장값 보존 확인 (FormerlySerializedAs 동작)
[ ] Animator Controller 연결 유지
[ ] Collider / Rigidbody 유지
[ ] Tag / Layer 유지
[ ] UnityEvent 바인딩 유지
[ ] NavMesh / 물리 설정 유지
[ ] 콘솔 에러 0 (Play Mode 진입)
```

---

## 9. 위험도 요약표 (C3 판정용)

| 변경 종류 | 위험도 |
|---|---|
| 순수 C# 계산 로직 | 낮음 |
| 일반 클래스 추가 | 낮음 |
| MonoBehaviour 로직 | 중간 |
| Inspector 공개 필드 변경 | 중간~높음 |
| SerializeField 변경 | 높음 |
| ScriptableObject 구조 변경 | 높음 |
| Prefab 변경 | 높음 |
| Scene 변경 | 높음 |
| asmdef 변경 | 높음 |
| Input / Addressables / Build Settings | 매우 높음 |
