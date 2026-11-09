# PH-LW-08 — подготовка и размещение Project Instance

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-07  

Дата: 2026-11-07. Additive Local Web `0.1.0-dev`, Engine `0.5.1` WIP. Фактические результаты находятся в `PH_LW_08_TEST_REPORT.md` и `PH_LW_08_LOGS` распакованного Engine. `LOCAL_WEB_MANUAL` остаётся `NO-GO` до PH-LW-12, `AUTOMATIC_EXECUTOR: NO-GO`, полная v0.5.1 `NO-GO / NOT RELEASED`.

## Порядок работы

1. Импортируйте MD либо ZIP, выполните опрос и ручной обмен draft с GPT.
2. Отдельно подтвердите Project Definition, Architecture, Technology, Codex Handoff; для Brownfield/Hybrid дополнительно нужен Brownfield Baseline. Все approvals должны соответствовать текущим источникам и draft.
3. Во вкладке «Согласования» введите имя **новой** папки в показанном каталоге и подтвердите размещение. По умолчанию это `%USERPROFILE%\HarnessProjects`. Нажмите «Собрать, проверить и разместить проект».
4. Мастер вызывает compiler, проверяет initial directory, initial ZIP и Project Instance, затем публикует каталог. Папку не нужно создавать заранее: даже пустой существующий каталог отклоняется.
5. После успеха показаны папка, active/target, exact Task/Run refs. «Копировать промпт» передаёт первый JIT в clipboard; при отказе браузера остаётся поле для выделения и Ctrl+C. «Открыть папку» открывает только зарегистрированный опубликованный каталог. «Экспортировать ZIP» скачивает исходный проверенный handoff.

Закрытие вкладки не останавливает worker. При возвращении вкладка читает сохранённый журнал. После сбоя процесса нажмите «Сверить и продолжить подготовку». Живой worker защищён общим OS fence: конкурентная сверка не начнёт вторую публикацию. Действия не запускают Codex, продуктовые команды, host fallback или automatic executor. Task/result/verify/complete UI относится к PH-LW-09 и этим этапом не добавлен.

На Windows краткий read handle от polling может мешать атомарной замене companion journal. Только запись preparation/operation receipt повторяется ограниченно (до 10 пауз по 50 мс); compiler, rename и core mutations этим механизмом не повторяются. Постоянная блокировка остаётся ошибкой и требует явного recovery; старый целый receipt сохраняется.

## API и границы данных

Архитектура: Browser → typed HTTP → `LocalWebService` / operation guard → `prepare_handoff`, validators и public `materialization` helpers → canonical Project Instance. Ни HTTP, ни JS, ни companion orchestration не редактируют `.harness` и не назначают core statuses.

| HTTP | Назначение |
|---|---|
| `GET /api/projects/{pid}/preparation` | Read-only предложение target либо durable progress; не compile/recover/validate |
| `POST …/preparation/target` | `folder_name`, `binding_digest`, `expected_fingerprint`, `confirm:true` |
| `POST …/preparation/start` | `target_id`, `binding_digest`, `expected_fingerprint`, `idempotency_key` |
| `POST …/preparation/recover` | Явная сверка/продолжение с `confirm:true` |
| `GET …/preparation/{operation_id}/prompt` | Только первый сохранённый JIT, bounded read и hash |
| `POST …/preparation/open-folder` | `confirm:true`; exact registered directory через `os.startfile(..., 'explore')` |
| `GET …/artifacts/{operation_id}` | Только immutable ZIP принадлежащей intake операции, bounded read и SHA-256 |

Все приватные reads/downloads требуют session; POST также требует exact Host/Origin/port и CSRF. Unknown/duplicate fields, raw path, traversal, ADS/device names, unsupported junction и чужие target/artifact IDs отклоняются. HTTP `operations/prepare` не обходит подтверждение target; generic `publish-project` POST также закрыт, используется отдельная typed форма. Прежний trusted Python `prepare` API PH-LW-03 сохраняется для совместимости и не является HTTP route публикации.

`LocalWebService(app_data, projects_directory=...)` позволяет доверенному локальному host выбрать другой корень проектов. Это Python configuration, не принимаемый из HTTP путь и не filesystem gateway. UI предлагает один настроенный корень; произвольный выбор диска через браузер не реализован. Staging всегда создаётся на volume назначения, поэтому переноса с app-data volume в product volume нет. Native publication в этой реализации поддерживается только на Windows; другие платформы явно отклоняются.

## Привязка, публикация и повторы

Target receipt и preparation record содержат workspace, input digest, source revision/inventory/live tree digest, exact companion approval receipt IDs и subject content, engine build digest и local web build ID. Перед compile и publication binding читается заново под shared workspace fence. `MANUAL_HANDOFF`/network `NONE` обязательны. Draft/source/approval mutations через service после начала публикации заблокированы; внешний CLI drift обнаруживается binding-проверкой, без изменения accepted history.

Новый staging — соседний `.harness-preparation-<random>` каталог с owner receipt. Compiler получает только ранее не существовавшие `project` и `handoff.zip` внутри него. Его разрушительная семантика `keep_directory` никогда не применяется к живому пользовательскому destination. Нет `force replace`, удаления либо слияния существующей папки.

Перед rename проходят `validate_handoff(directory)`, `validate_handoff(zip)`, `validate_project_directory(directory)` и сравнение всех файлов directory/ZIP. Сохраняются identity каталога (device/file ID), digest дерева, initial manifest, ZIP, accepted input и первого prompt. Непосредственно перед публикацией bytes/identity перепроверяются. Windows `os.rename` атомарно отказывает, если destination уже появился. Catalog commit выполняется лишь после реального rename и проверки опубликованного Project Instance.

Companion phases `INTENT → STAGING → COMPILING → VALIDATED → PUBLISHING → PUBLISHED → COMPLETE` — журнал подготовки, **не core Task/Run/Stage/Gate states**. Atomic records используют flush/fsync и replace. Повтор того же принятого input/target возвращает имеющуюся operation и проверенный результат. Другой target, input/source/approval/build или изменённый fingerprint target не считается replay. Idempotency key связан с action/payload/fingerprint.

При interruption после rename identity каталога позволяет отличить именно опубликованный результат от чужой папки. Catalog registration идемпотентна. Если compile оборвался до получения обоих outputs, явная сверка может создать новое staging (не более трёх повторов), сохранив все частичные каталоги. Полные outputs с проваленной semantic validation, неизвестный staging owner, tampered records или конфликтующий destination блокируют продолжение. Никакой cleanup пользовательских данных не выполняется.

Проверенные fault injection/process exits не равны физическому power-loss, disk-full либо отказу накопителя. Эти системные gates перечисляются отдельно в отчёте; подтверждение NTFS rename не является обещанием сохранности при любом аппаратном сбое.

## Первый JIT и проверки после изменения продукта

Compiler уже резервирует первый READY Task/Run/JIT. Orchestration читает `HANDOFF_RESULT.json` и canonical status; для показа кнопки `next` не вызывается. Tests дополнительно вызывают public `next_task` и сравнивают exact refs и bytes: это проверка core idempotency. Detailed Tasks/WP/JIT принадлежат active Stage; будущие Stage Plans до target остаются outlines. Accepted scope, evidence semantics и level sequence не меняются.

`validate_handoff` относится к immutable initial directory/ZIP. После product edits исходный manifest закономерно устаревает. Повтор/сверка опубликованного результата используют identity, accepted binding и **`validate_project_directory`**, не требуют совпадения изменяемого product tree с initial manifest. ZIP всегда остаётся исходным handoff и не является экспортом текущего продукта.

В product root копируется только существующая portable compiler структура с принятыми источниками. App catalog, owner/target/preparation receipts, raw uploads, auth/session, private logs и raw execution roots остаются снаружи. Initial ZIP сохраняется в owned staging как immutable artifact. Staging/abandoned artifacts автоматически не удаляются в этом этапе.

Для совместимости PH-LW-07 сохраняется историческое имя approval `next_action: PREPARATION_PENDING_PH_LW_08` и содержание ранее принятых subject receipts. Актуальный этап и фактическая публикация читаются из preparation namespace, а UI показывает действующую форму. Сохранение receipt не выдаётся за цифровую подпись.

Engine/Documentation ZIP этой работой не собираются. Product handoff ZIP создаётся compiler как обязательный runtime output PH-LW-08; это не архив поставки движка.
