# SAFETY_RULES — 파괴적 작업 금지 목록

> LOAD WHEN: 설치·삭제·설정 변경 등 부작용 있는 작업 직전. **S0 에서는 필수.**

---

## 1. 절대 금지 (사용자가 명시적으로 요청해도 재확인)

```
기존 Unity Editor 삭제
unity editors upgrade --replace
unity editors upgrade --remove-old
기존 AI Agent 설정 전체 덮어쓰기
기존 MCP 서버 설정 무단 삭제
Packages/manifest.json 직접 수동 편집
ProjectSettings/ProjectVersion.txt 직접 편집
git reset --hard
git clean -fd
Git working tree 변경사항 삭제
사용자 파일 삭제
프로젝트 전체 재생성
Assets/ 하위 대량 삭제
```

`manifest.json` 은 **반드시 `unity pipeline install` / `unity package` 등 CLI 를 통해서만** 변경한다.

---

## 2. 프로젝트 Editor 버전 보존

**최신 Editor 를 설치하는 것**과 **현재 프로젝트의 Editor 버전을 바꾸는 것**은 별개다.

- 최신 Editor 는 **side-by-side** 로 설치한다.
- `ProjectVersion.txt` 를 임의로 수정하지 않는다.
- 현재 프로젝트를 새 `major.minor` Editor 로 강제 오픈하지 않는다.
- 같은 `major.minor` 라인의 **패치 업데이트만** `unity editors upgrade` 로 수행한다.
- major.minor 마이그레이션은 **별도 작업 + 사용자 승인** (`ESCALATION.md` RISK).

---

## 3. Dry-run 우선

지원되는 작업은 실제 변경 전에 dry-run 또는 조회를 먼저 한다.

```bash
unity upgrade --dry-run --format json
unity editors upgrade --all --dry-run --format json
unity install latest --dry-run --format json
unity mcp configure <client> --dry-run
```

dry-run 결과에서 아래를 확인한 뒤에만 실제 실행한다.
- 현재 버전 / 대상 버전
- 변경될 파일
- 예상 설치 대상 및 용량

---

## 4. 실패를 숨기지 않는다

명령이 실패하면:

1. exit code 를 기록한다.
2. stderr 핵심 내용을 **원문 그대로** 기록한다.
3. 자동으로 위험한 우회 방법을 적용하지 않는다.
4. 가능한 공식 진단 명령을 수행한다 (`unity doctor`, `unity diagnose update`).
5. 해당 단계를 `FAILED` 또는 `BLOCKED` 로 표시한다.
6. 하위 단계가 이 단계에 의존하면 **무리해서 진행하지 않는다.**

**확인하지 못한 항목을 성공으로 추정하지 않는다.**

---

## 5. 변경 전 스냅샷

실제 변경 직전에 아래 파일들의 현재 상태를 확보한다 (diff 가능하도록).

```
Packages/manifest.json
Packages/packages-lock.json
ProjectSettings/ProjectVersion.txt
skills-lock.json
.agents/
.claude/
.cursor/
.vscode/
```

Git 프로젝트면:

```bash
git status --short
git branch --show-current
git rev-parse --show-toplevel
```

working tree 가 dirty 여도 **사용자 변경사항을 지우지 않는다.**
변경 예정 파일이 이미 수정되어 있으면 반드시 기록하고 보고한다.

---

## 6. 자격증명 취급

- 비밀번호 / 토큰 / 라이선스 키를 **로그에 출력하지 않는다.**
- 프롬프트에 그대로 노출하지 않는다.
- Git 에 저장하지 않는다.
- 로그인이 필요하면 `ESCALATION.md` 의 MANUAL 형식으로 사용자에게 넘긴다.

---

## 7. 중복 설치 방지

- 동일 CLI 를 여러 경로에 중복 설치하지 않는다.
- 최신 안정 Editor 가 **이미 설치되어 있으면 재설치하지 않는다.**
- 불필요한 `--force` 를 쓰지 않는다.
- 모든 build module 을 무조건 설치하지 않는다. 용도를 모르면 core 만 설치하고 보고한다.
