# PH-LW-12 — исправление трёх blockers и повторная приёмка

2026-11-08. **LOCAL_WEB_MANUAL: GO.**  
**AUTOMATIC_EXECUTOR: прежний NO-GO; выключен.**  
Полная v0.5.1: **NO-GO / NOT RELEASED**. Только Windows. Engine/Documentation ZIP не создавались.

Это новый checkpoint на [проверенной предыдущей базе](PH_LW_12_FIX_LOGS/INPUT_BASELINE.json). [Исходный NO-GO](PH_LW_12_TEST_REPORT.md) и его evidence сохранены. [Verdicts](PH_LW_12_FIX_LOGS/VERDICTS.json), [изменения](PH_LW_12_FIX_CHANGED_FILES.md), [точный diff](PH_LW_12_FIX_LOGS/CODE_DIFF.patch).

## Три исправления

1. **LW12-DEEP-APPDATA-INTAKE — CLOSED.** Native IO охватывает создание/replay/cleanup intake, источники, catalog/draft/fingerprint, approvals, compilation/ZIP validation, no-replace publication и затронутые manual Task/evidence/journal reads. Ordinary paths/refs сохраняются; UNC/device/reparse запреты не ослаблены. Исходная ошибка cleanup не маскируется; committed session не удаляется. Control-plane scan не объявляет существующие глубокие файлы удалёнными, а настоящий tamper/deletion остаётся FAIL.
2. **LW12-MAINTENANCE-RESULT-CONFLICT — CLOSED.** JSON и multipart одной вкладки проходят общую очередь с прежними reads и navigation resume. Внешний конфликт остаётся 409; POST не повторяется; исходные binding/consent не заменяются новыми автоматически. Actual maintenance result/evidence/verify/complete проверены реальными формами.
3. **LW12-PROJECT-LIST-PROJECTION — CLOSED.** Карточка обновляется из того же fresh public Engine view, что основной panel. После MVP→RELEASE проверяются core ACTIVE, lifecycle STAGE_PLANNING_REQUIRED и актуальная карточка; accepted history сохраняется.

Operation/preparation polling читает собственный атомарный companion snapshot без рекурсивного обхода меняющегося canonical дерева. Сохраняются catalog/project ownership, root/ancestor reparse checks, record integrity и прежняя migration policy. До появления snapshot preparation GET получает прежний shared guard; mutation admission и явное recovery сохраняют полную проверку дерева. GET не пишет журнал и не повторяет операции.

State machines, schemas/registries, порядок уровней, exact refs/digests, approvals, semantic evidence и manual/automatic policy не менялись. UI/HTTP не редактируют canonical YAML. Изменения соседнего core ограничены доказанными native IO regressions и read-only companion snapshot boundary.

## Фактические tests

Discovery: **619 methods / 54 modules**. Windows scope — **463**, итог `{'PASS': 461, 'SKIP': 2}`. **156 POSIX-only** methods NOT RUN вне разрешённой Windows платформы; Linux/WSL/Docker jobs не выполнялись. Source-layout-only PH-F01/F03/F04 — 27 methods на source; прочая текущая matrix — installed wheel из независимой Unicode CWD с пустым PYTHONPATH. Все case IDs, commands/exits/counts/elapsed/причины — в [method matrix](PH_LW_12_FIX_LOGS/METHOD_RESULTS.json), `.run.json` и [evidence index](PH_LW_12_FIX_LOGS/EVIDENCE_INDEX.json).

| Exact final run | Status |
|---|---|
| final05-installed-supported | PASS |
| final05-installed-deep | PASS |
| final05-installer-recovery | PASS |
| final05-installed-extended | PASS |
| final05-installed-deep-full | PASS |
| maturity-final05 | PASS |


Actual EXE extended — 22 methods; отдельный глубокий no-doc→GPT→4 approvals→publish→result→manual evidence→verify→complete проверен дополнительно. Deep MD/ZIP EXE — retained project/app-data paths **341/372** символов; LongPathsEnabled 0→0. [Deep EXE](PH_LW_12_FIX_LOGS/final05-installed-deep/RESULT.json), [deep full manual](PH_LW_12_FIX_LOGS/final05-installed-deep-full/RESULT.json), [22-method browser/security](PH_LW_12_FIX_LOGS/final05-installed-extended/RESULT.json), [actual installer recovery](PH_LW_12_FIX_LOGS/final05-installer-recovery/RESULT.json).

Native source diagnostic также прошёл полный manual путь при app-data 242 / project root 251 и public compile/initial validation при output parent 294. Это отдельный source evidence, не замена actual frozen run. External fixture agent пишет только product plane; его IO и полный non-empty control snapshot адаптированы к длинным путям. Initial advanced fixtures происходят из public kernel flow; browser segment применяет реальные reviewed forms, без изготовленных private approvals. GPT fixture проверяет протокол, не интеллект модели.

Два прежних capability SKIP сохранены с точными причинами: native file symlink требует отсутствующей privilege; casefold aliases требуют case-sensitive directory. Новых SKIP не допускается. Actual NTFS junction/hardlink и ZIP link/collision tests выполняются отдельно. Четыре принятых NOT RUN — clean Windows, physical offline, actual Unicode username, real disk-full — не открывались заново и не переименованы PASS. Headless Edge не объявляется новой проверкой visible default-browser second launch.

## Сохранённые диагностические попытки

Кандидаты 01/02 и прерванные legacy setups сохранены с исходными FAIL/exit/logs; их результаты не засчитаны финальной matrix. После исправления archive IO последующие проверки выявили plain-path control scan, archive comparison и rename; эти read/write sites исправлены до final freeze. Финальный набор включает 12 targeted regressions: 8 native IO/snapshot и 4 real Edge.

После успешных runtime tests кандидата 03 финальный docs validator обнаружил отсутствующее обязательное поле базовой даты в новой главе 23. FAIL сохранён в [metadata diagnostic](PH_LW_12_FIX_LOGS/DOC_VALIDATION_METADATA_FAIL.json); предварительный GO report не был завершённой аттестацией и сохранён отдельно. В кандидате 04 дата исправлена; docs validator и 14 documentation-sensitive contracts прошли. Full aggregate Local Web addenda не включает и корректно не изменился; ошибка строгого inventory assertion build-helper описана отдельно, build-04 сам PASS.

У кандидата 04 последний deep full E2E дал FAIL: publication journal в core SUCCEEDED, но UI после reload остановился на INTERNAL_ERROR. Isolated rerun и source trace прошли без изменений; это не было принято как устранение дефекта. [Scheduling-barrier reproduction](PH_LW_12_FIX_LOGS/poll-barrier-before/RESULT.json) детерминированно выявила реальный FileNotFoundError: GET рекурсивно сканировал временный файл публичной check-intake, который её настоящий atomic writer уже переименовал. Python stack первого frozen 500 не записан; связь с найденной гонкой — вывод по общему read path, а не восстановленный stack trace. Исключение в reproduction не изготовлено mock; менялся только порядок исполнения. Два новых теста на прежних bytes дали 2 ERROR, на исправленном коде — 2 PASS с теми же assertions. Обычный stress helper остановлен после собственного некорректного budget cleanup и не засчитан; запись сохранена. В [наблюдаемых positive-flow HTTP responses](PH_LW_12_FIX_LOGS/POSITIVE_FLOW_HTTP_STATUS.json) final05 неожиданных 5xx нет; границы наблюдения указаны явно.

Кандидат **05** меняет snapshot boundary и содержит эти regressions. Его source/wheel/frozen/installer зафиксированы заново; вся Windows matrix, fresh maturity и пять actual EXE/recovery наборов выполнены заново по **одному final05 freeze**. Никакие результаты прежних candidates и их прежние equivalence proofs в итоговые counts не перенесены. Глава 23 описывает дополнительную гонку; validator прошёл до build и финальной аттестацией.

Один прежний PH-LW-12 fault-test синхронизирован с новым serialized transport: искусственно задержанный GET освобождается до ожидания запроса, который правильно ждёт в очереди. Assertions exact fingerprint и canonical/UI state сохранены; исходные bytes — `_workspace/PH_LW_12_FIX/input-tests/`. Остальные legacy test assertions не менялись. Frozen HTTP driver сохраняет exact 431 assertion при Windows reset после уже полученного HTTP 431 status; body loss успешных responses остаётся ошибкой. Это не PASS при reset до HTTP status.

## Точные bytes и ограничения

Build `PH-LW-12-FIX5-20261108`; source digest `sha256:0789035971ad3488b37a3d1cc480a9c7c63effcc3c67c540630e452b77f936ae`.  
Wheel SHA-256 `22ce3cdca5fe875430d4780f163975ba896c3348fa2f30b5a88199064bec54a1`.  
UNSIGNED installer SHA-256 `a4c7432852aadf93fd19fa4646ef8306854369be8ff8fd941ce6d1d268cc5964`.

[Freeze](PH_LW_12_FIX_LOGS/RUNTIME_FREEZE.json), [installed environment](PH_LW_12_FIX_LOGS/WHEEL_ENVIRONMENT.json), [integrity](PH_LW_12_FIX_LOGS/INTEGRITY.json), [final attestation](../_workspace/PH_LW_12_FIX/FINAL_WORKING_TREE_VERIFICATION.json), [before/after hashes](../_workspace/PH_LW_12_FIX/CHANGED_FILE_HASHES.json). После freeze runtime/docs bytes не менялись; добавлены только tests/evidence/reports/navigation/manifests. Build metadata conservatively preserves pre-acceptance NO-GO release flags; текущий exact-hash manual verdict дан этим внешним отчётом, full v0.5.1 не переобъявлен RELEASE.

Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, pinned Playwright/real Edge 157.0.4341.42/TCP. Hash browser executable сохранён в environment evidence. Frozen child имеет System32-only PATH. Payload PE AMD64 0x8664; Inno bootstrap x86 0x14c с x64compatible target. Ни системные защитные настройки, ни LongPathsEnabled не менялись. Исторические archives не пересобраны.

[Acceptance](PH_LW_12_FIX_LOGS/ACCEPTANCE_MATRIX.json), [controls](PH_LW_12_FIX_LOGS/CONTROL_MATRIX.json), [security](PH_LW_12_FIX_LOGS/SECURITY_MATRIX.json), [published log scan](PH_LW_12_FIX_LOGS/PUBLISHED_LOG_SCAN.json), [операторская глава 23](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md). Scan имеет заявленные text-pattern границы; это не универсальная DLP. Raw auth/uploads/projects, `_scratch`, `_tools`, `.venv`, caches в distribution не включены.

Следующий разрешённый шаг: использовать/проверять принятый manual companion в указанном Windows scope. К automatic executor, Podman/egress или следующему этапу автоматически не переходить. ZIP только по отдельному запросу.
