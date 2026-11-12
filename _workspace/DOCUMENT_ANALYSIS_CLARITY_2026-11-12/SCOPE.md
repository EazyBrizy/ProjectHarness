# Разрешённое изменение и целевая проверка

Задание 2026-11-12: исправить инструкцию анализа, дубли вопросов, текущие/будущие
этапы, понятные ответы/план и явный выбор модели CLI. База — INPUT_BASELINE.json;
исходный freeze и оба input manifests проверены до правок. Прежние dirty
CURRENT_TASK/диагностический отчёт сохранены.

Allowed file changes: source перечислен в baseline; правильные resource paths —
`resources/local_web/assets/app.css` и `resources/local_web/metadata_v1.json`
(в первоначальном списке записаны предположительные styles.css/build_metadata.json,
они не существуют и не изменяются). Добавлены только local-web v3 schema/module;
core schemas/registries, execution и state machines не меняются. Допустимы
два обновления fixtures в test_cli_document_analysis.py/test_manual_analysis_archive.py,
новый test_document_analysis_clarity.py; новая операторская глава 34, FILE_INDEX,
зеркало docs; generated manifests/wheel/frozen/installer; новые evidence/helpers,
CURRENT_TASK и перенос текущего packaging anchor в check_repository/runbook.

Проверяются только: v3 normalization/strict preview/commit/reload; сохранение
источников и typed objects; текущие/будущие вопросы и roadmap; модель/effort,
фиксированные argv, snapshot/replay; затронутые connect/cancel/stale/restart
границы; ручной ZIP после изменения формата; реальный TCP/headless Edge.
Формальные Task plans не синтезируются и не исполняются. Отдельный actual native
CLI разбор четырёх пользовательских MD выполняется только в приватном scratch
workspace; канонический рабочий проект пользователя не меняется. Это проверка
новой инструкции на исходном проблемном случае, не полный прогон движка.

Для model selection сверены native codex-cli 0.154.0 --help/debug models и
[OpenAI Docs: CLI reference](https://learn.chatgpt.com/docs/cli/reference):
`--model`, config `model_reasoning_effort`, `debug models` (experimental).
Каталог загружается явным POST подключения; GET читает cache, без запуска CLI.
Отсутствие подходящего каталога/модели — понятная ошибка, не скрытая замена модели.
Сохраняется запрошенная модель; server-side alias resolution не выдумывается.

Full engine/core/PH-LW matrix NOT RUN. Повторяется только failed case либо
изменённая после проверки прямая зависимость. Packaging integrity не является
повторной runtime-приёмкой всего движка. Engine/Documentation ZIP не создаются.
