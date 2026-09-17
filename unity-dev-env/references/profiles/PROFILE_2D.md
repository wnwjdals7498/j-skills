# PROFILE_2D — 2D 프로젝트 규칙

> LOAD WHEN: 프로젝트 프로파일이 `2d` 일 때. V 트랙 전 스테이지에서 참조.

---

## 1. 2D 에서 전략이 다른 점

**2D 는 3D 보다 어렵다.** 컨셉에 있는 새 캐릭터 스프라이트나 배경 일러스트가 필요하면
코딩 에이전트만으로는 결국 **원본 이미지가 필요**하다. 이건 MANUAL 로 승격된다.

그러나 아래는 에이전트가 충분히 개선할 수 있다:
```
UI              ★★★★★   구조·여백·타이포·정렬 — 에이전트가 가장 잘하는 영역
크기/비율/PPU   ★★★★★   기술 규격 강제
Tilemap         ★★★★☆   배치·Palette·RuleTile
기존 스프라이트 재조합    ★★★★☆
색상 / 팔레트 / Shader    ★★★★☆
카메라 / Pixel Perfect    ★★★★★
파티클 / VFX              ★★★☆☆
배치 / 레이어 / 정렬       ★★★★☆
```

**생성을 주 파이프라인으로 놓지 않는다.** 승인된 스프라이트 팩 → 정규화 → 조합이 기본선.

### 아이소메트릭이면 3D→2D 프리렌더를 강력 권장

AI 로 strict isometric projection 을 수백 장 유지하는 것은 여전히 어렵다.
```
3D Model
  ↓ Fixed Orthographic Camera   (단일 표준 render scene)
  ↓ Fixed Lighting
  ↓ Fixed Shader
Render
  ↓ (선택) 후처리
2D Sprite
```
카메라/크기/투시 일관성이 거의 완벽하게 고정된다.
**모든 스프라이트를 하나의 표준 render scene 에서 렌더**하면 다운샘플 후에도 남는 차이가 줄어든다.

---

## 2. VISUAL_SPEC.yaml 스키마 (2D)

```yaml
profile: 2d
approved: false
approved_by: null
approved_at: null

target_resolution: [1920, 1080]
reference_resolution: [640, 360]   # ★ 에셋 제작 전에 결정. 이후 변경 금지
render_pipeline: URP

art_style: pixel                   # pixel | handpainted | vector | prerendered_3d

camera:
  projection: orthographic
  orthographic_size: 5.625         # reference_resolution / (2 * PPU)
  pixel_perfect: true
  pixels_per_unit: 32              # 프로젝트 기준 PPU
  upscale_render_texture: true
  crop_frame: none

sprites:                           # 카테고리별 크기 계약 — 크기 문제의 해법
  player:
    source_canvas: [256, 256]
    occupied_height_px: [180, 210]
    pixels_per_unit: 128
    pivot: [0.5, 0.08]
    world_height: [1.55, 1.75]
  npc:
    source_canvas: [256, 256]
    occupied_height_px: [170, 205]
    pixels_per_unit: 128
    pivot: bottom_center
  tree:
    source_canvas: [512, 512]
    pixels_per_unit: 128
    world_height: [3.0, 5.0]
    pivot: bottom_center
  item_icon:
    source_canvas: [128, 128]
    occupied_area_percent: [65, 82]
    padding_px: 12
    pivot: center
  tile:
    source_canvas: [32, 32]
    pixels_per_unit: 32
    pivot: center

import:
  filter_mode: Point               # pixel art 인 경우
  compression: None
  generate_mipmaps: false
  max_texture_size: 2048
  sprite_atlas: true

palette:                           # V1 dominant colors 에서 채운다
  primary_count: 16
  colors:
    - "#726241"
    - "#A88761"
    - "#34382D"
    - "#D7B874"
  shadow_hue: "#3B3A5C"
  highlight_hue: "#E8D08A"
  max_saturation: 0.75

lines:
  outer_contour_px: 3
  inner_detail_px: [1, 2]
  never_pure_black: true

shape_language:
  characters: "round upper body / large hands"
  buildings: "70% straight / 30% curved"
  props: "exaggerated silhouette"
  min_detail_px: 6

detail_density: [character, interactable, environment, background]

lighting:
  main_light_direction: upper_left
  shadow_softness: fixed
  baked_rim_in_texture: forbidden

postprocessing:
  profile: VP_Global
  tonemapping: Neutral
  saturation: 5
  contrast: 6
  bloom_intensity: 0.15

ui:
  spacing: {xs: 4, sm: 8, md: 16, lg: 24, xl: 32}
  radius: {button: 8, panel: 12}
  font: {body: 18, caption: 14, h1: 36}
  button: {min_height: 48, horizontal_padding: 20}
  nine_slice_border_px: 8

forbidden:
  - realistic_skin
  - cinematic_dof
  - glossy_plastic
  - random_rim_lights
  - photorealistic_textures
  - default_unity_material
  - non_uniform_sprite_scale
  - transform_scale_for_sizing     # 크기는 PPU/pivot 으로 맞춘다

notes: |
  형용사는 여기에만. 위 필드는 전부 숫자 또는 HEX.
```

---

## 3. 크기 문제는 컨셉이 아니라 계약 문제

`"사진 사이즈가 안 맞아 컨셉에 맞지 않는 크기로 출력"` 은
**"크기를 잘 맞춰" 라고 지시할 문제가 아니다.** 위 `sprites:` 계약으로 해결한다.

에이전트가 이미지를 새로 그리지 않아도,
들어온 스프라이트의 **크기/PPU/pivot 을 이 기준으로 자동 보정**할 수 있다.
Unity 공식 `sprite-editor` / `2d-pixel-perfect` skill 이 이 강제를 실제로 수행한다.

### 절대 규칙
```
크기는 PPU 와 pivot 으로 맞춘다.
Transform.scale 로 우겨넣지 않는다.
비균등 스케일(x != y)은 금지 — 스프라이트가 늘어난다.
reference_resolution 과 PPU 는 에셋 제작 전에 결정하고 이후 변경하지 않는다.
```

---

## 4. 스테이지별 2D 특이사항

### V2 Visual Foundation
```
CameraRig    orthographic size = reference_resolution.y / (2 * PPU)
             Pixel Perfect Camera 컴포넌트 (pixel art 인 경우)
PPU 고정     프로젝트 전역 상수로 박는다
LightingRig  2D Light (URP 2D Renderer) 또는 라이팅 없이 팔레트로
VP_Global    단일 프로파일
MasterShader Sprite 용. palette 제한 / outline / hue shift / dissolve
```

### V3 Blockout
2D 의 블록아웃은 **단색 사각형 + 올바른 크기**다.
```
BLOCKOUT_ 접두사 + MAT_Blockout_Grey
크기는 sprites 계약의 world_height 를 따른다
Tilemap 은 단색 타일로 레이아웃만
```

### V5 Asset Strategy — 2D 파이프라인
```
Approved sprite pack
        ↓
ASSET_CATALOG.json
        ↓
Unity Sprite Editor        rect / pivot / border / slice
        ↓
PPU / Pivot / Slice 정규화
        ↓
Sprite Atlas               packing
        ↓
Tilemap / RuleTile
        ↓
Global palette / material
```

정규화 필수:
```
[ ] PPU 통일 (카테고리별 계약값)
[ ] pivot 통일
[ ] source_canvas / occupied_height_px 기준 재단
[ ] Point filter / mipmap off / compression None (pixel art)
[ ] Sprite Atlas 편입
[ ] ASSET_CATALOG.json 등록
```

### 새 원본 아트가 필요할 때
```
STOP (MANUAL).
무엇이 왜 필요한지 목록화한다:
  - 카테고리 / 필요 개수 / source_canvas / 스타일 참조
가짜 플레이스홀더를 만들지 않는다. MISSING_ + MAT_Missing 으로 표시.
```

---

## 5. UI 는 2D 에서 가장 큰 개선 여지

UI 는 그림보다 **hierarchy / margin / padding / typography / color / alignment /
spacing / nine-slice / anchors** 가 중요해서 코딩 에이전트가 상대적으로 잘한다.

디자인 토큰만 제대로 만들어도 통일성이 크게 오른다. `ui:` 필드를
ScriptableObject 또는 USS 변수로 고정하고 린터로 강제한다.

공식 `ui-ugui` / `ui-uitk` skill 은 기존 프로젝트의 UI 프레임워크를 먼저 탐지한 뒤
동일 패턴을 따르도록 설계되어 있다. 프레임워크를 섞지 않는다.

---

## 6. VisualLinter 2D 규칙

| 규칙 | 실패 조건 |
|---|---|
| `camera.orthographic_size` | 스펙과 불일치 |
| `camera.pixel_perfect` | 컴포넌트 누락/설정 불일치 |
| `sprite.ppu` | 카테고리 계약값과 불일치 |
| `sprite.pivot` | 계약과 불일치 |
| `sprite.aspect_distorted` | Transform 비균등 스케일 |
| `sprite.transform_scale` | 스케일 != 1 (크기는 PPU 로) |
| `sprite.world_height` | 계약 범위 밖 |
| `sprite.filter_mode` | pixel art 인데 Point 가 아님 |
| `sprite.mipmap` | pixel art 인데 mipmap 활성 |
| `sprite.not_in_atlas` | Atlas 미편입 (경고) |
| `material.default` | `Sprite-Default` 원본 사용 |
| `material.color` | `palette` 에 없는 색 |
| `volume.profile` | `VP_Global` 이 아님 |
| `ui.spacing` | 디자인 토큰 최소값 미만 |
| `ui.font_size` | 토큰에 없는 크기 |
| `asset.not_in_catalog` | 카탈로그에 없는 스프라이트 |
| `missing.present` | `MISSING_` 오브젝트 존재 (경고) |

---

## 7. 2D 에서 흔한 실패 패턴

| 증상 | 원인 | 대응 |
|---|---|---|
| 캐릭터가 배경 대비 너무 크거나 작음 | PPU/pivot 계약 부재 | `sprites:` 계약 도입 후 전수 정규화 |
| 스프라이트가 늘어남 | Transform 비균등 스케일 | 스케일 1 고정, PPU 로 조정 |
| 픽셀이 뭉개짐 | Bilinear filter / mipmap / compression | 임포트 설정 정규화 |
| 타일 경계에 선이 보임 | Atlas padding / filter | Atlas 설정, Point filter |
| UI 가 해상도마다 깨짐 | reference_resolution 미고정 | Canvas Scaler + 토큰 |
| 화면이 산만함 | detail_density 역전 | 배경 채도/디테일 낮추기 |
| 아이소메트릭 각도가 제각각 | 생성 기반 파이프라인 | 3D→2D 프리렌더로 전환 검토 |
