# PH-LW-04 — защищённый loopback HTTP и оболочка Local Web (WIP)

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап реализации:** PH-LW-04, 2026-11-03  
**Действующая база:** PH-LW-03 на Engine v0.5.1-WIP / PH-051-11 lineage, а не принятый release PH-051-12. **Версия companion:** `0.1.0-dev`. **Статус:** реализация кода PH-LW-04, Windows 11 x64/NTFS и реальная HTTP/Waitress/browser security acceptance до фактического прогона не доказаны; v0.5.1 **NO-GO / NOT RELEASED**, Podman isolation и положительный per-Run egress остаются отдельными blockers. Это не implementation PH-LW-05–12.

## 1. Состав и граница

Новая публичная CLI-команда `project-harness ui [--app-data <trusted-local-directory>] [--no-browser]` запускает сервер, не реализующий бизнес-операции самостоятельно. Она доступна также как `python project-harness.py ui` из извлечённого source tree. `--no-browser` — режим диагностики listener без возможности войти через URL; он не выдаёт авторизацию из HTTP и не предназначен для нормальной работы пользователя. Для осмысленного входа используется обычный запуск с браузером. Доверенный `--app-data` задаётся оператором в командной строке, **не** из HTTP/JSON. Default на Windows: `%LOCALAPPDATA%\ProjectHarness`; на Linux: `$XDG_DATA_HOME/ProjectHarness` или `~/.local/share/ProjectHarness`. Этот каталог не совпадает с Project Instance и не включается в handoff.

**Зависимости:** Flask `3.1.3`, Waitress `3.0.2` и закреплённые транзитивные пакеты из `local_web/requirements-web-win_amd64-cp314.lock`. `pyproject.toml` предоставляет отдельный extra `local-web`; console-only wheel не импортирует Flask/Waitress до запуска `ui`. Пакеты должны быть установлены из точного lock / проверенного offline-wheelhouse на целевой платформе. Если они отсутствуют, `ui` возвращает нормальную `VALIDATION_FAILED`; не переходит на Flask development server или `http.server`. HTML, CSS и JS упакованы как `project_harness/resources/local_web/assets/`, доступны через установленный wheel без npm/Node/CDN/remote font. Установщик/Windows frozen bundle создаются только в PH-LW-11.

## 2. Listener, лимиты и адрес

`open_bound_loopback_socket()` заранее резервирует случайный OS-allocated порт (`bind(127.0.0.1, 0)`, `listen`), возвращает actual port, **не** освобождает порт для повторного bind. Waitress `create_server(..., sockets=[prebound_socket])` использует тот же descriptor; browser auto-open вызывается только после создания Waitress server. Никакого `0.0.0.0`, DNS auto-discovery, `localhost` alias, IPv6 wildcard, reverse proxy, firewall rule, TLS/remote ingress, browser terminal, hosted auth/proxy, shell/provider/Git API. **При падении сервера сессия исчезает**, повторный запуск выдаёт новый bootstrap.

Реальные WSGI-side budgets Waitress: `max_request_body_size=64 MiB` (проверка до Flask body parsing), `max_request_header_size=16 KiB`, `connection_limit=32`, `backlog=16`, `threads=4`, `channel_timeout=20s`, `trusted_proxy=None`, `clear_untrusted_proxy_headers=True`, `expose_tracebacks=False`. Application-layer JSON <=512 KiB, bootstrap JSON <=4 KiB, Flask `MAX_CONTENT_LENGTH=64 MiB`; запросы с query, `Content-Encoding` или неподдержанным HTTP method отвергаются. Ограничения импорта MD/ZIP из плана начнут проверяться в PH-LW-05, **здесь нет upload** и нет утверждений об их проверке.

## 3. Одноразовый вход и browser security

Trusted launcher выпускает 256-bit CSPRNG bootstrap `secrets.token_urlsafe(32)`, срок 90 секунд, хранит только SHA-256 в process memory, заменяет ранее выданный секрет при переиздании и удаляет при успешном обмене. Только **fragment** `http://127.0.0.1:<port>/#bootstrap=<one-time>` передаётся в browser; fragment не передаётся в HTTP request и удаляется `history.replaceState` до первого browser fetch из JS. `POST /api/session/bootstrap` принимает только exact same-origin `Origin` + JSON `{ "token": ... }`, выдаёт новый случайный 256-bit session ID в HttpOnly, host-only, SameSite=Strict cookie и отдельный CSRF token в JSON. Сервер хранит хэш session ID и csrf исключительно в памяти; absolute 8h и idle 30m TTL; logout инвалидирует сессию. Replay и expiry bootstrap отклоняются; секрет не появляется в URL query, response/error/diagnostic logs и exports. При отказе auto-open launcher показывает **только** копируемый *неавторизованный* адрес без секрета и объясняет, что для безопасного входа нужно повторить запуск после исправления browser integration. Не печатать одноразовый URL в redirected/записываемый stdout.

Cookies не получают флаг Secure, поскольку приложение работает строго на `http://127.0.0.1` и браузерная совместимость Secure cookie по HTTP/loopback неодинакова; такой локальный HTTP **не заменяет TLS или OS security boundary**. Защита обеспечивается bind-only loopback, совпадением полного raw `Host` **включая порт**, exact `Origin` для POST, блокировкой `null`/чужого Origin, `Sec-Fetch-Site`, proxy-derived Host, серверной сессией и отдельным `X-CSRF-Token` для всех изменяющих HTTP API, строгим SameSite cookie. DNS rebinding на другой Host/port блокируется. Сессия уязвима к вредоносному ПО с правами того же OS-пользователя, что вне текущей границы sandbox.

Заголовки для всех ответов: CSP `default-src 'none'`, `script/style/connect/img-src 'self'`, `frame-ancestors 'none'`, `object/worker/font-src 'none'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, private `Cache-Control: no-store`, `Permissions-Policy`. Нет CORS-allow headers. HTML статичен, никакая строка из core/GPT/filename не вставляется как `innerHTML`, Markdown и `javascript:`-links не рендерятся/не исполняются. Favicon/icons и JS/CSS локальные. Браузер не отправляет запросы на внешние сервисы.

## 4. Точные HTTP endpoints

| Method | Path | Доступ и семантика |
|---|---|---|
| GET | `/health` | Public `{"status":"ok"}`, без paths, version, project metadata |
| GET | `/`, `/assets/app.js`, `/assets/app.css` | Public статичная оболочка и только allowlisted assets |
| POST | `/api/session/bootstrap` | Exact Host/Origin, CSPRNG one-time exchange, no existing session required |
| GET | `/api/session` | Только факт авторизации (если да — текущий CSRF для same-origin JS); без project metadata |
| POST | `/api/session/logout` | Auth+CSRF, revocation |
| GET | `/api/projects` | Auth; service `list_projects`, непрозрачные `LWP-*` IDs, read-only |
| GET | `/api/projects/<LWP-ID>` | Auth; service `get_status`, exact current fingerprint/Stage refs; никакого `next` |
| GET | `/api/projects/<LWP-ID>/operations/<LWO-ID>` | Auth+ownership, только bounded projection существующей операции; без mutation/recovery |
| POST | `/api/projects/<LWP-ID>/operations` | Auth+CSRF+exact Origin, strict `action,payload,idempotency_key,expected_fingerprint`; recheck action availability/fingerprint, `LocalWebService.submit`, asynchronous operation ID. No generic dispatcher |
| GET | `/api/projects/<LWP-ID>/artifacts/<LWO-ID>` | Auth+owner, только successful `prepare` + verified exact handoff ZIP bytes; без `?path`, arbitrary filesystem, preview executable HTML или shell |

**Никаких других HTTP mutations:** `register_existing()` остаётся trusted Python API, а не браузерная операция. `update-draft` уже поддержан backend service, но browser form ещё не написана и в UI disabled; CLI/service operation contracts при этом неизменны. Доступные пользовательские shell кнопки `check-intake`, `prepare`, `next`, `validate-project`, `verify` вызывают только уже существующий allowlist service через explicit confirmation и unique idempotency key; сохранённое ядро выполняет отдельную проверку. `verify` не получает consent на выполнение product commands из браузера. Все будущие процедуры импорта, GPT draft, approvals, сборки, complete, Stage Gate, maintenance, migration **disabled** со строковой причиной. `execute-current` никогда не активируется этим UI. Refresh/GET/polling не выполняют `check-intake`/`next`/`verify`/reconciliation или другие core mutations.

Ошибки возвращают `{"status":"FAILED","error":{"code":...,"message_ru":...,"next_action_ru":...}}` без HTML tracebacks, user paths или текстов исключений неизвестного происхождения. Mutation POST с чужим/пустым Origin, чужой session, missing CSRF, stale fingerprint, unknown fields, wrong project ID и конфликтным key отказывается до mutation. Ключи и filenames не превращаются в backend FS path; artifact resolver повторно проверяет membership, operation state, path, hardlink/symlink и immutable ZIP SHA. Лимит читаемых артефактов 128 MiB.

## 5. UI и порядок оператора

Девять экранов: Проекты/запуск, Документы, Опрос/GPT, Согласования, Обзор, Задачи/Run, Стадии/доказательства, Обслуживание, Диагностика. PH-LW-04 даёт **только оболочку** и список доверенно зарегистрированных проектов; обзор показывает текущий core status, stage, target, highest accepted, blockers и required next action. В каждой недоступной операции есть текст причины. Loading, empty, stale/error, result, клавиатурный focus и текстовый статус доступны без цветового кодирования. Работа с документами/GPT/approvals/forms будет добавляться в указанных следующих пакетах, не имитируется здесь. UI работает на статичных assets из wheel с CSP; нет Node/npm у оператора.

Операторская установка для разработки с доступным Python: сначала установить wheel, отдельно **подтверждённый** Local Web dependency lock, затем `project-harness ui`. При отсутствии pinned deps честный отказ, не fallback. Клиент отображает только snapshot; `available_actions` и expected revision перепроверяются сервером и kernel operation fence. Любые позитивные security утверждения о реальном Windows/Waitress/browser требуют отдельного фактического прогона скрипта `local_web/ci_ph_lw_04_windows.ps1` на Windows 11 x64 NTFS с настоящим Flask/Waitress, MS Edge Playwright browser и сохранённым transcript.

## 6. Тесты и незакрытая приёмка

`tests/test_ph_lw_04_http.py` содержит dependency-independent CSPRNG/session/socket/assets tests, Flask client security tests, реальный Waitress TCP/security tests, browser Playwright test с XSS-as-text/fragment/no-external-requests. При отсутствующих Flask/Waitress они **SKIP / NOT RUN**, не превращаются в PASS. Проверка Waitress test client сама по себе не доказывает WSGI body protection, а Linux listener test не доказывает Windows Session/NTFS. Windows launcher/installer, Windows browser session, LAN isolation и published wheel после доставки должны быть отдельно проверены; их статусы и известные blockers фиксирует `PH_LW_04_TEST_REPORT.md`. Исторические normative spec v0.5.0/v0.5.1, Stage Gate governance, accepted histories и PH-051 отчёты не редактировались.
