# PH-LW-12 — глубокий app-data, result upload и актуальный список

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-08

Повторная приёмка трёх blockers описана в новом `PH_LW_12_FIX_TEST_REPORT.md` Engine и `PH_LW_12_FIX_LOGS/`. Исходный `PH_LW_12_TEST_REPORT.md` с NO-GO остаётся историческим фактическим результатом. Вердикт относится к точным hashes wheel/installer из нового отчёта; наличие собранного installer само по себе не означает GO.

## Глубокие локальные пути

Harness использует обычные абсолютные пути локального NTFS. Внутренние Windows IO операции используют extended spelling для создания, чтения, проверки существования, enumeration и cleanup, когда обычный путь превышает MAX_PATH. В catalog, canonical refs, lock identity и возвращаемых путях остаётся обычная форма. UNC/device input, junction/reparse points и недопустимые Windows components не становятся разрешёнными. LongPathsEnabled, execution policy и настройки защиты не меняются.

Исправлен весь затронутый маршрут intake: создание workspace и source snapshot, fingerprint/draft, источник для GPT, отдельные approval receipts, check/compile/publication и private result staging. Простая замена одного mkdir не закрывает такой дефект: последующие resolve/exists/unlink тоже должны использовать тот же IO boundary.

Ошибка до регистрации удаляет только свою незарегистрированную session. Исходная ошибка сохраняется. Если cleanup запрещён ОС, к ней добавляется диагностическое примечание; остаток требует operator review и не удаляется повторным POST наугад. Если registration уже committed, session и canonical input сохраняются; повтор exact request восстанавливает отсутствующий receipt. Другие project roots не очищаются.

Control-plane scanner читает длинные пути через тот же IO boundary: существующие файлы не объявляются удалёнными; tamper и настоящее удаление остаются FAIL. Создание, чтение, CRC и сравнение ZIP/directory для handoff сохраняют exact entry names и исходные bytes. Публикация использует тот же атомарный no-replace rename с проверкой directory identity; существующий destination и sentinel не заменяются.

Operation/preparation GET читает собственный атомарный companion snapshot, не обходит меняющееся canonical поддерево. Иначе временный файл публичной операции может исчезнуть между enumeration и stat, ошибочно превратив успешную подготовку в HTTP 500 после reload. Проверки catalog ownership, обычного root, ancestor reparse points, integrity/digest snapshot и отдельной migration policy сохраняются. Если snapshot ещё не создан, проверка canonical выполняется под прежним shared guard и возвращает конфликт при занятом корне. Mutation admission и явное recovery по-прежнему проходят полную проверку дерева; GET ничего не восстанавливает и не повторяет.

## Результат ручной Task

После получения JIT внешний агент меняет только разрешённый product plane. Выберите result JSON и нажмите «Получить результат из файла». JSON и multipart запросы одной вкладки проходят общую очередь: предыдущий status/list/task GET и navigation resume завершаются до отправки результата. Исходные fingerprint, Task/Run binding и consent сохраняются; UI не подставляет новую задачу автоматически.

Другая вкладка, CLI или процесс по-прежнему может вызвать `OPERATION_CONFLICT`. Это отказ до mutation. POST автоматически не повторяется. Дождитесь завершения чужой операции, нажмите «Обновить состояние», рассмотрите актуальные refs и выполните действие явно. Получение result, независимый verification PASS и отдельное complete остаются тремя разными действиями. Manual evidence и consent на команды не выводятся из результата агента.

## Статус списка проектов

После committed действия выбранная карточка получает `kind` и `core_status` из того же свежего ответа public Engine API, что и основной panel. UI не вычисляет Task/Run/Stage state сам. После MVP→RELEASE карточка должна показывать актуальный core route, а не сохранённый TARGET_LEVEL_REACHED предыдущего target. При внешних изменениях используйте явное обновление состояния.

## Границы повторной приёмки

Проверки выполняются только на Windows 11 x64/NTFS/non-admin, с настоящим TCP и headless Edge, отдельно для source, установленного wheel и actual installed EXE. Новые видимые browser windows не открываются. Advanced initial fixtures создаются через public kernel flow и отделены от проверяемых browser transitions; GPT fixture проверяет протокол, не интеллект модели.

Четыре принятых пользователем NOT RUN — clean Windows без developer runtimes, physical offline, real disk-full, actual Unicode username — остаются принятыми ограничениями. Unicode/deep paths, sanitized PATH, injected permission/ENOSPC и no-external-request assertions не объявляются заменой этих условий. Старые явные platform SKIP сохраняют собственные причины.

Build metadata фиксируется до проверки. Его консервативные release flags и полный v0.5.1 NO-GO не заменяют отдельный результат повторной приёмки точных bytes в отчёте. `LOCAL_WEB_MANUAL` и `AUTOMATIC_EXECUTOR` имеют независимые verdicts. Automatic executor выключен, Podman/egress не включаются. Engine/Documentation ZIP по заданию не создаются.
