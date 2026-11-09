# PH-LW-11 — изменения

Source: новые `local_web_instance.py`, `local_web_desktop.py`, `windows_package.py`; integration в `local_web_launcher.py`, `local_web_http.py`, `resources.py`, `resources/local_web/assets/app.js`, `index.html`, `metadata_v1.json`. Core algorithms не менялись.

Новые tests/build: `tests/test_ph_lw_11_desktop.py`, `local_web/ci_ph_lw_11_windows.ps1`, `local_web/windows/` (pinned locks/compiler hash/manifest/PyInstaller recipe/Inno source/actual EXE/recovery runners). Старые tests неизменны; semantic expectations не ослаблены.

Docs: новая глава 19 Windows Installation, README/FILE_INDEX/aggregate/manifests и byte-identical mirror; Engine README. Generated `build/lib`, `dist`, egg-info, `windows/` собраны из source. Новые reports/logs/evidence, `_workspace/PH_LW_11/`, `tools/*ph_lw_11*.py`, CURRENT_TASK/README/PROJECT_MAP/RUNBOOK; узкие additions в check_workspace/verify_installed.

Private scratch/tools/auth/uploads/browser caches/venv в поставку не включены. Normative/r2, schemas/registries, old tests/reports/NO-GO, `_inputs` и исторические архивы сохранены.

[Все before/after hashes](../_workspace/PH_LW_11/CHANGED_FILE_HASHES.json), [input hashes](../_workspace/PH_LW_11/INPUT_FILE_HASHES.json), [attestation](../_workspace/PH_LW_11/FINAL_WORKING_TREE_VERIFICATION.json), [отчёт](PH_LW_11_TEST_REPORT.md).
