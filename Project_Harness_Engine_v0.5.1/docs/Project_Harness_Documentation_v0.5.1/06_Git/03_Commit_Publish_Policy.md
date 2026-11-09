# Commit, push, PR и coordinated change sets

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Режимы политики

```text
REVIEW_ONLY
AUTO_COMMIT_AFTER_PASS
AUTO_PUSH_AFTER_PASS
DRAFT_PR_AFTER_PASS
```

Рекомендуемый baseline:

```text
AUTO_COMMIT_AFTER_PASS
NO_IMPLICIT_PUSH
```

Каждое действие дополнительно требует capability: `GIT_COMMIT`, `GIT_PUSH` или `PR_CREATE`.

## 2. Commit Plan

```yaml
commit_plan:
  id: CPL-TSK-BACKEND-040
  task_ref: TSK-BACKEND-040@3
  run_ref: RUN-20260806-0001
  repository_ref: REP-BACKEND-001
  branch: harness/tsk-backend-040-search
  base_revision: abc123
  files: []
  required_checks: []
  constraint_checks: []
  message: "feat(search): implement backend endpoint"
  sign: OPTIONAL
  capability_grant_ref: CGR-GIT-001
  push: false
  pull_request: false
```

`CPL` зарезервирован для Commit Plan. Context Plan использует prefix `CTX`.

## 3. Условия commit

- Task имеет eligible terminal result;
- required-now verification checks прошли;
- diff находится внутри ownership write set;
- unrelated/user changes не включены;
- secret/policy scans не выявили нарушения;
- Task Report, Run Trace и Evidence сохранены;
- documentation impact обработан;
- generated artifacts fresh;
- state transaction подготовлена;
- project policy и capability разрешают commit.

## 4. Push и PR

Push/PR — отдельная side-effect boundary. Перед действием Result/approval view показывает:

- remote и branch;
- commit set;
- required checks;
- protected-branch policy;
- approvals;
- PR mode;
- rollback/recovery route.

Bypass protected policy и implicit push запрещены.

## 5. Polyrepo

Абсолютной Git-атомарности между repositories нет. Используется coordinated change set:

```yaml
coordinated_change_set:
  id: CCS-2026-014
  project_revision: sha256:...
  commits:
    control: abc111
    backend: def222
    frontend: ghi333
  required_order: [backend, frontend, control]
  compatibility_window: "backend v2 совместим с frontend v1-v2"
  rollback_or_compensation: []
  integration_status: VERIFIED
```

## 6. Commit granularity

Один atomic Task обычно соответствует одному logical commit. Formatting noise, unrelated fixes, dependency upgrade и Harness maintenance не смешиваются с feature change. Multi-step migration сохраняет один change-set ID и explicit order.

## 7. Publication failure

Если local commit создан, а push/PR не выполнен:

- Task implementation result и evidence сохраняются;
- publication получает отдельный `FAILED_RECOVERABLE`/blocker route;
- commit не откатывается молча;
- пользователь видит exact recovery options;
- product task не переисполняется, если implementation уже подтверждена.
