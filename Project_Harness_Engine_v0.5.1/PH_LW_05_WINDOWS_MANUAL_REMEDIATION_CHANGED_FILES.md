# Изменения относительно предыдущей Windows HTTP поставки

Исторические reports/logs: **877 файлов побайтово неизменны**. Удалённых файлов нет. Полный список: [PH_LW_05_WINDOWS_MANUAL_REMEDIATION_CHANGED_FILES.json](PH_LW_05_WINDOWS_MANUAL_REMEDIATION_CHANGED_FILES.json).

Production: только `src/project_harness/migration.py` (Windows file flush и cleanup) и build metadata. Tests: platform-capability helper, 3 существующих fixture modules, новый native migration module. Docs: новый manual-migration chapter, README/CHANGELOG и generated aggregates/mirror. Build: source mirror, egg-info/SOURCES, wheel, manifests. Новые reports/logs не заменяют исторические.

Workspace отдельно: актуализированы AGENTS/current task/map/runbook и tools для адресной упаковки, установленного wheel, точного extracted rerun и отчёта с provenance. Эти development files не входят в Engine wheel.
