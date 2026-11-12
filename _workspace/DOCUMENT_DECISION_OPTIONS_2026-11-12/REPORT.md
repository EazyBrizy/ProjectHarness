# Готовые варианты решения вопросов

Дата: 2026-11-12. Build `DOC-DECISION-OPTIONS-20261112` установлен, ярлык обновлён,
данные и предыдущая версия сохранены.

Вопросы нового анализа содержат 2–3 варианта с описанием подхода, tradeoffs и
обоснованной рекомендацией. Они определяются документами конкретного проекта;
производственного списка универсальных «ответов на всё» нет. Вариант не выбран
автоматически. До сохранения анализа предложения видны read-only, затем одна
кнопка «Выбрать этот вариант» сохраняет ответ без дополнительного confirmation.
«Свой вариант» поддерживает текст и обычный typed editor. Вопросы будущих этапов
тоже получают варианты, оставаясь необязательными для текущей работы.

Для неизвестных фактов предлагается способ получения данных или явно обозначенное
допущение. Если resolves_question=false, сохраняется подход и прежний blocking,
а не выдуманный готовый факт. Выбранные ответы переживают reload, имеют provenance
USER_ANSWER и входят в следующий пакет как INPUT. Позднее отредактированные поля
помечаются superseded_fields, актуальный draft имеет приоритет. Для массивов
APPEND сохраняет другие ответы; SET защищён от перезаписи изменённых данных.

## Данные и границы

Новый local-web envelope v4 содержит choices/recommendation/existing_unknown_index.
V2/V3 и принятая история не переписаны; core schemas/registries не менялись.
Варианты проходят строгую проверку типа/семантики/refs до показа. Выбор передаёт
только server-issued IDs: произвольный patch готового варианта не принимается.
Недоступны execution/approvals/identity/Stage/Task/JIT/skills/work_packages и прямое
изменение unknowns. Последние меняет сервер для конкретного явно отвеченного
пункта. Основной v4 import не назначает target: для него нужен явный выбор.

Новый POST использует existing public draft update/commit и durable intent/recovery.
Source/input/revision/fingerprint/Origin/replay checks сохранены. GET/polling не
выбирают варианты. Выбор не запускает CLI/model request, команды или product writes.
Максимум v4 — 50 вопросов в прежнем bounded exchange; старому анализу без вариантов
нужен новый разбор. Сам выбор ответа не является formal approval или evidence.

## Только целевые проверки

**11 уникальных методов PASS**, [matrix](RESULTS.json), [среда](ENVIRONMENT.json).
[Source: 5 PASS](source-tests.run.json), [контекст после редактирования](source-context.run.json),
[явный target](source-target-choice.run.json), [final installed wheel: 6 PASS](wheel-targeted.run.json).
Windows 11 / CPython 3.14.10 / pinned Flask/Waitress/Playwright, real TCP/headless Edge,
independent installed wheel вне source tree; package inventory совпал с source.

Проверены обязательные options/recommendation, typed values и запрет protected
изменений, v2/v3 envelopes, привязка существующего вопроса без дубля/снятия blocking,
отсутствие автоподстановки target, SET/APPEND, KEEP_OPEN, custom reply, следующий
pack с ответами, источники/Origin/stale/replay/tamper, no extra model invocation,
existing recovery до/после atomic update. В UI — рекомендации без автоселекции,
один click, свой ответ, будущие вопросы, reload, сохранение typed структуры,
ручной ZIP/strict preview и совместимость текущего CLI пути, без JS errors/dialogs.

Первый [UI probe](ui-probe.run.json) дал ERROR в fixture: прямой service GET
конкурировал с собственными browser reads и правильно встретил operation guard.
Переведено только чтение fixture на существующий serialized public API;
[retry](ui-probe-retry.run.json) PASS, semantic assertions/guard не ослаблялись.
Уже прошедшие проверки повторялись только после изменения прямой зависимости
или для проверки финального distribution boundary. Полный движок не запускался.

## Реальный модельный ответ

Один synthetic CLI case, gpt-6-astra / low (выбран из actual CLI catalog):
существующий вопрос об учёте порядка JSON-массивов получил два содержательных
варианта: позиционное сравнение либо позиционное сравнение с отдельной отметкой
перестановок. Модель объяснила ограничения, рекомендовала простой подход для
прототипа. Рекомендуемый вариант явно выбран в тесте, typed architecture decision
сохранён, approvals false, Task execution отсутствует. Model requests **1**;
при выборе повторного вызова модели нет. [Native result](NATIVE_CASE.json),
[команда/log](native-case.run.json). Raw input/reply/snapshots — приватно в
`_scratch/document_decision_options_20261112/native/`; пользовательский проект
не анализировался повторно и его ответы не выбирались тестом.

Native run проверял source layout до финальной регенерации build metadata и
добавления flags устаревшего answer context/явного target guard. Для этого case
target уже выбран и старых answers нет; обе новые ветки проверены отдельно.
Actual installed-EXE browser reacceptance NOT RUN: UI evidence — final wheel,
EXE — полная byte equality/package/doctor. [Снимок вариантов](../../_scratch/document_decision_options_20261112/playwright/ready-options.png).

## Артефакты

Docs validator PASS / 0 errors / ожидаемый WARN без delivery ZIP:
[результат](DOC_VALIDATION.json). [Integrity](INTEGRITY.json) проверяет source,
build/lib, wheel, frozen including .pyd, mirrors/manifests, allowed changes и
сохранение предыдущей работы. [Upgrade](OPERATOR_UPGRADE.json), [shortcut](SHORTCUTS.json).
Source digest `sha256:4cad15d1c41f8386814bb44aa53218687c3ffdf73398c833ac6d0d3f48dfa092`.
Wheel SHA-256 `38354735dd4d278868fd34543c0702615121dcf6ca18e4a9a99fc88186194715`.
UNSIGNED installer SHA-256 `fc242b3bff45585ff1ff675d39a531dfaec12c0e10624a3a30e7bc7a657cb3ba`.
[Freeze](RUNTIME_FREEZE.json), [before/after](CHANGED_FILE_HASHES.json).

Full engine/core regression/PH-LW matrix NOT RUN. Старые verdicts не расширяются
на новые bytes; AUTOMATIC_EXECUTOR disabled / прежний NO-GO, full v0.5.1 NOT RELEASED.
Engine/Documentation ZIP, commit/push и Git-index equality check незакоммиченной
работы NOT RUN. История и все предыдущие uncommitted изменения сохранены.

Следующий шаг: открыть Harness прежним ярлыком, повторить анализ, сохранить
предложения; выбрать вариант на шаге 3. Другие этапы самостоятельно не выполнять.
