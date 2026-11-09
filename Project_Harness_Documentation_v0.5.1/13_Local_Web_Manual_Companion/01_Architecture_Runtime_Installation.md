# Архитектура Windows Local Web и воспроизводимый runtime

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап подготовки:** PH-LW-01, 2026-11-01  
**Статус:** CONTRACT DESIGN / NOT IMPLEMENTED / NATIVE WINDOWS NOT RUN

## Непереговорная граница

```text
Windows per-user launcher (future PH-LW-11)
  → local browser, localhost only, no CDN
  → Waitress WSGI HTTP 127.0.0.1:<ephemeral reserved port>
  → Flask view/controller; anti-CSRF, one-user session
  → local application service, protected operations journal
  → existing public Python API (never direct .harness writes)
  → intake workspace OR canonical project tree
```

Домен Local Web — **manual companion**, не новый AI provider. GPT изучает внешние источники вне приложения только по сознательному экспорту; Codex получает JIT вручную. GET/polling только возвращает persisted projections (не `next`, `check-intake`, `verify`). Всегда один mutating operation на project по shared interprocess lock + current core fingerprint, не только React/frontend flag. Crash recovery сверяет canonical core перед любым retry. Локальная auth не защищает от другого процесса под тем же Windows user.

## Первая поддерживаемая Windows platform matrix

| Параметр | Design decision | Доказано на Windows |
|---|---|---|
| ОС | Windows 11 x64, current NTFS, standard non-admin account | NOT RUN |
| Python приложения | CPython 3.14.10, Windows x64, pinned in frozen bundle | NOT RUN |
| WSGI/Web | Flask 3.1.3 + Waitress 3.0.2, static local HTML/CSS/JS | NOT RUN |
| WSGI transitive packages | Werkzeug 3.1.9, Jinja2 3.1.6, MarkupSafe 3.0.3 `cp314-win_amd64`, blinker 1.9.0, click 8.4.2, itsdangerous 2.2.0, colorama 0.4.6, **PyYAML 6.0.3 `cp314-win_amd64` for Harness core** | NOT RUN |
| Установщик | Inno Setup 6.7.4: `PrivilegesRequired=lowest`, `DefaultDirName={localappdata}\Programs\ProjectHarness`, per-user uninstall | NOT RUN |
| Freeze | PyInstaller 6.22.3 `onedir` на настоящем Windows builder; никаких unsupported cross-build | NOT RUN |
| Browser | встроенный системный браузер пользователя, проверка через настоящий браузер; без vendor cloud | NOT RUN |
| Нет на host Python/Node/WSL/Podman | Подготовка и manual handoff не требуют; project-specific SDKs при verify могут потребоваться отдельно | NOT RUN |

Это pinned **проектные версии для сборки**. Фактическая доступность названных бинарных wheel и работы на Windows не доказана в Linux. `local_web/requirements-web-win_amd64-cp314.lock` и `wheel_inventory_v1.json` содержат expected archive names + SHA-256; запрещено устанавливать latest/unpinned. Windows builder должен материализовать offline wheelhouse и с `--no-index --find-links ... --require-hashes` проверить файлы/транзитивные зависимости и совместимость с `cp314` (включая обязательный для bundled core `PyYAML`). Wheelhouse не включён в эту PH-LW-01 поставку. Если pin недоступен, сборка BLOCKED, не заменять молча.

Python project-Harness minimal `pyproject.toml` остаётся `dependencies = []`. Flask/Waitress не импортируются ни из `project_harness.__init__`, ни из CLI и не превращаются в обязательную зависимость console wheel. Engine resources `resources/local_web/*.json` включены в wheel package-data. Проверка frozen bundle/asset lookup/working directory делается позже.

## Файлы и путь установки

- Distribution: `%LOCALAPPDATA%\Programs\ProjectHarness\<local_web_build_id>`; frozen `Harness.exe` и read-only assets. Installer не требует UAC, устанавливается в профиль одного Windows OS user, не в `Program Files`.
- Per-user app data: `%LOCALAPPDATA%\ProjectHarness\` для SQLite project catalog, bounded operation journal, session bootstrap, staging/imports, diagnostics/exports; не для копии Stage State.
- Создаваемые проекты: `%USERPROFILE%\HarnessProjects\<project-slug>` либо явно выбранный **новый** локальный каталог на NTFS. `workspace`, импортированные `sources`, репозиторий и published product root никогда не вложены один в другой и не имеют файловых пересечений; используйте canonical absolute path + Windows file identity checks.
- Intake import staging per source revision; temp ZIP и session tokens не входят в output. Distributions/exports не содержат user private docs/logs. Uninstall удаляет программу, но сохраняет user projects по умолчанию.
- Исполняемый `Harness-Setup-win-x64.exe` / `Harness.exe` **ещё не создан**. Это имена будущих artifacts, не команды для проверки этого PH-LW-01.

## Packaging/version strategy

`engine_version=0.5.1`, исходный `core_schema_version=7`, `local_web_version=0.1.0-dev`, `local_web_build_id=PH-LW-01-PH05111-UNVERIFIED-WINDOWS`, `source_engine_zip_sha256`, `source_docs_zip_sha256`, отдельные `project_ref`, `exchange_id`, `operation_id`. Новый UI receipt не меняет `SCHEMA-PROJECT-PREPARATION-INPUT@4`, Stage/Run/Gate refs, registries или допустимые statuses. При будущем переносе на действительно PH-051-12 base обновлять build provenance и прогонять regressions, не перезаписывать принятые reports.

## Важные platform blockers PH-LW-02

`src/project_harness/__init__.py` импортирует `runtime`; `runtime.py` импортирует `apply`; `apply.py` безусловно импортирует Unix-only `fcntl`. Устранение требует честного portable locking без ослабления concurrency safety, и реального Windows import+lock test. `check_intake` и `next_task` mutating, не подключать их к GET/poll. В `compiler.prepare_handoff` `keep_directory` может удаляться через `shutil.rmtree`; публикация требует строго app-owned **нового** staging root и atomic/safe publish после PH-LW-08. `cli._demo` удаляет старую демо-папку и не является безопасным публичным Web API. Их production реализация **не изменялась** в PH-LW-01.
