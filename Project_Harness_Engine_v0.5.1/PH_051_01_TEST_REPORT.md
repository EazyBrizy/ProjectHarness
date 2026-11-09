# PH-051-01 — Отчёт о реализации, тестировании и сборке

**Дата:** 2026-10-25
**Статус:** `PH-051-01 CONTRACT SLICE PASS`; **v0.5.1 WIP / NOT RELEASED**.
**Область:** строго `PH-051-01` (контракты, реестры, схемы, `PROJECT_INPUT@4`, policy/lock metadata, совместимость, tests/docs).

## 1. Проверенная исходная база

- `Project_Harness_Engine_v0.5.0.zip`: SHA-256 `257aee9fb190a8cd09a6d5bbde6eca9a77fe58b25b09ad9f956d1ef260e5e6af` (PH-F08).
- `Project_Harness_Documentation_v0.5.0.zip`: SHA-256 `4f02f68f7d0a50ac17f0bb118a2c45e3bb2e240d01dfc74f1b6b57eab66cb9aa`.
- `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`: content SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`.
- Задача: `Project_Harness_v0.5.1_Implementation_Plan_RU.md`, PH-051-01 и §1.1.

## 2. Изменённые контракты / выбор версии

- `REG-ID-PREFIXES`: `2 → 3`; отдельный ID `SBX`, без подмены `ADP`.
- `REG-LIFECYCLE-STATUSES`: `5 → 6`; `sandbox_profile`.
- `REG-CONTRACT-CATALOG`: **`5 → 6`**. Нормативная §19.1 ошибочно предполагает базу `4 → 5`, тогда как **реальный принятый v0.5.0 уже имеет `@5`**. Решение: не перезаписывать и не понижать существующую revision; выпустить следующую новую `@6` и pin точных версий/digests в новом lock. Расхождение с буквальным текстом спецификации сохранено и явно раскрыто, источник нормативной спецификации не менялся. См. `IMPLEMENTATION_DECISIONS_v0.5.1_WIP.md`.
- `SCHEMA-PROJECT-PREPARATION-INPUT@3 → @4`, canonical `SCHEMA_VERSION 6 → 7`; `VERSION=0.5.1-WIP`, package engine `0.5.1`.
- Новые strict schemas `executor_profile`, `sandbox_profile`, `execution_result`, `apply_evidence`; `additionalProperties:false`, безопасные pinned image/backend/ref/secret boundaries.
- `execution` c default `MANUAL_HANDOFF`, `NONE`, `EXPLICIT_AFTER_VERIFICATION`, null ADP/SBX; `LOCAL_AUTOMATIC` требует exact revisioned ACTIVE profiles и валидные digest/subject bindings, но **не активирует** agent.
- Legacy `PROJECT_INPUT` нормализуется v3→v4 **в памяти** без переписывания accepted source. v3 не может скрытно включать автоматический режим: не-default execution в envelope v3 отклоняется. v0.5.0 manual Project Instance остается читаемым со старым exact pinned registry lock.
- New lock schema7 включает актуальные registry refs/digests и `execution_profile_bindings` с null полями для manual. Записи Run/Acceptance, существующие истории v0.5.0 не переписываются.

## 3. Фактическая матрица проверок

| Проверка | Команда / метод | Результат |
|---|---|---|
| PH-051-01 targeted contracts | `PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_01_contract_baseline` | **10/10 PASS** |
| Post-fix strict contract + v0.5.0 hardening | `PYTHONPATH=src:. python -m unittest -v tests.test_ph_051_01_contract_baseline tests.test_contract_hardening` | **41/41 PASS** |
| Все исходные + новые tests на окончательных исходниках | `PYTHONPATH=src:.:tests python -m unittest -v <test modules>` в 7 независимых группах | **178/178 PASS** (`168` старых + `10` новых) |
| Документация: собственный validator + итоговый ZIP | `python tools/validate_documentation.py . --zip <docs.zip> --json <report.json>` | **36/36 checks PASS**, 0 errors, 0 warnings, ZIP CRC OK |
| Собранный wheel | `pip wheel . --no-deps --no-build-isolation --wheel-dir dist`; `pip install --force-reinstall` | **PASS**, `project-harness --version` = `0.5.1` |
| Установленный wheel `doctor` | `<venv>/bin/project-harness doctor` | **PASS** |
| Original v0.5.0 Project Instance | Исходный движок `demo`, затем новый `validate-project --project <old-root>` | **PASS**, old lock kept intact |
| Original v0.5.0 manual continuation | `next --project <old-root>` | **PASS**, `VERIFY_CURRENT_TASK` / manual Codex route |
| Original v0.5.0 handoff archive | `validate-handoff --project <old-handoff.zip>` | **PASS**, historical handoff readable |
| Automatic executor / Podman security | Не является scope PH-051-01 | **NOT IMPLEMENTED / NOT RUN; release NO-GO** |

### Весь regression suite по группам

| Группа | Тестов | Время (s) | Exit | Модули |
|---:|---:|---:|---:|---|
| 1 | 9 | 132.8 | 0 | `test_ph_f08_release_acceptance`, `test_maintenance_lifecycle` |
| 2 | 24 | 149.6 | 0 | `test_engine`, `test_gate_evidence_contract` |
| 3 | 28 | 247.0 | 0 | `test_ph_f06_maturity_lifecycle`, `test_canonical_target`, `test_ph_051_01_contract_baseline` |
| 4 | 50 | 125.9 | 0 | `test_ph_f05_intake_acceptance`, `test_assessment_freshness`, `test_exact_assessment_ref`, `test_contract_hardening` |
| 5 | 22 | 143.8 | 0 | `test_ph_f03_active_stage_planning`, `test_implementation_levels`, `test_ph_f01_planner_regression` |
| 6 | 32 | 79.0 | 0 | `test_ph_f04_runtime_reachability`, `test_stage_transaction_recovery`, `test_stage_approval_preparation` |
| 7 | 13 | 61.1 | 0 | `test_ph_f02_semantic_proof_contract`, `test_stage_gate_preparation_block_recovery`, `test_ph_f01_gate_semantics_regression` |

Семь групп покрывают **все 20** `tests/test_*.py` source modules. Логи от каждого фактического запуска находятся в `PH_051_01_LOGS/PH_051_01_FINAL_GROUP_{1..7}.log`. Общее количество было проверено по runner summary; каждая группа завершилась `OK` с exit 0.

Первый предварительный прогон выявил 5 падений из-за тестовых ожиданий старых registry/schema версий; после корректировки только таких ожиданий повторный полный прогон и post-fix прогон завершились успешно. Исправления production code дополнительно прошли финальный regression suite; исходные исторические approval/transaction checks остались прежними.

## 4. Сохранённые инварианты

- Manual `intake → prepare → handoff → next → verify → complete`, baseline v0.5.0 и готовый JIT не требуют Podman.
- Последовательное `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, Stage Gate/semantic evidence, Stage transaction journal/recovery, canonical target и immutable history не менялись.
- Exact Brownfield assessment refs/digests, read-only assessment, baseline acceptance, same-level maintenance и `level-up` — покрыты прежними regressions.
- Нет тайного Host Codex subprocess, нет sandbox wrapper/исполняемой команды `execute-current`, `executor-doctor`, нет network bypass. `LOCAL_AUTOMATIC` при `prepare` отклоняется `AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED` даже при валидных профилях.
- Не добавлялись альтернативные provider API, Git/PR/deployment, VM, distributed execution, arbitrary secrets в input, не переписывались старые accepted records, исходная normative spec сохранена.

## 5. Верификация релиза / ограничения

- Documentation ZIP SHA-256: `9f843173695b9aa69ce572d09ffeba96ff0c0cb701705a451e4d0c00350965c3`.
- Два обновлённых ZIP имеют суффикс `v0.5.1`, но **не являются финальным релизом**: промежуточный этап по плану требует `PH-051-02` … `PH-051-12`.
- Rootless Podman, isolation self-tests, independent verification, protected apply **не реализованы / не проверялись** на этом этапе. Финальное решение по v0.5.1: **NO-GO / WIP**, несмотря на PASS контракта.
- Точные SHA-256 обоих выходных ZIP и результаты post-package validation фиксируются в `PH_051_01_PACKAGING.json` и внешнем manifest после упаковки; архивы проверяются по CRC и `MANIFEST.sha256`.

## 6. Приложения

- `PH_051_01_CHANGED_FILES.md`: точные добавленные/изменённые/переименованные пути относительно исходных ZIP.
- `PH_051_01_LOGS/`: семь regression logs, post-fix targeted checks, wheel build/install/doctor, docs validation JSON и проверки старого Project Instance.
