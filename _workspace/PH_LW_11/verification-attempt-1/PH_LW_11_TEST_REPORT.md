# PH-LW-11 — Windows launcher и self-contained installer

2026-11-08. **PH-LW-11: NO-GO.** Реальный unsigned Windows installer собран, код и документация обновлены. Доступные проверки выполнены; current regression matrix закрыта по test IDs без новых failures относительно PH-LW-10. Полная приёмка не закрыта: есть manual long-path FAIL и mandatory NOT RUN. Automatic executor выключен, PH-LW-12 не начат, Engine/Documentation ZIP не создавались.

## База и область

Выполнена реализация по [полному prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_11.md) на проверенной распакованной базе PH-LW-10. [Input baseline](../_workspace/PH_LW_11/INPUT_BASELINE.json), [input hashes](../_workspace/PH_LW_11/INPUT_FILE_HASHES.json), [предыдущий CURRENT_TASK](../_workspace/PH_LW_11/CURRENT_TASK.before.md). Входные manifests/wheel проверены, drift отсутствовал. Историческое требование ZIP-пары заменено явным запретом пользователя; сам prompt не переписан.

Allowed changes: Windows launcher/instance/desktop lifecycle/resource discovery/packaging/build, HTTP/UI integration stop/resume/manual login, доказанный direct upload regression fix, новые tests/docs/metadata/generated build/wheel/frozen bundle/manifests/reports/evidence/workspace navigation. Core governance/compiler/runtime/migration algorithms, schemas/registries, old tests, normative/r2 и исторические NO-GO неизменны. [Changed files](PH_LW_11_CHANGED_FILES.md), [before/after hashes](../_workspace/PH_LW_11/CHANGED_FILE_HASHES.json).

## Реализованное поведение

Pinned CPython 3.14.10 x64 + PyInstaller 6.22.3 onedir + Inno Setup 6.7.4. Installer включает Python runtime, pinned dependencies, static/docs/schema/registry/template/fixture assets и licenses. Per-user app directory отделён от app-data/intakes/projects. Никаких end-user pip/download/CDN, PATH/firewall/ExecutionPolicy changes, WSL/Podman installation или auto-update.

Один OS mutex на SID пользователя, отдельный mutually authenticated HMAC launcher channel с current-user DPAPI secret и fresh nonces. Порт резервируется реальным exclusive loopback bind. Unknown listener/occupied port не получает authority, чужие процессы не завершаются. Bootstrap не выводится в logs. Second launch открывает имеющийся server; resume хранит только opaque selection/revision вне canonical state.

GET/polling остаётся read-only. Новые POST сохраняют Host/Origin/port/session/CSRF, resume — CAS. Browser close не отменяет mutations; explicit stop проверяет HTTP/worker activity, закрывает admission и server. Native fallback показывает локальный адрес и одноразовый код. `Harness.exe` отвергает `-c`/scripts; source/wheel core CLI работает отдельно.

Installer проверяет compiled SHA-256 до исполнения extracted helper, затем exact inventory; staged copy → verify → version rename → atomic current pointer. Foreign nonempty destination, reparse/hardlinks, altered/extra files отвергаются. Live version не перезаписывается. Uninstall удаляет перечисленные app files и сохраняет projects/app-data; cleanup объяснён отдельно. Публичные Engine APIs и canonical state contracts не заменены UI logic.

## Фактические результаты

| Проверка | Результат |
|---|---|
| Финальный installed EXE | **4 PASS**, 0 SKIP: MD и ZIP → GPT fixture → отдельные approvals → Project Instance/JIT/download; restart/resume/second launch/port collision; idle crash/stale record; package doctor/interpreter refusal |
| Actual install/uninstall | PASS; foreign target exit 7, штатные install/uninstall exit 0; executable удалён, project/app-data bytes сохранены |
| Actual installer failure/recovery | **4 PASS**: interruption during staging copy, retry, read-only current pointer rejection, retry after restoring own fixture permission |
| Final source desktop tests | **18 PASS**, 0 SKIP: auth/resume/CAS/stop/busy, native mutex/DPAPI/handshake/spoof refusal, integrity/long-path/junction/hardlink/ENOSPC/read-only, реальный Edge manual login/upload race/multi-tab resume |
| Final installed wheel recheck | **31 PASS**, 0 SKIP: desktop, PH-LW-01, PH-LW-04 browser/XSS, прежний PH-LW-07 multi-tab approvals; независимая venv/Unicode CWD/site-packages, console doctor/launcher/TCP health |
| Installed wheel composite | **93 уникальных PASS**; ранее 69 non-browser PASS и полный последующий 38-method run с 2 ERROR, закрытыми final recheck; builds и supersession указаны отдельно |
| Source native aggregate | ABORTED, не PASS; 107 завершённых PASS сохранены отдельно |
| Ранний wheel browser aggregate | ABORTED после stalled browser.close; не PASS; последующие завершённые rechecks покрыли все cases |
| Upload race deterministic before/after | FAIL до исправления, PASS после; финальный EXE пересобран и полный flow повторён успешно |
| Manual-code Edge test | Final source/wheel PASS; исходные teardown TIMEOUT сохранены |
| Multi-tab resume regression | Детерминированный FAIL до исправления, source/wheel PASS после; старый PH-LW-07 test неизменён |
| PH-F06 | 13 PASS, 0 SKIP |
| PH-LW-10 advanced lifecycle recheck на frozen source | PASS; [отдельный log](PH_LW_11_LOGS/runs/lifecycle-frozen-recheck.log) |
| Current method matrix | 50 modules / 593 ожидаемых методов: {'PASS': 501, 'SKIP': 7, 'ERROR': 68, 'FAIL': 17} |
| Current module matrix | {'PASS': 40, 'PASS_WITH_SKIPS': 3, 'FAIL': 7} |

[EXE result](PH_LW_11_LOGS/installed-tab-final/RESULT.json), [installer recovery](PH_LW_11_LOGS/installer-fault-tab-verified/RESULT.json), [source desktop](PH_LW_11_LOGS/runs/desktop-source-tab-final.log), [final wheel](PH_LW_11_LOGS/runs/installed-tab-final.log), [method matrix](PH_LW_11_LOGS/REGRESSION_MATRIX_CURRENT.json), [comparison with PH-LW-10](PH_LW_11_LOGS/PREVIOUS_BASELINE_COMPARISON.json), [evidence index](PH_LW_11_LOGS/EVIDENCE_INDEX.json).

EXE tests выполнены на настоящем Windows 11 x64/NTFS/non-admin; runtime получил System32-only PATH, empty PYTHONPATH и независимые Unicode CWD/profile/app-data. Developer Python/Playwright были test driver. Это **не clean-machine acceptance**. Browser scenario проверяет отсутствие external app requests, но не заменяет physical offline. Unicode directory не заменяет actual Unicode username.

[Environment bindings](PH_LW_11_LOGS/RUN_ENVIRONMENT_BINDINGS.json) связывают команды, interpreter/dependencies/platform и результаты каждого run с source/wheel/builder environment; исходные JSON/logs сохраняют exit и причины FAIL/SKIP/TIMEOUT/ABORT. Pinned versions: CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, Playwright 1.64.1; runtime/build hashes и licenses включены в build evidence.

Общая core matrix была запущена до последних UI/metadata пересборок. Неизменность core algorithms/old tests проверена hashes; [последний delta](PH_LW_11_LOGS/TAB_RESUME_DELTA.json) содержит только app.js и generated metadata. Это composite по уникальным methods с явным supersession, а не монолитный exit 0 финального build. Первый PH-LW-10 advanced case получил ERROR и общий module TIMEOUT; отдельный recheck этого case PASS, все остальные methods завершены в последующих runs. Исходные ERROR/TIMEOUT не переписаны. Семь прежних automatic/platform FAIL имеют те же exact failed IDs; manual failures не списываются на automatic NO-GO.

## Диагностика и исправления

Первый setup attempt с CreateAppDir=no получил системный destination и отказ доступа; исправлено CreateAppDir=yes. Следующие attempts выявили Win32 long-path limit. Manifest LongPathAware сам по себе не помог при LongPathsEnabled=0; installer IO переведён на internal extended paths после проверки обычного local path, с проверкой reparse до обхода дерева. Системные настройки не менялись. Финальные native long-path/junction/hardlink checks PASS.

Frozen flow выявил UI race: upload success отображался до awaited refresh и снятия requestBusy, поэтому ранний переход к интервью мог молча отклонить save. Новый Edge test с задержанным GET воспроизвёл FAIL. Success теперь публикуется после refresh/освобождения busy. [Delta](PH_LW_11_LOGS/UPLOAD_FIX_DELTA.json), [before](PH_LW_11_LOGS/runs/upload-race-repro.log), [after](PH_LW_11_LOGS/runs/upload-race-fixed.log). Old assertions/deadlines/test bytes не менялись.

Первый short-profile EXE run имел 4 PASS, но общий runner FAIL на Chrome lockfile при чрезмерно широком retention snapshot. Snapshot ограничен Harness-owned state/projects; финальный actual uninstall PASS. Один desktop attempt пересёкся с собственным running EXE и получил mutex conflict; изолированный run повторён успешно. Ранние upload-test attempts имели ошибки cleanup route/PYTHONPATH; они сохранены и не используются как regression proof. `build-first` installer перекомпилировался при диагностике, поэтому его первый BUILD_RESULT не аттестует изменённый intermediate binary. Финальная поставка связана только с `build-tab-final`.

Первый recovery attempt финального installer истёк через 12 секунд до начала staging copy; installer продолжил проверку payload и затем штатно установился. Это FAIL runner, не наблюдаемое interruption. Новый runner использует ограниченные 120 секунд wall clock и прежние assertions: увидеть реальные скопированные файлы, остановить только собственное process tree до commit, выполнить recovery/read-only/retry. [Delta test harness](PH_LW_11_LOGS/INSTALLER_TEST_RUNNER_DELTA.json) подтверждает, что artifact inputs/source/wheel/installer не менялись; прежние product tests/deadlines не ослаблены. [Неудачный run](PH_LW_11_LOGS/runs/installer-fault-tab-final.run.json) сохранён отдельно от успешного verified run.

На позднем wheel run manual-code test завис в browser.close после assertions. Минимальная программа без Harness, только Edge `about:blank` → browser.close, повторила TIMEOUT в обеих venv. [Minimal source](PH_LW_11_LOGS/runs/minimal-close-source.run.json), [minimal wheel](PH_LW_11_LOGS/runs/minimal-close-wheel.run.json), [driver trace](PH_LW_11_LOGS/runs/minimal-close-debug.log). После завершения тяжёлых параллельных suites [минимальный recheck](PH_LW_11_LOGS/runs/minimal-close-idle.run.json), source desktop и installed wheel завершились PASS. Это наблюдаемая последовательность, не доказанная root cause; flags/security settings не ослаблялись. Прерванные aggregate runs сохраняют ABORTED. Текущая method matrix не имеет незакрытых TIMEOUT/NOT RUN; mandatory acceptance environments перечислены отдельно.

Завершённый 38-method wheel run обнаружил два ERROR. Старый PH-LW-04 запросил отсутствующий bundled Chromium из-за пропущенного PH_LW_04_BROWSER_CHANNEL=msedge в команде; final run использует Edge. PH-LW-07 получил click timeout на скрытом project selector второй вкладки. Новый desktop resume применял общий сохранённый экран к cookie-вкладке. [Детерминированный before FAIL](PH_LW_11_LOGS/runs/tab-resume-before.log) воспроизвёл hidden selector. Launcher/manual-code теперь восстанавливает общий экран, fresh cookie tab открывает список проектов, reload сохраняет tab screen. Новый test и неизменённый PH-LW-07 прошли на source/final wheel; [delta](PH_LW_11_LOGS/TAB_RESUME_DELTA.json). В исходном 38-method log также сохранён Waitress WinError 10038 при teardown test-owned LiveServer; assertions завершились, production launcher clean-stop проверен отдельно.

## Открытые gates

1. **Manual long-path FAIL:** длинный profile/project root с LongPathsEnabled=0 даёт PREPARATION_IO_BLOCKED в staging copy. Source public prepare_handoff при той же длине воспроизвёл WinError 3. [Первый trace](PH_LW_11_LOGS/long-preparation-exact/ERROR.txt); [повтор с command/interpreter/hash](PH_LW_11_LOGS/runs/long-path-final.run.json), [результат](PH_LW_11_LOGS/long-path-final/RESULT.json). После него изменились только UI/metadata; compiler/filesystem algorithms идентичны final source. Более короткий Unicode-path PASS его не закрывает. Общий compiler/filesystem scope не расширен молча.
2. **Mandatory NOT RUN:** clean Windows machine, actual Unicode username, physical offline, real volume/quota disk-full. ENOSPC injection PASS не заменяет полный диск. [Host limitations](PH_LW_11_LOGS/HOST_LIMITATIONS.json): Sandbox/VirtualBox/VMware недоступны, Hyper-V запрещён текущему non-admin пользователю.
3. Обычный nonsilent setup log предыдущего UI build подтверждает postinstall Run entry, authenticated server и пустой catalog без дополнительного запуска. Visual walkthrough не завершён: автоматическая защита Computer Use не смогла надёжно определить browser URL. Installer UI clicks этим агентом не зафиксированы. [Interactive result](PH_LW_11_LOGS/installed-interactive/RESULT.json). Финальный EXE проверен отдельной scripted install/browser/uninstall acceptance.
4. **UNSIGNED:** signing credentials отсутствуют; финальная signature check — NotSigned. Не обещается отсутствие SmartScreen warnings. Pinned recipe воспроизводим по inputs; byte-for-byte reproducible PE без отдельной повторной сборки не заявляется.

Physical power loss и процессный crash посреди kernel commit не подменяются idle crash/installer interruption. Existing recovery suites сохраняют свою область. Defender/SmartScreen/UAC/firewall/ExecutionPolicy/PATH/LongPathsEnabled ради приёмки не менялись.

## Поставка и verdicts

[Installer](windows/Harness-Setup-win-x64.exe), [frozen inventory](windows/Harness/PACKAGE_FILES.json), [build recipe](local_web/windows/build_windows.py), [pins](local_web/windows/build_tools.json), [licenses](windows/Harness/THIRD_PARTY_LICENSES/DEPENDENCIES.json), [операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/19_PH_LW_11_Windows_Installation.md).

- Build `PH-LW-11-20261108`; source digest `sha256:6c39f9441c520713f7161d51a88403ea04e30068cb1373f531771cfe8b325b97`.
- Installer SHA-256 `b24c93efdd32be6f5bed70ebeb88d31502d1bf48cec63b93f473a8cdd74c556c`.
- Wheel SHA-256 `4e484ea88ccbf7875227c5970949244ede5d868735700a17629892e3382c98f2`.
- PACKAGE_FILES SHA-256 `a396239db1e2cef5d87715222f5204c6fc5b13cba71ab7befa512e7e989d3f6f`.
- [Final integrity attestation](../_workspace/PH_LW_11/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](../_workspace/PH_LW_11/SHA256.txt). Integrity PASS не равен acceptance GO.

PH-LW-04/05 и PH-LW-06–10: прежний принятый scope сохранён; применимые текущие regressions PASS по composite test IDs. Это не расширяет их acceptance environments. **PH-LW-11 NO-GO; LOCAL_WEB_MANUAL NO-GO; AUTOMATIC_EXECUTOR NO-GO; v0.5.1 NO-GO / NOT RELEASED.** Podman/positive governed egress остаются отдельными NO-GO. Следующий разрешённый шаг — новое задание пользователя на конкретные PH-LW-11 blockers; к PH-LW-12 не переходить.
