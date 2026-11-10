# Прямой локальный доступ без входа

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-09

## Решение пользователя и изменение контракта

2026-11-09 пользователь явно потребовал удалить весь функционал локального входа, формы и логику прав доступа. Требования PH-LW-04 к launcher bootstrap, session cookies и CSRF отменены для текущего интерфейса этим решением. Исторические prompts/specs/отчёты не переписываются и описывают прежнюю реализацию; их auth verdict не переносится на новую сборку.

В действующем runtime отсутствуют LocalWebAuth, session store/TTL, выдача одноразовых кодов, auth cookies, CSRF headers/checks, login/logout routes и формы входа/выхода. Открытие обычного адреса `http://127.0.0.1:<port>/` сразу показывает проекты. Обновление вкладки, новый браузерный контекст, очистка cookies и перезапуск сервера не требуют входа. Старые `/api/session`, `/api/session/bootstrap`, `/api/session/logout` удалены и возвращают 404.

## Запуск и завершение

Откройте «Project Harness» либо «Project Harness — разработка». Launcher открывает обычный loopback URL без fragment, query, кода и пароля. Если браузер не открылся, сообщение показывает только адрес: его можно открыть вручную. `--no-browser` запускает такой же доступный локальный интерфейс, но не открывает окно браузера.

Повторный запуск использует прежний SID mutex одного экземпляра и читает `launcher-instance.json` с PID и HTTP port. Проверяются форма записи, работающий процесс и ответ `/health`; отдельного auth socket, DPAPI-ключа или challenge-response больше нет. Это обнаружение адреса, не аутентификация. При штатном завершении удаляется собственная запись; старая `launcher-private.json` выводится из использования при запуске новой версии под instance lock.

Нажмите «Завершить Harness» для штатной остановки. Active mutations по-прежнему должны закончиться; POST stop не отменяет их и не завершает чужие процессы принудительно. Выбор проекта/экрана хранится как UI preference; browser sessionStorage не является входом или правом доступа.

## Что сохраняется

Listener остаётся только `127.0.0.1`. Exact Host/Origin/port и запрет cross-site/proxy запросов, CSP/no external assets, body/connection/time limits, строгие schemas, безопасный импорт MD/ZIP, root/artifact membership и read-only GET не меняются. Прямой локальный HTTP клиент может работать без cookies и токенов; mutation использует предусмотренный exact Origin и current revision/fingerprint/idempotency key.

Project Definition, Architecture, Technology и Codex Handoff approvals остаются отдельными решениями по содержанию проекта. Actor — запись о проектном решении, не пользовательский аккаунт. Правила Task/Run/Stage/Gate, independent verification, accepted history, recovery и manual handoff сохраняются. Automatic executor выключен.

Точные изменённые файлы, результаты новых no-login tests, применимых regressions и artifact hashes находятся в `_workspace/REMOVE_LOCAL_LOGIN_2026-11-09/REPORT.md` workspace. Отсутствие входа — запрошенный режим, не обещание авторизации локальных процессов. LAN listener, provider API и shell/filesystem gateway этим изменением не добавляются.
