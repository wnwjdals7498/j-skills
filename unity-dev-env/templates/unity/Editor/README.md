# Assets/Editor/AIVisual — 에이전트 시각 검수 도구

> 대상 경로: `<PROJECT_ROOT>/Assets/Editor/AIVisual/`
> Editor 전용. 런타임 빌드에 포함되지 않는다.

| 파일 | 역할 |
|---|---|
| `GameViewCapture.cs` | Game View 를 고정 해상도로 캡처. **VISUAL_DOD 가 요구하는 증거를 만든다** |
| `ConceptOverlay.cs` | 컨셉아트를 Scene View 위에 0/25/50/75/100% 로 겹쳐 본다 |
| `VisualLinter.cs` | VISUAL_SPEC + ASSET_CATALOG 대비 정량 검사 |
| `AIVisual.Editor.asmdef` | Editor 전용 어셈블리 경계 |

---

## 호출 방법

세 도구 모두 **메뉴 / CLI / 코드** 3경로를 지원한다.

### 메뉴
```
Tools/AI Visual/Capture Game View
Tools/AI Visual/Concept Overlay
Tools/AI Visual/Run Visual Linter
```

### CLI (batchmode / -executeMethod)
```
-executeMethod AIVisual.Editor.GameViewCapture.CaptureFromCommandLine
    -captureWidth 1920 -captureHeight 1080
    -capturePath Assets/VisualTests/Screenshots/iter_07_palette.png

-executeMethod AIVisual.Editor.VisualLinter.RunFromCommandLine
```

`VisualLinter.RunFromCommandLine` 은 **error 가 있으면 exit code 1** 로 종료한다.
파이프라인 게이트에서 그대로 쓸 수 있다.

정확한 batchmode 문법은 실행 시점에 확인한다. `unity command --project-path ... --format json`
으로 Pipeline catalog 에 대응 command 가 있는지 먼저 본다.

---

## VisualLinter 전제

Unity 에는 YAML 파서가 없다. 그래서 린터는 **JSON 을 읽는다.**

```
Docs/Visual/VISUAL_SPEC.yaml     ← authoritative (사람이 읽고 승인)
Docs/Visual/VISUAL_SPEC.json     ← 린터가 읽음. YAML 변경 시 재생성
Docs/Visual/ASSET_CATALOG.json   ← path 필드만 추출해 사용
```

에이전트가 YAML 을 수정하면 **JSON 도 함께 갱신**해야 한다.

린터 결과:
```
Assets/VisualTests/lint_result.json
```
콘솔과 파일 양쪽에 나온다. 에이전트는 파일을 파싱하고, 증거로 남긴다.

---

## 규칙 추가

`references/guides/VISUAL_LINTER_SPEC.md` §7 절차를 따른다.

```
1. 규칙 ID 를 정한다 ({영역}.{항목})
2. VISUAL_LINTER_SPEC.md 표에 추가
3. 해당 프로파일 문서(PROFILE_3D/2D)의 린터 규칙 표에 추가
4. VisualLinter.cs 에 구현
5. 예외가 필요하면 VISUAL_SPEC 의 linter: 섹션에 필드 추가
```

**린터 규칙을 추가하는 것이 문서에 규칙을 적는 것보다 강력하다.**
문서는 에이전트가 잊을 수 있지만 린터는 잊지 않는다.

---

## 미구현 규칙

현재 `VisualLinter.cs` 는 씬 레벨(camera/light/volume)과 3D 오브젝트 규칙,
2D 의 `sprite.transform_scale` 을 구현한다. 아래는 프로젝트 필요에 따라 추가한다.

```
sprite.ppu / sprite.pivot / sprite.world_height / sprite.filter_mode / sprite.mipmap
sprite.not_in_atlas / camera.pixel_perfect
transform.catalog_scale (ASSET_CATALOG 의 allowedScale)
ui.spacing / ui.font_size (디자인 토큰)
geometry.tiny_feature
```

`VISUAL_LINTER_SPEC.md` 의 표가 목표 상태이고, 이 파일이 현재 상태다.
