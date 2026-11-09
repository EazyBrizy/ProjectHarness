# PH-LW-12 — финальная Windows/browser/security приёмка

2026-11-08. **PH-LW-12: NO-GO.**

`LOCAL_WEB_MANUAL: NO-GO`  
`AUTOMATIC_EXECUTOR: прежний NO-GO; выключен`

Полная v0.5.1 остаётся **NO-GO / NOT RELEASED**. Engine/Documentation ZIP не создавались. Поставляются распакованные рабочие файлы, wheel и UNSIGNED installer. Это самостоятельный checkpoint; старые reports/NO-GO и prompts r2 сохранены.

Отдельные текущие verdicts: PH-LW-04 — `GO in tested Windows scope`; PH-LW-05 — `NO-GO for deep app-data intake; baseline source-import coverage recorded separately`. Прежние отчёты не переписаны.

## База и область

Выполнен [полный PH-LW-12 r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_12.md) на проверенной PH-LW-11 базе, принятой пользователем с четырьмя ограничениями. [Input baseline](PH_LW_12_LOGS/INPUT_BASELINE.json), [input hashes](PH_LW_12_LOGS/INPUT_FILE_HASHES.json). Drift на входе отсутствовал. Новое явное уточнение пользователя ограничило платформу Windows: POSIX-only legacy cases не запускать и не назначать prerequisite. Первоначальный Linux test attempt остановлен; новый runner удалён из Engine; его результаты в приёмку не включаются.

Allowed changes: acceptance tests/runners, прямые UI regressions, current README/operator docs, mirrors, generated wheel/frozen/installer/manifests и новые evidence/reports. Python-алгоритмы core, schemas/registries, old test bytes и исторические отчёты не менялись; в service изменена только устаревшая формулировка disabled reason. [Изменения](PH_LW_12_CHANGED_FILES.md), [before/after](../_workspace/PH_LW_12/CHANGED_FILE_HASHES.json).

## Исправления

Пользовательский JSON POST теперь ждёт собственную очередь navigation resume: отдельный Edge regression воспроизвёл overtaking до fix и прошёл после. POST автоматически не повторяется, guards не ослаблены. Доступные stage-status/manual-evidence открывают существующие формы; удалены устаревшие обещания следующего этапа/ожидания PH-LW-09. Общий log export явно disabled с причиной.

После commit и явного refresh UI запрашивает новую проекцию, дождавшись старого in-flight чтения. Регрессия воспроизведена неизменными прежними assets из сохранённого frozen build: UI READY_FOR_CODEX при canonical TASK_BLOCKED; новый source test PASS. Python bytes и контракты при этом неизменны: [delta](PH_LW_12_LOGS/REFRESH_DELTA.json). Source/installed/frozen rechecks указаны отдельно; ранние FAIL/TIMEOUT не переписаны.

## Фактическая проверка

Текущий discovery: **607 methods / 53 modules**; Windows scope — 451 methods; Windows current outcomes: `{'PASS': 449, 'SKIP': 2}`. Не-Windows 156 methods — NOT RUN вне уточнённой платформы. [Полная method matrix](PH_LW_12_LOGS/METHOD_RESULTS.json), [verdicts и незакрытые cases](PH_LW_12_LOGS/VERDICTS.json).

| Run | Результат |
|---|---|
| installed-basic-supported | PASS |
| installer-recovery-final | PASS |
| installed-extended-final | FAIL |
| installed-extended-focus3 | FAIL |
| installed-no-doc-final | PASS |
| installed-maintenance-final | FAIL |
| maturity-final | PASS |
| exchange-http-final | PASS |
| lifecycle-http-final | PASS |
| lifecycle-service-final | PASS |
| wheel-browser-final | PASS |
| source-final-regressions | PASS |


Actual installed EXE baseline MD/ZIP→GPT fixture→отдельные approvals→publish/JIT, restart/resume/crash/port/no-browser second launch, doctor/interpreter refusal и uninstall: `PASS`, tests `{'ran': 4, 'errors': 0, 'failures': 0, 'skips': 0}`. Подтверждённые retained paths: `284` / `271` символов. LongPathsEnabled 0→0. [EXE result](PH_LW_12_LOGS/installed-basic-supported/RESULT.json), [actual installer recovery](PH_LW_12_LOGS/installer-recovery-final/RESULT.json).

Расширенный EXE набор: исходный полный run — 18 methods, 3 FAIL / 1 ERROR. Текущее объединение по test IDs после отдельных rechecks: **`{'PASS': 17, 'FAIL': 1}`**; это составное evidence, не новый monolithic PASS. No-doc весь путь result → manual evidence → независимый PASS → отдельное complete прошёл: [result](PH_LW_12_LOGS/installed-no-doc-final/RESULT.json). MVP → RELEASE с проверкой accepted history и production HTTP limits прошли в [focused run](PH_LW_12_LOGS/installed-extended-focus3/browser.log). Maintenance result-upload остаётся FAIL: [HTTP response](PH_LW_12_LOGS/installed-maintenance-final/task-responses-maintenance.json), [UI state](PH_LW_12_LOGS/installed-maintenance-final/ui-test_maintenance_task_completion_through_browser.json).

Исправления только нового driver: ошибочная повторная прогонка READY-task recipe из уже VERIFYING Gate заменена byte-validated accepted MVP cache; expect timeout 5 s, оставшийся несмотря на page timeout 30 s, исправлен на общий browser expect 30 s; внешний fixture agent формирует result до начала UI reads. Старые assertions не менялись. Предыдущие ошибки и исходные logs сохранены. [Runner versions](PH_LW_12_LOGS/FINAL_ACCEPTANCE_RUNNER_VERSION.json), [maintenance driver](PH_LW_12_LOGS/MAINTENANCE_RUNNER_VERSION.json).

Source-only fixture layout PH-F01/F03/F04: 27 PASS на native Windows source; попытка запустить их неизменёнными через wheel получила missing test-fixture paths, а не runtime failure. Тесты не переписаны. Параллельный native run также сохранил WinError 10055, timeout вложенной product fixture и два outer TIMEOUT; completed sequential rechecks имеют явный supersession по test IDs. Ни один незавершённый run не переименован PASS. [Source-layout rechecks](PH_LW_12_LOGS/source-layout-rechecks/MATRIX.json).

Advanced fixture cache — отдельно проверенные initial states публичного kernel flow, не browser E2E с нуля. Все засчитываемые browser transitions/approvals/result/verification/completion используют реальные формы. Product writes — явно внешний fixture agent; прямых YAML edits control plane в browser segment нет. GPT fixture проверяет протокол, а не интеллект модели. SDK в product-command fixtures — явно test-driver Python; no-doc full flow использует manual evidence без продуктового SDK. Четыре/пять approvals, Stage/MVP→RELEASE, maintenance, Brownfield и migration имеют собственные строки logs.

Среда: настоящий Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, pinned Playwright/реальный headless Edge/TCP. Wheel из независимой Unicode CWD/site-packages без source PYTHONPATH. Frozen process получает System32-only PATH. Это не clean-machine и не physical-offline evidence. Полные argv/cwd/interpreter/build bindings и exit — в `.run.json` и [evidence index](PH_LW_12_LOGS/EVIDENCE_INDEX.json).

## Открытые blockers и наблюдения

**LW12-DEEP-APPDATA-INTAKE: OPEN.** Дополнительный более глубокий app-data root приводит к WinError 206 при `intake.py:157` (`workspace.mkdir`); `local_web_sources_service.py:113` cleanup затем маскирует его WinError 145. Public intake не регистрируется; остаётся partial app-owned session. [Native reproduction](PH_LW_12_LOGS/ADDITIONAL_PATH_STRESS.json), [первый EXE stress FAIL](PH_LW_12_LOGS/installed-basic-final/RESULT.json). Это не прежний ZIP-import bug и не automatic-only blocker. Геометрия путей ранее принятой PH-LW-11 базы повторена отдельно и прошла; более глубокий FAIL сохранён и не объявлен принятым ограничением. Полный manual GO не выдаётся.

Узкие source experiments с mkdir/cleanup выявили дальнейшие plain-path resolve/existence failures и не дали полного IO fix. Они полностью отменены, точные production bytes восстановлены: [revert attestation](PH_LW_12_LOGS/PATH_IO_EXPERIMENT_REVERTED.json). Непроверенная часть исправления не включена в wheel/installer.

**LW12-MAINTENANCE-RESULT-CONFLICT: OPEN.** На actual installed EXE после создания maintenance Task и navigation/refresh загрузка result получает 409 `OPERATION_CONFLICT`; result остаётся NOT_RECEIVED, verification недоступна. Повтор с устранённым конфликтом fixture-helper тоже FAIL. Own UI read overlap — гипотеза по sequence и коду, точный holder guard не трассирован. Нельзя засчитать maintenance verify/complete по успешному start/cancel или по source API tests. [Final failing run](PH_LW_12_LOGS/installed-maintenance-final/RESULT.json).

**LW12-PROJECT-LIST-PROJECTION: OPEN, observed UI inconsistency.** На настоящем [скриншоте после MVP→RELEASE](PH_LW_12_LOGS/installed-extended-focus3/screenshots/10/mvp-to-release.png) lifecycle показывает STAGE_PLANNING_REQUIRED и active RELEASE, а карточка списка — прежний TARGET_LEVEL_REACHED. Вероятная причина — `state.projects` обновляется только list GET; это вывод из кода, не отдельно прошедший regression test. [Observation](PH_LW_12_LOGS/UI_PROJECTION_OBSERVATION.json). Отдельно исправленный stale lifecycle GET не закрывает это наблюдение.

Также незакрыты все NOT RUN/FAIL/TIMEOUT, явно перечисленные в current Windows matrix. Новые обязательные пробелы не списываются на старый automatic verdict. Четыре ранее принятых NOT RUN — clean Windows, physical offline, real disk-full и actual Unicode username — не блокируют повторно. Fresh normal second launch, открывающий default browser, не выполнялся по запрету новых видимых окон; точный отказ второго --no-browser и прежнее normal-launch evidence разделены.

## Поставка и целостность

Build `PH-LW-12-20261108`, source digest `sha256:54aff06eb60bd64b4c87e69c9b7d5c3133f4747bdff0c4ee1f570874cfac8b08`.  
Wheel SHA-256 `765e9bb3a63773e1d4710e21ad330c18713555fb6cf5d8e84660eee52c03ef93`.  
Installer SHA-256 `454d3db52f3c880a3ff1b1243059cf5818961c9f8fc22adca4eb9949a7dac630`.

[Integrity](PH_LW_12_LOGS/INTEGRITY.json): wheel CRC/RECORD/source bytes, frozen inventory, standalone/embedded/frozen docs, resource mirrors и отсутствие private runtime files. Payload Harness.exe — AMD64 PE `0x8664`; Inno Setup bootstrap — x86 PE `0x14c`, x64compatible target. Installer UNSIGNED. Exact schemas/registries сохраняются. После финального runtime freeze допустимы только tests/evidence/reports/навигация и manifests; любые прежние пересборки имеют отдельные hashes. [Freeze](PH_LW_12_LOGS/RUNTIME_FREEZE.json), [final working-tree attestation](../_workspace/PH_LW_12/FINAL_WORKING_TREE_VERIFICATION.json).

Scan имеет заявленные границы: controlled runtime source/resources/docs и публикуемые text logs; это не универсальная DLP или анализ секретов внутри всех бинарников. Raw uploads/auth/operator roots, `_scratch`, `_tools`, `.venv` и caches в distribution не копируются. [Published-log scan](PH_LW_12_LOGS/PUBLISHED_LOG_SCAN.json). Скриншоты — настоящие synthetic UI; приватных пользовательских документов/credentials в них нет.

[Acceptance matrix](PH_LW_12_LOGS/ACCEPTANCE_MATRIX.json), [Control matrix](PH_LW_12_LOGS/CONTROL_MATRIX.json), [Security matrix](PH_LW_12_LOGS/SECURITY_MATRIX.json), [операторская глава 22](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/22_PH_LW_12_Operator_Acceptance.md). Исторические Engine/Documentation ZIP неизменны и не называются обновлёнными.

Следующий шаг в пределах PH-LW-12 manual scope — устранение deep app-data intake/cleanup, result-upload конфликтов и устаревшей карточки, затем повтор затронутых Windows gates на новом freeze. К automatic executor/Podman/egress не переходить; Linux jobs не запускать; ZIP без отдельного запроса не создавать.
