# Основание и первичные источники

Дата сверки: 30 октября 2026 года. Это проект реализации Local Web, не отчёт о его выполнении.

**Уточнение r2 (2026-11-01):** входная пара — результат попытки PH-051-12 с NO-GO, а не принятый релиз. Исторические test counts ниже не являются новым прогоном. Ревизия r2 уточняет только инструкции использования WIP-базы; ядро, его документация и прежний release report не изменяются.

## Входные материалы проекта

- `Project_Harness_Engine_v0.5.1.zip`, SHA-256 `c4bd7bd446f926f32ccfe185fe89ede27207ca6ef0998a35ba3c971293b91174`.
- `Project_Harness_Documentation_v0.5.1.zip`, SHA-256 `3a5eee4fac314b5ecaec2edb338d64dd26ecddecc3d0e9212fdeff62ca88209a`.
- `PH_051_12_TEST_REPORT.md`: базовая поставка остаётся **v0.5.1 WIP / NO-GO** для полной приёмки автоматического исполнения. Реальный rootless Podman и положительный governed egress остаются открытыми условиями. Отчёт сообщает 346 выполненных test cases, 2 skipped, 0 failures; это исторические результаты, не новый прогон при подготовке этих промптов.
- `Project_Harness_v0.5.1_Implementation_Plan_RU.md`: особенно §2, §3, §7 и §9.
- `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`: неизменная нормативная спецификация автоматического исполнителя, SHA-256 содержимого `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`.
- `02_Project_Harness_v0.5.0_Implementation_Levels.md`: сохранение последовательной зрелости, exact evidence и formal decisions.

При подготовке этого набора фактически проверены CRC обоих ZIP и все записи их MANIFEST.sha256: 802 Engine и 133 Documentation, несовпадений нет. Исходный код не изменялся. Unit/E2E/Windows tests здесь не запускались.

## Фактически обнаруженные точки интеграции

Ссылки ниже относятся к точной исходной поставке, указанной выше; после патчей номера строк могут измениться.

- `src/project_harness/__init__.py` импортирует runtime при загрузке пакета; `runtime.py:15` импортирует apply; `apply.py:13` безусловно импортирует `fcntl`. Поэтому исправление только `cli.py` недостаточно для Windows-importability.
- `src/project_harness/runtime.py:138,179,549,848`: `project_status`, `next_task`, `verify_current`, `complete_current`. `next_task` может создавать Run/JIT и выполнять продолжение boundary; это не read-only HTTP GET.
- `src/project_harness/intake.py:244`: `check_intake` переписывает input/migration/readiness/questions/session. Его нельзя бездумно вызывать при каждом GET/polling.
- `src/project_harness/compiler.py:871`: `prepare_handoff(workspace, output, keep_directory=...)` уже выдаёт ZIP и папку. В строках 1185–1189 существующий `keep_directory` удаляется через `shutil.rmtree`. Веб-обёртка должна передавать только собственный новый staging-каталог, а не пользовательский существующий проект.
- `src/project_harness/project_input.py:226,230,987–996`: intake approvals имеют поля `approved`, `actor`, `approved_at`, `notes`; нельзя навязать им Stage DEC/ACT schema без отдельного изменения контракта.
- `src/project_harness/active_stage_planning.py:307,556`: `prepare_active_stage_plan`, `plan_active_stage`.
- `src/project_harness/stages.py:1820,2575,3174,3354`: `accept_stage`, `prepare_stage_approval`, `assess_maturity`, `level_up`.
- `src/project_harness/maintenance.py:645,859`: `start_maintenance`, `cancel_maintenance`.
- `src/project_harness/migration.py:917`: `migrate_project`.
- `src/project_harness/cli.py`: 26 команд, включая динамически добавленные `executor-doctor` и `execute-current`; карту всех команд содержит `CONTROL_MAP.md`.
- `pyproject.toml`: Python >=3.11, ядро сейчас без обязательных dependencies; ресурсы перечислены в `tool.setuptools.package-data`. Web-assets и зависимости оболочки необходимо отдельно включить в поставку и проверить в wheel/frozen build.

## Внешние первичные источники

Использованы как обоснование технических решений, не как нормативная спецификация Harness. Конкретные версии зависимостей необходимо закрепить и проверить при реализации, не выбирать `latest` во время установки у пользователя.

1. Flask / Waitress: Windows support, loopback bind, buffering входящего HTTP body: https://flask.palletsprojects.com/en/stable/deploying/waitress/
2. Flask deployment: даже локальная пользовательская поставка не должна использовать development server/debugger/reloader: https://flask.palletsprojects.com/en/stable/deploying/
3. Flask security: limits, escaping, CSP, Host validation: https://flask.palletsprojects.com/en/stable/web-security/
4. Python `fcntl`: Availability Unix: https://docs.python.org/3/library/fcntl.html
5. Python on Windows / embeddable distribution: https://docs.python.org/3.13/using/windows.html
6. PyInstaller: приложение с dependencies без пользовательской установки Python; Windows-сборка выполняется на Windows, это не cross-compiler: https://pyinstaller.org/en/stable/
7. OWASP File Upload: allowlist, отдельное хранение, ограничения размера и распаковки: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
8. OWASP CSRF: token, Origin validation, SameSite как дополнительная, а не единственная защита: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
9. Microsoft filename rules, case sensitivity и namespaces: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
10. Playwright Python: browser E2E на Windows, Linux и macOS; dependency только сборки/тестов, не пользователя: https://playwright.dev/python/docs/intro
