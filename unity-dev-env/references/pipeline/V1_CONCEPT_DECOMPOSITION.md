# V1 — CONCEPT DECOMPOSITION (컨셉아트 → 시각 계약)

> LOAD WHEN: 컨셉아트가 있고 `VISUAL_SPEC.yaml` 이 아직 확정(`approved: true`)되지 않았을 때.

**이 스테이지에서는 코드를 쓰지 않는다.** 씬도 만들지 않는다. 분석과 명세만 한다.

---

## ENTRY GATE
- S0 = `PASS` 또는 `PARTIAL`
- `<PROJECT_ROOT>/Docs/Visual/Reference/` 에 컨셉 이미지가 1장 이상 존재

컨셉 이미지가 없으면 → **STOP (MANUAL).** 에이전트는 이미지를 창작하지 못한다.

## INPUTS
- `Docs/Visual/Reference/Concept_Master.png` (+ 보조 컨셉들)
- `Docs/Visual/VISUAL_SPEC.yaml` (프로파일 템플릿, 아직 비어 있음)

---

## STEPS

### 1-A. 컨셉 이미지 등록

```
Docs/Visual/Reference/
├─ Concept_Master.png          ← 단일 진실 원본
├─ GoldenViews/
│  ├─ World_Main.png
│  ├─ Combat.png
│  ├─ Interior.png
│  ├─ NPC.png
│  ├─ Inventory.png
│  └─ Dialogue.png
```

컨셉이 1장뿐이면 `Concept_Master.png` 만 두고 나머지는 `UNDEFINED` 로 표시 (§1-D).

### 1-B. Semantic Analysis (에이전트가 이미지를 보고 판단)

**아직 아무것도 구현하지 않는다.** 아래만 뽑는다.

```
CAMERA        projection / 추정 FOV / 카메라 높이 / pitch / 피사체 거리 / 지평선 위치
COMPOSITION   focal point / 전경:중경:배경 비율 / 여백 / 시각 밀도 / 지배적 형태
SCALE         player:door / player:building / tree:building / road width:character / UI:viewport
SHAPE         지배적 기하 형태 / 실루엣 특징 / 베벨·둥글기 정도 / 엣지 처리 / 과장 정도
COLOR         주 팔레트 / 강조 팔레트 / 그림자 색 / 배경 채도 / 초점 채도
LIGHTING      광원 방향 / 부드러움 / 앰비언트 레벨 / 그림자 농도 / 난색:한색 관계
MATERIAL      거칠기/무광/광택 / 텍스처 밀도 / 양식화 정도
ENVIRONMENT   지형 구조 / 건물 밀도 / prop 밀도 / 식생 분포
UI            타이포 스케일 / 여백 / 불투명도 / 형태 언어
```

→ `Docs/Visual/CONCEPT_ANALYSIS.yaml` 의 `semantic:` 에 기록.

### 1-C. Deterministic Analysis (스크립트로 측정 — 추정 금지)

**에이전트의 눈을 정확한 계측기로 취급하지 않는다.** 측정 가능한 것은 코드로 측정한다.

로컬 스크립트(Python/PIL 또는 C#)로 뽑는다 — 별도 AI 비용 없음:

```
해상도 / 종횡비
dominant colors (k-means, k=8~16)  → HEX 목록
평균 밝기 / 채도 히스토그램
그림자 영역 평균 색상
하이라이트 영역 평균 색상
주요 오브젝트 bounding box (픽셀 좌표)
화면 점유율 (%)
지평선 y 좌표
UI 여백 (픽셀)
```

→ `CONCEPT_ANALYSIS.yaml` 의 `measured:` 에 기록.

**이 색상들이 그대로 Unity Material / Volume / UI 토큰이 된다.**

스크립트는 `Tools/concept_analyze.py` 에 남겨 재실행 가능하게 한다.

### 1-D. 정의 범위 분류 (매우 중요)

컨셉 한 장에서 알 수 없는 것이 반드시 생긴다. 건물 뒤, 캐릭터 뒤, 실내, 인벤토리, 야간, 전투 이펙트 등.
**상상해서 채우면 스타일이 붕괴된다.**

모든 항목을 셋 중 하나로 태그한다.

| 태그 | 의미 | 처리 |
|---|---|---|
| `REFERENCE_DEFINED` | 컨셉에 직접 보임 | 그대로 스펙에 반영 |
| `REFERENCE_INFERRED` | 보이는 것에서 합리적으로 유추 가능 | 스펙에 반영하되 `inferred: true` 표기 |
| `UNDEFINED` | 컨셉에 없음 | **임의 구현 금지.** 별도 design decision 으로 승격 |

`UNDEFINED` 항목은 V1 종료 시 사용자에게 일괄 질문한다 (`ESCALATION.md` DECISION).

### 1-E. VISUAL_SPEC.yaml 작성

`CONCEPT_ANALYSIS.yaml` → `VISUAL_SPEC.yaml` 로 번역한다.

핵심 원칙: **아트 문서가 아니라 API 명세처럼 쓴다.**

```
✗ "아기자기한 판타지, 따뜻하고 평화로운 분위기, low poly"
✓ camera.fov: 38
✓ world_scale.human_height: 1.75
✓ palette.grass: "#718C4C"
✓ materials.smoothness_max: 0.25
✓ lighting.main_light.color_temperature: 4700
✓ forbidden: [pure_white_material, realistic_pbr, neon_color]
```

**숫자와 HEX 가 아닌 항목은 스펙이 아니다.** 형용사는 `notes:` 로 밀어낸다.

프로파일별 스키마: `references/profiles/PROFILE_3D.md` 또는 `references/profiles/PROFILE_2D.md`

### 1-F. 금지 목록 작성

`forbidden:` 은 허용 목록만큼 중요하다. 컨셉에서 명확히 배제된 것을 적는다.
```yaml
forbidden:
  - pure_white_material
  - pure_black_material
  - realistic_pbr
  - neon_color
  - default_unity_material
  - cinematic_dof
  - photorealistic_microtexture
```

### 1-G. 사용자 승인 요청

`VISUAL_SPEC.yaml` 초안 + `UNDEFINED` 목록을 제시하고 승인을 받는다. **필수.**

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 컨셉 이미지 없음 | MANUAL | 이미지 제공 요청 |
| 컨셉 이미지끼리 서로 모순 | CONFLICT | 어느 것이 master 인지 질문 |
| 측정값 신뢰도가 낮음 (추정 폭 ±30% 이상) | CONFLICT | 추정치 2~3안 제시 후 선택 요청 |
| `UNDEFINED` 항목 존재 | DECISION | **V1 EXIT 전 반드시 일괄 질문** |
| 3D/2D 혼합 여부 불명 | DECISION | 프로파일 선택 질문 |
| VISUAL_SPEC 최종 승인 | DECISION | **에이전트 단독 통과 불가** |

### `UNDEFINED` 질문 템플릿 예시

```markdown
### 결정 항목: 컨셉아트에 없는 영역을 어떻게 처리할까?

| # | 항목 | 선택지 |
|---|---|---|
| 1 | 야간 조명 | (a) 주간 팔레트의 색상 회전 (b) 별도 컨셉 제공 (c) 이번 범위에서 제외 |
| 2 | 실내 씬 | (a) 동일 마스터 셰이더 + 조도만 조정 (b) 별도 컨셉 제공 (c) 범위 제외 |
| 3 | 인벤토리 UI | (a) 디자인 토큰만으로 구성 (b) 별도 컨셉 제공 (c) 범위 제외 |

**추천:** 전부 (c) 로 두고 World_Main 하나만 먼저 완성 →
그것이 V4 를 통과한 뒤 그 스타일을 나머지에 복제하는 것이 실패 확률이 가장 낮다.
```

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | `CONCEPT_ANALYSIS.yaml` 에 `semantic:` + `measured:` 둘 다 채워짐 |
| 2 | 모든 항목이 `REFERENCE_DEFINED` / `REFERENCE_INFERRED` / `UNDEFINED` 중 하나로 태그됨 |
| 3 | `VISUAL_SPEC.yaml` 의 필수 필드가 **숫자/HEX 로** 채워짐 (형용사 없음) |
| 4 | `forbidden:` 이 비어 있지 않음 |
| 5 | `VISUAL_SPEC.yaml` 에 `approved: true` + `approved_by` + `approved_at` 기록 (**사용자 승인**) |
| 6 | `UNDEFINED` 항목의 처리 방침이 `decisions:` 에 기록됨 |

## OUTPUTS
- `Docs/Visual/CONCEPT_ANALYSIS.yaml`
- `Docs/Visual/VISUAL_SPEC.yaml` (approved)
- `Tools/concept_analyze.py`

## STATE UPDATE
```yaml
stage: V1
status: PASS | BLOCKED
concept_master: Docs/Visual/Reference/Concept_Master.png
spec_approved_at: <iso8601>
undefined_items: [...]
decisions:
  - key: night_lighting
    value: out_of_scope
```
