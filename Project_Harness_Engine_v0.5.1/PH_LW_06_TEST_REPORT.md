# PH-LW-06 — опрос и управляемый manual GPT exchange

Дата: 2026-11-07. Build `PH-LW-06-20261107`, v0.5.1-WIP / NOT RELEASED.

Реализован маршрут documentation → outcome → target → semantic draft через typed forms и ручной GPT exchange. **PH-LW-06: PASS в scope этапа.** Автоматического executor, provider API и перехода к PH-LW-07 нет. Все 40 regression modules прогнаны заново; семь прежних Linux/automatic FAIL сохраняют общий NO-GO полной v0.5.1.

## Проверенная база и полномочия

Задание пользователя разрешило именно PH-LW-06 по полному prompt r2. Вход — предыдущая проверенная Windows manual remediation пара, а не ранний архив с той же версией имени:

| Архив | SHA-256 |
|---|---|
| Engine PH-LW-05 | `c8ccd7f1f1b93200db1936d58c274bf535fae09aa616309b54bed8e0e3da33f2` |
| Documentation PH-LW-05 | `5b1dbed1ab7b876b8d5f078596c5c7ca327cd1f269d438407e88ac7bd95d4bd9` |

До реализации проверены hashes, CRC, manifests и точное совпадение рабочих деревьев с этой парой. [Входные доказательства](PH_LW_06_LOGS/INPUT_BASELINE.json). Происхождение от прежних WIP/NO-GO сохранено в build metadata и исторических reports.

Во время задачи отдельно обновлено правило архивирования пользователя: все результаты хранятся распакованными; новые ZIP нужны только по явному запросу для анализа в ChatGPT. Это правило явно заменяет обязательную ZIP-пару из сохранённого prompt. Чужие изменения AGENTS/README/RUNBOOK/docs сохранены; [отдельный отчёт политики](../_workspace/ARCHIVE_POLICY_2026-11-07/REPORT.md) не переписан. **Новые Engine/Documentation ZIP не создавались**; предыдущие архивы не объявляются обновлёнными. Wheel, mirrors и manifests проверяются независимо от ZIP.

Allowed file changes: Local Web service/HTTP/UI, отдельные envelope schema/template, bounded exchange storage, tests/native runner, docs/evidence/workspace navigation и производные build/wheel/manifests. Единственное соседнее core изменение — доказанный readiness defect в `project_input.py`: UNKNOWN values и material unknowns считались заполненными; compound questions могли скрывать незаполненные дочерние поля. Теперь они остаются questions/gaps; `UNSURE` имеет статус `WAITING_DECISION` с сохранённым списком пробелов. Core schemas/registries, migration, automatic runtime, immutable specifications и набор prompts r2 не изменены. [Изменённые файлы](PH_LW_06_CHANGED_FILES.md), [инварианты](PH_LW_06_PRESERVED_INVARIANTS.md).

## Исполнение полного prompt

| Требование PH-LW-06 | Реализация и фактическое доказательство |
|---|---|
| 1. Реальные questions/readiness; docs→outcome→target | Service использует `questions_for`/`validate_project_input`, отдельно показывает persisted состояние и known answers с refs. No-documentation и MD/ZIP сценарии проходят в реальном Edge. UNKNOWN/material gaps не READY; UNSURE не заменяется предложением GPT. |
| 2. Public draft APIs, expected revision, явный check | Typed forms → guarded `update-draft` → public `update_provisional_draft`; `check-intake` — POST operation. Import сначала показывает diff, readiness и invalidation receipt. Bytes canonical input до commit неизменны. |
| 3. Полный bounded pack | Актуальный browser `GPT_PREPARATION.md`, `PROJECT_INPUT@4`, opaque IDs, input/source bindings, current draft/questions, constraints, schemas и полные документы. Один файл либо index/count/order/hash для всех частей. Реальный multipart UTF-8 и отказ pack >20 MiB проверены. |
| 4. Разрешение внешней передачи | Полная inventory, sensitivity и отдельная PUBLIC/INTERNAL классификация каждого документа/draft, explicit consent. High sensitivity и известные secret patterns отказывают. Copy/download только явным действием; сервер не делает внешних запросов. |
| 5. Строгий JSON envelope | Отдельный `LOCAL_WEB_GPT_DRAFT_ONLY@2`; duplicate keys, depth/nodes/size, NaN/Infinity/overflow, wrong project/export, stale bindings, unknown/missing fields отклоняются до записи. YAML browser import не поддерживается. |
| 6. Нет импортированного trust | Pending approval copies false/null обязательны; actor/approved:true, execution, server identity/paths и trusted fields отвергаются. Pre-existing local approvals synthetic fixture: unchanged binding сохраняет; material draft change инвалидирует с receipt. |
| 7. Provenance и repair | Claims связаны с exact refs/value digests и помечены `GPT_DRAFT_UNVERIFIED`; поддельные nested source refs reject. Внешние вопросы/uncertainties сохраняются как blocking unknowns. Bounded repair содержит exact paths/rules, без raw reply/docs/environment. |
| 8. Reload, restart, replay, cancel, recovery | Preview восстанавливается после reload; exact replay без дубля; cancel до commit. Checksummed intent + atomic public draft update. Реальный child `os._exit(86)` после commit и restart/recovery PASS; before/after failure injection и чужая CLI mutation не перезаписываются. GET только сообщает необходимость recovery. |

Ключевые tests находятся в [exchange suite](tests/test_ph_lw_06_exchange.py) и [TCP/Edge suite](tests/test_ph_lw_06_http.py). Два browser Greenfield сценария используют **явно синтетический GPT reply fixture**. Это проверка формата/маршрута, не реальное общение с GPT и не доказательство качества созданной архитектуры. Imported HTML/script остаётся текстом; external requests и browser JS errors проверяются.

## Фактические runs

| Проверка | Результат |
|---|---|
| Pre-change baseline | 7 модулей / 86 методов: 6 PASS, 1 PASS_WITH_SKIPS; единственный SKIP — NTFS case-sensitive-directory fixture |
| Последний предварительный target run | 15 exchange + 4 HTTP/browser methods PASS; далее добавлен шестнадцатый exchange case для forged nested source ref и exact semantic repair |
| Финальный native runtime | 64 PASS / 0 SKIP: прежние 44 HTTP/import/Edge и новые 16 exchange + 4 HTTP/browser; doctor PASS |
| Native wrapper и docs retest | Исходный wrapper FAIL только из-за двух новых docs formatting errors. Отдельный docs-only retest PASS после исправления; исходный FAIL сохранён. Runtime tests для этой правки не повторялись |
| Финальный installed wheel | 62 PASS / 0 SKIP: 27 HTTP/import/Edge + 15 native migration/recovery + 20 exchange/TCP/Edge; actual console launcher/doctor/health PASS; source import исключён |
| Полный regression run на финальном коде | 40 модулей / 456 methods: 30 PASS, 3 PASS_WITH_SKIPS, 7 FAIL; 24 failure events, 88 error events, 7 SKIP, 0 TIMEOUT. Все 38 прежних модулей сохранили свои результаты; 2 новых PASS |
| Documentation validator | PASS: 35 checks PASS, 1 WARN, 0 errors; 147 files, 931 links. WARN `zip path not supplied` соответствует новому правилу без ZIP |
| Точные рабочие деревья / mirrors / manifests | PASS при наличии PASS во внешней аттестации, связанной с точными final manifest hashes; source/build/wheel и оба docs tree должны совпадать |

Все новые runs содержат command, interpreter/platform/dependencies, UTC start, exit, duration и raw log hash. [Индекс evidence](PH_LW_06_LOGS/EVIDENCE_INDEX.json) различает raw/published SHA-256: в публикуемых текстах заменены пользовательские пути/bootstrap values. Private uploads/auth, fixtures проектов, caches, venv и wheelhouse в поставку не включены. [Native scope verdict](PH_LW_06_LOGS/NATIVE_SCOPE_VERDICT.json) связывает runtime PASS с отдельным docs retest, не скрывая wrapper FAIL.

Промежуточные failures сохранены: порядок проверки forged approvals исправлен для понятного отказа; сообщение после save перестало затираться refresh; старый preview очищается при новом запросе; busy UI блокирует формы на время запроса. Browser tests ожидают завершённый POST/видимый preview перед byte snapshot, поэтому pending POST не приписывается последующему GET. Продуктовые отрицательные ожидания не ослаблялись. [Все runs](PH_LW_06_LOGS/README.md).

## Общие регрессии и ограничения evidence

[Полная свежая матрица](PH_LW_06_LOGS/REGRESSION_MATRIX_CURRENT.json) содержит 40 модулей / 456 methods; **ни один результат не подставлен из истории**. [Сравнение с базой](PH_LW_06_LOGS/PREVIOUS_BASELINE_COMPARISON.json) подтверждает одинаковые status/test/failure/error/skip counts всех 38 прежних модулей. Два новых добавили 20 methods. Общий runner exit=1 из-за семи FAIL; TIMEOUT нет. Исторические Linux/automatic FAIL не считаются PASS локального browser companion. SKIP не закрывает обязательный gate. Failure/error events могут быть subtests; их нельзя вычитать из testsRun для вычисления числа успешных methods.

Все семь FAIL-модулей уже завершили свежий run; числа tests/failures/errors/skips и категории причин совпадают с предыдущей Windows manual remediation базой. Ни один не преобразован в PASS под видом platform-specific результата:

| Модуль | tests/failures/errors/skips | Причина оставшегося FAIL |
|---|---|---|
| `test_ph_051_03_rootless_podman` | 20/2/8/1 | POSIX `os.geteuid` отсутствует; Windows SANDBOX_UNAVAILABLE приходит раньше Linux policy/output expectations; real Podman prerequisite отсутствует |
| `test_ph_051_04_disposable_roots` | 21/0/16/1 | Automatic disposable baseline использует POSIX directory fd и Unix fixture; Windows PermissionError на `build/handoff` |
| `test_ph_051_05_codex_adapter` | 16/0/4/2 | POSIX `geteuid` mock и 3 automatic PreparedJit directory-fd errors; manual refusal и hardlink checks проходят |
| `test_ph_051_06_result_channel` | 13/0/21/0 | Linux automatic private output требует UID/dir_fd; это не public manual completion path |
| `test_ph_051_08_atomic_apply` | 25/0/31/0 | Automatic apply subtests не проходят POSIX disposable-baseline preparation на Windows |
| `test_ph_051_09_automatic_runtime` | 15/18/1/0 | Windows отказывает BLOCKED/SANDBOX_UNAVAILABLE до fake Linux automatic pipeline; host fallback не добавлен |
| `test_ph_051_10_migration_recovery` | 17/4/7/0 | 5 manual migration methods PASS, Linux automatic recovery имеет `geteuid`/conditional-import mock/Windows guard ошибки; весь mixed module остаётся FAIL |

Raw traces находятся в [regressions-final](PH_LW_06_LOGS/regressions-final). Семь SKIP: 3 file-symlink WinError 1314, 2 real Podman prerequisites, 1 Unix FIFO и 1 NTFS case-sensitive-directory fixture. Привилегии/системные настройки ради fixtures не менялись. Manual migration проверена отдельно в installed wheel; mixed FAIL не скрывает этот положительный subset.

Windows 11 Pro build 26200 x64, NTFS C:, non-admin; CPython 3.14.10 x64. Runtime установлен offline по hash lock: Flask 3.1.3, Waitress 3.0.2; Playwright 1.64.1 использует установленный Edge 157.0.4341.42. Изолированный wheel run использует новую venv и Unicode CWD вне Engine, пустой PYTHONPATH, actual console launcher/health; импорт пакета обязан идти из site-packages. Системные защитные настройки и привилегии не менялись.

Это developer acceptance на реальной Windows, не clean-machine installer. Process exit не равен Windows power-loss. Real rootless Podman, positive governed per-Run egress, clean-machine installer/power-loss остаются **NOT RUN / незакрытый gate**. PH-LW-07 approvals UI и следующие этапы — **NOT RUN / вне задания**. Реального provider/GPT диалога не было.

## Ограничения реализации

Только managed Greenfield intake и `MANUAL_HANDOFF` с network NONE. Структурированные Technology/Task DAG предложения приходят через GPT draft exchange; общего schema editor нет. Reply ≤512 KiB, depth ≤24, nodes ≤30000; pack ≤20 MiB; draft export ≤256 KiB; payload parts ≤256 KiB; до 32 exports/128 imports/64 MiB private storage. При превышении отказ без silent truncation и удаления прежних данных. Quotas, exact binding и safe JSON errors — продуктовые ограничения, не token/model context estimate.

Экспорт включает все документы. Разрешённый набор предварительно проверяет человек; auto-redaction/выборочного обхода policy нет. Secret pattern check не является полным DLP. После изменения binding прежний pack нельзя заново скачать; нужен новый export. Source provenance остаётся unverified, source change требует review. Server не интерпретирует imported AGENTS.md как инструкции. Подробнее — [новая глава](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/13_PH_LW_06_Interview_and_GPT_Exchange.md).

## Hashes и verdicts

Wheel SHA-256: `04c34ced9484c0664f399ef45fe393c475c55d33fdf0fd6df8bd8bbfbc25e1dc`. Source build digest: `sha256:803c13cbe3b1447cafd5d9f822ecc9cadec7aa9fa05539f3736816a0e642f0df`. [Build provenance](PH_LW_06_LOGS/BUILD_PROVENANCE.json). Новые manifests покрывают полные распакованные Engine/Documentation, включая отчёт и logs. Их точные hashes, preserved history, before/after hashes каждого изменённого файла и финальные doctor/docs/workspace checks находятся во [внешней аттестации](../_workspace/PH_LW_06/FINAL_WORKING_TREE_VERIFICATION.json) и [SHA256.txt](../_workspace/PH_LW_06/SHA256.txt); это устраняет цикл self-hash.

PH-LW-04: **PASS в проверенном HTTP/security scope**. PH-LW-05: **PASS в проверенном import/source/migration scope**. PH-LW-06: **PASS в scope опроса и ручного GPT exchange**. Общая regression matrix: **FAIL**, семь известных Linux/automatic модулей. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1: **NO-GO / NOT RELEASED**. Automatic executor не включён, PH-LW-07 не начат. Следующий этап требует отдельного задания пользователя.
