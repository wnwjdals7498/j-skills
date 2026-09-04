# v1 → v2 지연 이관
`python3 <skill-dir>/scripts/migrate_v1.py [--docs-root <path>] <slug> [--apply]`

기본 실행은 변경 없는 dry-run이다. `--apply`를 붙이면 프로젝트 안 `.migration-v1-backup/<시각>/`에 원본을 복사한 뒤 변환하고, 마지막에 `sync`와 `doctor`를 실행한다.

## 변환

1. Item 태그 `V`, `J`, `TE`, `HF`를 `view`, `job`, `test`, `hotfix`로 바꾼다.
2. `Information.md`를 facts, `histories.md`를 decisions 6열 형식으로 합친다.
3. requirements·todos·plans·issues·Bugs 행을 backlog로 합치고 원 ID를 내용 앞에 남긴다.
4. `## 진행 메모`를 `## 재개`로 바꾸고 누락된 v1 부모 Work를 만든다.
5. 연결 가능한 handoff를 Item 재개 절에 넣고 `resources/derived/handoff-archive/`로 옮긴다. 연결할 수 없으면 원본을 남기고 경고한다.
6. worklog frontmatter를 보강하고 `<slug>__<class>__<item>.md`로 정규화한다.
7. `works.md`, `classifications.md`를 제거하고 `list_refs`를 새 facts·decisions·backlog ID로 바꾼다.

## 안전 규칙

- dry-run 출력과 대상 slug를 먼저 확인한다.
- 적용 시 생성된 backup 경로를 보존한다.
- 실제 데이터는 임의로 추정하지 않는다. 미해결 handoff 경고가 있으면 원문을 확인한다.
- 성공 판정은 명령 종료 코드와 마지막 `doctor: fail 0`이다.
