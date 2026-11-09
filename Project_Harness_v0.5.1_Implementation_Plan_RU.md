# Project Harness v0.5.1 — поэтапный план реализации Local Codex CLI Executor и Rootless Container Sandbox

**Статус:** PLAN / NOT IMPLEMENTED. Этот документ не является отчётом о выполнении v0.5.1.  
**Дата подготовки:** 2026-10-25.  
**База:** финальная поставка Engine + Documentation v0.5.0 с PH-F08.  
**Целевая версия:** v0.5.1, PATCH / controlled local execution.  
**Локальные ID пакетов:** `PH-051-01` … `PH-051-12` — только идентификаторы этого плана, не нормативные issue IDs и не новые Implementation Levels.

## 1. Исходная база и нормативная иерархия

1. `Project_Harness_Engine_v0.5.0.zip` — SHA-256 `257aee9fb190a8cd09a6d5bbde6eca9a77fe58b25b09ad9f956d1ef260e5e6af`.
2. `Project_Harness_Documentation_v0.5.0.zip` — SHA-256 `4f02f68f7d0a50ac17f0bb118a2c45e3bb2e240d01dfc74f1b6b57eab66cb9aa`.
3. Нормативная `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` из `Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0.zip` (SHA-256 содержимого документа `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`). Разделы 1–25 определяют контракт v0.5.1.
4. Нормативная `02_Project_Harness_v0.5.0_Implementation_Levels.md`, embedded `12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`, а также действующая документация об agent adapter, execution, verification, transactions, миграциях и registries.
5. Текущие архивы включают `PH_F08_TEST_REPORT.md` и `PH_F08_ACCEPTANCE_MATRIX.md`: отчёт заявляет `I-01–I-14 = PASS`, `168/168` unit/regression tests, `GO` для **v0.5.0 с внешним исполнителем**. Это исходная заявленная приёмка, а не новый прогон тестов при составлении плана.

**Приоритет:** нормативная спецификация v0.5.1 → действующие v0.5.0 contracts/invariants → точная фактическая исходная кодовая база → этот план. Если обнаружено противоречие в версиях реестров, его необходимо письменно разрешить перед изменением контрактов; нельзя маскировать конфликт фиктивной совместимостью.

### 1.1. Обнаруженное несоответствие реестров (обязательный preflight)

Фактические версии в предоставленном v0.5.0 Engine:

| Registry / contract | В исходном ZIP | Указано в нормативной v0.5.1 (§19.1) | Правило |
|---|---:|---|---|
| `REG-ID-PREFIXES` | 2 | `2 → 3` | Плановый переход 2 → 3 |
| `REG-LIFECYCLE-STATUSES` | 5 | `5 → 6` | Плановый переход 5 → 6 |
| `REG-CONTRACT-CATALOG` | **5** | **`4 → 5`** | Коллизия: версия 5 уже существует |
| `SCHEMA-PROJECT-PREPARATION-INPUT` | `@3` | `@4` | Добавить строгий @4 с migration/compatibility |
| Harness `SCHEMA_VERSION` | 6 | 7 | Совместимый переход 6 → 7 |

**Предлагаемое разрешение:** сохранить существующий `REG-CONTRACT-CATALOG@5` и при действительно изменённом каталоге выпускать следующую свободную revision **5 → 6**, занеся расхождение нормативного ожидаемого стартового номера в `IMPLEMENTATION_DECISIONS`/migration note и проверив все consumers/project locks. Это *предложение совместимого решения*, а не утверждение, что текст спецификации уже изменён. Если контракт требует строго номер 5, пакет `PH-051-01` должен честно завершиться `BLOCKED` до принятого решения: запрещены downgrade, перезапись существующей версии или ложный PASS.

## 2. Цель и граница версии

Обеспечить один поддерживаемый автоматический путь:

```text
READY Task → JIT Prompt Bundle → Local Codex CLI
           → ROOTLESS_PODMAN / disposable product
           → exact Agent Task Result → independent SANDBOXED verification
           → validated diff → atomic/recoverable apply
           → completion according to project policy → next Task
```

**Выпускать только вместе**: `CODEX_CLI_LOCAL` Executor Adapter и `ROOTLESS_PODMAN` Sandbox backend. Даже если adapter готов, без проверенной изоляции `execute-current` не должен запускать процесс на host. Manual handoff остаётся поддерживаемым и выбираемым оператором; *ошибка sandbox не запускает manual или host execution автоматически*.

Нормативные зоны доверия:

- `HARNESS_DISTRIBUTION` — исходники/схемы/реестры, недоступные агенту на запись;
- `PROJECT_CONTROL` — `.harness`, агент не получает `PROJECT_CONTROL_WRITE`; kernel читает/пишет только свои bounded records;
- `CANONICAL_PRODUCT_ROOT` — настоящий проект пользователя, не монтируется agent на запись;
- `DISPOSABLE_EXECUTION_ROOT` — отдельный временный product snapshot; только здесь работает CLI agent и sandbox verifier.

### 2.1. Нельзя расширять scope

Не добавлять provider HTTP API, альтернативные модели/CLI/backends, unsandboxed execution, Git commit/push/PR, deployment, remote workers, VM, параллельные агенты, interactive proxy, token accounting, arbitrary destination allowlist, хранение секретов в `.harness`, shell interpolation пользовательских полей, недоверенный direct copy поверх canonical root. Всё перечисленное относится к отдельным будущим версиям либо явно исключено §2 спецификации.

### 2.2. Инварианты v0.5.0 должны сохраниться

- `PROTOTYPE → ALPHA → BETA → MVP → RELEASE` последовательно, только governed Stage Gate/level-up; target не расширяет accepted project scope; планирование только active Stage.
- Stage State — canonical target; initial accepted `PROJECT_INPUT`, принятую историю, Stage Acceptance Reports и completed Runs не переписывать.
- Exact refs, baseline/digest, semantic evidence, formal approvals, Brownfield read-only assessment и same-level maintenance — без регрессий.
- `next → verify → complete`, `prepare-stage-approval`, `accept-stage`, `prepare-active-stage-plan`, `plan-active-stage`, `level-up` и migration v0.4.1→v0.5.0 продолжают работать.
- Для automatic verification применимы только реальные исходы независимой проверки; generic PASS не становится подтверждением иных Gate subjects.
- Изменения control-plane и product apply защищены от частичных commit, повторов и прерываний; проверка Stage transactions после каждого затрагивающего шага.

## 3. Контракт публичного результата v0.5.1

Новые команды — только те, что требует спецификация:

```bash
project-harness executor-doctor --project <root>
project-harness execute-current --project <root>
```

Опции: `--adapter-profile <id-or-path>`, `--network NONE|EXPLICIT_APPROVED_EGRESS`, `--approval <record-path>` (только когда требуется), `--keep-execution-root` (только при разрешённой debug policy). Требуются Python API, documented status, correct exit codes, `next`/status continuation. Название существующих CLI-команд менять нельзя.

Семантика: automatic default network `NONE`; расширение до `EXPLICIT_APPROVED_EGRESS` — только с `NETWORK_WRITE`, `MODEL_EXTERNAL_EGRESS` и формальным exact Run-bound approval; per-Run approval нельзя заменить постоянной настройкой. Режим `NONE` должен реально запрещать сеть. Rootless, pinned image digest, read-only container rootfs, non-root UID, all caps dropped, no-new-privileges, bounded resources и безопасные mounts — обязательные **технические** свойства, не только YAML-декларации. `UNKNOWN` критичного self-test блокирует automatic activation.

Strict execution policy в новом `PROJECT_INPUT@4`:

```yaml
execution:
  mode: MANUAL_HANDOFF
  adapter_profile_ref: null
  sandbox_profile_ref: null
  network_mode: NONE
  completion_policy: EXPLICIT_AFTER_VERIFICATION
```

`LOCAL_AUTOMATIC` требует active exact adapter/sandbox refs, явную активацию и successful doctor. `AUTO_AFTER_PASS` разрешён только закреплённой policy после независимой verification. Секреты только в allowlisted environment refs; raw values не хранятся в Project Input, configs, plans, logs, archive или result.

## 4. Очерёдность отдельных implementation packages

| Пакет | Назначение | Зависимость | Приёмочная граница |
|---|---|---|---|
| **PH-051-01** | Contract/schema/registry baseline и execution policy | v0.5.0 PH-F08 | Строгие контракты, безопасный manual default, разрешена коллизия registry |
| **PH-051-02** | Минимальный Executor Adapter, fake CLI и argv policy | 01 | Нет host-execution path, детерминированные test doubles |
| **PH-051-03** | Единственный Rootless Podman runner + doctor | 01–02 | Isolation/self-test fail-closed, не pseudo-sandbox |
| **PH-051-04** | Disposable execution root + read-only control projection | 03 | Agent отделён от canonical product и `.harness` |
| **PH-051-05** | Local Codex CLI Adapter через validated `argv_template` | 02–04 | Реальный argv без shell, bounded process/exit classification |
| **PH-051-06** | Exact result channel, normalized result, secrets/logs | 04–05 | Agent result и логи не могут обойти boundary |
| **PH-051-07** | Independent SANDBOXED verification | 03–06 | Аgent PASS не заменяет kernel verification |
| **PH-051-08** | Diff/write-scope gate + atomic apply journal | 04–07 | Canonical root меняется только после PASS; rollback |
| **PH-051-09** | Governed Run lifecycle и публичный CLI/API | 01–08 | `execute-current` интегрирован, все failure routes явные |
| **PH-051-10** | Migration, cleanup, orphan/crash recovery, idempotency | 08–09 | Старые проекты/Рuns сохранены, no partial apply |
| **PH-051-11** | Operator docs/examples + полная security matrix | 01–10 | Docs описывают проверенные публичные интерфейсы |
| **PH-051-12** | Финальный E2E regression/security release gate и ZIP packaging | 01–11 | GO/NO-GO с доказательствами, согласованные два ZIP |

**Правило промежуточных этапов:** каждый пакет — отдельный диалог с последними архивами, ограниченными изменениями и новой парой Engine/Documentation ZIP. Пока `PH-051-12` не завершён, пакеты имеют статус **v0.5.1 WIP / NOT RELEASED**. Запрещено предъявлять готовность автоматического режима по green unit tests без реального Podman security integration.

## 5. Подробные implementation packages

### PH-051-01 — Contracts, registries, schema versioning, explicit execution policy

**Нормативные разделы:** 5, 7, 17, 18, 19, 19.1, 21.  
**Допустимые области:** `schemas/` и package-resource mirrors, `registries/{id_prefixes,statuses,contracts}.yaml` с package mirrors, `project_input.py`, `compiler.py`/project lock builders в объёме metadata, validation, contract docs/migration note, tests. Не изменять runtime execution.

1. Снять baseline diff всего control contract; разрешить коллизию contract registry version 5 (см. §1.1).
2. Добавить `SBX` как самостоятельный ID и lifecycle `sandbox_profile`, не подменяя `ADP`. Переиспользовать существующий `agent_adapter_profile` для executor; не создавать дубликат contract для ADP.
3. Добавить строгие schemas `executor_profile.schema.json`, `sandbox_profile.schema.json`, `execution_result.schema.json`, `apply_evidence.schema.json`; storage contracts `.harness/config/SANDBOXES/{id}@{revision}.yaml`, `.harness/runtime/EXECUTION_RESULTS/{id}.yaml`, `.harness/evidence/{id}.yaml`.
4. Переход `SCHEMA-PROJECT-PREPARATION-INPUT@3 → @4`, Harness SCHEMA_VERSION `6 → 7`, exact profile refs/digests и registry versions в PROJECT_LOCK. Не переписывать уже принятые immutable input/Run.
5. Добавить strict `execution` policy с default `MANUAL_HANDOFF`, без секретов/argv/mounts и явным opt-in для `LOCAL_AUTOMATIC`; реализовать compatible reading/migration для старых inputs/locks с documented boundary.
6. Положительные/отрицательные contract tests: schema unknown field, mutable image tag, unknown profile backend, missing exact refs, forbidden network, invalid secret data, incompatible profile status, replay unchanged.

**Приёмка:** schema/registry validator PASS, current manual lifecycle/168 baseline tests не ломаются; записи exact-bound; registry conflict разрешён прозрачно. Automatic invocation ещё отсутствует.

### PH-051-02 — Executor Protocol и deterministic fake CLI fixtures

**Нормативные разделы:** 4–5, 23.1–23.2.  
**Допустимые области:** `src/project_harness/executors/{__init__,base,codex_cli_local,result}.py` (только минимальные interfaces/argv normalization), отдельные fixtures и tests; без полноценного CLI/runtime mutation.

1. Реализовать `ExecutorAdapter` минимального состава: `doctor`, `prepare_invocation`, `execute`, `normalize_result`; `execute` не может исполнить `subprocess` напрямую на host в release workflow и должен передавать invocation trusted sandbox runner.
2. Проверять argv list, exact executable policy, allowed placeholders `{prompt_bundle_path}`, `{context_packet_path}`, `{agent_result_path}`, `{workspace_path}`, `{run_id}`, `{task_id}`. Reject неизвестные placeholders, command strings, redirect/pipeline/shell modes и arbitrary text substitution.
3. Создать один fake Codex **test double**, не второй публичный adapter. Для fixtures: success, exit nonzero, timeout, invalid/missing output, flood, child process, control write, wrong paths, secret echoes, baseline drift.
4. Unit negative test: даже если sandbox dependency недоступна, fake adapter не запускает CLI на host.

**Приёмка:** tests подтверждают deterministic argv+failure mapping, отсутствует unsandboxed fallback. Automatic route ещё не активен.

### PH-051-03 — Rootless Podman Sandbox Runner и честный doctor

**Нормативные разделы:** 6–8, 10, 14, 20, 23.3.  
**Допустимые области:** `src/project_harness/sandbox/{__init__,base,podman_rootless,profiles}.py`, resources/profile validation, focused tests и docs; не добавлять Docker/VM/remote альтернативы.

1. Один backend `ROOTLESS_PODMAN`, image строго `@sha256:<digest>`; enforce rootless/non-root UID, readonly rootfs, drop ALL capabilities, no-new-privileges, bounded CPU/memory/pids/timeout/output.
2. Защитить mount policy: disposable product `/workspace/product:rw`, bounded control projection `/workspace/control:ro`, exact output `/output:rw`, tmpfs `/tmp`, ephemeral HOME. Не монтировать host home, canonical project, sockets/SSH/cloud credentials и `.harness:rw`.
3. `NONE` использует `--network=none`; `EXPLICIT_APPROVED_EGRESS` допускается только через policy/approval, без ложного обещания destination allowlist. При `SECRET`/`REGULATED` sensitivity external model egress запрещён без отдельной explicit project-policy allowance и допустимого adapter profile. Запретить `--network=host`, inbound mapping, privileged flags.
4. Реальные self-tests: rootfs/control write fail, output mount works, effective non-root, caps dropped, home/socket absent, network none cannot egress, stop/timeout, configured executable available.
5. Если Podman/image/проверка отсутствует, вернуть fail/unknown с actionable diagnostic, automatic mode BLOCKED; нельзя объявлять PASS на mocks. Distribution doctor может диагностировать недоступность optional automatic executor, не ломая ручной режим без Podman.

**Приёмка:** документированные Podman security integration tests проходят на подходящем стенде; нет пути запуска agent при `SANDBOX_UNAVAILABLE`.

### PH-051-04 — Disposable root, baseline binding и bounded control projection

**Нормативные разделы:** 3, 8, 12, 18.  
**Допустимые области:** runtime root builder/projection в минимально затронутых модулях, `safety.py`, `archive.py`, metadata и tests.

1. На каждый Run создавать отдельный product snapshot вне canonical repository: `<configured-runtime-root>/<project-id>/executions/<RUN_ID>/product`.
2. Копировать исключительно product plane, исключая `.harness`, generated control files и небезопасные symlinks; сохранять immutable base tree digest, control plane digest, Task/JIT refs.
3. В `/workspace/control` выдавать только соответствующие текущему Run Prompt Bundle, Context Packet, Task Contract, Run Plan, разрешённую конфигурацию и необходимые schema. Делать projection read-only.
4. Metadata-only execution binding в `.harness/runtime/EXECUTION_BINDINGS/`; не включать execution root в exports/handoff/project lock.
5. Проверять, что canonical root digest не меняется из-за построения/работы disposable root; concurrent modification делает future apply `BASELINE_CHANGED`.

**Приёмка:** попытка изменить canonical control/product из disposable environment технически невозможна; creation/reuse root безопасны при replay.

### PH-051-05 — Реальный Local Codex CLI Adapter

**Нормативные разделы:** 4–5, 10–11, 15.  
**Допустимые области:** `executors/codex_cli_local.py`, profile loading, invocation/exit classification, tests. Не менять kernel evaluation/adapters API.

1. Реализовать единственный `CODEX_CLI_LOCAL` из active `ADP` profile и validated `argv_template` как массив аргументов, `shell=False`.
2. Не зашивать предполагаемый синтаксис Codex CLI в Kernel. `doctor` проверяет executable в pinned container image; тестовый real profile фиксирует фактически поддерживаемые flags. Test fake CLI запускается **в контейнере**, а не в host unsandboxed route.
3. Соблюдать `stdin_mode: CLOSED`, bounded timeout/grace/kill, environment allowlist и consistent exit/termination codes.
4. Подготовить JIT Prompt Bundle, Task и exact result destination, а не просить агента решать собственный Run authorization.

**Приёмка:** процесс вызывается через rootless runner; отсутствует второй public provider; container missing → не запускается host Codex.

### PH-051-06 — Exact result channel, provenance, environment/secrets и logs

**Нормативные разделы:** 9, 11, 19, 23.1–23.2.  
**Допустимые области:** `executors/result.py`, sandbox output validation, `safety.py`, schema validators, focused tests и docs.

1. Считаем единственным обязательным agent output `/output/agent-result.json`, который заранее создан/разрешён policy. Контроль: regular file, exact path, ownership/mode, size, no symlink/hardlink escape, valid bounded UTF-8/JSON.
2. Валидировать существующий `SCHEMA-AGENT-TASK-RESULT@1`, отдельно нормализовать execution result (`ART-*`) и bounded `stdout/stderr` refs; kernel сам сохраняет `.harness/runtime/AGENT_RESULTS/<RUN>.json`.
3. Дополнительные `/output` файлы — reject, кроме явных declared outputs и bounded kernel logs.
4. В profile допускаются только refs на env secrets; разрешать только явные переменные, никогда full host env. No secret values in schema, execution records, logs или ZIP.
5. Exact-value redaction + fail-closed secret leak detection в stdout/stderr/result; проверка изменённых product files перед apply — обязательная интеграция с PH-051-08.
6. Негативные проверки: missing/oversize/invalid result, link tricks, non-regular file, echo secret, injected shell-looking JSON, output flood; ни один случай не даёт optimistic PASS.

**Приёмка:** собственный текст/exit-0 агента не является доказательством завершения; outputs связаны с exact Run без уязвимого shared directory.

### PH-051-07 — Независимая проверка SANDBOXED

**Нормативные разделы:** 3.3, 14–15, 23.4.  
**Допустимые области:** `runtime.py`/verification helpers и sandbox command path, тесты; сохранять исторический `verify --allow-command-execution` manual mode.

1. Для automatic Run запускать declared verification argv в separate sandbox process внутри disposable product, не внутри agent process.
2. Sandbox verifier не получает agent secrets по умолчанию, использует `NONE` network кроме отдельно разрешённой policy, свои timeout/output limits.
3. Сверять actual changed paths с Task Contract, persisted baseline, independent verification results, control-plane invariants; exit 0 агента не заменяет verification.
4. Fail/timeout/wrong-path → `VERIFICATION_FAILED`/соответствующий reason, canonical root неизменен. Result evidence привязывается к реально проверенным subjects, а не всем Stage Gate claims.
5. Manual flow и existing stage/maintenance verification semantics остаются совместимыми.

**Приёмка:** test с агентским `COMPLETED` и заведомо проваленной независимой проверкой не вызывает apply/complete.

### PH-051-08 — Validated diff, path fence, secret scan и crash-consistent apply

**Нормативные разделы:** 12–13, 18–19, 22–23.  
**Допустимые области:** новый `src/project_harness/apply.py`, `safety.py`, минимальный runtime integration для apply records и tests.

1. Строить file-level diff от сохранённого snapshot; reject special files, sockets/devices, unsafe symlinks, unexpected deletes/adds. Динамический file write set должен попадать в Task Contract permitted scopes; expected writes проверяются отдельно.
2. Scan exact secret values в changed files, Agent Result и bounded logs; проверять declared project scan policies, но не объявлять общую «универсальную DLP».
3. Apply разрешён исключительно после independent PASS и повторной exact проверки **canonical baseline digest**; mismatch → `BASELINE_CHANGED`, без частичного переноса.
4. Создавать write plan с exact paths/content hashes. Для create/replace/delete — staging+fsync где применимо, durable journal/backups, deterministic rollback/recovery после crash. Не использовать небезопасное recursive copy.
5. Подписывать/сохранять immutable Apply Evidence (`EVD-*`) с before/after digests, write set, Run ref и verification binding; не переписывать historic evidence.
6. Fault injection между staged operations: atomic all-old/all-new, повтор safe, failure → `APPLY_FAILED_RECOVERABLE`, следующий запуск сначала recovery.

**Приёмка:** даже при crash на середине apply нет смешанного canonical product state; agent не имеет прямого доступа к нему.

### PH-051-09 — Governed automatic Runtime, CLI/API и route semantics

**Нормативные разделы:** 15–18, 20.  
**Допустимые области:** `runtime.py`, `cli.py`, `validation.py`, targeted API exports, status routing, tests и docs; минимальная интеграция готовых компонентов.

1. Добавить public `executor-doctor` и `execute-current`, Python APIs и structured envelopes с точными exit/status semantics; поддерживать только текущую `READY` Task/JIT и разрешённый Run context.
2. Поверх готовых `PH-051-02`–`08` оркестрировать `READY → RUNNING → VERIFYING → SUCCEEDED` с fail routes `TIMED_OUT`, `FAILED_RETRYABLE`, `BLOCKED`; reason codes строго из §15, включая sandbox, network, secrets, invalid result, scope, baseline, verification, apply.
3. Применять config precedence `distribution defaults < project profile < approved per-run narrowing`. Любое расширение разрешений — отдельное approval и новая revision Run Plan; нельзя повышать mounts/secrets/egress скрыто.
4. `AUTO_AFTER_PASS` только по explicit policy; иначе после controlled verification/apply ожидается documented explicit completion; не подменять user approval в Stage Gate.
5. Реализовать safe replay/idempotence: новый retry — новый immutable Run revision, не overwrite старого; stable project status и `next` без пропуска стадии.
6. `execute-current` на `MANUAL_HANDOFF` не активирует автоматический путь без явного opt-in, а при failing doctor возвращает `BLOCKED / SANDBOX_UNAVAILABLE` без fallback на host.

**Приёмка:** реальный публичный сценарий через fake Codex-in-Podman даёт ожидаемый статус и готовность следующей Task; manual route регрессий не имеет.

### PH-051-10 — Migration, termination, cleanup, interrupted-Run recovery

**Нормативные разделы:** 17, 19.1, 21–22.  
**Допустимые области:** `migration.py`, cleanup/recovery runtime и sandbox modules, PROJECT_LOCK/build metadata, docs/tests; не переписывать v0.5.0 Stage/Brownfield logic.

1. Реализовать migration `MIG-ENGINE-0.5.0-TO-0.5.1` с обязательной default policy `MANUAL_HANDOFF`, refs = `null`, network `NONE`, completion `EXPLICIT_AFTER_VERIFICATION`.
2. Сохранять immutable `PROJECT_INPUT_ACCEPTED`, Stage Acceptance Reports, completed manual Runs и exact historical Stage refs. Новые Runs получают `execution_origin: MANUAL_EXTERNAL | LOCAL_AUTOMATIC`.
3. Реализовать reliable SIGTERM→bounded grace→SIGKILL; container children завершаются вместе с container; state truthfulness для timeout, nonzero, missing result/cleanup.
4. Обнаруживать после host crash orphan container по labels и execution root; quarantined до проверки/cleanup; старый partial result не использовать для нового Run.
5. Apply journal recovery должен завершиться до нового attempt; повтор той же approved operation не дублирует result/Run/Apply Evidence.
6. Масштабную raw workspace/log data не включать в handoff/export; manifests и lock включают только согласованные bounded records/metadata.

**Приёмка:** migration idempotent, manual projects продолжают работать без Podman; pre-/post-commit interruptions не меняют historical v0.5.0 records.

### PH-051-11 — Operator documentation, examples, Podman security validation

**Нормативные разделы:** 16, 20–24; документация v0.5.0 (Execution/Contracts/Migrations).  
**Допустимые области:** README, MANUAL_INSTALL, GPT preparation instructions, `01_Architecture/`, `04_Execution/`, `05_Updates/`, `10_Contracts/`, `12_Implementation_Specifications` (только добавочное описание v0.5.1), examples, metadata, targeted tests; production runtime — только прямые найденные regression fixes.

1. Прописать единый runbook: external GPT source/intake → approved `PROJECT_INPUT@4` → prepare/handoff → manual/default либо explicit automatic opt-in → `executor-doctor` → `next` → `execute-current` → sandbox verifier/apply → next/blocked recovery → Stage Gate. Не выдавать agent-run за автоматическое формальное acceptance.
2. Дать strict profile/approval examples для `ADP`, `SBX`, per-Run egress, references to secret env; не вставлять реальные credentials или неподтверждённый mutable image tag.
3. Документировать различие `NONE` и `EXPLICIT_APPROVED_EGRESS` (нет per-host allowlist), limitations Podman, negative self-tests, inaccessible container image, cleanup/debug policy, safe manual fallback **по выбору**.
4. Выполнить реальную security matrix: read-only root/control, non-root, empty capabilities, no-new-privileges, no host home/sockets, no external net в `NONE`, pids/memory/time caps, bounded result channel, symlink/special-file and secret-leak negative tests. Отдельно зафиксировать проверенную версию Podman, platform, pinned image digest и команды.
5. Внешний операторский smoke по **опубликованным** CLI flags через installed wheel и bundled entrypoint. Синхронизировать embedded/standalone docs и distributable prompt template.

**Приёмка:** при отсутствии реального Podman стенда security matrix = `NOT TESTED / NO-GO`, не `PASS` по mocks; оператор может воспроизвести действия без private Python.

### PH-051-12 — Финальная интеграционная приёмка и release packaging

**Нормативные разделы:** 23–25.  
**Допустимые области:** финальные integration/acceptance tests, прямые release-blocking regressions, версии/package/docs/manifests, отчёты и ZIP; никакого функционала v0.6.0.

1. Прогнать все старые regression tests (в исходном PH-F08 было 168) плюс новые v0.5.1 — по финальным packaged source, не только staging worktree.
2. Прогнать матрицу §6, включая **реальный rootless Podman** и fake CLI внутри него, а также negative security cases и manual fallback.
3. Прогнать `doctor`, `executor-doctor`, docs validator, `validate-handoff`, `validate-project`, wheel install from fresh environment, CLI smoke и public APIs; проверить enabled automatic и manual-only без Podman.
4. Проверить `PROJECT_LOCK`, exact registry/schema versions, migration 0.5.0→0.5.1, every schema/resource mirror, manifest checksum и executable modes.
5. Проверить absence of leaked secrets в ZIP/logs/records; no raw execution roots/orphan control data в release archive.
6. Собрать два согласованных ZIP `Project_Harness_Engine_v0.5.1.zip` и `Project_Harness_Documentation_v0.5.1.zip`, SHA-256, changed-file list, test log, release matrix и явное GO/NO-GO. При незавершённых mandatory tests/несоответствиях — честное NO-GO.

**Приёмка:** все нормативные критерии §24 доказаны; v0.5.0 semantics не регрессировали; никаких утверждений «sandbox verified» без успешного фактического security run.

## 6. Сквозная матрица acceptance v0.5.1

Номера ниже — локальные test scenarios этого плана; соответствие нормативной §24 обязательно.

| ID | E2E/negative проверка | Expected |
|---|---|---|
| E-01 | Fresh `PROJECT_INPUT@4`, manual default → prepare/next/verify/complete | Тот же manual route, нет auto activation |
| E-02 | Migration живого v0.5.0 Project Instance | Только новый default/manual projection; immutable history неизменна |
| E-03 | Explicit `LOCAL_AUTOMATIC` + rootless doctor PASS + fake CLI success | Отдельные agent/verification processes, safe apply, Task DONE/next |
| E-04 | Podman отсутствует/не rootless/нет image digest | `BLOCKED / SANDBOX_UNAVAILABLE`, ни одной host CLI invocation |
| E-05 | Изменение `/workspace/control`, rootfs, host home/sockets | Технически запрещено; negative tests PASS |
| E-06 | `NONE` network; попытка outbound | Egress реально недоступен |
| E-07 | Egress без двух capabilities/Run approval либо SECRET/REGULATED без отдельного project-policy разрешения | `NETWORK_NOT_APPROVED`, нет запуска |
| E-08 | Секрет отсутствует, выведен в logs/result/product diff | `SECRET_REFERENCE_MISSING`/`SECRET_LEAK_DETECTED`, нет apply/leak в ZIP |
| E-09 | Missing/malformed/oversized/unsafe `/output/agent-result.json` | `RESULT_MISSING/INVALID` либо bounded failure, нет success |
| E-10 | Illegal paths, special files, unsafe links, deletion beyond scope | `SCOPE_VIOLATION`, canonical root bytes untouched |
| E-11 | Agent exit 0 / `COMPLETED`, independent verification FAIL | `VERIFICATION_FAILED`, no apply/complete |
| E-12 | Canonical product поменялся во время execution | `BASELINE_CHANGED`, no apply |
| E-13 | Interrupted atomic apply (несколько fault points) | Recovery all-old либо all-new, no mixed canonical state |
| E-14 | Timeout, child process, output flood | Bounded termination, accurate statuses, no false success |
| E-15 | Host crash/orphan execution root/container | Quarantine/recovery; retry не принимает старый partial result |
| E-16 | Duplicate/stale approvals, repeated execute/current, Run retry | Strict rejection/idempotence; старые Runs/reports immutable |
| E-17 | Greenfield stages, Stage Gate, level-up, Brownfield, maintenance | Все PH-F08 и v0.5.0 regressions сохраняются |
| E-18 | Wheel installation, source entrypoint, docs validation, ZIP manifest | PASS на финальной доставляемой паре архивов |

Особо проверить три разных статусных события: *исполнение agent*, *independent PASS verification*, *apply+completion*. Ни один из них не заменяет формальную Stage Acceptance/level-up decision.

## 7. Правила выполнения каждого отдельного пакета

1. **Отдельный диалог на `PH-051-NN`**. На вход — последние **успешно собранные** Engine/Documentation ZIP, архив нормативных спецификаций и этот план. Не работать на старой base по одной лишь одинаковой версии имени.
2. Сначала проверить входные SHA-256/manifest и актуальную границу implementation; перечислить `allowed file changes`. Действия пакета ограничиваются его областью; внеобластной найденный defect регистрируется, не исправляется самовольно.
3. Изменения production code требуют unit + targeted negative + integration теста своего контракта, потом контроль всего сохранённого предыдущего lifecycle. Если среда не поддерживает real Podman, явно указывать `NOT RUN` и сохранять fail-closed code; **не разрешать автоматическое исполнение** до настоящих security tests.
4. После каждого пакета выдавать два новых ZIP (Engine+Documentation), `PH_051_NN_CHANGED_FILES.md`, `PH_051_NN_TEST_REPORT.md`, соответствующие logs/fixtures и list preserved invariants. Предыдущие accepted artifacts/отчёты не переписывать.
5. Поддерживать source/package resources/embedded docs/wheel/standalone documentation sync, со строгими SHA-256 manifests. Указывать version и статус `WIP`, пока `PH-051-12` не примет release.
6. Не заявлять GO на основании одного `doctor`, unit PASS, fake CLI вне container или валидного handoff. Для security утверждений нужны фактические rootless Podman tests.
7. При direct conflict нормативного ожидания и поставленных actual registries не скрывать его: зафиксировать rationale/resolution и exact test coverage; если решение не утверждено — `BLOCKED`, без изменения уже закреплённого реестра.

### 7.1. Проверочные команды, существующие в исходной v0.5.0

```bash
# Из корня Engine source tree
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py
PYTHONPATH=src:. python project-harness.py doctor
python tools/validate_documentation.py . --zip <documentation-zip> --json <report.json>

# На установленном wheel / с тестовым Project Instance
project-harness --version
project-harness doctor
project-harness validate-handoff --project <handoff-zip>
project-harness validate-project --project <project-root>
project-harness next --project <project-root>
project-harness stage-status --project <project-root>
```

Команды `executor-doctor` и `execute-current` начнут существовать только после пакета `PH-051-09`; нельзя писать в отчёте раннего этапа, что они уже прошли. Команды из спецификации с placeholders — контракты, а не свидетельство реально выполненной проверки.

## 8. Готовые стартовые промты для отдельных диалогов

Общая формула каждого: «Используй последние обновлённые Engine/Documentation ZIP, нормативную `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` и `Project_Harness_v0.5.1_Implementation_Plan_RU.md`; исполни **только PH-051-NN**; не расширяй scope; проведи targeted negative tests и регрессии; верни два новых ZIP, changed-file list, test report и фактические логи; не называй промежуточный пакет финальным релизом».

**PH-051-01.** Реализуй только contracts/registries/schemas и default opt-in `PROJECT_INPUT@4`. Начни с фактической коллизии `REG-CONTRACT-CATALOG@5` vs normative `4→5`: разреши её документированным backward-compatible version decision или остановись с явным `BLOCKED`; не переписывай историю и не добавляй автоматический запуск.

**PH-051-02.** Реализуй только минимальные interfaces `ExecutorAdapter`, argv-template validation и fake Codex fixtures. Запрети shell/unsandboxed execution; проверь все разрешённые placeholders, bad argument/secret cases; CLI automatic route не добавляй.

**PH-051-03.** Реализуй только `ROOTLESS_PODMAN` sandbox backend, pinned image profile и honest doctor/self-tests. Протестируй реальные OS boundaries, если доступно; если нет — зафиксируй environment blocker, но не симулируй успешную isolation acceptance и не добавляй fallback.

**PH-051-04.** Реализуй per-Run disposable product snapshots, exact baseline/control projection и metadata bindings, не монтируя canonical root/`.harness` на запись. Добавь path-escape/byte equality tests; не реализуй diff apply.

**PH-051-05.** Реализуй ровно один local Codex CLI adapter через validated argv profile и уже готовый Podman runner. Не фиксируй CLI syntax в Kernel, не добавляй HTTP API/второй adapter.

**PH-051-06.** Реализуй strict `/output/agent-result.json` validation, normalized result/refs, bounded logs, secret ref allowlist/redaction. Добавь negative fixtures for invalid path/type/oversize/secret echo; canonical product не меняй.

**PH-051-07.** Реализуй independent automatic SANDBOXED verification отдельным process, сохраняй manual `verify` semantics. Никакой apply при FAIL/UNKNOWN и никаких универсальных Stage Gate `PASS`.

**PH-051-08.** Реализуй отдельный bounded diff/apply service: actual-vs-allowed/expected paths, secret scan, baseline recheck, durable journal, crash rollback, immutable Apply Evidence. Запрещай partial canonical writes.

**PH-051-09.** Собери из готовых компонентов public `executor-doctor` и `execute-current` с exact status/next/API semantics и policy-gated completion. Запрети автоматический путь при failing Podman doctor и denied egress. Разреши только current READY Task.

**PH-051-10.** Реализуй только migration 0.5.0→0.5.1 в manual default, `execution_origin`, orphan detection, container termination, cleanup and retry/journal recovery. Не меняй старые accepted records и Stage maturity.

**PH-051-11.** Обнови operator runbooks, samples, GPT instructions, embedded/standalone docs и выполни реальные security integration tests + installed CLI smoke. Не добавляй новый runtime функционал. При отсутствии Podman запиши `NO-GO` для security acceptance.

**PH-051-12.** Проведи финальную приёмку E-01–E-18 и normative §24 после всех пакетов; прогони весь старый + новый набор, реальную Podman security matrix, миграции, wheel/doc/ZIP integrity. Исправь только release-blocking regressions; собери два финальных v0.5.1 ZIP с SHA-256 и честным GO/NO-GO.

## 9. Решение о готовности

**GO v0.5.1** возможен только при одновременном доказанном выполнении всех 14 критериев нормативной §24, сценариев E-01–E-18 и сохранении v0.5.0 lifecycle. В частности, local Codex CLI никогда не исполняется вне корректно проверенного rootless Podman, diff переносится только после независимой verification и без частичного commit, а ручной маршрут по-прежнему доступен и безопасен без Podman.

**NO-GO** при любом невыполненном mandatory Podman security test, ложном `PASS` verification, unsandboxed fallback, утечке secret, недоверенном apply, нарушении immutable history или коллизии registry version без разрешённой миграции.

**Начинать с:** `PH-051-01`, используя текущие два v0.5.0 ZIP и неизменную нормативную v0.5.1 спецификацию. Версия v0.6.0 остаётся вне scope.
