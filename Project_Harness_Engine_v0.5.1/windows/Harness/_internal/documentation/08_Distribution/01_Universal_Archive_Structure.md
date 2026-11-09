# Структура универсального архива Harness

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION BASELINE

## 1. Release package

```text
Project_Harness_Engine_v0.4.1.zip
Project_Harness_Documentation_v0.4.1.zip
```

Engine archive самодостаточен для Python 3.11+ и содержит нормативную документацию. Documentation archive поставляется отдельно для аудита и реализации расширений.

## 2. Физическая структура Core release

```text
Project_Harness_Engine_v0.4.1/
├── README.md
├── VERSION
├── CHANGELOG.md
├── IMPLEMENTATION_DECISIONS_v0.4.1.md
├── TEST_REPORT_v0.4.1.md
├── ENGINE_VALIDATION_v0.4.1.json
├── MANIFEST.sha256
├── project-harness.py
├── bin/project-harness
├── pyproject.toml
├── dist/
│   └── project_harness_engine-0.4.1-py3-none-any.whl
├── src/project_harness/
├── schemas/
├── registries/
│   ├── id_prefixes.yaml
│   ├── project_profiles.yaml
│   ├── statuses.yaml
│   ├── request_routing.yaml
│   ├── capabilities.yaml
│   └── contracts.yaml
├── skills/
├── templates/
│   ├── GPT_PREPARATION_INSTRUCTIONS.md
│   └── PROJECT_INPUT_FIELD_GUIDE.md
├── fixtures/
├── examples/
├── tests/
└── docs/Project_Harness_Documentation_v0.4.1/
```

Имена шести canonical registries одинаковы в distribution, `PROJECT_LOCK` и documentation package. Устаревшие aliases `ids.yaml`, `profiles.yaml` и `operations.yaml` не используются.

## 3. Semantic boundaries

Distribution содержит universal contracts, schemas, ACTIVE seed skills, deterministic compiler/runtime, fixtures и documentation. Он не содержит project-specific architecture, secrets, provider billing, token ledger или cost-based routing.

Browser GPT выполняет semantic analysis, но не редактирует registries и не назначает canonical IDs. Codex выполняет product tasks, но не управляет routing, approvals или следующей Task.

## 4. Entry points

```text
python project-harness.py <command>
project-harness <command>           # после установки wheel
python .harness/engine/project-harness.py <command>  # внутри handoff
```

Минимальные commands: `doctor`, `start-intake`, `check-intake`, `prepare`, `validate-handoff`, `validate-project`, `status`, `next`, `verify`, `complete`, `block`, `resume`, `demo`.

## 5. Installation modes

```text
LOCAL_TOOL
VENDORED_HARNESS
WORKSPACE_SHARED
CONTROL_REPOSITORY
```

Установка pin-ит distribution/schema/registry/profile/adapter/skill revisions в Project Lock и не обновляет существующий Project Instance молча.

## 6. Integrity

Release требует:

- SHA-256 manifest всех поставляемых файлов;
- safe ZIP paths без traversal и symlinks;
- registry/schema/skill doctor;
- greenfield и brownfield conformance suite;
- wheel install smoke test;
- reproducible documentation aggregates и release ZIP;
- отдельные SHA-256 files для downloadable archives.
