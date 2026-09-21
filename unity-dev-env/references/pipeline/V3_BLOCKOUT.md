# V3 — BLOCKOUT (형태와 실루엣)

> LOAD WHEN: V2 = PASS 이고 큰 형태가 아직 컨셉과 맞지 않을 때.

**아직 텍스처를 만들지 않는다.** 큰 덩어리와 실루엣만 맞춘다.

---

## ENTRY GATE
- V2 = `PASS`
- ConceptOverlay 동작

## INPUTS
- `VISUAL_SPEC.yaml`, `CONCEPT_ANALYSIS.yaml`
- `VisualRebuild.unity`

---

## STEPS

### 3-A. 프리미티브 사용 규칙 (이 스테이지 한정)

`ASSET_POLICY.md` §3 예외가 여기서 발동한다.

```
Blockout 프리미티브는 아래 조건 전부 만족 시에만 허용:

1. 오브젝트가 Assets/VisualRebuild/Blockout/ 또는 씬의 "Blockout" 루트 아래
2. 이름에 BLOCKOUT_ 접두사
3. 머티리얼은 MAT_Blockout_Grey 단일 (컬러로 속이지 않는다)
4. Production Visual 합격 판정을 절대 통과할 수 없음
```

**이것은 캘리브레이션 도구이지 결과물이 아니다.**

### 3-B. 매스(mass) 순서

컨셉 오버레이를 켜고 아래 순서로 덩어리를 잡는다.

```
1. 지형 / 바닥 레벨
2. 주요 건축 매스 (건물 높이, 지붕 각도)
3. 큰 자연물 (절벽, 큰 바위, 나무 크기)
4. 도로/동선 폭
5. 캐릭터 프록시 위치
6. 주요 실루엣 라인
```

### 3-C. ProBuilder 활용

세부 형태가 필요하면 프리미티브 대신 ProBuilder 로 만든다.
`VISUAL_SPEC.architecture` 규칙을 파라미터로 준다.

```
Build a cottage using VISUAL_SPEC architecture rules.

Allowed primitives: ProBuilder cube / prism / stair / approved roof modules
Constraints:
  footprint: 6m x 8m
  floor_height: 2.8m
  wall_thickness: 0.2m
  door: 1.1 x 2.2m
  window: 0.9 x 1.1m
  roof_pitch: 42deg
  materials: MAT_Architecture_Wall_A, MAT_Architecture_Wood_A, MAT_Architecture_Roof_A only
  all camera-visible edges require bevel
```

**"집을 모델링해" 가 아니라 위처럼 제약을 준다.** 그러면 기본 사각형 느낌에서 꽤 멀리 간다.

### 3-D. 반복 루프

`references/guides/SCREENSHOT_LOOP.md` 프로토콜을 따른다. 루프당 **상위 3개 변경만.**

```
Iteration 03  Terrain / ground mass
Iteration 04  Architecture mass
Iteration 05  Nature mass
Iteration 06  Silhouette / negative space
```

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| ProBuilder 미설치 | DECISION | 설치 승인 요청 |
| 컨셉에 없는 영역의 형태가 필요 | DECISION | `UNDEFINED` 처리 방침 확인 |
| 5회 루프에도 실루엣 스코어 <4 | CONFLICT | 카메라(V2)가 틀렸을 가능성 — V2 재검토 제안 |
| 기존 지형/씬을 파괴해야 진행 가능 | RISK | 승인 요청. 새 씬에서 작업 중이면 해당 없음 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 컨셉 오버레이 50% 에서 주요 실루엣이 겹침 |
| 2 | 스코어카드 Camera / Scale / Composition / Silhouette **전부 ≥4** |
| 3 | 모든 프리미티브가 `BLOCKOUT_` 접두사 + Blockout 루트 하위 |
| 4 | VisualLinter error 0 (Blockout 예외 규칙 적용) |
| 5 | 각 iteration 스크린샷이 파일로 존재 |

## OUTPUTS
- `Assets/VisualRebuild/Blockout/` 하위 지오메트리
- `Assets/VisualTests/Screenshots/iter_03..06_*.png`

## STATE UPDATE
```yaml
stage: V3
status: PASS | BLOCKED
iterations: 4
scorecard: {camera: 5, scale: 4, composition: 4, silhouette: 4}
```
