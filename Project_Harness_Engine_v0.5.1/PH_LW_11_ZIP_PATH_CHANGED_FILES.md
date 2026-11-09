# PH-LW-11 long app-data ZIP-import — изменения

Source IO adapters: `local_web_imports.py`, `local_web_exchange.py`, `local_web_source_refresh.py`, `local_web_sources_service.py`, `inventory.py` (inventory_source), `safety.py` (copy_tree_filtered), `serialization.py` (atomic_write_text); generated build metadata. ZIP validation/governance contracts неизменны. [AST evidence](PH_LW_11_ZIP_PATH_LOGS/LOGIC_DELTA.json).

Новые tests: `tests/test_ph_lw_11_zip_path.py` (7), `local_web/windows/zip_path_acceptance.py` (startup/snapshot adapter, прежние assertions/deadlines). Старые tests не изменены. Новая docs глава 21, ссылки README, generated aggregates/manifests и byte-identical embedded mirror. Пересобраны build/lib/wheel/self-contained bundle/installer из source.

Новые report/logs/workspace input/output evidence, helpers `tools/*ph_lw_11_zip_path*.py`, CURRENT_TASK/navigation. Исторические reports/attestations/archives/r2/specs и чужие изменения сохранены. [Before/after hashes](../_workspace/PH_LW_11_ZIP_PATH/CHANGED_FILE_HASHES.json), [input hashes](../_workspace/PH_LW_11_ZIP_PATH/INPUT_FILE_HASHES.json). Engine/Documentation ZIP не собирались.
