# S0 — BOOTSTRAP (환경 표준화)

> LOAD WHEN: `PIPELINE_STATE.md` 가 없거나 `S0` 가 PASS 가 아닐 때.
> 원본 상세: `references/source/UNITY_AI_ENVIRONMENT_BOOTSTRAP_PROMPT.md` (명령 문법이 의심스러울 때만 참조)

**선행 필수:** `references/policy/SAFETY_RULES.md` 를 먼저 읽는다.

---

## ENTRY GATE
- 없음. 이것이 첫 스테이지다.

## INPUTS
- 대상 Unity 프로젝트 경로 (없으면 머신 레벨 작업만 수행)

---

## STEPS

### 0-A. Preflight — 조사만, 변경 없음

```bash
# OS / arch / shell / PATH / 권한
# 패키지 매니저 가용성: winget / brew / apt / dnf
node --version; npm --version; npx --version
git --version
```

Unity 프로젝트 루트 탐지 — 아래가 있는 디렉터리:
```
Packages/manifest.json
ProjectSettings/ProjectVersion.txt
Assets/
```
→ `<PROJECT_ROOT>` 로 확정.

**프로젝트를 못 찾으면:** 머신 레벨(CLI/Editor)까지만 수행. Skills/Pipeline/project-local MCP 는 `BLOCKED`.
**임의로 새 Unity 프로젝트를 만들지 않는다** — 그건 사용자 결정이다 (`ESCALATION` DECISION).

프로젝트 버전 기록:
```bash
cat "<PROJECT_ROOT>/ProjectSettings/ProjectVersion.txt"
```
→ `major.minor`, `patch`, editor line 기록.

Git 상태 스냅샷 (`SAFETY_RULES.md` §5).

---

### 0-B. Unity CLI 설치/업데이트

```bash
unity --version
```

**있으면:**
```bash
unity doctor --format json
unity diagnose update
unity upgrade --dry-run --format json
```
`unity diagnose update` 가 알려주는 **설치 소유자 기준**으로 업데이트한다. 설치 방식을 임의로 바꾸지 않는다.

| 설치 방식 | 업데이트 |
|---|---|
| CLI 자체 | `unity upgrade` |
| Homebrew | `brew upgrade unity-cli` |
| winget | `winget upgrade Unity.CLI` |
| apt/dnf | 해당 패키지 매니저 upgrade |

**없으면:**

Windows:
```powershell
winget install Unity.CLI
```
winget 불가 시 Unity 공식 PowerShell installer 사용 (채널은 실행 시점 공식 문서 확인).

macOS/Linux:
```bash
brew install --cask unity-cli
```
Homebrew 없으면 Unity 공식 설치 스크립트.

검증:
```bash
unity --version
unity --help
unity doctor --format json
```

> **문법 권위 순서:** `unity <cmd> --help` > 공식 문서 > release notes > `Unity-Technologies/*` repo.
> 블로그/오래된 예제를 복사하지 않는다. 이 문서의 예시 명령도 `--help` 와 다르면 `--help` 가 이긴다.

---

### 0-C. 인증 / 라이선스

```bash
unity auth status --format json
unity license status --format json
```

로그인 필요 → **STOP (MANUAL).** `ESCALATION.md` §4 형식으로 사용자에게 넘긴다.
```bash
unity auth login
```
자격증명을 로그에 남기지 않는다.

---

### 0-D. 기존 Editor 패치 업데이트 (major.minor 유지)

```bash
unity editors --installed --format json
unity editors upgrade --all --dry-run --format json
```

dry-run 결과 확인 후:
```bash
unity editors upgrade --all --yes --accept-eula
```

**`--replace` / `--remove-old` 를 자동으로 쓰지 않는다.** side-by-side 가 기본.

검증: `unity editors --installed --format json` 재실행 → 남은 패치 후보 없음.

---

### 0-E. 최신 안정 Editor 설치 (side-by-side)

```bash
unity editors --releases --format json      # 또는 unity releases --format json
unity install latest --dry-run --format json
```

선택 기준: official / production-stable / `f` 채널. alpha·beta 는 사용자 요청 없으면 제외.

이미 설치되어 있으면 **재설치하지 않는다.**

build module: 기존 프로젝트가 쓰는 모듈을 조사해 동일 ID 가 지원되면 같이 설치.
용도를 모르면 **core 만** 설치하고 필요한 모듈을 보고한다. Visual Studio 등 선택 도구를 임의 추가하지 않는다.

```bash
unity install latest --yes --accept-eula
```

검증: `ProjectVersion.txt` 가 **변경되지 않았는지** 반드시 확인.

---

### 0-F. Unity 공식 Agent Skills 동기화

```bash
cd "<PROJECT_ROOT>"
npx -y skills@latest add Unity-Technologies/skills --list
npx -y skills@latest list --json
npx -y skills@latest add Unity-Technologies/skills --all
```

`skills update` 대신 **repo 를 다시 source 로 지정**한다 — upstream 에 새로 추가된 skill 을 놓치지 않기 위해.

Node 가 없으면 비공식 installer 를 실행하지 말고 **STOP (MANUAL)**.

Unity repo 와 무관한 기존 프로젝트 skill 을 삭제/덮어쓰지 않는다.

기록: 설치된 skill 이름, source repo, scope, `skills-lock.json` 변경, agent 별 생성 경로.

> **이 skills 는 미술 능력을 추가하지 않는다.** 에이전트가 Unity 를 잘못 만지는 비율을 줄여줄 뿐이다.
> 실제 비주얼 개선은 V1~V7 이 담당한다.

---

### 0-G. Unity Pipeline 패키지

```bash
unity pipeline list --format json
unity pipeline list-versions --format json
```

미설치:
```bash
unity pipeline install --project-path "<PROJECT_ROOT>"
```
구버전:
```bash
unity pipeline upgrade --project-path "<PROJECT_ROOT>"
```
최신이면 아무것도 하지 않는다. `--force` 는 repair 목적 외 금지.

검증: `com.unity.pipeline` 존재, registry 최신, package resolution 성공, compile error 없음.
`manifest.json` / `packages-lock.json` diff 를 확인한다.

---

### 0-H. MCP 구성

**Pipeline 설치가 선행되어야 한다** (Pipeline 이 Editor 측 tool provider).

```bash
unity mcp configure --list
unity mcp configure --help
```

현재 AI client 판별 (codex / claude-code / cursor / vscode 등). project-local 을 선호한다.

```bash
unity mcp configure <client> --dry-run
unity mcp configure <client> --local --project-path "<PROJECT_ROOT>" --dry-run
unity mcp configure <client> --local --project-path "<PROJECT_ROOT>" --yes
```

- 기존 설정 파일의 다른 key 를 보존하도록 CLI 에 맡긴다. 파일 전체를 재생성하지 않는다.
- 별도 Python/서드파티 Unity MCP 를 새로 설치하지 않는다. `unity mcp` 내장 서버를 쓴다.
- legacy MCP (uv/uvx 기반, 구 Node server, 수동 localhost bridge, 중복 `unity` entry) 발견 시:
  기록 → 충돌 가능성 검사 → **자동 삭제 금지** → 보고서에 제거 권고.
- **`unity mcp` 를 터미널에서 단독 실행해 무한 대기시키지 않는다.** MCP client 가 stdio 로 띄우게 하는 것이 목적.

---

### 0-I. 키트 적용 (템플릿 주입)

```powershell
<skill-dir>/scripts/apply-kit.ps1 -ProjectRoot "<PROJECT_ROOT>" -Profile 3d   # 또는 2d
```

이것이 생성하는 것:
```
<PROJECT_ROOT>/AGENTS.md                          (얇은 진입점 → 키트를 가리킴)
<PROJECT_ROOT>/CLAUDE.md                          (AGENTS.md 링크)
<PROJECT_ROOT>/Docs/Visual/VISUAL_SPEC.yaml       (프로파일 템플릿 복사)
<PROJECT_ROOT>/Docs/Visual/CONCEPT_ANALYSIS.yaml
<PROJECT_ROOT>/Docs/Visual/ASSET_CATALOG.json
<PROJECT_ROOT>/Docs/Visual/PIPELINE_STATE.md
<PROJECT_ROOT>/Docs/Visual/Reference/             (컨셉아트 넣을 곳)
<PROJECT_ROOT>/.agents/skills/visual-director/SKILL.md
<PROJECT_ROOT>/Assets/Editor/AIVisual/*.cs        (GameViewCapture, ConceptOverlay, VisualLinter)
<PROJECT_ROOT>/Assets/VisualTests/Screenshots/
```

**프로파일(3d/2d)을 모르면 → STOP (DECISION).** 추측하지 않는다.

---

### 0-J. Live 연결 검증

```bash
unity open "<PROJECT_ROOT>"     # 프로젝트가 요구하는 Editor 버전으로. latest 로 강제 오픈 금지.
unity status --format json
unity command --project-path "<PROJECT_ROOT>" --format json
```

command catalog 가 반환되는지 확인. **command 이름을 추측하지 말고 catalog 에서 조회한 이름을 쓴다.**

read-only smoke test — catalog 에 C# eval 이 있으면:
```
return Application.unityVersion;
```

Editor 미실행이면 `BLOCKED — Editor not running`.

---

## STOP CONDITIONS

| 조건 | 분류 | 행동 |
|---|---|---|
| Unity 로그인/라이선스 필요 | MANUAL | 로그인 절차 안내 후 대기 |
| Node.js 미설치 | MANUAL | 설치 안내. 비공식 installer 실행 금지 |
| 관리자 권한 필요 (PATH, 심볼릭 링크) | MANUAL | 명령 제공 후 대기 |
| Unity 프로젝트를 찾을 수 없음 | DECISION | 새로 만들지 결정 요청 |
| 3D/2D 프로파일 불명 | DECISION | 선택지 제시 |
| major.minor 마이그레이션이 필요해 보임 | RISK | 별도 작업으로 분리, 승인 요청 |
| legacy MCP 와 충돌 | RISK | 제거 권고만, 자동 삭제 금지 |
| Editor 실행 불가 (GUI 필요) | MANUAL | Editor 실행 요청 후 대기 |

---

## EXIT GATE

| # | 검증 | 명령/방법 | PASS 조건 |
|---|---|---|---|
| 1 | CLI 최신 | `unity --version` / `unity doctor --format json` | 진단 오류 없음 |
| 2 | Editor 패치 | `unity editors upgrade --all --dry-run --format json` | 남은 후보 없음 |
| 3 | latest 설치 | `unity editors --installed --format json` | latest stable 존재 |
| 4 | 프로젝트 보존 | `ProjectVersion.txt` 재확인 | major.minor 불변 |
| 5 | Skills | `npx -y skills@latest list --json` | Unity 공식 skills 가 project scope 에 존재 |
| 6 | Pipeline | `unity pipeline list --format json` | `com.unity.pipeline` 최신 |
| 7 | MCP | `unity mcp configure --list` + client config | `unity mcp` 사용, 기타 설정 보존 |
| 8 | Live | `unity status` / `unity command` | Pipeline reachable, catalog 반환 |
| 9 | 키트 | 파일 존재 확인 | 위 §0-I 목록 전부 생성됨 |

전부 PASS → V1 진입 가능.
1~7 PASS + 8 만 실패 → `PARTIAL`, V1 진입은 허용 (V2 부터 Editor 필요).

---

## OUTPUTS
- `<PROJECT_ROOT>/Docs/Visual/PIPELINE_STATE.md` (초기화)
- 부트스트랩 보고서 (`references/source/UNITY_AI_ENVIRONMENT_BOOTSTRAP_PROMPT.md` §12 형식)

## STATE UPDATE
```yaml
stage: S0
status: PASS | PARTIAL | BLOCKED | FAILED
profile: 3d | 2d
mode: greenfield | rebase
unity_cli: <version>
project_editor: <version>
pipeline_package: <version>
mcp_client: <client>
blockers: []
```
