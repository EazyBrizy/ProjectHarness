# Project Harness v1.0 — Production Scope Freeze, Lifecycle Stabilization и Release Qualification

**Базовая версия:** последняя принятая v0.8.x single-node hardening release  
**Целевая версия:** v1.0.0  
**Тип релиза:** MAJOR / stable production contract  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью реализованные и принятые v0.4.1–v0.8.x  
**Порядок реализации:** восьмой и завершающий документ серии

## 1. Назначение версии

v1.0 не добавляет новую подсистему. Она фиксирует, проверяет и документирует уже реализованный lifecycle:

```text
intake
→ approved baselines
→ implementation levels and stage gates
→ JIT task planning
→ manual or sandboxed local execution
→ independent verification
→ optional commit/push/draft PR/deployment
→ optional safe local parallel batches
→ declarative PROJECT skill lifecycle
→ optional single-node remote coordination
→ export, migration and recovery
```

Главный результат v1.0 — не количество функций, а доказанная стабильность выбранного production scope.

## 2. Не входит в scope: запрет расширения

В v1.0 нельзя добавлять:

- provider API adapters;
- второй CLI agent adapter;
- второй sandbox backend;
- multi-node server/worker cluster;
- PostgreSQL/Redis/message bus;
- web UI;
- OIDC/SAML;
- polyrepo parallel execution;
- force push или automatic PR merge;
- новые PR providers;
- universal deployment providers;
- arbitrary executable skills/plugins;
- skill marketplace;
- token billing/accounting;
- advanced cost/model routing;
- Kubernetes как обязательную платформу;
- новые implementation levels;
- новый project lifecycle поверх существующих стадий;
- новый Change Pack scope, не реализованный в предыдущих версиях.

Любое обнаруженное желание добавить функцию оформляется как post-v1 backlog и не блокирует v1.0, если оно не является дефектом принятого scope.

## 3. Зафиксированный production scope

### 3.1. Supported modes

v1.0 поддерживает следующие режимы.

#### Mode A — Local Manual

```text
Browser/CLI preparation
→ handoff archive/directory
→ external manual Codex execution
→ Harness verify/complete
```

- не требует Podman;
- сохраняет v0.4.0 core semantics;
- подходит для greenfield/brownfield/hybrid;
- execution вне Harness явно обозначается как external/manual и не получает ложных sandbox guarantees.

#### Mode B — Local Automatic

```text
one local Codex CLI adapter
+ rootless Podman sandbox
+ disposable execution root
+ independent verification/apply
```

- production-supported host: Linux;
- sandbox backend: rootless Podman only;
- network default `NONE`;
- no unsandboxed fallback.

#### Mode C — Git Publication

- one local Git repository;
- exact local commit;
- explicit push;
- one GitHub draft PR adapter;
- no force push;
- no merge;
- deployment only through declared explicit command route.

#### Mode D — Local Parallel

- one local Git repository/monorepo;
- automatic sandboxed execution only;
- local atomic leases;
- dedicated worktrees;
- conservative conflict analysis;
- mandatory integration task;
- production-tested concurrency limit: `2` simultaneous Task executions in v1.0.

Higher values are rejected or treated as unsupported until a later version expands the tested boundary.

#### Mode E — Single-Node Remote

- one server process;
- SQLite WAL on local filesystem;
- local project/artifact storage;
- one top-level worker;
- API tokens;
- roles OWNER/OPERATOR/APPROVER/VIEWER;
- import/export/backup/restore;
- bounded internal parallelism according to Mode D.

### 3.2. Supported skill scope

```text
REUSE
CONFIGURE
TASK_ONLY
EXTEND PROJECT declarative skill
CREATE PROJECT declarative skill
```

UNIVERSAL/PROFILE authoring и executable plugins не поддерживаются.

### 3.3. Supported implementation levels

```text
PROTOTYPE → ALPHA → BETA → MVP → RELEASE
```

Семантика стадий, Stage Gate и level-up фиксируется как public contract v1.0.

## 4. Platform support contract

Подтверждённая минимальная Python requirement v0.4.0 — Python 3.11+. Для v1.0 release candidate команда обязана зафиксировать точную tested matrix в `COMPATIBILITY_MATRIX.md`.

Нельзя оставлять формулировку «работает везде».

Минимальное правило release:

- тестируется заявленная минимальная Python 3.11;
- тестируется основная Python minor, выбранная для production packaging;
- Linux является обязательной платформой для automatic/server modes;
- exact tested Git, Podman и SQLite versions фиксируются из фактической CI/release environment;
- manual local mode на других OS может документироваться только как tested или best-effort, без production guarantee;
- architecture identifiers и container image platforms перечисляются явно;
- unsupported combinations отклоняются doctor либо получают ясный warning до side effect.

Этот документ не угадывает будущие номера Git/Podman. Они фиксируются на основе фактического v1.0 qualification run.

## 5. Public contract freeze

До Release Candidate необходимо заморозить:

- CLI command names и exit-code classes;
- Result Envelope fields;
- canonical IDs/prefixes;
- status vocabularies и transitions;
- `PROJECT_INPUT` schema;
- Stage State/Plan/Acceptance contracts;
- Agent Task Result;
- Repository/Publication/Deployment contracts;
- Skill lifecycle contracts;
- Parallel Batch/Lease contracts;
- remote API `/api/v1` request/response shapes;
- Project Lock semantics;
- archive layout и manifest rules;
- migration discovery/application protocol;
- error/reason codes.

Freeze не означает запрет backward-compatible additions после v1.0. Он означает, что несовместимые изменения требуют v2 или formal compatibility bridge.

## 6. Schema и registry normalization

v1.0 release preparation обязана выполнить один полный audit:

1. каждый persisted entity имеет schema;
2. каждый status берётся из canonical registry;
3. каждый ID prefix зарегистрирован один раз;
4. aliases отсутствуют либо имеют documented migration mapping;
5. no duplicated contract names с разной semantics;
6. every registry exact version/digest входит в Project Lock;
7. JSON Schema и Python validation дают согласованные результаты;
8. unknown fields policy определена для каждого security-sensitive contract;
9. historical compatibility mapping отделён от new write rules;
10. generated documentation строится из actual registries/schemas.

Нельзя выпускать v1.0 с известным расхождением, аналогичным `Task COMPLETED` vs `DONE`.

## 7. Migration chain

Обязательный supported path:

```text
v0.4.0
→ v0.4.1
→ v0.5.0
→ v0.5.1
→ v0.6.0
→ v0.6.1
→ v0.7.0
→ v0.8.x
→ v1.0.0
```

Engine может применять migrations последовательно автоматически после explicit migration command/approval, но не пропускает transforms.

Для каждой migration:

- immutable ID/version;
- preconditions;
- source/target schema range;
- deterministic transform;
- snapshot/backup;
- validation;
- affected generated artifacts;
- prompt/skill invalidation;
- reversibility или compensation;
- recovery procedure;
- tests from real previous-version fixture.

Historical Runs/Evidence не переписываются. Success criteria:

- direct import v0.4.0 archive в v1.0 вызывает полную chain;
- после chain project semantics соответствуют промежуточным decisions;
- отсутствующие новые decisions (`target_level`, activation, remote membership) запрашиваются, а не угадываются;
- повторный migration run идемпотентен;
- partial migration recoverable.

## 8. Compatibility Matrix

Создать отдельный normative `COMPATIBILITY_MATRIX.md` в v1.0 distribution с фактически протестированными combinations:

| Area | Обязательные поля |
|---|---|
| Python | exact supported minors |
| OS | distro/family, architecture, mode |
| Podman | minimum/tested versions, rootless requirements |
| Git | minimum/tested versions |
| SQLite | library versions supplied by supported Python |
| Codex CLI | tested adapter profile revision and compatible version/range |
| GitHub transport | CLI/API mode and tested revision |
| Archive/schema | readable and writable version ranges |
| Container image | exact digest/platforms |

Unlisted combination считается unsupported, а не автоматически совместимой.

## 9. Packaging и distribution

v1.0 distribution должна содержать:

```text
wheel/source package
embedded local runtime
server entry point/package
registries
schemas
seed ACTIVE skills
pinned adapter/sandbox profiles
container image build definition + exact release digest reference
migrations
fixtures
human documentation
FILE_INDEX
MANIFEST.sha256
dependency and license inventory required by the accepted Technology/Supply-Chain baseline
release notes
compatibility matrix
```

Обязательные свойства:

- wheel устанавливается в clean environment без network для bundled runtime dependencies либо dependencies полностью declared/vendored according to distribution policy;
- `doctor` работает из source, installed wheel и embedded handoff runtime;
- package version, `resources/VERSION`, manifest и Project Lock compatible range совпадают;
- reproducible archive tree and hashes;
- no test secrets/credentials;
- no development caches or local paths;
- licenses/dependency inventory соответствуют фактическому package.

Dependency/license inventory является обычным release artifact и не вводит отдельную supply-chain platform.

## 10. Documentation set

v1.0 должна обновить существующую документацию, не переписывая архитектуру с нуля.

Минимум:

- Getting Started для Local Manual;
- Local Automatic prerequisites/doctor;
- Implementation Levels и Stage Gates;
- Brownfield maturity/level-up;
- Git publication;
- PROJECT skill lifecycle;
- Parallel execution boundaries;
- Server installation, users, backup/restore;
- security/trust boundaries;
- migration guide from v0.4.0;
- operational recovery guide;
- CLI reference;
- remote API reference;
- known limitations/non-goals;
- compatibility matrix;
- release notes.

Все examples проходят parser/schema validator. Links, generated indexes и manifest проверяются автоматически.

## 11. Stable error model

Каждая ошибка должна иметь:

```yaml
status: BLOCKED | FAILED_RECOVERABLE | INVALID | ...
code: STABLE_MACHINE_CODE
message: human-readable
subject_ref: optional
recovery_options: []
resume_condition: optional
correlation_id: ...
```

v1.0 audit обязан:

- устранить raw unclassified exceptions на expected paths;
- запретить false success после partial side effect;
- обеспечить stable codes для migration/sandbox/Git/skill/lease/server failures;
- сохранить diagnostic cause без secrets;
- различать user input, policy denial, environment failure, defect и external uncertainty.

## 12. Security qualification

### 12.1. Static/control checks

- strict schemas;
- no shell command construction;
- path normalization;
- archive traversal/symlink/device rejection;
- secrets forbidden in canonical artifacts;
- capability default deny;
- control-plane write invariants;
- dependency/container image pinning;
- token hashing/redaction;
- project isolation.

### 12.2. Sandbox adversarial suite

- host filesystem escape;
- `.harness` tampering;
- network access in `NONE`;
- privilege escalation/capability check;
- process/pid/output exhaustion;
- orphan child process;
- symlink/hardlink escape;
- result-channel abuse;
- secret exfiltration to logs/result;
- canonical base race.

### 12.3. Publication/deployment suite

- ref/branch injection;
- protected branch bypass;
- force push attempt;
- credential leakage;
- duplicate PR after timeout;
- deployment blind retry prevention;
- revision mismatch;
- production approval separation.

### 12.4. Server suite

- authentication bypass;
- role escalation;
- cross-project object access;
- idempotency collision;
- optimistic revision race;
- malicious import;
- path traversal;
- transaction crash at each phase;
- token leakage;
- backup/restore integrity.

Ни один unresolved critical/high issue внутри supported threat model не допускается к v1.0.

## 13. Тестовый план: functional end-to-end qualification

Обязательные fixtures:

### 13.1. Greenfield Local Manual

```text
documentation-first intake
→ approvals
→ target Prototype
→ handoff
→ two manual Agent Results
→ verification
→ Stage Acceptance
→ TARGET_LEVEL_REACHED
```

### 13.2. Greenfield Local Automatic

```text
target Alpha
→ Prototype Tasks in sandbox
→ Prototype Gate
→ Alpha delta
→ Alpha Gate
```

Проверяется отсутствие future-stage work.

### 13.3. Brownfield

```text
read-only inventory
→ claimed level
→ maturity assessment
→ Brownfield approval
→ complete current stage
→ level-up
```

### 13.4. Git publication

```text
verified Task
→ exact commit
→ explicit push to bare/test remote
→ draft GitHub adapter contract result
```

Live GitHub smoke может выполняться gated release job, но deterministic stub/contract suite обязателен и не требует external credentials.

### 13.5. PROJECT skill

```text
gap analysis
→ EXTEND/CREATE DRAFT
→ deterministic evaluation
→ activation approval
→ Task routing
→ revision update/invalidation
```

### 13.6. Parallel Batch

```text
two disjoint Tasks
→ leases/worktrees
→ concurrent Runs
→ commits
→ integration task
→ combined PASS
```

И negative overlap/expiry/crash cases.

### 13.7. Remote server

```text
import project
→ add members
→ concurrent status/mutation requests
→ approval
→ queued automatic Run
→ export
→ restore/import parity
```

## 14. Reliability и recovery qualification

Обязательные tests:

- process termination during every major state transaction;
- disk-full/write failure injection where test environment permits;
- corrupted manifest/artifact detection;
- stale lock/lease reconciliation;
- orphan container/worktree recovery;
- interrupted apply rollback;
- interrupted Git publication reconciliation;
- interrupted deployment reconciliation;
- server DB/filesystem journal recovery;
- backup then restore to clean host;
- export then local validation;
- retry creates new immutable Run, not mutation of old Run.

A recovery test passes only if outcome is one of two known valid states, not «process started again».

## 15. Performance boundaries

v1.0 не вводит performance platform, но должна исключить очевидные operational blockers.

Release qualification фиксирует фактические baselines для:

- `doctor` on distribution;
- project status load for reference fixture;
- JIT compilation one Task;
- archive validate/import/export;
- server API read latency under small-team load;
- SQLite mutation serialization;
- two-Task parallel batch overhead.

Thresholds выбираются до RC на основе supported fixture sizes и фиксируются в release acceptance record. Они не должны превращаться в обещание arbitrary scale.

## 16. Observability и audit readiness

В рамках существующего scope должны быть доступны:

- correlation/request IDs;
- Run/Task/Stage/Batch/Job refs;
- structured Result Envelopes;
- bounded redacted logs;
- append-only events/evidence;
- server audit records;
- exact next/recovery route;
- `doctor`/validation reports.

Новая metrics/telemetry SaaS integration не требуется. Пользователь может собирать server logs внешними средствами.

## 17. Release gates

### 17.1. Contract Gate

- schemas/registries synchronized;
- no undocumented aliases;
- compatibility matrix complete;
- API/CLI freeze approved.

### 17.2. Migration Gate

- every adjacent migration PASS;
- v0.4.0→v1.0 chain PASS;
- rollback/recovery tested;
- historical evidence immutable.

### 17.3. Functional Gate

- all supported end-to-end modes PASS;
- stage paths and brownfield routes PASS;
- publication/skill/parallel/server paths PASS.

### 17.4. Security Gate

- threat model current;
- adversarial suites PASS;
- no unresolved critical/high supported-scope findings;
- secret scan PASS.

### 17.5. Reliability Gate

- crash injection PASS;
- backup/restore PASS;
- orphan/reconciliation PASS;
- no false-success paths.

### 17.6. Packaging/Documentation Gate

- source/wheel/embedded/server installations PASS;
- docs validator PASS;
- examples schemas PASS;
- manifest/file index exact;
- release archive reproducible.

### 17.7. Release Approval Gate

Final decision records:

- production scope accepted;
- known limitations accepted;
- compatibility matrix accepted;
- migration/recovery accepted;
- release artifact digests accepted.

## 18. Defect policy

Release blockers:

```text
CRITICAL
HIGH within supported scope
false success
data/control-plane corruption
secret disclosure
sandbox escape within threat model
unrecoverable migration defect
cross-project authorization defect
non-deterministic canonical transition
```

`MEDIUM` может быть accepted только с:

- documented impact;
- safe workaround;
- owner;
- planned patch;
- explicit release decision.

Unsupported-scope feature request не является defect.

## 19. Versioning after v1.0

- `1.0.x`: backward-compatible fixes/hardening;
- `1.x`: backward-compatible capabilities within architecture;
- `2.0`: incompatible contracts/semantics.

Security suspension может немедленно disable adapter/skill/route через existing lifecycle without rewriting history.

Every release updates exact distribution version, registry/schema versions when changed, manifest and compatibility data. Переход к `v1.0.0` сам по себе не увеличивает canonical schema number: final v0.8.x value сохраняется, если RC audit не требует реальной contract migration. Любое исправление contract до freeze получает отдельную migration и только тогда повышает schema/registry version.

## 20. Критерии приёмки / Definition of Done v1.0

v1.0 считается готовой только если:

1. реализованы все версии этой серии в указанном порядке;
2. v1.0 не добавляет новую подсистему;
3. supported production modes явно перечислены;
4. unsupported scope явно перечислен;
5. public contracts и status semantics согласованы;
6. migration chain v0.4.0→v1.0 доказана fixtures;
7. Local Manual и Local Automatic e2e PASS;
8. greenfield/brownfield/level-up PASS;
9. commit/push/draft PR/deployment routes PASS;
10. declarative PROJECT skill lifecycle PASS;
11. local two-Task parallel integration PASS;
12. single-node remote auth/concurrency/import/export/backup PASS;
13. sandbox, authorization и crash adversarial suites PASS;
14. source/wheel/embedded/server packaging PASS;
15. documentation, FILE_INDEX и MANIFEST PASS;
16. exact compatibility matrix опубликована;
17. known limitations приняты explicit decision;
18. unresolved critical/high supported-scope defects отсутствуют;
19. release artifacts имеют immutable SHA-256 digests;
20. final Release Approval Gate принят.

## 21. Порядок реализации v1.0

1. Заморозить production scope и unsupported list.
2. Провести contract/status/schema/registry audit.
3. Завершить migration chain и fixtures.
4. Зафиксировать platform compatibility matrix.
5. Устранить failure/recovery gaps всех предыдущих versions.
6. Выполнить functional e2e matrix.
7. Выполнить security/adversarial matrix.
8. Выполнить crash/backup/restore matrix.
9. Проверить packaging во всех supported forms.
10. Обновить и валидировать документацию.
11. Провести Release Candidate qualification.
12. Закрыть blockers, повторить affected suites.
13. Зафиксировать artifact digests и approvals.
14. Выпустить v1.0.0 без post-freeze feature additions.
