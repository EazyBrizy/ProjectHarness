# Project Harness v0.6.0 — Repository Adapter, Commit, Push, Pull Request и Deployment Route

**Базовая версия:** Project Harness Engine v0.5.1  
**Целевая версия:** v0.6.0  
**Тип релиза:** MINOR / controlled publication side effects  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью принятые v0.4.1, v0.5.0 и v0.5.1  
**Порядок реализации:** четвёртый документ серии

## 1. Назначение версии

v0.6.0 добавляет контролируемый путь от проверенного локального изменения до публикации:

```text
verified product diff
→ local commit
→ optional explicit push
→ optional draft Pull Request
→ optional separate deployment route
```

Версия разделяет четыре side-effect boundary:

1. создание локального commit;
2. push конкретной ветки;
3. создание одного Pull Request через один adapter;
4. запуск заранее объявленного deployment route.

Каждое действие имеет отдельную capability, approval, evidence и recovery route. Успех предыдущего действия не является неявным разрешением следующего.

## 2. Не входит в scope

v0.6.0 не должна включать:

- parallel worktrees или ownership leases;
- polyrepo coordinated execution;
- force push;
- прямую запись в protected branch;
- merge Pull Request;
- review management;
- автоматическую обработку review comments;
- несколько PR providers;
- универсальную Git hosting abstraction с полностью реализованными GitLab/Bitbucket/Azure adapters;
- универсальный multi-cloud deployment engine;
- Kubernetes/Helm/Terraform orchestration как встроенный Harness feature;
- canary, blue/green или progressive delivery framework;
- автоматический production deployment после каждой Task;
- release publication/signing beyond explicit project command;
- secret storage;
- работу поверх unrelated dirty index без решения пользователя;
- отдельные worktrees для каждого Task — это v0.7.0.

## 3. Общий принцип side-effect separation

Canonical цепочка:

```text
IMPLEMENTATION_VERIFIED
→ COMMIT_ELIGIBLE
→ COMMITTED
→ PUSH_ELIGIBLE
→ PUSHED
→ PR_ELIGIBLE
→ PR_CREATED
```

Deployment не является обязательным продолжением PR:

```text
VERIFIED_RELEASE_OR_DEPLOYMENT_TASK
→ DEPLOYMENT_APPROVED
→ DEPLOYING
→ DEPLOYMENT_VERIFIED / DEPLOYMENT_FAILED_RECOVERABLE
```

Task, publication и deployment не должны использовать один status. Реализация может быть успешной, даже если remote недоступен.

## 4. Repository Adapter

Добавить пакет:

```text
src/project_harness/repositories/
  __init__.py
  base.py
  git_local.py
  models.py
```

Минимальный interface:

```python
class RepositoryAdapter(Protocol):
    def discover(self, path: Path) -> dict: ...
    def status(self, repository: dict) -> dict: ...
    def create_branch(self, plan: dict) -> dict: ...
    def create_commit(self, plan: dict) -> dict: ...
    def push(self, plan: dict) -> dict: ...
```

В v0.6.0 существует одна реализация:

```text
GIT_LOCAL
```

Adapter выполняет Git-команды как argv arrays через controlled process runner. Он не использует shell и не выполняет destructive cleanup.

## 5. Repository discovery contract

Для каждого repository записывается revisioned record:

```yaml
repository:
  id: REP-PROJECT-001
  revision: 1
  kind: GIT
  path: .
  role: IMPLEMENTATION
  git_dir_kind: WORKTREE
  head_revision: abc123
  current_branch: main
  detached_head: false
  default_branch: main
  canonical_remote: origin
  remotes:
    - name: origin
      fetch_url: <redacted-or-normalized-url>
      push_url: <redacted-or-normalized-url>
  protected_branches:
    - main
  branch_namespace: harness/
  dirty_state:
    worktree_paths: []
    index_paths: []
    untracked_paths: []
  status: ACTIVE
```

Discovery должна определить:

- repository root;
- worktree/submodule boundary;
- exact `HEAD`;
- current/detached branch;
- remotes;
- canonical remote из project policy либо ambiguity;
- default/protected branches из input/policy, а не из догадки;
- staged, unstaged и untracked changes;
- path outside repository;
- Git version и command availability.

Credentials и embedded tokens в remote URL должны быть redacted в artifacts/logs.

## 6. Existing dirty state policy

Harness никогда не выполняет автоматически:

```text
git reset --hard
git clean -fd
git checkout -- <unrelated files>
git stash
```

До local commit выполняется classification:

```text
TASK_VERIFIED_CHANGE
UNRELATED_USER_CHANGE
PREEXISTING_INDEX_CHANGE
GENERATED_STALE_CHANGE
UNKNOWN_CHANGE
```

Поскольку dedicated worktrees появятся только в v0.7.0, v0.6.0 применяет консервативное правило:

- index должен быть пуст до staging Harness commit;
- unrelated modified/untracked paths допускаются только если доказано, что exact commit path set с ними не пересекается и Git operation их не затронет;
- любой `UNKNOWN` или overlap → `WAITING_DECISION`;
- Harness не stash-ит изменения;
- пользователь может вручную очистить/commit-ить state либо выбрать `REVIEW_ONLY`.

## 7. Publication policy

Publication policy задаётся независимыми полями, а не одним неоднозначным mode:

```yaml
publication:
  repository_adapter: GIT_LOCAL
  commit_policy: AUTO_AFTER_PASS
  push_policy: EXPLICIT
  pull_request_policy: EXPLICIT_DRAFT_AFTER_PUSH
  pull_request_adapter: GITHUB_PULL_REQUEST
  canonical_remote: origin
  protected_branches: [main]
  branch_namespace: harness/
```

Allowed values:

```text
commit_policy: REVIEW_ONLY | EXPLICIT | AUTO_AFTER_PASS
push_policy: DISABLED | EXPLICIT
pull_request_policy: DISABLED | EXPLICIT_DRAFT_AFTER_PUSH
```

Рекомендуемый default для нового configured repository:

```text
commit_policy: AUTO_AFTER_PASS
push_policy: EXPLICIT
pull_request_policy: DISABLED
```

Meaning:

- local commit создаётся только после всех checks и соответствующего capability/policy;
- push всегда является отдельным explicit action;
- draft PR создаётся только после успешного push и отдельного approval;
- deployment всегда отдельный route.

## 8. Commit Plan

Использовать существующий prefix `CPL`.

```yaml
commit_plan:
  id: CPL-PROJECT-TSK-001
  revision: 1
  task_ref: TSK-PROJECT-001@2
  run_ref: RUN-PROJECT-001@1
  repository_ref: REP-PROJECT-001@1
  base_revision: abc123
  target_branch: harness/tsk-project-001-primary-flow
  expected_head_before_commit: abc123
  files:
    add:
      - src/feature.py
    modify:
      - tests/test_feature.py
    delete: []
  required_checks:
    - CHK-PROJECT-UNIT-001
  constraint_checks:
    - CHK-PROJECT-SCOPE-001
    - CHK-PROJECT-SECRETS-001
  message: "feat(core): implement primary flow"
  signing: DISABLED
  push: false
  pull_request: false
  capability_grant_ref: CGR-GIT-COMMIT-001
```

Commit Plan создаётся после independent verification, а не агентом.

## 9. Branch policy

v0.6.0 выполняет publication внутри Harness-controlled project workspace/handoff copy. Исходный brownfield repository, использованный как read-only source при intake, не переключается и не изменяется. Если пользователь подключает обычный primary worktree напрямую, branch switch/commit требует отдельного явного решения; dedicated worktrees по умолчанию появятся только в v0.7.0.

Если current branch является protected/default branch, Harness перед commit создаёт отдельную branch:

```text
harness/<task-id>-<slug>
```

Правила:

- branch name детерминирован и validated;
- base revision exact;
- branch не создаётся поверх неожиданно изменившегося `HEAD`;
- существующая branch с тем же именем допускается только если она соответствует тому же task/base и это доказано;
- automatic overwrite/delete branch запрещены;
- detached HEAD требует явного branch creation plan;
- direct commit в protected branch запрещён, даже если Git технически разрешает.

В v0.6.0 один active publishing Task на repository является operational precondition. Параллельное branch/worktree управление относится к v0.7.0.

## 10. Local commit algorithm

1. Прочитать Repository State и сверить `HEAD` с Commit Plan.
2. Убедиться, что Task `DONE`, Run `SUCCEEDED`, verification `PASS`.
3. Проверить control-plane invariants.
4. Проверить actual diff и exact files list.
5. Проверить index: он пуст и не содержит unrelated data.
6. Создать/перейти на approved branch без затрагивания unrelated files.
7. Stage только exact pathspec из Commit Plan.
8. Сверить staged diff с verified diff по paths и content digests.
9. Выполнить secret/policy checks, если они mandatory.
10. Создать commit с deterministic message.
11. Получить commit SHA и tree SHA.
12. Проверить, что commit parent равен expected base/previous Harness commit.
13. Записать immutable Commit Evidence.
14. Очистить index только как результат успешного commit; не очищать unrelated state.

Если staged diff отличается, commit блокируется. Harness не добавляет `git add -A` по умолчанию.

## 11. Commit Evidence

```yaml
commit_evidence:
  id: ART-PROJECT-COMMIT-001
  commit_plan_ref: CPL-PROJECT-TSK-001@1
  repository_ref: REP-PROJECT-001@1
  branch: harness/tsk-project-001-primary-flow
  commit_sha: def456
  parent_sha: abc123
  tree_sha: fedcba
  file_digests:
    src/feature.py: sha256:...
    tests/test_feature.py: sha256:...
  created_at: ...
  actor: ACT-HARNESS-LOCAL
  result_status: COMPLETED
```

Task history не переписывается. Commit Evidence ссылается на уже успешный Run.

## 12. Push Plan и explicit approval

Push — отдельный plan:

```yaml
push_plan:
  id: ART-PROJECT-PUSH-PLAN-001
  revision: 1
  repository_ref: REP-PROJECT-001@1
  commit_ref: ART-PROJECT-COMMIT-001
  remote: origin
  local_branch: harness/tsk-project-001-primary-flow
  remote_branch: harness/tsk-project-001-primary-flow
  expected_remote_state: ABSENT_OR_MATCHING_ANCESTOR
  force: false
  capability_grant_ref: CGR-GIT-PUSH-001
  approval_ref: DEC-PROJECT-PUSH-001
```

Перед approval пользователь видит:

- exact remote host/name;
- branch;
- commit SHA и parents;
- количество файлов;
- checks;
- protected branch evaluation;
- recovery route.

Push rules:

- только configured canonical remote;
- только allowed branch namespace;
- `--force` и `--force-with-lease` запрещены в этой версии;
- refspec формируется Kernel, не user string;
- protected branch target отклоняется;
- remote advancement/non-fast-forward → recoverable blocker;
- credentials подаются через external mechanism и не логируются;
- push запускается через v0.5.1 sandbox/process policy с минимальным network/secret grant.

## 13. Один Pull Request Adapter

### 13.1. Provider choice

В v0.6.0 реализуется один adapter:

```text
GITHUB_PULL_REQUEST
```

Core interface остаётся узким, чтобы provider code не проникал в Runtime:

```python
class PullRequestAdapter(Protocol):
    def doctor(self, profile: dict) -> dict: ...
    def create_draft(self, request: dict) -> dict: ...
```

Не реализуются update, merge, close, reviews или comments.

Release implementation обязана выбрать ровно один transport для `GITHUB_PULL_REQUEST` и зафиксировать его в adapter profile/compatibility tests. Второй transport в v0.6.0 не реализуется. В тестах используется stub/mock transport. Runtime не должен строить произвольные shell commands.

### 13.2. PR request contract

```yaml
pull_request_request:
  id: ART-PROJECT-PR-REQUEST-001
  revision: 1
  adapter: GITHUB_PULL_REQUEST
  repository_ref: REP-PROJECT-001@1
  remote: origin
  head_branch: harness/tsk-project-001-primary-flow
  base_branch: main
  title: "feat(core): implement primary flow"
  draft: true
  body_sections:
    summary_ref: ART-PROJECT-TASK-REPORT-001
    verification_refs:
      - CHK-PROJECT-UNIT-001
    stage: PROTOTYPE
    known_limitations_ref: VAL-PROJECT-PROTOTYPE-001
    blocker_refs: []
  capability_grant_ref: CGR-PR-CREATE-001
  approval_ref: DEC-PROJECT-PR-001
```

PR body должен содержать:

- human-readable summary фактического изменения;
- Task/Run references;
- verification evidence;
- Implementation Stage;
- known limitations;
- manual actions;
- отсутствие ложного утверждения, что deployment выполнен.

### 13.3. PR result

```yaml
pull_request_result:
  request_ref: ART-PROJECT-PR-REQUEST-001@1
  provider: GITHUB
  external_id: "123"
  web_url: <provider-returned-url>
  head_sha: def456
  base_branch: main
  draft: true
  created_at: ...
  result_status: COMPLETED
```

URL считается data, полученной от provider, и сохраняется только после validation допустимой схемы/host.

## 14. Publication failure model

Product Task не переисполняется, если implementation уже проверена и commit создан.

Примеры:

| Ошибка | Product result | Publication result |
|---|---|---|
| remote unavailable | остаётся successful | `FAILED_RECOVERABLE` |
| authentication failure | остаётся successful | blocker с credential route |
| non-fast-forward | остаётся successful | blocker: refresh/rebase/manual decision |
| PR provider unavailable | commit/push сохраняются | PR route recoverable |
| duplicate PR | reconcile existing external object | no duplicate creation |

Каждая внешняя операция получает idempotency fingerprint:

```text
repository + remote + branch + commit_sha + operation_kind
```

Перед повтором Harness пытается определить, не произошёл ли side effect при потерянном ответе.

## 15. Deployment как отдельный явный route

### 15.1. Ограниченная модель

Harness не знает, как разворачивать все типы проектов. Проект объявляет один или несколько named routes, но v0.6.0 реализует только общий command adapter поверх v0.5.1 sandbox.

```yaml
deployment_route:
  id: DEP-PROJECT-STAGING-001
  revision: 1
  name: staging
  command:
    - ./scripts/deploy.sh
    - staging
  working_directory: .
  environment: STAGING
  allowed_repository_revision: def456
  required_capabilities:
    - COMMAND_EXECUTE
    - NETWORK_WRITE
    - DEPLOY
  secret_environment_refs:
    - DEPLOY_TOKEN
  approval_required: true
  verification_command:
    - ./scripts/smoke-test.sh
    - staging
  rollback_command: null
  status: ACTIVE
```

Наличие `rollback_command: null` не означает, что deployment безопасен. Для stages, где rollback обязателен, Stage Gate не пропускает такой route.

### 15.2. Deployment rules

- route должен существовать в accepted project configuration;
- command является argv array;
- произвольная команда из CLI parameter запрещена;
- deployed revision exact;
- staging и production — разные route IDs;
- production требует отдельного approval, даже если staging был успешен;
- capabilities и secrets минимальны;
- network включается только для deployment Run;
- output redacted и bounded;
- verification выполняется отдельно;
- Harness не объявляет deployment успешным только по exit code deploy command;
- side effect uncertainty приводит к reconciliation, а не слепому retry.

### 15.3. Deployment lifecycle

```text
PLANNED
→ WAITING_APPROVAL
→ READY
→ DEPLOYING
→ VERIFYING
→ SUCCEEDED
```

Failure:

```text
DEPLOYING/VERIFYING
→ FAILED_RECOVERABLE
→ RECONCILING
→ SUCCEEDED | ROLLED_BACK | BLOCKED
```

Не следует добавлять новую общую `run` status vocabulary, если deployment хранится как специализированный Request/Result с публичными statuses. Если persisted deployment entity получает собственную группу, она должна быть зарегистрирована и проверяться validator.

## 16. CLI

Добавить команды:

```bash
project-harness repository-status --project <root>
project-harness commit-current --project <root>
project-harness publish-push --project <root> --approval <record>
project-harness publish-pr --project <root> --approval <record>
project-harness deploy --project <root> --route staging --approval <record>
project-harness deployment-status --project <root> --deployment <ref>
```

Имена `publish-push`/`publish-pr` подчёркивают отдельность publication от implementation completion.

Все команды возвращают Result Envelope и не печатают credentials.

## 17. Security и credentials

Capabilities:

```text
GIT_COMMIT
GIT_PUSH
PR_CREATE
DEPLOY
NETWORK_WRITE
SECRET_REFERENCE
EXTERNAL_SYSTEM_WRITE
```

Правила:

- Git/PR/deployment processes принадлежат Kernel, а не product agent; agent не получает `.git` metadata или publication credentials;
- для Git operation sandbox получает exact Harness-controlled repository/worktree и требуемую `.git` metadata на запись только на время operation;
- local commit не требует network;
- push/PR/deployment требуют explicit network grant;
- credentials поступают из external env/helper и никогда не сериализуются;
- remote URL с userinfo/token блокируется либо redacted;
- Git hooks по умолчанию не должны неожиданно выполнять host code. Commit выполняется в controlled environment; policy должна явно определить hook handling;
- для первой версии рекомендуется `hooks: DISABLED_FOR_HARNESS_COMMIT`, при этом required checks выполняются Harness verification отдельно;
- Git config scope ограничивается repository/local process;
- signing не включается автоматически;
- deployment scripts рассматриваются как project code и запускаются в sandbox.

## 18. Deployment ID и status registry

Deployment Route/Attempt является persisted entity. В `id_prefixes.yaml` добавить:

```yaml
- prefix: DEP
  entity: Deployment Route or Attempt
  schema_key: deployment
  status: ACTIVE
```

В `statuses.yaml` добавить группы:

```yaml
repository:
  - DISCOVERED
  - ACTIVE
  - STALE
  - BLOCKED
  - RETIRED

deployment_route:
  - DRAFT
  - VALIDATED
  - ACTIVE
  - SUSPENDED
  - DEPRECATED
  - RETIRED

deployment:
  - PLANNED
  - WAITING_APPROVAL
  - READY
  - DEPLOYING
  - VERIFYING
  - SUCCEEDED
  - FAILED_RECOVERABLE
  - RECONCILING
  - ROLLED_BACK
  - BLOCKED
  - CANCELLED
```

Repository discovery создаёт `DISCOVERED`; accepted project configuration переводит exact revision в `ACTIVE`. Deployment Route использует `deployment_route`, а execution attempt — `deployment`. Эти vocabularies нельзя смешивать. Commit/Push/PR plans остаются immutable intent records: их eligibility хранится в Gate/validation result, поэтому отдельный plan status lifecycle не добавляется.

## 19. Изменения модулей

Новые modules:

```text
repositories/base.py
repositories/git_local.py
repositories/models.py
publication/plans.py
publication/github_pr.py
publication/results.py
deployment/routes.py
deployment/runtime.py
```

Обновить:

- `cli.py` — repository/publication/deployment commands;
- `runtime.py` — связь successful Task с Commit Plan;
- `safety.py` — ref/branch/remote/path validation;
- `validation.py` — repository, commit, push, PR, deployment contracts;
- `project_input.py` — publication/deployment policy fields только при configured route;
- `render.py` — approval views;
- `archive.py` — включить evidence, исключить credentials;
- `capabilities.yaml` — использовать уже существующие entries;
- `contracts.yaml` и `id_prefixes.yaml` — зарегистрировать реально persisted entities, не дублируя generic `ART` без необходимости.

## 20. Schemas и input contract

`PROJECT_INPUT` получает строгие sections `publication` и `deployment`. Они содержат policy/route declarations, но не credentials:

```yaml
publication:
  repository_adapter: null
  commit_policy: REVIEW_ONLY
  push_policy: DISABLED
  pull_request_policy: DISABLED
  pull_request_adapter: null
  canonical_remote: null
  protected_branches: []
  branch_namespace: harness/
deployment:
  routes: []
```

Conditional rules:

- non-null repository adapter допускает только `GIT_LOCAL`;
- enabled PR policy требует `GITHUB_PULL_REQUEST`;
- remote/branch names проходят semantic validation;
- `deployment.routes` содержит declarative route objects/refs с argv arrays; arbitrary command strings запрещены;
- secret references допустимы, secret values запрещены.

Versioning:

```text
PROJECT_INPUT.schema_version: 5
SCHEMA-PROJECT-PREPARATION-INPUT@5
Harness canonical SCHEMA_VERSION: 8
Migration: MIG-ENGINE-0.5.1-TO-0.6.0
```

Добавить schemas:

```text
repository.schema.json
commit_plan.schema.json
commit_evidence.schema.json
push_plan.schema.json
publication_result.schema.json
pull_request_request.schema.json
deployment_route.schema.json
deployment_result.schema.json
```

Schemas должны запрещать unknown security-sensitive fields и shell-string commands.

### 20.1. Contract catalog и registry versions

В `contracts.yaml` зарегистрировать:

```yaml
repository:
  id_prefix: REP
  persistence: PERSISTENT
  lifecycle: repository
  storage_path: .harness/repositories/{id}@{revision}.yaml
  revision_policy: VERSIONED
push_plan:
  id_prefix: ART
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/changes/PUSH/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
pull_request_request:
  id_prefix: ART
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/changes/PULL_REQUESTS/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
publication_result:
  id_prefix: ART
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/evidence/PUBLICATION/{id}.yaml
  revision_policy: IMMUTABLE
deployment_route:
  id_prefix: DEP
  persistence: PERSISTENT
  lifecycle: deployment_route
  storage_path: .harness/config/DEPLOYMENT_ROUTES/{id}@{revision}.yaml
  revision_policy: VERSIONED
deployment_attempt:
  id_prefix: DEP
  persistence: PERSISTENT
  lifecycle: deployment
  storage_path: .harness/runtime/DEPLOYMENTS/{id}@{revision}.yaml
  revision_policy: VERSIONED
```

`commit_plan` уже зарегистрирован и не дублируется. Commit Evidence использует generic evidence/artifact contract.

Expected registry versions:

```text
REG-ID-PREFIXES:      3 → 4   # DEP
REG-CONTRACT-CATALOG: 5 → 6
REG-STATUSES:         6 → 7   # repository, deployment_route, deployment
```

## 21. Migration v0.5.1 → v0.6.0

Default для существующих проектов:

```yaml
publication:
  repository_adapter: null
  commit_policy: REVIEW_ONLY
  push_policy: DISABLED
  pull_request_policy: DISABLED
  pull_request_adapter: null
  canonical_remote: null
  protected_branches: []
  branch_namespace: harness/

deployment:
  routes: []
```

Migration:

- не создаёт remote;
- не выполняет `git init`;
- не включает auto-commit;
- не предполагает `main` как default branch без evidence/answer;
- не добавляет deployment command;
- сохраняет completed Task history.

Активация publication требует repository discovery и approval policy.

## 22. Recovery и cleanup

- commit failure до создания object оставляет Task successful, Commit Plan retryable;
- commit SHA после потерянного process response reconciled по tree/parent/message fingerprint;
- push retry сначала проверяет remote ref;
- PR retry сначала ищет exact head/base/external idempotency marker;
- deployment retry запрещён до reconciliation текущего environment state;
- branch deletion не входит в automatic cleanup;
- failed publication records сохраняются;
- секретные process artifacts удаляются после bounded retention;
- user dirty files не изменяются при recovery.

## 23. Тестовый план

### 23.1. Git adapter unit/integration

Использовать temporary repositories и bare remote:

- clean repository discovery;
- detached HEAD;
- subdirectory root resolution;
- staged unrelated change blocks commit;
- exact path staging;
- deletion commit;
- branch naming validation;
- protected branch rejection;
- HEAD/base mismatch;
- commit evidence digests;
- no reset/clean/stash;
- push to allowed branch;
- force/refspec injection rejected;
- non-fast-forward recovery.

### 23.2. PR adapter

Stub GitHub transport:

- successful draft PR;
- invalid base/head;
- authentication failure;
- timeout after provider creates PR;
- reconciliation prevents duplicate;
- provider URL/ID validation;
- PR body references evidence and stage;
- no merge/update operations exposed.

### 23.3. Deployment route

Fixture scripts:

- declared staging route success + smoke check;
- undeclared command rejected;
- missing approval;
- revision mismatch;
- secret redaction;
- deploy success but smoke failure;
- uncertain timeout requires reconciliation;
- production cannot reuse staging approval;
- no automatic retry of side effect.

### 23.4. End-to-end

```text
verified Task
→ local exact commit
→ explicit push
→ draft GitHub PR
```

и отдельно:

```text
accepted deployable revision
→ explicit staging deployment
→ independent smoke verification
→ deployment evidence
```

## 24. Критерии приёмки v0.6.0

Версия готова, когда:

1. один local Git Repository Adapter обнаруживает и фиксирует exact repository state;
2. Harness не выполняет reset/clean/stash;
3. commit включает только verified exact paths;
4. protected branch не изменяется напрямую;
5. push требует отдельный plan, capability и approval;
6. force push невозможен через v0.6.0 API/CLI;
7. реализован ровно один draft PR adapter для GitHub;
8. publication failure не переисполняет успешную product Task;
9. external side effects имеют reconciliation/idempotency fingerprint;
10. deployment запускается только через declared route;
11. production deployment требует отдельного approval;
12. deployment verification отделена от deploy command;
13. credentials не сериализуются и redacted в output;
14. v0.5.1 sandbox используется для commands с внешними side effects;
15. parallel worktrees и polyrepo не внедрены преждевременно.

## 25. Порядок реализации

1. Реализовать read-only Repository discovery/status.
2. Зафиксировать policy и schemas.
3. Реализовать exact local commit в temporary Git fixtures.
4. Добавить Commit Evidence и Runtime linkage.
5. Реализовать Push Plan, approval и bare-remote tests.
6. Реализовать GitHub draft PR adapter со stub transport.
7. Добавить reconciliation для push/PR.
8. Реализовать declared deployment route поверх sandbox.
9. Добавить deployment reconciliation и evidence.
10. Обновить CLI/render/validation/archive.
11. Выполнить full security/failure test matrix.
12. Оставить default `REVIEW_ONLY` для migrated projects.

v0.7.0 затем добавит dedicated worktrees, leases и безопасную параллельную интеграцию, используя commit evidence этой версии.
