# Риски, baseline decisions и открытые вопросы v0.4.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Accepted design decisions in documentation baseline

1. Natural-language single entry is mandatory; CLI commands are optional adapters.
2. Request Class, Mode and Internal Operation are separate taxonomies.
3. Every project start uses documentation-first adaptive questionnaire.
4. Brownfield starts read-only and produces separate continuation/fix/improvement/stabilization routes.
5. Request → Work Package → atomic Task → Run is the execution hierarchy.
6. Prompt compiles JIT for READY task; no mass future prompt generation.
7. Artifact dependencies enforce causal order.
8. Shared read-only frozen contracts allow parallel consumers; writes conflict.
9. ADR is only for material decisions.
10. Verification is profile/risk proportional; test DB uses snapshot/isolation where possible.
11. Request Trace spans all lifecycle stages.
12. Codex is first Agent Adapter, not governance owner.
13. Product, Project Control and Distribution Change Packs are isolated.
14. Run itself is an attempt; retry creates new Run.
15. Registries are single source for profiles, IDs and statuses.
16. Provider billing/token accounting remains out of scope.

## 2. Implementation decisions still required

Эти решения не блокируют утверждение архитектуры целиком. Каждое из них имеет owner role и должно быть закрыто только до начала зависимого `WP-HARNESS-*`.

| Решение | Default owner role | Resolve before | Expected output |
|---|---|---|---|
| Language/runtime deterministic kernel | Harness Architecture Owner | `WP-HARNESS-000` implementation start | `ADR-HARNESS-RUNTIME` |
| Files-first vs embedded transactional canonical store | Harness Architecture Owner | `WP-HARNESS-000` storage task | `ADR-HARNESS-STORE` |
| Exact local IPC/API shape of Single Entry | Runtime/API Owner | `WP-HARNESS-005` | `ADR-HARNESS-SINGLE-ENTRY` |
| Supported OS and sandbox boundaries for first release | Runtime Security Owner | governed adapter slice of `WP-HARNESS-080` | `ADR-HARNESS-SANDBOX` |
| Concrete Codex integration and tool mediation | Agent Adapter Owner | Codex slice of `WP-HARNESS-080` | `ADR-CODEX-INTEGRATION` |
| Test database clone/schema strategy for fixtures | Verification Owner | environment task in `WP-HARNESS-050` | `ADR-TEST-ENVIRONMENT` |
| Local identity and decision authority mechanism | Security/Authority Owner | approval-capable route in `WP-HARNESS-005` | `ADR-LOCAL-AUTHORITY` |
| Retention and encryption implementation | Security/Data Owner | persistent runtime/evidence task in `WP-HARNESS-080` | `ADR-RETENTION-ENCRYPTION` |
| Production/extended semantic-validator parser/toolchain beyond the bundled Python reference | Documentation Tooling Owner | extended validator task in `WP-HARNESS-110` | `ADR-DOCS-VALIDATOR` |
| Default Git commit policy | Git/Release Owner | publication task in `WP-HARNESS-110` | `ADR-GIT-COMMIT-POLICY` |

До указанного gate допустим интерфейс, fixture или reversible default, если он не фиксирует material semantics и явно отмечен в package plan.

## 3. Key risks and mitigations

| Risk | Mitigation |
|---|---|
| Single-entry prompt becomes monolith | Thin orchestrator + Request Plan + reusable contracts. |
| Too many questions | 3–5 batches, 7–12 target, source-derived omission, unknown path. |
| Brownfield damage | Read-only inventory, baseline gate, no hidden restructuring. |
| Prompt/task explosion | Work Packages + minimum atomic tasks + JIT bundles. |
| Future dependency | Artifact producer validation and causal readiness. |
| Parallel conflicts | Multi-domain read/write sets, frozen inputs, leases, integration gate. |
| ADR overload | Materiality policy and Task Report separation. |
| Test overhead | Verification Profiles, targeted suites, pre-migrated isolated DB. |
| Stale tests hide regressions | Baseline comparison and formal stale-test resolution. |
| Agent scope escape | Tool mediation and actual-write checks. |
| State/context loss | Canonical state + Request Trace + cold-start guidance. |
| Maintenance breaks active work | Quarantine, target-plane isolation, version activation and rollback. |
| Registry/document drift | Semantic documentation CI and generated aggregates. |
| Control plane too complex | Human views and MINIMAL/STANDARD modes. |
