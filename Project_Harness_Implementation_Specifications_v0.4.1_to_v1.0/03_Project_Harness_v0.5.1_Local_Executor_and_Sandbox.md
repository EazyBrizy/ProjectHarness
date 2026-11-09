# Project Harness v0.5.1 — Local Codex CLI Executor и Rootless Container Sandbox

**Базовая версия:** Project Harness Engine v0.5.0  
**Целевая версия:** v0.5.1  
**Тип релиза:** PATCH / controlled local execution  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью принятые v0.4.1 и v0.5.0  
**Порядок реализации:** третий документ серии

## 1. Назначение версии

v0.5.1 добавляет первый автоматический execution path:

```text
READY Task
→ JIT Prompt Bundle
→ local Codex CLI invocation
→ sandboxed product changes
→ normalized Agent Task Result
→ independent verification
→ complete / block
```

Версия выпускает вместе две неразделимые части:

1. один `Local Codex CLI Executor Adapter`;
2. один `Rootless Container Sandbox` backend.

Автоматический запуск без sandbox запрещён. Это основное safety-условие релиза.

Существующий manual handoff остаётся полностью поддерживаемым и является fallback по выбору пользователя, но не техническим fallback после ошибки sandbox.

## 2. Не входит в scope

v0.5.1 не должна включать:

- provider HTTP APIs;
- автоматический выбор модели или провайдера;
- несколько CLI adapters;
- retry между провайдерами;
- token accounting, billing или cost optimization;
- VM/microVM isolation;
- Kubernetes jobs;
- remote workers;
- Git commit, push или PR;
- deployment;
- parallel execution;
- arbitrary network host allowlists;
- интерактивный proxy для инструментов агента;
- хранение секретов внутри `.harness`;
- shell-строки с интерполяцией пользовательского ввода;
- автоматическое применение непроверенного diff к canonical project root.

Первая реализация должна быть маленькой, детерминированной и проверяемой.

## 3. Обязательные architectural boundaries

### 3.1. Четыре области

```text
HARNESS_DISTRIBUTION
PROJECT_CONTROL
CANONICAL_PRODUCT_ROOT
DISPOSABLE_EXECUTION_ROOT
```

- `HARNESS_DISTRIBUTION` содержит engine, registries и schemas; read-only.
- `PROJECT_CONTROL` — `.harness`; read-only для agent process, кроме отдельного result channel.
- `CANONICAL_PRODUCT_ROOT` — проверенная рабочая копия пользователя; agent не изменяет её напрямую.
- `DISPOSABLE_EXECUTION_ROOT` — временная копия product plane, доступная agent на запись.

### 3.2. Нет unsandboxed fallback

Если container backend отсутствует, misconfigured или не проходит self-test:

```text
execute-current → BLOCKED / SANDBOX_UNAVAILABLE
```

Harness предлагает:

- исправить sandbox;
- вернуться к manual handoff.

Он не запускает Codex CLI на host «временно».

### 3.3. Verification остаётся независимой

Exit code `0` и текст агента не являются доказательством успеха. После invocation Kernel:

1. проверяет Agent Task Result schema;
2. вычисляет фактический diff;
3. проверяет expected/allowed paths;
4. запускает declared verification commands в sandbox;
5. проверяет control-plane invariants;
6. только после `PASS` переносит проверенный diff в canonical product root;
7. вызывает обычный completion transition.

## 4. Executor Adapter contract

Добавить пакет:

```text
src/project_harness/executors/
  __init__.py
  base.py
  codex_cli_local.py
  result.py
```

Общий интерфейс должен быть минимальным:

```python
class ExecutorAdapter(Protocol):
    def doctor(self, profile: dict) -> dict: ...
    def prepare_invocation(self, run_context: dict) -> list[str]: ...
    def execute(self, invocation: list[str], sandbox_request: dict) -> dict: ...
    def normalize_result(self, process_result: dict, output_dir: Path) -> dict: ...
```

`cancel()` допускается как отдельный метод, если CLI process management уже поддерживает reliable termination. Нельзя добавлять асинхронный job lifecycle только ради будущего remote control plane.

## 5. Adapter Profile

Использовать существующую сущность `ADP` и lifecycle `adapter_profile`.

Пример distribution/project configuration:

```yaml
adapter_profile:
  id: ADP-CODEX-CLI-LOCAL-001
  revision: 1
  status: ACTIVE
  kind: CODEX_CLI_LOCAL
  executable: codex
  argv_template:
    - codex
    - exec
    - --prompt-file
    - "{prompt_bundle_path}"
    - --result-file
    - "{agent_result_path}"
  working_directory: /workspace/product
  timeout_seconds: 1200
  stdin_mode: CLOSED
  environment_allowlist:
    - LANG
    - LC_ALL
  secret_environment_refs: []
  sandbox_profile_ref: SBX-ROOTLESS-PODMAN-001
```

Точный синтаксис Codex CLI не должен быть зашит в Kernel. `argv_template` конфигурируется и валидируется как список аргументов.

Разрешённые placeholders:

```text
{prompt_bundle_path}
{context_packet_path}
{agent_result_path}
{workspace_path}
{run_id}
{task_id}
```

Неизвестный placeholder блокирует profile activation.

Запрещено:

- shell command string;
- `shell=True`;
- подстановка arbitrary user text в executable/flags;
- command substitution;
- redirect/pipeline syntax;
- relative executable, если policy требует exact resolved binary;
- передача всего host environment.

## 6. Rootless container backend

Первая и единственная поддерживаемая реализация v0.5.1:

```text
ROOTLESS_PODMAN
```

Выбор одного backend необходим для реального test matrix. Docker/rootless Docker, bubblewrap, nsjail и VM остаются вне scope.

Добавить:

```text
src/project_harness/sandbox/
  __init__.py
  base.py
  podman_rootless.py
  profiles.py
```

Sandbox interface:

```python
class SandboxRunner(Protocol):
    def doctor(self, profile: dict) -> dict: ...
    def run(self, request: dict) -> dict: ...
```

## 7. Sandbox profile

Sandbox Profile является отдельной persisted сущностью. В `id_prefixes.yaml` добавить:

```yaml
- prefix: SBX
  entity: OS-level Sandbox Profile
  schema_key: sandbox_profile
  status: ACTIVE
```

В `statuses.yaml` добавить отдельную группу:

```yaml
sandbox_profile:
  - DRAFT
  - VALIDATED
  - ACTIVE
  - SUSPENDED
  - DEPRECATED
  - RETIRED
```

Нельзя маскировать sandbox profile под agent adapter `ADP`: adapter и isolation backend имеют разные contracts.

```yaml
sandbox_profile:
  id: SBX-ROOTLESS-PODMAN-001
  revision: 1
  status: ACTIVE
  backend: ROOTLESS_PODMAN
  image: project-harness-codex-runtime@sha256:<digest>
  network_mode: NONE
  root_filesystem: READ_ONLY
  run_as_non_root: true
  drop_all_capabilities: true
  no_new_privileges: true
  writable_mounts:
    - /workspace/product
    - /output
    - /tmp
  limits:
    timeout_seconds: 1200
    memory_mb: 2048
    cpu_count: 2
    pids: 128
    output_bytes: 52428800
```

Container image должна быть pin by digest. Mutable tag без digest не проходит `doctor` в automatic mode.

## 8. Mount policy

Минимальные mounts:

| Host source | Container target | Mode |
|---|---|---|
| disposable product copy | `/workspace/product` | `rw` |
| run control projection | `/workspace/control` | `ro` |
| exact result directory | `/output` | `rw` |
| optional source cache | `/workspace/sources` | `ro` |
| temporary filesystem | `/tmp` | `tmpfs` |
| ephemeral non-host home | `/home/harness` | `tmpfs` or bounded writable mount |

`/workspace/control` содержит только projection, необходимую текущему Run:

- Prompt Bundle;
- Context Packet;
- Task Contract;
- Run Plan;
- permitted configuration;
- schemas, нужные для result format.

Не требуется монтировать весь `.harness`, если projection достаточно. Если весь `.harness` монтируется для совместимости, он должен быть строго read-only.

Container получает `HOME=/home/harness`; host home/config/cache не передаются. Это даёт CLI bounded writable home без раскрытия пользовательского окружения.

Не монтировать:

- `/var/run/docker.sock` или Podman socket;
- host home directory;
- SSH agent socket;
- Git credential store;
- cloud credentials directories;
- arbitrary host `/tmp`;
- Harness distribution на запись;
- canonical product root на запись.

## 9. Result channel

Agent Task Result записывается только в заранее созданный exact path:

```text
/output/agent-result.json
```

После завершения process Kernel:

1. проверяет, что path является regular file;
2. запрещает symlink/hardlink escape;
3. проверяет ownership/permissions;
4. ограничивает размер;
5. загружает JSON без executable interpretation;
6. валидирует `agent_task_result.schema.json`;
7. переносит validated copy в `.harness/runtime/AGENT_RESULTS/<RUN>.json` сам.

Agent не получает `PROJECT_CONTROL_WRITE`.

Дополнительные файлы в `/output` либо запрещаются, либо перечисляются в `declared_outputs`. По умолчанию разрешён только result JSON и bounded logs, которые Kernel собирает сам.

## 10. Network isolation

v0.5.1 поддерживает два режима:

```text
NONE
EXPLICIT_APPROVED_EGRESS
```

### 10.1. NONE

Default:

- container запускается с `--network=none`;
- DNS и outbound connection отсутствуют;
- подходит для local CLI, если модель/agent runtime не требует внешней сети, либо CLI использует host-mediated channel, не доступный container. Если выбранный Codex CLI технически требует сеть внутри container, используется второй режим.

### 10.2. EXPLICIT_APPROVED_EGRESS

Разрешается только при наличии:

```text
NETWORK_WRITE
MODEL_EXTERNAL_EGRESS
```

и formal approval, привязанного к Run/adapter profile.

В этой версии режим означает обычный rootless container network. Точный destination allowlist не реализуется. Поэтому approval должен честно фиксировать, что технический network boundary не ограничивает конкретные hosts.

`--network=host`, inbound port mapping и privileged networking запрещены.

При чувствительности `SECRET`/`REGULATED` external model egress блокируется, если project policy не содержит отдельного явного разрешения и допустимого adapter profile.

## 11. Secrets и environment

Secrets не хранятся в:

- `PROJECT_INPUT`;
- Prompt Bundle;
- Context Packet;
- `.harness` artifacts;
- logs;
- container image;
- manifest.

Adapter profile содержит только references:

```yaml
secret_environment_refs:
  - name: OPENAI_API_KEY
    source: ENV
    host_variable: OPENAI_API_KEY
```

Kernel:

- проверяет разрешённость secret reference;
- передаёт только перечисленные variables;
- никогда не выводит значения в structured result;
- применяет exact-value redaction к stdout/stderr;
- не сохраняет full environment;
- очищает temporary secret projection после Run.

Если required secret отсутствует, Run не стартует и получает recoverable blocker.

## 12. Disposable execution root

Для каждого Run создаётся отдельная директория вне canonical repository:

```text
<configured-runtime-root>/<project-id>/executions/<RUN_ID>/product
```

В `.harness/runtime/EXECUTION_BINDINGS/` хранится только bounded metadata/reference. Большой writable execution tree не должен находиться внутри canonical product/control repository.

Она формируется из canonical product snapshot, исключая `.harness` и generated control files.

Перед запуском Kernel сохраняет:

```yaml
execution_baseline:
  canonical_product_digest: <digest>
  control_plane_digest: <digest>
  base_revision: <git sha or tree digest>
  task_ref: <task@revision>
  prompt_bundle_ref: <bundle@revision>
```

После Run canonical root должен иметь тот же digest. Если пользователь или другой process изменил его во время execution, apply блокируется как `BASELINE_CHANGED`.

## 13. Diff extraction и apply

Agent changes не копируются рекурсивно поверх project root.

Алгоритм:

1. вычислить file-level diff между execution baseline и disposable product;
2. отклонить special files, device nodes, sockets и escaping symlinks;
3. проверить actual write set против Task Contract;
4. проверить expected write set;
5. проверить Agent Result, bounded logs и changed files на exact values переданных secrets; project-defined secret scan применяется, если он уже является mandatory policy;
6. выполнить verification в disposable root;
7. убедиться, что canonical base не изменился;
8. создать apply plan с exact paths и digests;
9. атомарно заменить/создать/удалить только перечисленные files;
10. пересчитать canonical digest;
11. записать Apply Evidence.

При ошибке в середине apply должна использоваться temporary staging directory и rollback journal. Частично применённый diff недопустим.

Удаление файла разрешается только если path входит в allowed writes и deletion явно отражена diff.

## 14. Verification внутри sandbox

Существующий `verify --allow-command-execution` должен получить backend mode:

```text
MANUAL_HOST
SANDBOXED
```

Для automatic Run используется только `SANDBOXED`.

Verification commands:

- остаются argv arrays;
- запускаются в disposable product root;
- используют тот же или отдельный pinned verification image;
- наследуют network mode `NONE`, если Task Contract явно не требует approved network;
- имеют собственные timeout/output limits;
- не получают agent secrets по умолчанию;
- сохраняют exit code и bounded output.

Agent invocation и verification должны быть разными process executions. Агент не может объявить собственный тест успешным вместо independent check.

## 15. Run lifecycle

Допустимый transition:

```text
READY
→ RUNNING
→ VERIFYING
→ SUCCEEDED
```

Failure routes:

```text
RUNNING → TIMED_OUT
RUNNING → FAILED_RETRYABLE
RUNNING → BLOCKED
VERIFYING → FAILED_RETRYABLE
VERIFYING → BLOCKED
```

Reason codes минимум:

```text
EXECUTOR_UNAVAILABLE
EXECUTOR_EXIT_NONZERO
EXECUTOR_TIMEOUT
SANDBOX_UNAVAILABLE
SANDBOX_POLICY_FAILURE
RESULT_MISSING
RESULT_INVALID
OUTPUT_LIMIT_EXCEEDED
NETWORK_NOT_APPROVED
SECRET_REFERENCE_MISSING
SECRET_LEAK_DETECTED
SCOPE_VIOLATION
BASELINE_CHANGED
VERIFICATION_FAILED
APPLY_FAILED_RECOVERABLE
```

Повторный запуск создаёт новый immutable Run/Run Plan revision. Старый Run не перезаписывается.

## 16. CLI

Добавить:

```bash
project-harness executor-doctor --project <root>
project-harness execute-current --project <root>
```

Опции первой версии:

```text
--adapter-profile <id-or-path>
--network NONE|EXPLICIT_APPROVED_EGRESS
--approval <record-path>   # только для egress/secret-sensitive run
--keep-execution-root      # только debug policy, default false
```

`execute-current` выполняет полный controlled route до verification, но completion может быть:

- automatic после PASS, если project policy разрешает;
- explicit отдельной командой `complete`, если approval требуется.

Выбранный режим должен быть заранее зафиксирован в project policy. Нельзя молча менять его между Runs.

## 17. Configuration precedence

```text
distribution defaults
< project adapter profile
< approved per-run override
```

Per-run override может только сужать capabilities/limits. Расширение network, mounts, secrets или timeout требует отдельного approval и новой Run Plan revision.

### 17.1. Строгий execution input

`PROJECT_INPUT`/project preparation contract получает только policy references, без secret values:

```yaml
execution:
  mode: MANUAL_HANDOFF
  adapter_profile_ref: null
  sandbox_profile_ref: null
  network_mode: NONE
  completion_policy: EXPLICIT_AFTER_VERIFICATION
```

Allowed values:

```text
mode: MANUAL_HANDOFF | LOCAL_AUTOMATIC
network_mode: NONE | EXPLICIT_APPROVED_EGRESS
completion_policy: EXPLICIT_AFTER_VERIFICATION | AUTO_AFTER_PASS
```

Conditional rules:

- `LOCAL_AUTOMATIC` требует active `adapter_profile_ref` и `sandbox_profile_ref`;
- `EXPLICIT_APPROVED_EGRESS` не является постоянным approval: каждый Run всё равно получает exact capability/decision binding;
- `AUTO_AFTER_PASS` разрешён только project policy и не отменяет independent verification;
- secret values, arbitrary argv и mount paths запрещены в `PROJECT_INPUT`.

Versioning:

```text
PROJECT_INPUT.schema_version: 4
SCHEMA-PROJECT-PREPARATION-INPUT@4
Harness canonical SCHEMA_VERSION: 7
Migration: MIG-ENGINE-0.5.0-TO-0.5.1
```

## 18. Изменения модулей

Обновить:

- `cli.py` — commands и structured envelopes;
- `runtime.py` — automatic Run orchestration;
- `safety.py` — mount/path/result checks;
- `validation.py` — adapter/sandbox profiles;
- `resources.py` — pinned profile/image metadata;
- `archive.py` — исключить execution roots из handoff/export;
- `prompting.py` — exact Agent Result destination;
- `capabilities.yaml` — использовать существующие capabilities без добавления лишних;
- `statuses.yaml` — добавить `sandbox_profile`; `adapter_profile` уже существует и используется только для executor adapter.

Новые modules:

```text
executors/base.py
executors/codex_cli_local.py
executors/result.py
sandbox/base.py
sandbox/podman_rootless.py
sandbox/profiles.py
apply.py
```

`apply.py` должен быть отдельным от adapter: provider не решает, что переносится в canonical root.

## 19. Schemas и records

Добавить schemas:

```text
executor_profile.schema.json
sandbox_profile.schema.json
execution_result.schema.json
apply_evidence.schema.json
```

Execution result минимум:

```yaml
execution_result:
  id: ART-PROJECT-EXECUTION-001
  run_ref: RUN-PROJECT-001@1
  adapter_profile_ref: ADP-CODEX-CLI-LOCAL-001@1
  sandbox_profile_ref: SBX-ROOTLESS-PODMAN-001@1
  started_at: ...
  finished_at: ...
  exit_code: 0
  termination_reason: EXITED
  stdout_artifact_ref: ART-...
  stderr_artifact_ref: ART-...
  agent_result_ref: ART-...
  execution_root_digest: ...
  result_status: COMPLETED
```

Logs должны быть bounded и redacted. Full raw output не обязано входить в handoff archive.

### 19.1. Contract catalog и registry versions

В `contracts.yaml` добавить:

```yaml
sandbox_profile:
  id_prefix: SBX
  persistence: PERSISTENT
  lifecycle: sandbox_profile
  storage_path: .harness/config/SANDBOXES/{id}@{revision}.yaml
  revision_policy: VERSIONED
execution_result:
  id_prefix: ART
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/runtime/EXECUTION_RESULTS/{id}.yaml
  revision_policy: IMMUTABLE
apply_evidence:
  id_prefix: EVD
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/evidence/{id}.yaml
  revision_policy: IMMUTABLE
```

Executor profile продолжает использовать существующий `agent_adapter_profile`/`ADP`; второй contract для того же adapter не создаётся.

Expected registry versions:

```text
REG-ID-PREFIXES:      2 → 3   # SBX
REG-CONTRACT-CATALOG: 4 → 5
REG-STATUSES:         5 → 6   # sandbox_profile
```

`PROJECT_LOCK` получает exact profile refs/digests и изменённые registry versions. Runtime execution root и raw logs в lock/archive не включаются.

## 20. Doctor checks

`executor-doctor` и distribution `doctor()` должны проверять:

- Podman executable существует;
- Podman работает rootless;
- effective UID внутри test container не root;
- image digest доступен;
- read-only root filesystem действительно read-only;
- write разрешён только в expected mounts;
- network none self-test не может установить outbound connection;
- mounted control projection нельзя изменить;
- result directory writable;
- capabilities dropped;
- no-new-privileges включён;
- timeout и process termination работают;
- configured Codex executable доступен внутри image;
- argv template валиден.

Если environmental network self-test невозможно выполнить детерминированно, он возвращает `UNKNOWN` и automatic mode остаётся заблокированным до explicit environment validation procedure.

## 21. Migration v0.5.0 → v0.5.1

Migration не включает automatic mode автоматически.

Для существующего проекта:

```yaml
execution:
  mode: MANUAL_HANDOFF
  adapter_profile_ref: null
  sandbox_profile_ref: null
  network_mode: NONE
  completion_policy: EXPLICIT_AFTER_VERIFICATION
```

Пользователь явно активирует:

```yaml
mode: LOCAL_AUTOMATIC
```

после successful doctor и approval.

Старые manual Runs остаются валидными. Новый engine должен различать:

```text
execution_origin: MANUAL_EXTERNAL | LOCAL_AUTOMATIC
```

## 22. Failure и recovery

- execution root сохраняется до завершения verification; затем удаляется по policy;
- при timeout сначала SIGTERM, затем bounded grace period, затем SIGKILL;
- дочерние процессы должны завершаться вместе с container;
- при host crash orphan container обнаруживается по labels и не считается успешным;
- orphan execution root quarantined до inspection/cleanup;
- retry не использует непроверенный partial result старого Run;
- apply journal позволяет завершить rollback после crash;
- missing logs не превращают failed Run в success;
- cleanup failure фиксируется отдельно и не изменяет результат product verification.

## 23. Тестовый план

### 23.1. Unit

- argv template expansion;
- unknown placeholders;
- environment allowlist;
- secret redaction;
- result size/type/path validation;
- symlink escape detection;
- diff/write-set validation;
- atomic apply and rollback;
- timeout reason mapping;
- no unsandboxed fallback.

### 23.2. Fake CLI integration

Создать deterministic fake Codex CLI fixtures:

- successful file change + valid result;
- non-zero exit;
- timeout;
- missing result;
- invalid JSON;
- attempted `.harness` write;
- write outside allowed paths;
- output flood;
- child process that does not exit;
- secret echo to stdout;
- secret value written into changed product file/result;
- canonical base modified concurrently.

### 23.3. Podman security integration

- root filesystem write fails;
- control mount write fails;
- host home unavailable;
- socket mounts absent;
- effective user non-root;
- capabilities empty;
- network none blocks egress;
- memory/pids/time limits enforced;
- exact output mount works;
- special-file creation rejected during apply.

### 23.4. End-to-end

```text
prepare project
→ next
→ execute-current with fake CLI
→ sandboxed verify
→ safe apply
→ Task DONE / Run SUCCEEDED
→ next task
```

Также проверить manual route без Podman activation.

## 24. Критерии приёмки v0.5.1

Версия готова, когда:

1. существует ровно один поддерживаемый local Codex CLI adapter;
2. automatic execution всегда использует rootless Podman sandbox;
3. отсутствие sandbox никогда не приводит к host execution;
4. agent не имеет write-доступа к canonical product root и `.harness`;
5. network default — `NONE`;
6. egress требует capabilities и approval;
7. secrets передаются только по references, redacted в logs и проверяются на exact-value leakage до apply;
8. Agent Result принимается через exact bounded result channel;
9. actual diff независимо проверяется до apply;
10. apply является path-bounded и recoverable;
11. verification выполняется отдельно от agent process;
12. manual handoff остаётся рабочим и является default после migration;
13. security integration tests подтверждают mount/network/process boundaries;
14. существующие v0.5.0 stage rules не изменяются.

## 25. Порядок реализации

1. Зафиксировать adapter/sandbox contracts и schemas.
2. Реализовать fake Executor Adapter и unit tests.
3. Реализовать Podman doctor/self-tests.
4. Реализовать execution-root builder и control projection.
5. Реализовать real local Codex CLI adapter через argv template.
6. Реализовать result channel и normalization.
7. Перевести verification automatic mode в sandbox.
8. Реализовать diff extraction и atomic apply.
9. Добавить Runtime transitions и CLI.
10. Добавить cleanup/crash recovery.
11. Выполнить security integration matrix.
12. Активировать automatic mode только после acceptance всех Gate tests.

v0.6.0 использует этот sandbox для deployment route и внешних Git/PR tools, но не расширяет executor adapters.
