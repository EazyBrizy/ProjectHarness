# Core MVP scope v0.4.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** IMPLEMENTED CORE BASELINE

## 1. Goal

Core поставляет один управляемый end-to-end loop:

```text
Browser GPT semantic intake
→ external provisional workspace
→ accepted definitions/baselines
→ deterministic Codex handoff
→ current READY Task
→ one JIT bundle and Run attempt
→ independent verification/evidence
→ next task, blocker or completion
```

## 2. Реализованный Core scope

- distribution doctor и exact registry loading;
- `START_INTAKE` вне product repository;
- documentation-first adaptive questionnaire input;
- greenfield, brownfield и hybrid modes;
- read-only brownfield inventory и four-route portfolio;
- explicit Project Definition, Architecture, Technology и Handoff approvals;
- canonical Project Lock, Session и baselines;
- Skill Gap Analysis с `REUSE`, `CONFIGURE`, `TASK_ONLY`;
- ACTIVE universal seed skills;
- Work Packages, atomic Tasks и causal DAG;
- Prompt Plans, Context Plans и Verification Profiles для accepted tasks;
- exactly one compiled bundle для current READY Task;
- self-contained Codex Handoff ZIP и embedded runtime;
- фактический diff/scope/expected-path verification;
- command verification без shell;
- Run-as-attempt, Evidence, Task Report, Blocker и resume;
- cold-start state recovery;
- manifest, safe ZIP extraction и conformance tests;
- semantic documentation validation.

## 3. Core skill boundary

Core загружает и pin-ит уже ACTIVE skill. Он не симулирует создание и activation нового PROJECT skill. `CREATE` или `EXTEND` даёт Blocker с route в hardening lifecycle. Эта граница позволяет проверить движок без циклической зависимости от ещё не реализованного skill-authoring subsystem.

## 4. Hardening после Core

- provider-specific automated Codex/API dispatch;
- OS-level sandbox и network isolation;
- parallel batches, worktrees, leases и integration orchestration;
- полный create/extend/evaluate/activate lifecycle PROJECT skills;
- несколько test-environment strategies и stale/flaky classification;
- full Change Packs, canary и distribution rollback;
- Git commit/push/PR, deployment и publication automation;
- multi-user authentication и remote control plane;
- extended adversarial, regulated, polyrepo и release suites.

Provider billing/token accounting остаётся permanent non-goal, а не deferred feature.

## 5. Pilot profiles

```text
CLI_TOOL
API_SERVICE
CUSTOM
```

Первый reference fixture — локальный CLI с двумя causal tasks и offline verification. Brownfield fixture — небольшой существующий repository с read-only inventory.

## 6. User journeys

1. Проверить engine distribution командой `doctor`.
2. Начать новый Project Instance во внешнем workspace.
3. Проанализировать документы и получить только недостающие вопросы.
4. Подтвердить четыре material Gate.
5. Получить валидный Codex Handoff ZIP со статусом `READY_FOR_CODEX`.
6. Выполнить одну atomic Task в declared scope.
7. Независимо проверить diff и commands.
8. Завершить Task и JIT-скомпилировать следующую.
9. Создать Blocker, принять решение и продолжить новой attempt.
10. Перезапустить process и восстановить exact current route.
11. Подключить brownfield repository без изменений исходника.

## 7. Release gate

Core release требует:

- все Core conformance tests PASS;
- `doctor` PASS из source tree и установленного wheel;
- greenfield full DAG reaches `COMPLETED`;
- brownfield source byte-identical до handoff;
- out-of-scope write и false agent diff отвергаются;
- manifest tampering и ZIP traversal отвергаются;
- docs validator возвращает zero errors/warnings;
- release archive после распаковки повторно проходит tests и manifest verification.
