# PH-051-09 — Governed automatic runtime, CLI/API: тестовый отчёт

**Дата:** 2026-10-26. **Версия:** v0.5.1 WIP / NOT RELEASED. **Scope:** PH-051-09 normative §§15–18,20, приоритет предыдущих PH-051-01..08.

## Проверенный вход

- Engine: `Project_Harness_Engine_v0.5.1_PH_051_08.zip`, SHA-256 `60842b6ac387a24e086ee3b713ebc5a41f2058821c1877353ceb5e7e4d862204`.
- Documentation: `Project_Harness_Documentation_v0.5.1_PH_051_08.zip`, SHA-256 `a569f528eb27f21061cc27e8247a3443c91fb64d668d235768e15c1b63a11170`.
- Нормативный `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`: SHA-256 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`. Manifest входной пары: Engine 588 / Docs 123 записей, ошибки 0. **План:** Project_Harness_v0.5.1_Implementation_Plan_RU.md.

## Реализация только PH-051-09

1. Public `executor-doctor` и `execute-current` CLI/Python APIs. `status`, `next`, `stage-status` предлагают поддерживаемые маршруты. Управляемый Stage fence и ONLY current READY Task/JIT; manual opt-out и failed doctor не изменяют Run.
2. Project-scoped исключающий lock, подписанные `AUTO_RUNNING → AUTO_VERIFYING → AUTO_VERIFIED` journal phases и структурированные Run statuses `RUNNING`, `VERIFYING`, `SUCCEEDED`, `TIMED_OUT`, `FAILED_RETRYABLE`, `BLOCKED`. Повтор после успешного apply idempotent без нового запуска; прерванный process не перезапускается неявно. Новый retry только через прежний governed `resume` создаёт отдельный immutable Run/Task revision.
3. Композиция уже имеющихся exact Codex CLI/Podman, validated result/ART, независимого verifier и PH-051-08 crash-consistent apply; SANDBOXED report/normalized task evidence не сертифицируют любые Gate subjects. Run complete привязан к signed Apply Evidence; `AUTO_AFTER_PASS` закрывает **Task**, не Stage Gate; explicit policy остаётся доступной.
4. Исправлен непосредственный integration defect: `validate-project` ошибочно искал `verification_report` вместо фактического `validation_report`, а новый `apply_evidence` отвергал как `verification_evidence`. Теперь apply evidence обрабатывается по существующей **строгой** `SCHEMA-APPLY-EVIDENCE@1`, проверяется точный filename/id и Run binding. Поддержан устаревший минимальный manual Run context в status-helper.
5. Базовые файлы, schemas/registries, Stage/Brownfield/maintenance contracts и ранее принятые evidence/reports не переписаны. Введённых unsandboxed, HTTP provider/Git/deployment/parallel функций нет.

## Проверки

| Проверка | Результат | Подтверждение |
|---|---|---|
| PH-051-09 targeted unit/negative/controlled integration | **PASS 15/15** | `PH_051_09_LOGS/PH_051_09_TARGETED_FINAL.log`; Podman в тесте mocked transport, **не** реальная sandbox attestation |
| Source compilation и mirrored distribution package | PASS | strict Python compilation; `src/` и `build/lib` согласованы |
| Первый последовательный full regression | **FAILED 315 tests, 9 errors, skipped 2** | Исполнен до окончательных fixes: 8 errors от утраты executable mode у zip-extracted `bin/project-harness`, 1 от неполного legacy Run context; логи сохранены отдельно. Ошибки воспроизведены и исправлены. Не учитывается как PASS. |
| Финальная регрессия всех модулей | **PASS: 320 tests / 11 shards, 2 skipped, 0 failures/errors** | `PH_051_09_LOGS/PH_051_09_FINAL_SHARD_SUMMARY.json` и `PH_051_09_SHARD_01..11.log`; команда `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -q tests.<module> ...` по всем modules предыдущей PH-051-08 матрицы + PH-051-09. Все exit 0. |
| Сохранение PH-F08, Stage/Brownfield/maintenance, PH-051-01..08 | **PASS** | 10 старых regression shards + 1 новая; scope-аудит неизменности historical records `PH_051_09_SCOPE_AUDIT_Engine.json`, `PH_051_09_SCOPE_AUDIT_Documentation.json` |
| Documentation validator и ZIP/manifest | **PASS: 36 checks / 0 warnings / 0 errors** | `PH_051_09_DOC_VALIDATOR_ZIP_PASS.json`, zip CRC/PASS, 124 hashed manifest entries, 125 files в документационном архиве |
| Installed wheel / CLI / project | **PASS** | `PH_051_09_WHEEL_BUILD.log`, `PH_051_09_WHEEL_SMOKE.log`: `pip install --no-index --no-deps <wheel>`; installed `project-harness --version`, `doctor`, оба новых `--help`, public Python API, `executor-doctor` и `execute-current` на demo `MANUAL_HANDOFF` (оба штатно exit **3**, `BLOCKED/EXECUTOR_UNAVAILABLE`), `validate-project` exit 0 / PASS. |
| Source distribution doctor | **PASS, 6 checks** | `PH_051_09_DOCTOR_PRELIMINARY.json`, canonical registries, 17 schemas, entrypoints/resources, distribution manifest. Финальная проверка после упаковки дополнительно. |
| Mirrors, permissions, history and scope | **PASS** | `src`↔`build/lib`, documentation standalone↔embedded byte-identical, original bundled executable mode `0755`, no deleted input files, no modifications prior PH reports. |
| Реальный `ROOTLESS_PODMAN` и fake CLI-in-container | **NOT RUN / NO-GO release** | `podman` отсутствует, packaging host UID 0. Mock НЕ является проверкой OS isolation. |

## Границы и оставшиеся риски

- Пока PH-051-10 не выполнен, глобальный orphan container recovery и interrupted-Run cleanup **не заявлены**. Auto Run со статусом `RUNNING/VERIFYING` нельзя неявно переисполнить; apply journal recovery действует в уже реализованном PH-051-08 контракте.
- Backend из PH-051-03 реализует только `network NONE`; даже с CLI `--network EXPLICIT_APPROVED_EGRESS --approval` запуск запрещён `NETWORK_NOT_APPROVED`, пока полноценный approved egress backend не существует. Debug root retention запрещён без принятой policy. Нет downgrade безопасности или host fallback.
- Расширенная security acceptance и migration относятся к PH-051-10..12; версия v0.5.1 остаётся **WIP / NOT RELEASED; выпуск GO не подтверждён**.

**Запуск финальной регрессии:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -q ...` в 11 независимых группах из опубликованной PH-051-08 матрицы (плюс новая PH-051-09), `PH_051_09_FINAL_SHARD_SUMMARY.json` фиксирует 320/320 успешных тестов на окончательных исходниках (318 executed, 2 expected skipped). Первоначальный неуспешный диагностический прогон не скрыт и в расчёт PASS не включён.

**Previous invariants:** Stage sequential target, immutable accepted history, exact evidence/refs, independent semantic Gate proof, crash-consistent stage+product apply, Brownfield read-only, same-level maintenance и manual handoff сохраняются.
