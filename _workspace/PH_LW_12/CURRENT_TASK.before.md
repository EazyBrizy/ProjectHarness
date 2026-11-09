# Текущая работа

2026-11-08. **PH-LW-11 long app-data ZIP-import: PASS. PH-LW-11 acceptance: GO с принятыми пользователем ограничениями.** Automatic executor выключен, PH-LW-12 не начат, Engine/Documentation ZIP не собирались.

## Решение пользователя от 2026-11-08

[Условия приёмки](../Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md), [decision JSON](PH_LW_11_ACCEPTANCE_SCOPE/DECISION.json), [новая проверка](PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json). Четыре ранее блокировавших NOT RUN приняты как ограничения; текущий PH-LW-11 GO относится только к согласованному объёму. Прежние отчёты/вердикты и аттестации ниже — история до этого решения. Runtime artifacts, source digest, wheel и installer hashes не менялись. LOCAL_WEB_MANUAL и полный релиз не объявляются GO.

[Новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_CHANGED_FILES.md), [глава 21](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md), [installer](../Project_Harness_Engine_v0.5.1/windows/Harness-Setup-win-x64.exe). Предыдущие [long-project report](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md) и исходный PH-LW-11 NO-GO/evidence сохранены.

## Проверенная база и результат

[Baseline](PH_LW_11_ZIP_PATH/INPUT_BASELINE.json), [input hashes](PH_LW_11_ZIP_PATH/INPUT_FILE_HASHES.json), [CURRENT_TASK before](PH_LW_11_ZIP_PATH/CURRENT_TASK.before.md), [final attestation](PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](PH_LW_11_ZIP_PATH/SHA256.txt), [before/after hashes](PH_LW_11_ZIP_PATH/CHANGED_FILE_HASHES.json).

Build `PH-LW-11-ZIPPATH-20261108`, digest `sha256:5f0d5ac595d8a052bfa456140f2d42c5d571c53ab38aff3c8831d4ebbe309bbf`. Wheel `9bb3e87fdf2b297e7292fd5d2216fc1a61c9dbe49e2e4cf018f5eb5f2aa19bc2`; installer `0550a5582182ab95aa8b5376b878cdb3210b126a53b6fd6f90746417d50abb94`. Доставка — распакованные файлы, wheel и UNSIGNED installer. Старые архивы неизменны.

До fix новый public ZIP test воспроизвёл WinError 206. После fix: 7 long-app-data tests PASS; source 242 methods в 20 scopes (2 прежних SKIP, 0 FAIL/ERROR); wheel HTTP/core 49 PASS и Edge/desktop 33 PASS. Actual installed EXE 4 PASS при длинных project и app-data roots одновременно: retained paths 284 и 278 символов. Installer recovery 4 PASS. LongPathsEnabled 0 → 0, non-admin/NTFS. [Verdicts](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_LOGS/VERDICTS.json).

## Scope и ограничения

IO-only ZIP upload/snapshot/preview/verified copy, source refresh/recovery/cleanup и manual exchange IO, inventory, filtered copy и atomic writes. AST бизнес-ветвей прежний после удаления IO adapters; names/budgets/CRC/refs/states/approvals/accepted history/schemas не менялись. Старые tests неизменны. Source/wheel/frozen/docs mirror/manifests синхронизированы.

ZIP-import blocker закрыт. PH-LW-11: GO в согласованном пользователем объёме. Clean-machine Windows, actual Unicode username, physical offline и real disk-full остаются NOT RUN как принятые ограничения; все четыре не блокируют приёмку и не требуют обязательного будущего прогона по явному решению пользователя от 2026-11-08. Прежние symlink/alias SKIP, unsigned status и незавершённый visual walkthrough сохранены явно. LOCAL_WEB_MANUAL NO-GO до PH-LW-12. AUTOMATIC_EXECUTOR NO-GO, выключен; полная v0.5.1 NO-GO / NOT RELEASED; Podman/positive egress не закрывались. Полная прежняя matrix — история, свежий scoped набор не равен полному automatic/upper-level rerun.

PH-LW-11 закрыт в согласованном объёме с принятыми ограничениями. Следующий этап — только по отдельному заданию пользователя; четыре снятых прогона не назначать как prerequisite. К PH-LW-12 не переходить; automatic executor не включать; ZIP без явного запроса не собирать.

Браузер: по явному указанию пользователя не открывать новые видимые окна; для ручной работы использовать уже открытое авторизованное окно. Browser regressions — headless. Обычный real second launch с открытием default browser в свежем повторе NOT RUN; вместо него проверен точный отказ второго --no-browser launch (exit 1), без изменения production launcher.
