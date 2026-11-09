# Текущая работа

Дата: 2026-11-07. Статус: **COMPLETE — PH-LW-06 реализован и проверен в разрешённом scope**. Это не release GO и не разрешение PH-LW-07.

## Задание пользователя и граница

«Приступай к PH-LW-06 по полному промпту из набора r2 на текущей проверенной базе. Выполни тесты, обнови документацию и отчёт. Automatic executor не включай, к PH-LW-07 не переходи.»

Полный [PH-LW-06 prompt](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_06.md) прочитан и реализован в scope опроса/draft APIs/strict exchange/template/bounded exporter-importer/UI/tests. Работаем над самим движком, не над продуктом Harness. Automatic executor выключен; PH-LW-07 не выполняется. Из соседнего core исправлен только прямой readiness defect `project_input.py` (UNKNOWN/material gaps/UNSURE и вопросы), schemas/registries неизменны.

## Текущая рабочая база

Рабочие файлы находятся в распакованных `Project_Harness_Engine_v0.5.1/` и `Project_Harness_Documentation_v0.5.1/`. Build `PH-LW-06-20261107`. Wheel SHA-256: `04c34ced9484c0664f399ef45fe393c475c55d33fdf0fd6df8bd8bbfbc25e1dc`. Новые Engine/Documentation ZIP не создавались.

Входная проверенная пара `_deliverables/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_2026-11-07` сохранена как исторический снимок:

| ZIP | SHA-256 |
|---|---|
| Engine PH-LW-05 | `c8ccd7f1f1b93200db1936d58c274bf535fae09aa616309b54bed8e0e3da33f2` |
| Documentation PH-LW-05 | `5b1dbed1ab7b876b8d5f078596c5c7ca327cd1f269d438407e88ac7bd95d4bd9` |

Эти архивы не содержат PH-LW-06 и не называются обновлёнными. Оригинальные inputs/specs/prompts/старые планы и прежние отчёты сохраняются. Перед изменениями hashes/CRC/manifests и exact исходные рабочие деревья проверены.

## Результат PH-LW-06

Typed forms и реальные questions/readiness; документация→outcome→target; полный локальный GPT pack с inventory/classification/consent; отдельный JSON envelope v2; preview/diff/repair, unverified claims/provenance; stale/forged approvals/unknown fields reject; public draft commit, cancel, exact replay, reload/restart и explicit crash recovery. В приёмке GPT response — **синтетическая fixture**, реального provider/model общения нет.

- [Фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_06_TEST_REPORT.md), [изменённые файлы](../Project_Harness_Engine_v0.5.1/PH_LW_06_CHANGED_FILES.md), [инварианты](../Project_Harness_Engine_v0.5.1/PH_LW_06_PRESERVED_INVARIANTS.md).
- [Глава для оператора](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/13_PH_LW_06_Interview_and_GPT_Exchange.md), [команды](RUNBOOK.md), [карта](PROJECT_MAP.md).
- Native Windows 11 x64/NTFS/non-admin/Python 3.14/pinned Flask/Waitress/Edge: **64 PASS / 0 SKIP**, doctor PASS. Исходный wrapper FAIL из-за двух docs formatting issues сохранён; отдельный docs retest PASS (35 PASS / 1 ожидаемый ZIP WARN).
- Финальный installed wheel, отдельная venv/Unicode CWD: **62 PASS / 0 SKIP**, source import исключён, actual console launcher/health PASS.
- Свежая общая matrix: **40 модулей / 456 methods; 30 PASS / 3 PASS_WITH_SKIPS / 7 FAIL; 24 failure events / 88 error events / 7 SKIP / 0 TIMEOUT**. Все 38 прежних модулей сохранили результаты; 2 новых PASS. Исторические результаты в эту matrix не подставлены.
- [Полная matrix](../Project_Harness_Engine_v0.5.1/PH_LW_06_LOGS/REGRESSION_MATRIX_CURRENT.json), [evidence index](../Project_Harness_Engine_v0.5.1/PH_LW_06_LOGS/EVIDENCE_INDEX.json), [финальная внешняя аттестация рабочих файлов](PH_LW_06/FINAL_WORKING_TREE_VERIFICATION.json), [точные hashes](PH_LW_06/SHA256.txt). Актуальность базы требует PASS аттестации и совпадения manifest hashes.

## Правило хранения файлов — сохраняется

Все рабочие файлы/evidence хранить распакованными. **Engine/Documentation ZIP создавать только по отдельному явному запросу пользователя для передачи в ChatGPT на анализ.** Это правило пользователя от 2026-11-07 заменяет прежнее обязательное ZIP-требование этапов, включая сохранённые prompts; исторические источники не переписываются. Wheel, docs mirror, validators и manifests по-прежнему обязательны по применимости.

Параллельная пользовательская правка правила сохранена: [её отчёт](ARCHIVE_POLICY_2026-11-07/REPORT.md), [предыдущий CURRENT_TASK](ARCHIVE_POLICY_TASK_COMPLETED.md). Старые runtime acceptance данные относятся к своей базе; новая аттестация PH-LW-06 описывает текущие рабочие деревья.

## Gates и следующий шаг

`LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12. `AUTOMATIC_EXECUTOR: NO-GO`, полная v0.5.1: `NO-GO / NOT RELEASED`. Реальный rootless Podman, positive governed per-Run egress, Windows power-loss и clean-machine installer остаются неподтверждёнными. Не менять системную защиту и не ослаблять Linux/automatic tests.

Разрешённый scope PH-LW-06 завершён. PH-LW-04, PH-LW-05 и PH-LW-06: PASS в своих проверенных scopes; общая regression matrix остаётся FAIL по семи прежним Linux/automatic модулям. **К PH-LW-07 не переходить; automatic executor не включать.** Следующий разрешённый шаг — новое явно назначенное задание пользователя; отдельный запрос требуется и для Engine/Documentation ZIP.
