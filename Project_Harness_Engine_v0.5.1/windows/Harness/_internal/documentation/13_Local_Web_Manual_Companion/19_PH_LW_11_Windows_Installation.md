# PH-LW-11 — Windows launcher, установка и resume

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-08  

Эта глава описывает реализацию PH-LW-11. Фактические build/test verdicts и ограничения конкретного комплекта находятся в `PH_LW_11_TEST_REPORT.md` Engine. До полной PH-LW-12 приёмки `LOCAL_WEB_MANUAL: NO-GO`; `AUTOMATIC_EXECUTOR: NO-GO`, полная v0.5.1 — `NO-GO / NOT RELEASED`.

## Установка и первый запуск

Запустите `Harness-Setup-win-x64.exe` обычным пользователем Windows 11 x64. Python, Node, WSL и Podman для подготовки не требуются. Runtime, pinned Flask/Waitress/PyYAML, static assets, schemas, registries, templates, fixtures и документация входят в локальный комплект. Установщик не скачивает зависимости, не меняет PATH/firewall/ExecutionPolicy и не отключает защиту Windows. Сборка без signing credentials имеет статус **UNSIGNED**; Windows может показать предупреждение SmartScreen. Подпись стороннего Inno compiler не является подписью Harness.

По умолчанию программа размещается в `%LOCALAPPDATA%\Programs\ProjectHarness\versions\<build-id>`. Ярлык Project Harness открывает `Harness.exe` из активированной версии; интерактивная установка предлагает его запуск сразу после завершения. Для unattended developer acceptance `/VERYSILENT` не открывает браузер; тест явно запускает установленный EXE отдельно.

Первый экран объясняет загрузку MD/ZIP и вариант «Документации нет». Создание intake требует отдельного действия. GPT exchange остаётся ручным: экспорт → внешний анализ → draft fixture/ответ → просмотр → отдельные approvals → подготовка Project Instance и JIT. Наличие установщика не включает automatic executor.

## Проекты, закрытие и повторный вход

App state находится в `%LOCALAPPDATA%\ProjectHarness`, intake/imports — в соседнем `ProjectHarness-workspaces`; проекты по умолчанию — `%USERPROFILE%\HarnessProjects`. Они отделены от установочных файлов. Explicit selection сохраняет только opaque project ID, экран и revision в `ui-resume.json`; canonical Task/Run/Stage states туда не копируются. GET/polling не сохраняет выбор и не создаёт intake. POST требует session/CSRF/exact Host/Origin/port; stale selection отвергается.

Повторный запуск использует один OS mutex на SID пользователя и fresh mutually authenticated HMAC handshake по отдельному loopback socket. Instance record содержит current-user DPAPI-encrypted key; bootstrap не хранится в нём, логах или exports. Listener выбирает порт реальным exclusive bind на `127.0.0.1:0`. Произвольный listener, старый record или конфликт порта не дают authority и не приводят к убийству процесса. Другая app-data configuration при занятом mutex не создаёт второй сервер.

Вход через launcher или ручной одноразовый код восстанавливает сохранённый экран. Новая вкладка уже открытой cookie-сессии начинает со списка проектов; reload сохраняет экран самой вкладки. Это позволяет выбирать проект независимо в нескольких вкладках. Чтение resume не сохраняет новый выбор.

Закрытие браузера не отменяет mutation и не останавливает сервер. Для нового входа снова откройте ярлык. Если default browser не открылся, локальное Windows окно показывает адрес и одноразовый код; откройте браузер вручную и введите код на странице. Код действует 90 секунд, новый запуск заменяет прежний неиспользованный код. `--no-browser` предназначен для developer diagnostics и не печатает credentials.

«Завершить Harness» — authenticated POST. При активном HTTP mutation или незавершённом worker operation он возвращает conflict. После завершения работы повторите stop. Сервер закрывает admissions, worker и listener; уже committed действия сохраняются. Process crash не повторяет операции автоматически: используйте существующие explicit recovery формы. `Harness.exe` не является Python interpreter и отвергает произвольные script/`-c` аргументы. Core CLI source/wheel остаётся отдельным интерфейсом.

## Целостность, версия и восстановление установки

Inno Setup сверяет compiled SHA-256 каждого извлечённого файла до выполнения frozen helper. Helper повторно сверяет exact file set и hashes, rejects reparse/hardlink paths, чужой непустой destination и overlap. Owned installation root отмечен `HARNESS_INSTALL_ROOT.json`; приложения и проекты не смешиваются.

Новая версия копируется в уникальный staging-каталог, проверяется, переименовывается в ранее отсутствующий version directory; затем атомарно заменяется `current.json`. Live version не перезаписывается. Одинаковая версия допускается только при полном совпадении inventory. При недостатке места, read-only/locked target или interruption остаётся прежний pointer либо целиком проверенная новая версия. Повторный setup допускает recovery без исполнения project operations. Незавершённые staging-каталоги сохраняются для диагностики; автоматического recursive cleanup неизвестных файлов нет. Резерв места снижает вероятность disk-full, но не заменяет реальные ENOSPC tests и не гарантирует power-loss durability.

Uninstall удаляет только перечисленные файлы установленных версий и пустые каталоги. Проекты, approvals, app-data и intake sources сохраняются. Для удаления приватных данных оператор отдельно выполняет backup и удаляет `ProjectHarness`/`ProjectHarness-workspaces`; папки проектов выбирает самостоятельно. Ни installer, ни uninstall не должны удалять пользовательский `.harness`. Running mutex блокирует setup/uninstall в активной Windows session; процессы не завершаются принудительно.

## Воспроизводимая developer сборка

Pipeline PH-LW-01 сохранён: CPython **3.14.10 x64**, PyInstaller **6.22.3 onedir**, Inno Setup **6.7.4**. Используйте отдельную build venv и два hash locks: `local_web/requirements-web-win_amd64-cp314.lock` и `local_web/windows/requirements-build-win_amd64-cp314.lock`. `build_tools.json` фиксирует compiler SHA-256 и версии. Offline установка builder dependencies — `pip install --no-index --find-links <wheelhouse> --require-hashes -r <lock>`. End-user installer не выполняет pip.

Из Engine вызовите developer Python:

```text
python local_web/windows/build_windows.py --output <new-absolute-output> --iscc <absolute-ISCC.exe>
```

Script требует новую output directory, проверяет platform/pins/compiler hash, собирает frozen комплект с `.py` source для поддержанного manual handoff, docs и licenses, выпускает `PACKAGE_FILES.json`, compiled installer checks и `BUILD_RESULT.json`. Build output не заменяет Windows/browser acceptance. `THIRD_PARTY_LICENSES/DEPENDENCIES.json`, текстовые licenses, lock hashes, Python/license и Inno pin описывают зависимости. Reproducibility означает закреплённые inputs и проверяемый recipe; byte-for-byte повторяемость PE/installer без отдельного сравнения не заявляется. Engine/Documentation ZIP не создаются.

Технические источники: [PyInstaller manual](https://pyinstaller.org/en/stable/), [Inno non-admin mode](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm), [Inno AppMutex](https://jrsoftware.org/ishelp/topic_setup_appmutex.htm), [compiled SHA-256 check](https://jrsoftware.org/ishelp/topic_isxfunc_getsha256offile.htm).

## Обнаруженная граница длинного project path

Installer IO поддерживает длинные локальные пути через внутреннее extended представление после проверки обычного local path; системный LongPathsEnabled не меняется. Это не добавляет такую поддержку всему manual core. На проверяемом host с LongPathsEnabled=0 подготовка в длинном profile root получила PREPARATION_IO_BLOCKED: копирование `.harness` в publication staging превысило Win32 limit. Отдельный source public `prepare_handoff` воспроизвёл отказ при той же длине staging path. Этот FAIL сохраняется как ограничение и не заменяется успехом более короткого Unicode profile. Не включайте системные изменения ради приёмки; отдельное исправление общей Windows filesystem границы требует собственного scope и regressions.

Последующее задание разрешило исправление этой границы подготовки: [дополнение long-path](20_PH_LW_11_Long_Path_Preparation.md). Абзац выше и прежний report описывают исходный NO-GO; свежий результат находится в отдельном `PH_LW_11_LONG_PATH_TEST_REPORT.md` Engine.
