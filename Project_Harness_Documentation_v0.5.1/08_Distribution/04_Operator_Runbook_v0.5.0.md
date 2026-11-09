# Project Harness v0.5.0 — операторский runbook (PH‑F07)

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Редакция инструкций:** PH‑F07, 2026-10-25  
**Статус:** OPERATOR GUIDE для фактически реализованного CLI/API v0.5.0; не PH‑F08 release acceptance.

Этот порядок относится к *одному* Project Instance. Browser GPT — интервьюер, который анализирует источники и подготавливает согласованный `PROJECT_INPUT@3`; Engine проверяет контракты, компилирует handoff, ведёт Task/Stage governance; **внешний Codex/оператор** изменяет файлы продукта. Команды ниже исполняются из корня распакованного Engine, если не указан корень Project Instance. Заменяйте значения путей и actor/decision IDs на **реальные**, а не на литералы в угловых скобках.

## 1. Установка и проверка до опроса

Из исходного архива Engine (Python 3.11+):

```sh
python project-harness.py --version
python project-harness.py doctor
python project-harness.py --help
```

Либо в новом виртуальном окружении без доступа к сети, из того же каталога:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install --no-index --no-deps dist/project_harness_engine-0.5.0-py3-none-any.whl
project-harness --version
project-harness doctor
```

Начиная со следующего пункта команды `python project-harness.py COMMAND ...` в исходном дереве и `project-harness COMMAND ...` после установки wheel — взаимозаменяемые. В извлечённом handoff действует включённый entrypoint `python .harness/engine/project-harness.py COMMAND ...`. **Не запускайте** `python -m pytest` из чистого дерева без установленного wheel или `PYTHONPATH`: для source suite используйте `python tests/run_tests.py`, а для отдельных тестов `PYTHONPATH=src:. python -m unittest tests.test_engine -v` (из корня Engine). `pytest` опционален; эквивалентно `PYTHONPATH=src:. python -m pytest -q tests/test_engine.py` при наличии pytest.

`doctor` проверяет поставку и manifest, но **не** доказывает готовность продукта к эксплуатации. Отдельный валидатор документации запускается из корня Documentation: `python tools/validate_documentation.py .` (PyYAML нужен только этому валидатору). `--build-aggregates` перестраивает объединённые документы/индекс, но **сам по себе не создаёт ZIP**.

## 2. Источники → семантический опрос → strict input

Первый вопрос GPT — о наличии, статусе и приоритете документации (normative/partial/stale/conflicting/absent). Далее зафиксировать **первый проверяемый результат пользователя**, затем **target** `PROTOTYPE | ALPHA | BETA | MVP | RELEASE`, и лишь потом Architecture/Technology. Если документов нет, `--source` не нужен: пользовательские ответы станут согласованным источником. Не спрашивать заново факты, которые надёжно установлены загруженными документами. `UNSURE` в выборе target означает `WAITING_DECISION`, а не придуманное значение target; чувствительность данных `UNKNOWN` или материалные пробелы — `WAITING_INPUT`.

```sh
: "Greenfield без исходных документов (внешний workspace)"
python project-harness.py start-intake --workspace ./work/intake \
  --project-name "My Project" --mode greenfield

: "Вместо предыдущей команды при наличии документов:"
python project-harness.py start-intake --workspace ./work/intake \
  --project-name "My Project" --mode greenfield \
  --source ./input/requirements.md

python project-harness.py check-intake --workspace ./work/intake
```

Для Brownfield/Hybrid используйте **отдельный** workspace, не внутри repository и не внутри источников; допускается повторный `--source`:

```sh
python project-harness.py start-intake --workspace ./work/existing-intake \
  --project-name "Existing Product" --mode brownfield \
  --source ./input/specification.md --repository ./input/existing-product.zip
python project-harness.py check-intake --workspace ./work/existing-intake
```

Оператор/GPT читает `work/intake/QUESTIONS.md` и обновляет `work/intake/PROJECT_INPUT.yaml` по `templates/PROJECT_INPUT_FIELD_GUIDE.md`, `schemas/project_input.schema.json` и `examples/project_input.greenfield.json` (в Engine). Внешний JSON `--input` при `start-intake` необязателен и используется только для уже подготовленного, реально подтверждённого проекта. `--force` не применять к workspace, пересекающемуся с исходными материалами или repository.

В input обязателен canonical `schema_version: 3`, разделы `metadata`, `project`, `implementation`, `profile`, `architecture`, `technology`, `skills`, `planning`, `brownfield`, `approvals`; `implementation.target_level` — решённый canonical target, `claimed_current_level` — `NONE` для Greenfield либо отделённый от фактов user claim для Brownfield/Hybrid. `planning.work_packages` описывает только текущую `PROTOTYPE`, без детальных future-stage Tasks. Каждая Task имеет ограниченные read/write/forbidden paths и реальную verification. Изменения принятого product scope нельзя скрывать в выборе более высокого уровня.

## 3. Отдельные решения → handoff

`approvals` в `PROJECT_INPUT.yaml` — **четыре отдельные** записи `project_definition`, `architecture_baseline`, `technology_baseline`, `codex_handoff` для Greenfield; для Brownfield/Hybrid — ещё `brownfield_baseline`. Каждая имеет явные `approved: true`, `actor: ACT-*`, действительный UTC `approved_at` и допустимый `notes` по strict schema. Статус интервью/обычный ответ/положительный `check-intake` **не** является approval. Утверждает реальный человек, а GPT только фиксирует решение. Сначала проверьте baseline и ограничения; затем повторно вызовите:

```sh
python project-harness.py check-intake --workspace ./work/intake
python project-harness.py prepare --workspace ./work/intake \
  --output ./output/my-project-handoff.zip \
  --keep-directory ./output/my-project
python project-harness.py validate-handoff --project ./output/my-project-handoff.zip
python project-harness.py validate-project --project ./output/my-project
```

`prepare` требует readiness после фактического согласования. Ожидаемый успешный результат — `READY_FOR_CODEX`: валидный ZIP, immutable initial input, Stage outlines до target и **ровно один first READY JIT** текущей Stage. Handoff — не продукт и не доказательство, что Codex уже создал, протестировал или опубликовал production-код. Для дальнейшей работы используйте распакованный/сохранённый Project Instance, а не immutable ZIP. `validate-handoff` проверяет начальную поставку; после продуктовых записей — **только** `validate-project`.

## 4. Product Task: внешний Codex → verify → complete

Из исходного Engine, если `./output/my-project` уже существует:

```sh
python project-harness.py stage-status --project ./output/my-project
python project-harness.py status --project ./output/my-project
python project-harness.py next --project ./output/my-project
```

Результат `next` указывает `task_ref`, `run_ref`, `prompt_bundle_path`, `prompt_markdown_path`, `next_operator_route`. Получите текущий JIT, передайте его **внешнему** Codex, затем проверьте фактические изменения продукта и запишите `Agent Task Result` по точному шаблону `examples/agent_task_result.template.json`: `schema_version`, `task_ref`, `run_ref`, `status`, `summary`, `changes.added/modified/deleted`, `commands`, `tests`, `evidence`, `blockers`, `notes`, `stage_scope_violations`. Единственное разрешённое agent-side изменение control-plane в Run — **regular JSON** `.harness/runtime/AGENT_RESULTS/<ACTIVE-RUN-ID>.json`. Нельзя позволять Codex переписывать `.harness` или защищённые root views.

```sh
python project-harness.py verify --project ./output/my-project --allow-command-execution
python project-harness.py complete --project ./output/my-project \
  --result ./output/my-project/.harness/runtime/AGENT_RESULTS/<ACTIVE-RUN-ID>.json
python project-harness.py next --project ./output/my-project
```

`verify` **не является OS sandbox**: `--allow-command-execution` разрешает выполнение заявленных argv из Verification Profile. Разрешайте его только при доверенном окружении и понятных командах; при необходимости используйте собственную VM/container isolation. `complete` требует положительную независимую Task verification и exact result. При Task blocker доступны `block --project <root> --reason <text> [--option <text>]` и, после решения, `resume --project <root> --resolution <text> [--blocker <id>]`. Gate blocker — **другая** операция. `next` повторно использует одну текущую JIT-резервацию, не запускает Codex самостоятельно.

## 5. Gate readiness и семантика evidence

После последней mandatory Task runtime проверяет **финальную** product baseline. Если профиль Gate уже подтверждён подходящими evidence — status `VERIFYING`. Если нет — создаёт bounded `STAGE_ACCEPTANCE_PREPARATION` Work Package с Task, которую выполняют тем же циклом `next → external work → verify → complete`. **PASS общей Task verification не доказывает** архитектуру, ограничения, permitted use, external evidence, безопасность или иное независимое утверждение. Если proof не хватает, Gate остаётся незакрытым / `BLOCKED`; повторяющийся no-op PASS не создаёт ложные evidence и бесконечные Tasks.

Для Gate каждый закрывающий `EVD-*` должен быть нормализованным, immutable, связанным с фактическим source artifact и digest, точным current `tree:sha256:...` baseline и **конкретным** subject. Нормативные поля: `verification_evidence.schema_version/id/ref/kind/status/provenance/base_revision/criterion_refs/outcome_refs/profile_control_refs/source_bindings/created_at`; семантика задаётся `details.semantic_proof` (`subject_ref`, `kind`, `status`, `method`, `coverage`, `source_ref`, `checked_items` и method-specific параметры). Методы — `EXECUTED_TEST` с конкретным тестом/выполнением; `DOCUMENT_REVIEW` с существующим содержательным документом; `OPERATOR_VERIFICATION` с именованной формальной проверкой; `EXTERNAL_SOURCE` с реальным issuer/origin. Конкретные формы: `schemas/gate_evidence.schema.json` и [Stage Gate documentation](../04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md). Простая строка, универсальный PASS report или README с названием уровня — не доказательства. Semantic review является **обязанностью ответственного оператора**, а не результатом одного checksum/validator PASS.

## 6. Подготовить Stage approval → принять или восстановить Gate

В `VERIFYING` (или при поддерживаемом Gate-related `BLOCKED` для подготовки записи):

```sh
python project-harness.py stage-status --project ./output/my-project
python project-harness.py prepare-stage-approval --project ./output/my-project \
  --output ./operator-records/stage-approval.json
```

`--output` — обязательный внешний операторский файл; внутри проекта допускается только `.harness/operator/APPROVALS/`. Существующий файл требует `--force`. Результат `DRAFT_PREPARED` / envelope `stage_approval` **не** утверждает Stage: `record_state: DRAFT`, `approved: false`, `id/actor/approved_at: null`, mandatory result statuses — `UNKNOWN`.

**Строгая схема:** `schemas/stage_approval.schema.json` (`SCHEMA-STAGE-APPROVAL@1`). Сохраняйте без изменения `level`, `target_level`, `acceptance_method`, exact `stage_plan_ref/path/revision/digest`, `gate_ref/path/revision/digest`, `baseline_revision`, `gate_base_revision`, `last_acceptance_ref/path`, `last_accepted_baseline_revision`, `assessment_ref/digest` (если применимо), `required_outcomes`, `level_criteria`, `hard_constraints`, `profile_controls`, `required_work_packages`, `critical_blockers`, `evidence_candidates`, `unresolved_gaps`, `evidence_refs`, `notes`, `prepared_from_stage_plan_status`, `prepared_from_gate_status`, `preparation_fingerprint`. Заполняются `record_state: APPROVED`, canonical `DEC-*` `id`, `approved: true`, `ACT-*` `actor`, точный `approved_at` (UTC), `outcome_results`, `criteria_results`, `hard_constraint_results`, `profile_control_results` (`PASS` + exact compatible `EVD-*` refs + rationale/validator, либо подтверждённо применимый `NOT_APPLICABLE`), `permitted_use.status: CONFIRMED`, `known_limitations`, `next_stage_gaps`. Не объявляйте `PASS` без факта; кандидаты в draft — **подсказки**, не автоматическое решение.

```sh
python project-harness.py accept-stage --project ./output/my-project \
  --level PROTOTYPE --approval ./operator-records/stage-approval.json
python project-harness.py stage-status --project ./output/my-project
```

`--level` должен в точности совпадать с текущей Stage (после `PROTOTYPE` последовательно `ALPHA`, `BETA`, `MVP`, `RELEASE`). Malformed/not-approved/stale digest, неверные refs, source tampering или неподходящая semantic proof отвергаются до Stage mutation. Структурно valid formal review с mandatory `UNKNOWN/PARTIAL/FAIL` **фиксирует Gate-related `BLOCKED`**, но не принимает Stage. После получения настоящего proof:

```sh
python project-harness.py resume-stage-gate --project ./output/my-project
python project-harness.py stage-status --project ./output/my-project
```

`resume-stage-gate` ревалидирует Gate, сохраняя blocked history; возможен новый bounded preparation Task либо `VERIFYING`. После смены Plan/Gate revision или baseline пересоздайте Stage approval draft, старый не переиспользуйте. После успешного промежуточного acceptance статус `STAGE_PLANNING_REQUIRED`; на принятом target — `TARGET_LEVEL_REACHED`. Acceptance Reports и completed Runs остаются immutable.

## 7. Следующая active Stage — отдельный reviewed planning route

Только когда `next`/`stage-status` сообщает `PLAN_ACTIVE_STAGE` / `STAGE_PLANNING_REQUIRED`:

```sh
python project-harness.py prepare-active-stage-plan --project ./output/my-project \
  --output ./operator-records/next-stage-plan.json
: "Оператор проверяет точный binding, текущие Tasks и scope."
python project-harness.py plan-active-stage --project ./output/my-project \
  --plan ./operator-records/next-stage-plan.json
python project-harness.py next --project ./output/my-project
```

Read-only `prepare-active-stage-plan` выдаёт `DRAFT_PREPARED`, а `plan-active-stage` — `STAGE_PLANNED` и первый `READY_FOR_CODEX` JIT ближайшего уровня. Один JSON envelope `active_stage_plan_review` (`SCHEMA-ACTIVE-STAGE-PLAN-REVIEW@1`, `schemas/active_stage_plan_review.schema.json`) содержит **все** обязательные разделы: `schema_version/schema_ref/record_kind/id/revision/route`, `binding`, `planning_basis`, `review`, `work_packages`, `candidate_work_digest`, `future_stage_work: FORBIDDEN`. `binding` включает `stage_state_revision/digest`, `highest_accepted_level`, `active_stage`, `target_level`, `stage_plan_ref/digest`, `gate_ref/digest`, `last_acceptance_ref/digest`, `accepted_baseline_revision`, `product_baseline_revision`, `accepted_scope_ref/digest`, `accepted_input_digest`, `maintenance_report_ref/digest` (maintenance-поля `maintenance_report_ref/digest` — `null` при отсутствии завершённой maintenance). `planning_basis` включает outcomes/criteria/controls/constraints, accepted scope/requirements, predecessor gaps/limitations/permitted use/product files; менять его нельзя.

**Неизменённый** автоматически сформированный план имеет `review: {material_change: false, scope_confirmed: true, decision: null}` — вызов `plan-active-stage` является явным принятием работ **в уже согласованном scope**, отдельная фиктивная DEC не нужна. При корректировке `work_packages` внутри accepted scope обязательна `review.decision`: exact `id: DEC-<draft.id без префикса RQP->-REVIEW`, `kind: ACTIVE_STAGE_PLAN_REVIEW`, `approved: true`, `actor: ACT-*`, ISO UTC `approved_at`, `rationale`; `review.material_change` всё равно `false`. Material scope divergence, future-stage work, protected paths или stale baseline — **rejection**, требуется отдельный существующий governance route, не silent plan patch. `--force` есть **только** у read-only `prepare-active-stage-plan`, а не у application.

Фактические записи после commit: `.harness/stages/PLANS/`, `GATES/`, `PLANNING/RECORDS/`, `TRANSACTIONS/`, `.harness/work-packages/`, `.harness/tasks/`, `.harness/verification/PROFILES/`, `.harness/context/PLANS/`, `.harness/prompts/`, `.harness/state/CURRENT_STATE.yaml` и `.harness/state/NEXT_TASK.yaml`. Повтор уже committed **идентичного** request идемпотентен. При interrupted transaction сначала проверьте `validate-project`, учитывая автоматическую journal recovery; если транзакция rolled back, выпустите **новый** draft, а не насильно переигрывайте прежний transaction id.

## 8. Target reached → level-up **или** same-level maintenance

При `TARGET_LEVEL_REACHED` повышение уровня не происходит автоматически. Для принятого MVP и нового RELEASE подготовьте **отдельный** formal JSON-файл:

```json
{
  "level_up_approval": {
    "id": "DEC-PROJECT-LEVELUP-001",
    "approved": true,
    "actor": "ACT-USER-001",
    "approved_at": "2026-10-25T12:00:00Z",
    "target_level": "RELEASE",
    "rationale": "Explicitly approve development toward RELEASE within accepted scope."
  }
}
```

Это **пример формы**, а не разрешение использовать чужой `DEC-*` или фиксированную дату. В данной поставке у `level-up` нет отдельного публичного `level_up_approval.schema.json`: Engine проверяет formal record (`approved`, `id`, `actor`, `approved_at`, exact `target_level`) и runtime preconditions через `level-up`. Не ссылайтесь на несуществующую схему. Путь `--approval` — в отдельном operator records directory:

```sh
python project-harness.py level-up --project ./output/my-project \
  --target RELEASE --approval ./operator-records/level-up.json
: "После успешного level-up повторить шаг 7 для RELEASE."
```

Ожидается `STAGE_PLANNING_REQUIRED`, затем первый Release JIT. Target может быть любым canonical уровнем **выше** принятого, однако активируется **только ближайшая следующая Stage**, без перескока фактических Stage/Gate. Downgrade/unaccepted previous Stage и конкурирующий level-up при незавершённом цикле отвергаются. `.harness/stages/STAGE_STATE.yaml` хранит current-cycle target; `PROJECT.yaml`/`CURRENT_STATE.yaml` — projections; `.harness/state/PROJECT_INPUT_ACCEPTED.yaml` содержит immutable **первоначальный** target. `level-up` невозможен при открытом maintenance и невозможен выше RELEASE.

Для исправления **внутри уже принятого уровня** используйте `start-maintenance`, без Stage acceptance и без изменения target:

```sh
python project-harness.py start-maintenance --project ./output/my-project \
  --plan ./operator-records/maintenance-plan.json
python project-harness.py next --project ./output/my-project
: "Внешний Codex и exact Agent Result, как в шаге 4."
python project-harness.py verify --project ./output/my-project --allow-command-execution
python project-harness.py complete --project ./output/my-project \
  --result ./output/my-project/.harness/runtime/AGENT_RESULTS/<ACTIVE-RUN-ID>.json
```

В v0.5.0 **нет CLI-команды для генерации maintenance draft**. Оператор подготавливает строгий `maintenance_plan` по `schemas/maintenance_plan.schema.json` (`SCHEMA-MAINTENANCE-PLAN@1`): `schema_version/schema_ref/record_kind/id/revision/status/route`, exact `highest_accepted_level`, `implementation_stage`, `target_level`, `last_acceptance_ref`, `accepted_scope_ref`, `objective/rationale`, approved `decision` (`kind: MAINTAIN_CURRENT_STAGE`, `DEC-*`, `ACT-*`, дата), `scope_boundary`, `work_package` c atomic current-level `tasks`, `verification_constraints`, `rollback_constraints`, `cancel_constraints`. `future_stage_work: FORBIDDEN` и реальная verification обязательны. Внутренние формы `scope/route/verification` — по схеме, а не произвольный JSON. Точные `highest_accepted_level`, `target_level`, `last_acceptance_ref` берите из `stage-status` / `.harness/stages/STAGE_STATE.yaml`; `accepted_scope_ref` — поле `scope_ref` принятого Project Definition, путь к которому указан в `.harness/state/CURRENT_STATE.yaml` (`entity_paths.project_definition`). Не копируйте значения из другого проекта. Реализованные storage paths — `.harness/maintenance/PLANS/`, `.harness/maintenance/REPORTS/`, `INDEX.yaml`, `CURRENT.yaml`.

Досрочная отмена возможна только **до продуктовых изменений** по отдельному строгому `maintenance_cancel_approval` (`schemas/maintenance_cancel_approval.schema.json`): `schema_version/schema_ref/record_kind/id/revision`, `kind: CANCEL_MAINTENANCE`, `approved`, `actor`, `approved_at`, `maintenance_plan_ref`, `work_package_ref`, `highest_accepted_level`, `target_level`, `last_acceptance_ref`, `rationale`, `cancel_mode: PRE_PRODUCT_CHANGE_ONLY`. Точные `maintenance_plan_ref` и `work_package_ref` возьмите из `.harness/maintenance/CURRENT.yaml`; отмена требует нового явно одобренного `DEC-*`, а не повторного использования предыдущего. Вызов:

```sh
python project-harness.py cancel-maintenance --project ./output/my-project \
  --approval ./operator-records/maintenance-cancel.json
```

Maintenance complete/cancel оставляет accepted maturity и immutable history на месте. Это не rollback продуктовых изменений; при изменённом product tree обычная отмена блокируется. Лишь после корректного закрытия maintenance можно снова запрашивать `level-up`.

## 9. Brownfield assessment и baseline acceptance

Для existing project сначала делайте inventory и принимайте `PROJECT_INPUT@3` с отдельным Brownfield Baseline approval (см. шаги 2–3). Assessment **не исполняет** repository commands и **не** является автоматическим Stage acceptance:

```sh
python project-harness.py assess-maturity --workspace ./work/existing-intake
: "Для фактических supplied evidence, когда это требуется:"
python project-harness.py assess-maturity --workspace ./output/my-project \
  --evidence ./operator-records/supplied-evidence.json
```

Формат второго файла — JSON объект `{"evidence": [...]}`; для prepared Project Instance допустим normalized body `verification_evidence` из `schemas/gate_evidence.schema.json` (без внешнего envelope, со всей semantic proof/source bindings). Source documents должны существовать, ссылки и SHA-256 — совпадать; для операторских источников допустим `.harness/operator/SOURCES/`. Engine импортирует прошедшие проверки normalized evidence в canonical storage, **не редактируйте** `.harness/evidence/` вручную. Разделяйте `claimed_current_level`, `observed_candidate_level`, `highest_satisfied_candidate` и `highest_accepted_level`.

`SATISFIED_BY_BASELINE` требует строгий `stage_approval` с **точным** `assessment_ref: <assessment-id>@<revision>`, `assessment_digest: sha256:...`, current product `baseline_revision`, `acceptance_method: SATISFIED_BY_BASELINE`, matching claim/target/history, все обязательные proof results и отдельный formal decision. Используйте только exact canonical ref из текущего assessment; вызов `accept-stage --project <root> --level <level> --approval <record>` принимает только реально удовлетворённые последовательные стадии, с отдельным immutable report для каждой. Stale, wrong-kind, fake README labels или missing runtime evidence отвергаются. Поля и критерии: [Stage Gate documentation](../04_Execution/07_Stage_Gates_Maturity_and_Level_Up.md), [PH‑F06 integration notes](../PH_F06_LIFECYCLE_NOTES.md).

## 10. Migration, failure и выходные коды

Прямой путь **только** с валидного extracted v0.4.1/schema 5 Project Instance, без незавершённого Run:

```sh
python project-harness.py migrate-project --project ./legacy-v0.4.1 \
  --input ./operator-records/approved-project-input-v3.json
python project-harness.py validate-project --project ./legacy-v0.4.1
```

`--input` — заранее формально одобренный `PROJECT_INPUT@3`, совместимый с legacy semantic baseline; не пытайтесь создавать target автоматически из README/version. Migration сохраняет completed Task/Run/Evidence/Decision byte-for-byte, а старое `COMPLETED` не повышает accepted maturity. Проверьте результат и возможный отдельный Brownfield assessment route. Исторические правила остаются в [Migration v0.4.1 → v0.5.0](../MIGRATION_FROM_v0.4.1.md), а не переписываются как будто Stage Gate существовал в v0.4.1.

В CLI JSON `status` и **код процесса различаются**: `WAITING_INPUT`, `WAITING_DECISION`, `BLOCKED` могут давать exit code **3** (не неожиданный crash); `FAIL/FAILED/INVALID` — **2**; ошибочные флаги/схемы могут давать иной ненулевой код. Всегда читайте JSON `errors`/`next_operator_route` и stderr. Для любого действующего состояния проверьте `stage-status`, `next` и `validate-project`, а не редактируйте canonical файлы. Ordinary Task recovery: `resume`; persisted Stage Gate recovery: `resume-stage-gate`; safety tamper/`STAGE_TRANSACTION_CORRUPT` — **никакого unsafe in-place resume**, только trusted restore/recovery с журналом и последующая проверка. Invalidated stale draft готовится заново.

**Граница v0.5.0:** ни valid handoff, ни `READY_FOR_CODEX`, ни `PASS` Task verification не гарантируют готовый production-продукт, architecture/security/compliance acceptance, sandbox isolation или независимую истинность source claims. Автоматического Codex Executor, OS/rootless sandbox, Git push/PR, deployment adapter, project skill authoring и parallel worktrees в этой версии нет. PH‑F08 — отдельная финальная интеграционная приёмка.
