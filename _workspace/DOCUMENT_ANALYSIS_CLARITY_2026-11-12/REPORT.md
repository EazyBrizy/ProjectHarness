# Результат анализа документов и явная модель CLI

Дата: 2026-11-12. Build `DOC-ANALYSIS-CLARITY2-20261112` установлен по стандартному пути;
обычный ярлык обновлён. Данные и предыдущие версии сохранены.

Исправлена причина прежних дублей: инструкция требовала одни вопросы в трёх
каналах, обработчик объединял их по точному тексту и делал любую строку blocker.
В новом local-web v3 один канал questions с устойчивыми id, field, объяснением,
источниками, текущим/будущим этапом. Дубли id/нормализованного текста объединяются;
противоречивые scope/blocking, notes вместо вопросов и future blockers отклоняются.
Существующие пользовательские unknowns сохраняются до явного решения пользователя.
Семантически разные формулировки с разными id не угадываются алгоритмом: за один
id независимой темы отвечает новая инструкция. История v2 не переписана.

Analysis хранит суть проекта, ответы с происхождением и статусом
описано/предложение/противоречие, ближайший рекомендуемый этап и roadmap с шагами
и критериями готовности. Будущие этапы/вопросы свёрнуты. Этот обзор не назначает
Stage и не выдаётся за утверждённые executable Tasks/JIT. Формальные пробелы
Harness показаны отдельно. Версии/цены/масштаб и утверждения не выдумываются.

PREVIEW больше не сопровождается старой пустой анкетой или ожиданием ответа.
Видно, что предложения ещё не сохранены; после сохранения показываются вопросы
с полным текстом и основанием. Структурированное редактирование сохраняет имя,
потребность, обоснование и другие поля; у технологий/версий есть обычная форма.
Разрешение вопроса — явное действие сохранения, без отдельного confirmation.
Raw refs/digests/JSON остаются в технических details, canonical values не меняются.

В карточке CLI есть выбор модели и глубины. Каталог получает явный connect POST
через native `codex debug models`; GET читает cache. Выбор проверяется по каталогу,
сохраняется и передаётся фиксированными `--model` / `model_reasoning_effort`.
Job хранит запрошенные параметры этого запуска. Новая настройка не меняет старый
job и не вызывает повторный запуск при replay. У исторических jobs модель честно
неизвестна; server-side alias resolution не заявляется измеренным. Фиксированный
read-only invocation, выключенные tools/apps/plugins/web, process limits,
strict preview/bindings/revisions/approvals и отсутствие product writes сохранены.
Каталог CLI experimental, проверен на native 0.154.0; доступ аккаунта не обещается.
Параметры сверены с [OpenAI Docs CLI reference](https://learn.chatgpt.com/docs/cli/reference)
и [config reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Проверка на исходном проблемном случае

Все четыре MD пользователя переданы целиком в отдельной scratch рабочей области.
Первый реальный ответ отклонён strict validator: включённый registry содержал key,
но не точный profile.ref. Добавлены exact allowed_refs из public registry API,
без изменения registry или ослабления validator. Повторён только неудачный case:
**PASS**, gpt-6-astra / medium, 14 содержательных ответов, 8 этапов, 2 текущих
решения и 13 будущих. Future blocking=false. Главные сведения о сценариях,
Flutter/Dart/SQLite, ограничениях, архитектуре и порядке модулей сохранены;
неизвестные версии не превращены в «стек неизвестен». Source business texts и
полные результаты остаются приватно в `_scratch/document_analysis_clarity_20261112/`.
Рабочий проект пользователя и его черновик не изменены этой проверкой.
[Первый результат](NATIVE_CASE.json), [повтор](NATIVE_CASE02.json),
[команда/log](native-case02.run.json), [UI actual result](NATIVE_UI.json).
Снимки реального ответа просмотрены; canonical inventory до/после UI одинаков.

## Только целевые проверки

**16 уникальных unittest methods PASS**, без полного движка/core/PH-LW matrix:
[matrix и причины focused повторов](FINAL_RESULTS.json), [первый run](WHEEL_RESULTS.json),
[focused](wheel-focused.run.json), [новая форма технологий](wheel-technology.run.json),
[структура объектов](wheel-typed-final.run.json), [v2 roundtrip](wheel-legacy-v2.run.json),
[ручной ZIP](wheel-archive-final.run.json). Среда — [ENVIRONMENT.json](ENVIRONMENT.json).
Первая matrix: 13 PASS; позднее повторялись только изменённые зависимости и новые
cases. Model requests 2 (первый rejected, второй PASS), не на каждом прогоне tests.

Проверены v3 dedupe/scope/notes/source refs/bindings/approval-forgery отказ,
PREVIEW без commit, commit/reload/provenance, сохранение пользовательских unknowns,
отсутствие блокировки future, model/effort/argv/snapshot/replay, cache recovery,
Origin/unknown fields, busy/cancel/stale/restart, ручной ZIP и структура ответа,
real TCP/headless Edge, понятные статусы, ввод/сохранение typed objects и версий,
отсутствие JS errors/dialogs. Существующий v2 documented/no-doc roundtrip PASS.

При финальной сверке исправлена старая v2 ссылка в отдельной ИНСТРУКЦИЯ.md
ручного ZIP: версия теперь берётся из exact skeleton. Повторён только archive
case. Первый candidate build/его проверка сохранены отдельно; итоговый build2
установлен новым version directory. Повторного model analysis для этой строки нет.

Docs validator: первый FAIL из-за отсутствующего metadata header новой главы;
исправлен только header, итог PASS / 0 errors / ожидаемый WARN без delivery ZIP:
[итог](DOC_VALIDATION_FINAL.json). Source/build/wheel/frozen equality,
полный frozen payload включая .pyd, docs mirrors/manifests, core/history preservation:
[integrity](INTEGRITY_FINAL.json). [Upgrade](OPERATOR_UPGRADE_FINAL.json),
[ярлыки](SHORTCUTS_FINAL.json). Старый процесс остановлен public stop без force kill;
данные до/после install одинаковы, previous version сохранена, package/doctor exit 0.

## Точные артефакты и границы

Source digest `sha256:2631abd3e35688bf80eb71186197e48466bdcc2c5faf04efa50a9c6bb6f105ad`.
Wheel SHA-256 `277ce9df1bdf2265236b8bf0fec008a6c098b2e962eb4c7ae25b91676330ba47`.
UNSIGNED installer SHA-256 `08a58a639ff5fa9ac783737cdcb8c5e80903ebd119bdab8c155a68c0a5674357`.
[Полный freeze](RUNTIME_FREEZE_FINAL.json), [изменённые hashes](CHANGED_FILE_HASHES.json).
В финале относительно успешного native case менялись только UI и версия инструкции
архива, не prompt/model argv/normalization. Побайтовые границы описаны в evidence.

Actual installed-EXE browser reacceptance, full engine/core/PH-LW matrix NOT RUN.
Браузерная проверка — independent installed wheel, installed EXE — package/doctor
и полная идентичность bytes. Старые verdicts не расширяются на новые bytes.
AUTOMATIC_EXECUTOR disabled / прежний NO-GO; full v0.5.1 NOT RELEASED.
Engine/Documentation delivery ZIP, commit/push не выполнялись. User documents,
auth/connection/jobs/caches не добавлены в Git. Git index equality check не запускался
как требование незакоммиченной правки; current packaging anchor обновлён для будущей
публикации. Лимит native analysis остаётся прежним 300 секунд; проверенный разбор
занял около 266 секунд. Более глубокие режимы могут потребовать ручного пакета.

Следующий разрешённый шаг: запустить обычный ярлык, открыть «Опрос и GPT», обновить
подключение (кнопка «Подключено»), выбрать модель/глубину и повторить анализ в рабочем
проекте. Затем «Сохранить предложения». Новые результаты не заменяют старые сами.
Другие этапы и Task executor не включать самостоятельно.
