# PH-LW-12 — исправление трёх blockers и повторная приёмка

2026-11-08. **LOCAL_WEB_MANUAL: GO.**  
**AUTOMATIC_EXECUTOR: прежний NO-GO; выключен.**  
Полная v0.5.1: **NO-GO / NOT RELEASED**. Только Windows. Engine/Documentation ZIP не создавались.

Это новый checkpoint на [проверенной предыдущей базе](PH_LW_12_FIX_LOGS/INPUT_BASELINE.json). [Исходный NO-GO](PH_LW_12_TEST_REPORT.md) и его evidence сохранены. [Verdicts](PH_LW_12_FIX_LOGS/VERDICTS.json), [изменения](PH_LW_12_FIX_CHANGED_FILES.md), [точный diff](PH_LW_12_FIX_LOGS/CODE_DIFF.patch).

## Три исправления

1. **LW12-DEEP-APPDATA-INTAKE — CLOSED.** Native IO охватывает создание/replay/cleanup intake, источники, catalog/draft/fingerprint, approvals, compilation/ZIP validation, no-replace publication и затронутые manual Task/evidence/journal reads. Ordinary paths/refs сохраняются; UNC/device/reparse запреты не ослаблены. Исходная ошибка cleanup не маскируется; committed session не удаляется. Control-plane scan не объявляет существующие глубокие файлы удалёнными, а настоящий tamper/deletion остаётся FAIL.
2. **LW12-MAINTENANCE-RESULT-CONFLICT — CLOSED.** JSON и multipart одной вкладки проходят общую очередь с прежними reads и navigation resume. Внешний конфликт остаётся 409; POST не повторяется; исходные binding/consent не заменяются новыми автоматически. Actual maintenance result/evidence/verify/complete проверены реальными формами.
3. **LW12-PROJECT-LIST-PROJECTION — CLOSED.** Карточка обновляется из того же fresh public Engine view, что основной panel. После MVP→RELEASE проверяются core ACTIVE, lifecycle STAGE_PLANNING_REQUIRED и актуальная карточка; accepted history сохраняется.

State machines, schemas/registries, порядок уровней, exact refs/digests, approvals, semantic evidence и manual/automatic policy не менялись. UI/HTTP не редактируют canonical YAML. Изменения соседнего core ограничены доказанным native IO regression на конкретных deep fixtures.

## Фактические tests

Discovery: **617 methods / 54 modules**. Windows scope — **461**, итог `{'PASS': 459, 'SKIP': 2}`. **156 POSIX-only** methods NOT RUN вне разрешённой Windows платформы; Linux/WSL/Docker jobs не выполнялись. Source-layout-only PH-F01/F03/F04 — 27 methods на source; прочая текущая matrix — installed wheel из независимой Unicode CWD с пустым PYTHONPATH. Все case IDs, commands/exits/counts/elapsed/причины — в [method matrix](PH_LW_12_FIX_LOGS/METHOD_RESULTS.json), `.run.json` и [evidence index](PH_LW_12_FIX_LOGS/EVIDENCE_INDEX.json).

| Exact final run | Status |
|---|---|
| final03-installed-supported | PASS |
| final03-installed-deep | PASS |
| final03-installer-recovery | PASS |
| final03-installed-extended | PASS |
| final03-installed-deep-full | PASS |
| maturity-final03 | PASS |


Actual EXE extended — 22 methods; отдельный глубокий no-doc→GPT→4 approvals→publish→result→manual evidence→verify→complete проверен дополнительно. Deep MD/ZIP EXE — retained project/app-data paths **341/372** символов; LongPathsEnabled 0→0. [Deep EXE](PH_LW_12_FIX_LOGS/final03-installed-deep/RESULT.json), [deep full manual](PH_LW_12_FIX_LOGS/final03-installed-deep-full/RESULT.json), [22-method browser/security](PH_LW_12_FIX_LOGS/final03-installed-extended/RESULT.json), [actual installer recovery](PH_LW_12_FIX_LOGS/final03-installer-recovery/RESULT.json).

Native source diagnostic также прошёл полный manual путь при app-data 242 / project root 251 и public compile/initial validation при output parent 294. Это отдельный source evidence, не замена actual frozen run. External fixture agent пишет только product plane; его IO и полный non-empty control snapshot адаптированы к длинным путям. Initial advanced fixtures происходят из public kernel flow; browser segment применяет реальные reviewed forms, без изготовленных private approvals. GPT fixture проверяет протокол, не интеллект модели.

Два прежних capability SKIP сохранены с точными причинами: native file symlink требует отсутствующей privilege; casefold aliases требуют case-sensitive directory. Новых SKIP не допускается. Actual NTFS junction/hardlink и ZIP link/collision tests выполняются отдельно. Четыре принятых NOT RUN — clean Windows, physical offline, actual Unicode username, real disk-full — не открывались заново и не переименованы PASS. Headless Edge не объявляется новой проверкой visible default-browser second launch.

## Сохранённые диагностические попытки

Кандидаты 01/02 и прерванные legacy setups сохранены с исходными FAIL/exit/logs; их результаты не засчитаны финальной matrix. После исправления archive IO последующие проверки выявили plain-path control scan, archive comparison и rename; эти read/write sites исправлены до final freeze. Source 10 regressions и full deep manual diagnostic прошли.

Один прежний PH-LW-12 fault-test синхронизирован с новым serialized transport: искусственно задержанный GET освобождается до ожидания запроса, который правильно ждёт в очереди. Assertions exact fingerprint и canonical/UI state сохранены; исходные bytes — `_workspace/PH_LW_12_FIX/input-tests/`. Остальные legacy test assertions не менялись. Frozen HTTP driver сохраняет exact 431 assertion при Windows reset после уже полученного HTTP 431 status; body loss успешных responses остаётся ошибкой. Это не PASS при reset до HTTP status.

## Точные bytes и ограничения

Build `PH-LW-12-FIX3-20261108`; source digest `sha256:6633069ce2a0b38d64169b4e3ce343badf421919a923329afb6ee887a847dc91`.  
Wheel SHA-256 `6ab5e977fc4d7e43ebfba1e2dd2a1342b213124cf90d5482f5011410414ee7f1`.  
UNSIGNED installer SHA-256 `43bce20185ae701743ffea12b79c7d301f14d298ffdbc586c7428a28e008ee08`.

[Freeze](PH_LW_12_FIX_LOGS/RUNTIME_FREEZE.json), [installed environment](PH_LW_12_FIX_LOGS/WHEEL_ENVIRONMENT.json), [integrity](PH_LW_12_FIX_LOGS/INTEGRITY.json), [final attestation](../_workspace/PH_LW_12_FIX/FINAL_WORKING_TREE_VERIFICATION.json), [before/after hashes](../_workspace/PH_LW_12_FIX/CHANGED_FILE_HASHES.json). После freeze runtime/docs bytes не менялись; добавлены только tests/evidence/reports/navigation/manifests. Build metadata conservatively preserves pre-acceptance NO-GO release flags; текущий exact-hash manual verdict дан этим внешним отчётом, full v0.5.1 не переобъявлен RELEASE.

Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, pinned Playwright/real Edge 157.0.4341.42/TCP. Hash browser executable сохранён в environment evidence. Frozen child имеет System32-only PATH. Payload PE AMD64 0x8664; Inno bootstrap x86 0x14c с x64compatible target. Ни системные защитные настройки, ни LongPathsEnabled не менялись. Исторические archives не пересобраны.

[Acceptance](PH_LW_12_FIX_LOGS/ACCEPTANCE_MATRIX.json), [controls](PH_LW_12_FIX_LOGS/CONTROL_MATRIX.json), [security](PH_LW_12_FIX_LOGS/SECURITY_MATRIX.json), [published log scan](PH_LW_12_FIX_LOGS/PUBLISHED_LOG_SCAN.json), [операторская глава 23](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md). Scan имеет заявленные text-pattern границы; это не универсальная DLP. Raw auth/uploads/projects, `_scratch`, `_tools`, `.venv`, caches в distribution не включены.

Следующий разрешённый шаг: использовать/проверять принятый manual companion в указанном Windows scope. К automatic executor, Podman/egress или следующему этапу автоматически не переходить. ZIP только по отдельному запросу.
