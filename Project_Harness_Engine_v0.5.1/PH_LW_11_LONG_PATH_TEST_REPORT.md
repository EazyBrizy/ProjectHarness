# PH-LW-11 — исправление long-path подготовки

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
| Installed wheel HTTP/core | 42 PASS, 0 SKIP; site-packages, независимая venv/Unicode CWD, console doctor/launcher/TCP; включая все 3 long-path cases |
| Installed wheel browser/desktop | 33 PASS, 0 SKIP; настоящий Edge/TCP, desktop/multi-tab/auth/XSS и применимые PH-LW-04–10 scenarios |
| Source core/Windows regressions | 18 module/class scopes, 232 methods; статусы {'PASS_WITH_SKIPS': 2, 'PASS': 16} |
| Установленный self-contained EXE в длинном Unicode profile path | 4 PASS, 0 errors/FAIL/SKIP; MD и ZIP → GPT fixture → separate approvals → project/JIT/download; restart/second launch/port collision/crash/stop; install/uninstall сохранность |
| Actual installer recovery | 4 PASS: прерывание копирования, восстановление, read-only pointer rejection, успешный retry |
| Fresh unique method coverage | 298 методов; {'PASS': 296, 'SKIP': 2} |

Максимальная длина retained project file path в actual EXE run — **281**. [Installed result](PH_LW_11_LONG_PATH_LOGS/installed-long-final/RESULT.json) подтверждает LongPathsEnabled=0 до и после, NTFS/non-admin, System32-only child PATH, empty PYTHONPATH и uninstall byte preservation. USERPROFILE/project root — длинный Unicode path; app-data — отдельный короткий fixture path, заданный --app-data-root. Test-only snapshot adapter читает каждый глубокий project file и фактический app-data через independent extended IO; исходные assertions/deadlines browser scenario не менялись. Это не проверка произвольно длинного app-data/intake root. [Adapter delta](PH_LW_11_LONG_PATH_LOGS/TEST_ADAPTER_DELTA.json) подтверждает неизменность artifact inputs.

Первый [installed run](PH_LW_11_LONG_PATH_LOGS/installed-long/RESULT.json) сохранил FAIL второго ZIP upload до preparation; первый MD project уже был опубликован с длинными paths, а 3 lifecycle tests прошли. [Public source diagnostic](PH_LW_11_LONG_PATH_LOGS/runs/long-appdata-zip-diagnostic-2.log) подтвердил WinError 206 в local_web_imports._private_directory при создании quarantine/materialized/LSD-* в длинном app-data root. Начальный diagnostic с неверным mode=ADD сохранён отдельно и не является доказательством причины. Этот соседний PH-LW-05 IO не изменён в preparation-only fix. В повторе app-data размещён в обычном коротком fixture root; project/profile root стал на символ длиннее. Исходный FAIL не закрыт коротким app-data PASS и остаётся отдельным manual blocker PH-LW-11.

Второй [run с коротким app-data](PH_LW_11_LONG_PATH_LOGS/installed-long-verified/RESULT.json) также сохранил общий FAIL: первый длинный project опубликован и 3 lifecycle cases PASS, но save answers второго intake получил явный OPERATION_CONFLICT. Это fail-closed operation fence, а не подтверждённый IO failure; точная interleaving причина не установлена. После завершения остальных suites один отдельный run на новых fixtures прошёл исходные assertions/deadlines. Guard не ослаблен, автоматический POST retry не добавлен, первые monolithic FAIL не объявлены PASS и product fix этого transient conflict не заявляется.

[Public API recheck](PH_LW_11_LONG_PATH_LOGS/public-recheck/RESULT.json), [wheel HTTP](PH_LW_11_LONG_PATH_LOGS/runs/installed-nonbrowser.log), [wheel browser](PH_LW_11_LONG_PATH_LOGS/runs/installed-browser.log), [source matrix](PH_LW_11_LONG_PATH_LOGS/regressions/MATRIX.json), [fresh method results](PH_LW_11_LONG_PATH_LOGS/METHOD_RESULTS.json), [installer recovery](PH_LW_11_LONG_PATH_LOGS/installer-recovery/RESULT.json), [evidence index](PH_LW_11_LONG_PATH_LOGS/EVIDENCE_INDEX.json). Команды, interpreter/platform/exit/time/log hashes сохранены в run JSON; dependencies — в SOURCE_ENVIRONMENT/WHEEL_ENVIRONMENT и hash locks/BUILD_RESULT. [Host settings](../_workspace/PH_LW_11_LONG_PATH/SOURCE_ENVIRONMENT.json).

Прежние native file-symlink SKIP из-за отсутствующей привилегии сохранены: [{'test': 'tests.test_contract_hardening.ContractHardeningControlPlaneTests.test_agent_result_symlink_is_rejected', 'reason': 'NOT RUN: native file symlink creation requires a Windows privilege unavailable to this non-admin user'}, {'test': 'tests.test_ph_lw_02_windows_core.WindowsCoreBoundaryTests.test_05_colliding_tree_rejected_without_rewriting_case', 'reason': 'NTFS casefold aliases require a case-sensitive directory; ZIP test is cross-platform'}]. Настройки/права ОС ради них не менялись. Полная прежняя 593-method matrix и семь automatic/platform FAIL modules остаются историческими результатами. В этом дополнении выполнены перечисленные свежие scoped regressions; automatic executor и полный верхнеуровневый maturity matrix не запускались и не повышены до PASS.

## Поставка, ограничения и verdicts

[Installer UNSIGNED](windows/Harness-Setup-win-x64.exe), [build recipe](local_web/windows/build_windows.py), [long-path EXE runner](local_web/windows/long_path_acceptance.py), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/20_PH_LW_11_Long_Path_Preparation.md).

- Build `PH-LW-11-LONGPATH-20261108`, source digest `sha256:cff006d0c0ef48ee942d5c7bdfb96c34e01c2f59c0682ca19a76a907cdd4559b`.
- Wheel SHA-256 `60a77d83e27de1e3e914ab7a21df1aa50d0348c07199765fb1ef33f9ffc15f40`.
- Installer SHA-256 `43cc06e7e3d1eac23133e1d324c911fb943ae37c403ef36dd860d766e37c2741`.
- PACKAGE_FILES SHA-256 `4764867437d4702aab529566c432957d73c9c84c8bdf255d135e1f3d4f9e0f38`.
- [Final integrity attestation](../_workspace/PH_LW_11_LONG_PATH/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](../_workspace/PH_LW_11_LONG_PATH/SHA256.txt). Docs mirror/source/build/lib/wheel/frozen resources сверены; integrity PASS не равен full acceptance GO.

Long-path preparation blocker закрыт на данной native среде. Это не утверждение о любом Windows filesystem или всех будущих product-command environments. Уже сохранённые partial stages не удаляются; stale engine/input bindings и явная recovery остаются действующими. Никаких автоматических compiler replays после commit не добавлено.

**PH-LW-11/LOCAL_WEB_MANUAL: NO-GO** из-за отдельного long app-data ZIP-import FAIL и mandatory NOT RUN: clean Windows без developer runtimes, actual Unicode username, physical offline, real disk-full. Developer host с очищенным PATH не заменяет clean-machine; injected ENOSPC не заменяет полный том. Signing credentials отсутствуют: UNSIGNED, отсутствие SmartScreen warnings не обещается. Прежний visual walkthrough остался незавершённым и не объявлен выполненным этим дополнением. Прежние PH-LW-04/05 acceptance reports не переписаны; свежий FAIL расширенного app-data scenario указан явно и не списан на automatic NO-GO.

**AUTOMATIC_EXECUTOR: NO-GO, выключен. Полная v0.5.1: NO-GO / NOT RELEASED.** Podman/positive governed egress не закрывались. Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments; PH-LW-12 не запускать. ZIP не создавались, прежние архивы неизменны.
