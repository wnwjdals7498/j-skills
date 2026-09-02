# v1 → v2 지연 이관

프로젝트를 다시 열 때 하나씩 이관한다. 먼저 `migrate v1 <slug>`로 계획을 보고, 백업을 확인한 뒤 `--apply`를 붙인다. 엔진은 프로젝트 안 `.migration-v1-backup/`에 변경 전 파일을 보존하고 성공 후 `sync`와 `doctor`를 실행한다.

## 변환

1. Item 태그 `V`, `J`, `TE`, `HF`를 각각 `view`, `job`, `test`, `hotfix` kind로 바꾼다. 기존 파일명 체인은 유지한다.
2. `Information.md`를 `facts.md`, `histories.md`를 `decisions.md`로 옮긴다. requirements·todos·plans·issues·Bugs 행은 `backlog.md`로 합치고 원 ID를 내용 앞에 남긴다. Bugs의 `## 점검 특징`은 보존한다.
3. `## 진행 메모`를 `## 재개`의 한 것·다음·주의로 바꾼다. 갱신 시각은 기존 `updated`를 사용한다.
4. `handoff-*.md`는 연결 가능한 In Progress Item 재개 블록에 흡수하고 `resources/derived/handoff-archive/`로 이동한다. 자동 연결이 불가능하면 이동하지 않고 경고한다.
5. worklog에 frontmatter를 보강하고 `<slug>__<class>__<item>.md`로 정규화한다. 추정 불가 `issues`는 빈 목록과 경고를 남긴다.
6. `works.md`, `classifications.md`는 `index.md` 생성 후 원본을 백업 영역으로 옮긴다. frontmatter의 `null` 키는 제거한다.
7. 관계와 `list_refs`를 새 ID로 다시 쓴 뒤 `doctor` fail 0일 때만 적용 성공으로 본다.

## 안전 규칙

- 기본은 dry-run이며 파일을 바꾸지 않는다.
- 이미 v2 표식이 있는 프로젝트에는 재적용하지 않는다.
- 프로젝트 밖 파일과 기존 Git 저장소를 수정하지 않는다.
- 모호한 handoff 연결, 파싱 불가능 행, 이름 충돌은 임의 추정하지 않고 경고한다.
- 실제 v1 프로젝트가 없으면 합성 fixture 테스트 결과만 보고하고 실데이터 호환을 주장하지 않는다.
