# PIPELINE_STATE

> 에이전트가 매 스테이지 종료 시 갱신한다.
> **새 세션에서 "이어서 해줘" 라고 하면 이 파일만 읽어도 어디서부터인지 알 수 있어야 한다.**

---

## 프로젝트

```yaml
project_name: {NAME}
project_root: {PATH}
kit_root: {KIT_ROOT}
profile: 3d            # 3d | 2d
mode: greenfield       # greenfield | rebase
render_pipeline: URP
unity_version: {VERSION}
mcp_client: {CLIENT}
updated_at: {ISO8601}
```

---

## 현재 위치

```yaml
active_track: none     # none | S0 | V | C
active_stage: S0
status: NOT_STARTED    # NOT_STARTED | IN_PROGRESS | PASS | PARTIAL | BLOCKED | FAILED
blocked_reason: null
awaiting_user: null    # 사용자 답을 기다리는 질문 요약
```

---

## 스테이지 진행

### S0 BOOTSTRAP
```yaml
status: NOT_STARTED
unity_cli: null
project_editor: null
latest_editor_installed: null
skills_synced: null
pipeline_package: null
mcp_configured: null
kit_applied: false
live_connection: null
blockers: []
```

### V 트랙 (비주얼)
```yaml
V1_concept_decomposition:
  status: NOT_STARTED
  concept_master: null
  spec_approved_at: null
  undefined_items: []
V2_visual_foundation:
  status: NOT_STARTED
  scene: null
  master_shader: null
  scorecard: {}
V3_blockout:
  status: NOT_STARTED
  iterations: 0
  scorecard: {}
V4_golden_scene:
  status: NOT_STARTED
  approved_at: null
  scorecard: {}
V5_asset_strategy:
  status: NOT_STARTED
  asset_strategy: []
  cc0_pack: null
  missing_count: 0
V6_gameplay_migration:
  status: NOT_STARTED       # greenfield 면 SKIPPED
  migrated_objects: 0
V7_full_migration:
  status: NOT_STARTED
  scenes_migrated: []
  scenes_remaining: []
```

### C 트랙 (코드)
```yaml
active_task: null           # TASK-0007
tasks:
  - id: TASK-0007
    title: null
    stage: C1               # C1~C6
    status: NOT_STARTED
    risk_level: null
    verification_level: []
    commits: []
    pushed: false
```

---

## 결정 기록 (같은 질문을 다시 하지 않기 위해)

```yaml
decisions:
  # - key: profile
  #   value: 3d
  #   decided_at: {ISO8601}
  #   scope: project
  # - key: night_lighting
  #   value: out_of_scope
  #   decided_at: {ISO8601}
  #   scope: V1
```

**결정이 뒤집히면** 영향받는 스테이지를 `INVALIDATED` 로 표시하고 어디부터 재작업인지 기록한다.

---

## 가정 기록 (ASSUME)

```yaml
assumptions:
  # - key: attack_cooldown
  #   value: 0.4
  #   basis: "기존 DashAbility.cooldown=0.5 와 동급 스케일"
  #   location: "Assets/Scripts/Combat/CombatModel.cs:12"
  #   confirmed: false
```

---

## 미해결 항목

```yaml
visual_missing: []          # MISSING_ 오브젝트 목록
manual_followups: []        # 사용자 수동 확인 필요
open_questions: []          # 답을 기다리는 질문
```
