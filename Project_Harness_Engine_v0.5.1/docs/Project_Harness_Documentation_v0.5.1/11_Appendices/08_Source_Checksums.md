# Source checksums и release basis

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** VERIFIED SOURCE PROVENANCE

## 1. Supplied archives

| Source | SHA-256 |
|---|---|
| `Project_Harness_Engine_v0.4.1.zip` | `6f8955583e6c50143072a0d16345cddbb742a4e16cacbfc7ed8833321d13f19a` |
| `Project_Harness_Documentation_v0.4.1.zip` | `3211c70d89f3a0f7c6d82fd40c448d22b51e6bd3f26c40f24ee1df28c075a653` |
| `Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0.zip` | `56bca615b7da5a0f48d0479c2de24ccd151fcefbf453fdfea89eab0d2675219e` |

## 2. Applied specification scope

Для current release применены последовательно принятый baseline v0.4.1 и только следующий patch document `Project Harness v0.5.0 — Implementation Levels, Stage Planning и Brownfield Maturity`. Спецификации v0.5.1 и выше не использованы как источник реализованного поведения.

## 3. Resolution

Единственная внутренняя неоднозначность v0.5.0 касается lowercase explanatory directory names в §8 и exact uppercase storage paths в Contract Catalog §9.1. Release использует uppercase paths `PLANS`, `GATES`, `ACCEPTANCE`, `ASSESSMENTS` как нормативные, поскольку catalog определяет persisted contract locations.

## 4. Derived artifacts

Generated aggregates, file index, manifest and final ZIP воспроизводятся из current source tree через `tools/validate_documentation.py`. Их digests фиксируются в release manifest и delivery summary; этот provenance document не образует circular self-hash.
