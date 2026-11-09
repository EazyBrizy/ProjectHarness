# Миграция Project Harness v0.3.1 → v0.4.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE MIGRATION GUIDE

## 1. Назначение

Миграция не меняет project-agnostic идею Harness. Она устраняет структурные блокеры и связывает документацию с исполняемым Core runtime.

## 2. Startup migration

Старая неявная последовательность:

```text
questionnaire needs .harness
→ .harness needs bootstrap
→ bootstrap needs accepted questionnaire and skills
```

заменяется на:

```text
START_INTAKE
→ external provisional workspace
→ accepted baselines and Skill Gap Analysis
→ prepare / bootstrap generated handoff
→ project-local .harness
```

Для brownfield provisional workspace обязан находиться вне исходного repository.

## 3. Registry migration

`statuses` повышен до v3 и включает lifecycle groups `session` и `architecture_baseline`.

`contracts` повышен до v2 и включает:

- `session`;
- `architecture_baseline`;
- `project_lock`;
- `skill_registry_index` как reproducible generated artifact.

`PROJECT_LOCK.registry_versions` использует точные имена:

```text
id_prefixes
project_profiles
statuses
request_routing
capabilities
contracts
```

## 4. Skill migration

Project start больше не трактуется как автоматическое создание project-specific skills. Сначала выполняется resolution:

```text
REUSE
CONFIGURE
TASK_ONLY
```

`CREATE` и `EXTEND` требуют отдельного hardening lifecycle и не выполняются Core compiler.

## 5. Prompt migration

Все Task Contracts, Prompt Plans, Context Plans и Verification Profiles могут быть подготовлены заранее. Compiled Prompt Bundle создаётся только для текущей READY task. Ранее созданные future compiled prompts должны быть удалены или считаться stale.

## 6. Browser GPT handoff

Добавлен новый route:

```text
PREPARE_FOR_CODEX
```

Browser GPT заполняет semantic `PROJECT_INPUT.yaml`, но ID, revision, DAG validation, lock, manifest и ZIP формирует executable engine.

## 7. Core/hardening boundary

Core release больше не зависит от:

- parallel worktrees;
- full skill authoring lifecycle;
- Git publication;
- full Change Pack maintenance plane;
- multiple advanced Test Environment strategies.

Эти механизмы остаются целевой архитектурой, но реализуются после рабочего single-task loop.

## 8. Compatibility action

Для существующего v0.3.1 Project Instance рекомендуется:

1. сохранить исходный repository и `.harness` backup;
2. создать новый external intake workspace;
3. импортировать подтверждённые Project Definition и baselines;
4. пересобрать `PROJECT_LOCK` exact registry names/digests;
5. пересоздать generated skill index;
6. проверить task DAG;
7. скомпилировать только текущую READY task;
8. выполнить `validate-project`.

Автоматическая in-place migration старых runtime states в v0.4.0 не заявлена; используется controlled re-handoff.
