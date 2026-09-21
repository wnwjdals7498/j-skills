# ASSET_POLICY — 무엇을 화면에 올려도 되는가

> LOAD WHEN: 씬에 **보이는** 오브젝트를 생성/배치/머티리얼 지정하기 직전. V2~V7 상시.
>
> 이 정책이 존재하는 이유: 코딩 에이전트는 이미지/모델을 창작하지 못한다.
> 그래서 방치하면 가장 쉬운 방법 — Cube, Plane, 기본 머티리얼, 임의 색 PNG — 을 골라놓고
> "요구 기능을 구현했다" 고 보고한다. 이것을 **명시적으로 금지**해야 한다.

---

## 1. 금지 (VISIBLE PRODUCTION ASSET)

아래 출처로 **최종 화면에 보이는 프로덕션 에셋을 만들지 않는다.**

```
Cube / Sphere / Quad / Capsule / Cylinder / Plane  (Unity 기본 프리미티브)
Unity default material (Lit / Default-Material / Sprite-Default 그대로)
프로그램으로 즉석 생성한 임시 PNG
임의 단색 텍스처
임의로 고른 색상
Asset Store 에서 계열이 다른 팩을 섞은 조합
```

**예외:** 태스크가 명시적으로 `PROTOTYPE` 또는 `BLOCKOUT` 으로 선언된 경우에만 허용. (§3)

---

## 2. 허용 (이 순서로 시도)

보이는 오브젝트는 **아래 중 하나에서만** 나와야 한다.

| 우선 | 출처 | 조건 |
|---|---|---|
| 1 | `ASSET_CATALOG.json` 에 등록된 승인 에셋 | 카탈로그의 `allowedScale` 범위 준수 |
| 2 | 승인된 외부 CC0 에셋 팩 | **단일 계열만.** 팩 도입은 사용자 승인 필요 (`ESCALATION` DECISION) |
| 3 | 승인된 메시들의 모듈러 조합 | 스케일/머티리얼 규칙 준수 |
| 4 | ProBuilder 지오메트리 | `VISUAL_SPEC` 의 architecture 규칙에 부합해야 함 |
| 5 | 절차적 Shader/Material | `VISUAL_SPEC` 의 material 규칙에 부합해야 함 |

**적합한 에셋이 없으면 → 비슷하게 생긴 가짜 플레이스홀더를 만들지 않는다.**

대신:
1. 오브젝트를 `VISUAL_MISSING` 으로 표시한다 (태그 또는 이름 접두사 `MISSING_`).
2. 프로젝트 표준 플레이스홀더 머티리얼(`MAT_Missing`, 마젠타 계열)을 적용한다.
3. `ASSET_CATALOG.json` 의 `missing[]` 배열에 항목을 추가한다.
4. 보고서에 누락 에셋 목록을 낸다.

> 가짜 플레이스홀더가 **최종 결과물처럼 보이는 것**이 가장 위험하다.
> 눈에 띄게 틀린 것이 그럴듯하게 틀린 것보다 낫다.

---

## 3. PROTOTYPE / BLOCKOUT 예외

프리미티브는 아래 조건 **전부** 만족 시에만 허용된다.

1. 태스크가 명시적으로 `PROTOTYPE` 또는 `BLOCKOUT` 단계로 선언되어 있다.
2. 오브젝트가 `Assets/VisualRebuild/Blockout/` 하위 또는 `Blockout` 루트 아래에 있다.
3. 오브젝트 이름에 `BLOCKOUT_` 접두사가 붙어 있다.
4. **Production Visual 합격 판정(`VISUAL_DOD.md`)을 절대 통과할 수 없다.**

즉 블록아웃 프리미티브는 **캘리브레이션 도구**이지 결과물이 아니다.

---

## 4. 머티리얼 정책

- 모든 보이는 오브젝트는 **마스터 머티리얼 패밀리**에서 파생되어야 한다.
- 머티리얼 패밀리는 `VISUAL_SPEC.yaml` 의 `materials.families` 에 정의된 것만 사용.
- 새 머티리얼은 마스터 셰이더의 **인스턴스/베리언트**로 만든다. 새 셰이더를 임의로 만들지 않는다.
- 색상은 `VISUAL_SPEC.yaml` 의 `palette` 에 정의된 값만 사용. 임의 색 금지.
- 금지 색: 순백(`#FFFFFF`), 순흑(`#000000`), 네온 채도 (스펙에서 명시 허용하지 않는 한).

```
MAT_Master_Stylized
 ├─ MAT_Nature_*
 ├─ MAT_Architecture_*
 ├─ MAT_Character_*
 ├─ MAT_Metal_*
 ├─ MAT_Cloth_*
 └─ MAT_FX_*
```

**서로 다른 출처의 무료 모델을 섞더라도, 전부 이 마스터 셰이더를 통과시키면 상당 부분 통일된다.**
이것이 이미지 생성 AI 없이 스타일을 통일하는 핵심 수단이다.

---

## 5. 스케일 정책

- 모든 배치는 `VISUAL_SPEC.yaml` 의 `world_scale` 을 기준으로 한다.
- 카탈로그 에셋은 `allowedScale` 범위를 벗어나 스케일하지 않는다.
- 비균등 스케일(`x != y != z`)은 금지. 필요하면 메시 자체를 교체하거나 ProBuilder 로 다시 만든다.
- 2D 스프라이트는 PPU/pivot 으로 크기를 맞춘다. Transform 스케일로 우겨넣지 않는다.

---

## 6. 외부 에셋 도입 규칙

- **한 계열만 쓴다.** 여러 제작자의 팩을 섞으면 통일성이 무너진다.
- 라이선스는 CC0 또는 상업적 사용이 명시 허용된 것만. (`references/guides/FREE_ASSETS.md`)
- 도입 전 사용자 승인 필요 (`ESCALATION.md` DECISION + 다운로드는 MANUAL).
- 도입 후 반드시 `ASSET_CATALOG.json` 에 등록한다. 카탈로그에 없는 에셋은 사용 불가.

---

## 7. 에이전트 자기점검 체크리스트

씬에 오브젝트를 추가하기 직전 스스로 답한다.

```
[ ] 이 오브젝트의 메시/스프라이트 출처가 ASSET_CATALOG.json 에 있는가?
[ ] 없다면 ProBuilder/절차적 생성이 VISUAL_SPEC 규칙에 부합하는가?
[ ] 그것도 아니면 나는 지금 VISUAL_MISSING 을 만들어야 하는 것 아닌가?
[ ] 머티리얼이 마스터 패밀리에서 왔는가?
[ ] 색상이 palette 에 있는가?
[ ] 스케일이 world_scale / allowedScale 범위 안인가?
[ ] 지금이 BLOCKOUT 단계가 아닌데 프리미티브를 쓰고 있지는 않은가?
```

하나라도 아니오 → 만들지 말고 `VISUAL_MISSING` 처리 후 보고.
