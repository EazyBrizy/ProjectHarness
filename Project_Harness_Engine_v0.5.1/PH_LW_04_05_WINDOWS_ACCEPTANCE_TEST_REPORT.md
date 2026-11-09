# PH-LW-04/05 — фактическая Windows/HTTP приёмка

Дата: 2026-11-07 (Europe/Moscow; raw timestamps UTC). Build: `PH-LW-05-WINDOWS-RETEST-20261107`. Версия: **0.5.1 WIP / NOT RELEASED**.

## Решение

| Область | Фактический результат |
|---|---|
| PH-LW-04: проверенная Windows/HTTP/security область | **PASS** — 17 tests в отдельном CI; production/cross-origin проверки также входят в совокупный suite |
| PH-LW-05 вместе с PH-LW-04 | **PASS** — 44 tests, 0 failures/errors/skips; настоящий Waitress TCP и Edge |
| Installed wheel вне source | **PASS** — 27 tests, 0 failures/errors/skips, doctor и фактический console launcher |
| Полный доступный regression набор | **FAIL** — 37 модулей / 424 tests; 27 модулей PASS, 1 PASS_WITH_SKIPS, 9 FAIL; 24 failure events, 95 error events, 4 skips |
| `LOCAL_WEB_MANUAL` release | **NO-GO** — серия до PH-LW-12 не завершена; полный manual/release gate этим отчётом не закрывается |
| `AUTOMATIC_EXECUTOR` и полная v0.5.1 | **NO-GO / NOT RELEASED** — прежние Podman/positive governed per-Run egress blockers сохранены; дополнительные Windows limitations ниже |
| PH-LW-06 | **NOT STARTED**, отдельного задания нет |

PASS целевых suites означает прохождение перечисленной HTTP/import области на этой машине. Он не превращает весь движок, старую migration ветку или все manual routes в принятый Windows release. Устаревшие отчёты не переписаны. User-facing shell не является готовым мастером всех этапов.

## Вход и разрешённые изменения

Пара получена от пользователя как PH-LW-05:

- Engine SHA-256: `d247127b5ab91b1dffd0f1f0649225bcf2b0bf02abea85a3c211cf3580b40c76`.
- Documentation SHA-256: `fd6a5d2aff1495708c30cf4f493ef30aed5bc6095a84a2fcd00e4a984013f1df`.
- CRC, safe paths, полный root manifest Engine (1151 records), standalone/embedded docs manifests (143 каждый) совпали. Specs и prompts: также CRC/manifests PASS. Внешнего expected SHA256 файла нет; наблюдаемые hashes фиксируют bytes, но не независимую authenticity attestation.
- Фактическая lineage — PH-051-11 WIP. Плановая PH-051-12 не считается выполненной. Пользовательские instructions определяют текущую задачу; прикреплённые prompts — scope/reference, не разрешение выполнить всю серию.

Allowed changes: workspace infrastructure; HTTP/auth/launcher/service/import boundary и assets; связанные tests/Windows CI; прямой Windows regression в используемой Stage transaction; docs, mirrors, wheel/manifests и полные новые ZIP. Normative specs, accepted contracts, status registries, automatic executor/migration implementation и исторические отчёты вне scope. После исследования ограничение выдержано.

## Среда

Windows 11 Pro x64 build 26200; C: NTFS; обычный non-admin пользователь. CPython **3.14.10 x64**, MSC v.1944. Официальный portable ZIP проверен по SHA-256 и распакован в локальный `_tools`, venv не меняет системный PATH/registry. Запуск installer был отклонён автоматической проверкой действия (дополнительной причины tool не сообщил); вместо него использован portable ZIP, installer не исполнялся.

Runtime: **Flask 3.1.3, Waitress 3.0.2**, остальные прежние runtime pins без изменений; wheelhouse скачан с `--require-hashes`, установлен offline `--no-index --find-links --require-hashes`. Edge **157.0.4341.42**, Playwright **1.64.1**. Dev-only build/browser/schema dependencies имеют отдельный lock. Jsonschema 4.26.0 добавлен только в dev venv для повторного запуска первоначально пропущенных contract tests; оба модуля затем PASS без skips. PowerShell CI реально запущен в Windows PowerShell **5.1**, direct venv `python.exe`, без ExecutionPolicy Bypass. System security settings, firewall и Developer Mode не менялись.

## Воспроизведённые дефекты и исправления

| Дефект до исправления | Минимальное исправление и подтверждение |
|---|---|
| Авторизованный GET `/api/projects/<id>` выдавал 500 из-за отсутствующего параметра handler | Handler принимает project_id; Flask, TCP, UI overview и read-only snapshot checks проходят |
| Неверный тип action и Unicode CSRF приводили к 500 | DTO validation до membership; ASCII check перед constant-time compare; structured 400/403 до mutation |
| Replay уже завершённой HTTP операции отклонялся как stale | Receipt lookup перед проверкой нового состояния в service; exact replay возвращает прежний operation ID после commit/restart; новый stale request и изменённый прежний key дают 409 |
| Повторные scalar multipart поля схлопывались Flask parser | Ровно одно значение каждого scalar; multiple files сохранены; hostile request отклоняется без source revision |
| Snapshot reads могли пройти через подменённый ancestor imports/snapshots | Проверка native parents до ledger/manifest/file read; real NTFS junction/hardlink rejection и copy-time digest tamper tests |
| Raw ZIP ошибочно проверялся по 8 MiB Markdown limit | Raw ZIP budget 64 MiB, entry/MD 8 MiB; законный ZIP >8 MiB, listing, retry и restart проходят |
| После source request кнопки оставались disabled | Единый finalizer восстанавливает source и core action buttons; browser create/upload/retry/replace/no-doc/preview PASS |
| Stage transaction `fsync` read-only fd давал EBADF на Windows | Только Windows file descriptor открыт O_RDWR; ошибки flush не скрываются; 15 transaction crash/rollback/replay tests PASS |
| Windows CI inline `-c` quoting и NativeCommandError ломали запуск | Python runner + прямые argv; проверка среды и exact exits; mandatory skips не дают PASS; оба PS5.1 scripts реально PASS |

Отдельно исправлены тестовые fixtures: ZIP filenames сохраняют backslash bytes на Windows; fault injection сравнивает компоненты Path; manual CLI tests запускают публичный Python entrypoint вместо Unix shebang. Ожидания governance/recovery не ослаблялись. Reduced-limit TCP fixture проверяет ранний 413 по Content-Length; отдельный production test фактически передаёт более 64 MiB chunked bytes. CORS rejection наблюдается через реальный HTTP status CDP, поскольку обычный Playwright response event скрыт при CORS failure. Foreign form отправляется в отдельный frame. Hidden action locator проверяет disabled state без обходного refresh.

Выполнен один независимый read-only review candidate по workflow `codex-security:fix-finding`: reviewer не нашёл дополнительных конкретных удалённых HTTP/upload bypass, но нашёл остаточный busy-state дефект core buttons. Он исправлен и покрыт browser assertion. Review статический и ограничен diff; это не полная независимая security certification.

## Фактические команды и evidence

Все пути ниже относительно Engine. Полные command/interpreter/cwd/time/exit — в `.run.json`; оригинальные raw runs сохранены в workspace `_scratch`. Публикуемые копии редактируют только machine paths/bootstrap URLs; [индекс](PH_LW_04_05_WINDOWS_LOGS/EVIDENCE_INDEX.json) отдельно связывает raw/redacted hashes.

| Run | Итог | Evidence |
|---|---|---|
| Исходный targeted suite и focused repro | FAIL, подтверждены дефекты до исправления | [baseline](PH_LW_04_05_WINDOWS_LOGS/runs/baseline-targeted.log), [repro](PH_LW_04_05_WINDOWS_LOGS/runs/reproductions-before.log) |
| `ci_ph_lw_04_windows.ps1 -PythonExecutable <venv-python> -DocumentationZip <exact-zip> -LogDirectory <external> -SkipRegressions` | exit 0; 17 tests; doctor/docs PASS | [CI04](PH_LW_04_05_WINDOWS_LOGS/ci04/PH_LW_04_WINDOWS_TEST_REPORT.json) |
| Аналогичный `ci_ph_lw_05_windows.ps1` | exit 0; 44 tests; doctor/docs PASS | [CI05](PH_LW_04_05_WINDOWS_LOGS/ci05/PH_LW_05_WINDOWS_TEST_REPORT.json), [stage log](PH_LW_04_05_WINDOWS_LOGS/ci05/stage_tests.log) |
| `tools/verify_installed.py --engine <test-package-only>` через отдельную venv | exit 0; 27 tests; actual installed console launcher PASS | [wheel run](PH_LW_04_05_WINDOWS_LOGS/runs/installed-wheel.run.json), [log](PH_LW_04_05_WINDOWS_LOGS/runs/installed-wheel.log) |
| `tools/run_regressions.py --jobs 3 --timeout 900` и указанные targeted reruns | full suite FAIL, все 37 модулей завершены; TIMEOUT нет | [итоговая матрица](PH_LW_04_05_WINDOWS_LOGS/REGRESSION_MATRIX_FINAL.json) |
| Documentation validator | 36 checks, 145 files, 925 links; 0 errors/warnings | [docs validation](PH_LW_04_05_WINDOWS_LOGS/ci05/DOC_VALIDATION.json) |

`-SkipRegressions` в stage scripts означает NOT RUN только в этом запуске; полный отдельный набор действительно выполнен и не объявлен зелёным. Initial monolithic run прерван после подтверждения fsync дефекта; его заменяет bounded per-module run. Итоговая матрица явно ссылается на более свежие runs для исправленных fixtures; неуспешные промежуточные runs сохранены. Failure/error counts включают subtests и не являются числом уникальных провалившихся test methods.

Проверены: реальный bind 127.0.0.1 до browser; отсутствие LAN listener; exact Host/Origin/port/null, session/CSRF, one-use и реальное истечение bootstrap; production body/header/connection/idle limits (64 MiB, 16 KiB, 32, 20 s); foreign browser fetch/form/frame; XSS как inert text и отсутствие external requests; Unicode/space filenames, malicious ZIP/CRC/encoding/collision/reparse/hardlink; immutable preview/refresh; cross-project rejection; import append/replace/retry/restart/no-doc; fault recovery; exact operation replay после server restart. Источники не исполнялись и наружу не отправлялись. Реальный wheel import подтверждён из независимой `site-packages`, CWD с кириллицей и пробелами, source PYTHONPATH отсутствовал.

## Оставшиеся FAIL / SKIP / NOT RUN

| Модули/граница | Причина и решение |
|---|---|
| `test_contract_hardening`, `test_ph_051_02_executor_protocol` | По одному ERROR подготовки file symlink: Windows WinError 1314 без привилегии. Не считать rejection доказанным этим тестом; защитные настройки не менять |
| `test_ph_051_03_rootless_podman`, `test_ph_051_04_disposable_roots`, `test_ph_051_05_codex_adapter`, `test_ph_051_06_result_channel`, `test_ph_051_08_atomic_apply` | Unix `geteuid`, directory-fd/dir_fd/O_NOFOLLOW assumptions, symlink prerequisites и недоступный real Podman. Это реально FAIL на Windows, а не успешная automatic acceptance |
| `test_ph_051_09_automatic_runtime` | SANDBOX_UNAVAILABLE/BLOCKED вместо ожидаемых fake Linux execution outcomes; 18 failure events, 1 error. Automatic route не включался |
| `test_ph_051_10_migration_recovery` | **Отдельный реальный Windows defect:** `_migration_sync_staged_tree` вызывает fsync на read-only fd (EBADF) в миграции v0.5.0→v0.5.1. Также Unix/fixture errors и несовместимый старый patch target. `migration.py` не изменён: ветка не используется HTTP/import PH-LW-04/05. Она блокирует соответствующую будущую migration/manual release приёмку и требует отдельного scope |
| 4 оставшихся skips | 3 real Podman/image prerequisites и 1 NTFS case-sensitive alias fixture. ZIP casefold collisions и real junction/hardlink проверены отдельно |
| Clean machine, installer/frozen/shortcut/uninstall | NOT RUN; PH-LW-11/12. Developer venv/wheel не заменяет installer |
| Новые interview/GPT approvals и полный UI lifecycle | NOT IMPLEMENTED в этой задаче; этапы 06+ не выполнялись |

Обычные ручные core regressions (assessment/evidence/levels/maintenance, Stage planner/reachability, 13 maturity lifecycle cases, 15 transaction recovery cases, service и importer) проходят; это не отменяет перечисленные gaps. Все 699 файлов исторических PH reports/logs совпадают с исходным архивом побайтово.

Pathname checks и digest verification отвергают persistent link/tamper cases, но не доказывают отсутствие любой TOCTOU гонки против произвольного процесса того же OS-user в private app-data. Power-loss durability не проверялась аппаратно. Изоляция remote upload и OS sandbox — разные утверждения; OS sandbox этим отчётом не принимается.

## Поставка и точные финальные bytes

Новая пара полных ZIP находится в отдельном каталоге `PH_LW_04_05_WINDOWS_RETEST_2026-11-07`; имена сохраняют PH_LW_05, оригиналы `_inputs` не затёрты. Source, regenerated build/lib, wheel, package resources, standalone/embedded docs и manifests синхронизированы. Wheel SHA-256: `db7ceb376304052c8a7eaa42716729ca042f7692d566fbf31cbd824c26e252e3`.

Внешний `PH_LW_04_05_WINDOWS_ACCEPTANCE_SHA256.txt` связывает точные output ZIP. Финальная повторная распаковка, CRC/manifests, doctor/docs и 44 stage tests фиксируются во внешнем `FINAL_VERIFICATION/FINAL_ARCHIVE_VERIFICATION.json` рядом с ZIP; он ссылается на их hashes и не включается внутрь ZIP, чтобы избежать самоссылочного hash cycle. Внешняя проверка определяет окончательный package verdict; этот внутренний отчёт описывает уже выполненную приёмку кода и wheel.

[Изменённые файлы](PH_LW_04_05_WINDOWS_ACCEPTANCE_CHANGED_FILES.md) · [сохранённые инварианты](PH_LW_04_05_WINDOWS_ACCEPTANCE_PRESERVED_INVARIANTS.md). Следующее функциональное действие — только после отдельного задания пользователя; PH-LW-06 автоматически не запускается.
