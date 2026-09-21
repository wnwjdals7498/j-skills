# J Skills

개인 개발 워크플로에서 재사용하는 Codex·Claude Code용 스킬 모음입니다. 각 스킬은 독립적으로 설치하거나 참조할 수 있으며, 실행 규칙과 검증 기준을 Markdown으로 관리합니다.

## 포함된 스킬

| 스킬 | 용도 | 핵심 산출물 |
| --- | --- | --- |
| [`claude-codex-workflow`](./claude-codex-workflow/SKILL.md) | Claude Fable 계획과 Codex Sol/Terra 구현·검증을 토큰 우선 균형형으로 조정 | 환경 캡슐, 간결 계획, 단계별 검증, 로컬 커밋 |
| [`codex-handoff`](./codex-handoff/SKILL.md) | 계획 태스크를 Codex 실행자에게 인라인 또는 큐 방식으로 전달 | 태스크별 실행·검증 결과와 핸드오프 센티널 |
| [`project-debate`](./project-debate/SKILL.md) | 상충하는 선택지를 A·B·C 역할로 검토하고 근거 기반 결정을 정리 | 회차별 주장·반박 기록과 정량 근거 보고서 |
| [`proj-mgmt-tool-v2`](./proj-mgmt-tool-v2/SKILL.md) | 장기 작업의 상태·결정·검증 기록을 로컬 문서로 관리 | 프로젝트 재개 정보, 작업 이력, 검증 기록 |

## 원칙

- 외부 사실은 공식 출처, 프로젝트 사실은 코드·설정·테스트 같은 직접 자료로 확인합니다.
- 사실·추정·의견·미확인을 구분합니다.
- 완료는 변경 자체가 아니라 검증 가능한 증거로 판단합니다.

## 빠른 확인

```powershell
python proj-mgmt-tool-v2/scripts/validate_skill.py
python proj-mgmt-tool-v2/scripts/pmt.py --help
```

## 설계 문서

- [`ai-collaboration-discussion-design.md`](./ai-collaboration-discussion-design.md): 협업 토론 스킬의 초기 설계
- [`project-debate/SKILL.md`](./project-debate/SKILL.md): 현재 실행 규칙
- [`proj-mgmt-tool-v2/SKILL.md`](./proj-mgmt-tool-v2/SKILL.md): 로컬 프로젝트 관리 규칙

## 포트폴리오 페이지 초안

[`portfolio-pages`](./portfolio-pages/)에는 GitHub Pages용 Markdown 초안을 둡니다. 이 폴더를 별도 `username.github.io` 저장소의 루트에 복사한 뒤 Pages를 활성화하면 됩니다.
