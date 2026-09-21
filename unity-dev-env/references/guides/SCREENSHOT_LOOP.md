# SCREENSHOT_LOOP — 컨셉 vs 렌더 수렴 프로토콜

> LOAD WHEN: V3 / V4 / V7 에서 렌더 결과를 컨셉과 비교할 때.
>
> 이 루프가 이 키트의 **실제 개선 엔진**이다. 나머지 문서는 이 루프가 헛돌지 않게 하는 장치다.

---

## 1. 왜 필요한가

현재 에이전트의 기본 동작:
```
코드 수정 → 컴파일 성공 → "완료"
```

비주얼 작업에서 이건 완료가 아니다. 바꿔야 할 동작:
```
수정 → Unity Game View → 1920x1080 스크린샷 → 에이전트가 직접 검사
     → 컨셉과 비교 → 수정 → 다시 스크린샷
```

Unity CLI 의 진짜 가치는 자동화 도구가 아니라 **에이전트의 눈과 Unity 사이의 피드백 인터페이스**라는 점이다.

---

## 2. 루프 1회 절차

```
① 캡처
   unity command --project-path "<PROJECT_ROOT>" ...  (catalog 에서 실제 command 이름 확인)
   또는 Assets/Editor/AIVisual/GameViewCapture.cs 메뉴/CLI 호출
   해상도: 1920x1080 (VISUAL_SPEC.target_resolution 이 있으면 그것)
   저장: Assets/VisualTests/Screenshots/iter_{nn}_{category}.png
        ↓
② 채점 — REFERENCE 와 CURRENT 를 함께 놓고 9항목 0~5점
        ↓
③ <4 인 항목마다 가장 큰 불일치 최대 3개 식별
        ↓
④ 각 불일치를 구체적 Unity 대상에 매핑
   (GameObject 이름 / Component / Material / Volume 파라미터)
        ↓
⑤ 화면 점유 영향(screen-space impact) 순으로 정렬
        ↓
⑥ 상위 3개만 수정          ← 3개 초과 금지
        ↓
⑦ ① 로 복귀
```

---

## 3. 채점 프롬프트 (그대로 사용)

```
Compare REFERENCE and CURRENT.

Do NOT propose new content yet.

Score CURRENT 0-5 for:
1. Camera
2. Composition
3. Silhouette
4. Scale
5. Palette
6. Lighting
7. Material language
8. Detail density
9. Focal hierarchy

For every category below 4:
- identify the three largest discrepancies
- map each discrepancy to Unity objects/components/materials
- propose measurable changes
- prioritize changes with highest screen-space impact

Then implement only the highest-priority 3 changes.
Capture another Game View screenshot and repeat.
```

**"컨셉처럼 만들어" 라고 하지 않는다.** 위 형식과의 차이가 결과를 크게 가른다.

---

## 4. 9항목 채점 기준

| 항목 | 0-1 | 2-3 | 4-5 |
|---|---|---|---|
| **Camera** | 투영/각도가 다른 게임 | 방향은 맞으나 수치 어긋남 | 오버레이 시 지평선·투시 일치 |
| **Composition** | 초점이 없음 | 요소는 맞으나 배치 어긋남 | 전경/중경/배경 비율 일치 |
| **Silhouette** | 형태가 다름 | 큰 덩어리만 유사 | 외곽선이 겹침 |
| **Scale** | 비례가 붕괴 | 일부 요소만 맞음 | player:door:building 비율 일치 |
| **Palette** | 색이 다름 | 계열은 맞으나 채도/명도 어긋남 | dominant colors 차이 ΔE 작음 |
| **Lighting** | 방향/색온도 다름 | 방향만 맞음 | 그림자 방향·농도·난한색 관계 일치 |
| **Material** | PBR/스타일 혼재 | 일부만 통일 | 전 오브젝트가 동일 재질 언어 |
| **Detail density** | 배경이 캐릭터보다 복잡 | 부분적 역전 | 캐릭터>상호작용>환경>배경 |
| **Focal hierarchy** | 시선이 흩어짐 | 초점이 약함 | 의도한 곳으로 시선이 감 |

---

## 5. 화면 점유 영향 우선순위

에이전트가 흔히 하는 실수: 작은 나무·버튼·prop 을 열심히 고친다.
하지만 화면이 별로인 이유는 대개:

```
Camera            30%
Lighting          25%
Environment mass  20%
Palette           15%
Small props        5%
etc.               5%
```

**규칙: `Always prioritize changes by visible screen-space impact.`**

수정 대상 정렬 시 아래 순서를 기본 가중치로 쓴다.
```
카메라/투영 > 조명/Volume > 큰 매스/지형 > 팔레트/머티리얼 > 중형 prop > UI > 소형 prop > VFX 디테일
```

---

## 6. 루프 카테고리 순서 (권장)

한 루프 = 한 카테고리. 변수를 동시에 여러 개 바꾸지 않는다.

| Iter | 카테고리 | 스테이지 |
|---|---|---|
| 01 | Camera | V2 |
| 02 | Lighting | V2 |
| 03 | Terrain / ground mass | V3 |
| 04 | Architecture mass | V3 |
| 05 | Nature mass | V3 |
| 06 | Silhouette / negative space | V3 |
| 07 | Palette | V4 |
| 08 | Material language | V4 |
| 09 | Detail density | V4 |
| 10 | Focal hierarchy | V4 |
| 11 | UI | V4 |
| 12 | Final color grading | V4 |

---

## 7. 정량 보조 (에이전트의 눈을 계측기로 믿지 않는다)

매 루프마다 스크립트로 뽑아 비교한다. 별도 AI 비용 없음.

```
dominant colors (k-means)        컨셉 vs 현재
평균 밝기 / 채도 히스토그램       컨셉 vs 현재
그림자 영역 평균 색상             컨셉 vs 현재
주요 오브젝트 화면 점유율 (%)     컨셉 vs 현재
지평선 y 좌표                     컨셉 vs 현재
```

`Tools/render_compare.py` 로 재실행 가능하게 남긴다.

**Semantic(에이전트가 잘하는 것)과 Deterministic(스크립트로 재는 것)을 섞지 않는다.**

| Semantic (에이전트) | Deterministic (스크립트) |
|---|---|
| 분위기 / focal point | 해상도 / 픽셀 좌표 |
| 형태 언어 | dominant colors |
| 정보 밀도 | UI margin |
| 계층 구조 | 객체 상대 크기 / 화면 점유율 |
| 무엇이 튀는가 | bounding box / 종횡비 |

---

## 8. 오버레이 활용

`ConceptOverlay` 로 opacity 를 바꿔가며 본다.

| Opacity | 무엇을 보나 |
|---|---|
| 0% | 현재 렌더 그대로 |
| 25% | 팔레트/톤 차이 |
| 50% | **실루엣/구도 정렬** (가장 유용) |
| 75% | 세부 위치 |
| 100% | 컨셉 원본 |

50% 오버레이 스크린샷은 매 iteration 마다 함께 저장한다.

---

## 9. 중단 조건

| 조건 | 행동 |
|---|---|
| 같은 카테고리 5~6회 루프에도 <4 | 접근이 틀렸을 가능성. 상위 스테이지(카메라/스펙) 재검토 제안 |
| 점수가 오히려 하락 | 직전 3개 변경을 되돌리고 원인 분석 |
| 개선에 새 원본 아트가 필수 | MANUAL 로 승격, 사용자에게 요청 |
| 스펙과 컨셉이 모순 | CONFLICT 로 승격, 질문 |

---

## 10. 산출물 규칙

```
Assets/VisualTests/Screenshots/
├─ concept_master.png              (읽기 전용 사본)
├─ iter_01_camera.png
├─ iter_01_camera_overlay50.png
├─ iter_02_lighting.png
├─ ...
├─ final_{scene}_{yyyymmdd_hhmm}.png
└─ sheet_all_scenes.png            (V7)
```

**"스크린샷을 찍었다" 는 말은 증거가 아니다. 파일이 실제로 존재해야 한다.**
