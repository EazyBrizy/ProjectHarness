# Windows manual remediation — миграция v0.5.0 → v0.5.1

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Дата дополнения:** 2026-11-07  
**Статус:** WIP / NOT RELEASED. Дополнение к PH-LW-05, не реализация PH-LW-06 или PH-LW-12.

## Задание и база

По отдельному заданию пользователя разобраны 9 FAIL-модулей прошлой Windows приёмки и исправлена применимая manual миграция. База — проверенная пара PH-LW-05 после HTTP retest: Engine SHA-256 `d48a47b43957df5fd3e4e57db98f0b4e2e73c668893489a528e9c739200cb6ef`, Documentation `5d610858306dc91e1b125711e30dc84e7f4aed046d4d72c20f0ff401f05f9b8b`.

Предыдущий `PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md` сохранён как исторический. Новый фактический результат, команды, skips и разбор каждого модуля — в Engine `PH_LW_05_WINDOWS_MANUAL_REMEDIATION_TEST_REPORT.md`; новые ZIP hashes — во внешнем `PH_LW_05_WINDOWS_MANUAL_REMEDIATION_SHA256.txt`. Normative specs и core contracts не изменены.

## Исправления

`migrate-project` сохраняет прежний whole-directory swap: validated source → private staged copy → file flush → journal → old/new rename → recovery. На Windows file flush получает write-capable descriptor; ошибка flush остаётся отказом до публикации journal и первого canonical rename.

Копирование теперь находится внутри блока очистки: если источник становится недоступен во время copy, частичный staging удаляется, исходный проект сохраняется. Windows read-only атрибуты могут препятствовать операции; отказ не превращается в успешную миграцию. При очистке разрешается снять read-only только с обычных файлов с одним hardlink приватного staged/backup sibling, прошедшего проверку родителя, точного имени с UUID и native пути. Атрибуты canonical source и внешнего hardlink не меняются; ACL/sharing failures не подавляются.

Миграция не активирует automatic executor: сохраняются `MANUAL_HANDOFF`, `network_mode=NONE`, null adapter/sandbox refs, `EXPLICIT_AFTER_VERIFICATION`. Accepted input, Stage и старые Run records сохраняются; продолжение manual Run использует прежние public `next`/`verify`/`complete` и отдельное подтверждение результата.

## Проверка и оставшиеся границы

Проверяются public CLI в пути с кириллицей/пробелами, exact replay без новых bytes, manual completion, flush/copy/rename failures, реальные `os._exit` до/после swap и восстановление через public API, native Windows sharing denial/read-only и отказ automatic dispatch без мутации.

File symlink fixtures сообщают SKIP только при фактическом WinError 1314. Составные tests разделены, чтобы этот prerequisite не скрывал malformed/oversize/hardlink проверки. SKIP не подтверждает rejection symlink и не означает PASS соответствующего security gate.

Linux-only result channel, disposable roots, atomic product apply и Podman recovery не портируются этим изменением. Их ошибки на Windows сохраняются в отчёте. Успешный manual subset не означает приёмку всего смешанного test-модуля. В прошлой сводке 4 skips были неточно описаны как 3 Podman + 1 NTFS: фактически это 2 Podman, 1 Unix FIFO и 1 NTFS case-sensitive fixture; raw logs были правильными и сохранены.

Windows power-loss durability не сертифицирована; реальные завершения процессов не имитируют обесточивание диска. Полный `LOCAL_WEB_MANUAL`, automatic executor и v0.5.1 — **NO GO**. Installer/clean-machine gates и PH-LW-06 не выполняются.
