# Понятный экран анализа документации

Дата: 2026-11-10. Build `CLEAR-INTERVIEW-20261110` установлен в стандартный пользовательский каталог; обычный desktop shortcut обновлён.

## Причина и результат

`get_interview` возвращает все непустые mutable draft fields. При начальной подготовке это включает настройки шаблона: `implementation.claimed_current_level`, `project.ambiguity_mode`, `skills.resolutions`. Старый renderer показывал их с canonical path, raw JSON и техническим provenance, как будто это уже известные ответы о пользовательском проекте. Хеши/revisions/statuses также попадали в основной текст. Эти значения не были результатами анализа загруженного ZIP.

Изменён только presentation layer:

- Вверху — понятный статус документов и следующий шаг «Подготовить пакет для анализа». Шаги расположены в порядке работы: подготовить пакет → вернуть ответ модели → уточнить вопросы.
- «Сохранённые сведения о проекте» показывают содержательные заполненные поля. Служебные template fields скрыты из этой группы; пустая группа прямо сообщает, что содержательных сведений ещё нет.
- Локальные значения имеют подпись «Сохранено в черновике проекта», без недоказанного утверждения, что их лично ввёл пользователь. GPT values имеют подпись «Предложено моделью» и читаемые имена источников; stale-source review warning сохранён.
- Названия полей, варианты выбора, статусы экрана, история пакетов/ответов, preview и сообщения сохранения показаны по-русски. Canonical option values и network payloads не меняются.
- Хеши, exact refs, status codes и полный технический view доступны в закрытых «Технических сведениях». Полная инструкция модели — отдельный раскрываемый блок с кнопкой копирования. В основной истории файлов нет digests/идентификаторов обмена.
- Общий banner «GET не запускает…» заменён на «Состояние обновлено».

API, provenance computation, schemas/registries, state transitions, sources, export/reply binding и содержимое пакета не изменены. UI не анализирует ZIP автоматически и не отправляет материалы модели. Local login, consent dialogs/checkboxes и automatic executor не возвращены.

## Как продолжить пользователю

Открыть Harness заново через ярлык → выбрать проект → «Опрос и GPT» → «Подготовить пакет для анализа» → выбрать категории данных → «Создать пакет для анализа». Скачать все файлы и передать их ChatGPT или Codex CLI с инструкцией из пакета. Полученный JSON вставить на шаге 2; посмотреть предложения и сохранить. При необходимости уточнить вопросы на шаге 3.

## Только целевые проверки

**2 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, один run без повторов. [Results](UI_RESULTS.json), [command/env/exit](targeted-ui.run.json), [raw log](targeted-ui.log).

1. Новый проект с ZIP из четырёх synthetic MD: next-action button виден до questionnaire; в видимом основном тексте отсутствуют hashes/internal refs/English status/provenance. Template facts не выданы за ответы. Закрытый technical block сохраняет original values/hashes. Общий banner понятный.
2. Сохранение ручного ответа → понятная local-draft provenance → создание/скачивание точного пакета → synthetic model reply с сохранением binding → preview с русскими labels → commit → понятная model provenance и история. Это declared fixture reply, не реальный вызов GPT/provider.

Проверки выполнены в независимой venv с установленным wheel вне source tree, CPython 3.14.10, Flask 3.1.3, Waitress 3.0.2, Playwright 1.64.1, Windows 11 x64/NTFS, real TCP/headless Edge. [Первый экран](screenshots/01-next-step.png), [сохранённое предложение модели](screenshots/02-saved-model-proposal.png); первый снимок визуально просмотрен. Синтаксис двух изменённых JS PASS.

Старые browser label expectations в PH-LW-06/08/12 адаптированы к русским надписям; их полные сценарии не запускались. Core tests и API expectations не ослаблялись. Full engine/core/PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN согласно правилу проверять только изменённое.

## Поставка и сохранность

[Documentation validator](DOCS_VALIDATION.json) PASS, ожидаемый ZIP-not-supplied warning. [Integrity](INTEGRITY.json): src/build/wheel/frozen UI bytes совпадают, все .pyd/payload files проверены, embedded mirror и manifests совпадают. [Build command](frozen-build.run.json), [BUILD_RESULT](BUILD_RESULT.json), [freeze](RUNTIME_FREEZE.json).

Запущенный dev server остановлен штатным public POST в idle состоянии, без force kill: [stop](STOP_FOR_UPDATE.json). [User upgrade](OPERATOR_UPGRADE.json) PASS: aggregate hashes/counts пользовательских app-data/projects до/после одинаковы; прежняя версия сохранена, package/doctor exit 0. [Ярлыки](SHORTCUTS.json). Visible browser windows не открывались; для применения открыть привычный ярлык заново.

В затронутом UI scope blockers нет. PH-LW-04/05: только затронутый presentation path PASS, новые полные verdicts не назначены. LOCAL_WEB_MANUAL full reacceptance NOT RUN; исторические GO сохраняют exact-byte границы. AUTOMATIC_EXECUTOR disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. Engine/Documentation ZIP не создавались; следующие этапы не выполнялись.

## Hashes и scope

- Source digest: `sha256:c82961af214e3ce0c6d1c23588fe1ace0d8ea4612bb260fbf0b6e1aa9a707da7`.
- Wheel SHA-256: `034e627d7ddf89d0e0a576bb1833d068914f01e2d53808ac7a283e7244ff8186`.
- Installer SHA-256: `f851a46e7bd94fb83ca5cae8331868ae46f6d8f5b4d2f9619f2abad04410cf65`.
- PACKAGE_FILES SHA-256: `59540292cb0d0c5daa2efd5a16e24678291ef5d67c3d20d659c3cce88735139d`.
- [Input baseline / allowed file changes](INPUT_BASELINE.json), [changed hashes](CHANGED_FILE_HASHES.json), [diff](CODE_AND_TEST_DIFF.patch).

Runtime diff ограничен `interview.js`, interview HTML, shared notice/description text в `app.js` и build metadata. Остальной backend/core и историческая документация сохранены по input hashes. Чужие изменения не отменялись. Правило понятных пользовательских подписей записано в AGENTS.md и [главе 29](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/29_Interview_Clarity.md).
