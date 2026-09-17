# V7 — FULL MIGRATION (전수 확대)

> LOAD WHEN: V5(greenfield) 또는 V6(rebase) = PASS. Golden Scene 스타일을 나머지 씬에 복제할 때.

---

## ENTRY GATE
- greenfield: V5 = `PASS`
- rebase: V6 = `PASS`
- Golden Scene 사용자 합격 승인 존재

## INPUTS
- 합격한 Golden Scene
- 나머지 씬 목록
- `Docs/Visual/Reference/GoldenViews/` (있으면)

---

## STEPS

### 7-A. 씬 우선순위 결정

**전부 동시에 하지 않는다.** 화면 노출 빈도 순으로 정렬한다.

```
1. 플레이어가 가장 오래 보는 씬
2. 첫 인상 씬 (타이틀, 튜토리얼)
3. 전투 씬
4. UI 화면 (인벤토리, 다이얼로그)
5. 나머지
```

### 7-B. 씬당 절차 (반복)

```
1. 해당 씬을 VisualRebuild 기반으로 옮기거나, 기반 요소를 주입
   - CameraRig / LightingRig / VP_Global / 마스터 머티리얼
2. 카탈로그 에셋으로 교체 (V5 매트릭스 적용)
3. GoldenView 가 있으면 스크린샷 루프 (SCREENSHOT_LOOP.md)
   없으면 Golden Scene 을 기준으로 톤 비교
4. VisualLinter 실행
5. VISUAL_DOD 절차
6. 통과 → 다음 씬
```

### 7-C. GoldenView 확장

컨셉이 World_Main 하나뿐이었다면, 새 화면마다 아래를 판단한다.
```
REFERENCE_DEFINED   → 그대로 적용
REFERENCE_INFERRED  → Golden Scene 규칙에서 유추, inferred 표기
UNDEFINED           → 사용자 결정 (DECISION)
```
**상상으로 채우지 않는다.**

### 7-D. 전역 검증

전 씬 완료 후 일괄 실행:
```
[ ] 모든 씬 VisualLinter error 0
[ ] 모든 씬이 동일한 VP_Global 사용
[ ] 카탈로그 외 에셋 0
[ ] MISSING_ 오브젝트 목록 최종 보고
[ ] 씬 간 톤 일관성 (씬별 대표 스크린샷을 한 장에 모아 비교)
```

씬별 대표 스크린샷을 **한 시트로 붙여서** 확인한다 — 개별로 보면 튀는 것을 못 잡는다.

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| 새 씬에 `UNDEFINED` 영역 등장 | DECISION | 처리 방침 질문 |
| 씬 간 톤이 갈림 | CONFLICT | 원인 + 통일안 제시 |
| 씬 수가 많아 범위 조정 필요 | DECISION | 우선순위 확인 |
| 기존 씬 대량 수정 | RISK | 백업/브랜치 확인 후 승인 |
| 특정 씬에 새 원본 아트 필수 | MANUAL | 목록화 후 요청 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 대상 씬 전부 VisualLinter error 0 |
| 2 | 대상 씬 전부 스코어카드 ≥4 |
| 3 | 전 씬 동일 `VP_Global` |
| 4 | 카탈로그 외 에셋 0 |
| 5 | 씬 대표 스크린샷 시트에서 튀는 씬 없음 |
| 6 | 남은 `MISSING_` 목록이 사용자에게 보고됨 |

## OUTPUTS
- 전 씬 마이그레이션 완료
- `Assets/VisualTests/Screenshots/sheet_all_scenes.png`
- 최종 보고서

## STATE UPDATE
```yaml
stage: V7
status: PASS | PARTIAL
scenes_migrated: [...]
scenes_remaining: [...]
missing_final: [...]
```
