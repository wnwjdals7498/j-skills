# V4 — GOLDEN SCENE (컨셉 vs 렌더 수렴 루프)

> LOAD WHEN: V3 = PASS. 이 스테이지가 **파이프라인 전체에서 가장 중요하다.**

개별 PNG 를 보고 "괜찮다" 고 판단하면 거의 반드시 실패한다.
**캐릭터 + 건물 + 나무 + 바닥 + UI + 이펙트를 한 화면에 동시에 놓고** 튀는 것을 찾는다.

---

## ENTRY GATE
- V3 = `PASS`
- ConceptOverlay + GameViewCapture + VisualLinter 전부 동작

## INPUTS
- `Concept_Master.png` (또는 해당 GoldenView)
- `VisualRebuild.unity`

---

## STEPS

### 4-A. Golden Scene 구성

한 화면에 **모든 요소 카테고리**를 배치한다. 하나라도 빠지면 검사가 무의미하다.

```
[ ] 캐릭터 (플레이어)
[ ] 적 / NPC
[ ] 건물
[ ] 자연물 (나무/바위)
[ ] 바닥 / 지형
[ ] 아이템 / prop
[ ] UI (HUD 1개 이상)
[ ] VFX (있으면)
```

이 시점에는 아직 Blockout + 마스터 머티리얼 조합이어도 된다.

### 4-B. 수렴 루프

`references/guides/SCREENSHOT_LOOP.md` 의 프로토콜을 **그대로** 실행한다.

```
캡처 (1920x1080)
  ↓
REFERENCE 와 CURRENT 를 함께 놓고 9항목 채점 (0-5)
  ↓
<4 인 항목마다 최대 3개 불일치 식별
  ↓
각 불일치를 Unity 오브젝트/컴포넌트/머티리얼에 매핑
  ↓
화면 점유 영향 순으로 정렬
  ↓
상위 3개만 수정
  ↓
다시 캡처 → 반복
```

**한 번에 전부 고치지 않는다.** 변수가 많으면 무엇 때문에 좋아졌는지 알 수 없다.

루프 순서 권장:
```
Iteration 07  Palette
Iteration 08  Material language
Iteration 09  Detail density
Iteration 10  Focal hierarchy
Iteration 11  UI
Iteration 12  Final color grading
```

### 4-C. 정량 보조

육안 채점만 믿지 않는다. 매 루프마다 스크립트로 뽑는다:
```
현재 렌더의 dominant colors  vs  CONCEPT_ANALYSIS.measured.dominant_colors
평균 밝기 / 채도 차이
주요 오브젝트 화면 점유율 차이
```
`Tools/render_compare.py` 로 남긴다.

### 4-D. 합격 판정

**최종 합격은 사용자가 한다.** 에이전트는 증거를 모아 제시한다.

```markdown
## Golden Scene 합격 요청

**컨셉:** Docs/Visual/Reference/Concept_Master.png
**렌더:** Assets/VisualTests/Screenshots/iter_12_grading.png
**오버레이 50%:** Assets/VisualTests/Screenshots/iter_12_overlay.png

### 스코어카드
| 항목 | 점수 |
|---|---|
| Camera / Composition / Silhouette / Scale / Palette / Lighting / Material / Detail / Focal | ... |

### 정량 비교
| 지표 | 컨셉 | 현재 | 차이 |
|---|---|---|---|

### 남은 VISUAL_MISSING
- ...

**합격 처리해도 되나?**
1. 합격 → V5 진행
2. 특정 항목 재작업 → 어느 항목인지 지정
3. VISUAL_SPEC 자체를 수정 → V1 로 롤백
```

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| **합격 판정** | DECISION | **필수. 에이전트 단독 통과 불가** |
| 6회 루프에도 특정 항목 <4 | CONFLICT | 접근이 틀렸을 가능성. 원인 후보 + 선택지 제시 |
| 개선에 새 원본 아트가 반드시 필요 | MANUAL | 무엇이 왜 필요한지 명시 후 요청 |
| 스펙과 컨셉이 모순됨을 발견 | CONFLICT | 어느 쪽이 진실인지 질문 |
| Editor 실행 불가 | MANUAL | 실행 요청 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 스코어카드 **9항목 전부 ≥4** |
| 2 | VisualLinter error 0 |
| 3 | Golden Scene 에 8개 요소 카테고리 전부 존재 |
| 4 | 각 iteration 스크린샷 존재 |
| 5 | **사용자 합격 승인** 기록 (`PIPELINE_STATE.decisions`) |

## OUTPUTS
- `Assets/VisualTests/Screenshots/iter_07..12_*.png`
- `Tools/render_compare.py`
- 합격 승인 기록

## STATE UPDATE
```yaml
stage: V4
status: PASS | BLOCKED
golden_scene_approved_at: <iso8601>
scorecard: {camera:5, composition:4, silhouette:4, scale:5, palette:4, lighting:5, material:4, detail:4, focal:4}
```
