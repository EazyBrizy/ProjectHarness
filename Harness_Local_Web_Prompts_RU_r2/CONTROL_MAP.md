# Карта визуальных элементов управления

**Назначение:** обязательный coverage checklist для PH-LW-01…12. Названия кнопок — проектируемый UX; команды/API в столбце «ядро» прочитаны из исходного `src/project_harness/cli.py`. Разработчик повторно проверяет их на актуальной базе. GET/mutation определяется фактическим поведением, не названием.

| № | Экран / действие | Существующая CLI-команда / Python API | Тип и пользовательское условие | Этап UI |
|---|---|---|---|---|
| 1 | Диагностика комплекта | `doctor` / `validation.doctor` | Явный diagnostic action; результаты без скрытого запуска agent | 04/11 |
| 2 | Новый проект | `start-intake` / `intake.start_intake` | POST; зарегистрированные disjoint root/source paths | 05 |
| 3 | Сохранить ответы / проверить готовность | `check-intake` / `intake.check_intake` | **Mutation**, не polling GET; pending approvals не автоодобрять | 06/07 |
| 4 | Подготовить проект | `prepare` / `compiler.prepare_handoff` | После действительных approvals; staging + no-clobber publish | 08 |
| 5 | Проверить исходный handoff | `validate-handoff` / `validation.validate_handoff` | Initial immutable handoff, отдельная диагностика | 08 |
| 6 | Проверить текущий проект | `validate-project` / `validation.validate_project_directory` | Mutable project validator, не old-manifest check | 09/10 |
| 7 | Обновить поддержанный проект | `migrate-project` / `migration.migrate_project` | Explicit confirmation, current version validation и сохранение истории | 10 |
| 8 | Обзор / текущая задача | `status` / `runtime.project_status` | Чистый read-only snapshot/projection; audit helpers for side effects | 04/09 |
| 9 | Следующее допустимое действие / Task | `next` / `runtime.next_task` | **POST**; может резервировать Run/JIT, не refresh | 09 |
| 10 | Готовность автоматического исполнителя | `executor-doctor` / `runtime.executor_doctor` | Explicit diagnostics; на unsupported Windows reason, не mock PASS | 04/10 |
| 11 | Автоматически исполнить текущую Task | `execute-current` / `runtime.execute_current` | В этом native manual выпуске **disabled** с причиной; не новый рабочий путь | 09/10 |
| 12 | Проверить результат | `verify` / `runtime.verify_current` | Mutation/evidence; host commands только с exact Run-bound consent | 09 |
| 13 | Завершить задачу | `complete` / `runtime.complete_current` | Текущий PASS/result/baseline, отдельный POST | 09 |
| 14 | Зафиксировать blocker | `block` / `runtime.block_current` | Reason/options, guarded POST | 09 |
| 15 | Возобновить Task | `resume` / `runtime.resume_blocked` | Exact blocker/resolution; не Stage Gate recovery | 09 |
| 16 | Состояние стадий | `stage-status` / `stages.stage_status` | Read-only projection; target/active/claim/observed/accepted раздельно | 10 |
| 17 | Подготовить Gate review | `prepare-stage-approval` / `stages.prepare_stage_approval` | Core не принимает Stage; output только в app-owned artifact area | 10 |
| 18 | Подготовить next-stage draft | `prepare-active-stage-plan` / `active_stage_planning.prepare_active_stage_plan` | Read-only относительно core, но создает draft file: explicit POST | 10 |
| 19 | Применить reviewed Stage plan | `plan-active-stage` / `active_stage_planning.plan_active_stage` | Exact context и material-change review | 10 |
| 20 | Перепроверить Gate после исправлений | `resume-stage-gate` / `stage_gate_lifecycle.resume_stage_gate` | Guarded recovery, не GET | 10 |
| 21 | Оценить исходный repository | `assess-maturity` / `stages.assess_maturity` | Product read-only, создаёт assessment records; не repository execution | 10 |
| 22 | Принять стадию | `accept-stage` / `stages.accept_stage` | Strict evidence + отдельный formal Stage approval | 10 |
| 23 | Повысить целевой уровень | `level-up` / `stages.level_up` | Explicit approval, ближайшая следующая Stage, no scope expansion | 10 |
| 24 | Начать обслуживание | `start-maintenance` / `maintenance.start_maintenance` | Exact same-level plan/approval | 10 |
| 25 | Отменить обслуживание | `cancel-maintenance` / `maintenance.cancel_maintenance` | Только existing allowed preconditions, formal approval | 10 |
| 26 | Создать учебный пример | `demo` / отдельный bounded demo service с existing fixture compiler | Новая отдельная папка; никогда не смешивать с реальным проектом | 11 |

`cli._demo` — private helper, не следует объявлять его публичным API. Для UI demo переиспользовать поддержанный compiler/fixture route через малый public wrapper; не создавать второй шаблон настоящего проекта из фиктивного demo input.

## Новые действия companion, не существующие команды базового ядра

| Действие | Правило |
|---|---|
| `project-harness ui` | Новый entrypoint этапа 04; не изменение имен старого CLI |
| Открыть существующий Project Instance | Явный root selection/registration, compatibility preflight, не migration по GET |
| Импорт MD/ZIP | Quarantine/limits/source provenance; только data files |
| Сохранить provisional draft | Public bounded intake helper, schema/revision/approval invalidation |
| Собрать пакет GPT | Exact source/input binding; пользователь видит состав; никакой внешней отправки |
| Импортировать ответ GPT | Draft-only, unknown/stale/malicious fields reject; не approval |
| Подтвердить intake subject | Реальная schema + versioned receipt; никакой цифровой подписи без реализации |
| Открыть папку / скачать artifact | Только зарегистрированный project/artifact; не arbitrary path execution |
| Импорт Agent Task Result | Strict schema/run binding, existing canonical channel invariants |
| Показать / экспортировать журнал | Bounded/redacted, no tokens/secrets; не полный host environment |
| Закрыть приложение | Safe drain; committed actions не rollback; явный эффект на active operation |

## Правило полноты

Каждая строка имеет test ID, working backend и UI action либо однозначный truthful disabled reason. Раздел «Дополнительно» допустим. Пустой placeholder экран не считается реализованным управлением. Ошибка в input не означает internal server failure. Disabled `execute-current` в native manual выпуске — сознательная capability boundary, а не незакрытая кнопка старта подготовки.
