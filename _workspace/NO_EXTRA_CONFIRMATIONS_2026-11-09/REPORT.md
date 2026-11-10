# Действия без повторных подтверждений

Дата: 2026-11-09. Build `SINGLE-ACTION-UI-20261109` установлен в стандартный `%LOCALAPPDATA%/Programs/ProjectHarness`.

## Что изменено

Во всех разделах Local Web удалены `window.confirm` и дополнительные обязательные галочки «подтверждаю / разрешаю / я прочитал». Создание проекта, загрузка/замена ZIP, ответ «Документации нет», остановка, создание GPT pack, применение решений, размещение папки, manual evidence, Task verification и lifecycle actions выполняются конкретной кнопкой без второго вопроса. При отсутствии данных либо ошибке показывается сообщение в форме.

Удалены DOM controls и все обращения к ним; обработчики отправляют существующие `confirm`/`confirmed`/`consent` поля по одному явному нажатию. Статусы проекта, binding/replay checks, источники и результаты не назначаются самим UI. Formal decisions остаются смыслом конкретной кнопки действия, без дополнительной галочки. GET/polling и GPT import не создают решений автоматически. Automatic executor не включался.

CLI `verify` принимает саму команду как намерение выполнить её declared verification plan; `record-task-manual-evidence` принимает саму команду как намерение сохранить переданные наблюдения. Дополнительные confirmation switches больше не обязательны и убраны из help; старые явные switches принимаются для совместимости. Product commands в этой проверке не запускались. Это явное изменение прежнего UX-контракта закреплено в AGENTS.md и [главе 28](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/28_Single_Action_Interface.md); исторические описания не переписывались.

## Только целевые проверки

Три уникальных метода проверяют изменённые UI paths; весь движок и полная PH-LW matrix не запускались.

| Проверка | Итог | Evidence |
|---|---|---|
| Создание проекта, missing fields inline, upload/replace ZIP, rejected ZIP без потери источников, local export, no-doc action и stop — без dialogs | PASS | [targeted log](targeted-ui.log) |
| Отдельные решения без checkbox, размещение папки одним действием | PASS | [focused log](focused-ui.log) |
| Task verify/manual evidence и lifecycle action отправляют current intent без удалённых DOM controls | PASS, typed UI fixtures + captured HTTP requests; business worker не запускался | [targeted log](targeted-ui.log) |
| Независимый installed wheel, исходники совпадают побайтово | PASS | [command/env](targeted-ui.run.json) |
| CLI help без confirmation switches | PASS; без исполнения product commands | [result](CLI_HELP.json) |
| Документация / embedded mirror / manifests / wheel CRC / frozen payload, включая .pyd | PASS | [docs](DOCS_VALIDATION.json), [integrity](INTEGRITY.json) |
| Обновление пользовательской установки, package/doctor и сохранность данных | PASS | [upgrade](OPERATOR_UPGRADE.json), [shortcuts](SHORTCUTS.json) |

Первый UI run: 2 PASS / 1 ERROR. Ошибка была в новом test selector: карточки показывают project ID, а fixture искал название. Исправлен только selector; повторён только этот метод, PASS. Уже прошедшие методы не повторялись. [Поимённые итоги](METHOD_RESULTS.json), [focused command](focused-ui.run.json). Это не исправление runtime через ослабление ожиданий: отсутствие dialogs/checkboxes, exact request count и обязательные API intent checks сохранены.

Windows 11 x64/NTFS/non-admin, CPython 3.14.10, Flask 3.1.3, Waitress 3.0.2, Playwright 1.64.1, headless Edge с реальным TCP. Реальный upload/export/decision путь проверен через public APIs; folder target и Task/lifecycle event checks останавливают mutation на HTTP fixture boundary, не заявляют проверку compiler/worker/core state machines. [Снимок формы](screenshots/documents-without-confirmations.png). Дополнительно проверен синтаксис изменённых JS и Python; run-wide business tests не запускались.

## Обновление и ограничения

Работавший dev server остановлен штатным public POST в idle состоянии, без force kill; [evidence](STOP_FOR_UPDATE.json). Установлен новый build, обычный ярлык обновлён; ярлык «разработка» использует текущий src. Aggregate hashes пользовательских app-data/projects до/после установки совпадают; прежняя версия сохранена. Откройте Harness заново через привычный ярлык, чтобы заменить старую страницу с загруженным JavaScript.

Actual installed-EXE browser/full workflow reacceptance NOT RUN: UI проверен из installed wheel, совпадение UI bytes с frozen/installed bundle доказано отдельно. Full core/PH-LW matrix NOT RUN согласно прямому правилу пользователя. Исторические GO не переносятся на новую сборку как full verdict. PH-LW-04/05: затронутый UI path PASS; LOCAL_WEB_MANUAL full reacceptance NOT RUN. AUTOMATIC_EXECUTOR disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. Engine/Documentation ZIP не создавались. В выполненном scope blockers нет; соседние этапы не запускались.

## Exact bytes

- Source digest: `sha256:2169962ef4e0e5db6f57b50f74e3013285347f0f34bb49cf5cb51aa662ca0acc`.
- Wheel SHA-256: `a4ecc559d6f11dcc42e20b48303a1de2b891d59ca50ace19d8566b82b579c187`.
- Installer SHA-256: `25690fac4d8190d345a0b240f910b19d5f018d8fb6494dbc919e842fcc99ab92`.
- PACKAGE_FILES SHA-256: `d93554a5aec8cf263cba917d42998f459598545fb121ebadf933d633356e669a`.
- [Input baseline / allowed changes](INPUT_BASELINE.json), [output freeze](RUNTIME_FREEZE.json), [changed hashes](CHANGED_FILE_HASHES.json), [diff](CODE_AND_TEST_DIFF.patch).

Runtime изменён только в шести UI scripts, HTML, CLI adapter и build metadata. Соседние core modules, schemas/registries и прежняя документация сохранены по baseline hashes. Старые UI tests адаптированы только к удалённым controls/изменённым надписям; новые целевые методы перечислены выше. Чужие изменения не отменялись.
