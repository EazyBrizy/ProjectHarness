# PH-LW-06 — Опрос и управляемый обмен с GPT без ручного YAML

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-06

UI вопросов/ответов, draft APIs, strict exchange schemas/templates, bounded pack exporter/importer, tests. Без provider API и автоматизации браузера ChatGPT.

Автоматизируй всю техническую часть подготовки, сохраняя внешнего GPT как семантического интервьюера. Сервер не должен выдавать распаковку или поиск ключевых слов за готовую архитектуру проекта.

### Требуется

1. Отобрази реальные `QUESTIONS`/readiness через service. Первый смысловой маршрут: наличие документации → основной результат → target до architecture/technology. Known facts показывай с source refs и не спрашивай заново без конфликта; UNKNOWN/material gaps остаются вопросами, UNSURE target остаётся WAITING_DECISION. Missing schema fields не подставляй выдуманными default проектами.
2. Формы сохраняют ответы через public draft-update API с expected revision; `check_intake` вызывается как mutation под guard. Пользователь не редактирует YAML. Покажи diff imported draft и текущих ответов до применения.
3. «Подготовить пакет для GPT»: server-generated TXT/MD-пакет и стартовый prompt с актуальным GPT_PREPARATION template, exact project/export ID, source snapshot digest/revisions, current draft/questions, target/scope constraints и strict return format. Небольшой комплект — один файл. Большой — явные части с оглавлением/count/hashes; ничего не обрезай молча и не называй pack size token estimate точным model limit.
4. Перед export показывай перечень документов, data sensitivity и предупреждение о ручной передаче внешней модели; секретные/неразрешённые данные не экспортируй в обход policy. Сам сервер не отправляет файлы/ключи наружу. «Копировать prompt» и download вызываются явным действием, автоматически в clipboard не писать.
5. Зафиксируй exchange envelope отдельной версии: opaque export/project IDs, input/source revision/digest и `PROJECT_INPUT@4` draft. JSON import обязателен; YAML только через уже поддержанную безопасную схему/парсер. Допустим paste текста в UI. Unknown fields, oversize/deep input, duplicate JSON keys, wrong project/export, stale response отклоняются до mutation.
6. Ответ GPT не может выставлять approvals, принимать Stage, добавлять trusted evidence, включать LOCAL_AUTOMATIC/egress, менять server paths/IDs или назначать actor. В template явно требуй pending/unapproved decisions; подделанные approved fields отвергай с понятным объяснением. Existing UI approvals сохраняются лишь при доказанно unchanged binding, иначе invalidated receipt; не доверять импортированной копии.
7. Содержательные claims сохраняй как draft с provenance, не как verified fact. После schema/readiness validation покажи остающиеся вопросы. Если ответ неверен, сформируй bounded repair prompt с exact errors, не отправляя случайно всё локальное окружение.
8. Обеспечь продолжение после reload/перезапуска, повтор того же ответа без дублирования и отмену import до commit. Убери устаревшие `PROJECT_INPUT@3` инструкции только из актуального browser startup route, не переписывай исторические отчёты.

### Приёмка

Два Greenfield сценария — MD/ZIP и «нет документации» — проходят typed forms/GPT draft exchange без ручного control-plane editing. Test GPT response — явная fixture, не объявляй это реальным общением с моделью. Stale/source-changed/approved:true/wrong-project/unknown-field cases не изменяют сессию; значимые unknowns не становятся READY_FOR_HANDOFF.
