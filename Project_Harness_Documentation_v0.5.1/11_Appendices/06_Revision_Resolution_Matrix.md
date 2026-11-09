# Матрица устранения пробелов аудита v0.4.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

| Пробел v0.2 | Решение v0.3 | Нормативный файл |
|---|---|---|
| Single entry без Request Contract | Request Class/Mode/Operation, Request lifecycle and Request Plan | `12_Implementation_Specifications/01...` |
| Нет общего результата | Result Envelope and public statuses | `12_Implementation_Specifications/02...` |
| Нет parent/user outcome model | Work Package + atomic tasks + runtime split | `12_Implementation_Specifications/03...` |
| Возможна массовая генерация prompts | JIT compilation and retention policy | `12_Implementation_Specifications/04...` |
| Task не знает sections документации | Stable documentation refs and impact gate | `12_Implementation_Specifications/05...` |
| ADR для каждой задачи | Material decision policy | `12_Implementation_Specifications/06...` |
| Хронология без artifact causality | Producer/consumer DAG and readiness | `12_Implementation_Specifications/07...` |
| Shared contract falsely conflicts | Contract read/write sets and frozen revisions | `12_Implementation_Specifications/08...` |
| Любая неоднозначность останавливает всё | Materiality + strict/pragmatic modes | `12_Implementation_Specifications/09...` |
| Blocker может быть тупиком | Recovery routes/recommendation/resume | `12_Implementation_Specifications/10...` |
| Универсальный test rule/test DB rebuild | Verification Profiles, baseline, snapshot/isolation | `12_Implementation_Specifications/11...` |
| Run logging begins too late | Request Trace/correlation from input to result | `12_Implementation_Specifications/12...` |
| Stack not formalized | Technology Baseline and compatibility | `12_Implementation_Specifications/13...` |
| Skills lack registry/lifecycle | Skill gap, readiness, evaluation and versioning | `12_Implementation_Specifications/14...` |
| Codex undefined | Codex Agent Adapter contract | `12_Implementation_Specifications/15...` |
| Harness maintenance mixed with product | Target-plane Change Packs | `12_Implementation_Specifications/16...` |
| Documentation too internal | Human/machine layers and materialization modes | `12_Implementation_Specifications/17...` |
| Profiles/IDs/statuses inconsistent | Versioned registries and Run-as-attempt | `12_Implementation_Specifications/18...` |
| Link checks miss semantic contradictions | Semantic documentation validator | `12_Implementation_Specifications/19...` |
| Existing project onboarding incomplete | Brownfield baseline and route portfolio | `12_Implementation_Specifications/20...` |
| No mandatory adaptive project questionnaire | Documentation-first bounded questionnaire | `12_Implementation_Specifications/21...` |
