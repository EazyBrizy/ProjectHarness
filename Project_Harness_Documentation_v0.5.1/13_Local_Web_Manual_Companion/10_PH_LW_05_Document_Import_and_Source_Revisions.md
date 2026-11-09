# PH-LW-05 — локальный импорт Markdown/ZIP и жизненный цикл источников

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап реализации:** PH-LW-05, 2026-11-04  

**Статус:** реализован отдельный этап PH-LW-05, **v0.5.1 WIP / NOT RELEASED**. Настоящий документ описывает проверенную на Linux Python-реализацию и недоказанные внешние свойства; не является Windows 11/Flask/Waitress/browser/Podman acceptance. Нормативные спецификации v0.5.0/v0.5.1 не изменялись. Automatic executor — NO-GO (rootless Podman security acceptance и governed positive per-Run egress остаются открыты).

## 1. Маршрут оператора

1. Запустить `project-harness ui` с закреплёнными optional dependencies `Flask==3.1.3`, `Waitress==3.0.2` через доверенную локальную сессию. **Нет** Flask dev server, удалённого binding, provider API или автоматического исполнения. Если HTTP-зависимостей нет, `ui` отказывается запускаться.
2. Во вкладке **Документы** ввести имя нового проекта и выбрать **«Создать intake для документов»**. Создаётся новый **GREENFIELD** `start_intake`, `mode=GREENFIELD`, в отдельном каталоге сессии, без `force=True`. Source imports и intake расположены в непересекающихся sibling-путях `.../session-*/imports/` и `.../session-*/intake/`. Полный путь не принимается из HTTP JSON. Новый Brownfield/Hybrid с локальным repository в UI этого этапа **UNSUPPORTED**; существующий ручной core API не меняется.
3. Перетащить или выбрать один/несколько `.md` / `.zip` файлов, `Добавить` или `Заменить весь набор`, затем отдельно подтвердить импорт. Пользовательские файлы не изменяются. После защищённого POST отображаются принятые/пропущенные/отклонённые элементы с причинами, прогресс **передачи** и ревизия источников. `100%` передачи не означает окончания серверной проверки; ответ `IMPORTED_NOT_ANALYZED` означает только успешный импорт, **не GPT-анализ и не formal approval**.
4. Список документов показывает исходное имя, относительный путь в ZIP, размер, SHA-256, revision, extraction provenance (ZIP entry, CRC, compression). Предпросмотр ограничен и выводится через DOM `textContent` как экранированный текст: HTML, JavaScript, Markdown links и внешние картинки не исполняются и не загружаются.
5. Кнопка **«Документации нет»** доступна при создании intake и отдельно при редактировании его источников. Это сознательный выбор пользователя, записывается `project.documentation.availability=NONE`, `normative_sources=[]`, источник не фабрикуется. После этого продолжать опрос — в PH-LW-06 будет отдельная форма GPT обмена; импорт сам не задаёт semantic answers.
6. Повтор побайтово идентичного источника в `append`, даже после перезапуска сервиса, возвращает `UNCHANGED` без копий или новой ревизии. Замена другого содержания выполняется явно в режиме `replace`, создаёт новую ревизию. Совпавшее имя с другими байтами в `append` — отказ `SOURCE_NAME_CHANGED_USE_REPLACE`.

## 2. Python API и строгие HTTP-контракты

Публичный `project_harness.intake.refresh_intake_sources(workspace, *, snapshot_ref, expected_revision, expected_input_digest, explicit_no_documentation=False)` вызывается только после подготовки/проверки отдельного source snapshot, **под общим `project_operation_guard`** и не использует `start_intake(force=True)`. Добавлены typed методы `LocalWebService`: `create_provisional_intake`, `upload_sources`, `list_sources`, `preview_source`, `select_no_documentation`, `recover_source_import`. Они не являются частью общего dispatcher для `next/verify/prepare`, не принимают raw absolute paths из HTTP.

Все HTTP-методы подчиняются прежним exact `Host`/Origin/session/CSRF security gate PH-LW-04:

| Метод и маршрут | Семантика |
|---|---|
| `POST /api/intakes` | Exact JSON `project_name`, `no_documentation` (bool), `idempotency_key`; только новый GREENFIELD/без пользовательских path; повтор key с другими данными reject |
| `GET /api/projects/<LWP-ID>/sources` | Read-only inventory, current snapshot/revision/status; private абсолютные пути и сырой workspace не выдаются |
| `POST /api/projects/<LWP-ID>/sources/upload` | `multipart/form-data`; **ровно** fields `mode=append\|replace`, `expected_fingerprint`, `expected_source_revision`, `files` (1–100), session/CSRF/Origin; ошибки и конфликт до mutation; никакого JSON с destination |
| `POST /api/projects/<LWP-ID>/sources/no-documentation` | Exact JSON `expected_fingerprint`,`expected_source_revision`; сознательное изменение выбора и source revision |
| `GET /api/projects/<LWP-ID>/documents/<LMD-ID>/preview` | Read-only, владелец и immutable SHA проверяются, bounded plain text JSON |
| `POST /api/projects/<LWP-ID>/sources/recover` | Exact JSON `{ "confirm": true }`; **явная** восстановительная операция после interrupted transaction, не GET/poll |

Существующие PH-LW-04 маршруты/права сохраняются. Создание intake и upload пока являются синхронными bounded POST с серверной проверкой. Прогресс в браузере относится к передаче байтов; очередь PH-LW-03 для иных операций остаётся прежней. Незавершённый импорт при GET даёт безопасный `SOURCE_RECOVERY_REQUIRED` без скрытых изменений.

## 3. Файлы, границы доверия и версионирование

- Upload поток сначала записывается в приватный уникальный `imports/quarantine/upload-*`. Только после полной проверки источник попадает в immutable `imports/snapshots/LWS-*/` с manifest и SHA-256 исходного файла, отдельным safe storage name, byte size, relative source path и extraction provenance. Неудачная загрузка удаляет temporary quarantine и не меняет canonical intake; опубликованные раньше snapshot не перезаписываются.
- `imports/state.json` — service ledger `revision`, `active_snapshot`, `snapshot_digest`, `documentation_choice`, `analysis_status=NOT_ANALYZED`. Engine intake остаётся canonical для опроса; журнал приложения не может повышать `approval`/Stage. Новый public refresh согласованно обновляет `SOURCE_INVENTORY`, `PROJECT_INPUT` (availability и reset approvals), `QUESTIONS`, `READINESS`, `SESSION` revision и `STATE` source revision/проверка provenance; ранее внесённые ответы требуют явного semantic review.
- Безопасный refresh создаёт private backup/staged write-set, durable `imports/pending.json` перед первым canonical replace; при ошибке выполняется rollback; после crash доступно явное восстановление `recover_source_import` (all-old или проверенный all-new). Ни `get-status`, ни polling не исправляют files автоматически.
- При `prepare` `RUNNING/SUCCEEDED/BLOCKED` в журнале этого service импорт блокируется: `SOURCE_REFRESH_AFTER_PREPARE_UNSUPPORTED`. Already-accepted `PROJECT_INPUT_ACCEPTED`, Stage Acceptance Reports и completed Runs не переписываются. Для accepted Project Instance upload запрещён. Если внешняя CLI-сборка была выполнена вне service и без записи о ней в workspace, service не может вывести этот факт из одного intake: оператор обязан использовать governed route, а не подменять принятые артефакты.
- Источники **UNTRUSTED_PROJECT_DATA**. `.harness` и `AGENTS.md` внутри ZIP не становятся control plane; такие archive entries не импортируются, имеют reason. Остальные инструкции в импортированных MD рассматриваются только как текст данных. Нет сетевых запросов, shell, repo commands, исполнения из источника или загрузки внешних URL.

## 4. Budgets / ZIP safety

| Контроль | Значение / действие |
|---|---|
| HTTP body (включая multipart) | `<=64 MiB` (Waitress, Flask, app-side) |
| MD или отдельная ZIP entry | `<=8 MiB`, actual decoded bytes |
| Общий распакованный объём и набор MD | `<=128 MiB`; measured stream bytes, не только headers |
| Число ZIP entries | `<=1000` |
| Глубина архива | `<=16` components |
| Compression ratio | `<=200:1` per entry |
| Encoding | Только strict UTF-8, UTF-8 BOM; invalid decode = reject |
| Path | Запрет `..`, absolute, UNC/device/drive-relative, slash/backslash ambiguity, ADS, NUL/control, Windows reserved devices, trailing dot/space, Unicode NFKC+casefold collisions, file-as-parent |
| Type | Reject links, FIFO/special/reparse, encrypted ZIP, nested `.zip`, inconsistent local header, invalid CRC/compression; никакого `ZipFile.extractall` |
| Unsupported ZIP entries | Файлы типа `.png` не извлекаются, но stream/CRC проверяется, reason `UNSUPPORTED_ATTACHMENT_ONLY_MD`; dangerous entry отклоняет **весь** архив |

Фактическая Windows NTFS защита от всех ссылок/reparse races и WSGI body limits требуют отдельного native security прогона; тесты путей на Linux — только детерминированные структурные проверки. Local Web не является ОС-сэндбоксом для вредоносного кода с теми же правами пользователя.

## 5. Тесты и недоказанные критерии

- `tests/test_ph_lw_05_import.py`: MD/ZIP Unicode/space, no-doc, multi-upload, immutable SHA/revisions, idempotent restart, false normative authority, stale/fingerprint, prepare fence, CRC/encoding/path/collision/link/bomb, rollback + explicit interrupted recovery, no shell invocation.
- `tests/test_ph_lw_05_http.py`: real Flask multipart+session/CSRF/Host/Origin, bounded preview, reject and no-doc. В среде без Flask тесты возвращают `SKIP` и должны быть отмечены `NOT RUN`, а не PASS.
- `local_web/ci_ph_lw_05_windows.ps1`: воспроизводимая команда для реального Windows 11 x64/NTFS/Edge; скрипт **не исполнялся** в Linux. PH-LW-04 external HTTP/browser и PH-051-12 Podman/egress blockers остаются открытыми. Пока эти обязательные проверки не выполнены, verdict только **WIP / NO-GO** для release, а не условно успешная Windows acceptance.
