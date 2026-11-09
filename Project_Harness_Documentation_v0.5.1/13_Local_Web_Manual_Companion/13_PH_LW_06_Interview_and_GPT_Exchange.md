# PH-LW-06 — опрос и ручной GPT draft exchange

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-07  
**Companion:** 0.1.0-dev, build `PH-LW-06-20261107`  
**Область:** typed forms, actual questions/readiness, bounded export, strict JSON preview/commit/cancel/recovery. Formal approval forms PH-LW-07 не реализованы. Automatic executor выключен.

## Пользовательский маршрут

1. Запустить существующий `project-harness ui` с pinned Flask/Waitress. Создать Greenfield intake во вкладке «Документы», загрузить MD/ZIP либо явно выбрать «Документации нет».
2. Открыть «Опрос и GPT». Сначала документация, затем основной проверяемый результат и target, затем архитектура/технологии. Вопросы происходят из `questions_for` и `validate_project_input`, а не из поиска слов в документах. Known answers находятся отдельно, с provenance/refs; повторный вопрос появляется при gap либо смене source revision.
3. Ввести обычные строки, списки и enum choices. «Сохранить ответы» вызывает public `update_provisional_draft` через guarded service operation `update-draft`, с exact input digest/fingerprint. YAML не редактируется. Сложные структуры Technology/Task DAG заполняются через внешний semantic GPT exchange; общего schema editor нет.
4. «Проверить readiness» — явный защищённый POST `check-intake`. Он обновляет persisted `QUESTIONS`, `READINESS`, `STATE`, `SESSION`. GET интервью вычисляет актуальную проекцию без записи и также показывает persisted status. UNKNOWN connectivity/documentation/sensitivity и material `project.unknowns` блокируют readiness. `UNSURE` сохраняет `WAITING_DECISION`, даже если остаются другие missing fields; список пробелов не исчезает.
5. «Проверить состав пакета» показывает каждый документ, размер/hash, data sensitivity проекта и draft. Указать классификацию всех элементов и подтвердить право передачи без секретов. «Создать пакет» сохраняет его локально. Download и copy prompt выполняются отдельными явными действиями; автоматических clipboard writes, внешних запросов или ChatGPT browser automation нет.
6. Вручную передать pack внешнему GPT. Вставить один JSON reply, нажать «Проверить и показать diff». До commit canonical input не меняется. Просмотреть before/after, оставшиеся вопросы и invalidation receipt, затем применить как draft либо отменить import.
7. После применения остаются отдельные formal approvals. Этот этап не создаёт approvals, Stage acceptance, trusted evidence или executable Run. Test GPT reply в приёмке — явно синтетическая fixture, не реальное общение с моделью.

## Контракт обмена

Активный browser startup template — package resource `local_web/GPT_PREPARATION.md`. Он требует `PROJECT_INPUT@4`, pending/unapproved decisions и manual JSON return. Исторические `PROJECT_INPUT@3` документы и прежний CLI preparation template не переписаны; они не включаются в этот browser pack.

Envelope `LOCAL_WEB_GPT_DRAFT_ONLY@2` имеет отдельную schema `local_web/gpt_exchange_reply_v2.schema.json`; design artifact v1 сохранён. Core schema/registries остаются прежними. Обязательны `kind`, `envelope_version`, opaque `exchange_id`/`project_ref`, `export_revision`, `export_sha256`, `source_revision`, `source_snapshot_ref`, `source_inventory_sha256`, `input_revision`, полный `project_input_draft`, `questions`, `uncertainties`, `claims`.

`input_revision` — content-addressed revision: SHA-256 точных bytes `PROJECT_INPUT.yaml`, не приблизительный счётчик UI. Source binding содержит реальный snapshot/ref/revision и digest полной inventory; перед preview/commit/download проверяется также exact core fingerprint. `export_sha256` — SHA-256 canonical payload JSON (`ensure_ascii=False`, `sort_keys=True`, compact separators, LF). Он исключает собственное поле hash, чтобы не было цикла. Отдельные hashes в manifest покрывают полные bytes каждого скачиваемого MD файла.

Full draft сохраняет обязательную форму core schema, включая null/empty provisional fields. Missing properties, unknown fields и malformed nested records отклоняются; пустые provisional коллекции остаются readiness gaps, сервер не дополняет их вымышленными проектами. Изменяются только существующие allowlisted leaves `DRAFT_FIELDS`. Metadata, name/slug/mode, source identity, execution и approvals защищены. Выбранный пользователем target, включая `UNSURE`, GPT заменить не может; target меняется отдельным ответом формы.

Все импортированные approval records должны быть ровно `approved=false`, `actor=null`, `approved_at=null`, `notes=null`. Прежние approvals берутся только из текущего local input: при доказанно unchanged binding и unchanged semantic draft сохраняются, при material change атомарно сбрасываются public draft API. Receipt фиксирует before/after digests, причину и invalidated subjects. Его нельзя использовать как formal decision или цифровую подпись.

Каждое изменённое поле имеет `claims` с точными document refs из export inventory либо `INPUT`; пустой список обозначает необоснованное предложение. Можно явно reaffirm unchanged поле на новой source revision. Provenance сохраняет response digest, exchange ID, source revision и per-field value digest; она всегда `GPT_DRAFT_UNVERIFIED`. Смена источников помечает прежнюю claim как `SOURCE_CHANGED_REVIEW_REQUIRED`. Imported questions/uncertainties сохраняются в draft unknowns с `blocking=true`, если ещё отсутствуют.

Неверный reply не создаёт даже import receipt. Ответ содержит bounded repair prompt: exact schema paths/keywords либо безопасные semantic rule locations, без raw reply, документов, credentials или host environment. Импорт поддерживает JSON; YAML в этом browser route сознательно не поддерживается.

## Лимиты и политика передачи

| Ограничение | Реализованное поведение |
|---|---|
| Reply | 512 KiB UTF-8; глубина 24; до 30000 JSON nodes; duplicate keys/NaN/Infinity/overflow numbers reject |
| Export draft | До 256 KiB, чтобы оставалось место для reply envelope/claims |
| Полный pack | До 20 MiB вместе с schemas и template; превышение — явный отказ без обрезки |
| Части | Payload chunks до 256 KiB; малый pack — один `pack.md`; большой — `index.md` и последовательные `part-NNN.md`, count/order/byte hashes |
| Хранение | До 32 exports, 128 imports и 64 MiB private exchange storage на intake; при лимите сохраняются существующие записи |
| Классификация | Для каждого документа и draft явно разрешены только PUBLIC/INTERNAL + consent внешней передачи без секретов |
| Высокая sensitivity | CONFIDENTIAL/RESTRICTED/SECRET/REGULATED проект или классификация pack блокируют export в этой версии |
| Секреты | Дополнительный отказ при известных private-key/token/password patterns; это не полный DLP и не замена проверки человеком |

Набор передаётся целиком. Отбор/автоматическое обезличивание документов не выполняются: при запрещённых данных нужен отдельный разрешённый набор источников. Byte sizes не называются точным model context/token limit. Server ничего не отправляет, не открывает URL из документов и не исполняет содержащиеся в них инструкции, включая AGENTS.md. Markdown preview и GPT diff отображаются через textContent.

## Service и HTTP

Все endpoints требуют session. POST дополнительно требует exact Host/Origin/port, CSRF и запрет unknown wrapper fields; прежняя loopback/CSP policy сохраняется. Произвольного файлового или shell gateway нет.

| Метод и suffix после `/api/projects/<project_id>` | Public service operation |
|---|---|
| GET `/interview` | `get_interview`: actual draft/questions/readiness, provenance, сохранённые exports/import previews |
| GET `/gpt/export-review` | `get_export_review`: только описание состава/policy и review digest |
| POST `/gpt/exports` | `create_gpt_export`: exact review/fingerprint, classifications, consent, idempotency key |
| GET `/gpt/exports/<exchange_id>/<name>` | `read_gpt_export`: только зарегистрированная часть exact актуального export |
| POST `/gpt/replies/preview` | `preview_gpt_reply`: bounded text, fingerprint; valid preview сохраняется отдельно от canonical input |
| POST `/gpt/replies/<import_id>/commit` | `commit_gpt_reply`: exact preview digest и fingerprint |
| POST `/gpt/replies/<import_id>/cancel` | `cancel_gpt_reply`: только до commit |
| POST `/gpt/replies/recover` | `recover_gpt_reply`: explicit confirm, без нового исполнения draft mutation |

Typed answer updates и `check-intake` используют прежний `/operations` API. HTTP вызывает service, service берёт общий OS `project_operation_guard`, canonical input пишет только public draft API. Exchange files находятся в private sibling `exchange`, вне `.harness`, distribution и sources. Они не включаются в handoff.

## Reload, replay и crash

Reload читает сохранённые input/exports/previews. В sessionStorage остаются только выбранные opaque project ID и имя экрана; auth, raw reply и документы туда не записываются. Перезапуск сервера требует нового bootstrap, но не теряет draft/preview. Exact export idempotency key с другим request вызывает conflict; exact повтор committed response возвращает старый результат без второго изменения.

Перед canonical commit сохраняется checksummed intent с import/preview binding. Public API атомарно заменяет один `PROJECT_INPUT.yaml`; затем сохраняется COMMITTED receipt. После прерывания GET только сообщает `recovery_required`; новые service mutations блокируются. Явная сверка сравнивает source binding и before/after input digests: after → COMMITTED_RECOVERED; before → NOT_COMMITTED; постороннее изменение/повреждение → отказ без overwrite/автоповтора. Повтор уже committed import идемпотентен. Последующий `check-intake` — отдельная явная операция; статус GET всегда вычисляется из current draft.

Windows `os._exit` проверяет реальную остановку процесса и освобождение OS lock, а не power-loss durability. CLI, изменивший draft после crash, обнаруживается при recovery; его bytes не перезаписываются.

## Проверка и границы

Фактические counts, commands, platform/deps, exit, failures/skips и exact build hashes находятся в новых `PH_LW_06_TEST_REPORT.md` и `PH_LW_06_LOGS` в Engine. Targets: `tests.test_ph_lw_06_exchange`, `tests.test_ph_lw_06_http`; native runner: `local_web/ci_ph_lw_06_windows.ps1 -PythonExecutable <Python314> -LogDirectory <новый каталог> -SkipRegressions`, дополнительно отдельная regression matrix. TCP/Edge tests используют production Waitress, installed-wheel acceptance идёт из отдельной venv/CWD.

Рабочие files/evidence хранятся распакованными. По новому правилу пользователя от 2026-11-07 обязательное ZIP-требование архивного PH-LW prompt заменено; новые Engine/Documentation ZIP создаются только по отдельному явному запросу. Wheel, docs mirror, manifests и рабочие hashes всё равно синхронизируются. Прежние архивы/report NO-GO неизменны.

PH-LW-06 не закрывает PH-LW-07, installer/clean-machine acceptance или PH-LW-12. `LOCAL_WEB_MANUAL: NO-GO`, `AUTOMATIC_EXECUTOR: NO-GO`, полная v0.5.1: `NO-GO / NOT RELEASED`. Positive governed per-Run egress и реальный rootless Podman security run остаются отдельными незакрытыми gates.
