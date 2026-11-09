"""Write the new PH-LW-11 report; do not rewrite the original NO-GO."""
import json
from package_acceptance import ROOT,ENGINE
W=ROOT/'_workspace/PH_LW_11_LONG_PATH';O=ENGINE/'PH_LW_11_LONG_PATH_LOGS'
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,text):p.write_text(text,'utf-8')
def main():
 v=read(O/'VERDICTS.json');b=read(O/'BUILD_PROVENANCE.json');core=read(O/'regressions/MATRIX.json')
 report=f'''# PH-LW-11 — исправление long-path подготовки

2026-11-08. **LONG_PATH_PREPARATION: PASS. PH-LW-11: NO-GO.** Прежний long-path blocker подготовки устранён на настоящем Windows 11 x64/NTFS/non-admin при LongPathsEnabled=0. System settings не менялись. Отдельный длинный app-data ZIP-import остаётся FAIL; mandatory clean-machine/Unicode username/physical offline/real disk-full — NOT RUN. Automatic executor выключен; PH-LW-12 не начат; Engine/Documentation ZIP не создавались.

## База и разрешённая область

Отдельное задание пользователя разрешило исправление long-path FAIL подготовки. База — [предыдущий PH-LW-11 NO-GO](PH_LW_11_TEST_REPORT.md) с [проверенной аттестацией](../_workspace/PH_LW_11/FINAL_WORKING_TREE_VERIFICATION.json). Старый report, его logs и аттестация сохранены побайтово. [Новая input baseline](../_workspace/PH_LW_11_LONG_PATH/INPUT_BASELINE.json), [input hashes](../_workspace/PH_LW_11_LONG_PATH/INPUT_FILE_HASHES.json); входные manifests/wheel/installer проверены без drift.

Allowed changes: IO-копирование и чтение длинных paths в preparation/publication/validation/first JIT; необходимые shared hashing/serialization/control-plane/Stage read helpers; новые tests и Windows acceptance adapter, build metadata, source-generated wheel/frozen installer, docs/mirror/manifests/reports/navigation. Schemas/registries, approvals, states, scope, refs/digests и immutable history не изменялись. [Before/after hashes](../_workspace/PH_LW_11_LONG_PATH/CHANGED_FILE_HASHES.json).

## Причина и исправление

Обычный Win32 path у copied `.harness` превышал MAX_PATH. `shutil.copytree` получал WinError 3. Замена только copy IO обнаружила дополнительные реальные ошибки: validators считали длинные schemas/registry/JIT/Stage State отсутствующими либо не могли прочитать их, а phase-boundary reader ошибочно выбирал fallback вместо существующего operation journal. Исходные ошибки и промежуточные diagnostic runs сохранены отдельно.

В `platform_fs` добавлены private `_native_io_path` и traversal adapters. Они преобразуют проверенное обычное drive spelling только для IO; UNC/device/ADS и недопустимые компоненты не получают authority. Существующие ownership/reparse/lock guards остаются действующими. Native traversal возвращает обычные логические paths. Compiler копирует tree через extended IO; validators, manifest hashing, protected-file scan, Stage target/index reader и first JIT reader используют тот же IO boundary. Public paths, refs, serialized records и successful UI results остаются без extended prefix.

Семантические ожидания не ослаблены. [AST delta](PH_LW_11_LONG_PATH_LOGS/LOGIC_DELTA.json) подтверждает идентичность business logic семи затронутых файлов после удаления явных IO adaptations. Это дополнительное static evidence; фактические positive/negative/recovery проверки приведены ниже. Старые tests и все normative/r2 источники сохранены.

## Фактические проверки

| Проверка | Результат |
|---|---|
| Исходный public `prepare_handoff` blocker | Исторический FAIL при leaf length 277 сохранён; новый тот же public API при length 281 — PASS, initial и mutable validation PASS, LongPathsEnabled 0 → 0 |
| Long-path tests | 3 PASS: service publication/validators/first JIT/replay/read-only reads; tampered deep schema → FAIL; after-rename recovery без compiler replay; device/UNC/ADS rejection |
| Installed wheel HTTP/core | {v['installed_wheel']['installed-nonbrowser']} PASS, 0 SKIP; site-packages, независимая venv/Unicode CWD, console doctor/launcher/TCP; включая все 3 long-path cases |
| Installed wheel browser/desktop | {v['installed_wheel']['installed-browser']} PASS, 0 SKIP; настоящий Edge/TCP, desktop/multi-tab/auth/XSS и применимые PH-LW-04–10 scenarios |
| Source core/Windows regressions | {v['core_scopes']} module/class scopes, {v['core_methods']} methods; статусы {dict(__import__('collections').Counter(r['status'] for r in core))} |
| Установленный self-contained EXE в длинном Unicode profile path | {v['installed_exe_tests']['ran']} PASS, 0 errors/FAIL/SKIP; MD и ZIP → GPT fixture → separate approvals → project/JIT/download; restart/second launch/port collision/crash/stop; install/uninstall сохранность |
| Actual installer recovery | 4 PASS: прерывание копирования, восстановление, read-only pointer rejection, успешный retry |
| Fresh unique method coverage | {v['fresh_unique_methods']} методов; {v['method_statuses']} |

Максимальная длина retained project file path в actual EXE run — **{v['maximum_project_file_path_length']}**. [Installed result](PH_LW_11_LONG_PATH_LOGS/installed-long-final/RESULT.json) подтверждает LongPathsEnabled=0 до и после, NTFS/non-admin, System32-only child PATH, empty PYTHONPATH и uninstall byte preservation. USERPROFILE/project root — длинный Unicode path; app-data — отдельный короткий fixture path, заданный --app-data-root. Test-only snapshot adapter читает каждый глубокий project file и фактический app-data через independent extended IO; исходные assertions/deadlines browser scenario не менялись. Это не проверка произвольно длинного app-data/intake root. [Adapter delta](PH_LW_11_LONG_PATH_LOGS/TEST_ADAPTER_DELTA.json) подтверждает неизменность artifact inputs.

Первый [installed run](PH_LW_11_LONG_PATH_LOGS/installed-long/RESULT.json) сохранил FAIL второго ZIP upload до preparation; первый MD project уже был опубликован с длинными paths, а 3 lifecycle tests прошли. [Public source diagnostic](PH_LW_11_LONG_PATH_LOGS/runs/long-appdata-zip-diagnostic-2.log) подтвердил WinError 206 в local_web_imports._private_directory при создании quarantine/materialized/LSD-* в длинном app-data root. Начальный diagnostic с неверным mode=ADD сохранён отдельно и не является доказательством причины. Этот соседний PH-LW-05 IO не изменён в preparation-only fix. В повторе app-data размещён в обычном коротком fixture root; project/profile root стал на символ длиннее. Исходный FAIL не закрыт коротким app-data PASS и остаётся отдельным manual blocker PH-LW-11.

Второй [run с коротким app-data](PH_LW_11_LONG_PATH_LOGS/installed-long-verified/RESULT.json) также сохранил общий FAIL: первый длинный project опубликован и 3 lifecycle cases PASS, но save answers второго intake получил явный OPERATION_CONFLICT. Это fail-closed operation fence, а не подтверждённый IO failure; точная interleaving причина не установлена. После завершения остальных suites один отдельный run на новых fixtures прошёл исходные assertions/deadlines. Guard не ослаблен, автоматический POST retry не добавлен, первые monolithic FAIL не объявлены PASS и product fix этого transient conflict не заявляется.

[Public API recheck](PH_LW_11_LONG_PATH_LOGS/public-recheck/RESULT.json), [wheel HTTP](PH_LW_11_LONG_PATH_LOGS/runs/installed-nonbrowser.log), [wheel browser](PH_LW_11_LONG_PATH_LOGS/runs/installed-browser.log), [source matrix](PH_LW_11_LONG_PATH_LOGS/regressions/MATRIX.json), [fresh method results](PH_LW_11_LONG_PATH_LOGS/METHOD_RESULTS.json), [installer recovery](PH_LW_11_LONG_PATH_LOGS/installer-recovery/RESULT.json), [evidence index](PH_LW_11_LONG_PATH_LOGS/EVIDENCE_INDEX.json). Команды, interpreter/platform/exit/time/log hashes сохранены в run JSON; dependencies — в SOURCE_ENVIRONMENT/WHEEL_ENVIRONMENT и hash locks/BUILD_RESULT. [Host settings](../_workspace/PH_LW_11_LONG_PATH/SOURCE_ENVIRONMENT.json).

Прежние native file-symlink SKIP из-за отсутствующей привилегии сохранены: {v['core_skips']}. Настройки/права ОС ради них не менялись. Полная прежняя 593-method matrix и семь automatic/platform FAIL modules остаются историческими результатами. В этом дополнении выполнены перечисленные свежие scoped regressions; automatic executor и полный верхнеуровневый maturity matrix не запускались и не повышены до PASS.

## Поставка, ограничения и verdicts

[Installer UNSIGNED](windows/Harness-Setup-win-x64.exe), [build recipe](local_web/windows/build_windows.py), [long-path EXE runner](local_web/windows/long_path_acceptance.py), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md).

- Build `{b['build_id']}`, source digest `{b['engine_build_digest']}`.
- Wheel SHA-256 `{b['wheel_sha256']}`.
- Installer SHA-256 `{b['installer_sha256']}`.
- PACKAGE_FILES SHA-256 `{b['package_manifest_sha256']}`.
- [Final integrity attestation](../_workspace/PH_LW_11_LONG_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](../_workspace/PH_LW_11_LONG_PATH/SHA256.txt). Docs mirror/source/build/lib/wheel/frozen resources сверены; integrity PASS не равен full acceptance GO.

Long-path preparation blocker закрыт на данной native среде. Это не утверждение о любом Windows filesystem или всех будущих product-command environments. Уже сохранённые partial stages не удаляются; stale engine/input bindings и явная recovery остаются действующими. Никаких автоматических compiler replays после commit не добавлено.

**PH-LW-11/LOCAL_WEB_MANUAL: NO-GO** из-за отдельного long app-data ZIP-import FAIL и mandatory NOT RUN: clean Windows без developer runtimes, actual Unicode username, physical offline, real disk-full. Developer host с очищенным PATH не заменяет clean-machine; injected ENOSPC не заменяет полный том. Signing credentials отсутствуют: UNSIGNED, отсутствие SmartScreen warnings не обещается. Прежний visual walkthrough остался незавершённым и не объявлен выполненным этим дополнением. Прежние PH-LW-04/05 acceptance reports не переписаны; свежий FAIL расширенного app-data scenario указан явно и не списан на automatic NO-GO.

**AUTOMATIC_EXECUTOR: NO-GO, выключен. Полная v0.5.1: NO-GO / NOT RELEASED.** Podman/positive governed egress не закрывались. Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments; PH-LW-12 не запускать. ZIP не создавались, прежние архивы неизменны.
'''
 write(ENGINE/'PH_LW_11_LONG_PATH_TEST_REPORT.md',report)
 write(ENGINE/'PH_LW_11_LONG_PATH_CHANGED_FILES.md','''# PH-LW-11 long-path — изменения

IO-only source adaptations: `platform_fs.py`, `compiler.py`, `hashing.py`, `serialization.py`, `workspace.py`, `validation.py`, `stages.py`, `materialization.py`, `local_web_preparation.py`; generated build metadata. Никаких новых governance statuses/CLI controls/schemas.

Новые tests: `tests/test_ph_lw_11_long_path.py`, `local_web/windows/long_path_acceptance.py`. Старые tests неизменны. Новая docs глава 20 и ссылка из главы 19/README; aggregates/manifests и byte-identical mirror. Source-generated build/lib/wheel/frozen installer. Новые logs/reports/workspace baseline/attestation и helpers `tools/*ph_lw_11_long_path*.py`; CURRENT_TASK/navigation.

Исторические PH-LW-11 report/logs/attestation, normative/r2, `_inputs`, schemas/registries и старые архивы сохранены. [Before/after hashes](../_workspace/PH_LW_11_LONG_PATH/CHANGED_FILE_HASHES.json), [input hashes](../_workspace/PH_LW_11_LONG_PATH/INPUT_FILE_HASHES.json), [отчёт](PH_LW_11_LONG_PATH_TEST_REPORT.md).
''')
 write(ROOT/'_workspace/CURRENT_TASK.md',f'''# Текущая работа

2026-11-08. **PH-LW-11 long-path preparation: PASS. PH-LW-11 acceptance: NO-GO.** Automatic executor выключен; PH-LW-12 не начат; Engine/Documentation ZIP не создавались.

[Новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md), [изменения](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_CHANGED_FILES.md), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md), [installer](../Project_Harness_Engine_v0.5.1/windows/Harness-Setup-win-x64.exe). [Исходный NO-GO](../Project_Harness_Engine_v0.5.1/PH_LW_11_TEST_REPORT.md) и его evidence/attestation сохранены.

## Проверенная база и результат

[Input baseline](PH_LW_11_LONG_PATH/INPUT_BASELINE.json), [input hashes](PH_LW_11_LONG_PATH/INPUT_FILE_HASHES.json), [прежний CURRENT_TASK](PH_LW_11_LONG_PATH/CURRENT_TASK.before.md), [новая аттестация](PH_LW_11_LONG_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](PH_LW_11_LONG_PATH/SHA256.txt), [before/after hashes](PH_LW_11_LONG_PATH/CHANGED_FILE_HASHES.json).

Build `{b['build_id']}`, digest `{b['engine_build_digest']}`. Installer SHA-256 `{b['installer_sha256']}`, wheel `{b['wheel_sha256']}`. Доставка — обычные распакованные файлы и UNSIGNED installer; архивы не обновлялись.

Public prepare_handoff повторён с leaf path 281: PASS. 3 long-path tests PASS, wheel {v['installed_wheel']} PASS, source core/Windows {v['core_methods']} methods в {v['core_scopes']} scopes. Фактический EXE: 4 PASS, retained file path до {v['maximum_project_file_path_length']} символов; installer recovery 4 PASS. LongPathsEnabled оставался 0, non-admin/NTFS; системные защитные настройки не менялись. [Свежие verdicts](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_LOGS/VERDICTS.json).

## Scope и оставшиеся gates

Разрешённый IO fix затронул только preparation/publication/validators, hashing/serialization/control-plane и Stage read helpers. States/approvals/refs/digests/accepted history/schemas не изменены. Старые tests неизменны; semantic ожидания не ослаблены. Source+wheel+frozen assets и docs mirror синхронизированы.

PH-LW-11 и LOCAL_WEB_MANUAL остаются NO-GO: отдельный ZIP-import FAIL в длинном app-data root (WinError 206 при создании quarantine/materialized; соседний PH-LW-05 IO не изменён), а также clean-machine Windows, actual Unicode username, physical offline, real disk-full — mandatory NOT RUN. Повторный EXE run использует короткий app-data и более длинный project root; он не закрывает исходный ZIP-import FAIL. Прежние file-symlink SKIP, unsigned status и незавершённый visual walkthrough не скрыты. Полная прежняя matrix — историческая; свежий scoped набор не объявлен полным повтором всех automatic/upper-level tests. AUTOMATIC_EXECUTOR NO-GO, полная v0.5.1 NO-GO / NOT RELEASED; Podman/positive egress не закрывались.

Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments. К PH-LW-12 не переходить, automatic executor не включать, ZIP без явного запроса не собирать.
''')
 for p,text in [(ROOT/'README.md','Текущая работа — PH-LW-11 long-path fix: [состояние](_workspace/CURRENT_TASK.md), [новый отчёт](Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md). Long-path preparation PASS, полная acceptance NO-GO; automatic executor выключен, PH-LW-12 не начат, ZIP не создавались.'),
  (ROOT/'_workspace/PROJECT_MAP.md','Актуальный PH-LW-11 long-path fix: [новый отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md), [глава 20](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md). Scope и verified hashes — [CURRENT_TASK](CURRENT_TASK.md). Предыдущие checkpoints ниже сохранены.')]:
  old=p.read_text('utf-8');write(p,text+'\n\n'+old)
 with (ROOT/'_workspace/RUNBOOK.md').open('a',encoding='utf-8') as stream:stream.write('''
## PH-LW-11 — long-path дополнение

Отдельный output/baseline: `_workspace/PH_LW_11_LONG_PATH`, `Engine/PH_LW_11_LONG_PATH_LOGS`; [отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_11_LONG_PATH_TEST_REPORT.md). Не перезаписывать прежнюю PH-LW-11 аттестацию.

Targeted source tests: `tests.test_ph_lw_11_long_path`. Independent installed wheel использует прежний `verify_installed.py --case ...`, empty PYTHONPATH/Unicode CWD/explicit msedge. `local_web/windows/long_path_acceptance.py` запускает прежние 4 EXE assertions, адаптируя startup roots и полный fixture snapshot IO; runtime-root должен быть новым длинным Unicode path, --app-data-root — отдельным новым коротким fixture path. Не менять registry/защиту Windows и не сокращать project path ради PASS. Первый длинный app-data ZIP-import FAIL сохраняется отдельно. Installer recovery — прежний `installer_fault_acceptance.py` с новым output.

`finalize_ph_lw_11_long_path.py` публикует только allowlisted evidence, `report_ph_lw_11_long_path.py` пишет новый report/navigation, затем `sync_working_tree.py` без rebuild и `verify_ph_lw_11_long_path.py`. Изменение wheel/frozen inputs требует новой сборки и применимых проверок. Никаких Engine/Documentation ZIP и перехода к PH-LW-12 без нового задания.
''')
 print('New PH-LW-11 long-path report/current task written; full acceptance NO-GO')
if __name__=='__main__':main()
