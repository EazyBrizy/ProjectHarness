# Project Harness v0.8.0+ — Single-Node Remote Multi-User Control Plane

**Базовая версия:** Project Harness Engine v0.7.0  
**Целевая версия:** v0.8.0 как первый release семейства v0.8.x  
**Тип релиза:** MINOR / optional single-node service mode  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью принятые v0.4.1–v0.7.0  
**Порядок реализации:** седьмой документ серии

## 1. Назначение версии

v0.8.0 добавляет optional server mode, в котором несколько пользователей работают с одним Project Harness Instance через единый coordination authority.

Сервер должен позволять:

- импортировать существующий локальный Harness project;
- видеть единое canonical состояние;
- выполнять разрешённые state transitions;
- принимать approvals и blocker resolutions;
- ставить Runs в очередь;
- предотвращать одновременные конфликтующие mutations;
- просматривать evidence и audit history;
- экспортировать проект обратно в self-contained archive.

Архитектура первой версии:

```text
one server process
├── HTTP/JSON API
├── deterministic Kernel library
├── SQLite coordination database (WAL)
├── local project/artifact storage
├── one top-level job worker
└── append-only audit/event records
```

Remote mode является дополнительным. Локальный CLI/filesystem mode остаётся поддерживаемым.

## 2. Не входит в scope

v0.8.0 не должна включать:

- multi-node/high-availability cluster;
- distributed locks или consensus;
- PostgreSQL;
- Redis/message broker;
- Kubernetes deployment requirement;
- browser/web UI;
- OIDC/SAML/enterprise identity provider;
- organization billing/quotas;
- model token accounting;
- public SaaS multi-tenancy;
- remote arbitrary workers;
- horizontal scaling;
- cross-region storage;
- real-time collaborative editing;
- built-in TLS certificate management;
- email/notification system;
- plugin marketplace;
- API compatibility с произвольным MCP protocol как обязательное условие;
- прямое редактирование canonical `.harness` files клиентами.

Версии v0.8.x могут исправлять hardening/operational defects этого single-node scope, но не должны превращаться в распределённую платформу до отдельного решения.

## 3. Canonical state и coordination state

Нужно избежать двух конкурирующих sources of truth.

### 3.1. Canonical project artifacts

Project model, Tasks, Runs, Evidence, registries/locks и generated views продолжают храниться в versioned `.harness` structure внутри server-managed project root.

Это необходимо для:

- воспроизводимости;
- локального экспорта;
- совместимости с существующим Kernel;
- независимости проекта от сервера.

### 3.2. SQLite coordination database

SQLite хранит только server-specific coordination и index data:

- users;
- hashed API tokens;
- project registrations и memberships;
- current project server revision;
- queued jobs;
- idempotency keys;
- active project mutations;
- server audit index;
- artifact metadata/index;
- transaction/recovery journal;
- lease mirror для remote coordination.

Canonical Task/Run contract не должен существовать только как opaque database row без export representation.

### 3.3. Revision rule

Каждая successful project mutation:

```text
expected_project_revision N
→ staged filesystem transaction
→ Kernel validation
→ commit canonical files
→ database revision N+1
→ audit event
```

Клиент обязан передавать expected revision для modifying requests. Несовпадение возвращает conflict, не last-write-wins.

## 4. Server storage layout

```text
server_root/
├── server.sqlite3
├── projects/
│   └── <project-id>/
│       ├── project/               # imported product + .harness
│       ├── transactions/
│       ├── runtime/
│       ├── artifacts/
│       └── exports/
├── logs/
└── backups/
```

Rules:

- project directories принадлежат service account;
- API clients не получают filesystem path/write access;
- runtime/worktrees/execution roots остаются вне export или помечаются ephemeral;
- server-only large logs/artifacts хранятся внутри project-local `artifacts/`; canonical refs остаются в `.harness`;
- global cross-project deduplication/content-addressed store не реализуется в v0.8.0;
- symlink escape и cross-project hardlink запрещены.

## 5. Server process model

Первая версия может быть одним Python process с чёткими logical components:

```text
api
application_service
kernel_adapter
job_worker
storage
security
audit
```

Один top-level worker последовательно забирает jobs из SQLite. Внутри одного v0.7 Parallel Batch он может запустить bounded local child executions, поскольку leases/worktrees остаются local и принадлежат тому же server authority.

Не нужно вводить отдельный worker service или message bus.

Server startup выполняет:

1. database schema check/migration;
2. storage permission check;
3. project transaction recovery;
4. stale job reconciliation;
5. local executor/sandbox doctor для execution-enabled projects;
6. audit append readiness;
7. bind listener.

Если recovery не завершена, affected project остаётся `BLOCKED` с reason code `RECOVERY_REQUIRED`; остальные проекты могут быть доступны.

## 6. SQLite configuration

Минимальные требования:

- SQLite WAL mode;
- foreign keys ON;
- explicit transactions;
- bounded busy timeout;
- one migration sequence;
- database file и WAL на local filesystem;
- no network filesystem support в v0.8.0;
- regular integrity check during backup/doctor.

Минимальные tables:

```text
schema_migrations
users
api_tokens
projects
project_memberships
project_revisions
jobs
job_attempts
idempotency_records
project_mutation_locks
audit_events
artifact_index
recovery_transactions
```

Canonical entity tables для Tasks/Runs не требуются. Search/status read model может индексироваться позже только если это необходимо; первая версия читает validated canonical state с bounded caching.

## 7. User и role model

Роли на уровне проекта:

```text
OWNER
OPERATOR
APPROVER
VIEWER
```

Минимальные permissions:

| Действие | OWNER | OPERATOR | APPROVER | VIEWER |
|---|---:|---:|---:|---:|
| Просмотр state/evidence | да | да | да | да |
| Import/create project | да | нет | нет | нет |
| Изменение membership | да | нет | нет | нет |
| Prepare/plan/next | да | да | нет | нет |
| Execute/verify/block/resume | да | да | нет | нет |
| Commit/push/PR/deploy route start | да | да, если policy разрешает | нет | нет |
| Approve Brownfield/Stage/Push/PR/Deploy/Skill | да | нет | да | нет |
| Export project | да | да | нет | нет |
| Delete project registration | да | нет | нет | нет |

Separation of duties является project policy, а не обязательной сложной enterprise-моделью. Если policy требует, actor, выполняющий operation, не может сам её approve. Default может позволять OWNER оба действия для малой команды.

## 8. Authentication

Первая версия использует API tokens.

Token lifecycle:

```text
create → active → revoke/expire
```

Rules:

- raw token показывается только один раз при создании;
- database хранит salted `scrypt` digest, рассчитанный стандартной `hashlib.scrypt`; параметры фиксируются server security profile, salt генерируется `secrets`, сравнение выполняется constant-time;
- lookup может использовать non-secret token ID + hashed secret;
- tokens имеют actor, created_at, expires_at, revoked_at;
- token не хранится в project archive;
- tokens не печатаются в server logs;
- authentication failures audit-ируются без raw credential;
- bootstrap first OWNER выполняется локальной administrative command на host.

Не следует изобретать собственную криптографию. Выбранная standard library/dependency фиксируется в technology baseline сервера и проверяется тестами.

## 9. Network exposure

Default:

```text
bind: 127.0.0.1
```

Для доступа с других машин:

- server размещается за доверенным TLS reverse proxy;
- proxy передаёт только validated HTTP traffic;
- Harness документирует required headers и trusted proxy policy;
- plain HTTP на non-loopback должен блокироваться policy либо явно обозначаться unsafe development mode.

Built-in certificate issuance и reverse-proxy management вне scope.

## 10. API design

Versioned base path:

```text
/api/v1
```

Минимальные endpoints:

```text
POST   /projects/import
GET    /projects
GET    /projects/{project_id}
GET    /projects/{project_id}/status
GET    /projects/{project_id}/events
GET    /projects/{project_id}/artifacts/{artifact_id}
POST   /projects/{project_id}/next
POST   /projects/{project_id}/execute-current
POST   /projects/{project_id}/verify
POST   /projects/{project_id}/complete
POST   /projects/{project_id}/block
POST   /projects/{project_id}/resume
POST   /projects/{project_id}/approvals
POST   /projects/{project_id}/level-up
POST   /projects/{project_id}/publish/push
POST   /projects/{project_id}/publish/pr
POST   /projects/{project_id}/deployments
GET    /projects/{project_id}/jobs/{job_id}
POST   /projects/{project_id}/export
GET    /exports/{export_id}
```

Endpoints, относящиеся к feature, доступны только если соответствующая версия/configuration активна.

В первой версии long-running operations возвращают job:

```yaml
status: ACCEPTED
job:
  id: JOB-...
  project_id: ...
  project_revision: 42
  operation: EXECUTE_CURRENT
  state: QUEUED
```

Клиент опрашивает job status. WebSocket/SSE не обязательны.

## 11. Request contract

Каждый modifying request содержит:

```yaml
request_id: <client-generated-id>
idempotency_key: <unique-key>
expected_project_revision: 42
actor_intent: <operation-specific-payload>
```

Server добавляет authenticated actor. Клиент не может подставить actor ID.

Responses используют существующий Result Envelope плюс:

```yaml
server:
  project_revision_before: 42
  project_revision_after: 43
  request_id: ...
  audit_event_ref: EVT-...
```

## 12. Idempotency

Idempotency обязательна для POST, особенно внешних side effects.

Key scope:

```text
actor + project + endpoint + idempotency_key
```

Rules:

- одинаковый key + одинаковый payload возвращает исходный result/job;
- одинаковый key + другой payload → conflict;
- record хранит payload digest, response/result ref и expiry policy;
- push/PR/deployment дополнительно используют side-effect fingerprints v0.6.0;
- потеря client connection не означает retry without reconciliation.

## 13. Project mutation serialization

На один project допускается один top-level state mutation transaction. Read requests выполняются параллельно против committed revision.

Механизм:

- SQLite row в `project_mutation_locks` внутри transaction;
- owner job ID и lease/heartbeat;
- expected project revision;
- bounded TTL;
- crash reconciliation.

Это server coordination lease и не заменяет v0.7 resource leases внутри Parallel Batch.

Два пользователя не могут одновременно:

- принять одну Stage Gate разными decisions;
- запустить одну READY Task дважды;
- изменить target level на разных revisions;
- активировать разные skill revisions без conflict.

Второй request получает `REVISION_CONFLICT` или `PROJECT_BUSY` с current revision и безопасным next action.

## 14. Filesystem transaction protocol

Поскольку SQLite и filesystem не имеют общей atomic transaction, использовать explicit journal:

```text
PREPARED
→ FILES_STAGED
→ FILES_COMMITTED
→ DB_COMMITTED
→ FINALIZED
```

Algorithm:

1. создать recovery transaction record;
2. скопировать/записать changed canonical files в transaction staging directory;
3. validate staged full project view;
4. fsync files/directories согласно platform policy;
5. atomically replace exact canonical files, сохранив rollback copies;
6. commit SQLite project revision/audit link;
7. mark finalized;
8. удалить rollback data по retention.

При crash startup reconciliation определяет последнюю durable phase и либо завершает DB commit, либо восстанавливает previous files. Не допускается молча продолжать с расходящимися revision numbers.

## 15. Server Job ID и status registry

Server Job является persisted coordination entity. В `id_prefixes.yaml` добавить:

```yaml
- prefix: JOB
  entity: Server-coordinated Job
  schema_key: server_job
  status: ACTIVE
```

В `statuses.yaml` добавить:

```yaml
server_job:
  - QUEUED
  - CLAIMED
  - RUNNING
  - SUCCEEDED
  - FAILED_RECOVERABLE
  - BLOCKED
  - CANCELLED
```

Job status не подменяет canonical Task/Run status. Job только координирует server-side operation.

## 16. Job lifecycle

```text
QUEUED
→ CLAIMED
→ RUNNING
→ SUCCEEDED
```

Failure:

```text
QUEUED/CLAIMED/RUNNING
→ FAILED_RECOVERABLE
→ BLOCKED
→ CANCELLED
```

Job является server coordination entity и не заменяет canonical Run. `EXECUTE_CURRENT` job создаёт один или несколько canonical Runs согласно v0.7 Batch.

Cancellation:

- queued job может быть cancelled;
- running external process получает controlled cancel v0.5.1;
- cancellation внешнего side effect требует reconciliation;
- canonical Run statuses остаются source of execution truth.

## 17. Audit events

Каждое security/material действие записывает:

```yaml
audit_event:
  id: EVT-SERVER-...
  occurred_at: ...
  actor_ref: ACT-...
  project_id: ...
  project_revision_before: 42
  project_revision_after: 43
  action: STAGE_APPROVED
  request_id: ...
  idempotency_key_digest: ...
  subject_refs: []
  result_status: COMPLETED
  remote_address: <bounded/redacted>
```

Audit records append-only на уровне API. OWNER не может редактировать history через обычный endpoint.

Server audit index ссылается на canonical project event, когда действие меняет project model.

## 18. Approval handling

Approval request должен показывать exact subject revision/digest. Approval endpoint принимает:

```yaml
kind: STAGE_ACCEPTANCE
subject_ref: GATE-PROJECT-BETA-001@1
subject_digest: sha256:...
decision: APPROVE
notes: ...
expected_project_revision: 42
```

Server проверяет:

- role;
- subject существует и current;
- digest совпадает;
- required evidence доступно;
- separation-of-duties policy;
- decision не duplicate/conflicting;
- transition допустим.

UI не требуется; CLI показывает approval view.

## 19. Remote CLI parity

Существующий CLI получает global mode:

```bash
project-harness --server https://harness.example status --project <id>
```

Token передаётся через environment/config reference, не command-line argument по умолчанию.

Команды сохраняют те же понятия и Result Envelopes. Локальный path `--project <root>` и remote project ID должны быть однозначно различимы parser/config.

Административные local-only commands:

```bash
project-harness-server init --root <path>
project-harness-server create-user --name <name>
project-harness-server create-token --user <id> --expires <date>
project-harness-server serve --config <path>
project-harness-server doctor --root <path>
project-harness-server backup --output <archive>
project-harness-server restore --input <archive> --target <path>
```

## 20. Import

Import принимает self-contained Harness archive либо server-local path through admin route.

Procedure:

1. quarantine upload;
2. size/type/path traversal checks;
3. unpack без symlink/device escape;
4. validate manifest/digests;
5. detect Harness/schema version;
6. run required migrations in staged copy;
7. validate project;
8. assign server project ID;
9. create OWNER membership;
10. atomically register project revision 1;
11. preserve original archive digest as provenance.

Project with active/uncertain local Run imports as `BLOCKED` с reason code `RECONCILIATION_REQUIRED`, не как clean ready project.

## 21. Export

Export должен создавать self-contained versioned archive, пригодный для локального mode и повторного import.

Включает:

- product files по policy;
- `.harness` canonical state/history/evidence;
- Project Lock;
- required project-local skills;
- manifest и digests;
- migration/version metadata.

Не включает:

- users;
- API tokens;
- server memberships;
- server database;
- active secret material;
- ephemeral execution roots/worktrees;
- reverse-proxy configuration.

Export фиксируется на exact committed project revision. Running mutation должна завершиться или export использует предыдущую committed revision.

## 22. Project isolation

Server должен предотвращать:

- path traversal между project roots;
- artifact ID подмену для другого project;
- чтение project без membership;
- job operation над чужим project;
- shared worktree/mount;
- secret leakage в export/logs;
- cross-project lease key collision.

Execution sandbox mounts получает только конкретный server-managed project/worktree и bounded control projection.

## 23. Backups и restore

Single-node production scope требует documented backup:

1. остановить новые mutations либо создать coordinated snapshot;
2. checkpoint WAL;
3. копировать SQLite через supported backup API;
4. копировать project/artifact roots с manifest;
5. записать server version/config metadata;
6. verify backup digest.

Restore выполняется в новый empty target, затем:

- DB integrity check;
- artifact manifest validation;
- project validation;
- transaction recovery;
- token policy review;
- server doctor.

Backup не заменяет project export; это два разных recovery mechanisms. Server backup содержит coordination database, включая token hashes и memberships, поэтому хранится и передаётся как sensitive administrative artifact. Project export этих данных не содержит.

## 24. Configuration

Минимальный server config:

```yaml
server:
  bind: 127.0.0.1
  port: 8740
  trusted_proxy: false
  root: /var/lib/project-harness
  database: server.sqlite3
  max_upload_bytes: 524288000
  job_worker:
    enabled: true
    poll_interval_seconds: 1
  retention:
    transaction_days: 7
    job_log_days: 30
```

Limits должны быть configurable, но сложная quota system не нужна.

## 25. Модули и packaging

Добавить отдельный package surface:

```text
src/project_harness_server/
  __init__.py
  cli.py
  app.py
  api.py
  auth.py
  authorization.py
  database.py
  migrations.py
  projects.py
  transactions.py
  jobs.py
  worker.py
  audit.py
  artifacts.py
  import_export.py
  recovery.py
```

Kernel business rules остаются в `project_harness`, чтобы local и server modes не расходились.

Server API layer не должен дублировать status transitions вручную.

### 25.1. Server schemas и contract registration

Добавить server-facing schemas:

```text
server_config.schema.json
api_request.schema.json
api_result.schema.json
server_job.schema.json
audit_event.schema.json
project_membership.schema.json
```

В distribution `contracts.yaml` зарегистрировать экспортируемые/идентифицируемые coordination records:

```yaml
server_job:
  id_prefix: JOB
  persistence: SERVER_COORDINATION
  lifecycle: server_job
  storage_path: sqlite:jobs
  revision_policy: APPEND_ONLY_ATTEMPTS
audit_event:
  id_prefix: EVT
  persistence: SERVER_COORDINATION
  lifecycle: IMMUTABLE_RECORD
  storage_path: sqlite:audit_events
  revision_policy: APPEND_ONLY
```

Users, token hashes, memberships и DB journal rows определяются SQL migrations и server schemas; они не копируются в project `.harness` contract catalog как project entities.

Expected distribution registry versions:

```text
REG-ID-PREFIXES:      4 → 5   # JOB
REG-CONTRACT-CATALOG: 8 → 9
REG-STATUSES:         7 → 8   # server_job
Harness canonical SCHEMA_VERSION: 11
Server DB schema version: 1
```

Project export обновляет distribution/registry compatibility metadata, но исключает server-only rows и credentials.

## 26. Database migrations

Server DB имеет собственный version domain. Migration contract включает:

- from/to version;
- preconditions;
- backup requirement;
- SQL/data transform;
- validation;
- rollback/restore route;
- minimum compatible Engine version.

Project model migrations остаются отдельными.

## 27. Migration v0.7.0 → v0.8.0

Локальный project не мигрирует автоматически в server mode.

Route:

```text
validate local project
→ export archive
→ server import
→ assign owner/memberships
→ verify parity
→ optionally stop local writers
```

После import нельзя одновременно изменять ту же physical project root локальным CLI и server. Server-managed root закрыт для direct client writes.

## 28. Failure и recovery

| Ситуация | Действие |
|---|---|
| Duplicate modifying request | вернуть idempotent prior result |
| Expected revision mismatch | `REVISION_CONFLICT` |
| Server crash during mutation | transaction journal recovery |
| Worker crash during Run | reconcile container/Run/lease |
| DB available, project files incomplete | block project, rollback/complete journal |
| Project files valid, DB revision missing | finish DB commit from journal |
| External side effect uncertain | reuse v0.6 reconciliation; no blind retry |
| Token revoked during long job | existing claimed job follows recorded actor authorization policy; new operations denied |
| Artifact missing/corrupt | project blocked for evidence integrity |
| Backup restore mismatch | fail restore, do not serve partial state |

## 29. Тестовый план

### 29.1. Auth/RBAC

- raw token shown once and not stored;
- invalid/revoked/expired token denied;
- every role matrix action enforced;
- project membership isolation;
- actor cannot be supplied by request;
- approval separation policy;
- logs redact tokens.

### 29.2. Concurrency/idempotency

- two clients update same revision: one succeeds, one conflicts;
- duplicate POST same payload returns same job/result;
- same key different payload rejected;
- two execute requests cannot claim same Task;
- reads see committed revisions only;
- one top-level mutation per project;
- different projects operate independently.

### 29.3. Transactions/crash recovery

Inject crash after each journal phase:

- PREPARED;
- FILES_STAGED;
- FILES_COMMITTED;
- DB_COMMITTED.

После restart project должен быть либо old valid revision, либо new valid revision, но не mixed state.

### 29.4. Import/export

- v0.7 archive imports;
- malicious archive traversal rejected;
- server-only data excluded from export;
- export validates locally;
- export→new server import parity;
- running mutation snapshot behavior;
- active uncertain Run imported blocked.

### 29.5. Jobs

- queue/claim/run/success;
- cancel queued;
- cancel running process;
- worker restart reconciliation;
- v0.7 Parallel Batch within one job;
- canonical Run remains source of execution result.

### 29.6. Backup/restore

- consistent backup under read load;
- restore to clean target;
- DB/artifact/project integrity;
- transaction recovery after restore;
- no raw credentials in backup diagnostics.

## 30. Критерии приёмки v0.8.0

Версия готова, когда:

1. один server process обслуживает несколько projects/users;
2. SQLite WAL и local storage являются единственным supported backend;
3. `.harness` остаётся экспортируемым canonical project state;
4. все modifying requests требуют role, expected revision и idempotency key;
5. один project mutation serialized;
6. API tokens хранятся только как secure hashes;
7. OWNER/OPERATOR/APPROVER/VIEWER permissions проверяются;
8. один top-level job worker корректно восстанавливается после crash;
9. filesystem/DB transaction journal исключает mixed committed state;
10. import/export создают portable archive без server credentials;
11. project isolation протестирована;
12. external side effects используют существующий reconciliation;
13. backup/restore проверены;
14. default bind loopback;
15. web UI, OIDC, PostgreSQL, HA и multi-node отсутствуют из реализации.

## 31. Порядок реализации

1. Выделить stable Kernel library API из local CLI paths.
2. Реализовать server storage layout и SQLite migrations.
3. Реализовать users/tokens/RBAC.
4. Реализовать project import/read/status/export.
5. Реализовать optimistic revisions и filesystem transaction journal.
6. Реализовать modifying API поверх Kernel.
7. Реализовать idempotency.
8. Реализовать one-worker job queue.
9. Интегрировать executor/publication/parallel routes.
10. Реализовать audit events и artifact access.
11. Реализовать backup/restore/recovery.
12. Выполнить concurrency, crash-injection и isolation tests.
13. Выпустить v0.8.0; использовать v0.8.x только для hardening этого scope до v1.0.
