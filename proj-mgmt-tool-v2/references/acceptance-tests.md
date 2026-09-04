# 수용·회귀 검증

변경 후 다음을 실행한다.

```text
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests -v
```

## 필수 시나리오

| 시나리오 | 합격 기준 |
|---|---|
| 콜드스타트 | `RESUME.md`가 4,500자 이하고 다음 행동·주의 절을 포함하며 Item 하나만 추가로 읽어 재개 가능 |
| 비정상 종료 | 다른 세션의 stale lock을 `start`가 자동 회수하고 재개 절의 비정상 종료 문구와 이전 기록을 보존 |
| 검증 게이트 | 성공 검증이 없으면 `--unverified` 필수, 현재 검증 뒤 완료 가능, 새 commit 뒤 `start`가 재검증 필요 출력 |
| 결정 체인 | 두 번 supersedes 뒤 `find --chain`이 전체 계보 출력, RESUME은 승인만 표시, compact 뒤 archive에서도 조회 |
| 병렬 | 같은 Item 동시 `start` 중 하나만 0, 여러 `--repo` lock은 경로 정렬 획득과 실패 시 되돌리기 |
| 체크포인트 보강 | heartbeat를 40분 전으로 바꾸면 공통 경고와 다른 Item 전이 게이트가 동작하고 `note` 뒤 착수 가능 |
| 규모 | `SKILL.md` 4,000자 이하, `pmt.py` 2,000줄 이하, 공개 명령 12개, 최악 RESUME 4,500자 이하 |

테스트는 임시 `--docs-root`를 사용한다. 시간 조건은 lock JSON의 heartbeat를 직접 바꾸며 `sleep`을 쓰지 않는다. 실제 `~/docs`, 원격 서비스, 사용자 Git 저장소를 수정하지 않는다.
