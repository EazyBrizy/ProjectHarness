# PH-LW-11 — ZIP-import при длинном app-data root

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-08  

Дополнение по отдельному заданию исправляет long-path ZIP-import FAIL из предыдущего отчёта подготовки проекта. Текущий фактический verdict, команды, ограничения и hashes — в `PH_LW_11_ZIP_PATH_TEST_REPORT.md` Engine; прежние отчёты и evidence сохранены. PH-LW-12 не выполняется, automatic executor выключен.

## ZIP и sources

Для ZIP upload, карантина, распаковки, immutable snapshots, preview и копирования принятых sources используется внутренний Windows IO adapter. Он применяется также к atomic writes и source refresh transaction: staging, backups, publication, rollback и явной recovery. Manual exchange читает принятые глубокие Markdown files через тот же IO adapter; его storage/count limits, exact bindings и approvals сохраняются. Обход дерева и stat видят глубокие файлы; проверки digests не пропускают их. Обычный короткий source open сохраняет прежнюю точку fault injection; extended spelling нужен для длинного Windows пути.

Внутренний extended drive path появляется только после проверки обычного локального пути и не выдаётся как public path/ref. Пользовательские UNC/device paths, ADS, drive-relative roots, junction/symlink ancestors и недопустимые имена остаются запрещены. Windows registry, LongPathsEnabled, политики и защитные настройки не меняются.

Порядок и значения проверок ZIP не изменены: whole-archive name/type checks до извлечения, traversal, Unicode/case collisions, links/reparse, encryption, nesting, count/depth/size/compression budgets, CRC и UTF-8. AGENTS.md и control names не становятся инструкциями. Исходные bytes/digests сохраняются; документация остаётся UNTRUSTED_PROJECT_DATA, preview — ESCAPED_PLAIN_TEXT. Отдельные approvals, exact revision/fingerprint checks и normative_sources не назначаются импортом.

## Повтор и восстановление

Append идентичных bytes остаётся UNCHANGED; replace создаёт новую revision, старый snapshot неизменен. Interrupted refresh требует существующей явной recovery action после перезапуска. GET/polling не выполняет recovery; rollback восстанавливает canonical files и ledger по прежним bindings/digests. Не удаляйте private imports вручную.

Actual installed EXE acceptance использует длинные Unicode profile/project paths и длинный app-data root одновременно. Fixture snapshot reader независимо читает каждый глубокий файл; прежние browser assertions/deadlines сохраняются. По явному указанию пользователя real second launch получает --no-browser; проверки процесса, mutex/catalog и exit сохраняются. Видимое окно системного браузера этим повтором не открывается. Это scoped native evidence, не замена clean-machine Windows, actual Unicode username, physical offline или real disk-full. Mandatory NOT RUN оставляют PH-LW-11 NO-GO; LOCAL_WEB_MANUAL GO возможно только после PH-LW-12. Installer UNSIGNED. Engine/Documentation ZIP не создаются.
