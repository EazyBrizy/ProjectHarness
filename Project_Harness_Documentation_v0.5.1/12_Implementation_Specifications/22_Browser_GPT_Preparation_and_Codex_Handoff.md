# Browser GPT Preparation and Codex Handoff

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Спецификация определяет Browser GPT как семантический подготовительный слой Project Harness и фиксирует детерминированную передачу подтверждённого проекта в Codex.

Browser GPT не является Agent Adapter исполняемого runtime.

Он не получает право самостоятельно изменять product repository после handoff.

Он выполняет анализ источников, диалог с пользователем и подготовку semantic input.

Project Harness выполняет канонизацию, проверки, компиляцию и packaging.

Codex выполняет только текущую atomic task.

## 2. Граница ответственности

```text
Browser GPT
→ understand natural language
→ analyze uploaded documentation
→ identify material gaps
→ ask adaptive questions
→ propose bounded alternatives
→ record confirmed semantic decisions

Deterministic Harness
→ assign stable IDs
→ validate registries and contracts
→ validate approvals
→ normalize task DAG
→ resolve ACTIVE skills
→ compile current prompt/context
→ generate lock, manifest and ZIP

Codex
→ read current bundle
→ change declared paths
→ run allowed checks
→ write Agent Task Result
```

Ни один слой не должен незаметно присваивать себе governance-функции другого слоя.

## 3. Режим операции

Canonical operation подготовительного слоя:

```text
PREPARE_FOR_CODEX
```

Operation относится к первоначальному `PROJECT_START` или к принятому Project Evolution.

Она не означает `EXECUTE_PRODUCT_TASK`.

Она завершается статусом:

```text
READY_FOR_CODEX
```

Она не может завершаться статусом `PROJECT_COMPLETED`, потому что product tasks ещё не исполнены.

## 4. Входной пакет

Минимальный вход содержит архив Project Harness Engine и описание проекта.

Рекомендуемый вход содержит:

- архив движка;
- документацию проекта;
- список нормативных источников;
- пользовательские ограничения;
- для brownfield — repository directory или ZIP;
- известные defects, gaps и technical debt;
- ожидаемый первый проверяемый outcome.

Browser GPT сначала различает:

```text
ENGINE_ARCHIVE
DOCUMENTATION_ARCHIVE
PROJECT_SOURCE
SUPPLEMENTAL_REQUIREMENT
UNKNOWN_FILE
```

Он не должен считать документационный архив исполняемым движком.

Он не должен утверждать, что видел repository structure, если загружен только README.

## 5. Distribution validation

Первое детерминированное действие:

```bash
python project-harness.py doctor
```

Browser GPT выводит фактический machine result.

При `FAIL` preparation останавливается с точным blocker.

Допустимые recovery routes:

```text
UPLOAD_COMPLETE_ENGINE_ARCHIVE
REPAIR_DISTRIBUTION
USE_MATCHING_DOCUMENTATION_VERSION
CANCEL_PREPARATION
```

Успешный doctor подтверждает registries, schemas, seed ACTIVE skills и entry points.

## 6. START_INTAKE

`START_INTAKE` создаёт provisional control workspace до project-local bootstrap.

Workspace не является product repository.

Для brownfield он обязан находиться вне target repository.

Пример greenfield:

```bash
python project-harness.py start-intake \
  --workspace ./work/project-intake \
  --project-name "Example Project" \
  --mode greenfield \
  --source ./input/requirements.md
```

Пример brownfield:

```bash
python project-harness.py start-intake \
  --workspace ./control/existing-intake \
  --project-name "Existing Project" \
  --mode brownfield \
  --source ./input/docs \
  --repository ./input/repository.zip
```

До accepted handoff исходный brownfield repository остаётся read-only.

## 7. Первый обязательный вопрос

Первый вопрос всегда относится к документации:

```text
Есть ли документация, ТЗ, схемы, ADR, README или другие материалы?
Какие материалы являются нормативными, частичными или устаревшими?
```

Browser GPT сначала анализирует доступные материалы.

Он не повторяет вопрос, если ответ достоверно найден.

При material interpretation он просит подтверждение интерпретации, а не повтор исходного вопроса.

## 8. Адаптивный опрос

Вопросы задаются пакетами по три–пять связанных пунктов.

Обычный целевой budget составляет семь–двенадцать ответов.

До первого Project Definition draft нельзя превышать пятнадцать вопросов без material reason.

Обязательные области:

- first user outcome;
- users;
- initial scale;
- connectivity;
- runtime platforms;
- deployment target;
- data sensitivity;
- integrations;
- scope and non-scope;
- mandatory and forbidden constraints;
- success criteria;
- architecture boundary;
- technology selections;
- minimal causal plan.

Неизвестное, которое не блокирует первый outcome, записывается как bounded unknown или assumption.

Material ambiguity блокирует соответствующий Gate.

## 9. Semantic input

Browser GPT заполняет `PROJECT_INPUT.yaml`.

Файл может использовать JSON syntax, совместимый с YAML 1.2.

Semantic input включает:

```text
metadata
project
profile
architecture
technology
skills
planning
brownfield
approvals
```

Browser GPT отвечает за смысл и grounding.

Harness отвечает за structural validity.

## 10. Project Definition Gate

До approval Browser GPT показывает:

- problem statement;
- primary outcome;
- users;
- scope;
- non-scope;
- constraints;
- success criteria;
- assumptions;
- unknowns.

Approval записывается отдельно от questionnaire answer.

Approval содержит actor и timestamp.

Молчание пользователя не считается approval.

## 11. Architecture Baseline Gate

Browser GPT формирует bounded architecture proposal.

Proposal содержит components, interfaces, data flow, quality attributes, risks и material decisions.

Пользователю показываются существенные alternatives.

Recommendation должна быть отделена от подтверждённого решения.

После approval Harness создаёт versioned Architecture Baseline.

Codex не может менять accepted Architecture Baseline обычной implementation task.

## 12. Technology Baseline Gate

Technology Baseline фиксирует selections, version ranges, build commands, test commands и lint commands.

Выбор не должен зависеть от ещё не проверенного future component.

Browser GPT не заявляет доступность runtime/toolchain без evidence.

Approval Technology Baseline является отдельным Gate.

## 13. Skill Gap Analysis

Последовательность resolution:

```text
documentation and answers
→ accepted Project Definition
→ accepted Architecture Baseline
→ accepted Technology Baseline
→ repeatable workflows
→ Skill Gap Analysis
```

Core actions:

```text
REUSE
CONFIGURE
TASK_ONLY
```

`CREATE` и `EXTEND` не выполняются из сырого questionnaire.

Новый PROJECT skill требует evaluation, validation и activation.

Для каждого проекта создаётся resolution и generated index, а не новая копия всей библиотеки skills.

## 14. Planning contract

Browser GPT предлагает минимальное число Work Packages.

Каждая executable task должна быть atomic.

Task содержит:

- purpose;
- expected result;
- dependency refs;
- requirement and constraint refs;
- read scope;
- write scope;
- forbidden scope;
- primary ACTIVE skill;
- required capabilities;
- acceptance criteria;
- verification commands or checks;
- documentation impact;
- rollback strategy.

Harness нормализует task aliases в canonical IDs.

Harness отклоняет dependency cycle.

Первая причинно доступная task получает `READY`.

Остальные получают `PLANNED`.

## 15. Prompt и Context preparation

Для всего DAG заранее создаются:

```text
Task Contracts
Prompt Plans
Context Plans
Verification Profiles
```

Для будущих tasks compiled bundle не создаётся.

Для текущей READY task Harness создаёт:

```text
Context Packet
Capability Grant
Compiled Prompt Bundle
Run Plan
pre-run Snapshot
NEXT_TASK
```

Compiled prompt связан с exact task revision и Run reservation.

## 16. Handoff approval

Перед packaging Browser GPT показывает:

- accepted Project Definition;
- Architecture Baseline;
- Technology Baseline;
- key decisions;
- constraints;
- unresolved unknowns;
- Skill Gap result;
- roadmap;
- first READY task;
- external sandbox limitations.

Только после explicit Handoff approval запускается `prepare`.

## 17. Deterministic prepare

```bash
python project-harness.py prepare \
  --workspace ./work/project-intake \
  --output ./output/Project_Codex_Handoff_v1.zip
```

Команда выполняет:

```text
validate semantic input
→ validate four Greenfield approvals or five Brownfield/Hybrid approvals
→ verify brownfield source digest
→ create handoff workspace
→ copy accepted product source when applicable
→ install project-local control plane
→ create canonical entities
→ build causal DAG
→ seed ACTIVE skills
→ create exact PROJECT_LOCK
→ compile first READY bundle
→ render human views
→ validate structure
→ generate MANIFEST.sha256
→ validate manifest
→ create deterministic ZIP
```

Исходный repository не изменяется.

## 18. Handoff archive

Обязательные root files:

```text
CODEX_START.md
AGENTS.md
HANDOFF_SUMMARY.md
PROJECT.md
ARCHITECTURE.md
TECHNOLOGY.md
ROADMAP.md
STATUS.md
VALIDATION_REPORT.json
MANIFEST.sha256
```

Обязательный control root:

```text
.harness/
```

В handoff находится embedded runtime, поэтому Codex не зависит от Browser GPT после каждого task transition.

## 19. PROJECT_LOCK

Lock содержит engine version и schema version.

Он фиксирует exact registry names:

```text
id_prefixes
project_profiles
statuses
request_routing
capabilities
contracts
```

Для каждого registry фиксируются version и SHA-256 digest.

Также фиксируются profile refs, adapter refs, skill refs, prompt spec refs и migrations applied.

## 20. Initial validation

До product changes выполняется:

```bash
python .harness/engine/project-harness.py validate-handoff --project .
```

Проверка включает immutable baseline manifest.

После начала разрешённых product changes используется:

```bash
python .harness/engine/project-harness.py validate-project --project .
```

`validate-project` проверяет contracts и runtime state без требования совпадения с исходным manifest.

## 21. Codex startup

Codex читает `CODEX_START.md` и `AGENTS.md`.

Он выполняет:

```bash
python .harness/engine/project-harness.py status --project .
python .harness/engine/project-harness.py next --project .
```

Codex не выбирает route или task самостоятельно.

Он читает prompt path из `NEXT_TASK.yaml`.

Он не редактирует `.harness/`, кроме exact Agent Task Result path.

## 22. Verification and completion

После implementation Codex запускает независимую проверку Harness:

```bash
python .harness/engine/project-harness.py verify \
  --project . \
  --allow-command-execution
```

Harness сравнивает pre-run snapshot и actual product tree.

Harness проверяет declared write scope и forbidden paths.

Commands выполняются без shell, в bounded cwd, с timeout и sanitized environment.

PASS verification не заменяет OS-level sandbox.

Codex записывает Agent Task Result.

Завершение:

```bash
python .harness/engine/project-harness.py complete \
  --project . \
  --result .harness/runtime/AGENT_RESULTS/<RUN-ID>.json
```

Declared changes должны точно совпасть с independently observed diff.

## 23. JIT progression

После accepted completion Harness создаёт immutable Run, Evidence и Task Report.

Task получает новую revision со статусом `DONE`; успешный Run фиксируется как `SUCCEEDED`.

Следующая причинно доступная task получает новую revision со статусом `READY`.

Только тогда компилируется её bundle.

Если задач больше нет, project status становится `COMPLETED`.

## 24. Blocker protocol

При material ambiguity Codex не импровизирует.

```bash
python .harness/engine/project-harness.py block \
  --project . \
  --reason "Precise material blocker" \
  --option "Safe recovery route"
```

Blocker сохраняет reason, recovery options и resume condition.

После решения:

```bash
python .harness/engine/project-harness.py resume \
  --project . \
  --resolution "Accepted resolution"
```

Создаётся новая Run attempt.

История предыдущей попытки не перезаписывается.

## 25. Brownfield guarantees

До handoff preparation:

- original repository remains byte-identical;
- `.harness/` is not installed into original repository;
- repository ZIP is extracted with path traversal protection;
- symlinks are not accepted as trusted archive entries;
- repository inventory and tree digest are recorded.

Handoff copy содержит route portfolio:

```text
CONTINUE_DEVELOPMENT
FIX_KNOWN_BUGS
IMPROVE_PROJECT
STABILIZE_BASELINE
```

## 26. Security boundary

Core runtime ограничивает logical scope.

Он не реализует kernel-level process sandbox.

External command может быть дополнительно ограничен контейнером, VM или managed sandbox.

Network access, writes outside repository и secret isolation должны обеспечиваться внешней средой исполнения.

Git push, deploy и release publication не входят в default Capability Grant.

## 27. Error statuses

Preparation возвращает structured status:

```text
WAITING_INPUT
WAITING_DECISION
INVALID
READY_FOR_CODEX
BLOCKED
FAIL
```

`WAITING_INPUT` означает, что semantic fields неполны.

`WAITING_DECISION` означает, что отсутствуют explicit approvals.

`INVALID` означает contract or registry violation.

`BLOCKED` означает material obstacle с recovery routes.

Browser GPT показывает status и exact next action без выдуманного успеха.

## 28. Idempotency

Повторный `next` при неизменном state возвращает тот же Run reservation и bundle.

Повторный `start-intake` для существующего valid workspace возвращает его readiness, если не указан controlled reset.

Run ID включает attempt number.

Retry не перезаписывает предыдущий Run.

## 29. Observability

Handoff сохраняет:

- Request;
- Request Plan;
- Session;
- Questionnaire;
- source and repository inventories;
- baselines;
- tasks and DAG;
- Prompt and Context plans;
- compiled bundles by Run;
- snapshots;
- Run records;
- Evidence;
- validation reports;
- task reports;
- events;
- current state.

Human-readable views являются generated projections canonical state.

## 30. Нормативные ограничения Browser GPT

Browser GPT не должен:

- заявлять выполнение команды без tool evidence;
- считать answers approvals;
- создавать PROJECT skill из одного ответа;
- precompile prompts для всего roadmap;
- скрывать material unknown;
- менять accepted architecture после approval;
- утверждать brownfield inventory без исходного repository;
- помещать provisional workspace внутрь target repository;
- возвращать `READY_FOR_CODEX`, если validator failed.

## 31. Критерии приёмки

Механизм считается реализованным, если одновременно выполнены следующие условия.

1. Browser GPT начинает с validation engine distribution.
2. Первый intake question относится к документации.
3. Provisional workspace создаётся до project-local bootstrap.
4. Brownfield workspace находится вне исходного repository.
5. Исходный brownfield repository не изменяется до handoff.
6. Semantic input содержит все required project fields.
7. Четыре material approvals записываются отдельно для Greenfield; Brownfield/Hybrid имеет отдельный пятый Brownfield Baseline approval.
8. Architecture Baseline имеет versioned persistent contract.
9. Session имеет lifecycle и persistent contract.
10. Skill Gap Analysis не создаёт новый skill автоматически.
11. Каждая task имеет atomic scope и verification.
12. Task DAG не содержит cycle и missing dependencies.
13. Exact registry versions and digests зафиксированы в Project Lock.
14. В initial handoff находится ровно один compiled prompt bundle.
15. Future tasks имеют plans, но не compiled bundles.
16. Handoff ZIP проходит safe extraction, CRC, structural и manifest validation.
17. Embedded runtime выполняет `status`, `next`, `verify`, `complete`, `block` и `resume`.
18. Повторный `next` идемпотентен.
19. Verification обнаруживает write outside declared scope.
20. Agent-declared diff сравнивается с independently observed diff.
21. Completed task создаёт Run, Evidence и Task Report.
22. Следующий bundle компилируется только после accepted transition.
23. Blocker сохраняет recovery routes и позволяет новую attempt.
24. Mutable project после product changes проходит `validate-project`.
25. Browser GPT возвращает архив только при `READY_FOR_CODEX`.

## 32. Definition of Done

Definition of Done включает greenfield и brownfield fixtures.

Greenfield fixture доказывает полный two-task JIT loop.

Brownfield fixture доказывает read-only discovery и exact four-route portfolio.

Conformance suite должна проверять explicit approvals, manifest tampering, unsafe ZIP, scope violation, Agent Task Result mismatch, Blocker/resume и final project completion.

Не реализованные hardening-механизмы перечисляются как ограничения и не имитируются.
