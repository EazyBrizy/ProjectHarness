# PH-051-02 — отчёт о реализации, тестах и границах v0.5.1 WIP

**Дата:** 2026-10-25  
**Этап:** `PH-051-02` — Executor Protocol и deterministic fake CLI fixtures  
**Результат этапа:** **PASS для локальной области PH-051-02; автоматический режим v0.5.1 остаётся WIP/NOT RELEASED**.

## Вход и проверка нормативной базы

- Полученный `Project_Harness_Engine_v0.5.1.zip`: SHA-256 `017f473f17b8bcf15a8ab99bf2c86598b54e105be9bf364fc3e6b73d7d8e9ec7`.
- Полученный `Project_Harness_Documentation_v0.5.1.zip`: SHA-256 `9f843173695b9aa69ce572d09ffeba96ff0c0cb701705a451e4d0c00350965c3`.
- `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`: SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e` (**совпадает** с нормативным значением в плане).
- Входные ZIP проверены на CRC, path traversal, Engine и Documentation SHA-256 manifests: **PASS**.
- Сохранён результат PH-051-01: `SCHEMA_VERSION=7`, `PROJECT_INPUT@4`, `REG-ID-PREFIXES@3`, `REG-LIFECYCLE-STATUSES@6`, `REG-CONTRACT-CATALOG@6` (письменно согласованная коллизия `5 → 6`).

## Реализованное (строго PH-051-02)

1. Добавлен единственный Python protocol `ExecutorAdapter` (`doctor`, `prepare_invocation`, `execute`, `normalize_result`) и один adapter `CodexCliLocalAdapter` типа `CODEX_CLI_LOCAL`, без новых публичных CLI-команд.
2. Строгая политика `argv_template`: именно list, точное сопоставление executable, шесть известных placeholders как **целые отдельные элементы**, sandbox-only paths, canonical Task/Run ids, отказ при shell/redirect/pipeline/command substitution, credential literals, raw user text, raw secret values, недопустимых environment names/refs и host paths. Флаги Codex CLI не зашиты в Kernel.
3. `execute` повторно сравнивает argv с подготовленным exact Run context и передаёт его **только инъецируемому sandbox runner** с подтверждённым doctor status. В поставке **нет** production sandbox runner, поэтому default `execute` возвращает `BLOCKED / SANDBOX_UNAVAILABLE`, статический `doctor()` тоже `BLOCKED`. В production executor нет вызовов host `subprocess`, `Popen`, `os.system`, нет `shell=True`/unsandboxed fallback. Тестовый recording stub — не изоляция и не второй adapter.
4. Базовая классификация process reasons и начальная syntactic result probe: отсутствие/некорректность файла, nonzero, timeout, flood, sandbox failure. Даже `exit_code=0` и `status=COMPLETED` внутри agent JSON дают только `PENDING_RESULT_VALIDATION`, никогда `PASS`/`SUCCEEDED`; полная проверка outcome отложена до PH-051-06.
5. Один fake Codex CLI test double и JSON index на **13 сценариев**, включая success/nonzero/timeout/missing/invalid JSON/flood/child/control write/wrong paths/secret echo/secret product/secret result/baseline drift. Fake CLI исполняется в PH-051-02 **только как in-process unit helper** на временных test dirs. Подпроцессные sandbox scenarios зарезервированы для PH-051-03 и последующих шагов.
6. Точечное v0.5.1-WIP дополнение документации `05_Updates/06_Executor_Protocol_v0.5.1_WIP.md`, актуальные banner/changelog/version metadata и синхронные generated aggregates. Предыдущие acceptance reports, registry/schema contracts и implementation history не переписаны.

**Allowed production changes:** только `src/project_harness/executors/{__init__,base,codex_cli_local,result}.py`; все остальные изменения — unit/tests/fixtures, WIP docs, generated wheel/build mirrors и release packaging metadata. См. `PH_051_02_CHANGED_FILES.md`.

## Фактические тесты

Все указанные команды запускались из корня Engine; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src:.:tests`.

| Группа | Test modules | Количество | Итог |
|---|---|---:|---|
| 01 | `test_ph_f08_release_acceptance`, `test_maintenance_lifecycle` | 9 | PASS |
| 02 | `test_engine`, `test_gate_evidence_contract` | 24 | PASS |
| 03 | `test_ph_f06_maturity_lifecycle`, `test_canonical_target`, `test_ph_051_01_contract_baseline` | 28 | PASS |
| 04 | `test_ph_f05_intake_acceptance`, `test_assessment_freshness`, `test_exact_assessment_ref`, `test_contract_hardening` | 50 | PASS |
| 05 | `test_ph_f03_active_stage_planning`, `test_implementation_levels`, `test_ph_f01_planner_regression` | 22 | PASS (повтор после mode fix) |
| 06 | `test_ph_f04_runtime_reachability`, `test_stage_transaction_recovery`, `test_stage_approval_preparation` | 32 | PASS (повтор после mode fix) |
| 07 | `test_ph_f02_semantic_proof_contract`, `test_stage_gate_preparation_block_recovery`, `test_ph_f01_gate_semantics_regression` | 13 | PASS |
| 08 | `test_ph_051_02_executor_protocol` | 24 | PASS |
| **ИТОГО** | **все 20 исходных test modules + 1 новый** | **202** | **202/202 PASS** |

Воспроизводимые команды для модулей:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests python -m unittest -v tests.test_ph_051_02_executor_protocol
# И отдельно для каждой строки 01–07:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests python -m unittest -v tests.<module1> tests.<module2> ...
```

Логи `PH_051_02_LOGS/REGRESSION_GROUP_01.log` … `_08.log`, summary
`PH_051_02_LOGS/FINAL_SUITE_SUMMARY.json`, целевой test log `TARGETED_FINAL.log`.

**Честное замечание о первом regression-run:** простой `zipfile.extractall()` убрал UNIX executable bit у `bin/project-harness`, исходный ZIP содержит `0755`. Первая попытка групп 05/06 поэтому дала `PermissionError` **из-за тестовой распаковки**, не из-за Executor Protocol. Режим из оригинального ZIP восстановлен в рабочем дереве (`chmod 755`), повтор 05/06 дал **22/22 и 32/32 PASS**. Оба исходных диагностических лога сохранены (`INITIAL_GROUP_05_EXTRACTION_MODE_ERROR.log`, `_06_...`). Выходной Engine ZIP сохраняет именно исходный `0755`.

### Wheel и документы

- `python -m pip wheel . --no-deps --no-build-isolation --no-cache-dir --wheel-dir <wheel-dir>` — **PASS** на финальном source.
- Установка wheel в чистое `venv`, `project-harness --version` — `0.5.1`, `project-harness doctor` — **PASS**.
- Из установленного wheel импортирован `CodexCliLocalAdapter`, все 4 source modules присутствуют; `prepare_invocation` формирует expected argv, `doctor` и `execute` без runner гарантированно возвращают **`BLOCKED / SANDBOX_UNAVAILABLE`**. Логи в `PH_051_02_LOGS/WHEEL_*.log`.
- Документационный validator `python tools/validate_documentation.py . --zip <documentation-zip> --json <report>` — **36/36 PASS**, без errors и warnings, CRC ZIP проверен; лог `PH_051_02_LOGS/DOC_VALIDATION.json`.
- Строгие schemas/registries не изменены, wheel содержит package-resource mirrors предыдущего PH-051-01.

## Матрица сохранённых инвариантов

| Инвариант | Контроль / состояние |
|---|---|
| Manual `intake→prepare→handoff→next→verify→complete` | Старые regression groups 01–04 и 07 PASS; новых automatic public routes нет |
| Sequential Stage/Gate/target/level-up, semantic Gate evidence | PH-F01–F08 regression groups 01,02,03,05,06,07 PASS; production-модули не тронуты |
| Brownfield exact assessment/read-only и formal baseline | groups 03–04 PASS |
| Maintenance same-level, immutable history и Stage transactions/recovery | groups 01,03,06 PASS |
| PH-051-01 execution policy, input v4, registry versions, exact refs | group 03 PASS; schema/registry source diff отсутствует |
| No host CLI fallback, shell or optimistic Run PASS | new group 08 PASS + installed wheel smoke |
| Sandbox technical isolation / secrets result validation / independent verification / safe apply | **NOT IMPLEMENTED / NOT TESTED; future PH-051-03/06/07/08** |

## Выходной статус

**PH-051-02 slice: PASS.** Обновлены два согласованных `v0.5.1` архива с SHA-256 манифестами и сохранением source package permissions. **v0.5.1 release: NO-GO (WIP)**, потому что настоящий Rootless Podman runner, независимая verification, diff/apply, public automatic route и security acceptance не входят в этот этап. Fake stub или успешный `doctor` distribution нельзя выдавать за проверку контейнерной изоляции.

Следующий самостоятельный пакет по плану: **PH-051-03 — Rootless Podman Sandbox Runner + реальный doctor/self-tests**. HTTP provider, Docker, unsandboxed execution, Git/PR/deploy и другие версии остаются вне scope.
