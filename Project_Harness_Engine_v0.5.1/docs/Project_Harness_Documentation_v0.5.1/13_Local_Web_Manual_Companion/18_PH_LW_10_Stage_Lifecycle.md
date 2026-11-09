# PH-LW-10 — Stage Gates, planning, level-up и обслуживание

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-07  

Дата реализации: 2026-11-07. Область — Local Web manual companion на проверенной базе PH-LW-09. Фактические verdicts и команды находятся в новом `PH_LW_10_TEST_REPORT.md` Engine; этот документ описывает интерфейс и контракт. Automatic executor остаётся выключен. PH-LW-11/12 этим этапом не выполняются.

## Уровни и история

Во вкладке «Стадии и доказательства» отдельно показаны target, active, claimed, observed и highest accepted. Current-cycle target читается из canonical Stage State, включая цикл после level-up. `PROJECT_INPUT_ACCEPTED` сохраняет историю и не заменяет текущий target.

Экран перечисляет обязательные semantic subjects, виды proof, exact evidence candidates, Plan/Gate refs/revisions/digests, baseline, constraints и реальные blockers. Read-only история acceptance, Run, Task reports и evidence содержит exact refs/digests. GET и polling не запускают подготовку, assessment, recovery или команды продукта.

## Review и acceptance

«Подготовить Stage review» вызывает `prepare_stage_approval` и сохраняет unsigned draft в отдельной app-data artifact directory. Draft привязан к project, fingerprint и operation ID. UI не записывает `.harness`.

Каждый outcome/criterion/profile control/constraint получает отдельные поля результата, rationale, validator и выбора evidence refs. Значения не подставляются массово как PASS. `UNKNOWN`, `PARTIAL`, `FAIL`, missing или несовместимый proof сохраняют реальный отказ. `NOT_APPLICABLE` требует существующего обоснования и validator. Permitted use, known limitations и next-stage gaps видны и редактируются в рамках существующего контракта.

Actor задаётся как `ACT-...`. Только отдельное подтверждение создаёт DEC, `approved_at`, `approved: true` и `record_state: APPROVED` по existing Stage schema; затем вызывается `accept_stage`. Imported JSON остаётся draft, не approval. Core проверяет semantic resolver, required work, immutable history и exact binding. App receipt не является цифровой подписью и не удостоверяет личность оператора.

`resume_stage_gate` — отдельная операция с пояснением missing subjects. Она не снимает обычный Task blocker. Недостающее evidence поставляется через существующие preparation Tasks и импортные contracts; универсального «upload = PASS» нет.

## План следующей Stage и level-up

`prepare_active_stage_plan` выдаёт draft только ближайшей active Stage. Форма показывает exact state/target/accepted scope/product baseline и позволяет review work packages/tasks, scope, dependencies, verification и documentation. `plan_active_stage` применяет strict reviewed plan и резервирует первый READY JIT без дубля.

Неизменённый work plan не требует несуществующего дополнительного Decision. Изменённый work plan требует отдельного rationale и существующего `ACTIVE_STAGE_PLAN_REVIEW` Decision с exact deterministic ID. Material scope divergence остаётся запрещённым этим planner: отдельный scope-change route не реализуется PH-LW-10.

Level-up показывает различие target/accepted и вызывает existing `level_up` после отдельного formal action. Новый target может быть выше на несколько уровней, но активируется только ближайшая следующая Stage; будущие детальные Tasks не создаются. `target <= accepted` возвращает `TARGET_ALREADY_REACHED` без mutation. Попытка пересоздать незавершённый target cycle отклоняется.

## Maintenance

Read-only `maintenance_draft` подставляет exact accepted level, target, last acceptance, scope и project-local IDs. Оператор заполняет цель, rationale, bounded Task scope, ожидаемый результат, verification и documentation. Подтверждение формирует existing strict `MAINTENANCE_PLAN`, затем `start_maintenance` запускает обычный manual Task lifecycle.

Команды verification здесь только планируются. Для их выполнения требуется отдельный Run-bound consent во вкладке «Задачи и Run». Manual checks требуют независимых observations и Task proof из PH-LW-09. Maturity не повышается, accepted history не заменяется.

Отмена получает отдельный exact `maintenance_cancel_approval` и вызывает `cancel_maintenance`. Core разрешает только допустимый pre-product-change route. Завершённые product-changing Tasks нельзя отменить этим действием; требуется completion либо governed compensation.

## Brownfield / Hybrid

«Выбрать существующий репозиторий…» открывает системное окно выбора папки. HTTP не принимает произвольный filesystem path или shell command. Новый intake и его source imports находятся отдельно от выбранного репозитория и product output. Существующий Harness instance открывается отдельным действием.

`assess_maturity` выполняется только после explicit POST. Repository inventory и текущий tree digest сверяются; stale repository отклоняется. Никакие repository commands не выполняются. Форма показывает exact assessment ref/revision/digest, claimed/observed/satisfied candidate и gaps. `README beta` не является maturity proof. Baseline approval остаётся отдельным действием существующей вкладки «Согласования»; новый Project Instance публикуется отдельно, исходная папка не перезаписывается.

## Migration

Поддержка source engine/schema определяется existing validator. План показывает validation errors, default `MANUAL_HANDOFF` и ограничения сохранения immutable input, completed Runs и Stage reports. Неподдержанный проект получает отказ без repair.

Для legacy v0.4.1 форма может передать только допустимое existing migration input: implementation fields и formal Brownfield baseline approval; core проверяет отсутствие иных изменений. v0.5.0→v0.5.1 не заменяет accepted input. `migrate_project` вызывается после отдельного подтверждения, использует existing transactional migration/replay. Ни migration, ни UI не активируют automatic mode.

Гарантии различаются по исходной версии. Existing v0.4.1 converter нормализует legacy `PROJECT_INPUT_ACCEPTED` в новый input contract и записывает `legacy_input_digest` в migration report; утверждение о побайтовой неизменности этого файла для v0.4.1 неверно. Completed Runs и исторические Task/WP revisions сохраняются. Для v0.5.0→v0.5.1 сохраняются exact bytes accepted input, completed Runs и Stage reports. UI не меняет эти правила и не приравнивает completed history к accepted maturity.

## Guard, replay и recovery

Все mutations проходят same-origin session/CSRF/Host/port checks и общий project operation fence. Новый запрос связан с expected fingerprint и idempotency key; одинаковый key с другим payload конфликтует. Draft привязан к владельцу, action и точному fingerprint. Unknown fields, stale refs и подменённые formal поля отклоняются.

При reload предыдущий GET может ещё удерживать read fence на сервере. UI ограниченно повторяет только GET с точным `OPERATION_CONFLICT` (до 12 раз с интервалом 250 ms); при сохранении конфликта показывает ошибку. POST никогда не повторяется этим механизмом. Backend guard и deadlines тестов не ослаблены.

Одновременные чтения одной approval form объединяются до завершения GET. Поздний дублирующий ответ не пересоздаёт поля и не сбрасывает отмеченный consent между действием оператора и отправкой POST. Это прямое исправление regression, выявленного прежним PH-LW-07 browser test; правила отдельных approvals не изменены.

После interruption UI не повторяет mutator. Для Stage acceptance/planning/level-up/maintenance сверка читает existing kernel transaction по exact reviewed-document digest. Подтверждённый commit отражается как commit; неоднозначный исход остаётся BLOCKED и требует core review. GET не восстанавливает и не перезапускает команды. Если migration journal остался после interruption, отдельное подтверждение вызывает core recovery даже при временно отсутствующей папке проекта. Fingerprint включает journal и участвующие деревья; default manual проверяется до вызова. Физическое отключение питания этим UI не моделируется как доказанное свойство.

Polling migration operation читает app-owned receipt по exact ownership и record digest, проверяя зарегистрированный путь и его ancestors. Он не перечисляет файлы canonical/backup tree, которые core может одновременно переименовывать или удалять. Canonical fingerprint/recovery snapshot по-прежнему проверяется перед mutation, отдельно от чтения статуса receipt.

Все previews и ошибки выводятся как текст, без HTML execution, внешних fetch/CDN/telemetry. История ограничена 1000 записями на категорию; превышение даёт явный отказ, а не ложную полноту. JSON import/export — дополнительный advanced путь; обычные действия доступны через schema-backed формы.

## Воспроизведение

Source: `tests.test_ph_lw_10_lifecycle`, `tests.test_ph_lw_10_http`, существующие PH-LW-04–09 и применимые PH-F/PH-051 suites. Windows runner: `local_web/ci_ph_lw_10_windows.ps1`. Installed wheel: отдельная venv и Unicode CWD с пустым source PYTHONPATH, `tools/verify_installed.py --ph-lw-10` вместе с флагами предыдущих этапов.

Native acceptance требует Windows 11 x64/NTFS/non-admin, Python 3.14 x64, pinned Flask/Waitress и реальный TCP/Edge. Test operator fixtures создают advanced states через public core flow; они не являются реальным Codex, Podman либо production certification. Engine/Documentation ZIP не создаются без явного запроса.
