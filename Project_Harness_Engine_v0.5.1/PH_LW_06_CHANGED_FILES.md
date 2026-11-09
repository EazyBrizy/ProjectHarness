# PH-LW-06 — изменённые файлы

Дата: 2026-11-07. База: Engine `c8ccd7f1f1b93200db1936d58c274bf535fae09aa616309b54bed8e0e3da33f2`, Documentation `5b1dbed1ab7b876b8d5f078596c5c7ca327cd1f269d438407e88ac7bd95d4bd9`. Пути в таблице — от Engine, если не указано иное.

| Файлы | Изменение |
|---|---|
| `src/project_harness/local_web_exchange.py` (новый) | Private bounded pack/preview/commit/cancel/recovery; exact source/input/core binding, provenance, replay и explicit transfer policy; canonical writes только через public draft API |
| `src/project_harness/local_web_exchange_contract.py` (новый) | Strict bounded JSON, safe validation errors/repair, protected fields/approvals, relative product paths, exact refs, secret pattern refusal |
| `src/project_harness/local_web_service.py`, `local_web_sources_service.py` | Explicit service entrypoints и pending-exchange mutation fence; actual status/target/readiness blockers |
| `src/project_harness/local_web_http.py` | Authenticated read endpoints и guarded POST exchange routes; strict wrappers/body limits; owned file downloads |
| `src/project_harness/project_input.py` | Прямой regression fix: UNKNOWN и material unknowns блокируют readiness; compound questions отражают missing children; UNSURE остаётся WAITING_DECISION |
| `src/project_harness/resources/local_web/gpt_exchange_reply_v2.schema.json`, `GPT_PREPARATION.md` (новые) | Отдельный envelope v2 и актуальный browser `PROJECT_INPUT@4` draft-only template; historical v1/@3 сохранены |
| `src/project_harness/resources/local_web/assets/interview.js` (новый), `app.js`, `app.css`, `index.html` | Typed forms/real questions/known-answer editing; review/export/copy/download; paste/repair/diff/cancel/commit/reload, text-only rendering |
| `src/project_harness/resources/local_web/metadata_v1.json` | PH-LW-06 build/source digest, exact входная база, envelope version и archive-policy provenance; старая lineage сохранена |
| `pyproject.toml` | В wheel включён новый `.md` browser template |
| `tests/test_ph_lw_06_exchange.py`, `tests/test_ph_lw_06_http.py` (новые) | 16 service/contract/recovery methods и 4 реальных TCP/Edge methods, включая оба Greenfield fixture сценария |
| `local_web/ci_ph_lw_06_windows.ps1` (новый), `run_windows_acceptance.py` | Native stage06, optional DocumentationZip по новому правилу; прежние stages сохранены |
| `README.md`, `PH_LW_06_*` | Текущий checkpoint, новый report, invariants и независимые logs; прежние reports/logs не переписаны |
| Standalone Documentation: новая глава `13_Local_Web_Manual_Companion/13_PH_LW_06_Interview_and_GPT_Exchange.md`, README, CHANGELOG | Полный текущий UI/contract/limits/recovery/runbook; сохранена отдельная пользовательская правка правила ZIP |
| Standalone aggregates/index/manifest и `docs/Project_Harness_Documentation_v0.5.1/` | Генерация aggregates/index и побайтовая синхронизация полного зеркала |
| `build/lib`, `dist`, `src/project_harness_engine.egg-info`, `MANIFEST.sha256` | Производные файлы из canonical source; вручную не исправлялись |
| Workspace: `tools/sync_working_tree.py`, `finalize_ph_lw_06_evidence.py`, `verify_ph_lw_06_working_tree.py` (новые) | Синхронизация без ZIP, публикация evidence и финальная hash-attestation рабочих деревьев |
| Workspace: `tools/verify_installed.py`, `check_workspace.py` | Installed-wheel PH-LW-06 subset; проверка новых report links, исключение code fences из Markdown link scanner |
| Workspace: CURRENT_TASK, PROJECT_MAP, RUNBOOK, `_workspace/PH_LW_06/` | Текущая база, воспроизводимые команды и внешние hashes; предыдущая archive-policy task сохранена отдельно |

`AGENTS.md`, workspace README и правило ZIP изменены отдельным параллельным заданием пользователя; они сохранены, не приписываются реализации PH-LW-06. Их provenance — [отдельный отчёт](../_workspace/ARCHIVE_POLICY_2026-11-07/REPORT.md). Документационные README/aggregate/manifests содержат обе совместимые правки.

Точная машинная ведомость всех additions/modifications/deletions с before/after SHA-256 находится в [CHANGED_FILE_HASHES.json](../_workspace/PH_LW_06/CHANGED_FILE_HASHES.json), полный итог — [TEST_REPORT](PH_LW_06_TEST_REPORT.md). Ведомость сравнивает рабочие деревья с проверенной входной ZIP-парой, поэтому включает сохранённое параллельное изменение политики. Новых Engine/Documentation ZIP нет.
