# PH-LW-11 — ZIP-import при длинном app-data root

2026-11-08. **Long app-data ZIP-import: PASS. PH-LW-11 acceptance: NO-GO.** Automatic executor выключен; PH-LW-12 не начат; Engine/Documentation ZIP не собирались.

## Основание и исправление

Отдельное задание пользователя разрешило исправление ZIP-import FAIL после прежнего preparation-only fix. Проверенная входная база — build PH-LW-11-LONGPATH-20261108, digest sha256:cff006d0c0ef48ee942d5c7bdfb96c34e01c2f59c0682ca19a76a907cdd4559b. [Baseline](../_workspace/PH_LW_11_ZIP_PATH/INPUT_BASELINE.json), [input hashes](../_workspace/PH_LW_11_ZIP_PATH/INPUT_FILE_HASHES.json). [Предыдущий отчёт](PH_LW_11_LONG_PATH_TEST_REPORT.md), исходный PH-LW-11 NO-GO, их logs/attestations, normative specs, r2 и архивы сохранены неизменными.

WinError 206 возникал в local_web_imports._private_directory: длинный app-data root + quarantine/upload/materialized/LSD-* превышал обычный Windows mkdir/path limit. [До исправления](PH_LW_11_ZIP_PATH_LOGS/runs/before.log) новый public upload test воспроизвёл тот же WinError 206. Прежний actual EXE FAIL и diagnostic также сохранены в PH_LW_11_LONG_PATH_LOGS.

Исправлены только IO spelling/traversal sites в local_web_imports, source refresh/rollback, cleanup sources service, manual exchange IO, inventory_source, copy_tree_filtered и atomic_write_text. Внутренний extended drive path применяется после прежней проверки обычного пути; public paths/relative refs не получают prefix. Системные настройки Windows, политики, права и LongPathsEnabled не менялись. Обычный короткий source open сохранён для прежнего IO contract/fault injection; длинный open использует private adapter.

[Структурное сравнение](PH_LW_11_ZIP_PATH_LOGS/LOGIC_DELTA.json) семи source files с immutable baseline: AST бизнес-логики совпадает после удаления только явных IO adapters. ZIP names/types/budgets/CRC, UTF-8, untrusted semantics, state transitions, exact refs/digests, approvals и transaction/recovery checks не изменены. Core schemas/registries и старые tests побайтово сохранены. Промежуточные adapter ошибки и один initial old-test FAIL сохранены в runs; final scoped runs используют исправленные inputs. Ожидания тестов не ослаблены.

## Повторная проверка

Настоящий Windows 11 x64/NTFS, non-admin, CPython 3.14.10 x64. Flask 3.1.3, Waitress 3.0.2; Playwright 1.64.1, настоящий Edge/TCP. Runtime/dev dependencies установлены offline по прежним pinned hash locks. Wheel проверен в новой venv из Unicode CWD вне Engine source tree; import из site-packages, PYTHONPATH пустой. [Source environment](../_workspace/PH_LW_11_ZIP_PATH/SOURCE_ENVIRONMENT.json), [wheel environment](PH_LW_11_ZIP_PATH_LOGS/WHEEL_FINAL_ENVIRONMENT.json), [build](PH_LW_11_ZIP_PATH_LOGS/build-final/BUILD_RESULT.json).

| Набор | Факт |
| --- | --- |
| Новые long-app-data tests | 7 PASS: manual exchange roundtrip/replay из глубокого ZIP source; вложенный Unicode ZIP/exact bytes/inert preview/read-only GET; append/replay/restart/replace и immutable old snapshot; прежние hostile ZIP wire cases/CRC/count/size budgets на длинном root; interrupted refresh → GET без recovery → explicit restart rollback/exact canonical+ledger bytes; tamper/junction rejection; hardlink/copy-time tamper rejection |
| Source core/Windows | 20 scopes, 242 methods: 240 PASS, 2 SKIP, 0 FAIL/ERROR; включая PH-LW-03–08, Windows migration, Stage/gate/recovery и прежние 3 long-project tests |
| Installed wheel HTTP/core | 49 PASS, 0 SKIP; прежние HTTP/auth/revision/replay checks, 3 long-project и 7 новых long-app-data cases |
| Installed wheel Edge/desktop | 33 PASS, 0 SKIP; desktop/multi-tab/lifecycle и применимые PH-LW-04–10 browser flows |
| Actual self-contained installed EXE | 4 PASS, 0 FAIL/ERROR/SKIP в описанной адаптированной области; MD и ZIP → GPT fixture → separate approvals → prepare/JIT/download, restart/second launch/port conflict/crash/stop/doctor/uninstall retention |
| Actual installer recovery | 4 PASS: interruption during copy/retry, read-only current pointer rejection/retry |
| Fresh unique method results | 305; {'PASS': 303, 'SKIP': 2} |

В actual EXE run длинные profile/project и app-data roots использованы **одновременно**. Максимальный retained project file path — **284**, app-data file path — **278** символов, retained imported Markdown files — 2. LongPathsEnabled **0 → 0**. Короткий app-data workaround не использован. [EXE result](PH_LW_11_ZIP_PATH_LOGS/installed-long-verified/RESULT.json) подтверждает System32-only child PATH, empty PYTHONPATH, non-admin/NTFS и byte preservation при uninstall. Test-only snapshot reader независимо читает все глубокие Harness-owned файлы; прежние browser assertions/deadlines не менялись. По явному указанию пользователя real second-launch command получает --no-browser: новый видимый системный browser window не открывается. Для --no-browser проверяется точный отказ exit 1 по существующему launcher contract, first process/mutex/catalog checks сохраняются. Обычный второй запуск с открытием default browser — NOT RUN по явному ограничению пользователя; его прежний PASS остаётся историческим. Headless Edge tests не используют пользовательский browser profile.

Первый [EXE run](PH_LW_11_ZIP_PATH_LOGS/installed-long/RESULT.json) сохранил 1 FAIL при export и 3 lifecycle PASS. [Public diagnostic](PH_LW_11_ZIP_PATH_LOGS/runs/exchange-before.log) доказал второй прямой IO regression: manual export читал импортированный deep Markdown обычным file.read_bytes(). Только exchange IO sites адаптированы; [повтор](PH_LW_11_ZIP_PATH_LOGS/runs/exchange-after.log) PASS. Предыдущий partial source run остановлен перед этой правкой и сохранён как INTERRUPTED в REGRESSION_SUPERSEDED; итоговая source matrix, wheel и EXE повторены на новых финальных inputs. Первый test adapter дополнительно столкнулся с lockfile чужого browser cache при измерении всего LocalAppData; measurement исправлен на точную прежнюю область retention: ProjectHarness и ProjectHarness-workspaces, без пропуска deep files. Исходные FAIL/exception logs сохранены, им не присвоен PASS.

В [первом повторе финального installer](PH_LW_11_ZIP_PATH_LOGS/installed-long-final/RESULT.json) full MD/ZIP flow и 2 lifecycle cases PASS; отдельный lifecycle case получил FAIL из-за ошибочного ожидания exit 0 в новом --no-browser adapter. Продукт правильно вернул 1: уже работающий Harness отклоняет второй --no-browser launch. В adapter исправлена только эта новая expectation на точное contract value 1; normal browser-launch case отмечен NOT RUN. [Adapter delta](PH_LW_11_ZIP_PATH_LOGS/TEST_ADAPTER_DELTA.json) подтверждает неизменность source/wheel/installer inputs. Старые test files/production launcher не менялись, другие assertions/deadlines прежние.

[Source matrix](PH_LW_11_ZIP_PATH_LOGS/regressions-final/MATRIX.json), [installed wheel HTTP](PH_LW_11_ZIP_PATH_LOGS/runs/installed-final-nonbrowser.log), [wheel browser](PH_LW_11_ZIP_PATH_LOGS/runs/installed-final-browser.log), [installer recovery](PH_LW_11_ZIP_PATH_LOGS/installer-recovery-final/RESULT.json), [unique method results](PH_LW_11_ZIP_PATH_LOGS/METHOD_RESULTS.json), [evidence index](PH_LW_11_ZIP_PATH_LOGS/EVIDENCE_INDEX.json). Каждый run хранит command/interpreter/platform/exit/elapsed/log hash; dependencies связаны environment/build JSON и locks. Секреты/private app-data/raw uploads не опубликованы в evidence.

SKIP не объявлены PASS:

- `tests.test_contract_hardening.ContractHardeningControlPlaneTests.test_agent_result_symlink_is_rejected` — SKIP: NOT RUN: native file symlink creation requires a Windows privilege unavailable to this non-admin user
- `tests.test_ph_lw_02_windows_core.WindowsCoreBoundaryTests.test_05_colliding_tree_rejected_without_rewriting_case` — SKIP: NTFS casefold aliases require a case-sensitive directory; ZIP test is cross-platform

Полная прежняя 593-method matrix остаётся исторической. Свежий scoped набор не объявляется полным повтором automatic executor/upper maturity matrix. Прежний незавершённый visual walkthrough не объявлен выполненным.

## Артефакты и оставшиеся gates

[Installer UNSIGNED](windows/Harness-Setup-win-x64.exe), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md), [changed files](PH_LW_11_ZIP_PATH_CHANGED_FILES.md).

- Build `PH-LW-11-ZIPPATH-20261108`, source digest `sha256:5f0d5ac595d8a052bfa456140f2d42c5d571c53ab38aff3c8831d4ebbe309bbf`.
- Wheel SHA-256 `9bb3e87fdf2b297e7292fd5d2216fc1a61c9dbe49e2e4cf018f5eb5f2aa19bc2`.
- Installer SHA-256 `0550a5582182ab95aa8b5376b878cdb3210b126a53b6fd6f90746417d50abb94`.
- PACKAGE_FILES SHA-256 `83c012a866071ab2dac1c19e75f79118e1786a32a13f360c4e962e2c4cc4d34f`.
- [Final attestation](../_workspace/PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](../_workspace/PH_LW_11_ZIP_PATH/SHA256.txt), [before/after hashes](../_workspace/PH_LW_11_ZIP_PATH/CHANGED_FILE_HASHES.json). Source/build/lib/wheel/frozen inputs, resources/docs mirrors и manifests проверены; integrity PASS не означает full acceptance GO.

Long app-data ZIP-import blocker закрыт на данной native среде. **PH-LW-11: NO-GO** из-за mandatory NOT RUN: clean Windows без developer runtimes, actual Unicode username, physical offline, real disk-full. Sanitized developer host не заменяет clean-machine, Unicode path не заменяет username, ENOSPC injection не заменяет полный том. Signing credentials отсутствуют; installer UNSIGNED.

**LOCAL_WEB_MANUAL: NO-GO** до PH-LW-12; **AUTOMATIC_EXECUTOR: NO-GO**, выключен; полная v0.5.1 **NO-GO / NOT RELEASED**. Podman/positive governed per-Run egress остаются отдельным NO-GO. Прежние PH-LW-04 и PH-LW-05 verdicts не переписаны. Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments. К PH-LW-12 не переходить; Engine/Documentation ZIP не создавать без отдельного явного запроса.
