# VISUAL_LINTER_SPEC — 자동 시각 검사 명세

> LOAD WHEN: `VisualLinter.cs` 를 구현/수정할 때. V2 에서 최초 설치.
>
> **에이전트는 정량 실패 조건이 있을 때 훨씬 잘한다.** 이 린터가 그 조건을 제공한다.

---

## 1. 역할

```
VISUAL_SPEC.yaml  +  ASSET_CATALOG.json
        ↓
   VisualLinter
        ↓
Scene Check 결과 (error / warning)
```

출력 예:
```
Scene Check — VisualRebuild.unity
────────────────────────────────────────
✓ Camera FOV = 38
✓ Directional Light = LightingRig
✓ Global Volume = VP_Global

✗ ERROR   primitive.outside_blockout   Cube primitive found: HouseTemp
✗ ERROR   material.default             Default-Material used: Prop_12
✗ ERROR   transform.catalog_scale      Tree scale 2.31 exceeds max 1.20
✗ ERROR   sprite.ppu                   PPU mismatch: npc_merchant (64, expected 128)
✗ ERROR   sprite.aspect_distorted      HUD_QuestIcon scale (1.0, 1.4, 1.0)
✗ ERROR   material.family              Building material not approved: MAT_Custom_9
✗ ERROR   ui.spacing                   Padding 6px below minimum 12px: ShopPanel
⚠ WARN    missing.present              MISSING_Fountain

Errors: 7   Warnings: 1
```

---

## 2. 구현 위치

```
<PROJECT_ROOT>/Assets/Editor/AIVisual/VisualLinter.cs
```

- `Game.Editor` asmdef 아래. 런타임 빌드에 포함되지 않는다.
- 메뉴 항목 + 정적 메서드 두 경로로 호출 가능해야 한다
  (CLI `-executeMethod` 및 `unity command` 에서 호출).
- 결과를 콘솔과 **파일** 양쪽에 낸다: `Assets/VisualTests/lint_result.json`
  (에이전트가 파싱하고, 증거로 남긴다).

---

## 3. 규칙 카테고리

규칙 ID 는 `{영역}.{항목}` 형식. 프로파일별 활성 규칙은 `PROFILE_3D.md` / `PROFILE_2D.md` 참조.

### 공통
| ID | 검사 | 등급 |
|---|---|---|
| `camera.projection` | 스펙과 일치 | error |
| `camera.fov` / `camera.orthographic_size` | 스펙 ±허용오차 | error |
| `camera.pitch` | 스펙 ±1도 | error |
| `light.rotation` | 스펙 ±2도 | error |
| `light.color_temperature` | 스펙 ±100K | error |
| `light.intensity` | 스펙 ±0.1 | error |
| `volume.profile` | `VP_Global` 단일 | error |
| `volume.duplicate` | Global Volume 이 2개 이상 | error |
| `material.default` | 기본 머티리얼 사용 | error |
| `material.family` | 마스터 셰이더 파생이 아님 | error |
| `material.color` | `palette` 에 없는 색 (ΔE 허용치 내 매칭) | error |
| `asset.not_in_catalog` | `ASSET_CATALOG.json` 에 없음 | error |
| `primitive.outside_blockout` | Blockout 루트 밖 프리미티브 | error |
| `blockout.naming` | Blockout 하위인데 `BLOCKOUT_` 접두사 없음 | error |
| `missing.present` | `MISSING_` 접두사 오브젝트 | warning |
| `ui.spacing` | 디자인 토큰 최소값 미만 | error |
| `ui.font_size` | 토큰에 없는 크기 | error |

### 3D 전용
| ID | 검사 |
|---|---|
| `material.metallic` | 스펙 초과 |
| `material.smoothness` | `smoothness_max` 초과 |
| `transform.non_uniform_scale` | x/y/z 불일치 |
| `transform.catalog_scale` | `allowedScale` 범위 밖 |
| `geometry.tiny_feature` | `min_feature_size_m` 미만 (경고) |

### 2D 전용
| ID | 검사 |
|---|---|
| `camera.pixel_perfect` | 컴포넌트/설정 불일치 |
| `sprite.ppu` | 카테고리 계약값과 불일치 |
| `sprite.pivot` | 계약과 불일치 |
| `sprite.aspect_distorted` | 비균등 스케일 |
| `sprite.transform_scale` | 스케일 != 1 |
| `sprite.world_height` | 계약 범위 밖 |
| `sprite.filter_mode` | pixel art 인데 Point 아님 |
| `sprite.mipmap` | pixel art 인데 mipmap 활성 |
| `sprite.not_in_atlas` | Atlas 미편입 (경고) |

---

## 4. 예외 규칙 (오탐 방지)

린터가 과하게 울면 무시하게 된다. 아래는 예외 처리한다.

```
Blockout 루트 하위 (BLOCKOUT_ 접두사)  → primitive / material.family / material.color 면제
MISSING_ 접두사                        → material / catalog 규칙 면제, missing.present 만 warning
Editor-only 오브젝트                   → 전부 면제
비활성(inactive) 오브젝트              → warning 으로 강등
UI 의 투명 레이아웃 그룹               → material 규칙 면제
```

예외는 **스펙 파일에 명시**한다. 코드에 하드코딩하지 않는다.
```yaml
linter:
  exempt_roots: [Blockout, EditorOnly]
  exempt_prefixes: [BLOCKOUT_, MISSING_, DEBUG_]
  color_delta_e_tolerance: 6
```

---

## 5. 판정과 게이트 연동

| 결과 | DoD 등급 |
|---|---|
| error 0, warning 0 | PASS 가능 |
| error 0, warning > 0 | PASS 가능 (warning 은 보고) |
| error > 0 | **FAILED** — 완료 보고 금지 |

`VISUAL_DOD.md` §4 와 연동된다. 린터 error 가 있으면 어떤 경우에도 PASS 가 아니다.

---

## 6. 구현 요구사항

```
[ ] VISUAL_SPEC.yaml 을 읽는다 (하드코딩 금지)
[ ] ASSET_CATALOG.json 을 읽는다
[ ] 프로파일(3d/2d)에 따라 활성 규칙 세트를 바꾼다
[ ] 현재 씬 또는 지정 씬을 대상으로 실행
[ ] 결과를 콘솔 + JSON 파일에 출력
[ ] 규칙별 error/warning 등급을 스펙에서 조정 가능
[ ] 메뉴 + 정적 메서드 두 경로 제공
[ ] 예외 규칙을 스펙에서 읽는다
[ ] 규칙 추가가 쉬운 구조 (규칙 1개 = 클래스/메서드 1개)
```

YAML 파서가 없으면 스펙을 JSON 으로도 읽을 수 있게 한다
(`VISUAL_SPEC.yaml` 옆에 생성된 `VISUAL_SPEC.json`).

---

## 7. 확장

새 규칙이 필요하면:
```
1. 규칙 ID 를 정한다 ({영역}.{항목})
2. 이 문서의 표에 추가한다
3. 해당 프로파일 문서의 린터 규칙 표에 추가한다
4. VisualLinter.cs 에 구현한다
5. 예외가 필요하면 스펙의 linter: 섹션에 필드를 추가한다
```

**린터 규칙을 추가하는 것이 문서에 규칙을 적는 것보다 강력하다.**
문서는 에이전트가 잊을 수 있지만 린터는 잊지 않는다.
