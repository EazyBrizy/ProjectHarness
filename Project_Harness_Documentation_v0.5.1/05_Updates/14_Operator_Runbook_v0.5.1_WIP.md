# PH-051-11 — операторский runbook Project Harness v0.5.1-WIP

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Обновлено:** 2026-10-29 (PH-051-11)  

**Статус:** `WIP / NOT RELEASED`, 2026-10-29. **Приоритет контрактов:** normative `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` §§16, 20–24 → действующие v0.5.0 governance invariants → фактический CLI/схемы → эта инструкция. **Это инструкция для реально доступных команд, а не подтверждение OS security.** Автоматический путь на предоставленном стенде не аттестован (`NOT TESTED / NO GO`).

## 1. Проверить поставку, не путать два doctor

Распакуйте Engine и Documentation в разные каталоги. Для Python 3.11+ выполните в **корне Engine** (без сети):

```bash
python project-harness.py --version
python project-harness.py doctor
python project-harness.py executor-doctor --help
python project-harness.py execute-current --help
```

Или установите **реально поставленный wheel 0.5.1** в отдельное окружение:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --no-index --no-deps dist/project_harness_engine-0.5.1-py3-none-any.whl
project-harness --version
project-harness doctor
```

`doctor` проверяет дистрибутив, ресурсы и manifest; не запускает Podman probes и не даёт права на automatic mode. `executor-doctor --project /absolute/project/root` проверяет **конкретный** проект, его immutable `PROJECT_LOCK`, pinned ACTIVE `ADP`/`SBX` и реальные rootless Podman self-tests. Для default manual project ожидается `BLOCKED / EXECUTOR_UNAVAILABLE`, CLI exit `3`: **это защитное срабатывание, а не поломка ручного режима**. Нельзя считать `doctor PASS` достаточным для `execute-current`.

Извлечённый Project Instance также содержит bundled entrypoint `python .harness/engine/project-harness.py`; он используется с теми же именами публичных операций и требует передать `--project` для project-local commands.

## 2. Внешний GPT → нормативный input → handoff

Browser GPT выступает семантическим интервьюером, а не rootless Executor. Он сперва уточняет наличие/нормативность документации, затем первый проверяемый outcome и **target** (`PROTOTYPE → ALPHA → BETA → MVP → RELEASE`); после чтения фактов задаёт только материальные дополнительные вопросы, не принимает согласие в чате за формальный approval. `UNSURE` по target — `WAITING_DECISION`; `UNKNOWN` по sensitivity — `WAITING_INPUT`; Brownfield claimed maturity не равна accepted.

```bash
project-harness start-intake --workspace /work/intake --project-name "Example Project" --mode greenfield
  # Для исходников дополнительно: --source /abs/path/to/material; для existing --mode brownfield --repository /abs/repo
project-harness check-intake --workspace /work/intake
  # Внешний GPT/оператор заполняет строгий /work/intake/PROJECT_INPUT.yaml и формальные approvals.
project-harness check-intake --workspace /work/intake
project-harness prepare --workspace /work/intake --output /work/output/example-handoff.zip
project-harness validate-handoff --project /work/output/example-handoff.zip
```

Начальный input — `PROJECT_INPUT@4` (schema_version `4`); runtime — schema `7`, registries `id@3`, `statuses@6`, `contracts@6`. Greenfield требует **четыре** разных approvals (Project Definition, Architecture, Technology, Codex Handoff), Brownfield/Hybrid — **пять**, включая Brownfield Baseline. `prepare` выдаёт `READY_FOR_CODEX` и **один first READY JIT**, не работающий production-код; `validate-handoff` проверяет **исходный ZIP**, а не изменённый позже product tree. Отдельные Stage outlines возможны до target, но детальные Tasks/Prompt Plans/JIT только для active Stage.

**Поддерживаемый default input:**

```yaml
execution:
  mode: MANUAL_HANDOFF
  adapter_profile_ref: null
  sandbox_profile_ref: null
  network_mode: NONE
  completion_policy: EXPLICIT_AFTER_VERIFICATION
```

**Обнаруженный при PH-051-11 pre-existing blocker:** хотя контракт определяет `LOCAL_AUTOMATIC`, публичный `prepare` ещё содержит PH-051-01 fail-closed ветку и отклоняет такой **новый** input (`AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`). Существующие integration tests автоматического пути создают **только test-fixture** с синтетической подписью lock; это не способ операторской активации. В данной стадии нет публичного governed маршрута перевода уже принятого manual `PROJECT_LOCK` в automatic, и **его нельзя заменять** правкой `.harness` или вызовом private Python. Такой блокер остаётся в выпускной матрице для отдельного решения после PH-051-11. Это не отменяет реально существующих, но fail-closed project-scoped `executor-doctor`/`execute-current`.

## 3. Manual mode — работающий default без Podman

После извлечения handoff ZIP в `/absolute/project/root`:

```bash
project-harness validate-project --project /absolute/project/root
project-harness status --project /absolute/project/root
project-harness next --project /absolute/project/root
  # Внешний Codex выполняет ТОЛЬКО текущий JIT в установленном write scope;
  # точный Agent Task Result записывается по разрешённому месту текущего Run.
project-harness verify --project /absolute/project/root
project-harness complete --project /absolute/project/root --result /absolute/project/root/.harness/runtime/AGENT_RESULTS/<current-run-id>.json
project-harness next --project /absolute/project/root
```

`<current-run-id>` **не пример реального ID**: берите точный путь из `next`/`status`, не угадывайте. `verify --allow-command-execution` допускается только при **осознанном** разрешении оператора в manual mode; это не OS sandbox. Заявленные agent PASS/exit0 не заменяют independent verification. При `BLOCKED` смотрите `status` и `next_operator_route`, затем `resume --project <root> --resolution <truthful explanation>` только после устранения причины. Не стирайте journals, не переписывайте завершённый Run.

## 4. Automatic mode — только для уже валидно opt-in и реально проверенного rootless Podman

**Не используйте этот маршрут для мигрированного/default manual проекта.** Предпосылки: exact accepted project execution policy `LOCAL_AUTOMATIC`, реально provisioned ACTIVE profiles по project-local revisioned paths `.harness/config/ADAPTERS/<ADP-ID>@1.yaml` и `.harness/config/SANDBOXES/<SBX-ID>@1.yaml`, exact digest bindings в `PROJECT_LOCK`, текущая `READY` Task/JIT и подтверждённая независимая isolation attestation.

Поля профилей и синтаксис strict examples: [ADP](../10_Contracts/examples/adapter_codex_cli_local.v0.5.1.example.yaml), [SBX](../10_Contracts/examples/sandbox_rootless_podman.v0.5.1.example.yaml), [policy](../10_Contracts/examples/execution_policy_manual.v0.5.1.example.yaml). Примеры не являются approved activated config: демонстрационный image digest синтаксически корректен, но **не указывает на подтверждённый image**. Сначала укажите локально существующий pinned digest и проверьте реальный Codex CLI `argv_template` в image; приведённые флаги CLI — **контрактный пример**, не подтверждение версии Codex. Секреты допускаются **только** в `secret_environment_refs: ["ENV:NAME"]`, когда это конкретно утверждено в ADP и переменная действительно предоставлена оператором; raw values никогда не записываются в ZIP, input или logs.

```bash
project-harness executor-doctor --project /absolute/project/root --network NONE
project-harness next --project /absolute/project/root
project-harness execute-current --project /absolute/project/root --network NONE
project-harness status --project /absolute/project/root
project-harness next --project /absolute/project/root
```

После real doctor PASS агент запускается только в disposable `/workspace/product` внутри rootless Podman (не canonical repo). `/workspace/control` read-only, `/output/agent-result.json` exact bounded. Отдельный **sandboxed verifier** проверяет реальные changes/Task scope; только independent PASS разрешает recoverable atomic apply и immutable Apply Evidence. Результат `AUTO_AFTER_PASS` завершает **только текущую Task**; с `EXPLICIT_AFTER_VERIFICATION` `SUCCEEDED / WAITING_EXPLICIT_COMPLETION` требует `complete --project ... --result <exact-path-from-status>`. Никакая Task completion не утверждает Stage Gate или повышенный level.

`executor-doctor` и `execute-current` принимают `--adapter-profile <id-or-path>` (только **точную уже pinned** запись), `--network NONE|EXPLICIT_APPROVED_EGRESS`, `--approval <path>`, `--keep-execution-root`. Но фактическая реализация **NONE-only**: `--network EXPLICIT_APPROVED_EGRESS` и `--approval` для egress/секретных расширений всегда завершаются `BLOCKED / NETWORK_NOT_APPROVED`, независимо от наличия файла. Существующей strict schema для принимаемого per-Run egress approval **нет**, поэтому [negative-approval example](../10_Contracts/examples/egress_request_REJECTED.v0.5.1.example.yaml) намеренно **не является операционным approval**. Egress mode по нормативной спецификации требует `NETWORK_WRITE`, `MODEL_EXTERNAL_EGRESS`, exact per-Run decision и согласованную sensitivity policy; с нынешней реализацией даже это не включает сеть. `EXPLICIT_APPROVED_EGRESS` **не реализует per-destination allowlist**. `--keep-execution-root` заблокирован без отдельной governed debug policy (сейчас её нет), не используйте как обход очистки. Нет host, `--network=host`, Git/PR/deployment или второго backend fallback.

`BLOCKED`, `TIMED_OUT`, `FAILED_RETRYABLE` — CLI exit `3`; schema/validation `INVALID/FAIL` — exit `2`; valid nonblocking — `0`. На отказ `doctor` **agent не стартует**; нельзя автоматически переключаться на manual выполнение того же подписанного automatic Run. Для явной смены operator mode требуется отдельный governance route; до него — устранение недостатка/`resume` в разрешённом контексте, без переписывания старой истории.

## 5. Stage Gate, target, maturity, maintenance

После последней mandatory Task runtime формирует Gate readiness и при нехватке подходящего semantic evidence — `STAGE_ACCEPTANCE_PREPARATION` WP. Generic PASS report (особенно от одного no-op test) не доказывает `ARCHITECTURE_RECORD`, permitted use, external evidence, security/compliance. Evidence должен соответствовать **конкретному subject, kind, source, provenance, current final product baseline**. Оператор по-настоящему оценивает ограничения и результат; formal Stage approval не создаётся автоматически.

```bash
project-harness stage-status --project /absolute/project/root
project-harness prepare-stage-approval --project /absolute/project/root --output /work/operator-records/stage-approval.json
  # Оператор проверяет источники и утверждает exact draft согласно stage_approval.schema.json.
project-harness accept-stage --project /absolute/project/root --level PROTOTYPE --approval /work/operator-records/stage-approval.json
  # Если нужен переход на ближайшую последующую Stage:
project-harness prepare-active-stage-plan --project /absolute/project/root --output /work/operator-records/next-stage.json
project-harness plan-active-stage --project /absolute/project/root --plan /work/operator-records/next-stage.json
project-harness next --project /absolute/project/root
```

Если Gate `BLOCKED`: используйте `resume-stage-gate --project <root>` после появления надлежащих proof artifacts, подготовьте **новый** exact approval draft, старый stale record нельзя переиспользовать. На `TARGET_LEVEL_REACHED` повышение — только отдельный formal `level-up --project <root> --target <next> --approval <record>`; same-level maintenance начинается `start-maintenance --project <root> --plan <record>` и работает через обычный Task cycle без повышения maturity. Brownfield `assess-maturity` read-only; baseline acceptance — только с exact assessment ref, evidence и formal approval. Старые immutable Stage Acceptance Reports/Run не переписывайте.

## 6. Миграция, crash recovery, cleanup и ограничения эксплуатации

```bash
project-harness migrate-project --project /absolute/legacy-v0.5.0-root
project-harness validate-project --project /absolute/legacy-v0.5.0-root
project-harness next --project /absolute/legacy-v0.5.0-root
```

Для v0.5.0/schema6 совместимая миграция сохраняет accepted `PROJECT_INPUT`, Stage Plans, reports, completed manual Runs и product bytes; обновляет runtime/lock до v0.5.1/schema7 и устанавливает **MANUAL_HANDOFF**, `NONE`, `EXPLICIT_AFTER_VERIFICATION`. Повтор даёт `NO_ACTION`. Старый v0.4.1→v0.5.0 маршрут не заменяется новой миграцией. После host crash `execute-current` проверяет orphan containers по project/run-bound labels, восстанавливает Apply journal, помещает старые execution roots в private quarantine; ambiguous states блокируют Run до восстановления. Quarantine может содержать секретную transient data — оператор защищает storage и удаляет по проверенной recovery procedure; ее нельзя вкладывать в handoff или archive. `--keep-execution-root` не является разрешённым debug shortcut.

## 7. Воспроизводимые проверки и точная граница GO

См. [Podman security validation](15_Podman_Security_Validation_v0.5.1_WIP.md) и соответствующий Engine `PH_051_11_SECURITY_MATRIX.md` с фактическими командами, platform, UID, Podman version, image digest, FAIL/NOT TESTED для каждой строки. `PYTHONPATH=src:. python tests/run_tests.py` проверяет реализованное поведение, а не kernel OS boundary. Реальный rootless Podman self-test и fake CLI внутри pinned image обязательны отдельно. Пока они не прошли, `v0.5.1 WIP / NO GO` независимо от количества green unit tests или установленного wheel. PH-051-12 — **отдельная** финальная release acceptance, не автоматически вытекает из PH-051-11.
