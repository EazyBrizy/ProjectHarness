Текущее дополнение PH-LW-12: [три blockers и операторский recovery](13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md). Фактическая повторная приёмка точных wheel/installer bytes — в новом PH_LW_12_FIX_TEST_REPORT.md Engine. Ниже сохранены предыдущие checkpoints.

Текущий этап — PH-LW-12: [операторский маршрут и границы приёмки](13_Local_Web_Manual_Companion/22_PH_LW_12_Operator_Acceptance.md). Фактический verdict — PH_LW_12_TEST_REPORT.md Engine. Automatic executor выключен; v0.5.1 WIP / NOT RELEASED. Ниже сохранены предыдущие checkpoints.

Текущий checkpoint — PH-LW-11, 2026-11-08: [Windows установка, resume и stop](13_Local_Web_Manual_Companion/19_PH_LW_11_Windows_Installation.md). Фактический verdict — в PH_LW_11_TEST_REPORT.md Engine; наличие EXE не означает GO. Automatic executor выключен; PH-LW-12 не начат. Далее сохранена история.

Текущий checkpoint — PH-LW-10, 2026-11-07: [Stage Gates, planning, level-up и обслуживание](13_Local_Web_Manual_Companion/18_PH_LW_10_Stage_Lifecycle.md). Фактические результаты — `PH_LW_10_TEST_REPORT.md` Engine. Automatic executor выключен; PH-LW-11 не начат. Ниже сохранены исторические checkpoints; их прежние ограничения не являются текущим test verdict.

Текущий checkpoint: [Task-level manual evidence intake](13_Local_Web_Manual_Companion/17_PH_LW_09_Task_Manual_Evidence.md). PH-F06 закрыт; повторная составная приёмка PH-LW-09 — PASS в назначенном scope. Исторические checkpoints ниже сохранены; полный релиз не принят.

## Текущий build — PH-LW-09, 2026-11-07

[Task/JIT и ручной цикл](13_Local_Web_Manual_Companion/16_PH_LW_09_Task_Run_Manual_Console.md): bounded result intake, отдельный consent на verification, complete/block/resume. Фактическая приёмка — `PH_LW_09_TEST_REPORT.md` в Engine. Automatic executor выключен; PH-LW-10 не выполнялся; полная v0.5.1 не выпущена (verdict — в отчёте). Ниже сохранены исторические checkpoints.

## Предыдущий build — PH-LW-08, 2026-11-07

[Подготовка и безопасное размещение](13_Local_Web_Manual_Companion/15_PH_LW_08_Preparation_and_Publication.md): действительные separate approvals, server-owned staging, initial validations, no-clobber publication, exactly one first JIT и recovery. Фактическая приёмка — `PH_LW_08_TEST_REPORT.md` в Engine. Automatic executor выключен, PH-LW-09 не выполнен, полный release не выпущен (verdict см. в отчёте).

## Предыдущий build — PH-LW-07, 2026-11-07

[Отдельные согласования и recovery](13_Local_Web_Manual_Companion/14_PH_LW_07_Separate_Approvals.md): четыре/пять осознанных решений, actor, exact bindings, companion receipts и invalidation. Фактический отчёт — `PH_LW_07_TEST_REPORT.md` в Engine. Подготовка Project Instance ожидает PH-LW-08; automatic executor выключен, полный release остаётся незакрытым (`NOT RELEASED`). Следующие checkpoints сохранены как история.

## Рабочие файлы и архивы — правило от 2026-11-07

Все рабочие файлы проекта — код, документация, планы, промпты, отчёты и evidence — хранятся в распакованных каталогах. Архив не должен быть единственным местом хранения файлов.

**После каждого этапа или правки Engine/Documentation ZIP собирать не нужно. Архивы создаются только по явному запросу пользователя для передачи в ChatGPT на анализ, когда это требуется.** Это указание заменяет прежнее требование обязательной упаковки после этапов в сохранённых планах/prompts. Исторические архивы, inputs и отчёты сохраняются неизменными; их hashes описывают соответствующие снимки, а не текущий workspace. Синхронизация документации, manifests и применимые проверки рабочих файлов продолжаются без обязательной ZIP-пары.

## Предыдущий build — PH-LW-06, 2026-11-07

[Опрос и manual GPT draft exchange](13_Local_Web_Manual_Companion/13_PH_LW_06_Interview_and_GPT_Exchange.md): typed ответы, actual readiness, bounded pack, strict JSON, diff до commit и recovery. Фактический отчёт — `PH_LW_06_TEST_REPORT.md` в Engine. Automatic executor выключен, PH-LW-07 не выполнялся; полный release остаётся незакрытым (`NOT RELEASED`). Следующие checkpoints сохранены как история.

## Предыдущий build — Windows manual migration remediation, 2026-11-07

[Миграция, recovery и границы Windows manual приёмки](13_Local_Web_Manual_Companion/12_Windows_Manual_Migration_Retest.md). Фактический отчёт — `PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md` в Engine. Ниже сохранены предыдущие checkpoints. Automatic executor не активирован; PH-LW-06 не выполнялся; полный release — **NO GO / NOT RELEASED**.

## Предыдущий build — Windows HTTP retest PH-LW-04/05, 2026-11-07

База PH-LW-05 перенесена в native Windows workspace и исправлена по результатам HTTP/importer приёмки. [Текущая область, команды и ограничения](13_Local_Web_Manual_Companion/11_PH_LW_04_05_Windows_HTTP_Acceptance.md). Фактический verdict и регрессии — `PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md` в Engine. Ниже сохранены исторические checkpoints: их NOT RUN относится к прежним сборкам. Полный `LOCAL_WEB_MANUAL`, automatic executor и v0.5.1 — **NO GO / NOT RELEASED**; PH-LW-06 не выполнялся.

## PH-LW-05 — MD/ZIP source importer, WIP (Windows/browser NOT TESTED)

The Local Web manual shell now provides «Документы»: controlled GREENFIELD intake, multiple MD/ZIP upload, immutable snapshots and source revisions, no-doc explicit choice, escaped text preview and safe retry/recovery. No accepted state or automated Codex is enabled. Real Windows NTFS/HTTP/Edge/Podman acceptance remains NOT RUN / NO GO. See [10_PH_LW_05_Document_Import_and_Source_Revisions.md](13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md) and the Engine `PH_LW_05_TEST_REPORT.md`.

## PH-LW-04 — HTTP + UI shell, WIP (Windows/browser NOT TESTED)

См. [Loopback HTTP, сессии/CSRF, UI shell и operator runbook](13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md). Новая команда `project-harness ui` запускает отдельный Flask+Waitress localhost server при наличии pinned зависимостей; project data и mutations за session, будущие формы disabled. Реальная Windows 11 x64/NTFS и Waitress/browser security acceptance ещё требуют запуска; полного GO v0.5.1 нет.

## PH-LW-03 — application service only (v0.5.1 WIP; native Windows NOT RUN)

См. [описание PH-LW-03 service/operation recovery](13_Local_Web_Manual_Companion/08_PH_LW_03_Application_Service_and_Operation_Recovery.md): один Python service над manual core, bounded draft API, межпроцессный OS guard с CLI, read-only status, идемпотентный журнал и fail-closed crash reconciliation. **Нет HTTP/UI, не включён automatic execution, Windows 11 x64/NTFS не проверен, полный v0.5.1 release блокирован.**

## PH-LW-02 — Windows manual core boundary (WIP; native Windows NOT RUN)

See [`13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md`](13_Local_Web_Manual_Companion/07_PH_LW_02_Native_Windows_Manual_Core.md) for supported path/lock semantics, fail-closed automatic boundary, Linux-targeted regression coverage and the native Windows CI entrypoint. This phase does not implement a Web UI or close the v0.5.1 automatic NO GO.

> **PH-LW-01 (0.5.1-WIP / not released):** [контракт Windows Local Web manual companion](13_Local_Web_Manual_Companion/00_Entry_And_Base.md) — карта 26 CLI/API, зависимостей, draft-only GPT и platform test baseline. Это design/fixtures, **не** реализованный Web-интерфейс и **не** Windows acceptance. Источник — предоставленные PH-051-11 ZIP, не заявленный PH-051-12 snapshot.

> **АКТУАЛЬНО — PH-051-11, 0.5.1-WIP / NOT RELEASED.** Текущие публичные `executor-doctor`, `execute-current`, `migrate-project` описаны в [операторском runbook v0.5.1](05_Updates/14_Operator_Runbook_v0.5.1_WIP.md), а реальная [Podman security matrix и стендовые требования](05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md) — отдельно. Действующие contract versions: `PROJECT_INPUT@4`, schema7, ID@3, statuses@6, contracts@6. Существующий `prepare` **не поддерживает новый `LOCAL_AUTOMATIC` intake** (fail-closed); отсутствие публичного opt-in нельзя обходить редактированием подписанного lock. **Real rootless Podman tests пока NOT TESTED / NO GO**. Тексты PH-051-01..10 и базовая v0.5.0 документация ниже сохранены как исторические checkpoints.

> **v0.5.1 WIP / PH-051-10 — NOT RELEASED.** Existing valid v0.5.0 Project Instances can explicitly execute `project-harness migrate-project --project <root>` into schema7 **manual-only** execution, retaining immutable history. Orphan/restart cleanup, bounded Podman termination and recoverable durable apply are implemented; real rootless Podman security acceptance remains **NOT RUN / NO GO**. See [PH-051-10 migration and cleanup](05_Updates/13_Migration_Cleanup_Orphan_Recovery_v0.5.1_WIP.md). Earlier sections below describe their historical implementation checkpoints.

## PH-051-06 (v0.5.1 WIP / NOT RELEASED)

[Exact Agent Result, bounded logs and ENV secret refs](05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md) documents internal behavior and security boundary. Automatic mode is still NO GO without real rootless Podman and stages PH-051-07–12.

> **PH-051-05 — 0.5.1 WIP / NOT RELEASED.** The single Codex CLI adapter
> now resolves pinned ACTIVE ADP/SBX profiles, builds current Run/JIT argv and
> forwards it only into RootlessPodmanRunner. This does **not** enable a public
> automatic route or trust agent output. Podman/image/real Codex flags were NOT
> TESTED here; manual handoff remains supported. See
> [PH-051-05 local adapter note](05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md).

> **PH-051-04 — 0.5.1 WIP / NOT RELEASED.** Per-Run product-only
> snapshots, exact baseline/task/JIT binding and bounded read-only control
> projection are implemented as Python API, with `EXECUTION_BINDINGS`
> excluded from handoff ZIP. Automatic CLI, verification and apply are not
> enabled. Real rootless Podman security acceptance remains NOT RUN / NO GO.
> See [PH-051-04 note](05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md).

> **v0.5.1 WIP / PH-051-03:** один Rootless Podman Sandbox runner и
> fail-closed Python `doctor`/OS self-tests добавлены **без** публичного
> `executor-doctor`/`execute-current`, автоматического изменения canonical
> product, egress или host fallback. Реальный Podman недоступен в стенде
> сборки: security acceptance `NOT RUN / release blocked`, manual handoff остаётся
> единственным публичным маршрутом.
> [Sandbox note](05_Updates/07_Rootless_Podman_Sandbox_v0.5.1_WIP.md),
> [Executor protocol](05_Updates/06_Executor_Protocol_v0.5.1_WIP.md).

# Project Harness — документация движка v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** IMPLEMENTATION LEVEL AND STAGE AWARE CORE RUNTIME BASELINE

Project Harness v0.5.0 добавляет управляемую глубину реализации поверх принятого product scope. Версия вводит пять последовательных Implementation Levels, Stage Plans, Stage Gates, immutable Stage Acceptance Reports, read-only Brownfield Maturity Assessment, same-level maintenance и явный level-up. Она не добавляет функции продукта автоматически и не расширяет разрешения исполнителя.

## PH‑F07 — единая инструкция оператора (2026-10-25)

Для **исполняемых** команд v0.5.0 используйте [сквозной operator runbook](08_Distribution/04_Operator_Runbook_v0.5.0.md) и [публичные workflows](08_Distribution/03_User_Workflows.md). Он связывает GPT/source/approvals, installed wheel или bundled entrypoint, external Codex Task cycle, предметную Gate proof, Stage planning, level-up, Brownfield, maintenance, recovery и конкретные schemas. Valid handoff **не** означает созданный production-код, а общий PASS verification **не** закрывает любой Gate evidence kind. Этот PH‑F07 checkpoint не равен PH‑F08 финальной приёмке.

## PH_F06 integration update — 2026-10-24

Проверенные границы зрелости, Brownfield evidence import и same-level maintenance:
[PH_F06 lifecycle notes](PH_F06_LIFECYCLE_NOTES.md).
Результаты отдельных и полных прогонов: [PH_F06 test report](PH_F06_TEST_REPORT.md).
Это scoped remediation v0.5.0, не финальная приёмка PH_F08.

## 1. Сквозной пользовательский поток

```text
Документация и исходники
→ внешний START_INTAKE
→ core outcome и project scope
→ обязательный target implementation level
→ Project Definition / Brownfield Baseline / Architecture / Technology approvals
→ Stage Plans от PROTOTYPE до target
→ детальные Work Packages и Tasks только active stage
→ один JIT Prompt Bundle для текущей READY Task
→ independent verification
→ deterministic final-baseline Gate readiness
→ governed STAGE_ACCEPTANCE_PREPARATION Task only for missing evidence
→ Stage Gate formal review
→ immutable acceptance baseline
→ следующая последовательная Stage либо TARGET_LEVEL_REACHED
```

`implementation_level` отвечает на вопрос «насколько глубоко и надёжно реализовать утверждённый scope». Он не заменяет `project_scope`, `project_profile`, `execution_mode` или `deployment_model`.

## 2. Что изменилось в v0.5.0

1. **Canonical scale.** `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`; `MVP` означает Production MVP. `UNSURE` остаётся decision state и не записывается как уровень.
2. **Strict `PROJECT_INPUT@3` и target authority.** Во внешнем intake current target читается из `PROJECT_INPUT.yaml`; после подготовки immutable `PROJECT_INPUT_ACCEPTED` сохраняет initial accepted target, а единственный current-cycle target находится в Stage State с согласованными PROJECT/CURRENT_STATE projections.
3. **Stage-aware planning.** Outline создаётся для каждой стадии до target, но detailed Work Packages, atomic Tasks, Context/Prompt Plans и JIT bundles разрешены только active stage.
4. **Stage Gate.** Mandatory criterion закрывается только `PASS` либо обоснованным `NOT_APPLICABLE`; средние баллы запрещены.
5. **Immutable acceptance.** Для каждой принятой стадии фиксируются baseline, permitted-use boundary, known limitations и next-stage gaps.
6. **Brownfield maturity.** Assessment использует предоставленные и read-only evidence, не запускает repository commands автоматически и не меняет accepted maturity без approval.
7. **Level-up и maintenance.** Повышение цели активирует только ближайшую следующую стадию; bugfix без повышения остаётся отдельным same-level route.
8. **Migration.** v0.4.1 → v0.5.0 сохраняет immutable history, не угадывает уровень по старому `COMPLETED` и применяет изменения только после полной проверки копии.
9. **Crash-consistent Stage transactions.** `accept-stage` и `level-up` используют durable journal/backups, deterministic recovery, exact terminal digests и idempotent committed replay.
10. **Trusted Gate evidence.** Every closing `EVD-*` ref resolves at one exact project-local path and is checked for normalized schema, semantic kind, positive status, provenance, subject mapping, current product baseline and immutable SHA-256 binding.
11. **Self-contained Stage approval preparation.** `stage-status` exposes the exact Gate/baseline contract, while `prepare-stage-approval` writes a deterministic strict `DRAFT` record with complete result skeletons, evidence candidates and unresolved gaps without approving or mutating the project.
12. **Full same-level maintenance lifecycle.** Strict `start-maintenance`/`cancel-maintenance` records create and close accepted-stage WP/Tasks through the ordinary runtime, preserve maturity/acceptance history and block level-up only while the maintenance WP is open.

Нормативная спецификация: [`24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md).

## 3. Быстрый запуск движка

```bash
cd /path/to/Project_Harness_Engine_v0.5.0  # source Engine root
python project-harness.py doctor
python project-harness.py --version
python project-harness.py demo --output-dir ./demo-output --keep-directory
python project-harness.py validate-handoff   --project ./demo-output/harness-demo-codex-handoff.zip
```

Для нового intake после анализа источников и определения core outcome требуется canonical target:

```text
PROTOTYPE | ALPHA | BETA | MVP | RELEASE
```

При ответе `UNSURE` подготовительный слой показывает рекомендацию с rationale, а readiness остаётся `WAITING_DECISION` до явного выбора.

## 4. Stage-aware runtime

Основные команды извлечённого Project Instance:

```bash
python .harness/engine/project-harness.py validate-project --project .
python .harness/engine/project-harness.py status --project .
python .harness/engine/project-harness.py stage-status --project .
python .harness/engine/project-harness.py next --project .
python .harness/engine/project-harness.py verify --project . --allow-command-execution
python .harness/engine/project-harness.py complete --project .   --result .harness/runtime/AGENT_RESULTS/<RUN-ID>.json
```

После последней ordinary mandatory Task оценивается readiness на final product baseline: при missing proof требуется bounded `STAGE_ACCEPTANCE_PREPARATION`; только при подтверждённом coverage возможен `VERIFYING`. Проект не получает ложный terminal `COMPLETED`: требуется formal Gate approval. Пользовательский цикл не требует чтения private Python code или ручного разбора Gate:

```text
stage-status → prepare-stage-approval → добавить/проверить evidence и formal fields → accept-stage
```

```bash
python .harness/engine/project-harness.py stage-status --project .
python .harness/engine/project-harness.py prepare-stage-approval \
  --project . \
  --output ../operator-records/prototype-stage-approval.yaml
python .harness/engine/project-harness.py accept-stage \
  --project . \
  --level PROTOTYPE \
  --approval ../operator-records/prototype-stage-approval.yaml
```

`stage-status` возвращает exact Plan/Gate refs, paths, revisions, Gate digest, canonical product `baseline_revision`, result counts и следующий операторский route. После последней ordinary mandatory Task runtime сначала оценивает Gate readiness: при missing exact-baseline evidence создаёт ровно один idempotent `STAGE_ACCEPTANCE_PREPARATION` WP/Task с первым JIT bundle, иначе сразу переводит Stage в `VERIFYING`. `prepare-stage-approval` затем пишет отдельный strict `SCHEMA-STAGE-APPROVAL@1` record: `record_state: DRAFT`, `approved: false`, `id/actor/approved_at: null`, все result statuses `UNKNOWN`. Evidence candidates являются подсказкой и не дают автоматический `PASS`. Сама команда не меняет Stage/Gate, не создаёт Work Package/Decision/Acceptance Report, не запускает repository commands и не изменяет product tree. Внутри Project Instance output разрешён только под `.harness/operator/APPROVALS/`; существующий файл требует explicit `--force`. Valid formal review с незакрытым mandatory result сохраняется как Gate-related `BLOCKED`; `resume-stage-gate` возвращает его в ACTIVE preparation либо VERIFYING, создавая новые revisions.

Каждый `PASS` после formal review обязан ссылаться на normalized immutable `.harness/evidence/EVD-*.yaml`, mapping’ить exact result, иметь compatible kind, positive status, provenance, current product baseline и digest-verifiable source. Изменение product tree или Gate revision делает старый approval stale. Подробный контракт: [`04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`](04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md).

Same-level maintenance uses a separate governed route and the existing Task runtime:

```bash
python .harness/engine/project-harness.py start-maintenance --project . --plan ../operator-records/maintenance-plan.yaml
python .harness/engine/project-harness.py next --project .
python .harness/engine/project-harness.py verify --project . --allow-command-execution
python .harness/engine/project-harness.py complete --project . --result .harness/runtime/AGENT_RESULTS/<RUN-ID>.json
python .harness/engine/project-harness.py cancel-maintenance --project . --approval ../operator-records/maintenance-cancel.yaml
```

The plan is strict and exact-bound to `highest_accepted_level`, current target, last acceptance and accepted scope. Completion/cancel restores the previous route without invoking Stage acceptance or changing target/accepted maturity. Cancel is permitted only before completed/observed product-changing work and never performs automatic rollback. Open maintenance blocks `level-up`; terminal maintenance history does not.

Если принята target stage, project status становится `TARGET_LEVEL_REACHED`. Для дальнейшего движения требуется отдельный approval:

```bash
python .harness/engine/project-harness.py level-up   --project . --target MVP --approval ./level-up-approval.yaml
```

## 5. Brownfield maturity

Assessment выполняется без автоматического запуска build/test/deployment commands:

```bash
python project-harness.py assess-maturity   --workspace ./work/existing-project-intake   --evidence ./provided-evidence.yaml
```

`claimed_current_level`, `observed_candidate_level`, `highest_satisfied_candidate_level` и `highest_accepted_level` имеют разный смысл и не сворачиваются в одно `current_level`. Baseline acceptance разрешён только для `BROWNFIELD`/`HYBRID`, требует canonical `<assessment-id>@<positive-integer-revision>` и `sha256:<64 lowercase hex>`, открывает только exact file в `.harness/stages/ASSESSMENTS/` и создаёт отдельный report для каждой последовательно принятой стадии. Glob/latest fallback отсутствует; filename, exact envelope, internal id/revision и digest file bytes проверяются до Stage mutation. Затем отдельный freshness preflight связывает assessment с current product tree, canonical Stage State target, previous accepted level, immutable accepted claim и sequential candidate context. Drift или stale/other-base evidence возвращает structured `STALE`, создаёт только новую immutable validation revision и оставляет acceptance state неизменным.

## 6. Миграция v0.4.1 → v0.5.0

```bash
python project-harness.py migrate-project   --project /path/to/extracted-v0.4.1-project   --input /path/to/PROJECT_INPUT_v3.yaml
```

Для проекта без выполненных задач migration пересобирает stage-aware planning после подтверждения target. Для проекта с completed history история сохраняется, создаётся консервативная assessment/review route, а accepted level не выводится автоматически. Подробности: [`MIGRATION_FROM_v0.4.1.md`](MIGRATION_FROM_v0.4.1.md).

## 7. Canonical control-plane paths

```text
.harness/stages/STAGE_STATE.yaml
.harness/stages/PLANS/
.harness/stages/GATES/
.harness/stages/ACCEPTANCE/
.harness/stages/ASSESSMENTS/
.harness/stages/STATE_HISTORY/
.harness/stages/TRANSACTIONS/
.harness/operator/APPROVALS/  # optional safe in-project operator output
.harness/maintenance/PLANS/
.harness/maintenance/REPORTS/
.harness/maintenance/INDEX.yaml
.harness/maintenance/CURRENT.yaml
```

Uppercase directory names являются contract paths. Lowercase формы в пояснительных примерах не переопределяют Contract Catalog.

`TRANSACTIONS/<transaction-id>/TRANSACTION.yaml` сохраняет complete ordered write set, backups/staged paths, existed-before markers, old/new digests, status/timestamps, result digest и per-entry progress до первого canonical replace. Перед `APPLYING` durable journal, все backups и все staged digests проходят повторный preflight. `validate-project` автоматически reconciles pending transaction: full-new digests завершают commit, иначе verified backups восстанавливают full-old state; corruption или mixed `Stage indexes / CURRENT_STATE / NEXT_TASK / Acceptance` блокирует mutation без guess-based repair.

## 8. Состав комплекта

- [`00_Overview`](00_Overview/) — product scope, роли и lifecycle;
- [`01_Architecture`](01_Architecture/) — canonical architecture и control plane;
- [`02_Intake`](02_Intake/) — documentation-first intake и approvals;
- [`03_Planning`](03_Planning/) — traceability, DAG, Stage Plans и stage fence;
- [`04_Execution`](04_Execution/) — task/run state, Stage Gates, maturity и level-up;
- [`05_Updates`](05_Updates/) — Change Packs, migration и transactional updates;
- [`06_Git`](06_Git/) — целевая Git architecture; публикация не входит в v0.5.0;
- [`07_Security`](07_Security/) — trust boundaries и sensitivity taxonomy;
- [`08_Distribution`](08_Distribution/) — distribution и project-local layout;
- [`09_Delivery`](09_Delivery/) — реализованный Core boundary и roadmap;
- [`10_Contracts`](10_Contracts/) — canonical examples;
- [`11_Appendices`](11_Appendices/) — matrices, risks и validation basis;
- [`12_Implementation_Specifications`](12_Implementation_Specifications/) — 24 normative specifications;
- [`registries`](registries/) — seven machine-readable canonical registries;
- [`tools/validate_documentation.py`](tools/validate_documentation.py) — structural and semantic validator.

## 9. Canonical versions

```text
Engine distribution      0.5.0
Canonical schema         6
PROJECT_INPUT contract   SCHEMA-PROJECT-PREPARATION-INPUT@3
Project migration        MIG-ENGINE-0.4.1-TO-0.5.0

id_prefixes              2
project_profiles         1
statuses                 5
request_routing          2
capabilities             1
contracts                5
implementation_levels    1
```

`PROJECT_LOCK` фиксирует exact version и SHA-256 digest каждого registry.

## 10. Scope boundary

В v0.5.0 не входят automated Codex CLI/API Executor Adapter, rootless container sandbox, local commit/push/PR adapters, deployment execution route, declarative PROJECT skill authoring, parallel worktrees/leases и remote multi-user control plane. Эти механизмы не считаются реализованными из-за наличия архитектурных глав.

## 11. Проверка документации

```bash
python tools/validate_documentation.py . --build-aggregates
: "После отдельной сборки ZIP можно проверить архив:"
python tools/validate_documentation.py . --zip ../Project_Harness_Documentation_v0.5.0.zip
```

Validation проверяет exact registry views, Contract Catalog, lifecycle applicability, Stage contract examples, generated aggregates, manifest и ZIP tree. Runtime conformance подтверждается отдельным `TEST_REPORT_v0.5.0.md` архива движка.

## PH‑F01 interim verification record (2026-10-23)

The [PH‑F01 integration matrix](PH_F01_INTEGRATION_MATRIX.md) describes reproduction fixtures, actual public CLI/API stage-boundary status and negative Gate evidence tests. At the PH‑F01 checkpoint, PH‑F02 and PH‑F03 defects were still open; that record is retained as historical evidence. The current PH‑F02 patch closes the semantic Gate-proof regression, while the active-stage planner regressions remain intentionally RED until PH‑F03. This is not the final v0.5.0 release. The engine archive includes execution reports.

## PH‑F02 evidence hardening (2026-10-24)

Stage Gate accepts only exact subject-specific semantic proof, never a generic verification PASS; see `04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md`. PH‑F03 subsequently adds the public active-stage planner; the PH‑F02 evidence contract remains unchanged.

## PH‑F03 public next-stage planner (2026-10-24)

После `accept-stage` либо `level-up` при `PLAN_ACTIVE_STAGE` теперь доступен
публичный цикл `prepare-active-stage-plan --project <root> --output <record>` →
`plan-active-stage --project <root> --plan <reviewed-record>` → `next`.
Он выпускает строго текущие Task/JIT, использует точный accepted scope,
Gate/Stage binding и crash-consistent commit; подробные поля и восстановление
см. `03_Planning/07_Implementation_Levels_and_Stage_Plans.md`.
Ограничения PH‑F02 на подлинные Gate evidence сохраняются.
Этот PH‑F03 checkpoint не является полным PH‑F08 release gate.

## PH‑F04 — runtime reachability (2026-10-24)

`next` и `stage-status` показывают исполнимое `next_operator_route` с точной CLI-командой или внешним prerequisite. `validate-project` проверяет фактическое существование continuation в CLI и согласованность Stage State/Plan/Gate/Task/Run; ожидание formal review не считается дефектом. Маршруты planning, Gate review/recovery, ordinary Task blockers, `TARGET_LEVEL_REACHED` и same-level maintenance различаются. Операторский status/route matrix приведён в [`08_Distribution/03_User_Workflows.md`](08_Distribution/03_User_Workflows.md).

## PH‑F08 — финальная интеграционная приёмка (2026-10-25)

Финальные сценарии I-01–I-14 проверены через публичный Engine CLI/API, отдельную установку wheel, `doctor`, validators и ZIP-манифесты. Итоги, полные реальные логи и release verdict см. в `PH_F08_TEST_REPORT.md` из Engine ZIP и [`08_Distribution/05_PH_F08_Release_Acceptance.md`](08_Distribution/05_PH_F08_Release_Acceptance.md). Semantic Gate proof, formal approvals, stage fence, immutable history и ограничения без локального Codex Executor неизменны.

PH-LW-11: [Windows установка и resume](13_Local_Web_Manual_Companion/19_PH_LW_11_Windows_Installation.md). Фактическая приёмка — отдельный Engine report; полный release остаётся NOT RELEASED.

Дополнение PH-LW-11: [long-path подготовка без изменения Windows settings](13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md). Предыдущий report сохранён; фактические повторные проверки — в новом Engine report.

[PH-LW-11: ZIP-import при длинном app-data root](13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md). Текущий scoped fix и ограничения — в новом отчёте Engine.
