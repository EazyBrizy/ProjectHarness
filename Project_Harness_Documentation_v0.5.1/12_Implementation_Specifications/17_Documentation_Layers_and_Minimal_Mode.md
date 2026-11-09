# Слои документации и режимы materialization

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness использует богатую machine-readable модель, но пользователь и Codex не должны постоянно читать десятки внутренних сущностей. Документация разделяется на понятный human layer и machine/control layer.

## 2. Human-readable layer

Рекомендуемый минимум проекта:

```text
PROJECT.md
ARCHITECTURE.md
TECHNOLOGY.md
ROADMAP.md
STATUS.md
DECISIONS/
TASK_REPORTS/
```

| Документ | Содержание |
|---|---|
| `PROJECT.md` | Цели, пользователи, scope, ограничения, success criteria. |
| `ARCHITECTURE.md` | Компоненты, границы, потоки, contracts и links to ADR. |
| `TECHNOLOGY.md` | Принятый stack, versions, compatibility and rationale. |
| `ROADMAP.md` | Work Packages, causal layers, milestones and current route. |
| `STATUS.md` | Что сделано, что blocked, next step, outstanding decisions. |
| `DECISIONS/` | Material ADR. |
| `TASK_REPORTS/` | Краткие проверяемые результаты выполненных задач. |

Эти документы генерируются или синхронизируются из canonical state, но допускают curated explanatory text с source mapping.

## 3. Machine/control layer

```text
.harness/
├── config/
├── registries/
├── intake/
├── canonical/
├── work-packages/
├── tasks/
├── prompts/
├── context/
├── skills/
├── runs/
├── evidence/
├── blockers/
├── changes/
├── events/
├── state/
└── generated/
```

`.harness/` является control plane. Пользователь обычно взаимодействует через single entry and generated views, а не редактирует state вручную.

## 4. Documentation modes

```text
MINIMAL
STANDARD
MULTI_REPO
REGULATED
```

### 4.1. MINIMAL

Для небольшого проекта:

- `PROJECT.md` объединяет project definition and basic technology;
- `ARCHITECTURE.md` только при material architecture;
- `ROADMAP.md` и `STATUS.md` обязательны;
- ADR только для material decisions;
- machine contracts сохраняются полностью;
- task reports могут агрегироваться по Work Package.

### 4.2. STANDARD

Default:

- все базовые human documents;
- отдельные ADR;
- task reports для executable tasks;
- requirements/coverage views;
- full trace/evidence digests.

### 4.3. MULTI_REPO

Добавляет:

- repository map;
- ownership and cross-repo contracts;
- coordinated change sets;
- integration/release order;
- per-repository status views.

### 4.4. REGULATED

Добавляет:

- formal approvals;
- stricter retention;
- data classification and audit exports;
- waiver register;
- independent validation and separation of duties;
- controlled document revisions.

Режим влияет на количество materialized views/gates, но не ослабляет semantics Task Contract, constraints, evidence или permissions.

## 5. Source of truth

```text
Canonical machine entity
→ human-readable synchronized document
→ generated summary/status
```

Generated `STATUS.md` или combined guide не становится canonical source. Ручное изменение generated file либо запрещается, либо импортируется как Change Pack candidate.

## 6. Избежание дублирования

Нормативное правило определяется один раз и переиспользуется ссылкой. Например, запрет billing/token accounting хранится в scope/non-goals и schema tests, а не копируется в каждом документе.

Documentation build должен поддерживать:

- transclusion/concatenation для общего руководства;
- source maps;
- link/anchor validation;
- duplicate normative statement warnings;
- version and metadata generation.

## 7. Общая пользовательская документация

Комплект публикует два агрегата:

```text
Project_Harness_User_and_Implementation_Guide_v0.4.1.md
Project_Harness_Architecture_v0.4.1_FULL.md
```

Первый объединяет реализационные спецификации 01–21. Второй объединяет весь комплект. Оба генерируются, а не редактируются независимо.

## 8. Generated project views

После intake Harness создаёт:

```text
PROJECT.md          accepted definition and assumptions
ARCHITECTURE.md     accepted architecture and contracts
TECHNOLOGY.md       accepted stack and compatibility
ROADMAP.md          work packages and DAG layers
STATUS.md           current result, blockers and next route
AGENTS.md           compact executor guidance
```

Каждый generated view содержит:

- generated timestamp;
- source revision/hash;
- «do not edit directly» marker либо import policy;
- source entity refs.

## 9. Пользовательский язык

Human layer обязан:

- объяснять термины при первом использовании;
- показывать последствия вариантов;
- не требовать знания internal enums;
- отделять «принято», «предполагается» и «неизвестно»;
- показывать current status and next step в начале `STATUS.md`;
- не скрывать blockers за техническим stack trace.

## 10. Документирование мелких задач

Мелкая task не обязана создавать новый Markdown-файл. Достаточно:

- Task Report record;
- обновления существующего раздела, если impact есть;
- event/evidence;
- generated status refresh.

Это предотвращает избыточное число документов.

## 11. Build pipeline

```text
Validate canonical schemas
→ resolve registries and references
→ render human views
→ render combined guides
→ validate links/anchors/examples
→ run semantic documentation tests
→ generate FILE_INDEX and checksums
→ package archive
```

## 12. Критерии приёмки

1. Human layer понятен без просмотра `.harness/` internals.
2. Machine layer сохраняет полную traceability.
3. MINIMAL не меняет core semantics.
4. Общие руководства генерируются из отдельных files.
5. Нормативные правила не дублируются бесконтрольно.
6. Generated views имеют source revisions/maps.
7. Мелкие tasks не создают искусственные документы.
8. STATUS всегда содержит текущий результат, blockers and exact next route.
