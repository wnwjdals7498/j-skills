# 수용·회귀 검증

변경 후 최소 검증:

```text
python scripts/validate_skill.py
python -m unittest discover -s tests -v
```

## 필수 시나리오

| 시나리오 | 합격 기준 |
|---|---|
| 콜드스타트 | `RESUME.md`만으로 다음 행동 1개와 주의점 1개 확인 가능 |
| 진입 | `new` → `add` → `start`, 세 단계 이내 착수 |
| 비정상 종료 | `start` → `note` → stale 조작 → 다른 session `lock reap`; 마지막 note와 비정상 종료 문구 유지 |
| 세션 종료 | `end --all --pause` 뒤 해당 session lock 0, RESUME 최신, doctor fail 0 |
| 무손실 compact | 이동 전후 `find <ID>` 결과 원문 동일 |
| 규칙 밀도 | `SKILL.md` 8000자 이하, 불변식 10개 이하, TODO scaffold 없음 |
| 병렬 안전 | 같은 Item 동시 start 중 하나만 0; 다른 Item은 둘 다 0 |
| 생성물 경합 | 동시 `sync` 호출이 모두 0이고 `graph.json`이 유효 |
| 완료 게이트 | `--result` 없는 done은 2; 자식 전부 Done이면 부모 자동 Done |
| 취소 안전 | 자식 있는 단위 skip은 2; leaf skip 후 doctor fail 0 |
| v1 이관 | dry-run 무변경, apply 후 진행 메모→재개, doctor fail 0 |
| 공용 경로 | 실제 폴더와 디렉터리 symlink/junction 양쪽에서 `--help`와 `validate_skill.py` 성공 |

테스트는 임시 `PMT_DOCS_ROOT`와 고정 `PMT_SESSION`을 사용한다. 실제 `~/docs`, 홈 스킬, 원격 서비스, Git 저장소를 건드리지 않는다. 시간 의존 테스트는 lock metadata의 heartbeat를 직접 과거로 바꾸고 sleep을 쓰지 않는다.
