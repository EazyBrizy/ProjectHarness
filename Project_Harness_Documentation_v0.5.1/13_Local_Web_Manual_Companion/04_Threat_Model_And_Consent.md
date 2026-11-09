# HTTP, ZIP, пути и границы доверия

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап подготовки:** PH-LW-01, 2026-11-01  
**Статус:** CONTRACT DESIGN / NOT IMPLEMENTED / NATIVE WINDOWS NOT RUN

## Границы угроз

Доверенные компоненты: локальный kernel/проверенные resource files и OS-user owner (но процессы того же user могут читать собственные файлы). Недоверенные компоненты: браузерное содержимое, файлы пользователя (в том числе MD и архивы), ZIP metadata, JSON ответа GPT, filenames, Agent Result, любые абсолютные пути/argv, результаты ручного Codex. Не считать локальный Web и same-user process isolation настоящим sandbox. Web server запрещено слушать `0.0.0.0`, IPv6 external, запускать debug/reloader либо открывать в сеть.

## HTTP политика, PH-LW-04

- Bind только `127.0.0.1` и действительный одноразовый port; launcher владеет instance nonce/verified PID. Не доверять существующему слушателю и не завершать произвольный process; second launcher должен безопасно отказать либо проверить свой instance.
- Startup bootstrap: криптостойкий одноразовый token передаётся в браузер через short-lived localhost link или локальный канал и немедленно обменивается на scoped HttpOnly `Secure` (когда HTTPS допустим), `SameSite=Strict` cookie; token не логировать, после exchange не сохранять в URL/browser history. Для loopback HTTP не утверждать, что `Secure` cookies работают на всех браузерах; предусмотреть проверяемую локальную cookie policy.
- Каждому запросу: строгое сравнение `Host=127.0.0.1:<current port>` (без доверия прокси/forward headers), Origin/Referer checks для mutations, anti-CSRF token binding в `POST`/form, content-type allowlist, no wildcard CORS, OPTIONS/DELETE blocked unless explicitly allowed. GET и polling только snapshot-read, без побочных effects.
- CSP `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:` при необходимом локальном preview (предпочтительно без внешних URL), `frame-ancestors 'none'`, `base-uri 'none'`, `form-action 'self'`; `X-Content-Type-Options:nosniff`, `Referrer-Policy:no-referrer`, `Cache-Control:no-store` для private data, JSON escaped, HTML untrusted text escaped, no inline scripts / external CDN or image fetch. Browser test обязан проверить content from hostile filename/MD/GPT.

## Предлагаемые executable budgets (только контракт, не реализованы)

| Resource | Limit | Enforcement (future) |
|---|---:|---|
| Один HTTP upload | 64 MiB | request body declared + streamed bytes, early reject |
| Один MD/document | 8 MiB | actual streamed bytes, not filename/Content-Length only |
| Распакованные MD суммарно | 128 MiB | actual expanded bytes; rollback partial import |
| Количество ZIP entries | 1000 | check central dir first then bounded streaming |
| Глубина nested directory | 16 segments | normalized paths, reject over limit |
| Compression ratio | 200:1 | compressed/uncompressed actual budget; reject bombs |
| Nested archive import | Запрещён | accept only MD leaves, no zip-in-zip recursive expansion |

## Безопасные пути (Windows NTFS)

Reject ZIP Slip (`..`), absolute/drive-relative paths (`C:foo`, `C:\\foo`, `/foo`), UNC (`\\\\server\\share`), `\\?\\` paths, NUL, control bytes, Unicode NFC/casefold collisions, Windows ADS (`:`), `CON/PRN/AUX/NUL/COM1..9/LPT1..9` с любой extension, reserved trailing dot/space, suspicious slash/backslash mixing, symlinks/hardlinks/junction/reparse points and special modes. Include ZIP encryption/CRC errors and file count/depth/ratio negative tests, no silent truncation. Path must resolve within a newly owned staging directory, disjoint from workspace/product; no generic file path/open shell APIs from Web.

## Consent и verification

`verify --allow-command-execution` выполняет возможные product test commands с полномочиями оператора на host. Сначала показать exact verification argv, cwd, declared write scope, toolchain prerequisite/risks; отдельный explicit consent с fingerprints на текущий Run, никакого автоматического process start из GET/GPT. Product-specific Python/Node/etc могут потребоваться — наличие frozen Python не доказывает availability of project SDK. Manual verification и UI не называются `SANDBOXED`. `execute-current` в companion disabled, `executor-doctor` только диагностический, неизвестная Podman safety = NOT RUN/NO-GO, host fallback запрещён.

## Уязвимости и границы будущих этапов

Будущие сценарии LW-E23–27, LW-E32 проверяют native browsers/OS, CSRF/clickjacking, ZIP/traversal, imports, session persistence. Этот PH-LW-01 зафиксировал правила, но не выполнил enforcement; не выдавать дизайн за положительный security test. Права одного OS-user не мешают malware тому же OS-user — это не изоляция.
