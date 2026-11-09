# Отчёт автоматической и семантической проверки комплекта

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** GENERATED VALIDATION REPORT

## Итог

**PASS** — structural and registry/contract semantic documentation validation.

## Область подтверждения

PASS означает, что текущий комплект прошёл перечисленные ниже автоматические проверки: Markdown/package structure, ссылки, YAML syntax, exact registry views, contract catalog coverage, entity-specific ID/status rules, canonical fields, capability values, roadmap identity/dependencies, generated aggregates, manifest and ZIP integrity.

PASS подтверждает только documentation/package artifacts и не заменяет отдельный executable conformance suite движка, security review или provider-adapter tests.

## Сводка

- validator: 1.4.0;
- файлов: 116;
- Markdown: 106;
- YAML registries: 8;
- YAML examples: 137;
- локальных ссылок: 819;
- проверок: 36;
- ошибок: 0;
- предупреждений: 0;
- source tree hash: `sha256:cc8f285a70cc2bcf2fc5d32678fc62b07420831321707968c7d250689c7f79f0`.

## Результаты

| Проверка | Результат | Детали |
|---|---|---|
| Required artifacts | PASS | all present |
| Archive hygiene | PASS | files=116, symlinks=0 |
| File types | PASS | expected types only |
| Markdown structure | PASS | one H1 in 106 files; balanced fences |
| Metadata | PASS | version/date present in 106 Markdown files |
| Relative links | PASS | checked=819, broken=0, escaping=0 |
| YAML registries | PASS | parsed=8 |
| YAML contract syntax | PASS | parsed=137 fenced examples |
| ID Registry uniqueness | PASS | prefixes=96, duplicates=0 |
| ID Registry coverage | PASS | used=92, unknown=0 |
| Legacy aliases | PASS | none in current normative source documents |
| Profile Registry consistency | PASS | profiles=14 represented in canonical views |
| Request routing enum equality | PASS | classes, modes and internal operations exactly match registry |
| Request routing value applicability | PASS | uses=15, unknown=0 |
| Registry-generated matrices | PASS | status, routing and capability views exactly match YAML registries |
| Contract Catalog integrity | PASS | entities=59, field contracts=17 |
| Contract Catalog example coverage | PASS | standalone examples=89, uncatalogued=0 |
| Entity ID prefix semantics | PASS | validated=89 examples |
| Lifecycle status applicability | PASS | validated=89 examples against entity status groups |
| Canonical contract fields | PASS | validated=29 focused examples |
| Capability Registry applicability | PASS | uses=23, unknown=0 |
| Billing/token accounting exclusion | PASS | no provider billing, cost or token-ledger fields in YAML contracts |
| Roadmap identity and dependencies | PASS | packages=14, unique IDs, exact causal table, acyclic dependencies |
| Lifecycle normalization | PASS | Run-as-attempt, compensation and parallelism rules normalized |
| Prompt lifecycle | PASS | COMPILED appears only on Compiled Prompt Bundle |
| Implementation specifications | PASS | 24 files; each >=150 lines and has acceptance criteria |
| Consolidated guide freshness | PASS | source markers=24/24; content reproducible |
| Full aggregate freshness | PASS | sources=95, content reproducible |
| File index freshness | PASS | file inventory, line and byte counts are current |
| Requirements coverage | PASS | unique=226, declared=226 |
| Questionnaire contract | PASS | documentation-first, bounded batches, unknown path and limits present |
| Brownfield contract | PASS | read-only inventory and four route families present |
| Core MVP and Hardening boundary | PASS | first vertical loop is separated from concurrency and maintenance hardening |
| Implementation decision gates | PASS | gated decisions=10, each with owner and ADR output |
| Manifest | PASS | entries=115, hashes verified |
| ZIP archive | PASS | entries=116, CRC PASS, tree exact |

## Исправленные audit invariants

- implementation packages use `WP-HARNESS-*`; `HNS-REQ-*` remains requirement-only;
- Request Class, Mode and Internal Operation views exactly equal `request_routing.yaml`;
- persistent examples are bound to Contract Catalog, entity ID prefix and lifecycle group;
- canonical field variants and forbidden aliases are validated from `contracts.yaml`;
- capability fields reject values absent from `capabilities.yaml`;
- roadmap IDs, names and dependency graph are checked against the causal sequence;
- generated guide/full document/file index are compared byte-for-byte with reproducible output.

## Ограничение

Этот отчёт подтверждает согласованность documentation/package artifacts версии 0.5.0. Runtime guarantees подтверждаются отдельным `TEST_REPORT_v0.5.0.md` в поставке движка и не выводятся только из этого документационного отчёта.
