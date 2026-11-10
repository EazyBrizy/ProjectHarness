# Активные кнопки документов — 2026-11-09

**Целевое исправление: PASS.** Во вкладке «Документы» кнопки доступны при незаполненных обязательных условиях. При нажатии появляется сообщение с конкретным следующим шагом; фокус переводится на нужное поле/кнопку. Пока выполняется запрос, повторное нажатие временно заблокировано.

Доступны создание проекта, обе формы «Документации нет», «Импортировать файлы» и «Перейти к опросу и GPT». Проверяются пустое название, отсутствие созданного/выбранного intake, отсутствие файлов, ещё не импортированный выбор, отсутствие MD/явного no-doc решения, неподходящий Project Instance и непрочитанный актуальный source inventory. Ошибка обязательного условия не отправляет mutation. Валидация public Engine APIs, confirmations, fingerprint/revision checks и отдельные approvals сохраняются.

Изменены только `app.js`, `index.html` и build metadata в runtime source. Backend, canonical states, schemas/registries и исходные core tests побайтово сохранены. Тесты предыдущего upload UX изменены по новому явному требованию пользователя: вместо ожидания disabled кнопки проверяют её доступность, сообщение и отсутствие недопустимого перехода. Semantic import/recovery assertions не ослаблены. Добавлены четыре UI-сценария в `test_document_button_validation.py` и операторская глава 25; docs mirrors/index/manifests синхронизированы.

## Проверенная база и результаты

Вход — `DOC-UPLOAD-UX-20261109`, source digest `sha256:629263b3719a325337b976402d37bfad8d3ef369a9d531eb937373d77c499386`. До edits подтверждены полный source freeze и standalone/embedded docs; сохранены [input hashes/scope](INPUT_BASELINE.json), before files и [Git status](GIT_STATUS.before.txt). Существующие dirty изменения и прежние отчёты не перезаписывались.

Новый build: **`ACTIVE-DOC-BUTTONS-20261109`**.

| Проверка | Результат | Evidence |
|---|---|---|
| Source UI: обязательные поля, позитивный импорт, negative ZIP, replay/reload, потеря ответа, busy guard | PASS, 16 исполнений: 10 уникальных cases и 6 повторно обнаруженных imported cases | [source log](source-ui.log), [command/exit](source-ui.run.json) |
| Финальный installed wheel вне source tree: новые UI + PH-LW-04/05/06 | **54 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, 54 уникальных cases | [log](wheel-tests-02.log), [run](wheel-tests-02.run.json), [summary](WHEEL_RESULTS_02.json) |
| Docs validator | PASS, 36 checks / 0 errors; ожидаемый WARN без ZIP | [result](DOC_VALIDATION.json), [run](docs-validation.run.json) |
| Frozen/installer build и package check | PASS, exit 0 | [build run](windows-build.run.json), [build result](BUILD_RESULT.json) |
| Новый frozen EXE `--doctor` | PASS, exit 0 | [run](frozen-doctor.run.json) |
| Source/build/wheel/frozen, полная payload с `.pyd`, docs mirrors/manifests, original core tests | PASS | [integrity](INTEGRITY.json), [run](integrity.run.json) |

Настоящий Windows 11 x64/NTFS/non-admin, Python 3.14.10 x64, pinned Flask 3.1.3 / Waitress 3.0.2, Playwright 1.64.1, headless Edge и реальный TCP. Wheel установлен offline `--no-index --no-deps --force-reinstall` в прежнюю независимую acceptance venv с закреплёнными зависимостями. Импорт исключительно из site-packages, пустой PYTHONPATH, отдельная Unicode CWD; exact installed bytes проверены перед suite.

Первый wheel run сохранён как **FAIL / 1 ERROR**: один прежний browser case пытался открыть отсутствующий Playwright Chromium, поскольку канал Edge не был указан. Это ошибка команды проверки, не frontend validation. Канал явно установлен в `msedge`; полный набор повторён без изменения runtime/test expectations. [Первый log](wheel-tests.log), [результат](WHEEL_RESULTS.json). Первичная source discovery дублировала импортированный TestCase; импорт заменён на module alias, в финальном wheel suite дублей нет.

## Точные артефакты

- Source digest: `sha256:2571b23e390a0ce925d3306dbffc6a0682ddfce30f8423e25fce5fb0f9f35bbf`.
- Wheel SHA-256: `969d013efc2cb3d9e14798eed524d7a7296ba5ded6977f126267cde789b4764f`.
- UNSIGNED installer SHA-256: `6ed97345bb83c530e9bd344dbd337448ab81acafe8d66dfeabcc186220001390`.
- Frozen manifest SHA-256: `5b3a861072e1a46339788842add1b7809509108c6327c61a4c684f118aa9d318`.

Полные source/docs hashes: [RUNTIME_FREEZE.json](RUNTIME_FREEZE.json). [Diff текущей правки](CODE_DIFF.patch), [output hashes](OUTPUT_HASHES.json), [снимок сообщения](screenshots/missing-project.png). Старые wheel/installer/frozen bytes сохранены обычными файлами в input wheel этого каталога и `_scratch/active_document_buttons_20261109/before`. Engine/Documentation ZIP не создавались.

Проверка текущих артефактов без перезаписи прежних checkpoints: `python -B _workspace/ACTIVE_DOCUMENT_BUTTONS_2026-11-09/checkpoint.py verify`.

## Использование и границы

Пользователь работает через **«Project Harness — разработка»**. Для применения новых assets достаточно обновить вкладку; для согласованного нового build identity рекомендуется штатно завершить Harness и открыть этот ярлык снова. Выбор файла после перезагрузки страницы нужно повторить. Переустановка не нужна; пользовательские проекты/документы в этом задании не изменялись.

Пользовательская установленная версия остаётся `DOC-UPLOAD-UX-20261109`: этот installer собран в workspace, но пользователю не устанавливался. Actual installed-EXE browser reacceptance новой сборки **NOT RUN**; выполнены frozen package/doctor и wheel UI/TCP проверки. Видимые окна не открывались; старые ограничения Windows acceptance не переименованы в PASS.

Отдельные verdicts: целевой document button UX — **PASS**; применимые PH-LW-04/05 regressions — PASS. Прежние PH-LW-12 / LOCAL_WEB_MANUAL GO сохраняют привязку к FIX5 и принятым ограничениям; полная повторная matrix нового build **NOT RUN**. AUTOMATIC_EXECUTOR — прежний NO-GO / disabled; Podman/positive governed per-Run egress — отдельный прежний NO-GO; полная v0.5.1 NOT RELEASED.

Новых blockers в целевом scope нет. Следующий разрешённый шаг — использовать форму документов через dev shortcut. К другим этапам и automatic executor самостоятельно не переходить.
