# Текущая работа

2026-11-08. **PH-LW-12: NO-GO; финальная приёмка выполнена, gate не закрыт.** `LOCAL_WEB_MANUAL: NO-GO`. `AUTOMATIC_EXECUTOR: прежний NO-GO; выключен`. Полная v0.5.1 — `NO-GO / NOT RELEASED`. Только Windows; Engine/Documentation ZIP не создавать.

## Задание и проверенная база

[Полный prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_12.md) выполнен на проверенной PH-LW-11 базе с принятыми ограничениями. [Input baseline](PH_LW_12/INPUT_BASELINE.json), [input hashes](PH_LW_12/INPUT_FILE_HASHES.json), [прежний CURRENT_TASK](PH_LW_12/CURRENT_TASK.before.md). Входные hashes/manifests PASS, drift отсутствовал.

Явное уточнение пользователя: Linux нигде не используется. Linux/WSL/Docker jobs не запускать; POSIX-only tests вне Windows scope, не prerequisites. Начатый отдельный Linux attempt остановлен, новый runner удалён из Engine; его результаты не засчитываются. Чужие контейнеры и системные настройки не менялись. Browser tests — headless Edge; новых видимых окон не открывать.

Четыре принятых NOT RUN — clean Windows без developer runtimes, physical offline, real disk-full, actual Unicode username — не назначать повторно обязательными. Новые FAIL ниже не являются принятыми ограничениями.

## Фактическая приёмка

[Отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_12_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_12_CHANGED_FILES.md), [verdicts](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/VERDICTS.json), [acceptance](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/ACCEPTANCE_MATRIX.json), [control](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/CONTROL_MATRIX.json), [security](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/SECURITY_MATRIX.json).

- Discovery 607 methods / 53 modules. Windows scope: **449 PASS / 2 SKIP** из 451, точные причины сохранены. 156 POSIX-only — NOT RUN вне платформы. Source-only fixture layout PH-F01/F03/F04: 27 PASS. Старые test bytes сохранены. Ранние FAIL/TIMEOUT/ABORT не переписаны.
- Final installed wheel browser/launcher/metadata **33 PASS**, final source UI regressions **4 PASS**. Final sequential rechecks: maturity **13 PASS**, lifecycle service **22 PASS**, exchange HTTP **3 PASS**, lifecycle HTTP **2 PASS**.
- Actual installed EXE на прежней геометрии путей **4 PASS**; project/app-data retained paths 284/271 символов, LongPathsEnabled 0→0. Install/uninstall и retention PASS. Actual installer fault/recovery **4 PASS**.
- Extended actual EXE: составное evidence **17 PASS / 1 FAIL** из 18 methods, не monolithic PASS. No-doc→GPT→approvals→publish→result→manual evidence→verify→complete PASS. MVP→RELEASE/history PASS. Maintenance result-upload FAIL. Initial advanced fixtures — public kernel setup; tested browser mutations — реальные формы.

Исправлены JSON POST/navigation resume ordering, свежая lifecycle проекция после commit/refresh, переходы stage-status/manual-evidence в существующие формы, устаревшие placeholders и truthful disabled log export. Core algorithms/statuses/refs/approvals/schemas/registries не менялись; в Python service только текст причины. Новая операторская глава 22 и standalone/embedded/frozen docs совпадают побайтово. Неполные deep-path IO experiments полностью отменены.

## Открыто в PH-LW-12

1. **LW12-DEEP-APPDATA-INTAKE:** дополнительный глубокий app-data root — WinError 206 при workspace mkdir; cleanup маскирует его WinError 145, остаётся partial app-owned session. [Reproduction](PH_LW_12/ADDITIONAL_PATH_STRESS.json), [отмена experiments](PH_LW_12/PATH_IO_EXPERIMENT_REVERTED.json). Прежняя геометрия PASS отдельно.
2. **LW12-MAINTENANCE-RESULT-CONFLICT:** actual EXE result-upload получает 409 OPERATION_CONFLICT после navigation/refresh, result NOT_RECEIVED. Own UI read overlap — гипотеза, точный holder не трассирован. [HTTP evidence](../Project_Harness_Engine_v0.5.1/PH_LW_12_LOGS/installed-maintenance-final/task-responses-maintenance.json).
3. **LW12-PROJECT-LIST-PROJECTION:** screenshot показывает STAGE_PLANNING_REQUIRED / active RELEASE в основном panel и прежний TARGET_LEVEL_REACHED в карточке списка. Observed UI inconsistency; отдельный regression test ещё не добавлен. [Observation](PH_LW_12/UI_PROJECTION_OBSERVATION.json).

## Точные текущие артефакты

Build `PH-LW-12-20261108`; source digest `sha256:54aff06eb60bd64b4c87e69c9b7d5c3133f4747bdff0c4ee1f570874cfac8b08`.

- Wheel SHA-256 `765e9bb3a63773e1d4710e21ad330c18713555fb6cf5d8e84660eee52c03ef93`.
- UNSIGNED installer SHA-256 `454d3db52f3c880a3ff1b1243059cf5818961c9f8fc22adca4eb9949a7dac630`.
- [Freeze](PH_LW_12/RUNTIME_FREEZE.json), [integrity](PH_LW_12/INTEGRITY.json), [final attestation](PH_LW_12/FINAL_WORKING_TREE_VERIFICATION.json), [SHA-256](PH_LW_12/SHA256.txt), [before/after](PH_LW_12/CHANGED_FILE_HASHES.json). PASS аттестации — целостность файлов, не release GO.

Старые reports/specs/r2/_inputs/archives сохранены. Engine/Documentation ZIP не собирались и не называются обновлёнными.

## Следующий разрешённый шаг

В пределах PH-LW-12 manual scope устранить три пункта выше, добавить regression tests, затем новый freeze/build и затронутые native Windows/wheel/actual EXE rechecks. Не повышать manual verdict по одной общей matrix. К следующему этапу/automatic executor/Podman/egress не переходить. Linux jobs не запускать; ZIP только по отдельному явному запросу.
