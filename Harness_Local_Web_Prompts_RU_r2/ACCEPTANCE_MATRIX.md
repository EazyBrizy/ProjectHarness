# Финальная acceptance matrix Windows Local Web

**Статус всех сценариев на дату создания плана: PLANNED / NOT RUN.** Таблица задаёт проверки будущей реализации. Наличие теста или fixture не означает прохождение. Итог PH-LW-12 заполняется реальными log/result refs и platform/build IDs.

| ID | Проверка | Обязательный наблюдаемый итог | Основные этапы |
|---|---|---|---|
| LW-E01 | Чистая Windows 11 x64, non-admin, нет Python/Node/WSL/Podman, offline installer | Один запуск устанавливает комплект и открывает локальный upload screen; без ручной распаковки/консоли | 02,11,12 |
| LW-E02 | Source/wheel/frozen startup из другой CWD, Unicode user path | Рабочие assets/schema/registries/docs, никакой зависимости от исходного дерева | 02,04,11 |
| LW-E03 | Один MD и несколько MD | Source inventory, SHA/provenance, видимые counts; содержимое не исполняется | 05 |
| LW-E04 | ZIP с подпапками/кириллицей/пробелами и неподдержанными картинками | Безопасный импорт MD, полная ведомость skipped, no silent truncation | 05 |
| LW-E05 | Нет документации | Опрос/уточнения без fake source и fabricated requirements | 05,06 |
| LW-E06 | Значимый unknown, sensitivity UNKNOWN, target UNSURE | Не READY; вопрос/WAITING_INPUT или WAITING_DECISION, одна ясная next action | 06 |
| LW-E07 | GPT export→fixture response→preview→apply | Exact export/project/source/input binding; без ручного YAML | 06 |
| LW-E08 | GPT response wrong project, old export, source changed, extra field, approved:true, AUTO/egress | Отказ до mutation с repair action; нет формального согласия от модели | 06,07 |
| LW-E09 | Четыре Greenfield/пять Brownfield approvals, один отсутствует | Только отдельные подтверждения, missing decision блокирует prepare | 07 |
| LW-E10 | Смена содержания после draft approval, two-tab confirmation | Invalidation/conflict, сохранение исторической записи; не stale approved | 03,07 |
| LW-E11 | Fully approved prepare | Valid ZIP + реально опубликованная папка + current active stage + exactly one first READY JIT | 08 |
| LW-E12 | Destination существует, содержит sentinel; output collision | Никакой rmtree/overwrite user data; понятный выбор новой папки | 08 |
| LW-E13 | Stage only active details | Future levels outlines, no future detailed tasks/JIT или scope expansion | 08,10 |
| LW-E14 | Manual Task: result → independent verify PASS → complete → next | Три разных состояния, exact Run/result/baseline, no duplicate | 09 |
| LW-E15 | Agent COMPLETED при verification FAIL/forbidden writes/tamper | Не DONE, реальный blocker/recovery; никаких generic Gate evidence | 09 |
| LW-E16 | Verification commands без consent, с consent, missing SDK | Без consent нет процесса; exact plan shown; no hidden toolchain install; not SANDBOXED claim | 09 |
| LW-E17 | Block/resume ordinary Task; Gate BLOCKED/recovery | Раздельные working routes, immutable previous Runs | 09,10 |
| LW-E18 | Prototype Gate accept→Alpha reviewed plan→first READY | Только формальная acceptance, нет dead end/missing refs | 10 |
| LW-E19 | Accepted MVP→level-up RELEASE и illegal skip/no-op | Последовательная активная стадия, canonical target/projections; history unchanged | 10 |
| LW-E20 | Maintenance start→tasks→complete/cancel allowed branch | Maturity неизменна, exact accepted context/replay | 10 |
| LW-E21 | Brownfield assessment, stale ref/digest/claim, fake README maturity | Repository read-only, unknown gaps не PASS, separate baseline approval | 05,10 |
| LW-E22 | Supported migration→restart→replay | MANUAL_HANDOFF default, immutable accepted input/reports/completed Runs | 10 |
| LW-E23 | No session/expired bootstrap/replay/unknown Host/foreign Origin/wrong port/CSRF | HTTP отказ, никакой приватной информации и mutation | 04 |
| LW-E24 | XSS filenames/MD/GPT/results, iframe, external image/CSP | Только безопасный текст, no external fetch/script, token не раскрыт | 04–10 |
| LW-E25 | ZIP Slip/UNC/drive-relative/ADS/device names/trailing dots/casefold collisions/links | Reject безопасно; ни одного файла вне private staging | 05 |
| LW-E26 | ZIP bomb/oversize/entry count/depth/CRC/encryption/partial stream | Реальные ограниченные bytes/resources; rollback partial import | 04,05 |
| LW-E27 | Cross-project artifact ID / traversal / arbitrary absolute path / untrusted open-folder | Отказ по ownership/root; нет generic filesystem/server shell | 03,04,08,09 |
| LW-E28 | Browser reload/close/reopen, 2 tabs, duplicate same key, key changed payload | Нет duplicate operations; truthful status/replay/conflict | 03–11 |
| LW-E29 | GUI-vs-CLI/process concurrency, current core changed | Shared fence/current fingerprint; no mixed Stage/result state | 02,03,10 |
| LW-E30 | Crash до mutation/после kernel commit/до UI result; неоднозначная verify | Reconcile from core; не повторять external commands; no false rollback/complete | 03,08–10 |
| LW-E31 | Interrupted publish/install; disk full/locked file/permission | Нет удаления existing project; all-old/all-new publication либо явный safe blocker | 02,08,11 |
| LW-E32 | Второй launcher/занятый порт/stale instance record | Один настоящий свой server, не attach к чужому listener; no arbitrary process kill | 04,11 |
| LW-E33 | Все элементы CONTROL_MAP | Working action или honest capability reason, никакой decorative fake кнопки | 04–12 |
| LW-E34 | Export/distribution/log scan | Нет session tokens/real secrets/raw roots/user docs в release; scan limitations записаны | 06,08,11,12 |
| LW-E35 | Frozen uninstall / дальнейший запуск / offline assets | Проекты сохранены, состояние восстанавливаемо, никакого CDN/pip latest | 11 |
| LW-E36 | Source/wheel/ZIP/installer exact integrity и legacy suite | Финальные bytes, manifests/CRC/resources sync, реальные regression outcomes | 12 |

## Требования к доказательствам

- Для UI E2E использовать настоящий браузер против фактического сервера; Flask test client дополняет, но не заменяет.
- Позитивная product fixture может играть роль внешнего Codex и изменять разрешённый product plane. Не разрешены direct edits `.harness`, manufactured approvals/evidence или private API обход UI в засчитываемом E2E. Начальные advanced-state fixtures создаются через public kernel flow и помечаются отдельно от проверяемого browser segment.
- Импорт ответа fixture GPT проверяет exchange/validation, а не интеллект модели. Manual operator smoke с настоящими документами желательно фиксировать отдельно, не выдавать его отсутствие за verified semantic understanding.
- Native Windows build/NTFS/file locking/clean install проверяются на Windows. Linux headless browser не подтверждает Windows packaging.
- Сохранять test logs/commands/exit codes/build hashes/platform/browser versions. Чувствительные данные и auth не логировать; screenshot только без приватных входных данных.
- Результаты Linux-only Podman tests и GO/NO-GO автоматического executor остаются отдельными. Их отсутствие не следует маскировать общей строкой «всё прошло».

## Release rules

`LOCAL_WEB_MANUAL=GO` только при прохождении всех обязательных применимых сценариев, реальной Windows установке/браузере и отсутствии critical skipped. `NOT RUN` в mandatory Windows/security scenario означает `LOCAL_WEB_MANUAL=NO-GO` до фактического выполнения. Legacy automatic-only tests остаются в Linux regression job, их platform skip на Windows обоснован, а не скрывает failure.

`AUTOMATIC_EXECUTOR` остаётся по исходному нормативному verdict — **NO-GO**. PH-LW не реализует positive governed egress и не подменяет Podman self-test.

## Уточнение r2: входная готовность

PH-LW-01 начинается с WIP snapshots из попытки PH-051-12 с NO-GO, не с принятого релиза. Известные automatic-only blockers явно наследуются, но не отменяют tests manual/preparation и shared governance. Native Windows readiness до реального прогона остаётся NOT TESTED. Ни положительная проверка архива, ни будущий LOCAL_WEB_MANUAL GO не меняют full v0.5.1 release verdict. Перезапуск PH-051-12 после отдельного устранения blockers требует тестирования точных финальных файлов, включая последующие изменения ядра.
