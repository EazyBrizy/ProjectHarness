# Единая матрица project profiles

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Registry

| Profile | Typical boundary | Additional discovery | Typical checks |
|---|---|---|---|
| `BASE_SOFTWARE` | Neutral software project | General users/data/operations | Build, test, docs, traceability |
| `WEB_APPLICATION` | Browser/UI/API/data | Accessibility, browser/session flows | Browser, accessibility, API integration |
| `API_SERVICE` | API/data/integrations | Contracts, auth, availability/rate | Contract, security, integration |
| `MOBILE_APPLICATION` | Device/app/backend | Platforms, offline, permissions/distribution | Device, privacy, upgrade |
| `DESKTOP_APPLICATION` | OS/app/local data | OS, packaging, local storage/update | Install/update, local data |
| `CLI_TOOL` | Shell/filesystem/network | Platforms, stdin/out, exit codes | Help, exit codes, filesystem safety |
| `LIBRARY` | Public API/consumers | Versions, compatibility, packaging | API compatibility, examples |
| `DATA_PIPELINE` | Sources/transforms/sinks | Quality, lineage, replay/scheduling | Data quality, replay/idempotency |
| `ML_SYSTEM` | Data/model/inference | Provenance, evaluation, drift | Reproducibility, evaluation, data policy |
| `INFRASTRUCTURE` | IaC/providers/environments | State, privileges, rollback | Plan/dry-run, policy, rollback |
| `EMBEDDED_SYSTEM` | Hardware/firmware/interfaces | Device constraints, timing, update/recovery | Hardware-in-loop/profile checks |
| `AUTOMATION` | Trigger/action workflows | Idempotency, credentials, schedules | Dry-run, retries, side effects |
| `MULTI_SERVICE_SYSTEM` | Services/contracts/platform | Ownership, deployment order, consistency | Contract, integration, release |
| `CUSTOM` | Explicit extension | User-defined checklist | Schema, security, traceability |

## 2. Composition

```yaml
project_profile:
  id: PRF-PROJECT-001
  primary: API_SERVICE
  extensions: [DATA_PIPELINE]
  overrides: {}
  status: CONFIRMED
  decision_ref: DEC-PROFILE-001
```

Conflicting defaults create a conflict/decision. Profile never silently chooses stack or weakens hard constraints.

## 3. Leakage test

Every profile release runs with an unrelated profile. Generated definitions/tasks/prompts must not contain foreign domain terms/paths.
