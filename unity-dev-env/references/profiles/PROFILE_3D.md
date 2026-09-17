# PROFILE_3D — 3D 프로젝트 규칙

> LOAD WHEN: 프로젝트 프로파일이 `3d` 일 때. V 트랙 전 스테이지에서 참조.
>
> 프로파일은 스테이지 문서를 **덮어쓰지 않고 채운다.** 스테이지가 뼈대, 프로파일이 수치.

---

## 1. 3D 에서 전략이 다른 점

> **스타일을 AI 생성에서 해결하지 말고 Unity 렌더러에서 해결한다.**

에셋 출처가 제각각이어도 (기존 프로젝트 + 무료 팩 + ProBuilder)
**전부 동일한 마스터 셰이더 / 조명 / Volume / LUT 를 통과시키면** 상당 부분 통일된다.

```
Shape consistency    = generation 단계 (에셋 선택/조립)
Rendering consistency = Unity 단계     ← 3D 의 주 전장
```

단, **잘못된 실루엣/형태는 렌더러가 고쳐주지 않는다.** 그건 V3 Blockout 의 몫.

### 코딩 에이전트에게 3D 가 유리한 이유

이미지를 창작하지 못하는 에이전트도 아래는 잘한다:
```
기존 modular mesh 선택 + 조합
scale 제한 준수
material 교체
shader 통일
lighting 통일
ProBuilder 절차적 지오메트리 (제약이 주어졌을 때)
```
**모델을 생성하지 않는다. 조립한다.** 레고 방식.

---

## 2. VISUAL_SPEC.yaml 스키마 (3D)

```yaml
profile: 3d
approved: false
approved_by: null
approved_at: null

target_resolution: [1920, 1080]
render_pipeline: URP            # URP | HDRP | BuiltIn

camera:
  projection: perspective       # perspective | orthographic
  fov: 38                       # perspective 일 때
  orthographic_size: null       # orthographic 일 때
  height_range: [8, 12]
  pitch: 35                     # degrees
  near: 0.3
  far: 300

world_scale:
  human_height: 1.75
  door_height: 2.2
  door_width: 1.1
  floor_height: 3.0
  window_height: 0.9

geometry:
  style: low_poly               # low_poly | mid_poly | realistic
  bevel: required
  hard_90_degree_edges: avoid
  tiny_geometry: forbidden
  min_feature_size_m: 0.05

palette:                        # V1 의 dominant colors 에서 채운다
  grass: "#718C4C"
  soil: "#6D513B"
  wood_dark: "#5C3A29"
  wood_light: "#956841"
  stone: "#80817B"
  accent: "#D7B874"

materials:
  master_shader: MAT_Master_Stylized
  families: [Nature, Architecture, Character, Metal, Cloth, FX]
  metallic: 0
  smoothness_max: 0.25
  normal_strength_max: 0.3

lighting:
  main_light:
    rotation: [45, -35, 0]
    color_temperature: 4700
    intensity: 1.1
  ambient_intensity: 0.35
  shadow_strength: 0.7
  fog:
    enabled: true
    color: "#A8B4A0"
    density: 0.012

postprocessing:
  profile: VP_Global
  tonemapping: Neutral          # Neutral | ACES | None
  saturation: 10
  contrast: 8
  bloom_intensity: 0.3
  vignette: 0.2
  lut: null

architecture:
  wall_height: 2.8
  wall_thickness: 0.2
  roof_pitch_range: [35, 50]
  footprint_grid_m: 0.5

ui:
  spacing: {xs: 4, sm: 8, md: 16, lg: 24, xl: 32}
  radius: {button: 8, panel: 12}
  font: {body: 18, caption: 14, h1: 36}
  button: {min_height: 48, horizontal_padding: 20}

forbidden:
  - pure_white_material
  - pure_black_material
  - realistic_pbr
  - neon_color
  - default_unity_material
  - cinematic_dof
  - photorealistic_microtexture
  - non_uniform_scale

notes: |
  형용사는 여기에만 쓴다. 위 필드는 전부 숫자 또는 HEX.
```

---

## 3. 스테이지별 3D 특이사항

### V2 Visual Foundation
```
CameraRig    perspective FOV / pitch / height 를 먼저 고정. 이것이 30% 를 지배한다
LightingRig  Directional 1개 + Ambient + Fog. 색온도까지 맞춘다
VP_Global    단일 프로파일. 씬마다 만들지 않는다
MasterShader Shader Graph 기반. ramp shading / vertex color tint / top tint /
             world Y gradient / controlled specular / distance fade / subtle noise
```

캘리브레이션 오브젝트:
```
BLOCKOUT_HumanProxy    capsule, height = world_scale.human_height
BLOCKOUT_DoorProxy     cube,    height = world_scale.door_height
BLOCKOUT_BuildingProxy cube,    wall_height 기준
BLOCKOUT_GroundPlane
```

### V3 Blockout — ProBuilder 우선
프리미티브보다 ProBuilder 를 쓴다. 제약을 파라미터로 준다.
```
Allowed: ProBuilder cube / prism / stair / approved roof modules
Constraints: footprint / floor_height / wall_thickness / door / window / roof_pitch
Materials: 승인 패밀리만
모든 카메라 가시 엣지에 bevel
```

### V5 Asset Strategy — 조달 우선순위
```
1. 기존 메시 재활용 + 마스터 머티리얼 (비용 0, 효과 큼)
2. 단일 계열 CC0 팩 (Quaternius MegaKit 등)
3. ProBuilder 모듈러 조합
4. 절차적 셰이더로 개성 부여 (텍스처 대신)
```

정규화 필수:
```
[ ] 스케일 정규화 (프리팹 단계)
[ ] 피벗 = 바닥 중심
[ ] 마스터 머티리얼 적용, 원본 baked lighting 무시
[ ] 폴리곤 밀도가 스펙과 크게 다르면 제외
[ ] 비균등 스케일 금지 — 필요하면 메시 교체
```

---

## 4. VisualLinter 3D 규칙

| 규칙 | 실패 조건 |
|---|---|
| `camera.projection` | 스펙과 불일치 |
| `camera.fov` | 스펙 ±0.5 초과 |
| `camera.pitch` | 스펙 ±1도 초과 |
| `light.rotation` | 스펙 ±2도 초과 |
| `light.color_temperature` | 스펙 ±100K 초과 |
| `volume.profile` | `VP_Global` 이 아님 |
| `material.default` | `Default-Material` / `Lit` 원본 사용 |
| `material.family` | 마스터 셰이더 파생이 아님 |
| `material.color` | `palette` 에 없는 색 |
| `material.metallic` | 스펙 초과 |
| `material.smoothness` | `smoothness_max` 초과 |
| `transform.non_uniform_scale` | x/y/z 불일치 |
| `transform.catalog_scale` | `allowedScale` 범위 밖 |
| `primitive.outside_blockout` | Blockout 루트 밖에 프리미티브 메시 |
| `asset.not_in_catalog` | `ASSET_CATALOG.json` 에 없는 메시 |
| `missing.present` | `MISSING_` 접두사 오브젝트 존재 (경고) |

---

## 5. 3D 에서 흔한 실패 패턴

| 증상 | 원인 | 대응 |
|---|---|---|
| 에셋은 예쁜데 한 화면에 놓으면 따로 놈 | 각 에셋의 baked lighting/PBR 이 다름 | 마스터 셰이더 강제, 원본 텍스처의 조명 정보 무시 |
| 컨셉과 전혀 다른 느낌 | 카메라 pitch/FOV 불일치 | V2 로 롤백. 카메라부터 |
| 스케일 감이 이상 | world_scale 미고정 | human_height 기준으로 전부 재조정 |
| 건물이 상자 같음 | bevel 없음, 90도 엣지 | ProBuilder bevel, roof_pitch 적용 |
| 색이 튐 | palette 밖 색상 사용 | 린터 `material.color` 규칙 |
| 무료 팩을 섞어 통일성 붕괴 | 여러 제작자 혼용 | 한 계열로 축소 (V5 DECISION) |
