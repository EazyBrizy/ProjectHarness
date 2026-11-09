# PH-F08 — изменённые файлы и границы scope

- `tests/test_ph_f08_release_acceptance.py`: 2 независимых публичных CLI e2e smoke (I-01, I-03/I-12).
- `PH_F08_TEST_REPORT.md`, `PH_F08_ACCEPTANCE_MATRIX.md`, `PH_F08_RELEASE_MATRIX.json`, `PH_F08_LOGS/`: release acceptance, реальные логи и вердикты.
- `CHANGELOG.md`: финальный release gate v0.5.0.
- `docs/Project_Harness_Documentation_v0.5.0/`: синхронная копия выпускаемой документации, включая regenerated aggregates/index и manifest.
- `MANIFEST.sha256`: digest всех файлов engine после release packaging.
- `dist/project_harness_engine-0.5.0-py3-none-any.whl`: проверенный wheel с теми же production Python/resource bytes (исходный PH-F07 wheel не менялся).
- Documentation: `README.md`, `CHANGELOG.md`, regenerated full/index files, `MANIFEST.sha256`.

Production Python, schemas, registries, normative specifications, prior tests, completed historical artifacts unchanged. No scope expansion.
