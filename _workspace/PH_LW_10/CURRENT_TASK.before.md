# Текущая работа

2026-11-07. Task-level manual evidence intake реализован; **PH-F06 blocker закрыт**, повторная **PH-LW-09 acceptance PASS в назначенном scope по current matrix с явными rechecks**. Монолитные native/wheel runs имели timing failures и сохраняют FAIL; подробности ниже и в новом отчёте. Automatic executor выключен, PH-LW-10 не начат, Engine/Documentation ZIP не создавались.

## База и результаты

Вход — проверенный PH-LW-09 WIP / NO-GO. [Baseline](PH_LW_09_MANUAL_EVIDENCE/INPUT_BASELINE.json), [input hashes](PH_LW_09_MANUAL_EVIDENCE/INPUT_FILE_HASHES.json), [предыдущий CURRENT_TASK](PH_LW_09_MANUAL_EVIDENCE/CURRENT_TASK.before.md). [Первый NO-GO report](../Project_Harness_Engine_v0.5.1/PH_LW_09_TEST_REPORT.md) и все его evidence сохранены неизменными.

Текущая распакованная версия: [новый фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_09_MANUAL_EVIDENCE_TEST_REPORT.md), [операторский контракт](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/17_PH_LW_09_Task_Manual_Evidence.md), [аттестация](PH_LW_09_MANUAL_EVIDENCE/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](PH_LW_09_MANUAL_EVIDENCE/SHA256.txt), [changed hashes](PH_LW_09_MANUAL_EVIDENCE/CHANGED_FILE_HASHES.json).

Build `PH-LW-09-MANUAL-EVIDENCE-20261107`; source digest `sha256:be49440e52d371bed2c15c8c1ce3ed0b5350f61c11c0b5c49a84a6f2dda4c1eb`; wheel SHA-256 `55402b3e747196789ebdd2dea75534e12a8a49cf10c820de8094901734903489`. Финальные manifests — во внешнем SHA256.txt; архивы не обновлялись.

- PH-F06: 13 PASS, 0 SKIP; все четыре прежних NOT RUN выполнены. Первый повтор при параллельной нагрузке остановился по исходному 10-second product subprocess timeout; отдельный полный повтор PASS без изменения проверок.
- Новые intake tests: 11 PASS в source и wheel, 0 SKIP.
- Native current matrix: 154 unique methods PASS, 0 SKIP. Монолитный run: один Edge locator timeout 30000 ms; точный case повторён и PASS. Doctor после manifest sync и docs validator PASS. Исходный FAIL сохранён.
- Installed wheel current matrix: 152 unique methods PASS, 0 SKIP, отдельная venv/Unicode CWD/site-packages и exact build metadata, console doctor/launcher/TCP health. Монолитный run: 1 import UI expectation timeout 5000 ms; тот же case повторён и PASS, timeout прежний. Исходный FAIL сохранён.
- [Полная свежая matrix](../Project_Harness_Engine_v0.5.1/PH_LW_09_MANUAL_EVIDENCE_LOGS/REGRESSION_MATRIX_CURRENT.json): 47 modules / 546 methods; 37 PASS, 3 PASS_WITH_SKIPS, 7 FAIL; 24 failure events, 88 errors, 7 SKIP, 0 module TIMEOUT. Mandatory NOT RUN назначенного scope отсутствует. [Сравнение](../Project_Harness_Engine_v0.5.1/PH_LW_09_MANUAL_EVIDENCE_LOGS/PREVIOUS_BASELINE_COMPARISON.json): семь прежних FAIL с теми же failed IDs; новый PH-F06 FAIL устранён.

## Scope и сохранённые границы

Allowed changes этого задания: новый public Task manual evidence API, runtime verify/complete, CLI, Local Web service/HTTP/UI; новые tests, усиленный PH-F06 operator fixture, PH-LW-09 positive browser flow и строгий PH-LW-01 CLI inventory update (29 exact entries: прежние 26 controls, launcher, две явные новые команды). Docs 16/17/README и mirrors, metadata/generated wheel/manifests, новые reports/evidence и workspace tooling/navigation. Старый PH-F06 test file и его assertions неизменны; нормативные specs/r2, core schemas/registries, planner, Stage approval/evidence semantics и accepted history не менялись.

Manual proof требует reviewer, observations, PASS/FAIL каждого точного check, current product sources/digests, exact Task/Run/snapshot/baseline/plan и отдельного consent. Один immutable review на Run; replay не создаёт новые evidence. Missing/stale/FAIL proof не даёт PASS. Verify/complete вновь проверяют текущий proof. Agent Result, allow_manual и command consent не заменяют operator review. Task proof не принимает Stage и не запускает команды. Public CLI: `task-manual-context`, `record-task-manual-evidence --input ... --confirm`; web form — «Задачи и Run».

Intermittent timing sensitivity наблюдалась в Edge/import и product subprocess приёмке. Она честно сохранена в raw logs; тестовые deadlines/assertions не увеличены и не отключены. Current verdict составной, не утверждение о зелёном exit монолитного CI; latency/stress гарантия не заявляется. Проверка общего устойчивого end-to-end остаётся предметом PH-LW-12. Physical power-loss/clean-machine installer/реальный Codex/positive governed per-Run egress/rootless Podman security не проверены этим дополнением.

PH-LW-04–09 PASS в своих scopes; LOCAL_WEB_MANUAL NO-GO до PH-LW-12; AUTOMATIC_EXECUTOR NO-GO; полная v0.5.1 NO-GO / NOT RELEASED. Следующий разрешённый шаг — только новое задание пользователя. К PH-LW-10 самостоятельно не переходить; automatic executor и ZIP не включать без нового явного задания.
