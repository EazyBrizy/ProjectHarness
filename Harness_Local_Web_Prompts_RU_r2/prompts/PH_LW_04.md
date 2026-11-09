# PH-LW-04 — Защищённый локальный веб-сервер и рабочая оболочка интерфейса

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-04

Local Web HTTP/server/auth/assets, command entrypoint `project-harness ui`, интеграция с application service, security/browser tests. Без реализации отсутствующих бизнес-операций в JavaScript.

Подними реальный localhost-интерфейс, который работает из package и не требует Node/npm от пользователя. `project-harness ui` — новая команда этого этапа; не путай её с уже имеющимся baseline CLI.

### Требуется

1. Flask + Waitress, debug/reloader/development server выключены. Listener только `127.0.0.1`, реальный bind до открытия browser, свободный порт выбирается безопасно. Не используй `0.0.0.0`, host auto-discovery, reverse proxy или firewall rule. Ограничения request body/connections/timeouts должны работать и на WSGI уровне: Waitress буферизует request body, одной проверки после `request.files` мало.
2. Реализуй launcher-ready session bootstrap: криптографически случайный одноразовый секрет, короткий срок, обмен на session, безопасное browser open. Не записывай секрет в query/logs/analytics/export. URL fragment допустим с немедленным удалением из history и POST exchange. Проверяй full Host/Origin включая порт, отклоняй unknown Host/Origin и `null` на mutation. Защити session cookies/CSRF, запрети permissive CORS. Не называй localhost достаточной авторизацией.
3. Все project metadata, file previews/downloads и mutations требуют session. Public health не раскрывает пути/версии приватных проектов. Artifact downloads — через opaque ID и membership/root checks, не `?path=C:\...`. Запрет generic filesystem и shell endpoints.
4. HTTP GET только read. Actions — защищённые POST с expected revision/idempotency; polling читает operation ID. Браузерное обновление страницы не запускает intake/next/verify/recovery. Ошибки context/schema/permission возвращают нормальный structured failure, не HTML traceback.
5. CSP для локальных assets, framing запрещён, nosniff/no-referrer, private responses no-store. User/GPT strings выводи как текст; raw HTML/JS, markdown links `javascript:`, внешние изображения и SVG из upload не исполняй. Все CSS/JS/icons/help локальные, без CDN/fonts/telemetry.
6. Создай UI shell с разделами из плана, списком проектов, read-only overview, текущей стадией/target и next action. Ещё не реализованные операции явно disabled. Русские подписи, keyboard navigation, readable focus, text-status кроме цвета, loading/empty/stale/error. Покажи копируемую browser address при неуспешном auto-open без утечки постоянного токена.
7. Добавь package-data для assets и tests запуска из installed wheel вне source tree. Клиент не принимает security решения, доступность действий повторно проверяет сервер.

### Приёмка и обязательные тесты

Реальный HTTP listener + browser test: нет session, cross-origin form/fetch, bad Host/DNS-rebinding header, wrong port, token replay/expired bootstrap, XSS filename/Markdown, path traversal download, GET refresh immutability. Listener не доступен через LAN interface. Проверяй CSP и отсутствие external requests. Security проверяется также против реального Waitress, не только Flask test client. Windows session smoke должен отличаться от Linux smoke в отчёте.
