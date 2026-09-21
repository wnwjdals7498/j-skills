---
name: visual-director
description: Unity 프로젝트의 모든 비주얼 작업을 지휘하는 상위 오케스트레이션 스킬. 컨셉아트 반영, 화면 통일성 개선, 카메라/조명/머티리얼 기반 구축, 에셋 배치, UI 레이아웃, 스크린샷 기반 검수를 담당한다. Unity 공식 skills(unity-cli, sprite-editor, 2d-pixel-perfect, tilemap-*, ui-ugui, ui-uitk, urp-postprocessing, shader-graph-*, manage-sprite-atlas)를 하위 도구로 호출한다. "비주얼 개선", "컨셉대로 만들어", "화면이 이상해", "씬 배치", "머티리얼 통일", "UI 레이아웃" 같은 요청에서 트리거된다.
---

# visual-director

> 상위 오케스트레이터. Unity 공식 skills 는 **하위 도구**다. 순서를 뒤집지 않는다.
>
> ```
> Codex / Claude Code
>         │
>   visual-director          ← 이 스킬 (아트 디렉터 + 검수자)
>         │
>   ┌─────┴─────┐
> VisualSpec  AssetCatalog
>         │
>  Unity 공식 Skills         ← 손
>         │
>     Unity CLI              ← Unity 를 만지는 인터페이스
>         │
>   실제 Unity Editor
> ```

---

## 1. 절대 전제

이 스킬은 **이미지를 창작하지 않는다.** 코딩 에이전트는 그림/모델을 만들지 못한다.
그래서 이 스킬의 역할은 창작이 아니라 **아트 디렉션 규칙 강제 + 조립 + 검수**다.

```
창작 ✗
조립 ✓   승인 에셋 선택 → 조합 → 스케일 제한 → 머티리얼 통일 → 셰이더 통일 → 조명 통일
검수 ✓   Game View 스크린샷 → 컨셉 비교 → 상위 3개 수정 → 반복
```

---

## 2. 시작 시 반드시 하는 것

```
1. <PROJECT_ROOT>/Docs/PIPELINE_STATE.md 를 읽는다      ← 어디서부터인지 파악
2. <PROJECT_ROOT>/Docs/Visual/VISUAL_SPEC.yaml 을 읽는다  ← authoritative
3. <PROJECT_ROOT>/Docs/Visual/ASSET_CATALOG.json 을 읽는다
4. {KIT_ROOT}/references/pipeline/PIPELINE.md 로 현재 V 스테이지 확인
5. 해당 스테이지 문서 + 프로파일(PROFILE_3D | PROFILE_2D) 로드
```

`VISUAL_SPEC.yaml` 의 `approved: false` 이면 → **V1 부터 시작한다.** 구현하지 않는다.

---

## 3. 작업 절차

```
① 현재 Scene 상태 조사        unity command / MCP
② VISUAL_SPEC 과 대조
③ 기존 승인 에셋 우선 사용     ASSET_CATALOG.json 밖은 쓰지 않는다
④ 없으면 ProBuilder 절차적 생성 (VISUAL_SPEC 제약 하에서)
⑤ 그것도 안 되면 VISUAL_MISSING 처리 + 보고
⑥ 승인 머티리얼 패밀리만 적용
⑦ Game View 스크린샷 캡처     1920x1080 (또는 스펙 target_resolution)
⑧ VisualLinter 실행
⑨ 컨셉과 비교 채점 (9항목)
⑩ 상위 3개만 수정 → ⑦ 로 반복
⑪ VISUAL_DOD 충족 확인 후 보고
```

---

## 4. 금지 (ASSET_POLICY.md 요약)

```
✗ Cube / Sphere / Quad / Capsule / Cylinder / Plane 로 프로덕션 에셋 제작
✗ Unity default material (Lit / Default-Material / Sprite-Default) 사용
✗ 즉석 생성 PNG / 임의 단색 텍스처
✗ palette 밖의 색상
✗ ASSET_CATALOG.json 밖의 에셋
✗ 비균등 스케일
✗ Transform.scale 로 2D 스프라이트 크기 맞추기 (PPU/pivot 을 쓴다)
✗ 여러 제작자의 무료 팩 혼용
```

예외: `BLOCKOUT_` 접두사 + Blockout 루트 하위 + 태스크가 명시적으로 BLOCKOUT/PROTOTYPE 단계일 때만.

적합한 에셋이 없으면 **비슷하게 생긴 가짜를 만들지 않는다.**
`MISSING_` 접두사 + `MAT_Missing` 으로 표시하고 `ASSET_CATALOG.json` 의 `missing[]` 에 등록 후 보고한다.

---

## 5. 우선순위 (화면 점유 영향)

작은 prop 이나 버튼을 먼저 만지는 것은 거의 항상 낭비다.

```
Camera            30%
Lighting          25%
Environment mass  20%
Palette           15%
Small props        5%
etc.               5%
```

**Always prioritize changes by visible screen-space impact.**

---

## 6. 완료 조건

`{KIT_ROOT}/references/policy/VISUAL_DOD.md`. 요약:

```
컴파일 성공은 완료가 아니다.

1. 씬을 연다
2. Game View 스크린샷 캡처 (파일로 저장)
3. VisualLinter 실행 → error 0
4. 스크린샷 육안 검사
5. 위반 수정
6. 최종 스크린샷
7. 보고 (스크린샷 경로 + 린터 결과 + 스코어카드 + 남은 MISSING)
```

**"찍었다고 말하기" 는 증거가 아니다. 파일이 존재해야 한다.**

---

## 7. 멈추고 물어야 할 때

`{KIT_ROOT}/references/policy/ESCALATION.md`. V 트랙에서 반드시 묻는 것:

```
아트 디렉션 최종값 (VISUAL_SPEC 승인)
3D / 2D 프로파일
GREENFIELD / REBASE 모드
에셋 조달 전략, 무료 팩 계열 선택
UNDEFINED 영역(야간/실내/인벤토리 등) 처리 방침
DELETE 판정
Golden Scene 합격 여부
새 원본 아트가 필요한 항목
```

질문은 **선택지 2~4개 + 추천 + 각 선택지의 결과/되돌리기 난이도**를 표로 제시한다.
막연한 질문을 하지 않는다.

반대로 아래는 **묻지 말고 그냥 한다**: 폴더 생성, 린터 실행, 스크린샷 촬영,
파일 이름, 다음 스테이지 진입(게이트 통과 시), 코드 스타일.

---

## 8. 하위 도구 (Unity 공식 skills)

| skill | 이 스킬이 시키는 일 |
|---|---|
| `unity-cli` | Editor 조작, Scene/GameObject 조사, C# 실행, 스크린샷 |
| `sprite-editor` | rect / pivot / border / slice 정규화 |
| `2d-pixel-perfect` | PPU / 필터링 / 카메라 / 픽셀 정렬 |
| `manage-sprite-atlas` | Atlas packing |
| `tilemap-*` | Tile 배치 / Palette / RuleTile |
| `ui-ugui` / `ui-uitk` | RectTransform / UXML / USS 구조 |
| `urp-postprocessing` | Volume / Tonemapping / ColorAdjustments / Bloom |
| `shader-graph-*` | 마스터 셰이더 제작·수정 |

이 skills 는 **미술 능력을 추가하지 않는다.** Unity 를 정확히 만지게 해줄 뿐이다.
아트 디렉션은 `VISUAL_SPEC.yaml` 과 이 스킬의 검수 루프가 담당한다.

---

## 9. 코드가 함께 걸리면

UI 코드, 카메라 스크립트, 셰이더 파라미터 제어 등은 C 트랙도 함께 돈다.
`unity-task-runner` 스킬과 병행하고, **`CODE_DOD` 와 `VISUAL_DOD` 를 둘 다 충족**해야 한다.
