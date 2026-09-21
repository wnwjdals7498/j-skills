# V5 — ASSET STRATEGY (블록아웃 → 실제 에셋)

> LOAD WHEN: V4 = PASS. 블록아웃을 실제 에셋으로 대체할 계획이 필요할 때.

---

## ENTRY GATE
- V4 = `PASS` (사용자 합격 승인 포함)

## INPUTS
- Golden Scene 의 블록아웃 목록
- `VISUAL_SPEC.yaml`
- 기존 프로젝트 에셋 (REBASE 모드)

---

## STEPS

### 5-A. 전수 조사

씬의 모든 시각 요소를 나열하고 아래 표를 채운다.

| 요소 | 지오메트리 품질 | 게임플레이 의존 | 판정 |
|---|---|---|---|
| Tree_A | 쓸 만함 | 없음 | RE-SKIN |
| House_01 | 부적합 | Door trigger 있음 | REBUILD (visual만) |
| NPC_Blacksmith | 쓸 만함 | AI 포함 | RE-SKIN |
| Rock_02 | 부적합 | 없음 | REPLACE |
| ShopPanel | 부적합 | Shop logic 포함 | RE-SKIN (UI) |

판정 5종:
```
KEEP     그대로 둔다
RE-SKIN  메시 유지, 머티리얼/셰이더만 교체
REBUILD  비주얼만 새로 만들고 게임플레이 컴포넌트는 이관
REPLACE  다른 에셋으로 교체
DELETE   제거  ← 사용자 승인 필수
```

### 5-B. 조달 경로 결정 (요소별)

`ASSET_POLICY.md` §2 의 우선순위대로 시도한다.

```
1. 기존 프로젝트 에셋 재활용        비용 0, 통일성은 마스터 셰이더가 담당
2. 무료 CC0 팩 (단일 계열)          references/guides/FREE_ASSETS.md
3. 승인 메시의 모듈러 조합           에이전트가 잘하는 영역
4. ProBuilder 절차적 생성            VISUAL_SPEC 제약 하에서
5. 절차적 Shader/Material            텍스처 대신 셰이더로 개성
─────────────────────────────────
6. 새 원본 아트 필요                 → VISUAL_MISSING + 사용자에게 보고
```

> **모델을 생성하지 않는다. 조립한다.** 레고 방식. 이것이 코딩 에이전트가 잘하는 영역이다.

### 5-C. 무료 팩 도입 (해당 시)

- **한 계열만 쓴다.** 여러 제작자를 섞으면 통일성이 무너진다.
- 라이선스 확인 (CC0 또는 상업적 사용 명시 허용).
- 다운로드는 **사용자 승인 + 사용자 실행** (MANUAL).
- 도입 후 반드시 `ASSET_CATALOG.json` 등록.

### 5-D. ASSET_CATALOG.json 작성

에이전트가 프로젝트 전체를 자유 검색하게 두지 않는다. **카탈로그에 있는 것만 쓴다.**

```
Assets/Art/
├─ Approved/        ← 카탈로그 등록된 것만
│  ├─ Characters/
│  ├─ Buildings/
│  ├─ Props/
│  ├─ Nature/
│  └─ UI/
├─ Experimental/    ← 아직 승인 안 됨. 씬에 못 들어감
└─ Missing/         ← VISUAL_MISSING 플레이스홀더
```

```json
{
  "tree_oak_01": {
    "path": "Assets/Art/Approved/Nature/tree_oak_01.fbx",
    "type": "tree",
    "style": "stylized_lowpoly",
    "worldHeight": 4.3,
    "allowedScale": [0.85, 1.20],
    "materialFamily": "MAT_Nature",
    "source": "Quaternius StylizedNature MegaKit (CC0)"
  }
}
```

지시 방식이 바뀐다:
```
✗ "적당한 나무를 만들어서 넣어라"
✓ "ASSET_CATALOG 의 type=tree 중 적합한 것을 선택하라"
```

### 5-E. Asset Family 구조

개별 에셋을 낱개로 늘리지 않는다. 패밀리로 파생시킨다.

```
Wood_Master          Tree
 ├─ oak               ├─ Oak
 ├─ burned            ├─ Pine
 ├─ mossy             ├─ Dead
 └─ wet               ├─ Magic
                      └─ Snow
```
같은 마스터에서 파생하면 100개를 무작위로 만든 것보다 훨씬 안정적이다.

### 5-F. 교체 실행 + 검증

RE-SKIN 부터 시작한다 (비용 최소, 효과 최대).
```
old mesh → new material → new lighting → new shader
```
에셋을 새로 만들지 않고도 완전히 다른 느낌으로 갈 수 있다. 이것이 Visual Rebase 의 핵심 수단.

교체 후 매번 `VISUAL_DOD.md` 절차 실행.

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| **에셋 조달 전략 선택** | DECISION | **필수** — 재활용/무료팩/ProBuilder/신규 |
| **어떤 무료 팩 계열을 쓸지** | DECISION | **필수** — 되돌리기 비쌈 |
| 팩 다운로드 | MANUAL | URL + 라이선스 + 설치 경로 안내 |
| **DELETE 판정** | DECISION | **필수** — 데이터 손실 |
| 새 원본 아트가 반드시 필요 | MANUAL | 무엇이 왜 필요한지 목록화 |
| 유료 에셋이 최선으로 보임 | DECISION | 대안 함께 제시. 구매는 에이전트가 하지 않음 |

---

## EXIT GATE

| # | 조건 |
|---|---|
| 1 | 모든 시각 요소가 KEEP/RE-SKIN/REBUILD/REPLACE/DELETE 중 하나로 판정됨 |
| 2 | `ASSET_CATALOG.json` 에 사용 중인 모든 에셋이 등록됨 |
| 3 | 카탈로그에 없는 에셋이 씬에 없음 (VisualLinter) |
| 4 | 해결 못 한 항목이 전부 `MISSING_` + `MAT_Missing` 으로 표시됨 |
| 5 | `missing[]` 목록이 사용자에게 보고됨 |
| 6 | 스코어카드 9항목 여전히 ≥4 (교체로 퇴행하지 않았는가) |

## OUTPUTS
- `Docs/Visual/ASSET_CATALOG.json`
- `Docs/Visual/ASSET_REPLACEMENT_MATRIX.md`
- `Assets/Art/Approved/` 정리

## STATE UPDATE
```yaml
stage: V5
status: PASS | PARTIAL | BLOCKED
asset_strategy: [reuse, cc0_pack, probuilder]
cc0_pack: "Quaternius StylizedNature MegaKit"
missing_count: 3
```
