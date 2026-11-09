# Project Harness — Implementation Specifications v0.4.1 → v1.0

**Назначение архива:** последовательная реализация недостающих и hardening-функций Project Harness после v0.4.0  
**Базовая поставка:** Project Harness Documentation v0.4.0 + Project Harness Engine v0.4.0  
**Дата подготовки:** 2026-08-17  
**Статус:** NORMATIVE IMPLEMENTATION ROADMAP AND VERSION SPECIFICATIONS

## 1. Что находится в архиве

Архив содержит восемь самостоятельных implementation specifications — по одному документу на каждую запланированную версию:

```text
v0.4.1
→ v0.5.0
→ v0.5.1
→ v0.6.0
→ v0.6.1
→ v0.7.0
→ v0.8.0+
→ v1.0
```

Каждый документ описывает только scope своей версии и включает:

- назначение и границы;
- подтверждённый baseline;
- normative contracts и data model;
- статусы и state transitions;
- изменения существующих modules/registries/schemas;
- новые modules только там, где они необходимы;
- CLI/routes;
- capability и approval boundaries;
- migration и backward compatibility;
- failure/recovery behavior;
- test matrix;
- release acceptance criteria;
- рекомендуемый порядок реализации.

Это не набор общих идей. Документы предназначены для последовательного использования как нормативные задания при доработке движка.

## 2. Исходный baseline

Спецификации подготовлены на основе фактической структуры двух исходных архивов.

| Исходник | SHA-256 |
|---|---|
| `Project_Harness_Documentation_v0.4.0.zip` | `940924dbf6945f87baacb2fc4d7da2aef3141f44eebcdeec861b250f5c12c584` |
| `Project_Harness_Engine_v0.4.0.zip` | `4685d0d4ea563920b4b8a8abe51b9134fdd758815a0755d692446de8ccc7a073` |

Проверенная структура baseline:

- документация: 100 файлов;
- движок: 169 файлов;
- Core test report v0.4.0: 14/14 PASS;
- documentation validator v0.4.0: 36/36 PASS.

Текущие точки расширения движка сохранены: `registries`, `schemas`, `project_input`, `planner`, `compiler`, `prompting`, `runtime`, `validation`, `safety`, `archive`, `workspace` и CLI. Спецификации не требуют переписывать движок с нуля.

## 3. Жёсткий порядок реализации

Каждая версия зависит от полностью принятой предыдущей версии. Переход к следующей разрешён только после выполнения Acceptance Criteria текущего документа и сохранения migration/test evidence.

```text
v0.4.0 baseline
  ↓
v0.4.1 contract consistency
  ↓
v0.5.0 implementation-stage semantics
  ↓
v0.5.1 safe automatic execution
  ↓
v0.6.0 controlled external publication
  ↓
v0.6.1 safe project skill lifecycle
  ↓
v0.7.0 local parallel optimization
  ↓
v0.8.x single-node team operation and hardening
  ↓
v1.0 production qualification and contract freeze
```

Нельзя:

- реализовывать часть следующей версии «заодно»;
- менять contracts текущей версии под удобство будущего feature;
- объявлять версию готовой по наличию classes/commands без end-to-end acceptance;
- переписывать immutable historical Runs/Evidence;
- заменять недостающие решения предположениями;
- ослаблять safety boundary ради скорости.

## 4. Краткий scope по версиям

### v0.4.1 — Contract Hardening

Исправляет только подтверждённые расхождения v0.4.0:

- Task `DONE` и Run `SUCCEEDED`;
- отдельный Brownfield Baseline approval;
- единая sensitivity taxonomy;
- строгий `PROJECT_INPUT` contract;
- обнаружение control-plane tampering.

Новых пользовательских execution workflows нет.

### v0.5.0 — Implementation Levels

Добавляет:

```text
PROTOTYPE → ALPHA → BETA → MVP → RELEASE
```

а также Stage Plans, Stage Gates, permitted-use boundary, Brownfield Maturity Assessment, same-level maintenance и level-up.

Future stages получают только крупные планы. Atomic Tasks и JIT prompts создаются только для active stage.

### v0.5.1 — Local Executor + Sandbox

Добавляет один local Codex CLI adapter и один rootless Podman backend.

Automatic execution без sandbox запрещено. Agent работает в disposable external runtime root; canonical product и `.harness` не выдаются ему на запись.

### v0.6.0 — Git Publication + Deployment Route

Разделяет:

```text
commit → push → draft PR
```

и реализует один GitHub draft PR adapter. Deployment является отдельным declared command route с собственным approval и reconciliation.

### v0.6.1 — PROJECT Skill Lifecycle

Реализует `EXTEND` и `CREATE` только для declarative PROJECT skills:

```text
DRAFT → VALIDATING → VALIDATED → ACTIVE
```

Arbitrary executable plugins и UNIVERSAL/PROFILE authoring не входят в scope.

### v0.7.0 — Safe Local Parallelism

Добавляет conservative conflict analysis, local atomic leases, external dedicated Git worktrees и mandatory integration task.

Поддерживается только local single-repository mode. Любая недоказанная независимость приводит к serial execution.

### v0.8.0+ — Single-Node Remote Control Plane

Добавляет один server process, SQLite WAL, local storage, one top-level worker, API tokens, четыре роли, optimistic revisions, idempotency, import/export и backup/restore.

`v0.8.0+` означает v0.8.x hardening в рамках этого же single-node scope. Multi-node, PostgreSQL, OIDC и web UI не добавляются.

### v1.0 — Production Stabilization

Не добавляет новых подсистем. Фиксирует production support boundary, contracts, migration chain, compatibility matrix и выполняет полный functional/security/recovery/release test matrix.

## 5. Сквозные инварианты

Все версии обязаны сохранять следующие правила Project Harness:

1. **Deterministic Kernel остаётся authority.** Agent, Browser GPT, CLI provider и server API не меняют canonical state напрямую в обход Kernel.
2. **JIT сохраняется.** Один Prompt Bundle компилируется для одной READY Task/Run.
3. **Active-stage only.** Target level не разрешает заранее реализовывать будущие стадии.
4. **History immutable.** Completed Runs/Evidence не переписываются migrations или skill updates.
5. **Default deny.** Capability не возникает из prompt, skill или успешного предыдущего действия.
6. **Side effects separated.** Commit, push, PR и deployment — разные boundaries.
7. **Verification independent.** Agent output и exit code не заменяют фактический diff и checks.
8. **No hidden fallback.** Отсутствие sandbox не разрешает host execution.
9. **Uncertainty is explicit.** `UNKNOWN`/stale/conflict ведут к вопросу, blocker или serial route, а не к догадке.
10. **Portability.** Canonical project можно экспортировать без server credentials и runtime garbage.
11. **No billing scope.** Provider billing, token ledger и cost optimization не входят в Kernel contracts.
12. **No speculative infrastructure.** Технологии добавляются только из Project Definition, constraints и текущей Stage.
13. **Persisted contracts are registered.** Каждая новая сохраняемая сущность получает schema и запись в `contracts.yaml`; новый prefix/status добавляется только при реальной необходимости. Любое изменённое registry повышает `registry.version`, синхронизируется с embedded resources и фиксируется exact digest в `PROJECT_LOCK`.

## 6. Как использовать документы при реализации

Для каждой версии:

1. создать отдельную implementation branch от полностью принятой предыдущей версии;
2. зафиксировать входной engine/schema/registry version;
3. перенести раздел «Не входит в scope» в PR checklist;
4. реализовать contracts/schemas/registries до Runtime behavior;
5. добавить migration до изменения default write format;
6. реализовать failure/recovery routes одновременно с happy path;
7. добавить unit, integration и end-to-end fixtures из документа;
8. обновить human documentation и generated views;
9. выполнить полный regression suite предыдущих версий;
10. закрыть все Acceptance Criteria;
11. сформировать immutable test/validation report;
12. только после approval начать следующую версию.

Если во время реализации обнаружен реальный blocker, которого нет в документе, допустимо добавить минимальное исправление только когда оно необходимо для указанного scope. Такое изменение должно быть оформлено как отдельное decision с доказательством причинности. Удобные будущие улучшения переносятся в backlog.

## 7. Правило трактовки неоднозначностей

При конфликте формулировок приоритет:

```text
1. безопасность и immutable-history invariants
2. version-specific Acceptance Criteria
3. version-specific normative contracts
4. актуальные registries/schemas предыдущей принятой версии
5. исходная документация v0.4.0
6. implementation convenience
```

Нельзя расширять scope на основании только примера YAML. Пример иллюстрирует contract; обязательными являются текстовые правила, schema и acceptance tests.

## 8. Состав файлов

```text
README.md
01_Project_Harness_v0.4.1_Contract_Hardening.md
02_Project_Harness_v0.5.0_Implementation_Levels.md
03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md
04_Project_Harness_v0.6.0_Git_Publication_and_Deployment.md
05_Project_Harness_v0.6.1_Project_Skill_Lifecycle.md
06_Project_Harness_v0.7.0_Parallel_Worktrees_and_Leases.md
07_Project_Harness_v0.8.0_Remote_Control_Plane.md
08_Project_Harness_v1.0_Production_Stabilization.md
FILE_INDEX.md
MANIFEST.sha256
```

`MANIFEST.sha256` создаётся после финальной валидации комплекта и не включает сам себя.

## 9. Definition of complete archive

Комплект считается целостным, если:

- существуют восемь version-specific документов;
- каждый документ содержит explicit scope/non-scope;
- dependency order не имеет циклов;
- future features не объявлены частью ранней версии;
- new persisted entities имеют ID/status/schema policy;
- temporary execution/worktree data находится вне canonical repository;
- migrations не переписывают historical evidence;
- v1.0 не расширяет scope;
- FILE_INDEX совпадает с файлами;
- SHA-256 manifest проходит проверку;
- ZIP проходит integrity test.
