# PH-LW-11 — решение пользователя об условиях приёмки

**Дата:** 2026-11-08  
**Текущий verdict PH-LW-11:** **GO с принятыми пользователем ограничениями**.

## Принятые ограничения

По прямому решению пользователя следующие четыре проверки **не являются блокерами PH-LW-11**. Они остаются фактически **NOT RUN**; результат PASS им не назначается.

| Проверка | Фактический результат | Влияние на приёмку |
| --- | --- | --- |
| Чистая Windows без инструментов разработчика | NOT RUN | Принятое ограничение; отдельную среду не требовать |
| Работа с физически отключённым интернетом | NOT RUN | Принятое ограничение; обязательный прогон отменён |
| Реально заполненный диск/том | NOT RUN | Принятое ограничение; обязательный прогон отменён |
| Настоящая учётная запись Windows с кириллицей | NOT RUN | Принятое ограничение; отдельный прогон не требуется |

Эти проверки не назначать повторно как prerequisite приёмки или продолжения работы. Вернуться к ним можно по новому явному заданию пользователя. Unicode paths, sanitized PATH, no-external-request checks и ENOSPC injection остаются ранее полученным evidence; они не переименовываются в прогоны перечисленных четырёх условий.

## Основание и изменение прежней нормы

Пользователь подтвердил: «Да, НЕ являются блокерами», затем отдельно уточнил: «Windows с кириллицей тоже не должна блокировать!». Это явное изменение условий пользовательской приёмки данного PH-LW-11.

В [полном prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_11.md) раздел «Реальная приёмка» требует эти проверки; [предыдущий отчёт](PH_LW_11_ZIP_PATH_TEST_REPORT.md) считал их mandatory NOT RUN и основанием NO-GO. Новое решение пользователя снимает именно блокирующий характер и обязательность этих четырёх прогонов. Исходный prompt, исторические NO-GO, raw test results, manifests и аттестации прежних checkpoints не переписываются. Настоящий документ и [машиночитаемое решение](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/DECISION.json) задают текущую политику поверх сохранённой истории.

Требования к self-contained installer, локальным assets, запрету CDN/provider calls, целостности и recovery не ослабляются; runtime-код и core contracts этим решением не меняются.

## Текущий статус и границы

Long-path ZIP-import и последующее чтение sources исправлены и ранее проверены на native Windows без изменения системных настроек. Проверенная база: PH-LW-11-ZIPPATH-20261108; source digest sha256:5f0d5ac595d8a052bfa456140f2d42c5d571c53ab38aff3c8831d4ebbe309bbf. Сохраняются результаты: source 240 PASS/2 SKIP, installed wheel 49+33 PASS, installed EXE 4 PASS, installer recovery 4 PASS. [Полный evidence](PH_LW_11_ZIP_PATH_LOGS/VERDICTS.json) отражает факты и прежнюю оценку до этого решения.

- **PH-LW-11: GO в согласованном пользователем объёме**, с четырьмя явно принятыми NOT RUN ограничениями.
- **LOCAL_WEB_MANUAL: NO-GO** до отдельного завершения PH-LW-12. Сам PH-LW-12 не начат и этим решением не разрешён.
- **AUTOMATIC_EXECUTOR: NO-GO**, выключен; Podman/positive governed per-Run egress не закрыты.
- Полная v0.5.1: **NO-GO / NOT RELEASED**. Подпись не добавлялась: installer UNSIGNED. Два прежних core SKIP и незавершённый visual walkthrough не объявляются PASS.

По отдельному указанию пользователя новые видимые browser windows не открывать; ручной UI выполнять в уже открытом авторизованном окне. Прежний fresh normal browser-opening second launch остаётся NOT RUN; подтверждённый historical normal launch и свежий точный отказ второго --no-browser launch (exit 1) сохраняются.

## Проверка документального обновления

Код, tests, standalone/embedded runtime docs, wheel, frozen bundle и installer не меняются. Решение хранится отдельным документом приёмки вне runtime package; пересборка и повтор runtime tests для этого изменения не требуются. Предыдущая [аттестация](../_workspace/PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json) сохраняется как snapshot до принятия исключений. Текущие hashes, проверка связности, manifests и byte preservation: [новая проверка](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json), [before/after](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/CHANGED_FILE_HASHES.json), [SHA-256](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/SHA256.txt).

Следующий этап — только по отдельному заданию пользователя. Automatic executor не включать, к PH-LW-12 самостоятельно не переходить, Engine/Documentation ZIP не собирать.
