# Текущая работа

Дата: 2026-11-07 (Europe/Moscow). Статус: **ЗАВЕРШЕНО в разрешённом scope** — workspace подготовлен, PH-LW-04/05 исправлены и проверены; полная поставка остаётся NO-GO.

## Задание пользователя

Подготовить workspace Codex, проверить документационную связность и AGENTS.md. Затем: «Прочитай AGENTS.md и выполни preflight текущих архивов. Затем проведи только незавершённую Windows/HTTP security-приёмку PH-LW-04, PH-LW-05. Исправь выявленные дефекты строго в пределах этапа. Выполни доступные тесты и представь фактический отчёт. Не переходи к PH-LW-06 без отдельного задания.»

## Точная база

| Артефакт в `_inputs/` | SHA-256 |
|---|---|
| `Project_Harness_Engine_v0.5.1_PH_LW_05.zip` | `d247127b5ab91b1dffd0f1f0649225bcf2b0bf02abea85a3c211cf3580b40c76` |
| `Project_Harness_Documentation_v0.5.1_PH_LW_05.zip` | `fd6a5d2aff1495708c30cf4f493ef30aed5bc6095a84a2fcd00e4a984013f1df` |

Остальные hashes и полная проверка — [PREFLIGHT_INPUTS.json](PREFLIGHT_INPUTS.json). Внешний `PH_LW_05_SHA256.txt` не предоставлен; вычисленные hashes фиксируют полученные bytes. CRC и все внутренние manifest records совпали. Исторический PH-LW-05 report описывает вход PH-LW-04; это не hashes текущих ZIP. Фактическая исходная lineage PH-LW — PH-051-11; упоминание плановой PH-051-12 не делает её принятой.

## Scope и критерии

Полные задания: [PH-LW-04](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_04.md), [PH-LW-05](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_05.md). Это приёмка уже реализованных этапов, не повтор всей серии.

Разрешены workspace infrastructure, HTTP/auth/launcher/assets/importer/service intake helpers, связанные tests/Windows CI, документация, зеркала и packaging. Core API — только прямой доказанный defect в используемом manual route. Не менять нормы, registry semantics или исторические отчёты.

Применимые сценарии [матрицы](../Harness_Local_Web_Prompts_RU_r2/ACCEPTANCE_MATRIX.md): LW-E02 (wheel, без frozen), E03–05 (import/no-doc, без опроса E06), E23–28 (реализованные HTTP/import/replay части), E29–31 (применимые regressions/recovery), E32 (bind; полный launcher ещё PH-LW-11), E33 (доступные/disabled действия), E34 (release hygiene), E36 (ZIP/wheel/docs/regressions; без installer).

Среда установлена фактически: Windows 11 Pro build 26200, x64, C: NTFS, non-admin, Microsoft Edge 157.0.4341.42. Python/dependencies и результаты текущих прогонов фиксируются в новом отчёте.

PH-LW-06 не разрешён. `LOCAL_WEB_MANUAL`, `AUTOMATIC_EXECUTOR` и полная v0.5.1 сохраняют NO-GO до соответствующих отдельных gates.

## Результат и точка продолжения

Основной [фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_04_05_WINDOWS_ACCEPTANCE_CHANGED_FILES.md), [инварианты](../Project_Harness_Engine_v0.5.1/PH_LW_04_05_WINDOWS_ACCEPTANCE_PRESERVED_INVARIANTS.md).

- Windows PowerShell CI04: PASS, 17 tests / 0 skips. Совокупный CI05: PASS, 44 tests / 0 skips, doctor/docs PASS.
- Установленный wheel в отдельной venv, CWD с кириллицей/пробелами, без source imports: PASS, 27 tests / 0 skips и настоящий console launcher.
- Полный regression набор с явно указанными повторными runs: **FAIL**, 37 модулей / 424 tests; 27 PASS, 1 PASS_WITH_SKIPS, 9 FAIL; 24 failure events, 95 error events, 4 skips. [Матрица](../Project_Harness_Engine_v0.5.1/PH_LW_04_05_WINDOWS_LOGS/REGRESSION_MATRIX_FINAL.json).
- Сохранены 699 исторических report/log файлов, все specs/prompts/старые планы и исходные ZIP. Документационный validator: 36 checks / 925 local links, 0 errors/warnings; standalone/embedded docs побайтово совпадают.

Поставка: [_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07](../_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07). [Output SHA-256](../_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07/PH_LW_04_05_WINDOWS_ACCEPTANCE_SHA256.txt). Номера этапа/версии намеренно не увеличены: это исправленный PH-LW-05, не PH-LW-06.

Финальная пара повторно распакована и проверена: CRC, полное совпадение tree/bytes, manifests 1332 + 144 + 144 records, 44 stage tests без skips, doctor/docs — **PASS**. [Точные output hashes и фактическая проверка](../_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07/FINAL_VERIFICATION/FINAL_ARCHIVE_VERIFICATION.json). Workspace linkage, 145 docs mirror files, 89 source/build/wheel files и неизменность всех семи входов также проверены.

Не считать весь движок Windows-ready: file-symlink fixture не выполним без привилегии; legacy automatic tests содержат Unix assumptions; отдельная migration v0.5.0→v0.5.1 имеет EBADF при fsync и требует отдельного исправления в соответствующем scope. Не запускать automatic executor и не выдавать общий GO. Следующий этап — только по новому явному заданию пользователя.
