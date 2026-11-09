# Модели размещения и репозиториев

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Локальная модель baseline

- Kernel запускается локально как CLI/library.
- Project instance хранится в control repository.
- Worktrees, caches и ephemeral run data находятся вне canonical source tree либо в ignored runtime area.
- Постоянный сервер не обязателен.
- Network capability выдаётся только конкретным tasks/tools.
- Credentials предоставляются через внешний secrets mechanism, а не canonical files.

## 2. Greenfield single repository

На этапе bootstrap Harness создаёт control plane и product skeleton в одном repository, если architecture decision не требует иного.

## 3. Monorepo

`.harness/` находится в root. Repository registry содержит один logical repository с component ownership и path scopes.

## 4. Polyrepo

Используется control repository:

```text
harness-control/
├── .harness/
└── project-docs/

service-a/
service-b/
infrastructure/
```

Canonical state не дублируется. Implementation repositories содержат adapter bootstrap и ссылку на exact control revision.

## 5. Offline/vendored mode

- distribution и dependencies импортируются заранее;
- project lock фиксирует exact digests;
- model/tool profiles ограничиваются локально доступными;
- update packages проходят quarantine;
- runtime не предполагает обязательные внешние API.

## 6. Возможная централизованная модель

Локальный daemon или MCP-compatible service может координировать несколько projects, но canonical state остаётся экспортируемым, versioned и не зависит от доступности сервера.
