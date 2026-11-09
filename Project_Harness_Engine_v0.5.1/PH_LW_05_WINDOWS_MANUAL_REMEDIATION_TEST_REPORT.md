# Windows manual remediation: фактический отчёт

Дата: 2026-11-07. Build `PH-LW-05-WINDOWS-MANUAL-REMEDIATION-20261107`, v0.5.1-WIP / NOT RELEASED.

Исправлена применимая Windows-миграция v0.5.0→v0.5.1 и два дефекта очистки staging. Проверены все 9 прежних FAIL-модулей: 2 стали PASS_WITH_SKIPS, 7 остаются FAIL в Linux/automatic частях. Manual migration subset проходит полностью. Automatic executor не включался; PH-LW-06 не выполнялся.

## База и область изменения

Входные Engine/Documentation ZIP: `d48a47b43957df5fd3e4e57db98f0b4e2e73c668893489a528e9c739200cb6ef` / `5d610858306dc91e1b125711e30dc84e7f4aed046d4d72c20f0ff401f05f9b8b`. Это предыдущая проверенная поставка, не исходный архив из browser chat. Preflight hashes/mirrors/doctor PASS; прежние архивы, normative specs, планы и исторические reports/logs сохранены побайтово.

Разрешённая область: `migration.py`, доказанные manual regressions, platform test fixtures, документация, evidence и производные build/wheel/manifests. Из production Python изменён только migration module; metadata обновлена для traceability. [Список изменений](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_CHANGED_FILES.md), [инварианты](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_PRESERVED_INVARIANTS.md).

## Дефекты и исправления

1. **Windows staged fsync:** 4 из 5 исходных migration cases падали с `OSError: [Errno 9] Bad file descriptor`. Windows `_commit` требует write-capable file descriptor. Staged files открываются с `O_RDWR` только на Windows; POSIX остаётся `O_RDONLY`. Flush выполняется до journal/первого canonical rename, ошибка не подавляется. [До](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/runs/migration-before.log), [после](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/runs/migration-after-fsync.log).
2. **Частичный copy:** copytree раньше стоял вне cleanup try; PermissionError оставлял staging. Copy включён в тот же блок восстановления, исходный проект остаётся неизменным. [Воспроизведение](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/runs/partial-copy-before.log).
3. **Read-only cleanup:** copied NTFS read-only файлы мешали удалить private staging после отказа миграции. Cleanup проверяет native path, parent и точное UUID-имя migration sibling; read-only снимается только с обычного single-link файла этого storage. Canonical source и внешний hardlink не меняются. ACL/sharing ошибки не подавляются. [Первичный failure](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/native-extra-initial/test_windows_manual_migration.log).

Readonly source не объявляется поддержанным успешным сценарием: миграция отказывает до swap, сохраняет bytes/attributes источника и удаляет свой staging. Это подтверждённый безопасный отказ. Не заявляется Windows power-loss durability: `os._exit` проверяет остановку процесса, не обесточивание диска.

## Результаты

| Проверка | Фактический результат |
|---|---|
| Новые native migration/cleanup cases | 10 PASS, 0 SKIP: CLI Unicode/spaces; replay; manual next→verify→complete; copy/fsync/rename failure; real process exit с обеих сторон swap; открытый Windows handle; read-only; чужой sibling/hardlink; запрет automatic dispatch |
| Прежние V051MigrationTests | 5 PASS, 0 SKIP; включены также в mixed PH-051-10 run |
| Свежий regression run | 18 модулей, 294 tests; 8 PASS / 3 PASS_WITH_SKIPS / 7 FAIL; 24 failure events, 88 error events, 7 SKIP; 0 TIMEOUT |
| Установленный финальный wheel, другая CWD/venv | 42 PASS, 0 SKIP: 27 HTTP/import/реальный Edge + 15 migration/cleanup; actual console launcher и loopback health PASS; импорт из site-packages |
| Documentation validator | 36 checks PASS, 0 errors/warnings; 146 files, 928 local links |
| Объединённая матрица с историей | 38 модулей, 436 tests; 28 PASS / 3 PASS_WITH_SKIPS / 7 FAIL. **20 модулей взяты из предыдущей приёмки, не запускались заново в этой задаче** |

Два разделённых составных tests и 10 новых увеличили число с 424 до 436. Error count снижен с 95 до 88: устранены 4 migration errors, 3 недоступных file-symlink fixtures стали явными SKIP. 24 failure events остались; subtest events нельзя вычитать из testsRun для вычисления числа успешных methods.

[Свежая матрица](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/REGRESSION_MATRIX_CURRENT.json), [объединённая provenance](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/REGRESSION_MATRIX_COMBINED.json), [installed wheel log](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/runs/installed-wheel-final.log), [индекс raw/published hashes](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/EVIDENCE_INDEX.json).

## Разбор девяти прежних FAIL

В числовой колонке: tests / failures / errors / skips. Статусы относятся к целому модулю; PASS subset не заменяет FAIL смешанного модуля.

| Модуль | Повторный результат | Причина и решение |
|---|---|---|
| [test_contract_hardening](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_contract_hardening.log) | PASS_WITH_SKIPS; 31/0/0/1 | Fixture prerequisite. Единственный прежний ERROR — WinError 1314 при создании file symlink. Helper пропускает только этот фактический OS отказ; остальные 30 cases проходят. Symlink rejection этим run не доказан. |
| [test_ph_051_02_executor_protocol](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_02_executor_protocol.log) | PASS_WITH_SKIPS; 25/0/0/1 | Fixture prerequisite. WinError 1314 отделён в самостоятельный symlink case. Malformed, missing и oversized result cases выполняются; теперь 25 tests. Продуктовые ожидания не ослаблены. |
| [test_ph_051_03_rootless_podman](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_03_rootless_podman.log) | FAIL; 20/2/8/1 | Linux/Podman path + fixture. os.geteuid/getegid отсутствуют, symlink fixture требует привилегии; Windows refusal/validation срабатывает раньше Linux output-limit/doctor ожиданий. Реальный rootless Podman не проверен. |
| [test_ph_051_04_disposable_roots](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_04_disposable_roots.log) | FAIL; 21/0/16/1 | Linux automatic implementation. safety.safe_disposable_baseline_revision открывает directory fd; Windows даёт PermissionError. Также недоступны Unix/symlink fixtures. Этот disposable root не используется manual handoff. |
| [test_ph_051_05_codex_adapter](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_05_codex_adapter.log) | FAIL; 16/0/4/2 | Смешанный, manual subset PASS. Отдельный hardlink test теперь выполняется и PASS; file symlink SKIP. Остались os.geteuid mock и 3 PreparedJit directory-fd errors. Manual mode cannot activate и проверки exact profiles проходят. |
| [test_ph_051_06_result_channel](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_06_result_channel.log) | FAIL; 13/0/21/0 | Linux private automatic output. Exact /output channel требует UID/mode/dir_fd; ошибки os.geteuid и disposable baseline. Manual Agent Result проходит другой public complete путь; его проверяет новый end-to-end migration case. |
| [test_ph_051_08_atomic_apply](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_08_atomic_apply.log) | FAIL; 25/0/31/0 | Linux automatic product apply. 31 subtest error на подготовке disposable baseline с POSIX directory fd. Даже manual-optout cases этого модуля сначала готовят automatic candidate. Это не доказательство поломки manual complete. |
| [test_ph_051_09_automatic_runtime](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_09_automatic_runtime.log) | FAIL; 15/18/1/0 | Windows refusal vs Linux expectations. Native Windows возвращает BLOCKED/SANDBOX_UNAVAILABLE до fake automatic pipeline. Не добавлялись mock bypass или host fallback; новый native test подтверждает отсутствие Popen и любых изменений project bytes. |
| [test_ph_051_10_migration_recovery](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/regressions-final/test_ph_051_10_migration_recovery.log) | FAIL; 17/4/7/0 | Исправленный manual + Linux recovery. Все 5 V051MigrationTests PASS. Оставшиеся 4 failures/7 errors: automatic Windows guard, os.geteuid, недоступный conditional-import mock target finalize_execution_root и symlink privilege; mixed module остаётся FAIL. |

Вне этого списка также проходит повторная проверка PH-LW-02 (с прежним NTFS case-sensitive SKIP), PH-LW-03 service, всех 44 HTTP/import/browser cases, 13 maturity lifecycle и 15 stage-transaction recovery cases. Дополнительных применимых manual дефектов эти прогоны не выявили.

Семь skips: 3 file-symlink WinError 1314, 2 real Podman prerequisites, 1 Unix FIFO, 1 NTFS case-sensitive fixture. Старый report неточно называл четыре прежних skips «3 Podman + 1 NTFS»; правильные raw logs сохранены. SKIP не закрывает соответствующий gate; системные привилегии не повышались.

## Среда, воспроизведение и поставка

Native Windows 11 Pro build 26200 x64, NTFS C:, non-admin; portable CPython 3.14.10 x64, Flask 3.1.3 и Waitress 3.0.2 по hash lock; Playwright 1.64.1 с установленным Edge 157.0.4341.42. jsonschema установлен в основной dev venv; wheel-run использует отдельную venv и импорт site-packages. Это не clean-machine installer acceptance.

Команды, UTC start, exit и durations записаны в MATRIX/run.json. Из корня workspace: `.venv/Scripts/python.exe tools/run_regressions.py --output <новый каталог> --jobs 3 --timeout 900 <modules из свежей матрицы>`. Только migration: `tests.test_windows_manual_migration tests.test_ph_051_10_migration_recovery.V051MigrationTests`. Для wheel: независимый Python запускает `tools/verify_installed.py --engine <Engine> --manual-migration` из другой CWD с пустым PYTHONPATH. Raw paths редактированы только в опубликованных копиях logs; raw hashes сохранены отдельно.

Финальный wheel SHA-256: `10dd00a409b673cd81286902058c22b0aac4170b7f2a17f403ec1941a6d4a78a`. Engine/Documentation ZIP hashes находятся рядом с архивами в `PH_LW_05_WINDOWS_MANUAL_REMEDIATION_SHA256.txt`. После упаковки точная пара распаковывается в отдельный каталог; выполняются CRC/exact tree/all manifests, 44 HTTP/import/browser tests, doctor/docs и 15 migration/cleanup tests. Фактический результат этого последнего шага — **внешняя аттестация** `FINAL_VERIFICATION/FINAL_ARCHIVE_VERIFICATION.json` рядом с ZIP, привязанная к их SHA-256; она намеренно не включена обратно в архив, чтобы не создавать цикл self-hash. Отсутствие PASS в этой аттестации означает незавершённую проверку поставки.

## Verdict и открытые gates

PH-LW-04/05 Windows HTTP/security regression — **PASS в проверенном scope**, прежняя приёмка сохранена. Windows v0.5.0→v0.5.1 manual migration remediation — **PASS** по source и final installed wheel. Общая regression matrix — **FAIL**, 7 модулей подробно классифицированы выше.

`LOCAL_WEB_MANUAL: NO-GO` до полного набора PH-LW gates, включая PH-LW-12. `AUTOMATIC_EXECUTOR: NO-GO`; real rootless Podman, positive governed per-Run egress и Linux automatic recovery этим Windows run не подтверждены. Полная v0.5.1 — **NO-GO / NOT RELEASED**. Automatic и PH-LW-06 не разрешены этим заданием.
