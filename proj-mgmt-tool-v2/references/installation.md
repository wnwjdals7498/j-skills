# PMT 스킬 설치·호출 참고

## 도구별 경로

Codex와 Claude Code는 같은 스킬 실물과 `~/docs`를 사용한다. 복사본을 따로 관리하지 않는다.

| 환경 | 스킬 링크 | 원천 |
| --- | --- | --- |
| Unix 기존 구성 | `~/.codex/skills/proj-mgmt-tool → ~/.claude/skills/proj-mgmt-tool` | `~/j-skills/proj-mgmt-tool-v2` |
| Windows Codex | `%USERPROFILE%\.codex\skills\proj-mgmt-tool-v2` 디렉터리 링크 | 현재 `j-skills/proj-mgmt-tool-v2` 폴더 |

Windows에서는 링크 대상의 실제 경로를 확인한다. 이 설치는 Claude Code 경로를 자동으로 만들지 않는다. Codex에서 자동 발견이 안 되면 다음 턴에 스킬 목록을 다시 읽고, `SKILL.md`를 명시적으로 읽어 사용한다.

## 호출 함정

1. `--session`을 명시한다. lock은 실행 세션에 묶이므로 `start`와 `end`를 같은 방식으로 호출한다.
2. `add item`은 `WorkN-1`을 만든다. 별도 이름 관례로 개명하면 파일명과 `id:`를 함께 바꾸고 엔진의 다음 번호 인식을 확인한다.
3. `## 완료 기준`이 비어 있으면 `verify`가 거부된다. `start` 뒤 기본 내용·범위·완료 기준을 먼저 채운다.
4. 셸에서 긴 `--result`·`--context`를 전달할 때 명령 치환 문법과 인용을 확인한다. Windows에서는 PowerShell 인수 전달을 검증한다.
5. `repositories[0]` 외 저장소에서 검증했다면 결과문에 실제 커밋 SHA를 적는다.
