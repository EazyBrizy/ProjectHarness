# PH-LW-07 — изменённые файлы

Дата: 2026-11-07. База: распакованные PH-LW-06 деревья, сверенные с предыдущей внешней аттестацией. Git checkout в workspace отсутствует; исходное состояние зафиксировано полным file-hash snapshot. Расхождений с проверенной базой не было.

## Разрешённые и фактические изменения

| Файл / группа | Назначение |
|---|---|
| [local_web_approval_core.py](src/project_harness/local_web_approval_core.py) | Новый public provisional approval API: schema/readiness/sequence, exact intent validation, atomic input write |
| [local_web_approvals.py](src/project_harness/local_web_approvals.py) | Новый application flow: actor, предметы, receipts, revisions/digests, rework/invalidation, replay, crash recovery и budgets |
| [local_web_service.py](src/project_harness/local_web_service.py) | Явные forwarding APIs согласований |
| [local_web_http.py](src/project_harness/local_web_http.py) | Защищённые routes, strict DTO fields, локальный asset; honest pending prepare до PH-LW-08 |
| [local_web_exchange.py](src/project_harness/local_web_exchange.py) | Fence незавершённого approval commit и показ unresolved rework comments в опросе |
| [approvals.js](src/project_harness/resources/local_web/assets/approvals.js) | Четыре/пять отдельных форм, exact content, actor, receipts, комментарии, stale/retry/recovery |
| [index.html](src/project_harness/resources/local_web/assets/index.html), [app.js](src/project_harness/resources/local_web/assets/app.js), [interview.js](src/project_harness/resources/local_web/assets/interview.js), [app.css](src/project_harness/resources/local_web/assets/app.css) | Экран согласований, навигация, доступные действия, rework и читаемая раскладка |
| [metadata_v1.json](src/project_harness/resources/local_web/metadata_v1.json) | Build PH-LW-07, provenance входных manifests, source build digest и сохранённые release boundaries |
| [test_ph_lw_07_approvals.py](tests/test_ph_lw_07_approvals.py), [test_ph_lw_07_http.py](tests/test_ph_lw_07_http.py) | Новые positive/negative/concurrency/recovery tests, настоящий subprocess, Waitress/TCP/Edge |
| [run_windows_acceptance.py](local_web/run_windows_acceptance.py), [ci_ph_lw_07_windows.ps1](local_web/ci_ph_lw_07_windows.ps1) | Native stage07 с прежними PH-LW-04–06 checks, без обязательного ZIP |
| [README.md](README.md), standalone docs README и [новая глава](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/14_PH_LW_07_Separate_Approvals.md) | Текущий операторский маршрут, APIs, limitations и связи; прежние главы остаются checkpoint history |
| Docs aggregate/index/manifests и embedded mirror | Генерация validator/helper, побайтовая синхронизация |
| `build/lib`, `dist`, `src/*.egg-info`, manifests | Сгенерированы из src/build inputs, не редактировались вручную |
| `PH_LW_07_TEST_REPORT.md`, `PH_LW_07_PRESERVED_INVARIANTS.md`, `PH_LW_07_LOGS/` | Новые фактические результаты, сохранённые ранние FAIL, финальные native/wheel/matrix runs |
| Workspace CURRENT_TASK/PROJECT_MAP/RUNBOOK/README, tools verify_installed/check_workspace и новые finalize/verify helpers | Навигация, воспроизведение без ZIP, независимая wheel acceptance и точная внешняя аттестация |

Список всех изменённых/новых рабочих файлов с before/after SHA-256 — [CHANGED_FILE_HASHES.json](../_workspace/PH_LW_07/CHANGED_FILE_HASHES.json). Входные bytes идентифицирует [INPUT_FILE_HASHES.json](../_workspace/PH_LW_07/INPUT_FILE_HASHES.json), финальные trees/wheel — [SHA256.txt](../_workspace/PH_LW_07/SHA256.txt). Evidence index отдельно различает raw и published hashes; logs не редактируют исторические verdicts.

Не менялись normative specs, prompts r2, `_inputs`, старые планы/reports/ZIP, core schemas/registries и существующие formal Stage/level-up tests. Не добавлены PH-LW-08 preparation/placement, automatic executor, provider/egress/Podman functionality. Engine/Documentation ZIP не собирались.
