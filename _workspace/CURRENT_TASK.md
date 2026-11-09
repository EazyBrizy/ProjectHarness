# Текущая работа

2026-11-09. Проверка переноса Git: добавлены обязательные `.pyd` frozen payload и пропущенный build evidence; для чистого checkout использовать [REPOSITORY_RUNBOOK](REPOSITORY_RUNBOOK.md) и `python -B tools/check_repository.py`. Runtime source, docs, wheel/installer FIX5 и их приёмочные hashes не меняются. [Результаты аудита](GIT_REPOSITORY_AUDIT_2026-11-09/REPORT.md).

2026-11-09. Подключён Git repository [EazyBrizy/ProjectHarness](https://github.com/EazyBrizy/ProjectHarness), целевая ветка `main`. [Область публикации и проверенные hashes](GIT_PUBLICATION_2026-11-09/PUBLISH_SCOPE.md). Git metadata и эта навигационная запись не меняют принятую базу FIX5 и её verdicts.

2026-11-08. **PH-LW-12: GO с ранее принятыми ограничениями; три blockers CLOSED. LOCAL_WEB_MANUAL: GO.** `AUTOMATIC_EXECUTOR: прежний NO-GO; выключен`. Полная v0.5.1 — `NO-GO / NOT RELEASED`. Только Windows. Engine/Documentation ZIP не создавались.

## Задание, scope и проверенная база

Выполнено задание пользователя: исправить три оставшихся blockers PH-LW-12 и повторить приёмку на проверенной предыдущей базе. [Полный prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_12.md); [input baseline](PH_LW_12_FIX/INPUT_BASELINE.json), [input hashes](PH_LW_12_FIX/INPUT_FILE_HASHES.json), [прежний CURRENT_TASK](PH_LW_12_FIX/CURRENT_TASK.before.md). Входные manifests/hashes проверены до изменений, чужие и исторические файлы сохранены.

Allowed file changes были ограничены native Windows IO на воспроизведённом intake/publication/manual пути, общей очередью JSON/multipart, свежей project-card projection, доказанным read-only snapshot polling race, regression tests/actual EXE driver, документацией, generated build artifacts и новыми отчётами. [Точный scope/diff](PH_LW_12_FIX/CODE_CHANGE_SCOPE.json), [diff](PH_LW_12_FIX/CODE_DIFF.patch), [полные before/after hashes](PH_LW_12_FIX/CHANGED_FILE_HASHES.json). State machines, schemas/registries, отдельные approvals, exact refs/digests, immutable accepted history и automatic policy не менялись.

Linux/WSL/Docker jobs не запускать: проект работает только на Windows. POSIX-only methods вне платформы, не prerequisites. Browser evidence — реальный headless Edge/TCP; новых видимых окон не открывать. Системные настройки и LongPathsEnabled не менялись.

## Исправления и результаты

1. **LW12-DEEP-APPDATA-INTAKE — CLOSED.** Native IO охватывает intake/replay/cleanup, источники, approvals, publication/archive validation и затронутые manual Task/evidence/control-plane операции. Публичные paths/refs остаются ordinary local paths; UNC/device/reparse запреты сохраняются. Cleanup сохраняет исходную ошибку и committed session. Настоящие tamper/deletion продолжают давать FAIL.
2. **LW12-MAINTENANCE-RESULT-CONFLICT — CLOSED.** JSON и multipart одной вкладки ждут предшествующие reads/navigation resume. Внешний guard conflict остаётся 409; POST не повторяется автоматически. Actual maintenance result→manual evidence→verify→complete PASS.
3. **LW12-PROJECT-LIST-PROJECTION — CLOSED.** Карточка и основной panel получают fresh public Engine view. MVP→RELEASE показывает ACTIVE / STAGE_PLANNING_REQUIRED; accepted history сохраняется.

[Новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_CHANGED_FILES.md), [verdicts](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_LOGS/VERDICTS.json), [method matrix](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_LOGS/METHOD_RESULTS.json), [evidence index](../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_LOGS/EVIDENCE_INDEX.json).

- Discovery 619 methods / 54 modules; Windows scope 463: **461 PASS / 2 SKIP**. 156 POSIX-only methods вне разрешённой платформы. Source-layout-only PH-F01/F03/F04 — 27 PASS; остальная matrix — installed wheel вне source tree. Fresh original maturity suite — 13 PASS. Новые targeted regressions — 12 PASS.
- Actual installed EXE supported MD/ZIP — 4 PASS; дополнительная deep geometry — 4 PASS, retained project/app-data paths **341/372** символа, LongPathsEnabled 0→0. Actual installer recovery — 4 PASS.
- Actual extended Edge/EXE — **22 PASS / 0 FAIL / 0 ERROR**, включая maintenance upload/complete и MVP→RELEASE/card/history. Отдельный глубокий no-doc→GPT→4 approvals→publish→result→manual evidence→verify→complete — 1 PASS.
- Один прежний fault-test синхронизирован с serialized transport, все assert/expect ASTs прежние. Другие файлы исходного `tests/`, включая fixtures и исторические test logs, побайтово сохранены. Неудачные/прерванные candidate01/02 runs не засчитаны финальной matrix; raw evidence сохранён.

Прежний [PH-LW-12 NO-GO](../Project_Harness_Engine_v0.5.1/PH_LW_12_TEST_REPORT.md) и `_workspace/PH_LW_12/` неизменны. Текущий GO относится к новым exact bytes и принятому Windows scope.

## Принятые ограничения и отдельные verdicts

Четыре ранее принятых NOT RUN остаются: clean Windows без developer runtimes, physical offline, actual Unicode username, real disk-full. Два прежних Windows capability SKIP: native file symlink без нужной privilege; casefold aliases без case-sensitive directory. Их не переименовывать PASS. Junction/hardlink/ZIP link/collision и interruption/read-only/injected failure checks выполнены отдельно. Headless browser не переименовывать проверкой visible default-browser second launch.

PH-LW-04 и PH-LW-05: GO в проверенном Windows scope. PH-LW-12 и LOCAL_WEB_MANUAL: GO с указанными ограничениями. AUTOMATIC_EXECUTOR: прежний NO-GO; disabled. Podman/positive governed per-Run egress — отдельный NO-GO. Полная v0.5.1 не RELEASED. Frozen metadata сохраняет pre-acceptance NO-GO flags; текущий exact-hash manual verdict находится во внешнем новом отчёте.

## Точные текущие артефакты

Build `PH-LW-12-FIX5-20261108`; source digest `sha256:0789035971ad3488b37a3d1cc480a9c7c63effcc3c67c540630e452b77f936ae`.

- Wheel SHA-256 `22ce3cdca5fe875430d4780f163975ba896c3348fa2f30b5a88199064bec54a1`.
- UNSIGNED installer SHA-256 `a4c7432852aadf93fd19fa4646ef8306854369be8ff8fd941ce6d1d268cc5964`.
- [Freeze](PH_LW_12_FIX/RUNTIME_FREEZE.json), [installed environment](PH_LW_12_FIX/WHEEL_ENVIRONMENT.json), [integrity](PH_LW_12_FIX/INTEGRITY.json), [final attestation](PH_LW_12_FIX/FINAL_WORKING_TREE_VERIFICATION.json), [SHA-256](PH_LW_12_FIX/SHA256.txt).

Final05 исправляет детерминированно воспроизведённую гонку snapshot GET с atomic writer. Два новых теста: 2 ERROR на прежних bytes, 2 PASS после исправления. Companion polling не сканирует изменяющееся canonical дерево; root/ownership/integrity и полная mutation admission сохранены. Все 463 Windows methods, fresh maturity и пять actual EXE/recovery наборов выполнены заново по одному final05 freeze; результаты предыдущих candidates не перенесены. Docs metadata FAIL кандидата 03, deep E2E FAIL кандидата 04 и предварительные отчёты сохранены.

[Операторская глава 23](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md) и standalone/embedded/frozen docs совпадают побайтово. После final freeze runtime/docs bytes не менялись; новые отчёты/навигация/manifests не требуют нового wheel. Исторические архивы сохранены, не называются обновлёнными.

## Следующий разрешённый шаг

Использовать/проверять принятый manual companion в указанном Windows scope. Новых blockers этих трёх исправлений нет. К следующему этапу, automatic executor, host fallback, provider API, Podman/egress или LAN listener самостоятельно не переходить. Новые feature работы — только по заданию пользователя. Linux не запускать. Engine/Documentation ZIP — только по отдельному явному запросу.
