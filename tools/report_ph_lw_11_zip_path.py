"""Write the new factual PH-LW-11 supplement and current navigation in Russian."""
from pathlib import Path
import json
from package_acceptance import ROOT,ENGINE,DOCS
S=ROOT/'_scratch/ph_lw_11_zip_path';O=ENGINE/'PH_LW_11_ZIP_PATH_LOGS'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,t):p.write_text(t,'utf-8')
def main():
 v=read(O/'VERDICTS.json');b=read(O/'BUILD_PROVENANCE.json');long=v['long_path']
 skips='\n'.join(f"- `{s['test']}` — SKIP: {s['reason']}" for s in v['core_skips'])
 report=f'''# PH-LW-11 — ZIP-import при длинном app-data root

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
| Source core/Windows | {v['core_scopes']} scopes, {v['core_methods']} methods: {v['core_methods']-len(v['core_skips'])} PASS, {len(v['core_skips'])} SKIP, 0 FAIL/ERROR; включая PH-LW-03–08, Windows migration, Stage/gate/recovery и прежние 3 long-project tests |
| Installed wheel HTTP/core | {v['installed_wheel']['installed-nonbrowser']} PASS, 0 SKIP; прежние HTTP/auth/revision/replay checks, 3 long-project и 7 новых long-app-data cases |
| Installed wheel Edge/desktop | {v['installed_wheel']['installed-browser']} PASS, 0 SKIP; desktop/multi-tab/lifecycle и применимые PH-LW-04–10 browser flows |
| Actual self-contained installed EXE | {v['installed_exe_tests']['ran']} PASS, 0 FAIL/ERROR/SKIP в описанной адаптированной области; MD и ZIP → GPT fixture → separate approvals → prepare/JIT/download, restart/second launch/port conflict/crash/stop/doctor/uninstall retention |
| Actual installer recovery | 4 PASS: interruption during copy/retry, read-only current pointer rejection/retry |
| Fresh unique method results | {v['fresh_unique_methods']}; {v['method_statuses']} |

В actual EXE run длинные profile/project и app-data roots использованы **одновременно**. Максимальный retained project file path — **{long['maximum_retained_project_file_path_length']}**, app-data file path — **{long['maximum_retained_app_data_file_path_length']}** символов, retained imported Markdown files — {long['retained_import_document_count']}. LongPathsEnabled **0 → 0**. Короткий app-data workaround не использован. [EXE result](PH_LW_11_ZIP_PATH_LOGS/installed-long-verified/RESULT.json) подтверждает System32-only child PATH, empty PYTHONPATH, non-admin/NTFS и byte preservation при uninstall. Test-only snapshot reader независимо читает все глубокие Harness-owned файлы; прежние browser assertions/deadlines не менялись. По явному указанию пользователя real second-launch command получает --no-browser: новый видимый системный browser window не открывается. Для --no-browser проверяется точный отказ exit 1 по существующему launcher contract, first process/mutex/catalog checks сохраняются. Обычный второй запуск с открытием default browser — NOT RUN по явному ограничению пользователя; его прежний PASS остаётся историческим. Headless Edge tests не используют пользовательский browser profile.

Первый [EXE run](PH_LW_11_ZIP_PATH_LOGS/installed-long/RESULT.json) сохранил 1 FAIL при export и 3 lifecycle PASS. [Public diagnostic](PH_LW_11_ZIP_PATH_LOGS/runs/exchange-before.log) доказал второй прямой IO regression: manual export читал импортированный deep Markdown обычным file.read_bytes(). Только exchange IO sites адаптированы; [повтор](PH_LW_11_ZIP_PATH_LOGS/runs/exchange-after.log) PASS. Предыдущий partial source run остановлен перед этой правкой и сохранён как INTERRUPTED в REGRESSION_SUPERSEDED; итоговая source matrix, wheel и EXE повторены на новых финальных inputs. Первый test adapter дополнительно столкнулся с lockfile чужого browser cache при измерении всего LocalAppData; measurement исправлен на точную прежнюю область retention: ProjectHarness и ProjectHarness-workspaces, без пропуска deep files. Исходные FAIL/exception logs сохранены, им не присвоен PASS.

В [первом повторе финального installer](PH_LW_11_ZIP_PATH_LOGS/installed-long-final/RESULT.json) full MD/ZIP flow и 2 lifecycle cases PASS; отдельный lifecycle case получил FAIL из-за ошибочного ожидания exit 0 в новом --no-browser adapter. Продукт правильно вернул 1: уже работающий Harness отклоняет второй --no-browser launch. В adapter исправлена только эта новая expectation на точное contract value 1; normal browser-launch case отмечен NOT RUN. [Adapter delta](PH_LW_11_ZIP_PATH_LOGS/TEST_ADAPTER_DELTA.json) подтверждает неизменность source/wheel/installer inputs. Старые test files/production launcher не менялись, другие assertions/deadlines прежние.

[Source matrix](PH_LW_11_ZIP_PATH_LOGS/regressions-final/MATRIX.json), [installed wheel HTTP](PH_LW_11_ZIP_PATH_LOGS/runs/installed-final-nonbrowser.log), [wheel browser](PH_LW_11_ZIP_PATH_LOGS/runs/installed-final-browser.log), [installer recovery](PH_LW_11_ZIP_PATH_LOGS/installer-recovery-final/RESULT.json), [unique method results](PH_LW_11_ZIP_PATH_LOGS/METHOD_RESULTS.json), [evidence index](PH_LW_11_ZIP_PATH_LOGS/EVIDENCE_INDEX.json). Каждый run хранит command/interpreter/platform/exit/elapsed/log hash; dependencies связаны environment/build JSON и locks. Секреты/private app-data/raw uploads не опубликованы в evidence.

SKIP не объявлены PASS:

{skips}

Полная прежняя 593-method matrix остаётся исторической. Свежий scoped набор не объявляется полным повтором automatic executor/upper maturity matrix. Прежний незавершённый visual walkthrough не объявлен выполненным.

## Артефакты и оставшиеся gates

[Installer UNSIGNED](windows/Harness-Setup-win-x64.exe), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md), [changed files](PH_LW_11_ZIP_PATH_CHANGED_FILES.md).

- Build `{b['build_id']}`, source digest `{b['engine_build_digest']}`.
- Wheel SHA-256 `{b['wheel_sha256']}`.
- Installer SHA-256 `{b['installer_sha256']}`.
- PACKAGE_FILES SHA-256 `{b['package_manifest_sha256']}`.
- [Final attestation](../_workspace/PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](../_workspace/PH_LW_11_ZIP_PATH/SHA256.txt), [before/after hashes](../_workspace/PH_LW_11_ZIP_PATH/CHANGED_FILE_HASHES.json). Source/build/lib/wheel/frozen inputs, resources/docs mirrors и manifests проверены; integrity PASS не означает full acceptance GO.

Long app-data ZIP-import blocker закрыт на данной native среде. **PH-LW-11: NO-GO** из-за mandatory NOT RUN: clean Windows без developer runtimes, actual Unicode username, physical offline, real disk-full. Sanitized developer host не заменяет clean-machine, Unicode path не заменяет username, ENOSPC injection не заменяет полный том. Signing credentials отсутствуют; installer UNSIGNED.

**LOCAL_WEB_MANUAL: NO-GO** до PH-LW-12; **AUTOMATIC_EXECUTOR: NO-GO**, выключен; полная v0.5.1 **NO-GO / NOT RELEASED**. Podman/positive governed per-Run egress остаются отдельным NO-GO. Прежние PH-LW-04 и PH-LW-05 verdicts не переписаны. Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments. К PH-LW-12 не переходить; Engine/Documentation ZIP не создавать без отдельного явного запроса.
'''
 write(ENGINE/'PH_LW_11_ZIP_PATH_TEST_REPORT.md',report)
 write(ENGINE/'PH_LW_11_ZIP_PATH_CHANGED_FILES.md','''# PH-LW-11 long app-data ZIP-import — изменения

Source IO adapters: `local_web_imports.py`, `local_web_exchange.py`, `local_web_source_refresh.py`, `local_web_sources_service.py`, `inventory.py` (inventory_source), `safety.py` (copy_tree_filtered), `serialization.py` (atomic_write_text); generated build metadata. ZIP validation/governance contracts неизменны. [AST evidence](PH_LW_11_ZIP_PATH_LOGS/LOGIC_DELTA.json).

Новые tests: `tests/test_ph_lw_11_zip_path.py` (7), `local_web/windows/zip_path_acceptance.py` (startup/snapshot adapter, прежние assertions/deadlines). Старые tests не изменены. Новая docs глава 21, ссылки README, generated aggregates/manifests и byte-identical embedded mirror. Пересобраны build/lib/wheel/self-contained bundle/installer из source.

Новые report/logs/workspace input/output evidence, helpers `tools/*ph_lw_11_zip_path*.py`, CURRENT_TASK/navigation. Исторические reports/attestations/archives/r2/specs и чужие изменения сохранены. [Before/after hashes](../_workspace/PH_LW_11_ZIP_PATH/CHANGED_FILE_HASHES.json), [input hashes](../_workspace/PH_LW_11_ZIP_PATH/INPUT_FILE_HASHES.json). Engine/Documentation ZIP не собирались.
''')
 current=f'''# Текущая работа

2026-11-08. **PH-LW-11 long app-data ZIP-import: PASS. PH-LW-11 acceptance: NO-GO.** Automatic executor выключен, PH-LW-12 не начат, Engine/Documentation ZIP не собирались.

[Новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_CHANGED_FILES.md), [глава 21](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md), [installer](../Project_Harness_Engine_v0.5.1/windows/Harness-Setup-win-x64.exe). Предыдущие [long-project report](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md) и исходный PH-LW-11 NO-GO/evidence сохранены.

## Проверенная база и результат

[Baseline](PH_LW_11_ZIP_PATH/INPUT_BASELINE.json), [input hashes](PH_LW_11_ZIP_PATH/INPUT_FILE_HASHES.json), [CURRENT_TASK before](PH_LW_11_ZIP_PATH/CURRENT_TASK.before.md), [final attestation](PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](PH_LW_11_ZIP_PATH/SHA256.txt), [before/after hashes](PH_LW_11_ZIP_PATH/CHANGED_FILE_HASHES.json).

Build `{b['build_id']}`, digest `{b['engine_build_digest']}`. Wheel `{b['wheel_sha256']}`; installer `{b['installer_sha256']}`. Доставка — распакованные файлы, wheel и UNSIGNED installer. Старые архивы неизменны.

До fix новый public ZIP test воспроизвёл WinError 206. После fix: 7 long-app-data tests PASS; source {v['core_methods']} methods в {v['core_scopes']} scopes (2 прежних SKIP, 0 FAIL/ERROR); wheel HTTP/core {v['installed_wheel']['installed-nonbrowser']} PASS и Edge/desktop {v['installed_wheel']['installed-browser']} PASS. Actual installed EXE 4 PASS при длинных project и app-data roots одновременно: retained paths {long['maximum_retained_project_file_path_length']} и {long['maximum_retained_app_data_file_path_length']} символов. Installer recovery 4 PASS. LongPathsEnabled 0 → 0, non-admin/NTFS. [Verdicts](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_LOGS/VERDICTS.json).

## Scope и ограничения

IO-only ZIP upload/snapshot/preview/verified copy, source refresh/recovery/cleanup и manual exchange IO, inventory, filtered copy и atomic writes. AST бизнес-ветвей прежний после удаления IO adapters; names/budgets/CRC/refs/states/approvals/accepted history/schemas не менялись. Старые tests неизменны. Source/wheel/frozen/docs mirror/manifests синхронизированы.

ZIP-import blocker закрыт. PH-LW-11 NO-GO из-за mandatory NOT RUN: clean-machine Windows, actual Unicode username, physical offline, real disk-full. Прежние symlink/alias SKIP, unsigned status и незавершённый visual walkthrough сохранены явно. LOCAL_WEB_MANUAL NO-GO до PH-LW-12. AUTOMATIC_EXECUTOR NO-GO, выключен; полная v0.5.1 NO-GO / NOT RELEASED; Podman/positive egress не закрывались. Полная прежняя matrix — история, свежий scoped набор не равен полному automatic/upper-level rerun.

Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments. К PH-LW-12 не переходить; automatic executor не включать; ZIP без явного запроса не собирать.

Браузер: по явному указанию пользователя не открывать новые видимые окна; для ручной работы использовать уже открытое авторизованное окно. Browser regressions — headless. Обычный real second launch с открытием default browser в свежем повторе NOT RUN; вместо него проверен точный отказ второго --no-browser launch (exit 1), без изменения production launcher.
'''
 write(ROOT/'_workspace/CURRENT_TASK.md',current)
 for p,text in [(ROOT/'README.md','Текущий PH-LW-11: [long app-data ZIP-import report](Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md), [состояние](_workspace/CURRENT_TASK.md). Scoped ZIP fix PASS; полная acceptance NO-GO. Automatic executor выключен; PH-LW-12 не начат; ZIP не собирались.'),(ROOT/'_workspace/PROJECT_MAP.md','Актуальный PH-LW-11: [long app-data ZIP-import](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md), [глава 21](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/21_PH_LW_11_Long_App_Data_ZIP_Import.md). Verified hashes/scope — [CURRENT_TASK](CURRENT_TASK.md). Предыдущие checkpoints ниже сохранены.')]:
  write(p,text+'\n\n'+p.read_text('utf-8'))
 with (ROOT/'_workspace/RUNBOOK.md').open('a',encoding='utf-8') as stream:stream.write('''
## PH-LW-11 — long app-data ZIP-import

Новое задание разрешило соседний ZIP IO fix: `_workspace/PH_LW_11_ZIP_PATH`, `Engine/PH_LW_11_ZIP_PATH_LOGS`, [новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_ZIP_PATH_TEST_REPORT.md). Старые LONG_PATH и исходные PH-LW-11 reports/attestations не перезаписывать.

Target `tests.test_ph_lw_11_zip_path` (7): public upload/replay/replace, old snapshots, hostile ZIP bytes/CRC/budgets, explicit recovery, deep tamper/junction/hardlink/copy-time guard. Независимый snapshot reader читает все deep files. `zip_path_acceptance.py` сохраняет прежние 4 installed-EXE assertions/deadlines; default app-data root находится внутри длинного output, длинный Unicode runtime-root новый для каждого run. Не применять прежний short app-data workaround для закрытия ZIP blocker, не менять registry/защиту Windows.

Wheel: fresh venv, pinned hash locks, empty PYTHONPATH/Unicode CWD/explicit msedge, `run_ph_lw_11_zip_path_wheel.py`. `check_ph_lw_11_zip_path_logic.py` — AST proof в дополнение к runtime tests. Build/freeze → applicable tests → `finalize_ph_lw_11_zip_path.py` → `report_ph_lw_11_zip_path.py` → sync manifests без rebuild → `verify_ph_lw_11_zip_path.py`. Source/docs/wheel inputs после freeze не менять; изменения требуют rebuild/retest. Evidence publisher использует allowlist и не публикует app-data/auth/raw uploads. Engine/Documentation ZIP и PH-LW-12 без отдельного задания запрещены.

Пользователь запретил новые видимые browser windows: ручной UI — в уже открытом авторизованном окне. Автотесты Edge headless. В zip_path_acceptance второй процесс запускается с --no-browser и должен получить точный отказ exit 1, сохранив first process/catalog; обычный browser-opening second launch — свежий NOT RUN. Не менять production launcher или ослаблять auth ради этой проверки.
''')
 print('New PH-LW-11 ZIP-path report/current task written; full acceptance NO-GO')
if __name__=='__main__':main()
