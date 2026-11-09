# Публикация проверенной базы Project Harness в Git

Дата: 2026-11-09. Репозиторий: [EazyBrizy/ProjectHarness](https://github.com/EazyBrizy/ProjectHarness), ветка `main`. Репозиторий на входе пустой; публикация создаёт начальный commit. Force push не используется.

В Git включены исходники движка, standalone/embedded документация, specs, prompts r2, планы, tests, tooling, фактические отчёты/evidence, принятые wheel, Windows installer и frozen bundle FIX5. Существующие `_inputs`, `_deliverables`, `_scratch`, `_tools`, `.venv`, generated build/egg-info, caches и приватные operator uploads/auth остаются локальными. Другие результаты `dist` исключены; точный принятый wheel включён отдельно.

Build `PH-LW-12-FIX5-20261108`:

- Source digest: `sha256:0789035971ad3488b37a3d1cc480a9c7c63effcc3c67c540630e452b77f936ae`.
- Wheel SHA-256: `22ce3cdca5fe875430d4780f163975ba896c3348fa2f30b5a88199064bec54a1`.
- Installer SHA-256: `a4c7432852aadf93fd19fa4646ef8306854369be8ff8fd941ce6d1d268cc5964`.

Предпубликационная проверка принятых source/docs/artifacts/manifests: PASS. Точные hashes — [BASELINE.json](BASELINE.json), исходная приёмка — [PH-LW-12 FIX report](../../Project_Harness_Engine_v0.5.1/PH_LW_12_FIX_TEST_REPORT.md). Бинарные artifacts используются без пересборки. `.gitattributes` отключает преобразование окончаний строк, сохраняя исходные bytes; перед commit индекс Git сверяется с рабочими файлами.

Credential/auth scan имеет ограниченную область: текстовые кандидаты Git и известные marker patterns. Совпадение PEM header в `test_ph_lw_06_exchange.py` — отрицательная fixture `synthetic-not-a-key`; реальных key/auth values в проверенном наборе не найдено. Бинарный payload сверяется по принятому freeze; scan не является универсальной DLP.

Runtime, tests, standalone/embedded docs и прежние отчёты/аттестации не редактируются. `CURRENT_TASK.md` получает отдельную запись о Git; его прежний hash остаётся в исторической аттестации, а прежние bytes сохранены в [CURRENT_TASK.before.md](CURRENT_TASK.before.md). Полные acceptance manifests описывают рабочую поставку с generated build outputs и локальными input provenance, а не состав Git checkout; для source/docs/artifacts используется точный freeze.

Новые тесты движка для Git metadata не требуются. Сохраняется прежний verdict: `LOCAL_WEB_MANUAL: GO` с принятыми ограничениями; `AUTOMATIC_EXECUTOR: NO-GO`, выключен; полная v0.5.1 `NOT RELEASED`. Linux/WSL/Docker и новые CI workflows не запускаются. Engine/Documentation ZIP не создаются.
