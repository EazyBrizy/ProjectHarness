# Текущая работа

2026-11-08. **PH-LW-11 long-path preparation: PASS. PH-LW-11 acceptance: NO-GO.** Automatic executor выключен; PH-LW-12 не начат; Engine/Documentation ZIP не создавались.

[Новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_CHANGED_FILES.md), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md), [installer](../Project_Harness_Engine_v0.5.1/windows/Harness-Setup-win-x64.exe). [Исходный NO-GO](../Project_Harness_Engine_v0.5.1/PH_LW_11_TEST_REPORT.md) и его evidence/attestation сохранены.

## Проверенная база и результат

[Input baseline](PH_LW_11_LONG_PATH/INPUT_BASELINE.json), [input hashes](PH_LW_11_LONG_PATH/INPUT_FILE_HASHES.json), [прежний CURRENT_TASK](PH_LW_11_LONG_PATH/CURRENT_TASK.before.md), [новая аттестация](PH_LW_11_LONG_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](PH_LW_11_LONG_PATH/SHA256.txt), [before/after hashes](PH_LW_11_LONG_PATH/CHANGED_FILE_HASHES.json).

Build `PH-LW-11-LONGPATH-20261108`, digest `sha256:cff006d0c0ef48ee942d5c7bdfb96c34e01c2f59c0682ca19a76a907cdd4559b`. Installer SHA-256 `43cc06e7e3d1eac23133e1d324c911fb943ae37c403ef36dd860d766e37c2741`, wheel `60a77d83e27de1e3e914ab7a21df1aa50d0348c07199765fb1ef33f9ffc15f40`. Доставка — обычные распакованные файлы и UNSIGNED installer; архивы не обновлялись.

Public prepare_handoff повторён с leaf path 281: PASS. 3 long-path tests PASS, wheel {'installed-nonbrowser': 42, 'installed-browser': 33} PASS, source core/Windows 232 methods в 18 scopes. Фактический EXE: 4 PASS, retained file path до 281 символов; installer recovery 4 PASS. LongPathsEnabled оставался 0, non-admin/NTFS; системные защитные настройки не менялись. [Свежие verdicts](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_LOGS/VERDICTS.json).

## Scope и оставшиеся gates

Разрешённый IO fix затронул только preparation/publication/validators, hashing/serialization/control-plane и Stage read helpers. States/approvals/refs/digests/accepted history/schemas не изменены. Старые tests неизменны; semantic ожидания не ослаблены. Source+wheel+frozen assets и docs mirror синхронизированы.

PH-LW-11 и LOCAL_WEB_MANUAL остаются NO-GO: отдельный ZIP-import FAIL в длинном app-data root (WinError 206 при создании quarantine/materialized; соседний PH-LW-05 IO не изменён), а также clean-machine Windows, actual Unicode username, physical offline, real disk-full — mandatory NOT RUN. Повторный EXE run использует короткий app-data и более длинный project root; он не закрывает исходный ZIP-import FAIL. Прежние file-symlink SKIP, unsigned status и незавершённый visual walkthrough не скрыты. Полная прежняя matrix — историческая; свежий scoped набор не объявлен полным повтором всех automatic/upper-level tests. AUTOMATIC_EXECUTOR NO-GO, полная v0.5.1 NO-GO / NOT RELEASED; Podman/positive egress не закрывались.

Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments. К PH-LW-12 не переходить, automatic executor не включать, ZIP без явного запроса не собирать.
