# VISUAL_DOD — 비주얼 작업 완료 정의

> LOAD WHEN: 어떤 비주얼 작업이든 "완료" 로 보고하기 직전. **예외 없음.**

---

## 1. 완료가 **아닌** 것

아래는 완료 조건이 **아니다.**

```
✗ 코드가 컴파일된다
✗ GameObject 가 존재한다
✗ 게임플레이가 동작한다
✗ 콘솔 에러가 없다
✗ 내가 보기에 코드가 맞다
```

비주얼 작업에서 **컴파일 성공을 완료 조건으로 삼으면 반드시 실패한다.**
결과를 실제로 **렌더해서 봐야** 한다.

---

## 2. 완료 절차 (순서 고정)

```
1. 영향받은 씬을 Unity 에서 연다.
2. Game View 에 들어간다.
3. 타깃 해상도로 스크린샷을 캡처한다.        (기본 1920x1080)
4. VisualLinter 를 실행한다.
5. 스크린샷을 직접 검사한다.
6. 위반 사항을 전부 수정한다.
7. 최종 스크린샷을 다시 캡처한다.
8. 변경 내용 + 남은 누락 에셋을 보고한다.
```

3~7 이 빠지면 **완료 보고 금지.** Editor 를 띄울 수 없으면 `BLOCKED — Editor not running` 이다.

---

## 3. 검사 항목 (스크린샷 육안 + 린터)

### 자동 검사 (VisualLinter — 정량)

| 항목 | 실패 조건 |
|---|---|
| 기본 머티리얼 | `Default-Material` / `Sprite-Default` 를 쓰는 렌더러 존재 |
| 의도치 않은 프리미티브 | BLOCKOUT 루트 밖에 프리미티브 메시 존재 |
| 스케일 위반 | 카탈로그 `allowedScale` 초과 / 비균등 스케일 |
| 팔레트 위반 | 머티리얼 색상이 `VISUAL_SPEC.palette` 에 없음 |
| 카메라 | FOV / projection / height 가 스펙과 불일치 |
| 조명 | Directional Light 회전/색온도/강도 스펙 불일치 |
| Volume | Global Volume 프로파일이 스펙 프로파일이 아님 |
| 2D PPU | 스프라이트 PPU 가 카테고리 기준과 불일치 |
| 2D 종횡비 | 스프라이트가 늘어남 (비균등 스케일) |
| UI 여백 | 디자인 토큰 최소값 미만 |
| 누락 에셋 | `MISSING_` 접두사 오브젝트가 씬에 존재 |

상세 규칙과 구현: `references/guides/VISUAL_LINTER_SPEC.md`

### 육안 검사 (스크린샷 — 정성)

| 항목 | 확인 |
|---|---|
| 실루엣 | 컨셉과 큰 형태가 맞는가 |
| 초점 계층 | 시선이 의도한 곳으로 가는가 |
| 디테일 밀도 | 캐릭터 > 상호작용물 > 환경 > 배경 순인가 |
| 톤 일관성 | 한 화면 안에서 다른 게임에서 온 것처럼 보이는 물체가 있는가 |
| 스케일 감 | 캐릭터 대비 문/건물/나무 비례가 자연스러운가 |

---

## 4. 통과 기준

| 등급 | 기준 |
|---|---|
| **PASS** | 린터 error 0 + 스코어카드 9항목 전부 ≥4 + 스크린샷 증거 있음 |
| **PARTIAL** | 린터 error 0 이지만 스코어카드 일부 <4, 또는 `VISUAL_MISSING` 이 남아 있음 |
| **BLOCKED** | Editor/라이선스/에셋 부재로 검증 자체가 불가 |
| **FAILED** | 린터 error 존재 |

스코어카드 정의: `references/guides/SCREENSHOT_LOOP.md`

---

## 5. 증거 보관

모든 완료 보고는 스크린샷 경로를 포함해야 한다.

```
Assets/VisualTests/Screenshots/
├─ concept_master.png            (참조 원본, 읽기 전용)
├─ iter_01_camera.png
├─ iter_02_composition.png
├─ ...
└─ final_{scene}_{yyyymmdd_hhmm}.png
```

**"찍었다고 말하기" 는 증거가 아니다.** 파일이 실제로 존재해야 한다.

---

## 6. 보고 템플릿

```markdown
## VISUAL DoD — {PASS | PARTIAL | BLOCKED | FAILED}

**씬:** {scene}
**해상도:** 1920x1080
**스크린샷:** `Assets/VisualTests/Screenshots/final_xxx.png`

### 린터
| 규칙 | 결과 |
|---|---|
| ... | ✓ / ✗ {상세} |

에러 {n}건 / 경고 {n}건

### 스코어카드
| 항목 | 점수 | 근거 |
|---|---|---|
| Camera | 0-5 | |
| Composition | | |
| Silhouette | | |
| Scale | | |
| Palette | | |
| Lighting | | |
| Material language | | |
| Detail density | | |
| Focal hierarchy | | |

### 남은 VISUAL_MISSING
- ...

### 판정 근거
{왜 이 등급인지 한 문단}
```
