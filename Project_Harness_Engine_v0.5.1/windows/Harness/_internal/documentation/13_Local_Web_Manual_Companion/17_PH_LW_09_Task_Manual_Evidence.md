# PH-LW-09 — Task-level manual evidence intake

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-07  

Дата: 2026-11-07. Дополнение реализовано по отдельному заданию пользователя после первого PH-LW-09 NO-GO. Старый отчёт и evidence сохранены. Актуальная повторная приёмка: `PH_LW_09_MANUAL_EVIDENCE_TEST_REPORT.md` в Engine. Automatic executor выключен; PH-LW-10 не входит в это дополнение. Полная v0.5.1 остаётся NOT RELEASED.

## Назначение и полномочия

`allow_manual:true` разрешает ручной review, но не подтверждает его выполнение. Оператор отдельно проверяет каждый `manual_checks` текущей Task, выбирает просмотренные product files, записывает observation и PASS либо FAIL. Reviewer и явное подтверждение обязательны. Agent Task Result, GPT-текст, exit0, command consent и последующие Stage approvals не заменяют это evidence.

Это новый bounded public intake для Task, разрешённый текущим заданием. Normative specs, core schemas/registries и planner не изменены. Используется существующий normalized `REVIEW_RECORD` с `task_ref`, `run_ref`, source binding на kernel receipt и runtime-only `profile_control_refs:[RUNTIME_TASK_MANUAL_REVIEW]`. Criterion/outcome mappings пусты; `semantic_proof` отсутствует. Запись не принимается как Stage criterion proof и не заменяет Stage approvals. Проверка нормализованного evidence и его immutable storage использует существующий core contract.

Manual evidence является явным утверждением ответственного локального оператора о проверке, а не криптографическим удостоверением личности и не автоматическим доказательством истинности observation. Engine проверяет полноту, exact binding, неизменность bytes и источников; качество предметного review остаётся ответственностью reviewer. Он должен прочитать источники и выполнить применимые независимые проверки. Нельзя импортировать заявление агента и подтвердить его без собственного review.

## Публичный формат и API

`task_manual_evidence.manual_evidence_context(root)` — read-only. Возвращает `binding`, product paths/digests и текущий manual gate. `binding` содержит `schema_version:1`, `record_kind:TASK_MANUAL_EVIDENCE`, exact `task_ref`, `run_ref`, `binding_digest`, `plan_digest`, ordered `checks` (тексты). Binding включает Run snapshot ref/hash и текущий product tree digest; plan digest включает verification commands/cwd/timeout, expected paths и manual checks.

`record_manual_evidence(root, document, confirmed=True)` — kernel mutation под project operation guard. `document` содержит ровно поля binding, `reviewer` и `checks`, где каждый элемент имеет ровно:

```json
{"index":0,"check":"точный текст из binding.checks[0]","status":"PASS","observation":"что и как проверено, фактический результат и границы review","sources":[{"path":"README.md","sha256":"sha256:<64 lowercase hex>"}]}
```

Все checks обязательны, в точном порядке и без повторов/пропусков. Разрешены только PASS и FAIL; NOT_APPLICABLE и permission flags не повышают gate. Sources — только существующие product files из current context с точным digest. Control-plane paths, arbitrary filesystem paths, missing/changed files и чужие refs отклоняются. Paths — ключи canonical product snapshot; HTTP не читает произвольные файлы.

Лимиты: JSON до 256 KiB UTF-8, strict duplicate-key/nonfinite rejection; до 100 checks по 4000 символов, reviewer 1–200 символов, observation 1–4000, 1–32 уникальных sources на check. Пустые observations и unknown fields запрещены. `confirmed` — только boolean true, отдельный от command consent.

## Операторский путь

В «Задачи и Run» откройте «Manual checks: независимое review оператора». Для каждого пункта выполните review, выберите источники, укажите observation и результат; укажите reviewer и отдельное подтверждение. «Сохранить manual evidence» вызывает защищённый POST action `manual-evidence` с payload `{document,confirmed}` через существующий operation journal/fingerprint/idempotency. Session, exact Host/Origin/port, CSRF и concurrency fence обязательны. Текст инертен, внешние fetch/команды отсутствуют. Поля и confirmation не заполняются из Agent Result; после операции consent сбрасывается.

CLI предоставляет `task-manual-context --project <root>` и `record-task-manual-evidence --project <root> --input <review.json> --confirm`. CLI читает bounded strict JSON; receipt всегда создаёт kernel. Вставлять файлы в `.harness` вручную не требуется. Python API поддерживает тот же путь для инструментов локального оператора.

После intake результат `MANUAL_EVIDENCE_RECEIVED` ещё не independent verification PASS. Выполните «Проверить», отдельно разрешив точные product commands, когда это необходимо. Runtime вновь проверяет current proof после команд; изменившийся продукт делает manual gate BLOCKED. FAIL observation даёт manual gate FAIL. Completion требует последнего PASS report, текущих result/product digests и того же exact manual evidence. Intake не запускает команды, не завершает Task и не принимает Stage.

## Immutable history, replay и recovery

Один immutable review на Run. Kernel записывает `.harness/runtime/TASK_MANUAL_EVIDENCE/<exact-run>.json`, затем normalized `.harness/evidence/EVD-MANUAL-<run-token>.yaml` и sealing phase boundary. Evidence Ref включается в verification report и completed Run/Task report. Все source bindings проверяются; product edits, новый Run, changed plan/task/checks не наследуют proof.

Точный повтор того же document возвращает прежний ref без новых файлов/evidence. Изменённый повтор отклоняется; для исправленного продукта/review используйте block/resume и новый Run. Старая verification остаётся immutable; после intake требуется новая verification, предыдущий BLOCKED report не переписывается.

При прерывании между receipt/evidence/sealing частичные файлы сохраняются, control check блокирует продолжение. Неоднозначная операция не воспроизводит команды автоматически; используйте canonical диагностику/recovery. Fault injection проверяет этот fail-closed путь; это не physical power-loss acceptance. Чтение формы/GET/polling не создаёт evidence и не меняет Task/Run states.

## PH-F06 regression

Fixture теперь сначала получает BLOCKED без manual proof, затем независимый TEST reviewer запускает реальные product tests, читает README/CLI/test sources и передаёт observation и digests через public CLI intake. Только после этого verify должен дать PASS. Прежние 13 test methods и их assertions сохранены. Stage-specific sources и отдельные approvals остаются последующим самостоятельным шагом. Это bounded fixture evidence; оно не удостоверяет реальный Codex/Podman или готовность продукта к production.
