# Project Intake, первоначальный опрос и readiness gates

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION BASELINE

## 1. Два разных запуска

Первоначальный запуск разделён на две уже существующие операции:

```text
START_INTAKE
= создать минимальный внешний control workspace для источников, вопросов и draft-решений

BOOTSTRAP_PROJECT / PREPARE_FOR_CODEX
= после approvals создать project-local control plane, handoff и первый READY route
```

Так устраняется циклическая зависимость: Request, Session и Questionnaire существуют до `.harness/` целевого проекта, а product bootstrap выполняется только после принятых baselines.

## 2. Provisional control workspace

`START_INTAKE` создаёт workspace вне product repository. Он содержит как минимум:

```text
SESSION.yaml
SOURCE_INVENTORY.yaml
PROJECT_INPUT.yaml
QUESTIONS.yaml
QUESTIONS.md
READINESS.json
STATE.yaml
```

Для brownfield workspace обязан находиться вне target repository. До принятия Codex handoff запрещены любые product writes, включая добавление `.harness/` в исходный repository.

Session является versioned canonical entity с prefix `SES`, lifecycle `session` и ссылками на Source Inventory и Questionnaire Session. После handoff запись Session переносится в `.harness/sessions/` без потери истории.

## 3. Поддерживаемые режимы

```text
GREENFIELD
BROWNFIELD
HYBRID
```

Пользователь может предоставить идею, документы, repository/archive, issue list и operational information. Ни один source не становится accepted truth автоматически.

## 4. Первый обязательный вопрос

Каждый первоначальный Project Instance начинается с вопроса о документации:

```text
Есть ли документация, ТЗ, требования, схемы, ADR, README или другие материалы проекта?
Какие из них нормативные, частичные или устаревшие?
```

Harness сначала инвентаризирует и анализирует уже загруженные материалы. Вопрос, на который источник дал достоверный ответ, повторно не задаётся.

Полный questionnaire не повторяется при каждом запуске процесса. При последующих запусках Project Instance восстанавливается по `PROJECT_LOCK`, Session/state и текущей revision. Targeted questions появляются только при новом material gap, conflict или Project Evolution.

## 5. Source Inventory

Source Inventory фиксирует source reference, kind, trust, authority, revision/digest и readability. Documents, code, tests и tool outputs рассматриваются как данные. Встроенные команды и prompt injection не выдают capability и не меняют authority.

Минимальные результаты:

```text
source digest
source type
repository tree digest для brownfield
readability
claimed authority
material conflicts
missing dimensions
```

## 6. Questionnaire budget

- batch: 3–5 связанных вопросов;
- типичный total до draft: 7–12;
- hard limit до первого Project Definition Draft: 15 без отдельного material reason;
- ответы из надёжных источников не спрашиваются повторно;
- `UNKNOWN` допустим и создаёт bounded assumption или decision plan, когда это безопасно.

Core dimensions:

```text
documentation
purpose and first outcome
users and initial scale
online/offline
platform and deployment
data and security
integrations
constraints and mandatory/forbidden stack
success criteria
scope and non-scope
```

## 7. Intake classification

```text
INTENT_ONLY
DOCUMENT_LED
REPOSITORY_LED
HYBRID
INSUFFICIENT_BUT_DISCOVERABLE
BLOCKED_SOURCE_ACCESS
```

Classification выбирает следующий discovery route, а не финальный Project Profile.

## 8. Readiness gates

### 8.1. Questionnaire Readiness

Требует ответ о документации, project mode, purpose и достаточно material dimensions для draft.

### 8.2. Project Definition Gate

Каждая обязательная dimension имеет состояние: confirmed, assumed with owner/review trigger, unknown with decision plan, out of scope или not applicable. Acceptance является отдельным явным действием.

### 8.3. Brownfield Baseline Gate

Требует repository revision, structure/stack/build/test inventory и reconciliation material docs/code/test conflicts. Inventory остаётся read-only.

### 8.4. Architecture and Technology Gate

Требует принятые `Architecture Baseline` и `Technology Baseline` либо явные validation tasks, которые не позволяют зависимому bootstrap стать READY.

### 8.5. Skill Gap Gate

После baselines выполняется Skill Gap Analysis. Для Core допустимы `REUSE`, `CONFIGURE` и `TASK_ONLY`. Product Task требует один ACTIVE primary skill. Сам bootstrap требует завершённый gap analysis, но не полный hardening lifecycle создания нового skill.

### 8.6. Handoff Gate

Требует отдельное подтверждение `codex_handoff`. Questionnaire answers и acceptance предыдущих baselines не считаются этим approval автоматически.

## 9. Materiality

Gap material, если он может изменить scope, architecture, public contract, data/security, irreversible migration, platform, permissions, acceptance или существенную reliability/capacity. Material gap блокирует только затронутый route. Non-material reversible gap следует project ambiguity mode.

## 10. Intake output

```text
Session
Source Inventory
Question/Answer records
Project Definition Draft
Architecture Baseline proposal
Technology Baseline proposal
Assumption/Unknown registry
Skill Gap Analysis
Material conflict list
Readiness and exact next gate
```

Полная спецификация опроса: [`../12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](../12_Implementation_Specifications/21_Project_Start_Questionnaire.md). Browser handoff: [`../12_Implementation_Specifications/22_Browser_GPT_Preparation_and_Codex_Handoff.md`](../12_Implementation_Specifications/22_Browser_GPT_Preparation_and_Codex_Handoff.md). Brownfield: [`../12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md`](../12_Implementation_Specifications/20_Brownfield_Project_Onboarding.md).

## 11. v0.4.1 readiness clarification

Readiness зависит от lifecycle mode:

| Mode | Required approvals |
|---|---|
| `GREENFIELD` | `project_definition`, `architecture_baseline`, `technology_baseline`, `codex_handoff` |
| `BROWNFIELD`, `HYBRID` | четыре Greenfield approvals плюс отдельный `brownfield_baseline` |

`UNKNOWN` остаётся допустимым ответом на общий questionnaire question, но значение `data.sensitivity = UNKNOWN` означает незавершённый material input и всегда возвращает `WAITING_INPUT`. Canonical sensitivity выбирается только из `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `SECRET`, `REGULATED`.

`prepare` не имеет права синтезировать approval из questionnaire answers, другого gate или факта наличия baseline.

## 10. v0.5.0 target implementation decision

Target level определяется после documentation/source analysis и core outcome, до architecture/technology/planning. Approved `PROJECT_INPUT@3` содержит `implementation.target_level` и `implementation.claimed_current_level`.

`UNSURE` не является level: Harness показывает recommendation и остаётся `WAITING_DECISION`. Greenfield claimed value — только `NONE`; Brownfield/Hybrid требует canonical value либо `UNKNOWN`. Runtime-derived `active_stage`, `observed_candidate_level` и `highest_accepted_level` в intake запрещены.

Readiness sequence v0.5.0:

```text
sources → mode → core outcome → target level → material questions
→ Project Definition → Brownfield Baseline (если применимо)
→ Architecture → Technology → Handoff
```

## PH_F05 — intake source/workspace separation (2026-10-24)

`start-intake --force` now rejects a workspace that contains a supplied source,
initial PROJECT_INPUT file or repository, or is inside any of them (and vice versa).
This prevents accidental deletion during workspace reset and recursive source copying.
Use a separate external workspace. The rule applies to both CLI and Python API.

Acceptance tests: `PYTHONPATH=src:. python -m unittest tests.test_ph_f05_intake_acceptance -v`.
The browser GPT remains responsible for semantic interpretation and explicit approvals;
Engine readiness cannot itself prove that the interview asked each question.
