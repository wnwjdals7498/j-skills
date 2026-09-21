# UNITY_CLI — 명령 참조

> LOAD WHEN: `unity` 명령을 쓰기 직전.
>
> **권위 순서:** `unity <cmd> --help` > Unity 공식 문서 > release notes > `Unity-Technologies/*` repo > 이 문서
> 이 문서의 예시가 `--help` 와 다르면 **`--help` 가 이긴다.** 버전을 하드코딩하지 않는다.

---

## 1. 구조화 출력

파싱이 필요한 명령에는 항상:
```bash
--format json
```
CLI 버전에 따라 `--json` 인 경우도 있다. `unity <cmd> --help` 로 확인.

---

## 2. 진단 / 상태

```bash
unity --version
unity --help
unity doctor --format json
unity diagnose update
unity status --format json
```

`unity diagnose update` 는 **설치 소유자와 올바른 업데이트 방법**을 알려준다. 그걸 따른다.

---

## 3. CLI 자체

```bash
unity upgrade --dry-run --format json
unity upgrade
```

설치 방식별 업데이트:
| 방식 | 명령 |
|---|---|
| CLI 자체 | `unity upgrade` |
| Homebrew | `brew upgrade unity-cli` |
| winget | `winget upgrade Unity.CLI` |
| apt/dnf | 해당 패키지 매니저 |

**설치 방식을 임의로 바꾸지 않는다.**

---

## 4. 인증 / 라이선스

```bash
unity auth status --format json
unity auth login              # ← MANUAL. 에이전트가 자격증명을 입력하지 않는다
unity license status --format json
```

CI/서비스 환경은 사용자 OAuth 대신 service-account 방식을 검토.
**secrets 를 로그·프롬프트·Git 어디에도 남기지 않는다.**

---

## 5. Editor 관리

```bash
unity editors --installed --format json
unity editors --installed --verbose --format json
unity editors --releases --format json        # 또는 unity releases --format json

unity editors upgrade --all --dry-run --format json
unity editors upgrade --all --yes --accept-eula

unity install latest --dry-run --format json
unity install latest --yes --accept-eula
```

### 금지
```
--replace       기존 Editor 를 대체 (자동 사용 금지)
--remove-old    구버전 제거 (자동 사용 금지)
```
side-by-side 가 기본. major.minor 는 유지, 패치만 올린다.

module 지정은 현재 CLI 문법 확인 후 `--module` / `-m` 사용.

---

## 6. 프로젝트 열기

```bash
unity open "<PROJECT_ROOT>"
```

**현재 프로젝트가 요구하는 Editor 버전을 쓴다.** 방금 설치한 latest 로 강제 오픈하지 않는다.

---

## 7. Pipeline 패키지

```bash
unity pipeline list --format json
unity pipeline list-versions --format json
unity pipeline install --project-path "<PROJECT_ROOT>"
unity pipeline upgrade --project-path "<PROJECT_ROOT>"
```

`Packages/manifest.json` 을 직접 편집하지 않고 **반드시 이 CLI 를 통한다.**
`--force` 는 repair 목적 외 금지.

Pipeline 은 Unity Editor 측 **tool provider** 다. MCP 보다 먼저 설치되어야 한다.

---

## 8. MCP

```bash
unity mcp configure --list
unity mcp configure --help
unity mcp configure <client> --dry-run
unity mcp configure <client> --local --project-path "<PROJECT_ROOT>" --dry-run
unity mcp configure <client> --local --project-path "<PROJECT_ROOT>" --yes
```

지원 client 예시 (실제 목록은 `--list` 출력이 우선):
```
claude  claude-code  cursor  vscode  vscode-insiders  copilot-cli
windsurf  cline  codex  kiro  trae  openclaw  antigravity  zed  continue  inspect
```

### 규칙
- **project-local 을 선호한다** (프로젝트별 연결 고정, 팀 재현성, 다른 Unity 프로젝트와 충돌 감소).
- 별도 Python/서드파티 Unity MCP 를 새로 설치하지 않는다. 내장 서버를 쓴다.
- 기존 설정 파일의 다른 key 는 CLI 가 보존하도록 맡긴다. 파일 전체 재생성 금지.
- **`unity mcp` 를 터미널에서 단독 실행해 무한 대기시키지 않는다.** MCP client 가 stdio 로 띄우게 하는 것이 목적.
- legacy MCP (uv/uvx, 구 Node server, 수동 localhost bridge, 중복 `unity` entry) 는 기록·보고만. 자동 삭제 금지.

---

## 9. Live Editor 조작

```bash
unity command --project-path "<PROJECT_ROOT>" --format json
unity list --project-path "<PROJECT_ROOT>" --format json     # 버전에 따라
```

**command 이름을 추측하지 않는다.** catalog 에서 조회한 실제 이름을 쓴다.

read-only smoke test — catalog 에 C# eval 이 있으면:
```
return Application.unityVersion;
```

이것이 **스크린샷 루프의 실행 통로**다 (`references/guides/SCREENSHOT_LOOP.md`).

---

## 10. Agent Skills

```bash
npx -y skills@latest add Unity-Technologies/skills --list
npx -y skills@latest list --json
npx -y skills@latest add Unity-Technologies/skills --all
```

`skills update` 대신 **repo 를 다시 source 로 지정**한다 — upstream 신규 skill 을 놓치지 않기 위해.

CLI 내장 skill 이 있으면:
```bash
unity skill install --list
unity skill refresh --dry-run
unity skill refresh --yes
```
`Unity-Technologies/skills` 를 이미 project-local 로 설치했다면 **동일 경로 덮어쓰기에 주의.**
충돌 예상 시 자동 overwrite 하지 말고 어느 source 를 쓰는지 보고한다.

---

## 11. 공식 Skills 가 해결하는 것 / 못 하는 것

| Skill | 해결 | 해결 못 함 |
|---|---|---|
| `unity-cli` | Editor 조작, Scene/GameObject 조사, C# 실행 | 그림/모델 창작 |
| `sprite-editor` | rect / pivot / border / slice | 원본 그림 품질 |
| `2d-pixel-perfect` | PPU, 필터링, 카메라, 픽셀 정렬 | 그림 스타일 |
| `tilemap-*` | Tile 배치 / Palette / RuleTile | Tile 원본 생성 |
| `ui-ugui` / `ui-uitk` | RectTransform / UXML / USS 구조 | 일러스트 제작 |
| `urp-postprocessing` | 화면 색감/톤 통일 | 실루엣/모델링 |
| `shader-graph-*` | 재질 스타일 통일 | 복잡한 모델 자체 |
| `manage-sprite-atlas` | packing / technical consistency | 컨셉 |

```
Skills = 미술 능력 추가 ✗
Skills = 에이전트가 Unity 를 잘못 만지는 비율 감소 ✓
```

**"설치하면 아트가 좋아진다" 는 기대는 하지 않는다.**
아트 디렉션 규칙(VISUAL_SPEC)과 검수 시스템(스크린샷 루프 + 린터)이 실제 개선을 만든다.
