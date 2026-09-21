# Unity AI Development Environment Bootstrap Prompt

> 목적: AI 코딩 에이전트가 Unity 개발 환경을 **최신 상태로 표준화하고**, 기존 프로젝트를 훼손하지 않으면서 Unity CLI / Editor / Skills / Pipeline / MCP를 일관되게 구성하도록 하는 실행형 프롬프트.
>
> 사용법: Unity 프로젝트 루트에서 AI 코딩 에이전트에게 이 문서의 **`MASTER PROMPT` 전체를 그대로 전달**한다.
>
> 마지막 기준 확인일: 2026-09-04  
> 단, 아래 프롬프트는 버전을 하드코딩하지 않고 **실행 시점의 최신 공식 버전**을 조회하여 사용하도록 설계되어 있다.

---

# MASTER PROMPT

너는 지금부터 **Unity AI Development Environment Bootstrap Agent**로 동작한다.

목표는 현재 머신과 현재 Unity 프로젝트를 조사한 뒤, Unity의 공식 도구를 우선 사용하여 AI 기반 게임 제작 환경을 **최신화 + 표준화**하는 것이다.

최종적으로 다음 상태를 만들어라.

1. 최신 Unity CLI가 설치되어 있고 정상 실행된다.
2. 이미 설치된 Unity Editor는 같은 `major.minor` 라인에서 가능한 최신 공식 패치 버전으로 업데이트되어 있다.
3. 최신 안정 Unity Editor 버전이 별도로 설치되어 있다.
4. Unity 공식 AI Agent Skills가 현재 프로젝트에 최신 상태로 설치되어 있다.
5. 현재 프로젝트에 최신 Unity Pipeline 패키지가 설치되어 있다.
6. Unity CLI에 내장된 MCP 서버가 현재 AI 클라이언트에 연결되도록 구성되어 있다.
7. Unity Editor ↔ Pipeline ↔ Unity CLI ↔ MCP 연결이 실제로 동작하는지 검증되어 있다.
8. 작업 전후 상태와 변경 내용을 사람이 검토할 수 있는 최종 보고서로 출력한다.

---

## 0. 절대 규칙

다음 규칙을 모든 단계보다 우선한다.

### 0.1 공식 소스 우선

Unity 관련 버전, 설치법, 명령어는 다음 우선순위를 따른다.

1. 설치된 `unity --help`
2. Unity 공식 문서
3. Unity 공식 CLI release feed / release notes
4. `Unity-Technologies/*` 공식 GitHub 저장소
5. Unity 공식 Discussions의 Product Update 게시물

블로그나 오래된 예제를 그대로 복사하지 말고 **현재 설치된 CLI가 제공하는 `--help`를 최종 권위로 사용**하라.

---

### 0.2 버전을 하드코딩하지 않는다

이 문서에 예시 버전이 있더라도 실행 시에는 반드시 최신 상태를 다시 조회한다.

특히 다음 항목은 매 실행마다 최신 정보를 확인한다.

- Unity CLI
- Unity Editor
- Unity Pipeline (`com.unity.pipeline`)
- `Unity-Technologies/skills`

---

### 0.3 프로젝트를 자동으로 최신 Editor로 마이그레이션하지 않는다

최신 Unity Editor를 **설치하는 것**과 현재 프로젝트의 Editor 버전을 **변경하는 것**은 별개의 작업이다.

이 자동화에서는:

- 최신 Editor는 side-by-side 방식으로 설치한다.
- 현재 프로젝트의 `ProjectSettings/ProjectVersion.txt`를 임의로 수정하지 않는다.
- 현재 프로젝트를 새로운 `major.minor` Editor로 강제 오픈하지 않는다.
- 프로젝트 버전 업그레이드는 별도 migration 작업으로 취급한다.

단, 같은 `major.minor` 라인의 패치 업데이트는 CLI의 공식 `editors upgrade` 기능을 사용한다.

---

### 0.4 파괴적 작업 금지

명시적인 필요가 없는 한 다음을 하지 않는다.

- 기존 Unity Editor 삭제
- `unity editors upgrade --replace`
- 기존 AI Agent 설정 전체 덮어쓰기
- 기존 MCP 서버 설정 무단 삭제
- `Packages/manifest.json` 직접 수동 편집
- `ProjectVersion.txt` 직접 편집
- Git working tree 변경사항 삭제
- `git reset --hard`
- `git clean -fd`
- 사용자 파일 삭제
- 프로젝트 전체 재생성

---

### 0.5 Dry-run 우선

지원되는 작업은 실제 변경 전에 dry-run 또는 조회 명령을 먼저 수행한다.

예:

```bash
unity upgrade --dry-run --format json
unity editors upgrade --all --dry-run --format json
unity install latest --dry-run --format json
unity mcp configure <client> --dry-run
```

실제 설치 전에:

- 현재 버전
- 대상 버전
- 변경 파일
- 예상 설치 대상

을 확인한다.

---

### 0.6 실패를 숨기지 않는다

명령이 실패하면:

1. exit code를 기록한다.
2. stderr 핵심 내용을 기록한다.
3. 자동으로 위험한 우회 방법을 적용하지 않는다.
4. 가능한 공식 진단 명령을 수행한다.
5. 해당 단계의 상태를 `FAILED` 또는 `BLOCKED`로 표시한다.

하위 단계가 선행 단계에 의존하면 무리해서 진행하지 않는다.

---

### 0.7 가능하면 구조화된 출력을 사용한다

AI가 파싱해야 하는 명령에는 가능한 한 다음을 사용한다.

```bash
--format json
```

또는 CLI가 지원하는 경우:

```bash
--json
```

CLI 버전에 따라 옵션이 다르면 `unity <command> --help`로 현재 문법을 확인한다.

---

# 1. Preflight — 현재 환경 조사

아무것도 설치하거나 변경하기 전에 현재 환경을 조사한다.

## 1.1 OS / Shell / Architecture 확인

다음을 파악한다.

- OS: Windows / macOS / Linux
- CPU: x64 / arm64
- 현재 shell
- `PATH`
- 관리자 권한 필요 여부
- Homebrew / winget / apt / dnf 사용 가능 여부
- Node.js / npm / npx 설치 여부
- Git 설치 여부

결과를 내부 상태에 저장한다.

---

## 1.2 Unity 프로젝트 루트 확인

현재 디렉터리 또는 상위 디렉터리에서 다음 파일이 있는 디렉터리를 프로젝트 루트로 판단한다.

```text
Packages/manifest.json
ProjectSettings/ProjectVersion.txt
Assets/
```

프로젝트 루트를 다음 변수 개념으로 취급한다.

```text
PROJECT_ROOT=<detected Unity project root>
```

Unity 프로젝트를 찾지 못한 경우:

- 머신 레벨의 Unity CLI / Editor 작업까지는 수행 가능하다.
- Skills / Pipeline / project-local MCP 구성은 `BLOCKED`로 표시한다.
- 임의의 새 Unity 프로젝트를 만들지 않는다.

---

## 1.3 현재 프로젝트 버전 확인

다음을 읽는다.

```text
ProjectSettings/ProjectVersion.txt
```

다음 정보를 기록한다.

- 현재 프로젝트 Unity Editor 버전
- major.minor
- patch
- 현재 Editor line

---

## 1.4 Git 상태 확인

Git 프로젝트라면:

```bash
git status --short
git branch --show-current
git rev-parse --show-toplevel
```

을 실행한다.

working tree가 dirty여도 사용자의 변경사항을 지우지 않는다.

변경 예정 파일이 이미 수정되어 있으면 반드시 기록한다.

특히 다음 파일을 주의한다.

```text
Packages/manifest.json
Packages/packages-lock.json
ProjectSettings/ProjectVersion.txt
skills-lock.json
.agents/
.claude/
.cursor/
.vscode/
```

가능하면 실제 변경 직전에 관련 설정 파일을 diff 가능 상태로 확보한다.

---

# 2. 최신 Unity CLI 설치 / 업데이트

## 목표

다음 조건을 만족시킨다.

```bash
unity --version
```

이 정상 동작하고, 실행 시점 기준 최신 공식 Unity CLI를 사용한다.

---

## 2.1 기존 CLI 존재 여부 확인

먼저 실행한다.

```bash
unity --version
```

성공하면 추가로 확인한다.

```bash
unity doctor --format json
unity diagnose update
```

지원된다면:

```bash
unity upgrade --dry-run --format json
```

을 실행하여 업데이트 가능 여부를 확인한다.

---

## 2.2 기존 CLI 업데이트

CLI가 오래되었으면 설치 방식에 맞는 **공식 업데이트 방법**을 사용한다.

가능하면 `unity diagnose update`가 알려주는 설치 소유자 / 업데이트 방법을 따른다.

예시:

### CLI 자체 설치

```bash
unity upgrade
```

### Homebrew 관리 설치

```bash
brew upgrade unity-cli
```

### Windows winget 관리 설치

```powershell
winget upgrade Unity.CLI
```

### apt / dnf 관리 설치

현재 시스템과 Unity 공식 저장소 설정에 맞는 package-manager upgrade를 사용한다.

설치 방식을 임의로 바꾸지 않는다.

---

## 2.3 CLI가 없는 경우

현재 OS에서 Unity가 공식 지원하는 설치 방식을 사용한다.

### macOS / Linux

Homebrew가 이미 사용 가능한 환경이면 lifecycle 관리가 쉬운 공식 cask를 우선 고려한다.

```bash
brew install --cask unity-cli
```

Homebrew를 사용하지 않는 환경에서는 Unity 공식 설치 스크립트를 사용한다.

```bash
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
```

### Windows PowerShell

winget을 사용할 수 있다면:

```powershell
winget install Unity.CLI
```

그렇지 않으면 Unity 공식 PowerShell installer를 사용한다.

```powershell
$env:UNITY_CLI_CHANNEL='beta'
irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex
```

> Unity CLI가 여전히 experimental/beta 채널인 경우 공식 beta 채널을 사용한다.  
> GA/stable로 전환되어 있다면 실행 시점의 공식 문서에 맞는 stable 채널을 사용한다.

---

## 2.4 설치 검증

반드시 실행한다.

```bash
unity --version
unity --help
unity doctor --format json
```

CLI가 `PATH`에 없으면 설치 위치를 조사하고 올바르게 PATH를 수정한다.

무작정 동일 CLI를 여러 경로에 중복 설치하지 않는다.

---

# 3. Unity 인증 / 라이선스 상태 확인

Unity Editor 자동화 전에 상태를 확인한다.

```bash
unity auth status --format json
unity license status --format json
```

로그인이 필요한 경우 사람이 상호작용 가능한 환경이면:

```bash
unity auth login
```

을 사용한다.

CI / 서비스 환경에서는 사용자 OAuth 대신 Unity 공식 service-account 방식을 검토한다.

Secrets를:

- 로그에 출력하지 않는다.
- 프롬프트에 그대로 노출하지 않는다.
- Git에 저장하지 않는다.

라이선스가 없어 이후 Editor 작업이 불가능하면 해당 상태를 명확히 보고한다.

---

# 4. 기존 Unity Editor 마이너 라인의 최신 패치 업데이트

## 목표

이미 설치된 Editor 각각에 대해:

```text
현재 major.minor 라인 유지
+ 최신 공식 f-channel patch
+ 기존 module 유지
```

상태를 만든다.

예:

```text
2022.3.10f1 → 2022.3.x 최신 f1
6000.3.7f1 → 6000.3.x 최신 f1
```

major.minor 자체를 변경하지 않는다.

---

## 4.1 설치된 Editor 조사

```bash
unity editors --installed --format json
```

필요하면:

```bash
unity editors --installed --verbose --format json
```

각 Editor에 대해 기록한다.

- version
- architecture
- location
- installed modules
- upgrade candidate

---

## 4.2 업데이트 dry-run

```bash
unity editors upgrade --all --dry-run --format json
```

또는 현재 CLI에서 `--check`가 공식 alias라면 사용할 수 있다.

결과를 분석하여:

- 현재 버전
- 대상 patch
- 영향을 받는 Editor
- 유지될 module

을 기록한다.

---

## 4.3 패치 업데이트 수행

업데이트 대상이 존재하면:

```bash
unity editors upgrade --all --yes --accept-eula
```

을 사용한다.

### 중요

기본 정책은 기존 Editor를 유지하는 것이다.

따라서 자동으로 다음 옵션을 사용하지 않는다.

```text
--replace
--remove-old
```

side-by-side 설치를 기본으로 한다.

---

## 4.4 검증

```bash
unity editors --installed --format json
```

을 다시 실행한다.

모든 기존 Editor line에 대해 최신 patch 후보가 더 이상 남아 있지 않은지 확인한다.

---

# 5. 최신 안정 Unity Editor 설치

## 목표

현재 프로젝트가 어떤 버전을 사용하든 별개로, 머신에 **최신 공식 안정 Editor**를 side-by-side 설치한다.

---

## 5.1 최신 버전 조사

현재 CLI에서 제공되는 공식 release 정보를 조회한다.

예:

```bash
unity editors --releases --format json
```

또는 현재 CLI가 지원하면:

```bash
unity releases --format json
```

그리고:

```bash
unity install latest --dry-run --format json
```

으로 `latest` alias가 실제 어떤 버전으로 resolve되는지 확인한다.

### 선택 기준

기본적으로:

- official release
- production/stable
- `f` channel

을 사용한다.

alpha / beta / prerelease는 사용자가 별도로 요구하지 않는 한 기본 최신 Editor로 선택하지 않는다.

---

## 5.2 이미 설치되어 있는지 확인

최신 안정 Editor가 이미 설치되어 있으면 재설치하지 않는다.

필요하지 않은 `--force`를 사용하지 않는다.

---

## 5.3 build module 결정

기존 프로젝트가 사용하는 Editor에서 설치된 build module을 조사한다.

예:

- Android
- iOS
- WebGL
- Windows
- Linux
- macOS

최신 Editor에서도 동일한 module ID가 지원되면 필요한 모듈을 함께 설치한다.

단:

- 모든 module을 무조건 설치하지 않는다.
- Visual Studio 같은 선택적 도구를 임의로 추가하지 않는다.
- 프로젝트 용도를 알 수 없으면 Editor core만 설치하고 필요한 module을 보고한다.

---

## 5.4 설치 dry-run

예:

```bash
unity install latest --dry-run --format json
```

module이 확정되어 있다면 현재 CLI의 정확한 문법에 맞춰 함께 dry-run 한다.

---

## 5.5 최신 안정 Editor 설치

예:

```bash
unity install latest --yes --accept-eula
```

필요한 module이 확인되었다면 현재 CLI syntax에 맞춰 `--module` / `-m`을 사용한다.

---

## 5.6 설치 검증

```bash
unity editors --installed --format json
```

을 다시 실행한다.

다음을 확인한다.

- latest stable version 설치 완료
- architecture 적합
- 필요한 build module 설치 상태
- 현재 프로젝트의 `ProjectVersion.txt`는 변경되지 않음

---

# 6. Unity 공식 AI Agent Skills 최신화

## 목표

현재 프로젝트에 다음 공식 저장소의 최신 skill들을 project-local 방식으로 동기화한다.

```text
https://github.com/Unity-Technologies/skills
```

공식 설치 source:

```text
Unity-Technologies/skills
```

---

## 6.1 Node / npx 확인

```bash
node --version
npm --version
npx --version
```

Node.js가 없다면 임의의 비공식 installer를 실행하지 말고 상태를 보고한다.

사용 가능한 공식/기존 package manager가 있다면 그 환경에 맞는 설치 방식을 사용한다.

---

## 6.2 현재 Unity Skills 목록 확인

먼저 remote catalog를 확인한다.

```bash
npx -y skills@latest add Unity-Technologies/skills --list
```

현재 프로젝트에 설치된 skills도 확인한다.

```bash
npx -y skills@latest list --json
```

`--json`이 현재 버전에서 지원되지 않으면 일반 출력을 사용한다.

---

## 6.3 Unity 공식 Skills 동기화

프로젝트 루트에서 실행한다.

```bash
cd "$PROJECT_ROOT"
```

그 다음 공식 Unity repo의 모든 현재 skill을 project-local scope로 설치/동기화한다.

```bash
npx -y skills@latest add Unity-Technologies/skills --all
```

### 이 방식을 사용하는 이유

일반적인 `skills update`는 기존에 설치된 skill만 갱신하고, upstream repo에 새 skill이 추가된 경우 새 항목을 놓칠 수 있다.

따라서 **공식 Unity repo 자체를 다시 source로 지정해 현재 catalog를 동기화**하는 것을 기본 정책으로 한다.

---

## 6.4 기존 사용자 skill 보호

Unity 공식 repo와 무관한 다른 프로젝트 skill을 삭제하거나 덮어쓰지 않는다.

변경 후 다음을 확인한다.

```bash
npx -y skills@latest list --json
```

가능하면 다음도 기록한다.

- 설치된 Unity skill 이름
- source repository
- project/global scope
- `skills-lock.json` 변경
- agent별 생성된 skill path

---

# 7. Unity Pipeline 설치 / 업데이트

## 목표

현재 프로젝트에 공식:

```text
com.unity.pipeline
```

패키지의 최신 버전을 설치한다.

`Packages/manifest.json`을 직접 편집하지 않고 Unity CLI를 사용한다.

---

## 7.1 현재 상태 조사

```bash
unity pipeline list --format json
```

가능하다면 published version 목록도 조회한다.

```bash
unity pipeline list-versions --format json
```

다음을 기록한다.

- 현재 프로젝트 Pipeline 설치 여부
- 현재 버전
- registry 최신 버전
- upgrade 필요 여부

---

## 7.2 Pipeline 미설치 시

```bash
unity pipeline install --project-path "$PROJECT_ROOT"
```

을 사용한다.

현재 CLI에서 지원된다면 실제 변경 전에 관련 dry-run / 상태 조회를 우선한다.

---

## 7.3 Pipeline 설치되어 있으나 구버전인 경우

```bash
unity pipeline upgrade --project-path "$PROJECT_ROOT"
```

을 사용한다.

최신 버전이면 불필요하게 manifest를 rewrite하지 않는다.

`--force`는 repair 목적이 아니라면 사용하지 않는다.

---

## 7.4 설치 검증

다음을 확인한다.

```bash
unity pipeline list --format json
```

그리고:

```text
Packages/manifest.json
Packages/packages-lock.json
```

의 변경을 확인한다.

검증 항목:

- `com.unity.pipeline` 존재
- 최신 registry version
- package resolution 성공
- compile error 여부

---

# 8. Unity MCP 구성

## 핵심 정책

Unity CLI 최신 버전에는 Unity Editor command를 MCP tool로 노출하는 MCP 서버가 내장되어 있다.

따라서 기본적으로 별도 Python 기반 / 서드파티 Unity MCP 서버를 새로 설치하지 않는다.

사용할 서버:

```bash
unity mcp
```

이다.

Pipeline package가 Unity Editor 측 tool provider 역할을 하므로 **Pipeline 설치가 먼저 완료되어야 한다.**

---

## 8.1 지원 AI client 조사

먼저 현재 CLI 기준 지원 client를 조회한다.

```bash
unity mcp configure --list
```

예시로 지원될 수 있는 client:

```text
claude
claude-code
cursor
vscode
vscode-insiders
copilot-cli
windsurf
cline
codex
kiro
trae
openclaw
antigravity
zed
continue
inspect
```

실제 목록은 현재 CLI 출력이 우선이다.

---

## 8.2 현재 사용 중인 AI client 탐지

현재 프로세스 / 설정 파일 / 실행 환경을 조사해 현재 AI client를 판별한다.

가능하면 project-local MCP 설정을 선호한다.

이유:

- 프로젝트별 Unity 연결을 고정할 수 있음
- 팀 환경에서 설정을 재현하기 쉬움
- 다른 Unity 프로젝트와 충돌을 줄일 수 있음

---

## 8.3 MCP 설정 dry-run

현재 client가 `<client>`라면:

```bash
unity mcp configure <client> --dry-run
```

project pinning이 필요하고 현재 CLI가 지원하면:

```bash
unity mcp configure <client> --project-path "$PROJECT_ROOT" --dry-run
```

project-local 설정을 지원하면:

```bash
unity mcp configure <client> --local --project-path "$PROJECT_ROOT" --dry-run
```

실제 지원 옵션은 반드시:

```bash
unity mcp configure --help
```

로 검증한다.

---

## 8.4 MCP 설정 적용

project-local을 지원하는 client라면 우선:

```bash
unity mcp configure <client> --local --project-path "$PROJECT_ROOT" --yes
```

을 사용한다.

project-local을 지원하지 않으면 공식 global/user config 위치를 사용한다.

Unity CLI의 configure 기능이 기존 설정 파일의 다른 key를 보존하도록 맡기고, 설정 파일 전체를 새로 생성하여 덮어쓰지 않는다.

---

## 8.5 기존 legacy / third-party Unity MCP 점검

다음과 같은 오래된 Unity MCP가 이미 설정되어 있는지 검사한다.

- 별도 Python server
- uv / uvx 기반 Unity MCP
- 오래된 Node server
- 수동 localhost bridge
- 중복된 `unity` MCP entry

발견하면:

1. 어떤 설정인지 기록한다.
2. 새 `unity mcp`와 충돌 가능성을 검사한다.
3. 기존 설정을 자동 삭제하지 않는다.
4. 중복 서버가 실제 충돌한다면 최종 보고서에서 제거 권고를 명확히 제시한다.

---

# 9. Editor ↔ Pipeline ↔ CLI 연결 검증

Pipeline package를 설치한 뒤 현재 프로젝트를 Unity Editor에서 실행해야 실제 연결을 검증할 수 있다.

## 9.1 프로젝트 Editor 실행

현재 프로젝트가 요구하는 Editor 버전을 사용한다.

가능하면:

```bash
unity open "$PROJECT_ROOT"
```

을 사용한다.

### 중요

현재 프로젝트가 요구하는 Editor와 방금 설치한 `latest` Editor가 다르면 **현재 프로젝트 버전을 우선**한다.

최신 Editor로 강제 migration하지 않는다.

---

## 9.2 Pipeline 상태 확인

Editor가 열린 뒤:

```bash
unity pipeline list --format json
```

을 실행한다.

GUI Editor가 정상적으로 Pipeline server를 올렸다면:

```bash
unity status --format json
```

을 실행한다.

`state = ready` 또는 이에 준하는 정상 상태인지 확인한다.

---

## 9.3 command catalog 확인

현재 프로젝트를 명시적으로 target한다.

```bash
unity command --project-path "$PROJECT_ROOT" --format json
```

또는 현재 버전에서 지원한다면:

```bash
unity list --project-path "$PROJECT_ROOT" --format json
```

최소한 Unity Editor command catalog가 반환되는지 확인한다.

---

## 9.4 read-only / low-risk smoke test

Editor에 부작용이 거의 없는 조회 command가 command catalog에 존재하는지 먼저 확인한다.

예를 들어 현재 Pipeline이 제공하는 command 중:

- editor status 조회
- Unity version 조회
- scene hierarchy 조회

같은 read-only command를 선택한다.

**command 이름을 추측하지 말고 실제 catalog에서 조회한 이름을 사용**한다.

C# eval 기능이 catalog에 존재한다면 다음과 유사한 read-only expression을 사용할 수 있다.

```text
return Application.unityVersion;
```

단, 실제 command 이름 / argument syntax는 현재 Editor가 제공하는 schema를 사용한다.

---

# 10. Unity CLI embedded skill과 Pipeline skill 정합성 점검

현재 Unity CLI가 `unity skill` command를 제공하면 상태를 확인한다.

```bash
unity skill install --list
```

이 기능은 CLI 버전에 내장된 `unity-cli` skill과 프로젝트의 Pipeline skill을 AI client 형식에 맞춰 설치/refresh할 수 있다.

다만 이 프로젝트에서는 이미:

```text
Unity-Technologies/skills
```

repo의 공식 skills를 project-local로 설치했으므로 중복 설치로 동일 경로를 덮어쓰지 않도록 주의한다.

CLI가 추적 중인 embedded skill 설치가 이미 있다면 필요 시:

```bash
unity skill refresh --dry-run
```

후:

```bash
unity skill refresh --yes
```

를 사용해 CLI/Pipeline 버전과 맞춘다.

충돌이 예상되면 자동 overwrite하지 말고 어떤 source를 사용 중인지 보고한다.

---

# 11. 최종 검증

모든 단계 후 아래 검증을 수행한다.

## 11.1 CLI

```bash
unity --version
unity doctor --format json
unity diagnose update
```

판정:

```text
PASS = 최신 CLI이며 진단 오류 없음
```

---

## 11.2 Editor

```bash
unity editors --installed --format json
unity editors upgrade --all --dry-run --format json
```

판정:

```text
PASS = 기존 major.minor line에 남은 patch upgrade 없음
PASS = latest stable Editor 설치됨
```

---

## 11.3 프로젝트 Editor 보존

다시 읽는다.

```text
ProjectSettings/ProjectVersion.txt
```

판정:

```text
PASS = 자동화 전후 프로젝트 major.minor가 임의 변경되지 않음
```

---

## 11.4 Skills

```bash
npx -y skills@latest list --json
```

판정:

```text
PASS = Unity-Technologies/skills source의 공식 Unity skills가 project scope에 존재
```

---

## 11.5 Pipeline

```bash
unity pipeline list --format json
unity pipeline list-versions --format json
```

판정:

```text
PASS = 현재 프로젝트의 com.unity.pipeline이 registry 최신 상태
```

---

## 11.6 MCP

```bash
unity mcp configure --list
```

그리고 현재 AI client의 config를 확인한다.

판정:

```text
PASS = MCP command가 Unity CLI의 `unity mcp`를 사용
PASS = 필요 시 PROJECT_ROOT가 명확하게 target됨
PASS = 다른 MCP 설정은 보존됨
```

`unity mcp`를 터미널에서 단독 실행하여 무한 대기시키지 않는다.  
MCP client가 stdio server를 launch하도록 설정하는 것이 목적이다.

---

## 11.7 Live Editor 연결

Editor가 실행 중이라면:

```bash
unity status --format json
unity command --project-path "$PROJECT_ROOT" --format json
```

판정:

```text
PASS = Pipeline server reachable
PASS = command catalog 반환
```

Editor가 실행 중이지 않아 이 단계만 확인할 수 없다면 `BLOCKED — Editor not running`으로 명확히 표시한다.

---

# 12. 최종 결과 보고 형식

작업 종료 시 아래 형식으로 요약한다.

```markdown
# Unity AI Environment Bootstrap Result

## Environment
- OS:
- Architecture:
- Project Root:
- Project Editor Version:
- Git Branch:
- Working Tree:

## Unity CLI
- Before:
- After:
- Install Method:
- Status: PASS / FAILED / BLOCKED

## Existing Editor Patch Updates
| Before | After | Modules carried | Old version kept | Status |
|---|---|---|---|---|

## Latest Stable Editor
- Resolved latest:
- Installed:
- Modules:
- Project migrated: NO
- Status:

## Unity Skills
- Source: Unity-Technologies/skills
- Scope: project
- Installed/Updated skills:
- Lock/config files changed:
- Status:

## Unity Pipeline
- Before:
- After:
- Package: com.unity.pipeline
- Status:

## Unity MCP
- Client:
- Mode: project-local / global
- Server command: unity mcp
- Project pinned:
- Legacy MCP detected:
- Status:

## Live Connection
- Pipeline reachable:
- Editor state:
- Command catalog:
- Read-only smoke test:
- Status:

## Files Changed
- ...

## Warnings
- ...

## Manual Follow-ups
- ...

## Overall
PASS / PARTIAL / FAILED
```

---

# 13. 완료 조건

다음이 모두 만족되면 `PASS`로 종료한다.

- Unity CLI 최신
- 기존 Editor patch 최신
- 최신 stable Editor 별도 설치
- 현재 프로젝트 Editor version 강제 migration 없음
- Unity official skills 최신 동기화
- Pipeline 최신
- MCP가 `unity mcp` 기반으로 구성
- Editor 실행 시 Pipeline command catalog 접근 가능
- 기존 사용자 변경사항 손실 없음

일부 항목이 사용자 로그인, 라이선스, Editor 실행 여부 등으로 확인 불가하면 `PARTIAL`로 종료하고 정확한 차단 원인을 적는다.

절대로 확인하지 못한 항목을 성공했다고 추정하지 않는다.

---

# 참고: 2026-09-04 기준 확인된 최신 흐름

이 섹션은 **참고용 baseline**일 뿐이며 실행 시 다시 확인해야 한다.

- Unity CLI는 독립형 `unity` binary이며 Hub 없이도 Editor 설치/관리/자동화에 사용할 수 있다.
- Unity CLI에는 `unity editors upgrade`가 있어 설치된 Editor를 동일 `major.minor` line의 최신 공식 patch로 올릴 수 있다.
- Unity CLI에는 `unity mcp` 및 `unity mcp configure <client>`가 내장되어 있다.
- Unity Editor를 실제로 제어하려면 프로젝트에 `com.unity.pipeline`이 필요하다.
- `unity pipeline install`, `unity pipeline upgrade`, `unity pipeline list-versions`를 통해 Pipeline을 관리할 수 있다.
- Unity의 공식 Agent Skills 저장소는 `Unity-Technologies/skills`이다.
- 최신 Editor는 항상 `unity install latest`가 resolve하는 안정 채널을 먼저 검증한 뒤 설치한다.

공식 참고 URL:

- https://docs.unity.com/en-us/unity-cli
- https://docs.unity.com/en-us/hub/use-unity-cli
- https://github.com/Unity-Technologies/skills
- https://unity.com/blog/meet-the-unity-cli

# END OF MASTER PROMPT
