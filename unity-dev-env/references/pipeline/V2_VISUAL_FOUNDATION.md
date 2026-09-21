# V2 — VISUAL FOUNDATION (기반층)

> LOAD WHEN: `VISUAL_SPEC.yaml` 이 `approved: true` 이고 `VisualRebuild.unity` 기반이 아직 없을 때.

**여기서 만드는 것은 에셋이 아니다.** 카메라, 스케일, 조명, Volume, 마스터 셰이더 — 화면 전체를 지배하는 것들이다.

---

## ENTRY GATE
- V1 = `PASS` (`VISUAL_SPEC.yaml` `approved: true`)
- Unity Editor 실행 가능 (`unity status` 정상) — 아니면 `BLOCKED`

## INPUTS
- `Docs/Visual/VISUAL_SPEC.yaml`
- `Docs/Visual/Reference/Concept_Master.png`

---

## STEPS

### 2-A. 새 씬 생성 (기존 씬을 고치지 않는다)

```
Assets/VisualRebuild/
├─ Scenes/VisualRebuild.unity      ← 여기서 전부 새로 쌓는다
├─ Blockout/                        ← V3 프리미티브 전용
├─ Materials/
├─ Shaders/
└─ Profiles/
```

REBASE 모드라도 **기존 씬을 직접 수정하지 않는다.** 기존 비주얼의 잘못된 전제가 새 디자인을 오염시킨다.

### 2-B. 컨셉 오버레이 설치

`Assets/Editor/AIVisual/ConceptOverlay.cs` 를 통해 Game View 위에 컨셉 이미지를
opacity 0 / 25 / 50 / 75 / 100 % 로 토글할 수 있게 한다.

```
Concept
   ↕   ← 직접 겹쳐 본다
Current Unity Render
```

이것이 이후 모든 스테이지의 **1차 계측기**다.

### 2-C. CameraRig — 가장 먼저, 가장 중요

집을 아무리 잘 만들어도 카메라 pitch 가 37° vs 52° 면 완전히 다른 게임처럼 보인다.

`VISUAL_SPEC.camera` 를 그대로 적용:
```
projection / fov(또는 orthographic size) / height / pitch / near-far / aspect
```

캘리브레이션 오브젝트만 배치한다 — 이때 프리미티브 허용 (`BLOCKOUT_` 접두사).
```
BLOCKOUT_HumanProxy   (capsule, height = world_scale.human_height)
BLOCKOUT_DoorProxy    (cube, height = world_scale.door_height)
BLOCKOUT_GroundPlane
BLOCKOUT_BuildingProxy
```

컨셉 오버레이를 켜고 아래가 맞을 때까지 **카메라만** 조정한다:
- 지평선 위치
- 캐릭터 화면 높이 (%)
- 바닥 면적
- 건물 투시 각도
- 화면 점유율

### 2-D. World Scale 고정

`VISUAL_SPEC.world_scale` 을 프로젝트 상수로 박는다.
```
human_height / door_height / floor_height / (2D: pixels_per_unit, reference_resolution)
```
2D 의 `reference_resolution` 과 PPU 는 **에셋 제작 전에 결정하고 이후 변경하지 않는다.**

### 2-E. LightingRig — 두 번째로 중요

컨셉에서 아래를 재현한다:
```
Key Light (방향/색온도/강도)
Ambient
Shadow (농도/부드러움)
Fog
Sky
```

모델이 아직 큐브뿐이어도, **조명이 맞으면 컨셉 방향이 보이기 시작한다.**

### 2-F. Global Volume

`VISUAL_SPEC.postprocessing` 으로 단일 Volume Profile 을 만든다.
```
Assets/VisualRebuild/Profiles/VP_Global.asset
```
Tonemapping / ColorAdjustments / Bloom / Vignette / LUT 등.

```
VISUAL_SPEC
     ↓
VP_Global (단 하나)
     ↓
모든 Scene
```

씬마다 다른 프로파일을 만들지 않는다. 톤 통일이 목적이다.

### 2-G. Master Shader + Material Families

컨셉을 보고 재질을 하나씩 만들지 않는다. **패밀리를 먼저 만든다.**

```
MAT_Master_Stylized  (Shader Graph, 단 하나)
 ├─ Base Color
 ├─ Ramp Lighting
 ├─ AO
 ├─ Top Tint          (world Y 기준)
 ├─ Edge Tint
 ├─ Subtle Noise
 └─ Optional Detail

파생 패밀리
 ├─ MAT_Nature_*
 ├─ MAT_Architecture_*
 ├─ MAT_Character_*
 ├─ MAT_Metal_*
 ├─ MAT_Cloth_*
 └─ MAT_FX_*
```

**이것이 이미지 생성 AI 없이 스타일을 통일하는 핵심 장치다.**
출처가 다른 무료 모델을 섞어도 전부 이 셰이더를 통과시키면 상당 부분 통일된다.

추가로 `MAT_Missing` (마젠타)을 만든다 — `VISUAL_MISSING` 표시용.

### 2-H. 디자인 토큰 (UI)

`VISUAL_SPEC.ui` 를 ScriptableObject 또는 USS 변수로 고정한다.
```
spacing: xs/sm/md/lg/xl
radius: button/panel
font: body/caption/h1
button: min_height / horizontal_padding
```

### 2-I. VisualLinter 설치 + 1회 실행

`references/guides/VISUAL_LINTER_SPEC.md` 대로 `Assets/Editor/AIVisual/VisualLinter.cs` 를
`VISUAL_SPEC.yaml` 을 읽도록 구성하고 실행한다. 이 시점에서 error 0 이어야 한다
(씬에 캘리브레이션 프리미티브만 있고 전부 `BLOCKOUT_` 이므로).

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| Editor 실행 불가 | MANUAL | Editor 실행 요청 |
| 렌더 파이프라인 불명 (Built-in/URP/HDRP) | DECISION | 선택지 제시. URP 권장 |
| URP 미설치인데 스펙이 URP 를 요구 | DECISION | 패키지 설치 승인 요청 |
| 카메라 값을 컨셉에서 3회 반복해도 못 맞춤 | CONFLICT | 추정 후보 2~3안 제시 |
| Shader Graph 미설치 | DECISION | 설치 승인 또는 코드 셰이더 대안 제시 |
| 기존 프로젝트에 이미 다른 Global Volume 이 있음 | RISK | 덮어쓰지 말고 새 프로파일 + 보고 |

---

## EXIT GATE

| # | 조건 | 검증 |
|---|---|---|
| 1 | `VisualRebuild.unity` 존재 | 파일 |
| 2 | Camera 값이 `VISUAL_SPEC.camera` 와 정확히 일치 | VisualLinter |
| 3 | Directional Light 가 스펙과 일치 | VisualLinter |
| 4 | Global Volume 이 `VP_Global` 단일 프로파일 | VisualLinter |
| 5 | `MAT_Master_Stylized` + 패밀리 전부 존재 | 파일 |
| 6 | `MAT_Missing` 존재 | 파일 |
| 7 | ConceptOverlay 동작 | 스크린샷 (오버레이 50% 상태) |
| 8 | 스코어카드 Camera / Lighting / Palette ≥ 3 | `references/guides/SCREENSHOT_LOOP.md` |
| 9 | VisualLinter error 0 | 린터 출력 |

> **8번이 이 스테이지의 핵심이다.** 큐브만 있는 상태에서도 "컨셉의 톤이 보여야" 한다.
> 안 보이면 조명/Volume/팔레트가 아직 틀린 것이다. V3 로 넘어가지 않는다.

## OUTPUTS
- `Assets/VisualRebuild/Scenes/VisualRebuild.unity`
- `Assets/VisualRebuild/Profiles/VP_Global.asset`
- `Assets/VisualRebuild/Shaders/MAT_Master_Stylized`
- `Assets/VisualRebuild/Materials/MAT_*`
- `Assets/VisualTests/Screenshots/iter_01_camera.png`, `iter_02_lighting.png`

## STATE UPDATE
```yaml
stage: V2
status: PASS | BLOCKED
scene: Assets/VisualRebuild/Scenes/VisualRebuild.unity
render_pipeline: URP
master_shader: MAT_Master_Stylized
scorecard: {camera: n, lighting: n, palette: n}
```
