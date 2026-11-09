# PH-LW-12 — изменения

Allowed scope: acceptance tests/runners, прямые UI regression fixes, current operator docs/README, generated resources/build/wheel/frozen/installer/manifests, новые logs/matrices/reports и workspace navigation.

- `src/project_harness/resources/local_web/assets/app.js`, `lifecycle.js`, `tasks.js`, `interview.js`: resume ordering, свежие post-commit/read projections, навигация существующих форм.
- `assets/index.html`, `local_web_service.py`: truthful labels/disabled reasons, удаление исторических UI обещаний; в Python service только текст причины.
- `metadata_v1.json`, README и generated build/lib/egg-info/wheel/frozen/installer: новая сборка с точным digest.
- Новый `tests/test_ph_lw_12_acceptance.py`, `local_web/windows/final_acceptance.py` и `tools/ph_lw_12_*.py`: тесты, bounded runners, observers и публикация evidence. Старые test files/assertions не менялись.
- Новая глава `22_PH_LW_12_Operator_Acceptance.md`, docs aggregates/index/manifests и byte-identical embedded/frozen docs; текущая навигация workspace.
- Новые `PH_LW_12_LOGS`, report/matrices/changed-files и final attestation.

Нормативные specs/r2, `_inputs`, исторические reports/archives, core algorithms/schemas/registries сохранены. Automatic executor выключен. Engine/Documentation ZIP не собирались. Полный before/after hash inventory — [CHANGED_FILE_HASHES.json](../_workspace/PH_LW_12/CHANGED_FILE_HASHES.json); [test report](PH_LW_12_TEST_REPORT.md).
