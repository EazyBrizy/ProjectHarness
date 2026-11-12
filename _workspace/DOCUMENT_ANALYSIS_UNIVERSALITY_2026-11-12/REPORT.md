# Универсальность работы с документацией

Дата: 2026-11-12. Build `DOC-ANALYSIS-UNIVERSAL-20261112` установлен, обычный desktop
shortcut обновлён. Данные и предыдущая версия сохранены. Найденные привязки
исправлены; это проверка текущего документального пути, не гарантия результата
модели на любом возможном входе.

| Область | Результат проверки и изменение |
|---|---|
| Импорт/ZIP/exact payload | Фиксированных четырёх файлов, имён исходного архива или ролей документов нет. Тексты и refs передаются по inventory. Проверены 1/2/3/6 документов, BOM, вложенность, произвольные Unicode names и обратный порядок ZIP entries. |
| Инструкция | Убраны пример Android-specific topic ID, привязка к прототипу и автоматическое отнесение тематических работ к будущему. Область, стек, зрелость, темы и план определяются источниками. Есть правила для действующих систем, миграции, исследований, непрограммных и неполных описаний, конфликтов и отсутствующего плана. |
| Обработка | Ключ текста больше не стирает значимые знаки/регистр: C/C++/C#, MB/Mb, x²/x2 и Unicode различаются. Повтор одной темы по stable id/тексту объединяется без потери разных решений. Похожие формулировки с разными id автоматически семантически не угадываются. |
| Ответы/UI | Структуры и enum берутся из canonical schema в read-only interview, без отдельного hardcoded technology template. Поддержаны refs, варианты string/object, списки/вложенные объекты, bool, number и null; значения не выбираются автоматически. Отсутствующий план явно показан. Перевод названий уровней ограничен соответствующим полем, literal API/build identifiers сохраняются. |
| Общие правила | Canonical fields/enums/refs/digests, bounded exchange, source/secret/policy/Host/Origin guards, mutable whitelist и readonly tools policy — общие контракты, не факты о предметной области. Они сохранены. |

Изменены только пять разрешённых source files: [scope](SCOPE.md),
[before/after hashes](CHANGED_FILE_HASHES.json). [Scan](RUNTIME_LITERAL_SCAN.json)
не нашёл исходных продуктовых имён/стека/ID в текущем local-web пути; сам поиск
литералов не заменяет семантические проверки. Исторические specs/prompts/reports
и legacy full-manual template сохранены. Последний не используется текущим
Local Web/CLI document packet; его общие engine contracts не переписаны.

## Целевая проверка

**7 уникальных методов PASS по scoped runs.** [Результаты](RESULTS.json),
[source probe](source-probe.run.json), [installed wheel](wheel-targeted.run.json),
[один focused retry](wheel-focused.run.json), [среда](ENVIRONMENT.json).
Первый source run: 3 PASS, включая 4 предметные области и реальный Edge/TCP.
Wheel run: 3 PASS / 1 FAIL — прежняя fixture заполняла поля по позиции; schema
передаётся JSON object и порядок ключей не является контрактом. Fixture переведена
на labels, semantic asserts технологии/версии сохранены. Runtime bytes не менялись;
повторён только этот failed case — PASS. Полный движок/core/PH-LW matrix не запускался.

Проверены exact texts/payload hashes, разные filenames/counts/порядок, изоляция
проектов, строгий preview без canonical commit, сохранение неизвестного target
и отсутствие подставленного стека, точные поля schema. В UI проверены создание
пользователя/компонента/критерия/технологии через общий editor, сохранение вложенных
значений, null/неизменённых списков, отсутствующий roadmap, enum из schema,
literal RELEASE в неподходящем для перевода контексте, inert HTML, отсутствие
JS errors/dialogs. Устаревший v2 unknowns/UNSURE/pending-approvals guard PASS.

## Реальный CLI отдельно от fixtures

Два синтетических входа, выбранная из native CLI catalog модель gpt-6-astra / low:

- Действующий сервис Go/PostgreSQL, 3 документа: 5 ответов, 2 этапа. CURRENT —
  миграция R7 с обязательным платёжным callback, FUTURE — дизайн R8. Подготовка
  intake не превратила существующую систему в разработку прототипа.
- Непрограммная заявка на выставку, 1 документ: 4 ответа, roadmap пустой.
  Фактический этап обозначен неизвестным, уточнение условий — рекомендация;
  программный стек не навязан.

[CLI results](NATIVE_CASES.json), [команда/log](native-cases.run.json),
[exact packet/source bindings](NATIVE_PACKET_BINDINGS.json). Runtime source и
prompt соответствуют финальным bytes; native runs выполнялись в source layout
до регенерации build metadata. Final metadata отличается как metadata сборки.
Raw JSON/inputs/result находятся в `_scratch/document_analysis_universality_20261112/`.
Это 2 model requests, не повторный разбор пользовательского проекта. Canonical
draft каждого case до/после одинаков, сохранено только PREVIEW; product writes,
Task executor и команды из документов не запускались.

## Артефакты и пределы

Docs validator PASS / 0 errors, ожидаемый WARN без delivery ZIP:
[результат](DOC_VALIDATION.json). Source/build/wheel/frozen equality, docs mirrors,
manifests, весь frozen payload включая .pyd, сохранение core/history и предыдущих
изменений: [integrity](INTEGRITY.json). Установка/данные/previous version,
--check-package/--doctor exit 0: [upgrade](OPERATOR_UPGRADE.json),
[shortcut](SHORTCUTS.json). Visible browser не открывался.

Source digest `sha256:1bedd12563c82f881e24888e3add198d0c349c8fbb6e6118881092fa86ca20fa`.
Wheel SHA-256 `9527fb6c973ebfb10268d76e24d3298bd23059c8d7680ae3eb0fb29ed3d267ed`.
UNSIGNED installer SHA-256 `e9bc3126d505fbe48ec311ff6dcb6a675bf0cd64c05e948e6601a1b3fba9225c`.
[Полный freeze](RUNTIME_FREEZE.json).

Универсальность касается содержания поддерживаемых **UTF-8 Markdown и ZIP с MD**.
PDF/DOCX/OCR, nested ZIP и снятие прежних limits/policy не добавлялись. Некоторое
описание может быть недостаточным или неприменимым для формального software
handoff Harness; это не основание придумывать детали. Формальная подготовка,
stage assignment, approvals и фактическая зрелость остаются отдельными.

Actual installed-EXE browser reacceptance NOT RUN; browser evidence — source и
independent installed wheel, installed EXE — byte equality/package/doctor.
Старые release verdicts сохраняют прежние exact-byte границы. AUTOMATIC_EXECUTOR
disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. Engine/Documentation ZIP,
commit/push и Git-index equality check незакоммиченной работы NOT RUN. Новая
working packaging anchor подготовлена для следующей публикации; предыдущая
uncommitted работа сохранена.

Следующий разрешённый шаг — открыть Harness прежним ярлыком и использовать
анализ для своего проекта; для нового результата повторить анализ. Другие этапы
и полную matrix самостоятельно не запускать.
