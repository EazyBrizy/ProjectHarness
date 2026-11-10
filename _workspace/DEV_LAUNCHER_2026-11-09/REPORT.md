# Постоянный запуск исходников Harness — 2026-11-09

На рабочем столе создан **Project Harness — разработка.lnk**. Ярлык **Project Harness.lnk** установленной сборки и его запись в меню «Пуск» сохранены. Оба пути проверены через Windows Shell.

Новый ярлык запускает `.venv/Scripts/pythonw.exe -B tools/launch_harness_dev.py` с абсолютными путями текущего workspace. Он явно импортирует `Engine/src/project_harness` и вызывает существующий public `run_local_web`. Исходники читаются заново при каждом запуске; установщик, wheel и frozen bundle для такого запуска не используются. Изменения кода/локальных UI assets появляются после штатного завершения Harness и повторного открытия ярлыка разработки. Простое закрытие вкладки сервер не завершает.

Используется та же стандартная app-data и те же project roots, что у установленного приложения. Сохранены SID mutex, loopback listener, session/CSRF/Host/Origin checks и manual режим. Если установленный Harness ещё работает, ярлык разработки не заменяет его процесс: существующая launcher policy обслуживает повторный запуск. Поэтому перед переходом на исходники нужно нажать «Завершить Harness» в работающей версии.

Запуск из исходников — режим разработки, не новая принятая frozen release. Самообновление установленного EXE не добавлялось. При изменении зависимостей требуется отдельно обновить workspace venv по закреплённым locks; launcher не скачивает и не устанавливает зависимости. При переносе workspace ярлык нужно создать заново с новым абсолютным путём.

## Scope и сохранность

Allowed file changes до реализации: `tools/launch_harness_dev.py`, этот новый evidence-каталог, навигационная запись `CURRENT_TASK.md`, новый desktop shortcut. [Входные hashes](INPUT_BASELINE.json), [прежний CURRENT_TASK](CURRENT_TASK.before.md), [состояние Git до изменений](GIT_STATUS.before.txt), [точные свойства ярлыка](SHORTCUT.json).

Canonical engine source/resources, tests, docs/mirror, wheel, frozen bundle, installer и их manifests не менялись. Их целостность до/после подтверждена отдельным текущим verifier; Engine/Documentation ZIP не создавались. Существующие незакоммиченные upload UI изменения и OpenDesign prompt сохранены. Исходный текст CURRENT_TASK сохранён после новой навигационной записи.

## Фактическая проверка

Windows 11 x64/NTFS/non-admin; CPython 3.14.10 x64 workspace venv, Flask 3.1.3 и Waitress 3.0.2. Команды, platform, interpreter/deps, exit и hashes logs сохранены в соседних JSON/log files.

- [Environment check](environment-check.log), [run](environment-check.run.json): **PASS / exit 0**, doctor и source import из ожидаемой папки; listener/browser не запускались.
- [Real TCP smoke](tcp-smoke-02.log), [run](tcp-smoke-02.run.json), [summary](SMOKE_RESULT.json): **PASS / exit 0**. Настоящий source launcher с fixture app-data и пустым PYTHONPATH: Waitress health, закрытая unauthenticated session, актуальный source HTML, отказ второму экземпляру до создания app-data, authenticated graceful stop. `pythonw.exe --check` также exit 0. Видимые окна браузера не открывались; пользовательские проекты/auth/uploads не читались.
- Первая [попытка](tcp-smoke.log) — **FAIL / exit 1** из-за работающего пользовательского installed Harness и его SID mutex. Этот log сохранён. После явного сообщения пользователя «Harness завершён» запущен новый независимый fixture; защиту не меняли и процессы пользователя не завершали принудительно.
- Byte equality source/build/wheel/frozen, полная `.pyd` payload, docs mirrors/manifests и неизменные package hashes: **PASS**. [Итоговые hashes](OUTPUT_HASHES.json).

Обычный запуск с открытием default browser здесь **NOT RUN**: действующее ограничение запрещает новые видимые окна. Проверены настоящий TCP запуск без браузера, штатная авторизация/остановка fixture и windowless interpreter ярлыка. Это не повтор полной PH-LW acceptance.

Новых blockers для source launch нет. Следующий разрешённый шаг — пользоваться ярлыком разработки при текущих правках и перезапускать Harness после изменений. Automatic executor остаётся disabled / прежний NO-GO; предыдущие stage/manual verdicts сохраняют свои exact-byte границы; полная v0.5.1 NOT RELEASED. К другим этапам не переходить самостоятельно.
