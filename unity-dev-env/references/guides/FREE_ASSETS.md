# FREE_ASSETS — 무료 에셋 조달

> LOAD WHEN: V5 에서 외부 에셋 도입을 검토할 때.

---

## 1. 대원칙: 많이 모으지 말고 **한 계열만** 쓴다

여러 제작자의 팩을 섞으면 통일성이 무너진다. 마스터 셰이더가 상당 부분 덮어주지만
**형태 언어(shape language)와 폴리곤 밀도는 셰이더로 못 고친다.**

```
✗ Kenney 3개 + Quaternius 2개 + Asset Store 무료 5개
✓ Quaternius 단일 제작자의 MegaKit 계열만
```

---

## 2. 후보

| 출처 | 라이선스 | 강점 | 적합 |
|---|---|---|---|
| **Kenney** (kenney.nl) | CC0, 상업 사용 가능 | 2D/3D 폭넓음, 일관된 스타일, UI 아이콘 강함 | 2D, UI, 프로토타입 |
| **Quaternius** (quaternius.com) | CC0, 상업 사용·수정 가능 | Low-poly 3D MegaKit (Stylized Nature, Medieval Village, Fantasy Props 등) | 3D stylized low-poly |

MegaKit 계열은 **같은 제작자의 여러 팩이 서로 호환되는 스타일**이라 계열 유지가 쉽다.

> 라이선스는 **도입 시점에 반드시 원문을 재확인**한다. 이 표는 참고일 뿐이다.
> 상업 배포 시 크레딧 요구 여부, AI 생성물 표기 의무 등을 사용자가 확인해야 한다.

---

## 3. 도입 절차

```
1. 에이전트: 후보 팩 2~3개 제시 (URL + 라이선스 + 스타일 + VISUAL_SPEC 적합도)
        ↓
2. 사용자: 계열 선택               ← DECISION (필수)
        ↓
3. 사용자: 다운로드 및 Assets/Art/Experimental/ 에 배치   ← MANUAL (필수)
        ↓
4. 에이전트: 스케일 정규화 + 마스터 머티리얼 적용
        ↓
5. 에이전트: Golden Scene 에 넣고 스크린샷 검사
        ↓
6. 통과한 것만 Assets/Art/Approved/ 로 이동 + ASSET_CATALOG.json 등록
```

**에이전트는 다운로드하지 않는다.** URL 과 설치 경로를 안내하고 대기한다.

---

## 4. 도입 후 정규화 (필수)

외부 팩을 그대로 쓰지 않는다. 반드시 통과시킨다.

### 3D
```
[ ] 스케일 정규화 — VISUAL_SPEC.world_scale 기준으로 리스케일 (프리팹 단계에서)
[ ] 피벗 정규화 — 바닥 중심
[ ] 마스터 머티리얼 적용 — MAT_Master_Stylized 파생만
[ ] 원본 텍스처의 baked lighting 제거 또는 무시
[ ] 폴리곤 밀도가 스펙과 크게 다르면 제외
[ ] ASSET_CATALOG.json 등록 (worldHeight, allowedScale, materialFamily)
```

### 2D
```
[ ] PPU 통일 — VISUAL_SPEC.sprites.<category>.pixels_per_unit
[ ] pivot 통일
[ ] source_canvas / occupied_height_px 기준 재단
[ ] Point filter / mipmap off / compression 규칙 (pixel art 인 경우)
[ ] Sprite Atlas 편입
[ ] ASSET_CATALOG.json 등록
```

Unity 공식 `sprite-editor` / `2d-pixel-perfect` skill 이 이 정규화를 실제로 수행해준다.

---

## 5. 대안: 에셋을 받지 않고 만드는 길

무료 팩이 스펙에 안 맞으면 아래를 먼저 검토한다. 다운로드보다 통일성이 높다.

| 방법 | 적합 | 비고 |
|---|---|---|
| **ProBuilder 모듈러** | 건축물, 지형 구조물 | `VISUAL_SPEC.architecture` 제약을 파라미터로 |
| **절차적 Shader** | 재질 개성, 패턴 | 텍스처 대신 셰이더로 개성 — 이미지 없이 가능 |
| **기존 메시 리스킨** | 이미 있는 에셋 | 비용 0, 효과 큼 |
| **3D → 고정 정사영 렌더 → 2D 스프라이트** | 아이소메트릭 2D | strict isometric 을 AI 로 유지하기 어려움. 렌더가 확실 |

### 3D → 2D 프리렌더 (아이소메트릭 2D 프로젝트에 강력 추천)
```
3D Model
  ↓ Fixed Orthographic Camera   (단일 표준 render scene)
  ↓ Fixed Lighting
  ↓ Fixed Shader
Render
  ↓
2D Sprite
```
**모든 스프라이트를 하나의 표준 render scene 에서 동일 카메라/조명/포스트로 렌더**하면
다운샘플링 후에도 남는 lighting/material 차이를 크게 줄일 수 있다.
카메라/크기/투시 일관성은 거의 완벽하게 고정된다.

---

## 6. 절대 하지 않는 것

```
✗ 에이전트가 직접 다운로드
✗ 유료 에셋 구매
✗ 라이선스 미확인 에셋 사용
✗ 여러 제작자 팩 혼용
✗ 정규화 없이 씬에 투입
✗ ASSET_CATALOG.json 등록 없이 사용
```
