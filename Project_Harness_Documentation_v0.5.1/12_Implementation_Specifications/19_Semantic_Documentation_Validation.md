# Semantic documentation validation

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Проверка ссылок и checksum недостаточна. Documentation CI должен обнаруживать смысловые расхождения: неизвестные enum, разные profile lists, entity без contract catalog binding, lifecycle/status mismatch, неканонические field aliases, capability вне registry, конфликтующие roadmap IDs и route без Result Envelope.

## 2. Validator pipeline

```text
Parse metadata and Markdown structure
→ load machine registries
→ extract declared entities/enums/contracts
→ resolve internal links and stable anchors
→ run semantic rules
→ build combined documents
→ compare generated/index/checksum outputs
→ emit Validation Report
```

## 3. Обязательные semantic rules

```text
SEM-001 Every declared enum value exists in a registry.
SEM-002 Every canonical entity has a schema or explicit internal-only marker.
SEM-003 Every lifecycle entity has allowed transitions.
SEM-004 Every persistent entity has a storage path and revision policy.
SEM-005 Every ID prefix exists and is unambiguous.
SEM-006 Every profile reference exists in Profile Registry.
SEM-007 Every generated artifact declares canonical sources and retention.
SEM-008 Every user-facing route returns Result Envelope.
SEM-009 Every executable task schema contains documentation and verification blocks.
SEM-010 Every required artifact has a producer or accepted external source.
SEM-011 Every material decision class maps to ADR/Decision policy.
SEM-012 Every blocker example contains options and resume condition.
SEM-013 Prompt artifact status matches its entity type.
SEM-014 No separate Attempt entity exists in v0.3 baseline.
SEM-015 Combined guides are generated from current source files.
SEM-016 Version/date metadata is consistent.
SEM-017 No broken relative links or duplicate stable section IDs.
SEM-018 No forbidden mixed-plane Change Pack example.
SEM-019 No provider billing/token accounting fields in core schemas.
SEM-020 Questionnaire and brownfield workflows lead to readiness gates.
SEM-021 Generated enum/matrix views exactly equal their machine registries.
SEM-022 Contract examples obey canonical fields and status-specific schema variants.
SEM-023 Every capability-bearing field resolves only to Capability Registry values.
SEM-024 Roadmap package IDs, names and dependencies are unique, aligned and acyclic.
SEM-025 Validation Report states the exact automated coverage and does not imply runtime conformance.
```

## 4. Severity

```text
ERROR
WARNING
INFO
```

- `ERROR` блокирует archive/release.
- `WARNING` требует explicit acknowledgement или issue.
- `INFO` показывает coverage/quality hints.

Unknown enum, broken link, mismatched combined guide, profile inconsistency и schema-less canonical entity являются `ERROR`.

## 5. Validation Report Contract

```yaml
validation_report:
  id: VAL-DOCS-20260807-001
  documentation_version: 0.5.0
  validator_version: 1.1.0
  source_tree_hash: sha256:...

  summary:
    errors: 0
    warnings: 0
    info: 3

  checks:
    - rule: SEM-006
      status: PASS
      evidence: "14 profile references resolved"

  generated_artifacts:
    - Project_Harness_User_and_Implementation_Guide_v0.5.0.md
    - Project_Harness_Architecture_v0.5.0_FULL.md
    - FILE_INDEX.md
    - MANIFEST.sha256

  result: PASS
```

## 6. Registry-driven extraction

Normative lists должны находиться либо:

- в machine-readable registry files при реализации;
- либо в одном designated Markdown registry section до появления code.

Остальные документы ссылаются на registry и могут показывать generated table. Validator сравнивает tables с source registry.

## 7. Contract example validation

YAML/JSON examples извлекаются по fenced code block markers и проверяются:

- syntax;
- required and forbidden canonical fields;
- status-specific draft/accepted variants;
- enum values;
- entity-specific ID prefix;
- references;
- lifecycle status applicability;
- capability values against `registries/capabilities.yaml`.

Illustrative ellipses `...` разрешены только в blocks, помеченных `illustrative: true`, либо исключённых explicit annotation.

## 8. Cross-document assertions

Примеры:

- profile count одинаков в overview and profile matrix;
- `COMPILED` не встречается как Prompt Plan status;
- `PARTIALLY_COMPENSATED` встречается только в compensation registry/fields;
- task lifecycle одинаков в planning, execution and contracts;
- user workflow references existing Request Classes;
- implementation roadmap begins with single-entry vertical slice;
- delivery roadmap and causal-sequence table use the same `WP-HARNESS-*` IDs and titles;
- roadmap dependencies reference existing packages and form an acyclic graph;
- project-local structure содержит `skills/`, `requests/`, `work-packages/` and traces.

## 9. Combined document generation

Combined guide не редактируется вручную. Generator:

1. читает index order;
2. вставляет source path markers;
3. нормализует heading levels;
4. сохраняет source path markers;
5. нормализует relative links к archive root;
6. сравнивает guide/full aggregate byte-for-byte с воспроизводимым output;
7. regenerates `FILE_INDEX.md` from current files;
8. fails CI при drift.

## 10. CI stages

```text
PR fast checks:
  metadata + links + registries + schemas + examples

Main/release checks:
  all semantic rules + combined build + checksums + archive integrity

Migration checks:
  old-version samples + alias mapping + regenerated views
```

## 11. Documentation coverage

Каждая implementation specification должна иметь:

- purpose;
- normative rules;
- contract/schema example;
- lifecycle/algorithm where applicable;
- error/blocker behavior;
- acceptance criteria;
- links to related canonical chapters.

Missing section является warning/error по configured completeness mode.

## 12. Reference validator interface

```text
python tools/validate_documentation.py <root>
  --zip <distribution.zip>
  --json <result.json>
  --write-report <VALIDATION_REPORT.md>
  --build-aggregates
```

Reference implementation reports validator version `1.1.0`, validates manifest automatically and verifies ZIP only when `--zip` is supplied. Отсутствующий ZIP является warning в local/fast run, но release invocation обязана передать archive path и получить zero warnings.

Implementation language runtime не является архитектурным решением Harness kernel; этот distribution validator реализован на Python как воспроизводимый packaging tool, а его output contract фиксирован.

## 13. Область значения PASS

`PASS` подтверждает только реально перечисленные автоматические проверки документационного комплекта: structure, links, YAML syntax, exact registry views, Contract Catalog coverage, entity-specific ID/status rules, canonical fields, capabilities, roadmap consistency, generated artifacts, manifest and ZIP.

`PASS` не подтверждает наличие реализованного runtime и не заменяет behavioral, security, adapter or executable conformance tests. Validation Report обязан повторять это ограничение.

## 14. Критерии приёмки

1. Validator обнаруживает profile, ID and entity-specific status inconsistencies.
2. Contract examples проходят syntax, required/forbidden field and status-variant checks.
3. Request Classes, Modes, Internal Operations and generated registry matrices сравниваются с registry exact-set/exact-order rules.
4. Capability-bearing fields отклоняют неизвестные aliases.
5. Roadmap package IDs/names совпадают в delivery and causal sequence; dependency graph acyclic.
6. Broken links and stale guide/full aggregate/file index блокируют release.
7. Every standalone entity example связан с Contract Catalog, storage/revision policy and lifecycle marker.
8. Validation Report перечисляет реальные checks, source tree hash and exact scope of PASS.
9. CI разделяет fast and release suites.
10. v0.2/v0.3 migration aliases тестируются, но новые normative examples используют canonical identifiers.
