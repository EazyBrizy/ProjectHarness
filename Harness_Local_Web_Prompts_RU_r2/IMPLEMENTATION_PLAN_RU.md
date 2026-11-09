# Harness Local Web — план Windows-first реализации

**Дата:** 2026-10-30. **Статус:** PROPOSED IMPLEMENTATION PLAN / NOT IMPLEMENTED.
**Идентификаторы:** PH-LW-01 … PH-LW-12. Это локальные work-package IDs, не новые уровни зрелости и не переименование PH-051.

## 0. Уточнение r2: что означает база PH-051-12

**Дата уточнения: 2026-11-01.** Речь идёт о WIP snapshots, собранных после попытки финальной приёмки, а не об успешно завершённой приёмке. `PH_051_12_TEST_REPORT.md` сохраняет решение **NO-GO**, полная v0.5.1 остаётся **NOT RELEASED**. Ни этот план, ни его выполнение не изменяют исторический отчёт.

Для PH-LW-01 допустима именно такая зафиксированная база разработки: точные Engine/Documentation hashes указаны в `SOURCES_AND_BASELINE.md`. Перед изменениями проверяются целостность и применимые regression tests. Неподтверждённые Windows-свойства проверяются в PH-LW-02/11/12, а не считаются доказанными исходными Linux-тестами.

Разработка manual companion не зависит от закрытия двух известных automatic blockers: реальной rootless Podman security acceptance и положительного governed per-Run egress. Они сохраняются в каждом отчёте отдельно. Обнаруженный дефект общих manual/preparation API, governance или сохранности данных, напротив, блокирует использующий его PH-LW до исправления в разрешённой области. Нельзя исключить такой дефект из приёмки под видом «это старый NO-GO».

Сначала можно выполнить PH-LW-01…12 для ручной подготовки, а отдельную нормативную приёмку automatic executor провести позже. Альтернативный порядок — сначала реализовать approved egress, провести фактическую Podman matrix и повторить PH-051-12; тогда новая пара архивов становится другой базой, её hashes и применимые тесты нужно зафиксировать заново. Не смешивать вручную файлы двух веток и не применять старые hashes к новой поставке.

Даже при будущем `LOCAL_WEB_MANUAL: GO` полный release v0.5.1 не становится GO автоматически. Согласованный scope этой серии — подготовка и ручное сопровождение через UI; ни egress, ни реальный Podman security run не подменяются интерфейсом.

## 1. Принятое для этого плана направление

Один Windows-запуск открывает локальный веб-мастер. Документы загружаются MD/ZIP; сервер выполняет безопасный импорт, хранит подготовительную сессию, организует обмен с внешним GPT, оформляет отдельные пользовательские согласования и сам собирает/размещает Project Instance. В интерфейсе доступны существующие ручные операции задач, проверки, Stage Gate, планирования, level-up, maintenance и migration.

Промпты можно передавать GPT/Codex вручную. Не требуется вручную распаковывать проекты, переносить служебные файлы, редактировать YAML или запускать внутренние команды. Не обещается автоматический смысловой анализ без внешнего GPT или AI-provider integration.

**Главный путь:** запуск → MD/ZIP или «нет документации» → подготовленный пакет GPT → импорт draft → отдельные согласования → автоматическая сборка и проверка → папка проекта и первый JIT → ручная передача Codex.

## 2. Выбранная архитектура

```text
Harness-Setup-win-x64.exe → Harness.exe
                             │
                    локальный браузер
                             │ same-origin, authenticated
                 HTTP 127.0.0.1:<выбранный порт>
                             │
                Flask + Waitress / Local Web
                             │
               application service / operation guard
                             │
            существующие публичные Python API Harness
                             │
          intake workspace либо canonical Project Instance
```

Python backend + Flask/Waitress и локальные HTML/CSS/JavaScript. Без React/Node/npm в пользовательском окружении, CDN, Electron, Docker, WSL или обязательного Podman для подготовки. Framework versions закрепляются при PH-LW-01. Waitress поддерживает Windows; development server Flask не подходит для пользовательской поставки (источники 1–2).

Статусы доставляются bounded polling; WebSocket, Redis/Celery и remote workers не нужны. Один локальный сервер обслуживает одного OS-пользователя. Поддерживаются несколько открытых вкладок, но ровно одна изменяющая операция на один проект. Нет совместного сетевого доступа и серверного управления другими компьютерами.

Core — единственный источник истинных Task/Run/Stage/Gate states. UI-проекции и журнал операций не могут объявить accepted/complete/PASS вопреки core. HTTP-обработчик не редактирует `.harness` напрямую. Отсутствующие небольшие операции provisional intake оформляются как публичные проверяемые Python API, а не набор разрозненных записей из маршрутов.

## 3. Windows и распределение ответственности

Целевая первая подтверждаемая платформа: Windows 11 x64, обычный пользователь, локальный NTFS. Это выбранная стартовая support matrix, не утверждение о тестировании. Windows 10/ARM64/macOS и сетевые/синхронизируемые project roots не объявляются поддержанными без отдельной проверки.

Нативные подготовка и manual lifecycle отделяются от Linux-only executor imports. Нельзя «исправить» `fcntl` фиктивной функцией или убрать locking. По текущему коду blockers существуют также в `__init__.py → runtime.py → apply.py`; Windows-работоспособность требует фактического теста, не только условного импорта.

Для поставки выбирается один путь: frozen Windows `onedir` bundle (PyInstaller) + per-user Windows installer, например Inno Setup с проверенной non-admin configuration. Runtime/dependencies/assets входят в поставку. Точный installer tool закрепляется в PH-LW-01 и не меняется произвольно посередине серии. PyInstaller build выполняется на Windows (источник 6).

Одна первая команда после получения установщика: `.\Harness-Setup-win-x64.exe`. При завершении установки открывается мастер; дальнейшие старты — ярлык или `Harness.exe`. Эти имена — проектируемые артефакты, не существующие команды базового Engine.

Нужные именно продукту SDK, интерпретаторы и toolchains — не зависимости оболочки. Подготовка не требует их установки. Проверка продуктовых команд позже показывает недостающую зависимость и не ставит ПО без согласия; frozen `sys.executable` нельзя выдавать за общий Python продукта.

## 4. Данные и каталоги

- Distribution: `%LOCALAPPDATA%\Programs\ProjectHarness\<build-id>` — только комплект приложения.
- Local Web state: `%LOCALAPPDATA%\ProjectHarness\` — project catalog, сессии, bounded operation journal, staging/imports/exports, несекретные настройки.
- Для каждого workspace: соседние, непересекающиеся каталоги `imports/<snapshot-id>` и `intake`. Это учитывает safety contract `start_intake`, запрещающий пересечение workspace с sources/repository.
- Product root по умолчанию: отдельная папка в `%USERPROFILE%\HarnessProjects\`. Другую локальную папку выбирают/подтверждают один раз; каталог уже существующего проекта не перезаписывается.
- `.harness` остаётся canonical project control. UI store вне product root и не влияет на product baseline, Stage target или evidence.
- Session/auth tokens, исходные temp uploads, raw execution roots и приватные logs не включаются в handoff/distribution.

Допустима stdlib SQLite только для локального каталога/операций; не для дублирования canonical Stage State. Хранилище должно быть проверяемо восстанавливаемым, без распределённой инфраструктуры.

## 5. Экраны и обязательный UX

1. **Проекты / запуск:** новый, открыть существующий, продолжить; версия и фактические capability checks.
2. **Документы:** MD/ZIP upload, перечень принятых/пропущенных файлов, причины, source revisions и provenance.
3. **Опрос:** текущие вопросы, известные ответы и источники, подготовка GPT-пакета, импорт ответа и ошибки.
4. **Согласования:** отдельные definition/baseline/architecture/technology/handoff decisions, просмотр точного содержимого и invalidation.
5. **Обзор проекта:** accepted scope, target/active/accepted levels, next action, blockers, дорожная карта.
6. **Задачи / текущий Run:** Work Packages, зависимости списком/таблицей, Task Contract, scope, JIT, импорт результата, verify/complete/block/resume.
7. **Стадии и доказательства:** Gate subjects, evidence kinds/refs/status, draft/review/accept, active-stage plan, level-up.
8. **Обслуживание:** maintenance, read-only Brownfield assessment, explicit migration, проверки проекта.
9. **Диагностика:** журнал операций, версии, docs, download reports, read-only автоматический executor readiness.

Сложные операции помещаются в «Дополнительно», но остаются достижимыми. Недоступная кнопка объясняет причину. Ни одного декоративного clickable action без backend operation и теста. Не нужен графический редактор DAG, IDE или терминал в браузере.

Каждый экран содержит: **что завершено / текущее состояние / что мешает / что требуется от пользователя / одно основное следующее действие**. Обязательны русский интерфейс, клавиатурная навигация, контраст/текст помимо цвета, loading/empty/error/stale/success states.

## 6. Подготовка и решения

MD/ZIP import означает только «файлы приняты», не «анализ завершён». Внешний GPT выполняет семантический анализ и опрос. Сервер детерминированно собирает ограниченный пакет с source IDs/hashes, текущими ответами, правилами и strict return contract. Перед экспортом показывается состав и чувствительность данных; сервер ничего не отправляет внешним сервисам.

Обратный ответ — draft-only envelope с exact export/project/source revisions и `PROJECT_INPUT@4`. `approved: true`, подменённые refs, смена execution mode и внедрённые локальные пути не становятся доверенными. Формальные подтверждения создаются только после отдельного осознанного действия в UI.

Greenfield — четыре отдельных подтверждения; Brownfield/Hybrid — пять, включая baseline. Intake approval использует фактическую input schema; Stage/level-up используют их существующие strict DEC/ACT contracts. Новый fingerprint/receipt оболочки не выдаётся за цифровую подпись или внешнюю проверку личности.

В этом выпуске UI создаёт новые проекты в `MANUAL_HANDOFF`. Автоматический executor показывается диагностически, но не включается этой серией. Его full release NO-GO, egress и реальные Podman tests не закрываются красивым интерфейсом.

## 7. Сервер и импорт: безопасность обязательна с начала

Listener только `127.0.0.1`, без LAN binding/proxy/tunnel. Одноразовый bootstrap для запуска браузера → session authentication; точные Host/Origin включая порт, CSRF и запрет cross-origin CORS; CSP, запрет framing, безопасный вывод текста/Markdown. Все приватные чтения, downloads и mutations требуют session authorization. Bootstrap не хранится в query/logs/localStorage; одноразовый URL fragment допустим только с немедленным удалением из history и обменом на сессию.

Установка браузерной сессии не даёт произвольного доступа ко всем файлам. Backend принимает opaque project/artifact IDs, проверяет принадлежность и путь. Нет generic `exec`, shell terminal, произвольной загрузки URL, файлового менеджера всего диска или передачи raw absolute paths в core из недоверенного JSON.

Загруженные документы и ответы GPT — данные, а не инструкции серверу; содержимое не исполняется и не назначается управляющим `AGENTS.md`. Raw HTML и внешние картинки в документах не активируются. Для первого выпуска достаточно безопасного text preview.

Предлагаемые исходные budgets: HTTP upload <=64 MiB, один документ <=8 MiB, суммарные extracted MD <=128 MiB, до 1000 entries, глубина <=16, ratio <=200:1. Это проектные defaults, не нормы исходного Engine; закрепить в PH-LW-01 и проверять реальные распакованные байты. Неподдержанные форматы показываются явно; опасный архив отвергается целиком. Вложенные архивы не распаковываются рекурсивно.

Учесть ZIP Slip, абсолютные/UNC/drive paths, `..`, backslashes, ADS, device names Windows, trailing dots/spaces, NUL/control chars, casefold/Unicode collisions, links/reparse points, oversized/CRC/encrypted ZIP. Источники хранятся отдельно от web static и final project.

Локальная оболочка не является sandbox от malware, работающего с теми же правами Windows-пользователя. Manual product verification по прежнему может запускать код на host только после отдельного точного consent; сервер не называет это SANDBOXED.

## 8. Повторы, фоновые операции и восстановление

Длительная локальная операция имеет persistent operation_id и bounded журнал. Браузер может закрыться без потери операции; это реальная функция приложения, не обещание ассистента выполнить работу позже. UI polling только читает. `check_intake`, `next`, verify, recovery и diagnostics с побочными эффектами вызываются через защищённый POST.

Idempotency key bound к action/project/request digest/expected revision. Тот же key с другим payload — conflict. Перед изменением проверяется актуальный fingerprint. Сериализация одного проекта должна работать между вкладками и процессами, включая публичный CLI, а не только frontend flag.

После interruption сначала сверить canonical core journal/result/refs. UI ledger не может повторять уже committed Stage acceptance, Run creation или completion. Незавершённые внешние команды автоматически не перезапускаются; неоднозначность блокируется с ясным действием. Commit нельзя «отменить» только потому, что browser request оборвался.

## 9. Версии, границы и поставка

Local Web — additive companion к выбранной базе. В метаданных явно разделить `engine_version`, `engine_build_digest`, `local_web_version`, `local_web_build_id`, `schema_version`. Не объявлять v0.5.1 released, не менять её нормативную спецификацию задним числом, не занимать roadmap v0.6.0/v0.8.0.

Предлагаемая версия companion: `0.1.0-dev` до PH-LW-12. Реальные source patches ядра отражаются в build digest/changelog. Engine registry/schema versions изменяются только при необходимом изменении нормативного core contract; UI DTOs имеют отдельный namespace/version и не подменяют canonical statuses.

На каждом этапе: два новых ZIP Engine/Documentation с суффиксом PH_LW_NN, changed files, test report, логи и SHA-256. После PH-LW-11 дополнительно реальный Windows installer, если он фактически собран. После PH-LW-12 два независимых verdicts: `LOCAL_WEB_MANUAL` и `AUTOMATIC_EXECUTOR`. GO первого не превращает NO-GO второго в PASS.

Вне scope: provider API и встроенный AI, удалённый control plane, мультипользовательские аккаунты, Git/PR/deployment, новые исполнители, Docker backend, автоматическая установка Podman/WSL, command terminal, универсальный редактор схем, поддержка PDF/DOCX/RAR/7z, общий auto-update service.

## 10. Порядок

| Этап | Область | Зависит от |
|---|---|---|
| PH-LW-01 | Точный контракт, карта действий, версия и test baseline | Зафиксированные WIP snapshots из попытки PH-051-12 с NO-GO; полный release GO не требуется для разработки companion |
| PH-LW-02 | Native Windows imports/manual core compatibility | 01 |
| PH-LW-03 | Application service, статус, concurrency, operation recovery | 02 |
| PH-LW-04 | Защищённый loopback server и UI shell | 03 |
| PH-LW-05 | Импорт MD/ZIP и source revision lifecycle | 04 |
| PH-LW-06 | Опрос, GPT exchange, draft validation | 05 |
| PH-LW-07 | Четыре/пять отдельных approval forms | 06 |
| PH-LW-08 | Автосборка и безопасное размещение Project Instance | 07 |
| PH-LW-09 | Текущая Task/JIT, manual results/verify/complete | 08 |
| PH-LW-10 | Stage/level-up/maintenance/Brownfield/migration controls | 09 |
| PH-LW-11 | Windows one-start launcher и offline installer | 10 |
| PH-LW-12 | Реальная Windows/browser/security acceptance и документация | 11 |

Начинать каждый этап с последней пары предыдущего этапа и её отчёта; различать проверки целостности, применимые тесты и release acceptance, не с самой большой/поздней по имени случайной ZIP. Набор промптов остаётся планом до фактической реализации и проверки.
