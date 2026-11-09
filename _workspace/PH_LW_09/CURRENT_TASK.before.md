# Текущая работа

Дата: 2026-11-07. Статус: **COMPLETE — PH-LW-08: PASS в назначенном scope**.

Пользователь назначил только PH-LW-08 полного r2 prompt на проверенной базе PH-LW-07. Automatic executor выключен; PH-LW-09 не выполнялся; Engine/Documentation ZIP не создавались.

Входные manifests/wheel/workspace hashes совпали с PH-LW-07, drift отсутствует. [Входной baseline](PH_LW_08/INPUT_BASELINE.json), [snapshot CURRENT_TASK](PH_LW_08/CURRENT_TASK.before.md).

Allowed changes: public materialization helper, preparation orchestration/service/HTTP/UI, новые tests/native runner, точечное уточнение PH-LW-07 HTTP test запрета generic prepare без target, docs/README/mirror, metadata/wheel/manifests, новые evidence/reports и workspace navigation/tooling. Core schemas/registries/planner, Stage/level-up tests и исторические источники сохранены.

Реализованы approved-input/build-bound preparation, server-owned staging на destination volume, initial directory/ZIP/project validation и byte comparison, no-clobber publication, catalog registration после rename, explicit recovery, ровно один первый JIT и completion UI. Никаких manual файловых переносов. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1 `NO-GO / NOT RELEASED`.

Фактическая приёмка: 29 новых target tests PASS; native Windows 11 x64/NTFS/non-admin/Python 3.14.10/Edge/Waitress TCP — 115 PASS / 0 SKIP, doctor/docs PASS. Installed wheel в отдельной venv/Unicode CWD — 113 PASS / 0 SKIP, console launcher/health PASS. Полная свежая matrix: 44 модулей / 507 methods, 34 PASS / 3 PASS_WITH_SKIPS / 7 FAIL, 24 failure events / 88 error events / 7 SKIP / 0 TIMEOUT. Все 42 прежних модуля сохранили результаты; новых runtime regression failures нет. Native wrapper FAIL из-за generated metadata закрыт последующими doctor/docs PASS без изменения runtime source; исходный статус сохранён в отчёте.

Текущая распакованная база: build `PH-LW-08-20261107`, source digest `sha256:54980ac893ee5fc38f1cadb1f8807fd21d8923bead7d2dac10d0eb7ba9999c02`, wheel SHA-256 `91367028938d984b0c5f91a6dba9fe953a888d6cd9c9944ccb94cb9f6e94049e`. Docs mirror побайтово синхронизирован. Архивы поставки не обновлялись.

- [Фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_08_TEST_REPORT.md), [changed files](../Project_Harness_Engine_v0.5.1/PH_LW_08_CHANGED_FILES.md), [инварианты](../Project_Harness_Engine_v0.5.1/PH_LW_08_PRESERVED_INVARIANTS.md).
- [Операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/15_PH_LW_08_Preparation_and_Publication.md), [evidence index](../Project_Harness_Engine_v0.5.1/PH_LW_08_LOGS/EVIDENCE_INDEX.json).
- [Финальная аттестация](PH_LW_08/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](PH_LW_08/SHA256.txt), [changed hashes](PH_LW_08/CHANGED_FILE_HASHES.json).

Отдельные PH-LW-04/05/06/07/08 verdicts PASS в их scopes. Открыты physical power-loss/storage-failure, clean-machine installer и весь manual lifecycle, positive governed per-Run egress/Podman. Partial staging сохраняется; publication вне native Windows не поддержана. Подробные NOT RUN и ограничения — в report.

Следующий шаг — только новое задание пользователя. PH-LW-09 не начат. Automatic executor не включать. ZIP поставки требуют отдельного запроса.
