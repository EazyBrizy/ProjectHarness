"""Promote CURRENT_TASK only after PH-LW-10 evidence has been published."""
import json
from package_acceptance import ROOT,ENGINE
W=ROOT/'_workspace/PH_LW_10'
def read(p):return json.loads(p.read_text('utf-8'))
summary=read(W/'RESULT_SUMMARY.json');assert summary['stage_verdict']=='PASS'
assert (ENGINE/'PH_LW_10_TEST_REPORT.md').is_file()
final=W/'FINAL_WORKING_TREE_VERIFICATION.json'
if final.exists() and read(final).get('status')=='PASS':raise RuntimeError('Completed checkpoint is immutable')
frozen=read(ROOT/'_scratch/ph_lw_10/FINAL_BUILD_FREEZE.json');native=summary['native'];matrix=summary['matrix']
text=f'''# Текущая работа

2026-11-07. **PH-LW-10 выполнен; PASS в назначенном manual scope.** Полный prompt r2 выполнен на проверенной базе PH-LW-09 manual evidence. Automatic executor выключен; PH-LW-11 не начат; Engine/Documentation ZIP не создавались.

## База и результаты

[Входной baseline](PH_LW_10/INPUT_BASELINE.json), [input hashes](PH_LW_10/INPUT_FILE_HASHES.json), [предыдущий CURRENT_TASK](PH_LW_10/CURRENT_TASK.before.md). Исторические отчёты/NO-GO и evidence сохранены неизменными.

[Фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_10_TEST_REPORT.md), [операторский контракт](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/18_PH_LW_10_Stage_Lifecycle.md), [changed files](../Project_Harness_Engine_v0.5.1/PH_LW_10_CHANGED_FILES.md), [аттестация](PH_LW_10/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](PH_LW_10/SHA256.txt), [before/after hashes](PH_LW_10/CHANGED_FILE_HASHES.json).

Build `PH-LW-10-20261107`; source digest `{frozen['engine_build_digest']}`; wheel SHA-256 `{frozen['wheel_sha256']}`. Актуальная поставка — обычные файлы в распакованных Engine/Documentation, с byte-identical docs mirror и синхронным wheel/build/lib. Архивы не обновлялись.

- Новые PH-LW-10 tests: {native['ph_lw_10_tests']} PASS, 0 SKIP в source и установленном wheel.
- Native PH-LW-04–10: {native['tests']} unique methods PASS, 0 SKIP в current composite matrix; полный run + {native['final_source_recheck_tests']}-test recheck (включая {native['native_final_ui_tests']} browser/HTTP cases) и новый deterministic polling test. Doctor/docs PASS.
- Installed wheel: {native['installed_wheel_tests']} unique methods PASS, 0 SKIP в current composite matrix; исходные main/native + final installed browser/HTTP/native recheck. Отдельная venv/Unicode CWD/site-packages; exact metadata, console doctor/launcher/TCP health PASS.
- PH-F06: 13 PASS, 0 SKIP; Windows manual migration: 10 PASS.
- [Полная matrix](../Project_Harness_Engine_v0.5.1/PH_LW_10_LOGS/REGRESSION_MATRIX_CURRENT.json): {matrix['modules']} modules / {matrix['test_methods']} methods; {matrix['module_statuses']['PASS']} PASS, {matrix['module_statuses']['PASS_WITH_SKIPS']} PASS_WITH_SKIPS, 7 inherited FAIL; {matrix['failure_events']} failure events, {matrix['error_events']} errors, {matrix['skips']} SKIP, {matrix['timeouts']} module TIMEOUT. Mandatory NOT RUN назначенного scope отсутствует.

Первый native attempt остановлен после выявления несовместимого action inventory GREENFIELD (32 вместо 27); raw ABORTED/FAIL сохранены. Новые helpers ограничены совместимым kind, UI IDs уникальны. Исходный PH-LW-03 test не менялся; полный recheck 15 PASS, PH-LW-01 9 PASS. Последующие полные native/installed runs получили по одному FAIL в прежнем PH-LW-07 browser case и не объявлены PASS: два concurrent reads заново рисовали consent field до POST. `approvals.js` объединяет чтения; после fix три исходных cases и все затронутые browser/HTTP modules повторены успешно в source/wheel. Промежуточный HTTP recheck с WinError 10055 сохранён, закрыт полным module PASS; системные настройки не менялись. Verdict composite, не монолитный CI exit 0.

Промежуточный ui-final также выявил ошибку команды без явного msedge и migration UI polling timeout. Новый deterministic test воспроизвёл чтение уже удалённого backup при polling receipt. Исправлены только `_registered`/`get_operation`: app-owned migration status не сканирует изменяемое дерево; ownership/digest/native ancestor checks и все mutation/recovery fences сохранены. После fix весь затронутый scope повторён source/wheel. Исходные FAIL/ERROR сохранены. Точная связь исходного browser timeout с этой гонкой — inference, так как server trace того occurrence отсутствует.

[Build delta](../Project_Harness_Engine_v0.5.1/PH_LW_10_LOGS/BUILD_DELTA.json) проверяет hashes/AST изменённых двух service methods, approvals.js, metadata и единственный добавленный polling test; core algorithms, mutators и прежние test bytes неизменны. [Сравнение](../Project_Harness_Engine_v0.5.1/PH_LW_10_LOGS/PREVIOUS_BASELINE_COMPARISON.json) сохраняет те же failed IDs семи унаследованных FAIL. Семантические assertions и deadlines не ослаблены.

## Scope и сохранённые границы

Allowed changes этого задания: новые lifecycle_forms/local_web_lifecycle/local_web_selection; LocalWeb service/HTTP/assets integration; новые PH-LW-10 tests/Windows runner; глава 18, README/aggregates/docs mirror; metadata/generated wheel/manifests; новые reports/evidence/workspace tooling/navigation. Core governance/migration/maintenance algorithms, core schemas/registries, прежние test files, normative specs/r2 и исторические reports/evidence сохранены.

Stage overview использует canonical target и exact semantic gaps. Отдельный per-subject review → existing accept_stage; active planning → первый READY ближайшей Stage; level-up последовательный. Maintenance same-level с ordinary manual Tasks и допустимой отменой. Brownfield source read-only, stale inventory отвергается, baseline approval отдельно. Migration через validator/public API, manual default, immutable history, explicit journal recovery. GET/polling read-only; только bounded GET retry при OPERATION_CONFLICT, POST автоматически не повторяется. UI не назначает canonical states.

Physical power loss, clean-machine installer, реальный Codex и полный PH-LW-12 end-to-end не подтверждены этим этапом. Rootless Podman security и positive governed per-Run egress остаются отдельными NO-GO.

PH-LW-04–10 PASS в своих scopes; `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1 `NO-GO / NOT RELEASED`. Следующий разрешённый шаг — только новое задание пользователя. К PH-LW-11 самостоятельно не переходить; automatic executor и ZIP не включать.
'''
(ROOT/'_workspace/CURRENT_TASK.md').write_text(text,'utf-8')
