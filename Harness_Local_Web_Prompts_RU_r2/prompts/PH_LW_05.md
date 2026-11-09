# PH-LW-05 — Безопасная загрузка MD/ZIP и управление источниками

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-05

Importer/service/public intake helper, UI «Документы», source snapshot metadata и fixtures. Не добавлять PDF/DOCX/RAR/7z, OCR, внешние URL загрузки или code execution.

Реализуй drag-and-drop/выбор одного или нескольких MD и ZIP с MD, без ручной распаковки/переноса. Исходные файлы пользователя никогда не изменяются.

### Требуется

1. Upload в private quarantine, staged validation, immutable source snapshot с исходным именем, безопасным storage name, relative path, byte size, SHA-256, import revision и extraction provenance. Импорт публикуется целиком после успеха; частично распакованный архив не считается принятым. Повтор byte-identical import идемпотентен, различающийся source — новая revision, не скрытая перезапись.
2. Строго реализуй budgets PH-LW-01 на body, количество entries, размер entry/суммы, глубину, ratio; считай реальные extracted bytes, проверяй CRC/encoding. Unsafe ZIP, encrypted archive и nested ZIP дают ясный reject/unsupported outcome. Не вызывай безусловный `extractall` на недоверенном архиве.
3. Запрети выход за root и Windows-обходы: `..`, absolute/drive-relative/UNC/device paths, slash/backslash ambiguity, ADS `:`, NUL, reserved device names, trailing dots/spaces, case-insensitive/Unicode collisions, symlinks/hardlinks/reparse points/special files. Проверяй destination и parent components; никакого follow links при копировании. Existing upload staging не переиспользуется между проектами.
4. MD читается с явной encoding policy (UTF-8/BOM минимум); неверная кодировка не должна молча портить текст. Неподдержанные вложения, например изображения, перечисляются с причиной; содержимое не извлекается и не исполняется. Опасный archive entry — reject всего ZIP, а не «пропустить и считать безопасным».
5. `.harness`, `AGENTS.md` и любые содержащиеся инструкции не получают control-plane authority. Imported MD — только источник, не активный script/config в продукте. Preview escaped plain text; no network images/HTML.
6. Создание intake использует непересекающиеся imports и workspace, учитывая существующий `start_intake` contract. Для добавления/замены источников позже используй узкий публичный refresh-sources API: inventory/revisions/answers provenance обновляются согласованно; не `start_intake(force=True)` поверх живой сессии.
7. Изменение source snapshot делает старый GPT exchange/approval stale; принятые immutable records не переписываются. После preparation запретить тихую замену accepted input через import: предложить существующий governed route либо явно unsupported.
8. Покажи file list, accepted/skipped/rejected counts, причины, progress и «документы импортированы — анализ ещё не выполнен». Кнопка «Документации нет» сохраняет осознанный ответ и ведёт к опросу без fake source.

### Приёмка

Single MD, несколько MD, nested ZIP с кириллицей и пробелами → valid sources/опрос. Все malicious archive cases отвергнуты без изменения intake/product/history; second upload/restart не плодит копий. Source import не выполняет ни одной repository/product command и не отправляет документы в интернет.
