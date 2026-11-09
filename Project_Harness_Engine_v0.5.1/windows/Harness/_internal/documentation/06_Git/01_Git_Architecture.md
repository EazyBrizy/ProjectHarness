# Git architecture и repository discovery

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Git не является обязательным на этапе intent

Greenfield workspace может не иметь repository до Bootstrap Gate. Harness не создаёт repository, remote или initial commit без подтверждённого Bootstrap Plan и capability grant.

Для существующего проекта порядок discovery:

1. определить наличие `.git`;
2. определить root/worktree/submodule boundaries;
3. прочитать remotes;
4. определить canonical remote;
5. проверить default/current branch;
6. проверить read/fetch access;
7. отдельно проверить push permission только при соответствующем route;
8. определить monorepo/polyrepo;
9. запросить URL, только если remote отсутствует или неоднозначен.

## 2. Repository registry

```yaml
repositories:
  control:
    path: .
    remote: origin
    role: HARNESS_CONTROL
    default_branch: main
    allowed_capabilities:
      - FILESYSTEM_READ
      - FILESYSTEM_WRITE
  backend:
    path: services/backend
    remote: origin
    role: IMPLEMENTATION
    default_branch: main
```

Registry также содержит protected branches, commit/PR policy, CI requirements, ownership, data classification и compatibility relationships.

## 3. Base revision

Каждый task, Context Plan, Run и Change Pack фиксирует exact base revision. Выполнение на другой revision требует refresh, rebase decision или `REPLAN_REQUIRED`.

## 4. Existing dirty state

Harness не выполняет reset/clean автоматически. Changes классифицируются:

- owned by active task/run;
- unrelated user changes;
- generated stale artifacts;
- bootstrap work;
- unknown.

При конфликте используется отдельный worktree, scope reduction или `WAITING_DECISION`.

## 5. Greenfield bootstrap

Bootstrap Plan задаёт:

- repository count and roles;
- initialization order;
- default branches;
- initial directory layout;
- baseline files;
- first validation commands;
- commit and publication policy;
- cleanup при partial failure.

## 6. Branch naming

Baseline:

```text
harness/<task-id>-<slug>
fix/<task-id>-<slug>
docs/<task-id>-<slug>
bootstrap/<change-set-id>-<slug>
```

Project policy может задать другой deterministic pattern.
